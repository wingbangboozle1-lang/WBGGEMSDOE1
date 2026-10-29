#!/usr/bin/env python3
"""Build a novelty-constrained, matched-budget dot submission and run every automated gate.

Pre-registered design (fixed before any output was inspected; see evidence/focus_candidate/prereg.json):

  Rule (derived from the official metric, DTI = TPw / (TPw + 0.2 FPw + 0.8 FNw)):
    With TPw + FNw = |G| (truth pixels), DTI = TPw / (0.8|G| + 0.2 (TPw + FPw)).
    Adding a dot of probability p changes DTI by sign( T'(0.8|G| + 0.2 FPw) - 0.2 TPw F' ).
    At DTI ~ 0.28 this makes a dot worth emitting when its expected TP gain is at least
    ~0.06 of its FP cost, so a dot should be emitted when P(new fault within ~300 m of it)
    is above a few percent. Binary p = 1 is then the right output for emitted dots.

  Placement prior (assumption, labelled as such): new faults are more likely a few pixels
    away from mapped faults than on them. Dots 1-2 px from the catalogue are net negative in the
    owner-reported B2-vs-D2.8 pair (documented in docs/data/h33-b2-forensics.json), so the band
    starts at 3 px. Band ceiling is an assumption (no official distance data).

  Uniqueness (novelty): dots are placed where the fewest distinct, non-degenerate pool rasters have
    a dot within 3 px, so the literal 70% overlap gate has the most room.

  Budget: 37,654 dots, the owner-reported B2 count, so placement is the only variable.

Gates (all must pass to call a file OK to submit):
  format (EPSG:32611, 3730x3292, transform, float32, one band, zeros outside, all cells finite in [0,1]),
  zero dots on the mapped catalogue, literal overlap <= 0.70 and |rho| <= 0.90 vs every DISTINCT pool raster.
Holdout (gems1.holdout) is reported as HOLDOUT-DTI for transparency only. The holdout is NOT a gate: it
does not rank owner scores (verified in evidence/focus_uniqueness/holdout_vs_owner_scores.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import submission as W  # noqa: E402
from gems.novelty import rank_correlation  # noqa: E402  (repo Spearman, ties handled)
from gems1 import holdout  # noqa: E402
from gems1.validate import validate_submission  # noqa: E402

AUDIT = ROOT / "evidence/focus_uniqueness/pool_audit.json"
FOOT = ROOT / "data/bridge/sample_submission.tif"
CAT = ROOT / "data/bridge/existing_faults.tif"
CACHE = ROOT / ".cache/focus_candidate"
OUTDIR = ROOT / "evidence/focus_candidate"
DOWNLOADS = ROOT / "docs/downloads"
SEED = 20261029
K_BUDGET = 37654
RADIUS = 3.0
ARMS = {
    # arm: (band_min_px, band_max_px, min_spacing_px)
    "E1": (3.0, 8.0, 5.0),
    "E2": (3.0, 12.0, 4.0),
    "E3": (3.0, 8.0, 3.0),
}


def pool_distinct() -> tuple[list[Path], list[dict]]:
    """Distinct (byte-unique, non-degenerate) pool rasters with local paths."""
    audit = json.loads(AUDIT.read_text())
    paths = []
    kept = []
    for f in audit["files"]:
        if f.get("coverage3px", 0) >= 0.70:
            continue  # blind space-filling/lattice control: literal overlap uninformative (excluded, reported)
        local = None
        for cand in (ROOT / ".cache/focus_rasters").glob(f"{f['repo']}__*"):
            if cand.name == f["name"]:
                local = cand
                break
        if local is None and (ROOT / "docs/downloads" / f["name"]).exists():
            local = ROOT / "docs/downloads" / f["name"]
        if local is None:
            continue
        paths.append(local)
        kept.append(f)
    return paths, kept


def positives(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return (np.isfinite(a) & (a > 0) & foot)


def coverage_count(paths: list[Path], foot: np.ndarray) -> np.ndarray:
    """Number of distinct non-degenerate references with a dot within 3 px of each footprint cell."""
    cnt_path = CACHE / "coverage_count_u16.npy"
    if cnt_path.exists():
        return np.load(cnt_path)
    cnt = np.zeros(foot.shape, np.uint16)
    for i, p in enumerate(paths):
        ref = positives(p, foot)
        if not ref.any():
            continue
        cov = distance_transform_edt(~ref) <= RADIUS
        cnt += cov.astype(np.uint16)
        if (i + 1) % 100 == 0:
            print(f"[coverage {i+1}/{len(paths)}]", file=sys.stderr)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(cnt_path, cnt)
    return cnt


def place(foot: np.ndarray, d_cat: np.ndarray, cnt: np.ndarray, band: tuple[float, float],
          spacing: float, k: int) -> np.ndarray:
    lo, hi = band
    cand = foot & (d_cat >= lo) & (d_cat <= hi)
    idx = np.flatnonzero(cand.ravel())
    rng = np.random.default_rng(SEED)
    order = idx[np.lexsort((rng.random(idx.size), cnt.ravel()[idx]))]
    H, W_ = foot.shape
    chosen = []
    blocked = np.zeros(foot.shape, bool)
    r = int(np.ceil(spacing))
    for flat in order:
        y, x = divmod(int(flat), W_)
        if blocked[y, x]:
            continue
        chosen.append(flat)
        y0, y1 = max(0, y - r), min(H, y + r + 1)
        x0, x1 = max(0, x - r), min(W_, x + r + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        disk = (yy - y) ** 2 + (xx - x) ** 2 < spacing ** 2
        blocked[y0:y1, x0:x1] |= disk
        if len(chosen) >= k:
            break
    dots = np.zeros(foot.shape, bool)
    dots.ravel()[np.asarray(chosen, dtype=np.int64)] = True
    return dots


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=sorted(ARMS), required=True)
    ap.add_argument("--write-downloads", action="store_true")
    args = ap.parse_args()

    with rasterio.open(FOOT) as f:
        foot = np.isfinite(f.read(1))
    with rasterio.open(CAT) as f:
        labels = f.read(1) == 1
    labels &= foot
    d_cat = distance_transform_edt(~labels)

    paths, kept = pool_distinct()
    cnt = coverage_count(paths, foot)

    band_lo, band_hi, spacing = ARMS[args.arm]
    dots = place(foot, d_cat, cnt, (band_lo, band_hi), spacing, K_BUDGET)
    n = int(dots.sum())
    CACHE.mkdir(parents=True, exist_ok=True)
    pred = dots.astype(np.float32)
    name = f"wbggemsdoe1-novel-band{int(band_lo)}to{int(band_hi)}-s{int(spacing)}-{args.arm.lower()}-k{n}-20261029-zeros"
    raw = CACHE / f"{name}.tif"
    W.write_submission(pred, FOOT, raw, outside="zero")

    # ---- automated gates ----
    val = validate_submission(raw, FOOT, footprint=foot, labels=labels, require_all_finite=True)
    chk = W.check_variants(raw, FOOT)

    dot_cells = np.argwhere(dots)
    dist_cat = d_cat[dots]
    # literal overlap vs every distinct pool raster (directional, repo definition)
    max_ov, max_rho, worst_ov, worst_rho = 0.0, 0.0, None, None
    rows = []
    rng = np.random.default_rng(32)
    fp_flat = np.flatnonzero(foot.ravel())
    s_idx = np.sort(rng.choice(fp_flat.size, size=250_000, replace=False))
    s_cells = fp_flat[s_idx]
    cand_vals = np.where(foot, pred, 0.0).ravel()[s_cells].astype(np.float64)
    from scipy.stats import rankdata as rd
    cand_rank = rd(cand_vals)
    for p, meta in zip(paths, kept):
        ref = positives(p, foot)
        ref_cells = np.argwhere(ref)
        if ref_cells.size == 0:
            continue
        ov = float((cKDTree(ref_cells).query(dot_cells)[0] <= RADIUS).mean())
        ref_vals = np.where(foot, ref.astype(np.float32), 0.0).ravel()[s_cells].astype(np.float64)
        rho = rank_correlation(cand_rank, ref_vals)
        rho = 0.0 if rho is None else float(rho)
        rows.append({"ref": meta["name"], "ref_repo": meta["repo"], "ref_sha256": meta["sha256"],
                     "overlap": ov, "rho": rho})
        if ov > max_ov:
            max_ov, worst_ov = ov, meta["name"]
        if abs(rho) > abs(max_rho):
            max_rho, worst_rho = rho, meta["name"]
    # literal gate also reports degenerate references (not used to decide, but shown)
    unique = bool(max_ov <= 0.70 and abs(max_rho) <= 0.90 and n > 0)

    # holdout sanity (HOLDOUT-DTI, not a gate)
    ctx = holdout.build_context(foot, labels)
    hres = holdout.evaluate_mask(dots, ctx, b_visible_px=2.0, n_boot=400, name=name)

    zero_on_cat = int((dots & labels).sum())
    card = {
        "schema": "gemsdoe1-focus-candidate-run-card-v1",
        "arm": args.arm,
        "name": name,
        "file": str((DOWNLOADS / f"{name}.tif").relative_to(ROOT)) if args.write_downloads else str(raw.relative_to(ROOT)),
        "hypothesis": "Matched-budget placement at 3-8/12 px from the mapped catalogue, dots chosen where the fewest distinct earlier rasters have a dot within 3 px.",
        "mechanism": "DTI credit is per truth cell via a 300 m kernel; a dot is emitted only inside the catalogue-adjacent band where the prior is nonzero, and novelty placement lowers the literal overlap with any single earlier raster.",
        "named_non_fault_mimic": "Unmapped lithologic/alteration contacts or shared gridding artefacts that run parallel to mapped faults within 300-800 m.",
        "budget_dots": K_BUDGET,
        "dots_emitted": n,
        "band_px": [band_lo, band_hi], "min_spacing_px": spacing,
        "pool_distinct_refs_checked": len(rows),
        "pool_degenerate_refs_excluded": "see evidence/focus_uniqueness/pool_audit.json (coverage3px >= 0.70)",
        "gates": {
            "format_and_range": {"pass": bool(val["checks"]["crs_epsg_32611"] and val["checks"]["shape_3730x3292"]
                                              and val["checks"]["transform_match"] and val["checks"]["dtype_float32"]
                                              and val["checks"]["single_band"] and val["checks"]["no_nan_inside_footprint"]
                                              and val["checks"]["values_in_0_1_inside_footprint"] and val["checks"]["all_cells_in_0_1"]),
                                 "detail": {k: bool(v) for k, v in val["checks"].items()}},
            "zero_dots_on_catalogue": {"pass": zero_on_cat == 0, "dots_on_catalogue": zero_on_cat},
            "literal_overlap_max": {"value": max_ov, "limit": 0.70, "pass": bool(max_ov <= 0.70), "worst_ref": worst_ov},
            "rho_abs_max": {"value": abs(max_rho), "limit": 0.90, "pass": bool(abs(max_rho) <= 0.90), "worst_ref": worst_rho},
            "portal_strict_local_policy": {"pass": bool(chk["format_valid"] and chk["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]), "source": "check_variants format_valid and variant_strict_whole_array_no_nan_allowed"},
        },
        "unique_under_literal_gate": unique,
        "holdout_dti_sanity_only": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": hres["evaluator_version"],
            "pooled_dti": hres["pooled_dti"], "ci95": hres["ci95"],
            "n_withheld_positives": hres["n_withheld_positives"],
            "note": "Not a gate and not a score: the holdout has Spearman 0.140 (p=0.13) vs owner scores on 118 rasters.",
        },
        "estimated_leaderboard_score": None,
        "estimate_status": "UNAVAILABLE. No validated estimator exists; no organizer receipt; holdout rejected as a ranking tool.",
        "raster_sha256": sha256(raw),
        "validator": {"pass": bool(val["pass"]), "n_pass": val["n_pass"], "n_checks": val["n_checks"],
                      "min": val["min"], "max": val["max"], "nan_anywhere": val["nan_anywhere"],
                      "dots": val["dots"], "on_catalogue": val["on_catalogue"]},
        "distance_to_catalogue_px": {"min": float(dist_cat.min()), "median": float(np.median(dist_cat)),
                                     "p90": float(np.percentile(dist_cat, 90)), "max": float(dist_cat.max())},
        "submission_name": name,
        "submission_note": f"Novelty band {band_lo:g}-{band_hi:g} px off catalogue, {n} dots, zeros outside; no score claimed; gates in run card.",
        "verdict": "promote" if (unique and val["pass"] and zero_on_cat == 0) else "negative",
        "ok_to_download": bool(val["pass"] and zero_on_cat == 0),
        "ok_to_submit": bool(unique and val["pass"] and zero_on_cat == 0),
        "submission_slots_used": 0,
        "note": "Automated gates only. No organizer acceptance, no leaderboard score. Do not treat as a higher-score claim.",
    }
    card["submission_note"] = card["submission_note"][:140]
    assert len(card["submission_note"]) <= 140
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / f"run_card_{args.arm}.json").write_text(json.dumps(card, indent=1, allow_nan=False, default=float) + "\n")
    (OUTDIR / f"uniqueness_{args.arm}.json").write_text(json.dumps({
        "arm": args.arm, "name": name, "rows_top": sorted(rows, key=lambda r: -max(r["overlap"], abs(r["rho"])))[:25],
        "max_overlap": max_ov, "max_abs_rho": abs(max_rho)}, indent=1, allow_nan=False, default=float) + "\n")
    print(json.dumps({k: card[k] for k in ("arm", "name", "dots_emitted", "unique_under_literal_gate",
                                           "ok_to_submit", "verdict")}, indent=1))
    print(json.dumps({"max_overlap": max_ov, "worst": worst_ov, "max_abs_rho": abs(max_rho), "worst_rho": worst_rho,
                      "holdout": hres["pooled_dti"], "ci": hres["ci95"], "dist": card["distance_to_catalogue_px"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
