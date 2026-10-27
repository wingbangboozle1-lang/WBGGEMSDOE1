"""Retired WBG-2 metric cross-check; not the authoritative evaluation path.

This historical implementation was transcribed from the organizer problem
page. It is retained for archived arithmetic and unit tests only. It must not
be used for holdout scoring, promotion, or organizer-score claims; any newly
authorized lane must use the pinned shared evaluator in ``vendor/gems57``.
Manual-review source: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/

    TI(a,b) = sum_x p(x)g(x) /
              ( sum_x p(x)g(x) + a*sum_x p(x)(1-g(x)) + b*sum_x (1-p(x))g(x) )

    k(d) = max(1 - d/R, 0),  R = 300 m

    TP_w = sum_{g in G} max_{x: d(x,g) <= R} p(x) k(d(x,g))
    FP_w = sum_{x: p(x) > 0} p(x) [1 - max_{g in G} k(d(x,g))]
    FN_w = sum_{g in G} [1 - max_{x: d(x,g) <= R} p(x) k(d(x,g))]

    DTI(a,b) = TP_w / (TP_w + a*FP_w + b*FN_w + eps)

with a = 0.2 (false-positive penalty) and b = 0.8 (false-negative penalty).

Implementation notes
--------------------
The organizer equations are defined on the full grid. We use an exact separable
distance transform which is O(N) per source set, so the metric is computed on the
whole 3730x3292 grid rather than on a crop.

`R` is expressed in pixels because the grid is exactly 100 m. R = 3 px = 300 m.
The kernel argument d/R is therefore d_px/3.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

#: Triangular kernel support, in metres (organizer text: R = 300 m).
R_METRES = 300.0
#: Grid posting, in metres. The competition grid is 100 m.
PIXEL_METRES = 100.0
#: Kernel support in pixels.
R_PIXELS = R_METRES / PIXEL_METRES
#: Organizer alpha (false-positive weight).
ALPHA = 0.2
#: Organizer beta (false-negative weight).
BETA = 0.8
#: Organizer epsilon (guards a fully empty denominator).
EPS = 1e-9


def triangular_kernel(distance_px: np.ndarray) -> np.ndarray:
    """k(d) = max(1 - d/R, 0) with R = 3 px. Values outside support are 0."""
    return np.maximum(1.0 - np.asarray(distance_px, dtype=np.float64) / R_PIXELS, 0.0)


def _distance_to(points: np.ndarray, region: np.ndarray) -> np.ndarray:
    """Euclidean distance (in px) from every pixel of `region` to the nearest
    True pixel of `points`. Returns +inf where `points` is empty."""
    if not points.any():
        return np.full(region.shape, np.inf, dtype=np.float64)
    # distance_transform_edt returns the distance to the nearest *zero* pixel,
    # so we invert: pixels that are True in `points` become 0 distance.
    return ndi.distance_transform_edt(~points).astype(np.float64)


def dti(
    prediction: np.ndarray,
    truth: np.ndarray,
    footprint: np.ndarray | None = None,
    alpha: float = ALPHA,
    beta: float = BETA,
    profile: bool = False,
):
    """Distance-weighted Tversky index.

    Parameters
    ----------
    prediction
        float array in [0, 1]. Non-finite cells are treated as 0 (no prediction)
        and reported separately by the caller's validator; the metric itself
        never silently rewrites the caller's file.
    truth
        boolean array, the ground-truth positives.
    footprint
        boolean array of cells the organizers will score. Cells outside it are
        ignored. Defaults to all cells.
    profile
        when True, also return the weighted components.

    Returns
    -------
    dti : float
    components : dict (only when profile=True)
    """
    p = np.asarray(prediction, dtype=np.float64)
    g = np.asarray(truth, dtype=bool)
    if p.shape != g.shape:
        raise ValueError(f"shape mismatch: prediction {p.shape} vs truth {g.shape}")
    if footprint is None:
        footprint = np.ones(p.shape, dtype=bool)
    footprint = np.asarray(footprint, dtype=bool)

    # The organizer defines the sums over the scored grid only.
    p = np.where(footprint & np.isfinite(p), np.clip(p, 0.0, 1.0), 0.0)
    g = g & footprint

    gt_points = g
    pred_points = p > 0.0

    # d(x, g): distance from every predicted cell to the nearest ground-truth pixel.
    d_pred_to_gt = _distance_to(gt_points, p.shape)

    # FP_w: each predicted cell pays (1 - k) of its own probability.
    pred_w = p * (1.0 - triangular_kernel(d_pred_to_gt))
    pred_w = np.where(pred_points & footprint, pred_w, 0.0)
    fp_w = float(pred_w.sum())

    # m_g = max over predicted cells x within R of p(x) * k(d(x,g)).
    gt_ys, gt_xs = np.nonzero(gt_points)
    tp_w = 0.0
    if pred_points.any() and gt_ys.size:
        weight = np.where(pred_points, p, 0.0)
        rad = int(np.ceil(R_PIXELS))
        padded = np.zeros((p.shape[0] + 2 * rad, p.shape[1] + 2 * rad), dtype=np.float64)
        padded[rad:rad + p.shape[0], rad:rad + p.shape[1]] = weight
        best = np.zeros(gt_ys.size, dtype=np.float64)
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                k = 1.0 - np.hypot(dy, dx) / R_PIXELS
                if k <= 0.0:
                    continue
                vals = padded[gt_ys + rad + dy, gt_xs + rad + dx] * k
                np.maximum(best, vals, out=best)
        tp_w = float(best.sum())
    fn_w = float(gt_ys.size) - tp_w
    denom = tp_w + alpha * fp_w + beta * fn_w + EPS
    value = tp_w / denom

    if not profile:
        return value
    return value, {
        "tp_w": tp_w,
        "fp_w": fp_w,
        "fn_w": fn_w,
        "denominator": denom,
        "gt_pixels": int(gt_points.sum()),
        "predicted_pixels": int(pred_points.sum()),
        "alpha": alpha,
        "beta": beta,
        "r_pixels": R_PIXELS,
    }
