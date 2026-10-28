#!/usr/bin/env python3
"""Fit the WBG-6 radial hidden-truth model to the 118 owner-reported scores.

The private label set of DrivenData competition 306 is never released, but each
reported score is an exact functional of it.  This script inverts 118 of those
scores into (a) the total number of hidden-truth cells K and (b) the radial
distribution of those cells relative to the *public* mapped-fault catalogue.

Outputs (all MODEL-ESTIMATE, never ORGANIZER-CONFIRMED):
  evidence/wbg6_truth_fit.json      fitted parameters, LOO diagnostics
  .cache/wbg6_stats.npz             per-submission sufficient statistics
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.optimize import minimize

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from wbg6.truth_model import (RADIUS_PX, RING_LABELS, ModelFit, ring_ids)

STATS = ROOT / ".cache/wbg6_stats.npz"


def coverage_field(dots: np.ndarray) -> np.ndarray:
    """f(x) = max kernel to the nearest dot: the submission's own coverage field."""
    d = ndi.distance_transform_edt(~dots)
    return np.maximum(1.0 - d / RADIUS_PX, 0.0).astype(np.float32)


def build_stats():
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as src:
        cat = src.read(1) > 0
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        foot = np.isfinite(src.read(1))
    d_cat = ndi.distance_transform_edt(~cat)
    rings = ring_ids(d_cat)
    rings = np.where(foot, rings, -1)
    n_rings = len(RING_LABELS)
    ring_cells = np.array([int((rings == r).sum()) for r in range(n_rings)], float)
    names, abars, counts, scores = [], [], [], []
    for rec in fetch["entries"]:
        with rasterio.open(ROOT / rec["local"]) as src:
            a = src.read(1)
        dots = np.isfinite(a) & (a > 0) & foot
        cov = coverage_field(dots)
        abar = np.zeros(n_rings)
        cnt = np.zeros(n_rings)
        for r in range(n_rings):
            m = rings == r
            if m.any():
                abar[r] = float(cov[m].mean())
            mr = dots & m
            cnt[r] = float(mr.sum())
        names.append(rec["name"])
        abars.append(abar)
        counts.append(cnt)
        scores.append(float(rec["score"]))
        if len(names) % 25 == 0:
            print(f"  {len(names)} rasters", flush=True)
    np.savez_compressed(STATS, names=np.array(names), abar=np.array(abars),
                        counts=np.array(counts), scores=np.array(scores),
                        ring_cells=ring_cells)
    return names, np.array(abars), np.array(counts), np.array(scores), ring_cells


def unpack(theta):
    K = float(np.exp(theta[0]))
    z = np.asarray(theta[1:], float)
    e = np.exp(z - z.max())
    return K, e / e.sum()


def residuals(theta, abar, counts, scores, ring_cells):
    K, w = unpack(theta)
    pred = np.array([_score(abar[i], counts[i], ring_cells, w, K)
                     for i in range(len(scores))])
    return pred - scores


def _score(abar, counts, ring_cells, w, K):
    # inlined predict_score for speed inside the optimiser
    lam = K * w / np.maximum(ring_cells, 1.0)
    tp = float(min((abar * (K * w)).sum(), K))
    S = 9.380297810508184
    fp = float(min((counts * (1.0 - np.exp(-S * lam))).sum(), counts.sum()))
    fn = max(K - tp, 0.0)
    den = tp + 0.2 * fp + 0.8 * fn + 1e-12
    return tp / den if den > 0 else 0.0


def fit(abar, counts, scores, ring_cells, x0=None, n_rings=8, loss="l2"):
    if x0 is None:
        x0 = np.r_[np.log(4000.0), np.zeros(n_rings)]
    def obj(t):
        r = residuals(t, abar, counts, scores, ring_cells)
        return float((r ** 2).mean())
    best = None
    rng = np.random.default_rng(7)
    starts = [x0] + [x0 + rng.normal(0, 0.7, size=len(x0)) for _ in range(6)]
    for s in starts:
        out = minimize(obj, s, method="Nelder-Mead",
                       options={"maxiter": 4000, "xatol": 1e-4, "fatol": 1e-10})
        if best is None or out.fun < best.fun:
            best = out
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()
    if args.rebuild or not STATS.exists():
        names, abar, counts, scores, ring_cells = build_stats()
    else:
        z = np.load(STATS, allow_pickle=False)
        names, abar, counts, scores, ring_cells = (z["names"], z["abar"],
                                                   z["counts"], z["scores"], z["ring_cells"])
    n_rings = len(RING_LABELS)
    out = fit(abar, counts, scores, ring_cells, n_rings=n_rings)
    K, w = unpack(out.x)
    pred = np.array([_score(abar[i], counts[i], ring_cells, w, K) for i in range(len(scores))])
    r2 = 1 - ((scores - pred) ** 2).sum() / ((scores - scores.mean()) ** 2).sum()

    loo = np.empty_like(scores)
    for i in range(len(scores)):
        m = np.ones(len(scores), bool)
        m[i] = False
        o = fit(abar[m], counts[m], scores[m], ring_cells, x0=out.x, n_rings=n_rings)
        K_i, w_i = unpack(o.x)
        loo[i] = _score(abar[i], counts[i], ring_cells, w_i, K_i)
    r2loo = 1 - ((scores - loo) ** 2).sum() / ((scores - scores.mean()) ** 2).sum()
    from scipy.stats import pearsonr, spearmanr
    print(f"\nK (hidden-truth cells) = {K:,.0f}")
    print("hidden truth by distance-to-catalogue ring:")
    for lbl, ww, rc in zip(RING_LABELS, w, ring_cells):
        print(f"  {lbl:>6s}: w={ww:7.4f}  cells={int(rc):>9,}  truth_cells={K*ww:8.1f}")
    print(f"\nin-sample R^2 = {r2:.3f}")
    print(f"LOO R^2       = {r2loo:.3f}")
    print(f"LOO Pearson   = {pearsonr(scores, loo)[0]:.3f}   "
          f"LOO Spearman = {spearmanr(scores, loo)[0]:.3f}")
    print(f"LOO RMSE      = {np.sqrt(((scores-loo)**2).mean()):.4f} "
          f"(sd {scores.std():.4f})")
    fit_obj = ModelFit(K, w, ring_cells,
                       r2_in_sample=float(r2), r2_loo=float(r2loo),
                       loo_pearson=float(pearsonr(scores, loo)[0]),
                       loo_spearman=float(spearmanr(scores, loo)[0]),
                       loo_rmse=float(np.sqrt(((scores - loo) ** 2).mean())),
                       n_submissions=int(len(scores)),
                       score_label="OWNER-REPORTED",
                       evidence_class="MODEL-ESTIMATE")
    payload = fit_obj.to_dict()
    payload["loo_predictions"] = [
        {"name": str(nm), "score": float(s), "loo_pred": float(p)}
        for nm, s, p in zip(names, scores, loo)]
    payload["predictions_in_sample"] = [
        {"name": str(nm), "score": float(s), "pred": float(p)}
        for nm, s, p in zip(names, scores, pred)]
    (ROOT / "evidence/wbg6_truth_fit.json").write_text(json.dumps(payload, indent=1))
    print("wrote evidence/wbg6_truth_fit.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
