#!/usr/bin/env python3
"""Fold-safe hide-and-recover lane, 31 Oct 2026 (WBGGEMSDOE1).

Uses the UNCHANGED shared owner template pieces, vendored under ``vendor/gems57``:

* ``holdout.buffered_component_draw``  -- whole-component withholding, 3 px context
  collar, 12 px quadrant boundary (evaluator split ``buffered-whole-components-loqo-v2``).
* ``evaluate_holdout.evaluate`` + ``pooled_summary`` -- pooled DTI (alpha 0.2, beta 0.8,
  300 m triangular kernel) with a paired percentile CI over 20 km physical blocks
  (evaluator ``gems57-pooled-hide-v2``).
* ``emit.greedy_allocate``            -- exact-marginal dot allocation.

Leakage rules enforced here (the reason earlier catalogue-distance fields were inflated):

1. Every feature a candidate uses is computed from ``fold['visible']`` only, never from
   the full catalogue.
2. A candidate for held-out quadrant k is trained on labels from the OTHER quadrants,
   with a 12 px exclusion band around quadrant k (spatial block CV).
3. The expected hidden-truth budget is ``0.25 x visible catalogue in the quadrant``
   (the protocol's 20 % hide fraction, expressed from visible information only).

Every printed number is labelled HOLDOUT-DTI (with evaluator version, n withheld
positive pixels and 95 % CI) or LEAKAGE-CANARY (per-feature AUC).  Nothing here is an
organizer score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import emit as EM  # noqa: E402
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as GR  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import metric as MT  # noqa: E402

CACHE = ROOT / ".cache/features"
OUT = ROOT / "evidence/fold_safe_20261031"
SEEDS = (20, 21)
BLOCK = 200           # 20 km physical clusters (200 px x 100 m)
CANARY_N = 30_000
NEG_TRAIN = 200_000
TRAIN_EXCLUDE_PX = 12  # buffer between training quadrants and the held quadrant
COLLAR_PX = 3


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_grid_and_bands():
    grid = GR.load_grid(ROOT / "data/bridge")
    with rasterio.open(ROOT / ".cache/training_features.tif") as src:
        names = [(d or f"band{i}").split(" - ")[0] for i, d in enumerate(src.descriptions, 1)]
    fp = grid.footprint
    fp_idx = np.flatnonzero(fp)
    cols = []
    for i in range(1, 20):
        a = np.load(CACHE / f"band-{i:02d}.npy", mmap_mode="r")
        v = np.asarray(a[fp], dtype=np.float64)     # footprint-only copy
        good = np.isfinite(v)
        med = np.median(v[good]) if good.any() else 0.0
        v = np.where(good, v, med)
        sd = v.std() or 1.0
        cols.append(((v - v.mean()) / sd).astype(np.float32))
        del a
    X = np.stack(cols, axis=1)
    return grid, names, fp_idx, X


def quadrant_of(quad: np.ndarray, k: int) -> np.ndarray:
    return quad == k


def visible_distance(visible: np.ndarray) -> np.ndarray:
    return ndi.distance_transform_edt(~visible).astype(np.float32)


def calibrate_to_budget(p: np.ndarray, allowed: np.ndarray, k_expected: float) -> np.ndarray:
    """Scale p (odds-free) so that sum over allowed cells equals the expected hidden budget."""
    p = np.clip(p, 0.0, 1.0).astype(np.float64)
    if float(p[allowed].sum()) <= 0:
        return np.zeros(p.shape, np.float32)
    # find c with sum(clip(c*p)) == k_expected via bisection on log scale
    lo_c, hi_c = 1e-9, 1e9
    for _ in range(80):
        mid = np.sqrt(lo_c * hi_c)
        s = float(np.clip(mid * p[allowed], 0, 1).sum())
        if s > k_expected:
            hi_c = mid
        else:
            lo_c = mid
    return np.clip(np.sqrt(lo_c * hi_c) * p, 0, 1).astype(np.float32)


ALLOC = {"mode": "greedy", "topn_factor": 3.0}


def allocate(p: np.ndarray, allowed: np.ndarray, k_expected: float) -> np.ndarray:
    """greedy: shared exact-marginal allocator. topn: fixed budget N = factor x k_expected
    taking the N highest-scoring allowed pixels (ranking ablation, E3)."""
    if ALLOC["mode"] == "topn":
        n = int(round(ALLOC["topn_factor"] * k_expected))
        score = np.where(allowed, p, -np.inf).reshape(-1)
        n = min(n, int(allowed.sum()))
        idx = np.argpartition(-score, n - 1)[:n]
        out = np.zeros(p.size, bool)
        out[idx] = True
        return out.reshape(p.shape) & allowed
    pc = calibrate_to_budget(p, allowed, k_expected)
    alloc = EM.greedy_allocate(pc, allowed, k_truth=k_expected)
    return np.asarray(alloc.emitted, bool) & allowed


def train_predict_quadrant(grid, X, fp_idx, visible, quad, k, names):
    """Fit on other quadrants (visible labels only); predict on quadrant k."""
    fp = grid.footprint
    # distance of every footprint pixel from the held-out quadrant k (0 inside k)
    dist_k = ndi.distance_transform_edt(~quadrant_of(quad, k) & fp).astype(np.float32)
    vis_fp = visible[fp]
    train_pix = (quad[fp] != k) & (dist_k[fp] > TRAIN_EXCLUDE_PX)
    rng = np.random.default_rng(7 + k)
    dil = ndi.binary_dilation(visible, iterations=COLLAR_PX)
    pos_idx = np.flatnonzero(train_pix & vis_fp)
    neg_pool = np.flatnonzero(train_pix & ~dil[fp])
    neg_idx = rng.choice(neg_pool, size=min(NEG_TRAIN, neg_pool.size), replace=False)
    idx = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate([np.ones(pos_idx.size), np.zeros(neg_idx.size)])
    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, max_leaf_nodes=31,
                                           l2_regularization=1.0, random_state=0)
    model.fit(X[idx], y)
    test_pix = np.flatnonzero(quad[fp] == k)
    prob = np.zeros(fp.shape, np.float32)
    prob_fp = prob[fp]
    prob_fp[test_pix] = model.predict_proba(X[test_pix])[:, 1].astype(np.float32)
    prob[fp] = prob_fp
    meta = dict(fold=k, n_pos_train=int(pos_idx.size), n_neg_train=int(neg_idx.size),
                n_neg_pool=int(neg_pool.size), n_test_pixels=int(test_pix.size))
    return prob, meta


def run_draw(seed, grid, X, fp_idx, mode, names):
    folds, quad = HO.buffered_component_draw(grid, seed=seed)
    visible = folds[0]["visible"]
    dist_vis = visible_distance(visible)
    fp = grid.footprint
    shape = fp.shape
    terms = {"candidate": 0.0, "uniform_null": 0.0, "proximity_null": 0.0}
    per_fold = []
    canary = {}
    rng = np.random.default_rng(seed * 31 + 5)
    for fold in folds:
        k = fold["fold"]
        region = fold["region"]
        truth = fold["truth"]
        allowed = region & fp & ~visible          # pixels that may carry a dot
        k_expected = 0.25 * float((visible & region).sum())
        # -- candidate ------------------------------------------------------
        if mode == "hgb":
            prob, meta = train_predict_quadrant(grid, X, fp_idx, visible, quad, k, names)
        else:
            raise ValueError(mode)
        cand = allocate(prob, allowed, k_expected)
        n_dots = int(cand.sum())
        # -- controls (matched budget) ----------------------------------------
        pool = np.flatnonzero(allowed)
        uni = np.zeros(shape, bool)
        uni.reshape(-1)[rng.choice(pool, size=min(n_dots, pool.size), replace=False)] = True
        prox = np.where(allowed, np.exp(-dist_vis / 3.0), 0.0).astype(np.float32)
        prox_emit = allocate(prox, allowed, k_expected)
        arms = {"candidate": cand.astype(np.float32), "uniform_null": uni.astype(np.float32),
                "proximity_null": prox_emit.astype(np.float32)}
        for name, arr in arms.items():
            _, t = EH.evaluate(arr, fold, fp, block_side=BLOCK, origin=(0, 0), global_shape=shape)
            terms[name] = terms[name] + t if not isinstance(terms[name], float) else t
        per_fold.append(dict(draw=seed, fold=k, n_dots=n_dots, n_truth=int(truth.sum()),
                             k_expected=k_expected, prediction=meta if mode == "hgb" else None,
                             proximity_dots=int(prox_emit.sum()), uniform_dots=int(uni.sum())))
        # -- leakage canary: each feature alone, holdout positives vs active negatives
        neg = np.flatnonzero(region & ~visible & ~truth & fp)
        pos = np.flatnonzero(truth)
        if pos.size and neg.size:
            ps = rng.choice(pos, size=min(CANARY_N, pos.size), replace=False)
            ns = rng.choice(neg, size=min(CANARY_N, neg.size), replace=False)
            yy = np.concatenate([np.ones(ps.size), np.zeros(ns.size)])
            for j, nm in enumerate(names + ["dist_to_visible_catalogue"]):
                flat = np.concatenate([ps, ns])
                if j < len(names):
                    vals = X[np.searchsorted(fp_idx, flat)][:, j]
                else:
                    vals = dist_vis.reshape(-1)[flat]
                a = float(roc_auc_score(yy, vals))
                canary.setdefault(nm, []).append(a)
    return terms, per_fold, canary, visible


def canary_table(canary_raw):
    rows = []
    for nm, aucs in canary_raw.items():
        worst = max(aucs, key=lambda a: abs(a - 0.5))
        rows.append(dict(feature=nm, auc_worst_draw_fold=round(worst, 4),
                         auc_direction_free=round(max(worst, 1 - worst), 4),
                         evidence_class="LEAKAGE-CANARY", threshold=0.90,
                         pass_=bool(max(worst, 1 - worst) <= 0.90)))
    rows.sort(key=lambda r: -r["auc_direction_free"])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--experiment", default="E2-hgb-visible", help="label recorded in the receipt")
    ap.add_argument("--mode", default="hgb", choices=["hgb"])
    ap.add_argument("--alloc", default="greedy", choices=["greedy", "topn"])
    ap.add_argument("--topn-factor", type=float, default=3.0)
    a = ap.parse_args()
    ALLOC["mode"] = a.alloc
    ALLOC["topn_factor"] = a.topn_factor
    t0 = time.time()
    grid, names, fp_idx, X = load_grid_and_bands()
    print(f"[load] footprint={int(grid.footprint.sum())} catalogue={int(grid.catalogue.sum())} bands={len(names)}", flush=True)
    all_terms = {"candidate": None, "uniform_null": None, "proximity_null": None}
    per_fold_all, canary_all = [], {}
    draws = {}
    for seed in SEEDS:
        terms, per_fold, canary, _vis = run_draw(seed, grid, X, fp_idx, a.mode, names)
        print(f"[draw {seed}] folds={len(per_fold)} elapsed={time.time()-t0:.0f}s", flush=True)
        for name in all_terms:
            t = terms[name]
            all_terms[name] = t if all_terms[name] is None else all_terms[name] + t
        per_fold_all += per_fold
        for nm, v in canary.items():
            canary_all.setdefault(nm, []).extend(v)
        draws[seed] = terms
    summary = EH.pooled_summary(all_terms, draws=1000, seed=520810, candidate="candidate")
    per_draw = {}
    for seed, terms in draws.items():
        per_draw[str(seed)] = EH.pooled_summary(terms, draws=1000, seed=520810, candidate="candidate")["scores"]["candidate"]
    ctable = canary_table(canary_all)
    receipt = dict(
        schema="gems-fold-safe-lane-v1",
        experiment=a.experiment,
        evidence_class_note="HOLDOUT-DTI; LEAKAGE-CANARY. Not an organizer score.",
        evaluator_version=EH.VERSION,
        evaluator_source_sha256={n: sha256(ROOT / "vendor/gems57" / n) for n in ("evaluate_holdout.py", "holdout.py", "metric.py", "emit.py", "grid.py")},
        holdout=dict(draw_seeds=list(SEEDS), split="buffered-whole-components-loqo-v2", hide_frac=0.20,
                     collar_px=COLLAR_PX, quadrant_boundary_px=12, block_side_px=BLOCK,
                     paired_summary=summary),
        per_draw_candidate=per_draw,
        per_fold=per_fold_all,
        canary=ctable,
        canary_pass_all=bool(all(r["pass_"] for r in ctable)),
        runtime_s=round(time.time() - t0, 1),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{a.experiment}.json"
    path.write_text(json.dumps(receipt, indent=2, allow_nan=False, default=float) + "\n")
    sc = summary["scores"]
    print(json.dumps(dict(
        candidate_dti=round(sc["candidate"]["dti"], 6), ci95=[round(x, 6) for x in sc["candidate"]["ci95"]],
        withheld_positive_pixels=sc["candidate"]["withheld_positive_pixels"],
        uniform_null=round(sc["uniform_null"]["dti"], 6), proximity_null=round(sc["proximity_null"]["dti"], 6),
        delta_vs_proximity=summary["paired_differences"]["proximity_null"]["delta"],
        delta_vs_proximity_ci95=summary["paired_differences"]["proximity_null"]["ci95"],
        max_canary_auc=ctable[0]["auc_direction_free"], canary_top=ctable[0]["feature"],
        canary_pass_all=receipt["canary_pass_all"], written=str(path.relative_to(ROOT))), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
