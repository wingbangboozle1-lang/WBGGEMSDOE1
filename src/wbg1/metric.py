"""Pooled distance-tolerant Tversky index (DTI) and helpers.

Official metric (DrivenData #306 problem page, as transcribed by sibling audits):
    DTI = TPw / (TPw + alpha*FPw + beta*FNw), alpha=0.2, beta=0.8,
    k(d) = max(1 - d/300m, 0) triangular kernel (R = 3 px at 100 m cells).

Exact terms (matches GEMSDOE28 `kernel_terms`, verified line-by-line):
    A  = sum over predicted pixels of k(dist to nearest truth)
    B  = sum over truth pixels of k(dist to nearest prediction)
    N  = # predicted, T = # truth
    FPw = N - A, FNw = T - B, TPw = A
    DTI = A / (A + 0.2*FPw + 0.8*FNw)

Marginal rule (exact rearrangement): adding one emitted pixel with expected
kernel credit `a` raises DTI iff a > 0.2*DTI; dropping one raises DTI iff its
own credit a < 0.2*DTI. Break-even at DTI=0.2778 is 0.05556.

Naive closure (A ~= B, one-to-one matching): DTI = a / (0.8 + 0.2*N/|G|)
with a = A/T credit fraction. Used ONLY for labelled PROJECTIONS, never scores.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
KERNEL_R_PX = 3.0  # 300 m at 100 m cells
GRID_SHAPE = (3730, 3292)
GRID_CRS = "EPSG:32611"
GRID_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def kernel_from_mask(mask: np.ndarray, r_px: float = KERNEL_R_PX) -> np.ndarray:
    """Triangular kernel field k(d)=max(1-d/r,0) from a boolean mask (float32)."""
    d = distance_transform_edt(~mask)
    k = 1.0 - d / r_px
    k[k < 0.0] = 0.0
    return k.astype(np.float32)


def dti_terms(
    pred: np.ndarray,
    truth: np.ndarray,
    foot: np.ndarray | None = None,
) -> dict:
    """Exact pooled DTI terms. pred/truth bool arrays of GRID_SHAPE.

    Outside-footprint pixels are forced to False for both pred and truth.
    """
    pred = np.asarray(pred, dtype=bool)
    truth = np.asarray(truth, dtype=bool)
    if foot is not None:
        foot = np.asarray(foot, dtype=bool)
        pred = pred & foot
        truth = truth & foot
    k_truth = kernel_from_mask(truth)
    k_pred = kernel_from_mask(pred)
    a = float(k_truth[pred].sum())
    b = float(k_pred[truth].sum())
    n = float(pred.sum())
    t = float(truth.sum())
    fpw = n - a
    fnw = t - b
    denom = a + ALPHA * fpw + BETA * fnw
    dti = a / denom if denom > 0 else 0.0
    return {
        "A": a, "B": b, "N": n, "T": t,
        "FPw": fpw, "FNw": fnw, "DTI": float(dti),
        "credit_fraction_a": (a / t) if t > 0 else 0.0,
        "n_over_t": (n / t) if t > 0 else 0.0,
    }


def dti_from_terms(a: float, fpw: float, fnw: float) -> float:
    denom = a + ALPHA * fpw + BETA * fnw
    return float(a / denom) if denom > 0 else 0.0


def block_ids(shape: tuple[int, int], n_blocks: int = 16) -> np.ndarray:
    """Spatial block id in [0, n_blocks*n_blocks) for cluster bootstrap."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    by = np.minimum((yy * n_blocks) // h, n_blocks - 1)
    bx = np.minimum((xx * n_blocks) // w, n_blocks - 1)
    return (by * n_blocks + bx).astype(np.int32)


def block_contributions(
    pred: np.ndarray,
    truth: np.ndarray,
    foot: np.ndarray,
    n_blocks: int = 16,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-block (A, FPw, FNw) sums for the spatial cluster bootstrap."""
    pred = (np.asarray(pred, dtype=bool) & foot)
    truth = (np.asarray(truth, dtype=bool) & foot)
    k_truth = kernel_from_mask(truth)
    k_pred = kernel_from_mask(pred)
    bids = block_ids(pred.shape, n_blocks)
    nb = n_blocks * n_blocks
    a_blk = np.zeros(nb, dtype=np.float64)
    fp_blk = np.zeros(nb, dtype=np.float64)
    fn_blk = np.zeros(nb, dtype=np.float64)
    py, px = np.nonzero(pred)
    if len(py):
        b = bids[py, px]
        kv = k_truth[py, px].astype(np.float64)
        np.add.at(a_blk, b, kv)
        np.add.at(fp_blk, b, 1.0 - kv)
    ty, tx = np.nonzero(truth)
    if len(ty):
        b = bids[ty, tx]
        kv = k_pred[ty, tx].astype(np.float64)
        np.add.at(fn_blk, b, 1.0 - kv)
    return a_blk, fp_blk, fn_blk


def bootstrap_ci(
    a_blk: np.ndarray,
    fp_blk: np.ndarray,
    fn_blk: np.ndarray,
    n_rep: int = 2000,
    seed: int = 0,
) -> dict:
    """256-block spatial cluster bootstrap 95% CI over pooled DTI."""
    rng = np.random.default_rng(seed)
    nb = len(a_blk)
    idx = rng.integers(0, nb, size=(n_rep, nb))
    a_s = a_blk[idx].sum(axis=1)
    fp_s = fp_blk[idx].sum(axis=1)
    fn_s = fn_blk[idx].sum(axis=1)
    denom = a_s + ALPHA * fp_s + BETA * fn_s
    with np.errstate(divide="ignore", invalid="ignore"):
        vals = np.where(denom > 0, a_s / denom, 0.0)
    point = dti_from_terms(float(a_blk.sum()), float(fp_blk.sum()), float(fn_blk.sum()))
    return {
        "point": float(point),
        "mean": float(vals.mean()),
        "std": float(vals.std()),
        "ci95": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))],
        "n_rep": n_rep,
        "n_blocks": nb,
        "seed": seed,
    }


def pooled_with_ci(
    folds: list[tuple[np.ndarray, np.ndarray]],
    foot: np.ndarray,
    n_blocks: int = 16,
    n_rep: int = 2000,
    seed: int = 0,
) -> dict:
    """Pool (pred, truth) fold pairs: micro-averaged terms + block bootstrap CI.

    Block ids are shared across folds (same grid), so contributions accumulate.
    """
    nb = n_blocks * n_blocks
    a_blk = np.zeros(nb, dtype=np.float64)
    fp_blk = np.zeros(nb, dtype=np.float64)
    fn_blk = np.zeros(nb, dtype=np.float64)
    per_fold = []
    for pred, truth in folds:
        t = dti_terms(pred, truth, foot)
        per_fold.append(t)
        ab, fpb, fnb = block_contributions(pred, truth, foot, n_blocks)
        a_blk += ab
        fp_blk += fpb
        fn_blk += fnb
    ci = bootstrap_ci(a_blk, fp_blk, fn_blk, n_rep=n_rep, seed=seed)
    return {
        "pooled": {
            "A": float(a_blk.sum()),
            "FPw": float(fp_blk.sum()),
            "FNw": float(fn_blk.sum()),
            "DTI": ci["point"],
        },
        "ci": ci,
        "per_fold_dti": [f["DTI"] for f in per_fold],
        "per_fold": per_fold,
    }


def break_even(dti: float) -> float:
    """Marginal credit threshold: a dot must earn > 0.2*DTI to help."""
    return ALPHA * dti


def naive_closure(a: float, n_over_t: float) -> float:
    """DTI = a / (0.8 + 0.2*N/|G|). PROJECTION helper only."""
    return float(a / (0.8 + 0.2 * n_over_t))


def solve_credit_fraction(target: float, n_over_t: float) -> float:
    lo, hi = 1e-12, 1.0
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if naive_closure(mid, n_over_t) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
