"""Metric-rational sparse placement for the distance-weighted Tversky index.

Why placement is a separate problem from detection
--------------------------------------------------
With ``DTI = TPw / (TPw + a*FPw + b*FNw)``, a=0.2, b=0.8 and
``k(d) = max(1 - d/300m, 0)``, adding one predicted pixel with value 1 at a
location whose nearest ground-truth pixel has kernel weight ``k`` changes

    dTPw = +k,  dFNw = -k (only if it becomes that truth pixel's max),  dFPw = +(1-k)

Because 1 - alpha - beta = 0, the denominator moves by exactly ``alpha`` no
matter what ``k`` is:

    dD = dTPw + alpha*dFPw + beta*dFNw
       = k + alpha*(1 - k) + beta*(-k) = alpha + k*(1 - alpha - beta) = alpha

so ``dDTI > 0`` iff ``k*D > TPw*alpha`` iff **``k > alpha*DTI``** (exact in the
single-truth limit and cross-checked numerically against the shared metric in
``tests/test_wbg5.py``). For DTI = 0.28 that is k > 0.056, i.e. a dot within
about 2.8 px of a ground truth pixel is always worth emitting, while a
redundant dot on ground truth that is already covered adds nothing.

Consequence: the objective is *distinct* truth coverage, not surface ranking.
Ranking by probability and taking the top N (or thresholding a surface) spends
most of the budget on the dense cores of a few ridges. A greedy max-coverage
order with a hard minimum spacing turns the same budget into much more covered
fault length. ``suppression_order`` implements that greedy order efficiently
(descending score, accept, then suppress a disk of radius ``d_min``).
"""

from __future__ import annotations

import numpy as np


def _disk_offsets(radius: float) -> tuple[np.ndarray, np.ndarray]:
    r = int(np.ceil(radius))
    dy, dx = np.mgrid[-r : r + 1, -r : r + 1]
    keep = np.hypot(dy, dx) <= radius
    return dy[keep], dx[keep]


def suppression_order(
    score: np.ndarray,
    eligible: np.ndarray,
    *,
    d_min: float,
    max_n: int,
    keep_frac: float = 0.2,
) -> np.ndarray:
    """Greedy spacing-constrained coverage order; returns flat indices, best first.

    ``d_min`` is the suppression radius in pixels (Euclidean). ``keep_frac``
    pre-filters to the top fraction of eligible scores; it only bounds runtime
    and must be large enough that ``max_n`` dots fit inside it.
    """
    score = np.asarray(score, np.float32)
    eligible = np.asarray(eligible, bool)
    if score.shape != eligible.shape:
        raise ValueError("score/eligible shape mismatch")
    if max_n <= 0 or d_min <= 0:
        raise ValueError("positive d_min and max_n required")

    ids = np.flatnonzero(eligible & np.isfinite(score) & (score > 0))
    if not len(ids):
        return np.empty(0, np.int64)
    if keep_frac < 1.0:
        cut = np.quantile(score.ravel()[ids], 1.0 - keep_frac)
        ids = ids[score.ravel()[ids] >= cut]
    vals = score.ravel()[ids]
    order = ids[np.argsort(-vals, kind="stable")]

    height, width = score.shape
    dy, dx = _disk_offsets(d_min)
    blocked = np.zeros(score.size, bool)
    accepted: list[int] = []
    for flat in order:
        if blocked[flat]:
            continue
        accepted.append(int(flat))
        row, col = divmod(int(flat), width)
        rr = row + dy
        cc = col + dx
        ok = (rr >= 0) & (rr < height) & (cc >= 0) & (cc < width)
        blocked[rr[ok] * width + cc[ok]] = True
        if len(accepted) >= max_n:
            break
    return np.asarray(accepted, np.int64)


def dots_from_order(order: np.ndarray, n: int, shape: tuple[int, int]) -> np.ndarray:
    """Binary dot mask from the first ``n`` accepted indices."""
    out = np.zeros(shape, bool)
    if n > 0 and len(order):
        out.ravel()[order[:n]] = True
    return out


def marginal_threshold(current_dti: float, alpha: float = 0.2) -> float:
    """Exact kernel weight above which one additional isolated dot raises DTI.

    ``k* = alpha * DTI`` because the metric denominator is shift-invariant in
    ``k`` (1 - alpha - beta = 0). See the module docstring for the derivation.
    """
    return alpha * float(current_dti)


def coverage_report(dots: np.ndarray, truth: np.ndarray, radius: float = 3.0) -> dict:
    """Kernel coverage of a truth set by a binary dot set (independent of the metric)."""
    from scipy.ndimage import distance_transform_edt

    dots = np.asarray(dots, bool)
    truth = np.asarray(truth, bool)
    n_truth = int(truth.sum())
    if n_truth == 0:
        return {"n_truth": 0, "n_dots": int(dots.sum()), "coverage": 0.0, "mean_k": 0.0}
    if not dots.any():
        return {"n_truth": n_truth, "n_dots": 0, "coverage": 0.0, "mean_k": 0.0}
    dist = distance_transform_edt(~dots)
    k = np.maximum(1.0 - dist[truth] / radius, 0.0)
    return {
        "n_truth": n_truth,
        "n_dots": int(dots.sum()),
        "coverage": float(k.sum() / n_truth),
        "mean_k": float(k.mean()),
    }
