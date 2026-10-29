#!/usr/bin/env python3
"""Unique-candidate lane: three fixed arms, one shared emitter, one shared evaluator.

Protocol (PROMPT.md, parallel-run rules)
---------------------------------------
* REUSE   : holdout folds from ``gems57.holdout.build_holdout``; scoring with
            ``gems57.evaluate_holdout.evaluate`` / ``pooled_summary`` (pooled DTI,
            alpha 0.2, beta 0.8, 300 m triangular kernel); emission with the shared
            ``gems57.emit.greedy_allocate`` (exact marginal-credit rule).
* VISIBLE : every catalogue-derived probability uses the *visible* catalogue of the
            fold only (``ctx.visible(key)``); withheld segments never enter ``p``.
* SELECT  : each arm's free parameter is chosen on holdout draw 20 and reported on
            draw 21 only (no tuning on the reporting draw).
* NULL    : a matched-budget uniform-random emission inside the same allowed cells.
* CANARY  : AUC of each arm's visible-only probability field against withheld truth
            (AUC > 0.90 means leakage until proven otherwise).
* LABEL   : all holdout numbers are HOLDOUT-DTI (evaluator version, withheld positives,
            95% CI). ORGANIZER-CONFIRMED is never produced here.

Usage
-----
    python scripts/unique_candidate_lane.py                 # holdout experiments only
    python scripts/unique_candidate_lane.py --emit-final ARM PARAM   # full-catalogue emission
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import holdout as H  # noqa: E402
from gems57.emit import greedy_allocate  # noqa: E402
from gems57.evaluate_holdout import evaluate, pooled_summary, VERSION  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.metric import PIXEL_M  # noqa: E402

EVIDENCE = ROOT / "evidence/unique_candidate_lane.json"
K_STAR_FINAL = 12395          # calibrated hidden-truth cell count (owner-reported calibration, see evidence/wbg6_null_calibration.json)
PX = PIXEL_M                  # metres per pixel (100)


def dist_to(mask: np.ndarray) -> np.ndarray:
    """Euclidean distance (pixels) to the nearest True cell of ``mask``."""
    if not mask.any():
        return np.full(mask.shape, 1e6)
    return ndi.distance_transform_edt(~mask).astype(np.float64)


def field_decay(vis: np.ndarray, footprint: np.ndarray, lam_m: float) -> np.ndarray:
    """Arm A: isotropic exponential decay from the visible catalogue, lambda in metres."""
    d = dist_to(vis)
    return np.exp(-d * PX / lam_m) * footprint


def field_ring(vis: np.ndarray, footprint: np.ndarray, mu_m: float, sigma_m: float = 750.0) -> np.ndarray:
    """Arm B: Gaussian ring at a fixed lateral offset from the visible catalogue (fault-spacing hypothesis)."""
    d = dist_to(vis) * PX
    return np.exp(-0.5 * ((d - mu_m) / sigma_m) ** 2) * footprint


def field_tip_gap(vis: np.ndarray, footprint: np.ndarray, lam_m: float) -> np.ndarray:
    """Arm C: decay from visible-catalogue *endpoints* only (fault tips), not the whole trace.

    An endpoint is a visible catalogue cell with exactly one 8-connected visible neighbour.
    """
    nb = ndi.convolve(vis.astype(np.int16), np.ones((3, 3), np.int16), mode="constant") - vis.astype(np.int16)
    ends = vis & (nb == 1)
    if not ends.any():
        return np.zeros(vis.shape, np.float64)
    d = dist_to(ends)
    return np.exp(-d * PX / lam_m) * footprint


ARMS = {
    "A_decay": (field_decay, [2000.0, 4000.0]),
    "B_ring": (field_ring, [1500.0, 3000.0]),
    "C_tipgap": (field_tip_gap, [2000.0]),
}
# Budget: the shared primary instrument is withholding mode "all" (8 cells); the
# conservative "detached" mode is not run in this lane (time budget; see caveats).
HOLDOUT_MODE = "all"   # overridable with --mode detached


def scale_to_budget(p: np.ndarray, allowed: np.ndarray, K: float) -> np.ndarray:
    """Scale a non-negative field so that sum(p over allowed) = K, clipped to [0,1]."""
    s = float(p[allowed].sum())
    if s <= 0:
        return np.zeros_like(p, np.float32)
    q = np.clip(p * (K / s), 0.0, 1.0).astype(np.float32)
    return q


def cell_domain(grid, quad, fold_index: int) -> np.ndarray:
    q = quad == fold_index
    return ndi.binary_erosion(q, iterations=H.DOMAIN_ERODE) & grid.footprint


def fold_index_of(key: str) -> int:
    return H.FOLD_NAMES.index(key.split("_fold")[1].split("_")[0])


def emit_cell(field_fn, param, vis_full, fp_full, domain_full, K_cell, sl):
    """Fields are built on the FULL grid (catalogue distances must see all visible traces);
    only the greedy step runs on the padded cell bbox ``sl`` (6 px padding >= kernel radius, exact)."""
    allowed_full = domain_full & ~vis_full
    p_full = field_fn(vis_full, fp_full, param) * domain_full
    p_full = scale_to_budget(p_full, allowed_full, K_cell)
    p = p_full[sl]
    allowed = allowed_full[sl]
    alloc = greedy_allocate(p, allowed, K_cell)
    return alloc.emitted & allowed, p


def run(mode: str = HOLDOUT_MODE, only: tuple[str, ...] | None = None) -> dict:
    grid = load_grid(ROOT / "data")
    ctx = H.build_holdout(grid)
    results = {"schema": "unique-candidate-lane-v1", "evaluator_version": VERSION, "withholding_mode": mode,
               "evidence_class": "HOLDOUT-DTI", "k_rule": "K_cell = 0.25 * visible catalogue in domain (non-leaky)",
               "selection_draw": 20, "report_draw": 21, "arms": {}}
    fp = grid.footprint
    quad = ctx.quad
    per_arm_terms = {}
    for arm, (fn, params) in ARMS.items():
        if only and arm not in only:
            continue
        for param in params:
            name = f"{arm}@{int(param)}m"
            terms_by_draw = {20: None, 21: None}
            null_by_draw = {20: None, 21: None}
            canary = []
            cell_rows = []
            for cell in ctx.cells_of(mode):
                draw = int(cell.key.split("_")[0].replace("draw", ""))
                fidx = fold_index_of(cell.key)
                sl = cell.bbox
                oy, ox = sl[0].start, sl[1].start
                gshape = fp.shape
                # full-grid masks, cropped to the cell bbox for speed (6 px padding keeps the kernel exact)
                domain_full = cell_domain(grid, quad, fidx)
                vis_full = ctx.visible(cell.key)
                domain = domain_full[sl]
                vis = vis_full[sl]
                footprint_c = fp[sl]
                hidden_c = (ctx.hidden_by_cell[cell.key] & fp)[sl]
                vis_in = vis_full & domain_full
                K_cell = 0.25 * float(vis_in.sum())
                emitted, p = emit_cell(fn, param, vis_full, fp, domain_full, K_cell, sl)
                fold = dict(region=domain, visible=vis, masked_known=vis, truth=hidden_c)
                res, terms = evaluate(emitted.astype(np.float64), fold, footprint_c, block_side=200,
                                      origin=(oy, ox), global_shape=gshape)
                terms_by_draw[draw] = terms if terms_by_draw[draw] is None else terms_by_draw[draw] + terms
                # matched-budget uniform null inside the same allowed cells
                rng = np.random.default_rng(1000 * draw + 7 * fidx + int(param))
                allowed = domain & ~vis
                cells_idx = np.flatnonzero(allowed.ravel())
                n = int(emitted.sum())
                pick = rng.choice(cells_idx, size=min(n, cells_idx.size), replace=False)
                nullm = np.zeros(allowed.size, bool)
                nullm[pick] = True
                nullm = nullm.reshape(allowed.shape)
                nres, nterms = evaluate(nullm.astype(np.float64), fold, footprint_c, block_side=200,
                                        origin=(oy, ox), global_shape=gshape)
                null_by_draw[draw] = nterms if null_by_draw[draw] is None else null_by_draw[draw] + nterms
                # leakage canary on the visible-only field (domain pixels not visible)
                act = domain & ~vis
                y = hidden_c[act]
                sc = p[act]
                if y.any() and (~y).any():
                    canary.append(float(roc_auc_score(y.astype(int), sc)))
                cell_rows.append(dict(cell=cell.key, dti=res["dti"], n_emitted=n,
                                      withheld_positive_pixels=int(res["n_truth"]),
                                      K_cell=K_cell, null_dti=nres["dti"]))
            # pooled summaries per draw (reported draw is 21; draw 20 selects the parameter)
            summ = {}
            for draw in (20, 21):
                summ[draw] = pooled_summary({name: terms_by_draw[draw], "null_matched_budget": null_by_draw[draw]},
                                            candidate=name, draws=1000, seed=520810 + draw)
            results["arms"][name] = dict(
                arm=arm, param_m=param,
                draw20=summ[20]["scores"][name], draw21=summ[21]["scores"][name],
                draw21_null=summ[21]["scores"]["null_matched_budget"],
                draw21_paired_vs_null=summ[21]["paired_differences"]["null_matched_budget"],
                draw20_paired_vs_null=summ[20]["paired_differences"]["null_matched_budget"],
                canary_auc_max=max(canary) if canary else None,
                canary_auc_per_cell=canary,
                cells=cell_rows,
            )
            per_arm_terms[name] = (terms_by_draw[20], terms_by_draw[21])
            print(f"{name}: draw20 DTI={summ[20]['scores'][name]['dti']:.4f} "
                  f"draw21 DTI={summ[21]['scores'][name]['dti']:.4f} "
                  f"null21={summ[21]['scores']['null_matched_budget']['dti']:.4f} "
                  f"AUCmax={max(canary) if canary else float('nan'):.3f}", flush=True)
    # select, per arm, the parameter with the best draw-20 DTI; report draw 21 for the winners
    chosen = {}
    for arm in ARMS:
        if only and arm not in only:
            continue
        cands = [k for k in results["arms"] if results["arms"][k]["arm"] == arm]
        best = max(cands, key=lambda k: results["arms"][k]["draw20"]["dti"])
        chosen[arm] = best
    results["selected_on_draw20"] = chosen
    results["selected_reported_draw21"] = {a: results["arms"][k]["draw21"] for a, k in chosen.items()}
    results["caveats"] = [
        "HOLDOUT-DTI on owner-mirror catalogue proxies; not the organizer's hidden test set.",
        "Holdout DTI is not an organizer score and was not shown to rank registry submissions (see evidence/holdout_proxy_portfolio.json).",
        "Greedy emission uses K_cell from visible catalogue only; the final full-catalogue emission uses K* = 12,395 (owner-calibrated).",
        "Withholding mode is recorded in withholding_mode; 'all' is the primary instrument, 'detached' the conservative one.",
        "Greedy allocator is the shared gems57.emit.greedy_allocate, unmodified.",
    ]
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=EVIDENCE)
    ap.add_argument("--mode", default=HOLDOUT_MODE, choices=("all", "detached"))
    ap.add_argument("--only", default="", help="comma-separated arm names, e.g. A_decay,B_ring")
    args = ap.parse_args()
    only = tuple(x for x in args.only.split(",") if x) or None
    res = run(mode=args.mode, only=only)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=1, allow_nan=False, default=float) + "\n")
    print(f"wrote {args.out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
