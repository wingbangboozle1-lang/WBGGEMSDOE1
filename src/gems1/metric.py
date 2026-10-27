"""Official Distance-Weighted Tversky Index (DTI) for DrivenData competition 306.

Source (verbatim, problem description page 967, fetched 2026-10-26):
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric

  k(d) = max(1 - d/R, 0), R = 300 m = 3 px at 100 m.
  TP_w = sum_{g in G} max_{x: d(x,g)<=R} p(x) k(d(x,g))
  FP_w = sum_{x: p(x)>0} p(x) [1 - max_{g in G} k(d(x,g))]
  FN_w = |G| - TP_w
  DTI(alpha=0.2, beta=0.8) = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)

Known USGS/INGENIOUS pixels are excluded from scoring
(organizer forum thread 11516).
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA: float = 0.2
BETA: float = 0.8
RADIUS_PX: float = 3.0
EPS: float = 1e-12


def kernel(d, radius: float = RADIUS_PX):
    return np.maximum(1.0 - np.asarray(d, dtype=np.float64) / radius, 0.0)


def _offsets(radius: float = RADIUS_PX):
    r = int(np.ceil(radius))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = float(kernel(np.hypot(dy, dx), radius))
            if k > 0.0:
                out.append((dy, dx, k))
    return out


_OFFS = _offsets()


def dti_binary(pred_bool, truth, valid=None, known=None, alpha: float = ALPHA, beta: float = BETA) -> dict:
    """Exact DTI for binary {0,1} predictions via Euclidean distance transforms."""
    pred_bool = np.asarray(pred_bool, bool)
    truth = np.asarray(truth, bool)
    valid_ = np.ones(pred_bool.shape, bool) if valid is None else np.asarray(valid, bool)
    known_ = np.zeros(pred_bool.shape, bool) if known is None else np.asarray(known, bool)
    active = valid_ & ~known_
    p = pred_bool & active
    g = truth & active
    n = int(g.sum())
    if n == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0, coverage=0.0)
    if not p.any():
        return dict(tp=0.0, fp=0.0, fn=float(n), n_truth=n, dti=0.0, coverage=0.0)
    dp = distance_transform_edt(~p)
    tp = float(kernel(dp[g]).sum())
    fn = float(n) - tp
    dg = distance_transform_edt(~g)
    fp = float((1.0 - kernel(dg[p])).sum())
    dti = tp / (tp + alpha * fp + beta * fn + EPS)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n, dti=float(dti), coverage=tp / n)


def dti_exact(pred, truth, valid=None, known=None, alpha: float = ALPHA, beta: float = BETA) -> dict:
    """Exact DTI for soft predictions in [0, 1]."""
    pred = np.asarray(pred)
    truth = np.asarray(truth)
    valid_ = np.ones(pred.shape, bool) if valid is None else np.asarray(valid, bool)
    known_ = np.zeros(pred.shape, bool) if known is None else np.asarray(known, bool)
    active = valid_ & ~known_
    vals = pred[active]
    if vals.size and (not np.isfinite(vals).all() or (vals < 0).any() or (vals > 1).any()):
        raise ValueError("predictions inside the scored domain must be finite and in [0, 1]")
    p = np.where(active & np.isfinite(pred), pred, 0.0).astype(np.float64)
    g = active & (np.asarray(truth) > 0)
    H, W = p.shape
    yy, xx = np.nonzero(g)
    n = int(yy.size)
    if n == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0, coverage=0.0)
    credit = np.zeros(n, dtype=np.float64)
    for dy, dx, k in _OFFS:
        ny, nx = yy + dy, xx + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        credit[ok] = np.maximum(credit[ok], p[ny[ok], nx[ok]] * k)
    tp = float(credit.sum())
    fn = float(n) - tp
    d = distance_transform_edt(~g)
    fp = float((p * (1.0 - kernel(d))).sum())
    dti = tp / (tp + alpha * fp + beta * fn + EPS)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n, dti=float(dti), coverage=tp / n if n else 0.0)


def dti_bruteforce(pred, truth, alpha: float = ALPHA, beta: float = BETA, radius: float = RADIUS_PX) -> dict:
    """O(|G|*|P|) transcription of the published equations — unit-test oracle only."""
    pred = np.asarray(pred, float)
    truth = np.asarray(truth, bool)
    gs = np.argwhere(truth)
    xs = np.argwhere(pred > 0)
    tp = fn = 0.0
    for g in gs:
        best = 0.0
        for x in xs:
            d = float(np.hypot(*(x - g)))
            if d <= radius:
                best = max(best, pred[tuple(x)] * max(1.0 - d / radius, 0.0))
        tp += best
        fn += 1.0 - best
    fp = 0.0
    for x in xs:
        kmax = 0.0
        for g in gs:
            kmax = max(kmax, max(1.0 - float(np.hypot(*(x - g))) / radius, 0.0))
        fp += pred[tuple(x)] * (1.0 - kmax)
    return dict(tp=tp, fp=fp, fn=fn, dti=tp / (tp + alpha * fp + beta * fn + EPS))
