"""Priority Poisson-disk emission + budget helpers."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt


def top_n_mask(surface: np.ndarray, allowed: np.ndarray, n: int) -> np.ndarray:
    surface = np.asarray(surface, dtype=np.float64)
    allowed = np.asarray(allowed, dtype=bool)
    vals = surface[allowed]
    if len(vals) == 0 or n <= 0:
        return np.zeros(surface.shape, dtype=bool)
    n = min(n, len(vals))
    order = np.argpartition(vals, len(vals) - n)[len(vals) - n:]
    yy, xx = np.nonzero(allowed)
    out = np.zeros(surface.shape, dtype=bool)
    out[yy[order], xx[order]] = True
    return out


def poisson_disk_thin_priority(
    surface: np.ndarray,
    allowed: np.ndarray,
    min_dist_px: float,
    max_dots: int,
    existing: np.ndarray | None = None,
    seed: int = 0,
) -> np.ndarray:
    """Greedy priority-ordered Poisson-disk thinning (grid-hash accel).

    Candidates sorted by surface desc (ties broken by seeded shuffle); a
    candidate is kept iff no kept/existing dot lies within min_dist_px.
    Deterministic given surface + seed.
    """
    surface = np.asarray(surface, dtype=np.float64)
    allowed = np.asarray(allowed, dtype=bool).copy()
    if existing is not None:
        allowed &= ~np.asarray(existing, dtype=bool)
    yy, xx = np.nonzero(allowed)
    if len(yy) == 0 or max_dots <= 0:
        return np.zeros(surface.shape, dtype=bool)
    rng = np.random.default_rng(seed)
    score = surface[yy, xx]
    jitter = rng.random(len(score)) * 1e-12
    order = np.argsort(-(score + jitter), kind="mergesort")
    yy, xx = yy[order], xx[order]

    cell = max(min_dist_px, 1e-6)
    grid: dict[tuple[int, int], list[tuple[int, int]]] = {}
    if existing is not None:
        ey, ex = np.nonzero(np.asarray(existing, dtype=bool))
        for y, x in zip(ey.tolist(), ex.tolist()):
            grid.setdefault((int(y // cell), int(x // cell)), []).append((y, x))
    out = np.zeros(surface.shape, dtype=bool)
    r2 = min_dist_px * min_dist_px
    kept = 0
    span = int(np.ceil(min_dist_px / cell)) + 1
    for y, x in zip(yy.tolist(), xx.tolist()):
        if kept >= max_dots:
            break
        cy, cx = int(y // cell), int(x // cell)
        ok = True
        for gy in range(cy - span, cy + span + 1):
            for gx in range(cx - span, cx + span + 1):
                for ky, kx in grid.get((gy, gx), ()):
                    if (y - ky) ** 2 + (x - kx) ** 2 < r2:
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
    return out


def flank_allowed(foot: np.ndarray, labels: np.ndarray, flank_px: float) -> np.ndarray:
    """Footprint minus catalogue flank (dist to labels < flank_px excluded)."""
    foot = np.asarray(foot, dtype=bool)
    labels = np.asarray(labels, dtype=bool)
    if flank_px <= 0 or not labels.any():
        return foot & ~labels
    d = distance_transform_edt(~labels)
    return foot & (d >= flank_px)
