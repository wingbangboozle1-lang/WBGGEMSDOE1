#!/usr/bin/env python3
"""WBG-5 holdout: per-fold train on visible catalogue, emit blended dots, score."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path("/home/user/WBGGEMSDOE1")
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "vendor"))
from gems.holdout import SegmentHoldout
from gems57.emit import greedy_allocate

WORK = Path("/tmp/wbg5")
LABELS = ROOT / "data/bridge/labels.tif"
SEED = 20261028
K_TRUTH_FOLD = 60988.0  # full catalogue positives for the surrogate bar

with rasterio.open(LABELS) as s:
    lab = s.read(1)
foot = lab != -1
cat = lab == 1

feats = np.lib.format.open_memmap(WORK / "wbg5_features.npy", mode="r", dtype="float32",
                                  shape=(46, lab.shape[0], lab.shape[1]))
dcoc = np.asarray(feats[41]).copy()


def norm01(a, foot):
    a = np.where(foot, a, 0.0)
    mx = np.nanmax(a[foot]) if foot.any() else 1.0
    return (a / mx).astype(np.float32) if mx > 0 else a.astype(np.float32)


dcoc_n = norm01(dcoc, foot)
ho = SegmentHoldout(foot, cat)
print(f"folds: {[f['name'] for f in ho.folds]}", flush=True)

from sklearn.ensemble import HistGradientBoostingClassifier

def run_variant(w_dcoc, tag):
    t0 = time.time()
    preds = []
    for fold in ho.folds:
        visible = fold["visible"]; train = fold["train"]
        pos_mask = visible & train
        neg_pool = train & ~pos_mask
        rng = np.random.default_rng(SEED + fold["id"])
        pos_idx = np.flatnonzero(pos_mask.ravel())
        neg_idx = np.flatnonzero(neg_pool.ravel())
        neg_idx = rng.choice(neg_idx, size=min(neg_idx.size, 4 * pos_idx.size), replace=False)
        sel = np.r_[pos_idx, neg_idx]
        y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
        X = np.empty((sel.size, feats.shape[0]), np.float32)
        rows, cols = np.divmod(sel, lab.shape[1])
        for j in range(feats.shape[0]):
            X[:, j] = np.asarray(feats[j])[rows, cols]
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
                                             max_leaf_nodes=63, min_samples_leaf=40,
                                             l2_regularization=1.0, random_state=SEED)
        clf.fit(X, y)
        surf = np.zeros(lab.shape, np.float32)
        for r0 in range(0, lab.shape[0], 128):
            r1 = min(lab.shape[0], r0 + 128); h = r1 - r0
            Xc = np.empty((h * lab.shape[1], feats.shape[0]), np.float32)
            for j in range(feats.shape[0]):
                Xc[:, j] = np.asarray(feats[j][r0:r1]).ravel()
            surf[r0:r1] = clf.predict_proba(Xc)[:, 1].reshape(h, lab.shape[1]).astype(np.float32)
        surf[~foot] = 0.0
        del X, Xc
        surf_n = norm01(surf, foot)
        s = ((1 - w_dcoc) * surf_n + w_dcoc * dcoc_n).astype(np.float32)
        # admissible mask is the fold quadrant (hidden truth lives there); the
        # full catalogue must NOT be removed or the hidden positives vanish.
        allowed = fold["valid"]
        ktruth = float(fold["truth"].sum())
        a = greedy_allocate(s, allowed, ktruth, floor=0.02, max_dots=60000)
        dots = a.emitted.astype(np.float32)
        preds.append(dots)
        print(f"  {tag} fold {fold['name']}: dots {int(dots.sum())} ({time.time()-t0:.0f}s)", flush=True)
    res = ho.summarize(preds, ci_draws=999)
    print(f"{tag}: HOLDOUT-DTI {res['dti']:.6f} CI {res['ci95']['interval']} "
          f"n={res.get('n_truth', '?')} ({time.time()-t0:.0f}s)", flush=True)
    return res

results = {}
for w, tag in [(0.0, "pureHGB"), (0.75, "blend75")]:
    results[tag] = run_variant(w, tag)
(WORK / "holdout.json").write_text(json.dumps(results, indent=1, default=float))
print(json.dumps({k: {"dti": v["dti"], "ci": v["ci95"]["interval"]} for k, v in results.items()}, indent=1))
