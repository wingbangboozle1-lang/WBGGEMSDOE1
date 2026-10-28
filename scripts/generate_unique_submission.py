#!/usr/bin/env python3
"""Generate a unique, portal-valid GeoTIFF submission for the DOE GEMS Prize.

Geological hypothesis (blind-fault adjacency with distance-decayed emission):

  Known USGS/INGENIOUS catalogue faults are already mapped; the leaderboard
  rewards newly discovered faults.  Blind faults are most likely to occur
  adjacent to -- but not on -- mapped traces (splays, stepovers, blind
  extensions).  GEMSDOE32's B2 (reported 0.2778) uses a hard catalogue
  exclusion (dots > 2 px from the catalogue).  This script replaces that hard
  cut with a smooth, distance-decayed emission kernel whose probability peaks
  at an intermediate distance (~150 m) from known faults, then decays toward
  both the catalogue (already mapped) and the far background (unrelated
  structure).  The resulting dot field is intentionally different from every
  registry raster: it carries no dots on the catalogue and a distinct spatial
  decay signature.

Usage:
    .venv/bin/python scripts/generate_unique_submission.py

Outputs:
    docs/downloads/<name>.tif            portal-safe float32 GeoTIFF (zeros outside)
    docs/downloads/<name>.zip             one-TIFF ZIP
    docs/downloads/<name>.validator.json  format validation receipt
    docs/downloads/<name>.holdout.json    HOLDOUT-DTI receipt
    docs/downloads/<name>.note.txt        submission name + <=140 char note
    docs/downloads/<name>.run-card.json   complete JSON run card

All numbers are labelled MODEL-ESTIMATE / HOLDOUT-DTI.  No organizer score is
claimed.  Verdict is promote only if: format PASS, HOLDOUT-DTI CI strictly
positive, no dots on catalogue.  Otherwise the verdict is negative (a
deliverable).
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems1.grid import read_template, read_labels, write_geotiff  # noqa: E402
from gems1.holdout import build_context, evaluate_mask, EVALUATOR_VERSION as HOLDOUT_VERSION  # noqa: E402
from gems1.metric import dti_binary, ALPHA, BETA  # noqa: E402
from gems.submission import check_variants  # noqa: E402
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DOWNLOADS = ROOT / "docs" / "downloads"
BRIDGE = ROOT / "data" / "bridge"
TEMPLATE_PATH = BRIDGE / "sample_submission.tif"
LABELS_PATH = BRIDGE / "existing_faults.tif"

# Emission kernel: Gaussian in distance, peak at d_peak px from catalogue.
# At 100 m resolution, 1 px = 100 m.  Peak at ~1.5 px = 150 m targets the
# blind-fault adjacency zone; sigma ~ 1.0 px = 100 m controls decay width.
D_PEAK_PX = 1.5
D_SIGMA_PX = 1.0

# Emission budget: 2.5% of footprint pixels per quadrant (same as holdout).
BUDGET_FRAC = 0.025

STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
FAMILY = "WBGGEMSDOE1"
HYPOTHESIS = "blind-fault-adjacency-distance-decay"
NAME = f"{FAMILY}-{HYPOTHESIS}-{STAMP}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_surface(labels: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Smooth distance-decayed emission surface from the catalogue.

    Zero on/very near known faults (already mapped), rising to a peak at an
    intermediate blind-fault distance, then decaying toward background.
    """
    dist = distance_transform_edt(~labels)  # px distance to nearest catalogue pixel
    z = (dist - D_PEAK_PX) / D_SIGMA_PX
    bump = np.exp(-0.5 * z * z)
    bump = np.where(dist <= 0.5, 0.0, bump)  # hard zero on catalogue
    bump = np.where(~footprint, 0.0, bump)
    mx = float(bump.max())
    if mx > 0:
        bump = bump / mx
    return bump.astype(np.float32)


def place_dots(surface: np.ndarray, footprint: np.ndarray, labels: np.ndarray,
               budget_frac: float = BUDGET_FRAC) -> np.ndarray:
    """Place binary dots via per-quadrant top-k on the emission surface.

    No dots on the catalogue.  Budget = budget_frac of footprint pixels total,
    split evenly across 4 spatial quadrants to avoid clustering.
    """
    H, W = surface.shape
    yy, xx = np.nonzero(footprint)
    ym, xm = int(np.median(yy)), int(np.median(xx))
    gy, gx = np.ogrid[:H, :W]
    quad = np.full((H, W), -1, dtype=np.int8)
    quad[(gy < ym) & (gx < xm) & footprint] = 0
    quad[(gy < ym) & (gx >= xm) & footprint] = 1
    quad[(gy >= ym) & (gx < xm) & footprint] = 2
    quad[(gy >= ym) & (gx >= xm) & footprint] = 3

    dots = np.zeros((H, W), dtype=bool)
    total_budget = int(round(budget_frac * int(footprint.sum())))
    per_quad = max(1, total_budget // 4)

    for q in range(4):
        qmask = footprint & (quad == q)
        if not qmask.any():
            continue
        eligible = qmask & ~labels  # never dot on known faults
        scores = np.where(eligible, surface, -1.0)
        ids = np.flatnonzero(eligible & (surface > 0))
        if not len(ids):
            continue
        order = np.lexsort((ids, -scores.ravel()[ids]))
        k = min(per_quad, len(ids))
        dots.ravel()[ids[order[:k]]] = True

    return dots


def check_registry_uniqueness(dots: np.ndarray, surface: np.ndarray,
                              footprint: np.ndarray) -> dict:
    """Compare against registry rasters that are available locally.

    Falls back gracefully when registry cache files are not restored.
    """
    registry_json = ROOT / "registry" / "registry.json"
    if not registry_json.exists():
        return {"error": "registry.json not found", "checked": 0}

    reg = json.loads(registry_json.read_text())
    entries = reg["entries"]

    # Collect local comparison cache NPY files
    available = []
    for entry in entries:
        cpath = entry.get("comparison_cache_path")
        if cpath:
            full = ROOT / cpath
            if full.exists():
                available.append((entry, full))

    if not available:
        return {
            "error": "no registry comparison caches restored locally",
            "checked": 0,
            "total_registry_entries": len(entries),
            "note": "Run scripts/fetch_repositories.py to restore registry caches, "
                    "then rerun this uniqueness check.",
        }

    max_rho = 0.0
    max_ov = 0.0
    max_ov_literal = 0.0
    drifted = False
    drifted_reason = None
    rows = []

    for entry, cpath in available:
        try:
            other_positions = np.load(cpath, mmap_mode="r", allow_pickle=False)
            other_dots = np.zeros(footprint.shape, dtype=bool)
            flat_ids = np.flatnonzero(footprint)
            other_dots.ravel()[flat_ids[other_positions.astype(np.int64)]] = True
        except Exception as e:
            rows.append({"file": entry.get("file", "?"), "error": str(e)})
            continue

        # Spearman on surface vs other dots (binary reference)
        from gems1.uniqueness import spearman_surface
        rho = abs(spearman_surface(surface, other_dots.astype(np.float32), footprint))

        # Directional overlap: candidate dots within 3px of registry dots
        from scipy.ndimage import distance_transform_edt
        d = distance_transform_edt(~other_dots)
        ov_frac = float((d[dots] <= 3.0).mean()) if dots.any() else 0.0
        n_other = int(other_dots.sum())
        other_frac_fp = n_other / max(int(footprint.sum()), 1)
        space = other_frac_fp >= 0.70

        max_rho = max(max_rho, rho)
        max_ov_literal = max(max_ov_literal, ov_frac)
        if not space:
            max_ov = max(max_ov, ov_frac)

        row = {
            "file": entry.get("file", "?"),
            "repo": entry.get("repo", "?"),
            "rho": rho,
            "overlap_frac": ov_frac,
            "n_other": n_other,
            "space_filling": space,
        }
        rows.append(row)

        if rho > 0.90:
            drifted = True
            drifted_reason = f"spearman {rho:.4f} > 0.90 vs {entry.get('file', '?')}"
        if (not space) and ov_frac > 0.70:
            drifted = True
            drifted_reason = drifted_reason or f"overlap {ov_frac:.4f} > 0.70 vs {entry.get('file', '?')}"

    return {
        "checked": len(available),
        "total_registry_entries": len(entries),
        "max_abs_spearman": max_rho,
        "max_overlap_non_spacefill": max_ov,
        "max_overlap_literal": max_ov_literal,
        "rho_threshold": 0.90,
        "overlap_threshold": 0.70,
        "drifted": drifted,
        "drifted_reason": drifted_reason,
        "unique": (not drifted) and max_rho <= 0.90 and max_ov <= 0.70,
        "top": sorted(rows, key=lambda r: -max(abs(r.get("rho", 0)), r.get("overlap_frac", 0)))[:12],
    }


def main() -> int:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    # ---- 1. Load grid and catalogue ---------------------------------------
    template_arr, footprint, meta = read_template(TEMPLATE_PATH)
    labels = read_labels(LABELS_PATH)
    print(f"Grid: {footprint.shape}, footprint={int(footprint.sum()):,}, "
          f"catalogue positives={int(labels.sum()):,}")

    # ---- 2. Build emission surface ----------------------------------------
    surface = build_surface(labels, footprint)
    print(f"Emission surface: max={surface.max():.4f}, nonzero px={int((surface > 0).sum()):,}")

    # ---- 3. Place dots ----------------------------------------------------
    dots = place_dots(surface, footprint, labels)
    n_dots = int(dots.sum())
    dots_on_cat = int((dots & labels).sum())
    print(f"Dots placed: {n_dots:,} (footprint share {n_dots / footprint.sum():.6f})")
    print(f"Dots on catalogue: {dots_on_cat} (must be 0)")

    # ---- 4. Write portal-safe GeoTIFF -------------------------------------
    pred = np.where(dots, np.float32(1.0), np.float32(0.0)).astype(np.float32)
    tif_path = DOWNLOADS / f"{NAME}.tif"
    write_geotiff(pred, tif_path, template_path=TEMPLATE_PATH, outside="zeros")
    print(f"Wrote {tif_path} ({tif_path.stat().st_size:,} bytes)")

    # ZIP twin
    zip_path = DOWNLOADS / f"{NAME}.zip"
    info = zipfile.ZipInfo(tif_path.name, date_time=(2026, 10, 2, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(info, tif_path.read_bytes(), compresslevel=9)
    print(f"Wrote {zip_path}")

    # ---- 5. Format validation --------------------------------------------
    receipt = check_variants(tif_path, TEMPLATE_PATH)
    fmt_ok = receipt["format_valid"]
    print(f"Format valid: {fmt_ok}")
    if not fmt_ok:
        print("HARD FORMAT FAILURES:", receipt["hard_failures"])
    val_path = DOWNLOADS / f"{NAME}.validator.json"
    val_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    # ---- 6. Registry uniqueness ------------------------------------------
    uniq = check_registry_uniqueness(dots, pred, footprint)
    print(f"Registry uniqueness: checked={uniq.get('checked', 0)}/{uniq.get('total_registry_entries', 0)}, "
          f"unique={uniq.get('unique', False)}, "
          f"max |rho|={uniq.get('max_abs_spearman', 0):.4f}, "
          f"max overlap={uniq.get('max_overlap_non_spacefill', 0):.4f}")
    if "error" in uniq:
        print(f"  Note: {uniq['error']}")
    uniq_path = DOWNLOADS / f"{NAME}.uniqueness.json"
    uniq_path.write_text(json.dumps(uniq, indent=2, allow_nan=False) + "\n")

    # ---- 7. HOLDOUT-DTI evaluation ----------------------------------------
    ctx = build_context(footprint, labels, collar_px=15)
    holdout = evaluate_mask(
        dots, ctx, b_visible_px=2.0, n_boot=1000, seed=20261026, name=NAME
    )
    dti = float(holdout["pooled_dti"])
    ci_lo = float(holdout["ci95"][0])
    ci_hi = float(holdout["ci95"][1])
    print(f"HOLDOUT-DTI: pooled={dti:.6f}, CI95=[{ci_lo:.6f}, {ci_hi:.6f}], "
          f"n_withheld={holdout['n_withheld_positives']:,}")
    ho_path = DOWNLOADS / f"{NAME}.holdout.json"
    ho_path.write_text(json.dumps(holdout, indent=2, allow_nan=False) + "\n")

    # Full-domain DTI reference
    full = dti_binary(dots, labels, valid=footprint, known=labels, alpha=ALPHA, beta=BETA)
    print(f"Full-domain DTI (catalogue known-masked): {full['dti']:.6f}")

    # ---- 8. Verdict -------------------------------------------------------
    lane_unique = bool(uniq.get("unique", False))
    fmt_pass = bool(fmt_ok)
    ci_positive = ci_lo > 0
    no_dots_on_cat = dots_on_cat == 0

    verdict = "promote" if (fmt_pass and ci_positive and no_dots_on_cat) else "negative"
    # Lane uniqueness is advisory when registry caches are absent
    if uniq.get("error"):
        verdict = "negative"  # cannot confirm uniqueness without registry check
        print("  Overriding to negative: registry uniqueness not confirmed locally")

    print(f"\n=== VERDICT: {verdict.upper()} ===")
    print(f"  Format pass: {fmt_pass}")
    print(f"  Lane unique: {lane_unique} (registry caches: {'available' if not uniq.get('error') else 'NOT available'})")
    print(f"  HOLDOUT-DTI CI strictly positive: {ci_positive} ({ci_lo:.6f} to {ci_hi:.6f})")
    print(f"  No dots on catalogue: {no_dots_on_cat}")

    # ---- 9. Submission name + note (<=140 chars) -------------------------
    note = (f"WBGGEMSDOE1 blind-fault-adjacency distance-decay dots, off-catalogue, "
            f"{n_dots:,} dots | HOLDOUT-DTI={dti:.4f} | research")
    if len(note) > 140:
        note = note[:137] + "..."
    print(f"  Name: {NAME}")
    print(f"  Note ({len(note)} chars): {note}")

    note_path = DOWNLOADS / f"{NAME}.note.txt"
    note_path.write_text(f"{NAME}\n{note}\n")

    # ---- 10. Run card -----------------------------------------------------
    run_card = {
        "schema": "gemsdoe1-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "Blind faults occur adjacent to -- not on -- mapped "
                      "catalogue traces.  A smooth distance-decayed emission "
                      "kernel peaking ~150 m from known faults targets blind "
                      "splays/stepovers better than GEMSDOE32 B2's hard >200 m "
                      "exclusion.",
        "mechanism": "Distance-to-catalogue Gaussian bump (peak 1.5 px, sigma "
                     "1.0 px) -> per-quadrant top-k dot placement -> binary "
                     "GeoTIFF, zeros outside footprint.",
        "named_non_fault_mimic": "Linear topography / DEM scarp edges unrelated "
                                 "to faults can produce similar distance-from-"
                                 "catalogue structure.",
        "holdout_dti": dti,
        "holdout_ci95": [ci_lo, ci_hi],
        "n_withheld_positives": int(holdout["n_withheld_positives"]),
        "evaluator_version": HOLDOUT_VERSION,
        "registry_unique": lane_unique,
        "max_abs_rank_correlation": uniq.get("max_abs_spearman"),
        "max_dot_overlap_3px": uniq.get("max_overlap_non_spacefill"),
        "raster_sha256": sha256_file(tif_path),
        "format_valid": fmt_pass,
        "values_in_0_1": True,
        "crs": "EPSG:32611",
        "shape": [3730, 3292],
        "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
        "submission_name": NAME,
        "note": note,
        "note_length": len(note),
        "verdict": verdict,
        "dots_on_catalogue": dots_on_cat,
        "n_dots": n_dots,
        "registry_entries_available": uniq.get("checked", 0),
        "registry_entries_total": uniq.get("total_registry_entries", 0),
    }
    card_path = DOWNLOADS / f"{NAME}.run-card.json"
    card_path.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")
    print(f"\nRun card: {card_path}")
    print(f"SHA-256: {run_card['raster_sha256']}")

    return 0 if verdict == "promote" else 1


if __name__ == "__main__":
    raise SystemExit(main())
