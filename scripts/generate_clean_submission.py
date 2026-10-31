#!/usr/bin/env python3
"""Generate a *clean*, unique, portal-valid GeoTIFF submission for the DOE GEMS Prize.

Geological hypothesis (blind-fault adjacency with distance-decayed emission,
leakage-free holdout):

  Known USGS/INGENIOUS catalogue faults are already mapped; the leaderboard
  rewards newly discovered faults.  Blind faults are most likely to occur
  adjacent to -- but not on -- mapped traces (splays, stepovers, blind
  extensions).  GEMSDOE32's B2 (reported 0.2778, USER-REPORTED) uses a hard
  catalogue exclusion (dots > 200 m from the catalogue).  This script replaces
  that hard cut with a smooth, distance-decayed emission kernel whose
  probability peaks at an intermediate distance (~150 m) from *visible* faults,
  then decays toward both the catalogue and the far background.

  CRITICAL leakage fix vs the previous archived lane:
  every fold's dots are placed using *that fold's visible faults only* (the
  withheld faults of that fold never influence its dots).  The final raster is
  scored with ``pred_by_fold`` so catalogue-derived candidates are never scored
  with dots generated from withheld faults.  Distance-to-visible is the only
  catalogue-derived field, and its leakage canary AUC is reported.

Outputs:
    docs/downloads/<name>.tif            portal-safe float32 GeoTIFF (zeros outside)
    docs/downloads/<name>.zip             one-TIFF ZIP
    docs/downloads/<name>.validator.json  format validation receipt
    docs/downloads/<name>.holdout.json    clean HOLDOUT-DTI receipt (pred_by_fold)
    docs/downloads/<name>.canary.json     leakage canary receipt
    docs/downloads/<name>.note.txt        submission name + <=140 char note
    docs/downloads/<name>.run-card.json   complete JSON run card

All numbers are labelled HOLDOUT-DTI / MODEL-ESTIMATE.  No organizer score is
claimed.  A projection is never written as a score.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems1.grid import read_template, read_labels, write_geotiff  # noqa: E402
from gems1.holdout import (
    build_context,
    evaluate_mask,
    EVALUATOR_VERSION as HOLDOUT_VERSION,
)  # noqa: E402
from gems.submission import check_variants  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DOWNLOADS = ROOT / "docs" / "downloads"
BRIDGE = ROOT / "data" / "bridge"
TEMPLATE_PATH = BRIDGE / "sample_submission.tif"
LABELS_PATH = BRIDGE / "existing_faults.tif"

# Emission kernel: Gaussian in distance to VISIBLE faults, peak at d_peak px.
# 100 m resolution -> 1 px = 100 m.  Peak ~1.5 px = 150 m targets the
# blind-fault adjacency zone; sigma ~ 1.0 px = 100 m decay width.
D_PEAK_PX = 1.5
D_SIGMA_PX = 1.0
B_VISIBLE_PX = 2.0  # holdout gate: dots must be > 2 px from visible faults

# Emission budget: 2.5% of footprint pixels total, split across 4 folds.
BUDGET_FRAC = 0.025

STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
FAMILY = "WBGGEMSDOE1"
HYPOTHESIS = "blind-fault-adjacency-distance-decay-clean-perfold"
NAME = f"{FAMILY}-{HYPOTHESIS}-{STAMP}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_surface(d_vis: np.ndarray, footprint: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Smooth distance-decayed emission surface from VISIBLE faults only.

    Zero on/very near known faults (already mapped), rising to a peak at an
    intermediate blind-fault distance, then decaying toward background.
    """
    z = (d_vis - D_PEAK_PX) / D_SIGMA_PX
    bump = np.exp(-0.5 * z * z)
    bump = np.where(d_vis <= 0.5, 0.0, bump)  # hard zero on catalogue pixels
    bump = np.where(~footprint, 0.0, bump)
    mx = float(bump.max())
    if mx > 0:
        bump = bump / mx
    return bump.astype(np.float32)


def place_dots_in_region(
    surface: np.ndarray,
    eligible: np.ndarray,
    k: int,
) -> np.ndarray:
    """Top-k dot placement by emission score within an eligible boolean region."""
    dots = np.zeros(eligible.shape, dtype=bool)
    ids = np.flatnonzero(eligible & (surface > 0))
    if not len(ids) or k <= 0:
        return dots
    scores = surface.ravel()[ids]
    order = np.argsort(-scores, kind="mergesort")
    take = min(k, len(ids))
    dots.ravel()[ids[order[:take]]] = True
    return dots


def check_leakage_canary(ctx, sample_neg=80_000, seed=32) -> dict:
    """AUC of distance-to-visible as a ranker of withheld positives.

    Must be <= 0.90 else the visible-catalogue field leaks withheld-fault
    location information.  Distance-to-FULL-catalogue is expected to leak and is
    NOT used as a placement feature; it is reported for contrast only.
    """
    rng = np.random.default_rng(seed)
    hidden = np.zeros(ctx.foot.shape, bool)
    active = np.zeros(ctx.foot.shape, bool)
    for f in ctx.folds:
        hidden |= f.hidden & f.active
        active |= f.active
    y_pos = hidden
    bg = active & ~y_pos
    py, px = np.nonzero(y_pos)
    ny, nx = np.nonzero(bg)
    if ny.size > sample_neg:
        pick = rng.choice(ny.size, size=sample_neg, replace=False)
        ny, nx = ny[pick], nx[pick]

    def auc(scores, y):
        s = np.asarray(scores, dtype=np.float64).ravel()
        yy = np.asarray(y, dtype=bool).ravel()
        n_pos = int(yy.sum())
        n_neg = int((~yy).sum())
        if n_pos == 0 or n_neg == 0:
            return float("nan")
        order = np.argsort(s, kind="mergesort")
        ranks = np.empty(s.size, dtype=np.float64)
        ranks[order] = np.arange(1, s.size + 1, dtype=np.float64)
        sum_pos = float(ranks[yy].sum())
        return (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)

    rows = {}
    leak = []
    fields = {
        "distance_to_visible_catalogue": -ctx.folds[0].d_visible,  # higher = nearer visible
    }
    # d_visible differs per fold; use a composite "nearest visible fault" field
    d_vis_min = np.full(ctx.foot.shape, np.inf, dtype=np.float64)
    for f in ctx.folds:
        d_vis_min = np.minimum(d_vis_min, f.d_visible)
    fields = {"nearest_visible_fault_distance": -d_vis_min}
    for name, field in fields.items():
        sp = field[py, px]
        sn = field[ny, nx]
        scores = np.concatenate([sp, sn])
        y = np.concatenate([np.ones(sp.size, bool), np.zeros(sn.size, bool)])
        a = auc(scores, y)
        rows[name] = float(a) if np.isfinite(a) else None
        if np.isfinite(a) and a > 0.90:
            leak.append(name)
    return {
        "n_pos": int(y_pos.sum()),
        "n_neg_sampled": int(ny.size),
        "auc": rows,
        "leaking_auc_gt_0.90": leak,
        "pass": len(leak) == 0,
    }


def main() -> int:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    # ---- 1. Load grid and catalogue ---------------------------------------
    template_arr, footprint, meta = read_template(TEMPLATE_PATH)
    labels = read_labels(LABELS_PATH)
    print(f"Grid: {footprint.shape}, footprint={int(footprint.sum()):,}, "
          f"catalogue positives={int(labels.sum()):,}")

    # ---- 2. Holdout context (visible/hidden fault segments) ---------------
    ctx = build_context(footprint, labels, collar_px=15)
    print(f"Folds: {[f.name for f in ctx.folds]}, hidden px per fold: "
          f"{[f.n_hidden for f in ctx.folds]}")

    # ---- 3. Per-fold dot placement (visible faults only) ------------------
    all_dots = np.zeros(footprint.shape, dtype=bool)
    pred_by_fold = {}
    total_budget = int(round(BUDGET_FRAC * int(footprint.sum())))
    per_fold = max(1, total_budget // 4)

    for f in ctx.folds:
        # Emission from THIS fold's visible faults only.
        surface = build_surface(f.d_visible, footprint, labels)
        # Eligible: this fold's active region, not on any catalogue pixel,
        # beyond the visible-collar gate, never on a withheld fault pixel.
        eligible = (
            f.active
            & ~labels                      # no dots on any catalogue fault
            & (f.d_visible > B_VISIBLE_PX)  # holdout gate
        )
        dots_f = place_dots_in_region(surface, eligible, per_fold)
        # Constribute dots only where this fold is allowed to score them.
        dots_f &= f.active
        all_dots |= dots_f
        pred_by_fold[f.index] = dots_f
        n_cat = int((dots_f & labels).sum())
        print(f"  {f.name}: dots={int(dots_f.sum()):,}, on_catalogue={n_cat}")

    dots = all_dots
    n_dots = int(dots.sum())
    dots_on_cat = int((dots & labels).sum())
    print(f"Total dots placed: {n_dots:,} (footprint share {n_dots / footprint.sum():.6f})")
    print(f"Dots on catalogue: {dots_on_cat} (must be 0)")

    # ---- 4. Write portal-safe GeoTIFF -------------------------------------
    pred = np.where(dots, np.float32(1.0), np.float32(0.0)).astype(np.float32)
    tif_path = DOWNLOADS / f"{NAME}.tif"
    write_geotiff(pred, tif_path, template_path=TEMPLATE_PATH, outside="zeros")
    print(f"Wrote {tif_path} ({tif_path.stat().st_size:,} bytes)")

    zip_path = DOWNLOADS / f"{NAME}.zip"
    info = zipfile.ZipInfo(tif_path.name, date_time=(2026, 10, 2, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(info, tif_path.read_bytes(), compresslevel=9)
    print(f"Wrote {zip_path}")

    # ---- 5. Format validation ---------------------------------------------
    receipt = check_variants(tif_path, TEMPLATE_PATH)
    fmt_ok = receipt["format_valid"]
    print(f"Format valid: {fmt_ok}")
    if not fmt_ok:
        print("HARD FORMAT FAILURES:", receipt["hard_failures"])
    val_path = DOWNLOADS / f"{NAME}.validator.json"
    val_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    # ---- 6. Leakage canary ------------------------------------------------
    canary = check_leakage_canary(ctx)
    print(f"Leakage canary: pass={canary['pass']}, auc={canary['auc']}, "
          f"leaking={canary['leaking_auc_gt_0.90']}")
    canary_path = DOWNLOADS / f"{NAME}.canary.json"
    canary_path.write_text(json.dumps(canary, indent=2, allow_nan=False) + "\n")

    # ---- 7. Clean HOLDOUT-DTI (pred_by_fold, no leakage) ------------------
    holdout = evaluate_mask(
        np.zeros(footprint.shape, bool),  # ignored when pred_by_fold given
        ctx,
        b_visible_px=B_VISIBLE_PX,
        n_boot=1000,
        seed=20261026,
        name=NAME,
        pred_by_fold=pred_by_fold,
    )
    dti = float(holdout["pooled_dti"])
    ci_lo = float(holdout["ci95"][0])
    ci_hi = float(holdout["ci95"][1])
    print(f"Clean HOLDOUT-DTI: pooled={dti:.6f}, CI95=[{ci_lo:.6f}, {ci_hi:.6f}], "
          f"n_withheld={holdout['n_withheld_positives']:,}")
    ho_path = DOWNLOADS / f"{NAME}.holdout.json"
    ho_path.write_text(json.dumps(holdout, indent=2, allow_nan=False) + "\n")

    # ---- 8. Registry uniqueness (caches usually absent locally) -----------
    uniq = {"checked": 0, "total_registry_entries": 0, "error": "not checked locally",
            "note": "registry comparison caches not restored in this sandbox;"}
    uniq_path = DOWNLOADS / f"{NAME}.uniqueness.json"
    uniq_path.write_text(json.dumps(uniq, indent=2, allow_nan=False) + "\n")

    # ---- 9. Verdict -------------------------------------------------------
    fmt_pass = bool(fmt_ok)
    ci_positive = ci_lo > 0
    no_dots_on_cat = dots_on_cat == 0
    canary_pass = bool(canary["pass"])

    # Clean-lane verdict: format OK + clean holdout CI positive + no catalogue
    # dots + no leakage.  Registry uniqueness cannot be confirmed without
    # restored caches, so we do NOT claim full uniqueness here.
    verdict = "promote" if (fmt_pass and ci_positive and no_dots_on_cat and canary_pass) else "negative"
    if uniq.get("error"):
        verdict = "negative"  # cannot confirm uniqueness without registry check
        print("  Overriding to negative: registry uniqueness not confirmed locally")

    print(f"\n=== VERDICT: {verdict.upper()} ===")
    print(f"  Format pass: {fmt_pass}")
    print(f"  Clean HOLDOUT-DTI CI strictly positive: {ci_positive} ({ci_lo:.6f} to {ci_hi:.6f})")
    print(f"  No dots on catalogue: {no_dots_on_cat}")
    print(f"  Leakage canary pass: {canary_pass}")

    # ---- 10. Submission name + note (<=140 chars) -------------------------
    note = (f"WBGGEMSDOE1 clean blind-fault-adjacency per-fold dots, off-catalogue, "
            f"{n_dots:,} dots | clean HOLDOUT-DTI={dti:.4f} | research")
    if len(note) > 140:
        note = note[:137] + "..."
    print(f"  Name: {NAME}")
    print(f"  Note ({len(note)} chars): {note}")

    note_path = DOWNLOADS / f"{NAME}.note.txt"
    note_path.write_text(f"{NAME}\n{note}\n")

    # ---- 11. Run card -----------------------------------------------------
    run_card = {
        "schema": "gemsdoe1-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": ("Blind faults occur adjacent to -- not on -- mapped "
                       "catalogue traces.  A smooth distance-decayed emission "
                       "kernel peaking ~150 m from VISIBLE faults targets blind "
                       "splays/stepovers; dots placed per-fold from visible "
                       "faults only (no leakage), scored with pred_by_fold."),
        "mechanism": ("Distance-to-visible-catalogue Gaussian bump (peak 1.5 px, "
                      "sigma 1.0 px) -> per-fold top-k dot placement in active "
                      "regions -> binary GeoTIFF, zeros outside footprint."),
        "named_non_fault_mimic": ("Linear topography / DEM scarp edges unrelated "
                                  "to faults can produce similar distance-from-"
                                  "catalogue structure."),
        "holdout_dti": dti,
        "holdout_ci95": [ci_lo, ci_hi],
        "n_withheld_positives": int(holdout["n_withheld_positives"]),
        "evaluator_version": HOLDOUT_VERSION,
        "leakage_canary": canary,
        "registry_unique": False,
        "registry_entries_available": uniq.get("checked", 0),
        "registry_entries_total": uniq.get("total_registry_entries", 0),
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
    }
    card_path = DOWNLOADS / f"{NAME}.run-card.json"
    card_path.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")
    print(f"Run card: {card_path}")
    print(f"SHA-256: {run_card['raster_sha256']}")

    return 0 if verdict == "promote" else 1


if __name__ == "__main__":
    raise SystemExit(main())
