#!/usr/bin/env python3
"""Experiment H2 - potential-field edge corroboration (research lane, 31 Oct 2026).

Hypothesis (ranked #1 of the 27 Oct untested list, see docs/research/future-hypotheses-20261027.md):
a concealed, catalogue-absent fault offsets magnetic and gravity basement fabric at the
same place. Edges that are co-located in BOTH the reduced-to-pole magnetic field and the
isostatic gravity field, and that sit on coherent (linear) fabric, should be more
fault-like than edges seen in only one field.

Scoring surface S uses ONLY the 19 cached potential-field / terrain bands. It never reads
the catalogue, so it cannot leak a withheld fault. The catalogue enters only as the
avoidance rule (dots keep >= 3 px from mapped faults), which is applied per fold to the
VISIBLE catalogue of that fold (shared gems57 holdout), never to withheld truth.

Shared tools reused: gems57.grid (grid + catalogue), gems57.holdout (hide-and-recover folds,
per-cell DTI via score_cell), gems57.metric (DTI constants). Nothing here is a private
evaluator: cell scoring is the shared score_cell; pooling is the shared evaluate() formula.

Usage: .venv/bin/python scripts/run_h2_lag_corroboration.py [--arm full|mag_only|grav_only]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import holdout as H
from gems57.grid import load_grid
from gems57.metric import ALPHA, BETA

EVALUATOR = "gems57-pooled-hide-v2 (vendor/gems57/holdout.py score_cell + pooled formula)"
K_TOTAL = 37654          # size of the best-reported focus file; matched budget for all arms
SEP_R = 2                # Chebyshev blocking radius -> accepted dots are >= 3 px apart
AVOID_PX = 3             # keep dots >= 3 px from the (visible) catalogue
BAND = {}                # filled from band descriptions


def band_index() -> dict[str, int]:
    with rasterio.open(ROOT / "data/training_features.tif") as ds:
        names = [d.split(" - ")[0] for d in ds.descriptions]
    return {n: i + 1 for i, n in enumerate(names)}


def read_band(idx: int) -> np.ndarray:
    with rasterio.open(ROOT / "data/training_features.tif") as ds:
        return ds.read(idx).astype(np.float64)


def robust_z(a: np.ndarray, fp: np.ndarray) -> np.ndarray:
    v = a[fp]
    med = np.median(v)
    mad = 1.4826 * np.median(np.abs(v - med)) + 1e-12
    z = (a - med) / mad
    z[~fp] = 0.0
    return z


def fill_outside(a: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Replace non-finite / outside values with the footprint median so filters do not ring."""
    out = np.where(np.isfinite(a) & fp, a, np.nan)
    med = np.nanmedian(out)
    out = np.where(np.isfinite(out), out, med)
    return out


def components(fp: np.ndarray) -> dict[str, np.ndarray]:
    """Named component fields. None of them reads the catalogue."""
    bi = band_index()
    mag = fill_outside(read_band(bi["rtp"]), fp)
    grav = fill_outside(read_band(bi["iso_grav_anom"]), fp)
    mag_s = ndi.gaussian_filter(mag, 1.0)
    grav_s = ndi.gaussian_filter(grav, 1.0)
    gy_m, gx_m = np.gradient(mag_s)
    gy_g, gx_g = np.gradient(grav_s)
    e_mag = robust_z(np.hypot(gx_m, gy_m), fp)
    e_grav = robust_z(np.hypot(gx_g, gy_g), fp)
    # structure-tensor coherence of the magnetic fabric at 3 px (1 = strictly linear)
    j11 = ndi.gaussian_filter(gx_m * gx_m, 3.0)
    j22 = ndi.gaussian_filter(gy_m * gy_m, 3.0)
    j12 = ndi.gaussian_filter(gx_m * gy_m, 3.0)
    coh = ((j11 - j22) ** 2 + 4 * j12 ** 2) / ((j11 + j22) ** 2 + 1e-12)
    coh = np.clip(coh, 0, 1)
    coh[~fp] = 0.0
    return {"edge_mag": np.clip(e_mag, 0, None), "edge_grav": np.clip(e_grav, 0, None),
            "coherence": coh}


def score_surface(c: dict[str, np.ndarray], arm: str) -> np.ndarray:
    if arm == "full":
        s = np.sqrt(c["edge_mag"] * c["edge_grav"]) * c["coherence"]
    elif arm == "mag_only":
        s = c["edge_mag"] * c["coherence"]
    elif arm == "grav_only":
        s = c["edge_grav"] * c["coherence"]
    elif arm == "random":
        s = np.random.default_rng(31).random(c["coherence"].shape)
    else:
        raise ValueError(arm)
    return s


def place(score: np.ndarray, region: np.ndarray, avoid: np.ndarray, k: int) -> np.ndarray:
    """Greedy top-k with a 3-px minimum spacing. Deterministic (ties broken by index)."""
    ok = region & ~avoid
    cand = np.flatnonzero(ok.ravel())
    if cand.size == 0 or k <= 0:
        return np.zeros(score.shape, bool)
    vals = score.ravel()[cand]
    order = cand[np.lexsort((cand, -vals))]
    h, w = score.shape
    blocked = np.zeros(score.shape, bool)
    out = np.zeros(score.shape, bool)
    n = 0
    for flat in order:
        y, x = divmod(int(flat), w)
        if blocked[y, x]:
            continue
        out[y, x] = True
        blocked[max(0, y - SEP_R):y + SEP_R + 1, max(0, x - SEP_R):x + SEP_R + 1] = True
        n += 1
        if n >= k:
            break
    return out


def auc(score_vals: np.ndarray, label: np.ndarray) -> float:
    """Rank AUC (Mann-Whitney), no sklearn dependency."""
    from scipy.stats import rankdata
    pos = label.astype(bool)
    npos, nneg = int(pos.sum()), int((~pos).sum())
    if npos == 0 or nneg == 0:
        return float("nan")
    r = rankdata(score_vals)
    return float((r[pos].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def emissions_for_holdout(ctx, surface: np.ndarray, quad: np.ndarray, fp: np.ndarray) -> dict:
    """One emission per (draw, mode). Each quadrant uses its own VISIBLE catalogue."""
    out = {}
    k_q = int(round(K_TOTAL / 4))
    for seed in (20, 21):
        for mode in ("all", "detached"):
            em = np.zeros(fp.shape, bool)
            for qi, qname in enumerate(H.FOLD_NAMES):
                key = f"draw{seed}_fold{qname}_{mode}"
                vis = ctx.visible(key)
                avoid = (ndi.distance_transform_edt(~vis) <= AVOID_PX) if AVOID_PX > 0 else np.zeros(fp.shape, bool)
                region = (quad == qi) & fp
                em |= place(surface, region, avoid, k_q)
            out[(seed, mode)] = em
    return out


def pooled_from_cells(cell_results: list[dict]) -> dict:
    tp = sum(r["tp"] for r in cell_results)
    fp_ = sum(r["fp"] for r in cell_results)
    fn = sum(r["fn"] for r in cell_results)
    dti = tp / (tp + ALPHA * fp_ + BETA * fn + 1e-12)
    return {"pooled_dti": float(dti), "tp": tp, "fp": fp_, "fn": fn,
            "n_truth": int(sum(r["n_truth"] for r in cell_results))}


def bootstrap_ci(cells: list[dict], n_boot: int = 2000, seed: int = 7) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = []
    m = len(cells)
    for _ in range(n_boot):
        idx = rng.integers(0, m, m)
        vals.append(pooled_from_cells([cells[i] for i in idx])["pooled_dti"])
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def run_arm(ctx, arm: str, comps: dict, quad, fp) -> dict:
    surface = score_surface(comps, arm)
    ems = emissions_for_holdout(ctx, surface, quad, fp)
    cells = []
    for cell in ctx.cells:
        seed = cell.seed
        r = H.score_cell(cell, ems[(seed, cell.mode)])
        r["key"] = cell.key
        cells.append(r)
    res = pooled_from_cells(cells)
    res["ci95_bootstrap_over_16_cells"] = list(bootstrap_ci(cells))
    res["per_cell"] = {c["key"]: c["dti"] for c in cells}
    return res, cells, surface


def canary(comps: dict, ctx, fp) -> dict:
    """Each feature alone: rank AUC of the feature (inside each fold's active domain)
    against the withheld truth of that fold. Leakage alarm if > 0.90."""
    rows = {k: [] for k in comps}
    labels = []
    for cell in ctx.cells:
        sl = cell.bbox
        act = cell.active
        truth = np.zeros(act.shape, bool)
        truth[cell.truth_yx] = True
        sel = act
        labels.append(truth[sel])
        for k, v in comps.items():
            rows[k].append(v[sl][sel])
    lab = np.concatenate(labels)
    out = {}
    for k in comps:
        vals = np.concatenate(rows[k])
        out[k] = round(auc(vals, lab), 4)
    out["max_alone_auc"] = max(out.values())
    out["leakage_alarm_gt_0_90"] = bool(out["max_alone_auc"] > 0.90)
    return out


def main() -> int:
    global AVOID_PX
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["full", "mag_only", "grav_only", "random"])
    ap.add_argument("--out", type=Path, default=ROOT / "evidence/h2_lag/experiment_20261031.json")
    ap.add_argument("--avoid-px", type=int, default=AVOID_PX,
                    help="catalogue-avoidance radius (0 = no avoidance)")
    args = ap.parse_args()
    AVOID_PX = args.avoid_px

    grid = load_grid()
    fp = grid.footprint
    quad = H.quadrant_ids(fp)
    ctx = H.build_holdout(grid)
    comps = components(fp)
    # comparability check: the catalogue and holdout are shared, not re-derived here
    report = {
        "experiment": "H2 potential-field edge corroboration",
        "date_utc": "2026-10-31",
        "evaluator": EVALUATOR,
        "budget_dots": K_TOTAL,
        "avoid_px": AVOID_PX,
        "note": "AVOID_PX=0 disables catalogue avoidance (ablation)",
        "spacing_chebyshev_radius": SEP_R,
        "holdout": "H.build_holdout: seeds (20,21) x quadrants x modes (all, detached); 16 cells",
        "n_cells": len(ctx.cells),
        "arms": {},
        "canary_alone_auc": canary(comps, ctx, fp),
        "scores_use_catalogue": False,
        "label": "HOLDOUT-DTI",
    }
    cell_store = {}
    for arm in args.arms:
        res, cells, _ = run_arm(ctx, arm, comps, quad, fp)
        report["arms"][arm] = {k: v for k, v in res.items() if k != "per_cell"} | {"per_cell": res["per_cell"]}
        cell_store[arm] = cells
        print(f"{arm:10s} HOLDOUT-DTI {res['pooled_dti']:.6f} "
              f"95%CI [{res['ci95_bootstrap_over_16_cells'][0]:.6f}, {res['ci95_bootstrap_over_16_cells'][1]:.6f}] "
              f"n_truth={res['n_truth']}", flush=True)
    if "random" in cell_store and "full" in cell_store:
        diffs = [a["dti"] - b["dti"] for a, b in zip(cell_store["full"], cell_store["random"])]
        d = np.array(diffs)
        rng = np.random.default_rng(11)
        boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        report["paired_full_minus_random_mean_cell_dti"] = float(d.mean())
        report["paired_ci95_over_16_cells"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
