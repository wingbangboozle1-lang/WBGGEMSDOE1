#!/usr/bin/env python3
"""WBG-3 Experiment 3 (pre-registered before fitting, 2026-10-27).

Diagnosis motivating this experiment (measured on Experiment 2 surfaces):
the HGB surface's top-8,000 pixels per fold sit on average 250-520 px from the
visible catalogue and fold AUC is 0.57-0.70 -- the raw stack is dominated by
broad regional propensity (basin depth, earthquake density), not local
lineaments. Experiment 3 adds LOCAL features only:

  * local contrast (value - Gaussian sigma=8 px) for lidar step_max,
    tmi_hg, det_elev_slope, iso_grav_anom_hg, depth_to_base gradmag,
    cond_surf gradmag;
  * structure-tensor line-likeness (wbg2.features.structure_tensor,
    sigma=2, rho=5) of lidar step_max and of tmi_hg;
  * Laplacian (sigma=2) of det_elev and tmi.

Everything else is identical to Experiment 2: same folds, same HGB settings,
same negatives, same dotted emission (clearance >2 px, spacing block 2,
budgets 37,654 and 22,000). This is the last experiment in the budget of 3
(Exp1 was invalidated by IR-WBG3-01 leakage and produced no valid measurement;
Exp2 = detector v2; Exp3 = this local-feature detector).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems.holdout import SegmentHoldout  # noqa: E402
from wbg2.features import structure_tensor  # noqa: E402
from run_wbg3_experiments import build_static_features, dotted, WORK, SEED, LABELS  # noqa: E402


def build_local_features(static, names, foot):
    cache = WORK / "local_features.npy"
    idx = {n: i for i, n in enumerate(names)}
    src_bands = ["lidar:step_max", "official:tmi_hg", "official:det_elev_slope",
                 "official:iso_grav_anom_hg", "gradmag:depth_to_base_surf", "gradmag:cond_surf"]
    n = len(src_bands) + 2 + 2
    shape = (n, foot.shape[0], foot.shape[1])
    if cache.exists():
        return np.lib.format.open_memmap(cache, mode="r", dtype="float32", shape=shape), \
            [f"contrast8:{b}" for b in src_bands] + ["tensor:lidar_step", "tensor:tmi_hg",
                                                     "lap2:det_elev", "lap2:tmi"]
    arr = np.lib.format.open_memmap(cache, mode="w+", dtype="float32", shape=shape)
    out_names = []
    i = 0
    for b in src_bands:
        a = np.asarray(static[idx[b]], dtype=np.float64)
        a = np.where(np.isfinite(a), a, 0.0)
        arr[i] = np.where(foot, a - ndi.gaussian_filter(a, 8.0), 0.0).astype(np.float32)
        out_names.append(f"contrast8:{b}"); i += 1
    for b, nm in (("lidar:step_max", "tensor:lidar_step"), ("official:tmi_hg", "tensor:tmi_hg")):
        a = np.asarray(static[idx[b]], dtype=np.float64)
        a = np.where(np.isfinite(a), a, 0.0)
        ll, _, _ = structure_tensor(a.astype(np.float32), foot, sigma=2.0, rho=5.0)
        arr[i] = ll; out_names.append(nm); i += 1
    for b, nm in (("official:det_elev", "lap2:det_elev"), ("official:tmi", "lap2:tmi")):
        a = np.asarray(static[idx[b]], dtype=np.float64)
        a = np.where(np.isfinite(a), a, np.nanmean(a[foot & np.isfinite(a)]))
        arr[i] = np.where(foot, ndi.gaussian_laplace(a, 2.0), 0.0).astype(np.float32)
        out_names.append(nm); i += 1
    arr.flush()
    return np.lib.format.open_memmap(cache, mode="r", dtype="float32", shape=shape), out_names


def main() -> int:
    t0 = time.time()
    with rasterio.open(LABELS) as s:
        lab = s.read(1)
    foot = lab != -1
    cat = lab == 1
    static, names = build_static_features(lab.shape)
    local, lnames = build_local_features(static, names, foot)
    print("local features", lnames, flush=True)
    ho = SegmentHoldout(foot, cat)

    # canary on the new features alone
    canary = ho.canary({n: np.asarray(local[i]) for i, n in enumerate(lnames)}, max_per_class=8000)
    (WORK / "canary_exp3.json").write_text(json.dumps(canary, indent=1))
    print("exp3 canary passed:", canary["passed"], flush=True)

    from sklearn.ensemble import HistGradientBoostingClassifier
    n_static, n_local = static.shape[0], local.shape[0]
    total_foot = int(foot.sum())
    surfaces, fold_data = [], []
    for fold in ho.folds:
        tf = time.time()
        dist_v = ndi.distance_transform_edt(~fold["visible"]).astype(np.float32)
        train = fold["train"]
        pos_mask = fold["visible"] & train
        neg_pool = train & ~pos_mask
        rng = np.random.default_rng(SEED + fold["id"])
        pos_idx = np.flatnonzero(pos_mask.ravel())
        neg_idx = np.flatnonzero(neg_pool.ravel())
        neg_idx = rng.choice(neg_idx, size=min(neg_idx.size, 4 * pos_idx.size), replace=False)
        sel = np.r_[pos_idx, neg_idx]
        y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
        rows, cols = np.divmod(sel, lab.shape[1])
        X = np.empty((sel.size, n_static + n_local), np.float32)
        for j in range(n_static):
            X[:, j] = np.asarray(static[j])[rows, cols]
        for j in range(n_local):
            X[:, n_static + j] = np.asarray(local[j])[rows, cols]
        clf = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
            min_samples_leaf=40, l2_regularization=1.0, random_state=SEED)
        clf.fit(X, y)
        surf = np.zeros(lab.shape, np.float32)
        F = n_static + n_local
        for r0 in range(0, lab.shape[0], 128):
            r1 = min(lab.shape[0], r0 + 128)
            h = r1 - r0
            Xc = np.empty((h * lab.shape[1], F), np.float32)
            for j in range(n_static):
                Xc[:, j] = np.asarray(static[j][r0:r1]).ravel()
            for j in range(n_local):
                Xc[:, n_static + j] = np.asarray(local[j][r0:r1]).ravel()
            surf[r0:r1] = clf.predict_proba(Xc)[:, 1].reshape(h, lab.shape[1]).astype(np.float32)
        surf[~foot] = 0.0
        np.save(WORK / f"surface_exp3_fold{fold['id']}.npy", surf)
        surfaces.append(surf)
        fold_data.append((fold, dist_v))
        print(f"fold {fold['name']} done {time.time()-tf:.0f}s", flush=True)

    results, preds_by_budget = {}, {}
    for budget in (37654, 22000):
        preds = []
        for fold, dist_v in fold_data:
            b = int(round(budget * int((fold["valid"] & foot).sum()) / total_foot))
            preds.append(dotted(surfaces[fold["id"]], fold["valid"] & foot, dist_v, b, 2))
        res = ho.summarize(preds, ci_draws=999)
        results[f"E3_local_budget{budget}"] = res
        preds_by_budget[budget] = preds
        print(f"E3 budget {budget} HOLDOUT-DTI {res['dti']:.5f} {res['ci95']['interval']}", flush=True)

    # paired vs Experiment 2 E1 (identical dotted emission, budget 37654)
    exp2 = json.loads((WORK / "experiments.json").read_text())
    # rebuild Exp2 preds from saved surfaces for paired comparison
    from run_wbg3_experiments import dotted as _dotted  # noqa
    preds_e2 = []
    for fold, dist_v in fold_data:
        s2 = np.load(WORK / f"surface_fold{fold['id']}.npy")
        b = int(round(37654 * int((fold["valid"] & foot).sum()) / total_foot))
        preds_e2.append(dotted(s2, fold["valid"] & foot, dist_v, b, 0))
    paired = ho.compare_paired(preds_by_budget[37654], preds_e2, ci_draws=999)
    out = {"arms": results, "paired_E3_vs_E2": paired, "exp2_reference": exp2["arms"],
           "local_feature_names": lnames, "elapsed_s": time.time() - t0}
    (WORK / "experiments_exp3.json").write_text(json.dumps(out, indent=1, default=float))
    print("paired E3-E2", paired["paired_delta_dti"], paired["paired_delta_ci95"], flush=True)
    print(f"DONE {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
