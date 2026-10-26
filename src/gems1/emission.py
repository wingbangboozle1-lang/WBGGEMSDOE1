"""Sparse emitters: a detector field becomes a legal {0,1} prediction raster.

DTI with alpha=0.2 rewards sparse, well-placed dots. Isolated-pixel break-even
credit is k > alpha * DTI (0.0556 at 0.2778) — a heuristic, never a projected score.
"""
from __future__ import annotations

import numpy as np


def poisson_priority(
    field: np.ndarray,
    support: np.ndarray,
    min_dist: float,
    n_max: int | None = None,
) -> np.ndarray:
    """Priority Poisson-disk: keep highest-field pixels subject to min_dist.

    Distinct from the H19-5 family raster-order cascade (GEMSDOE25/32), which
    walks candidates in ascending raster index and ignores the field.
    """
    ys, xs = np.nonzero(support)
    if ys.size == 0:
        return np.zeros(support.shape, bool)
    order = np.argsort(-np.asarray(field, dtype=np.float64)[ys, xs], kind="mergesort")
    r2 = float(min_dist) * float(min_dist)
    cell = max(1.0, float(min_dist))
    grid: dict = {}
    out = np.zeros(support.shape, bool)
    kept = 0
    n_cap = int(n_max) if n_max is not None else ys.size
    for i in order:
        y, x = int(ys[i]), int(xs[i])
        cy, cx = int(y // cell), int(x // cell)
        ok = True
        for gy in range(cy - 2, cy + 3):
            for gx in range(cx - 2, cx + 3):
                for ky, kx in grid.get((gy, gx), ()):
                    dy, dx = y - ky, x - kx
                    if dy * dy + dx * dx < r2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            out[y, x] = True
            grid.setdefault((cy, cx), []).append((y, x))
            kept += 1
            if kept >= n_cap:
                break
    return out


def nms_ridge(field: np.ndarray, gy: np.ndarray, gx: np.ndarray) -> np.ndarray:
    """Non-maximum suppression along the local gradient (1-px ridge centerline)."""
    H, W = field.shape
    mag = np.hypot(gy, gx) + 1e-12
    ny = np.clip(np.round(gy / mag).astype(np.int32), -1, 1)
    nx = np.clip(np.round(gx / mag).astype(np.int32), -1, 1)
    yy, xx = np.ogrid[:H, :W]
    y1 = np.clip(yy + ny, 0, H - 1)
    x1 = np.clip(xx + nx, 0, W - 1)
    y2 = np.clip(yy - ny, 0, H - 1)
    x2 = np.clip(xx - nx, 0, W - 1)
    return (field >= field[y1, x1]) & (field >= field[y2, x2]) & (field > 0)


def top_quantile(field: np.ndarray, q: float, footprint: np.ndarray) -> np.ndarray:
    vals = field[footprint]
    if vals.size == 0:
        return np.zeros(field.shape, bool)
    tau = np.quantile(vals, 1.0 - q)
    return footprint & (field >= tau)
