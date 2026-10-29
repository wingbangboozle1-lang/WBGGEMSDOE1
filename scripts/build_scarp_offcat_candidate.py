#!/usr/bin/env python3
"""SCARP-NMS-OFFCAT-36800 — fold-safe candidate builder (2026-10-29).

Hypothesis (one sentence): unmapped Quaternary fault scarps in the GeoDAWN
footprint leave short-wavelength (2 m-resolved) slope excess above the 30 m
regional slope, measured from the USGS 3DEP 1 m DEM tiles restored by
data/external/lidar_scarp_features_u8.tif (band ``ex_max``), and that excess
is locally maximal along scarp crests.

Method (no learned model, no fitted parameters beyond the fixed ones below):
  1. Decode ex_max from the uint8 quantisation (sqrt, xmax=1.5 m/m):
        q = 1 + round(254 * sqrt(clip(x/xmax)))  ->  x = xmax * ((q-1)/254)**2 ; q=0 -> no LiDAR.
  2. Score S = ex_max where LiDAR is valid AND inside the footprint.
  3. Non-maximum suppression with a 7x7 window; keep peaks in descending S order
     with a greedy 5-pixel (500 m) minimum separation (kernel-disjoint dots).
  4. Exclude any pixel within 3 px (300 m, = the scoring kernel radius) of the
     catalogue that is *visible to that computation*.
       - Fold replay: the visible catalogue of that fold only.
       - Final file:  the full mapped catalogue (the target is UNMAPPED faults).
  5. Budget N = 36,800 dots (matches the repo's 36,800-dot family). Fold replays
     receive N_f = round(N * region_pixels_f / footprint_pixels).

Fold-safe replay: for every hide-and-recover fold, the dots are regenerated
from that fold's VISIBLE catalogue only, restricted to the fold's region, and
scored against that fold's withheld truth with the shared evaluator
(vendor/gems57, evaluate_holdout.evaluate, pooled_summary with 20 km blocks).
A random control with the same per-fold budget and mask is scored the same way.

Limitations (see run card): LiDAR coverage is partial (3,892,964 of 12,279,160
cells); ex_max also responds to roads, channels, terrace risers, paleo-shorelines,
landslides and mines (source JSON caveats); the holdout is catalogue-based and
is NOT the organizer's private-test score.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import evaluate_holdout as E  # noqa: E402
from gems57 import holdout as H  # noqa: E402
from gems57.grid import load_grid, write_submission  # noqa: E402

LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"
LIDAR_SHA256 = "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568"
BRIDGE = ROOT / "data/bridge"
VARIANTS = {"exmax": "wbggemsdoe1-lidar-scarp-nms-offcat-36800-20261029-zeros",
            "exmax_x_coh100": "wbggemsdoe1-lidar-scarp-coh-nms-offcat-36800-20261029-zeros",
            "exmax_x_coh100_halo15": "wbggemsdoe1-lidar-scarp-coh-halo15-36800-20261029-zeros"}
# Halo exclusion radius per variant (px at 100 m). Experiment 3 tests the
# distance-to-catalogue hypothesis from the nine-site geometry audit.
HALO_PX = {"exmax": 3, "exmax_x_coh100": 3, "exmax_x_coh100_halo15": 15}  # 3 px = scoring kernel radius
NAME = VARIANTS.get(sys.argv[1] if len(sys.argv) > 1 else "exmax", VARIANTS["exmax"])
OUT_TIF = ROOT / "docs/downloads" / f"{NAME}.tif"
RUN_CARD = ROOT / "evidence/scarp_offcat" / f"run_card_{NAME}.json"
N_DOTS = 36800
NMS_WINDOW = 7
MIN_SEP_PX = 5
BUFFER_PX = 3
EX_MAX_XMAX = 1.5
EX_MAX_BAND = 0  # band index in lidar_scarp_features_u8.tif (ex_max)
DRAWS = 1000
EVAL_SEED = 520810


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_ex_max(q: np.ndarray) -> np.ndarray:
    t = (q.astype(np.float32) - 1.0) / 254.0
    x = EX_MAX_XMAX * t * t
    x[q == 0] = np.nan
    return x


def greedy_peaks(score: np.ndarray, allowed: np.ndarray, n: int) -> np.ndarray:
    """Local maxima (NMS) inside ``allowed``, taken in descending score with a
    minimum Chebyshev separation of MIN_SEP_PX; returns a bool dot mask."""
    s = np.where(allowed & np.isfinite(score), score, -np.inf)
    local = (s == ndi.maximum_filter(s, size=NMS_WINDOW, mode="constant", cval=-np.inf)) & np.isfinite(s)
    ys, xs = np.nonzero(local)
    order = np.argsort(-s[ys, xs], kind="stable")
    dots = np.zeros(s.shape, bool)
    taken = np.zeros(s.shape, bool)
    h, w = s.shape
    k = 0
    for idx in order:
        if k >= n:
            break
        y, x = int(ys[idx]), int(xs[idx])
        if taken[y, x]:
            continue
        dots[y, x] = True
        k += 1
        r = MIN_SEP_PX - 1
        taken[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)] = True
    return dots


def auc_rank(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC (no sklearn dependency)."""
    allv = np.concatenate([pos, neg])
    ranks = np.empty(allv.size, float)
    ranks[np.argsort(allv, kind="mergesort")] = np.arange(1, allv.size + 1)
    # average tied ranks
    _, inv, cnt = np.unique(allv, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    ranks = (sums / cnt)[inv]
    rp = ranks[: pos.size].sum()
    return float((rp - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))


def main() -> int:
    if sha256(LIDAR) != LIDAR_SHA256:
        raise SystemExit("LiDAR feature raster hash mismatch; refusing to run")
    variant = sys.argv[1] if len(sys.argv) > 1 else "exmax"
    global VARIANT
    VARIANT = variant
    if variant not in VARIANTS:
        raise SystemExit(f"unknown variant {variant}; choose from {sorted(VARIANTS)}")
    grid = load_grid(BRIDGE)
    fp = grid.footprint
    cat = grid.catalogue
    with rasterio.open(LIDAR) as src:
        q_ex = src.read(EX_MAX_BAND + 1)
        q_coh = src.read(10)  # coh100 band (index 9, linear 0..1)
    lidar_ok = (q_ex > 0) & fp
    S = decode_ex_max(q_ex)
    if variant.startswith("exmax_x_coh100"):
        coh = (q_coh.astype(np.float32) - 1.0) / 254.0
        coh[q_coh == 0] = np.nan
        S = S * coh
    S = np.where(lidar_ok, S, np.nan).astype(np.float32)
    # Fraction of cells with LiDAR inside the footprint (run-card coverage figure).
    coverage = float(lidar_ok.sum()) / float(fp.sum())

    # ---- fold-safe replay -------------------------------------------------
    folds, _quad = H.buffered_component_draw(grid, seed=71614, hide_frac=0.2,
                                             buffer_px=3, boundary_px=12)
    fp_count = float(fp.sum())
    terms_cand: np.ndarray | None = None
    terms_ctrl: np.ndarray | None = None
    fold_rows = []
    rng = np.random.default_rng(20)
    canary_pos, canary_neg = [], []
    for fold in folds:
        visible = np.asarray(fold["visible"], bool)
        region = np.asarray(fold["region"], bool) & fp
        known = np.asarray(fold.get("masked_known", visible), bool)
        truth = np.asarray(fold["truth"], bool)
        d_vis = ndi.distance_transform_edt(~visible)
        excl = d_vis <= HALO_PX[VARIANT]
        allowed = lidar_ok & region & ~excl
        n_f = int(round(N_DOTS * float(region.sum()) / fp_count))
        dots = greedy_peaks(S, allowed, n_f)
        pred = dots.astype(np.float64)
        # Control: uniform random cells with the same mask and budget.
        cand_idx = np.flatnonzero(allowed.ravel())
        ctrl = np.zeros(fp.shape, bool)
        pick = rng.choice(cand_idx, size=min(n_f, cand_idx.size), replace=False)
        ctrl.ravel()[pick] = True
        # Leakage canary: S alone, within this fold's scorable domain.
        active = lidar_ok & region & ~known
        pos_v = S[active & truth]
        neg_v = S[active & ~truth]
        if pos_v.size and neg_v.size:
            neg_s = rng.choice(neg_v, size=min(200_000, neg_v.size), replace=False)
            canary_pos.append(pos_v)
            canary_neg.append(neg_s)
        # Fold-level scoring with the shared evaluator (20 km aligned blocks).
        res_c, blk_c = E.evaluate(pred, fold, fp)
        res_r, blk_r = E.evaluate(ctrl.astype(np.float64), fold, fp)
        terms_cand = blk_c if terms_cand is None else terms_cand + blk_c
        terms_ctrl = blk_r if terms_ctrl is None else terms_ctrl + blk_r
        fold_rows.append({
            "fold": int(fold["fold"]), "budget": n_f, "dots_placed": int(dots.sum()),
            "region_px": int(region.sum()), "withheld_positive_px": int(res_c["n_truth"]),
            "candidate_dti_fold": round(float(res_c["dti"]), 6),
            "control_dti_fold": round(float(res_r["dti"]), 6),
        })

    pooled = E.pooled_summary({"candidate": terms_cand, "control_random_same_mask": terms_ctrl},
                              draws=DRAWS, seed=EVAL_SEED, candidate="candidate")
    cand = pooled["scores"]["candidate"]
    ctrl = pooled["scores"]["control_random_same_mask"]
    # Paired difference CI from the same block resampling (shared evaluator).
    diffs = pooled["paired_differences"]

    # Canary: AUC of S alone against withheld positives (fold-pooled).
    pos_all = np.concatenate(canary_pos) if canary_pos else np.array([])
    neg_all = np.concatenate(canary_neg) if canary_neg else np.array([])
    auc = auc_rank(pos_all, neg_all) if pos_all.size and neg_all.size else float("nan")

    # ---- final full-catalogue file ----------------------------------------
    excl_full = ndi.distance_transform_edt(~cat) <= HALO_PX[VARIANT]
    allowed_full = lidar_ok & ~excl_full
    final_dots = greedy_peaks(S, allowed_full, N_DOTS)
    values = np.zeros(fp.shape, np.float32)
    values[final_dots & fp] = 1.0
    OUT_TIF.parent.mkdir(parents=True, exist_ok=True)
    wr = write_submission(OUT_TIF, values, mode="zeros")

    card = {
        "schema": "gemsdoe1-run-card-v1",
        "date_utc": "2026-10-29",
        "name": NAME,
        "variant": sys.argv[1] if len(sys.argv) > 1 else "exmax",
        "hypothesis": "Unmapped Quaternary scarps leave 2 m-resolved slope excess above the 30 m regional slope in USGS 3DEP 1 m DEM; NMS peaks of that excess, excluding 300 m of the mapped catalogue, are off-catalogue fault candidates.",
        "mechanism": "Fault scarp crest: concentrated short-wavelength slope excess (ex_max, 2 m work grid) where regional slope is low; crest peaks survive NMS.",
        "named_non_fault_mimic": "Roads, canal/ditch banks, channel banks, terrace risers, paleo-shorelines (Lake Lahontan), landslide headscarps and mines (listed as caveats in data/external/lidar_scarp_features.json).",
        "inputs": {
            "lidar_raster": "data/external/lidar_scarp_features_u8.tif",
            "lidar_sha256": LIDAR_SHA256,
            "lidar_coverage_of_footprint": round(coverage, 6),
            "catalogue": "data/bridge/existing_faults.tif (identical to labels.tif, sha256 7ba308cc...)",
        },
        "parameters": {
            "dots": N_DOTS, "nms_window_px": NMS_WINDOW, "min_separation_px": MIN_SEP_PX,
            "catalogue_halo_exclusion_px": HALO_PX[variant], "ex_max_xmax": EX_MAX_XMAX, "ex_max_quantisation": "sqrt",
            "fold_generator": "gems57.holdout.buffered_component_draw(seed=71614, hide_frac=0.2, buffer_px=3, boundary_px=12)",
        },
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": E.VERSION,
            "withheld_positives": cand["withheld_positive_pixels"],
            "candidate_dti": round(cand["dti"], 6),
            "candidate_ci95": [round(x, 6) for x in cand["ci95"]],
            "control_random_same_mask_dti": round(ctrl["dti"], 6),
            "control_ci95": [round(x, 6) for x in ctrl["ci95"]],
            "paired_difference": diffs,
            "bootstrap": pooled["bootstrap"],
            "per_fold": fold_rows,
            "leakage_canary_auc_ex_max_alone": round(auc, 6),
            "leakage_canary_threshold": 0.90,
            "leakage_canary_pass": bool(auc <= 0.90),
            "caveat": "Catalogue hide-and-recover proxy, not the organizer's private test. Withheld faults are the catalogue, not new faults.",
        },
        "validator": {
            "shape": list(values.shape),
            "dtype": "float32",
            "finite_all": True,
            "min": float(values.min()), "max": float(values.max()),
            "dots": int(final_dots.sum()),
            "writer": wr,
        },
        "sha256": sha256(OUT_TIF),
        "estimated_leaderboard_score": "UNAVAILABLE",
        "verdict": "pending_uniqueness_audit",
    }
    RUN_CARD.parent.mkdir(parents=True, exist_ok=True)
    RUN_CARD.write_text(json.dumps(card, indent=2, default=float) + "\n")
    print(json.dumps({k: card[k] for k in ("sha256",)}, indent=1))
    print(json.dumps(card["holdout"], indent=1, default=float)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
