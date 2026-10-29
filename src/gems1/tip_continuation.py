"""Catalogue-only strike-continuation candidate for the GEMS Prize (WBGGEMSDOE1, 2026-10-29).

Hypothesis (catalogue-geometry only, no feature stack):
    Mapped fault traces in the USGS/INGENIOUS catalogue frequently stop at a
    mapping cut-off rather than at a physical tip. Continuing an elongated
    trace along its own strike, beyond each mapped end, places dots where
    unmapped (concealed or under-mapped) extensions of the same structure
    would lie.

Mechanism of the candidate:
    1. Visible catalogue -> 8-connected trace components (>= 8 px).
    2. Keep only elongated components (PCA eigenvalue ratio >= 3), so that
       blobs with no defined strike are not extrapolated.
    3. From each trace end, march outward along the principal strike from
       2 px to 15 px (200 m to 1.5 km) in 0.5 px steps.
    4. Stop a ray when it leaves the footprint or reaches a point within
       2 px (200 m) of a visible fault. Every emitted dot is therefore strictly
       more than 2 px from the visible catalogue.
    5. Thin so no two dots are 8-adjacent (spacing >= 2 px).

Named non-fault mimic: strike-parallel cultural or hydrological lineaments
(road, pipeline, canal, drainage, claim boundaries) and stratigraphic contacts
that share the trace's trend and happen to end where the mapped fault ends.

Leakage rule: every catalogue-derived quantity uses only the visible faults
passed in. The holdout caller passes each fold's visible set.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, label

MIN_COMPONENT_PX = 8
MIN_ELONGATION = 3.0
RAY_START_PX = 2.0
RAY_END_PX = 15.0
RAY_STEP_PX = 0.5
GATE_PX = 2.0  # dots must satisfy d(visible) > GATE_PX (strict, 200 m)


def _component_tips(visible: np.ndarray):
    """Yield (row, col, outward_dy, outward_dx) for each elongated trace end."""
    comp, n = label(visible, structure=np.ones((3, 3), int))
    if n == 0:
        return
    fy, fx = np.nonzero(comp)
    labels_at = comp[fy, fx]
    order = np.argsort(labels_at, kind="stable")
    fy, fx, labels_at = fy[order], fx[order], labels_at[order]
    bounds = np.searchsorted(labels_at, np.arange(1, n + 2))
    for cid in range(1, n + 1):
        lo, hi = bounds[cid - 1], bounds[cid]
        ys, xs = fy[lo:hi], fx[lo:hi]
        if ys.size < MIN_COMPONENT_PX:
            continue
        X = xs.astype(np.float64) * 100.0
        Y = -ys.astype(np.float64) * 100.0
        mx, my = X.mean(), Y.mean()
        cov = np.cov(np.vstack([X - mx, Y - my]))
        evals, evecs = np.linalg.eigh(cov)
        lam_big, lam_small = evals[1], max(evals[0], 1e-12)
        if lam_big / lam_small < MIN_ELONGATION:
            continue
        uX, uY = evecs[0, 1], evecs[1, 1]  # principal strike, unit vector (metres)
        t = (X - mx) * uX + (Y - my) * uY
        i_max, i_min = int(np.argmax(t)), int(np.argmin(t))
        # pixel-space outward direction for a unit step along +u / -u
        d_plus = (-uY, uX)
        d_minus = (uY, -uX)
        yield int(ys[i_max]), int(xs[i_max]), d_plus
        yield int(ys[i_min]), int(xs[i_min]), d_minus


def generate_dots(visible: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Return a boolean dot mask using only ``visible`` catalogue faults."""
    visible = np.asarray(visible, bool) & footprint
    H, W = footprint.shape
    d_vis = distance_transform_edt(~visible)
    raw = np.zeros((H, W), bool)
    for r0, c0, (dy, dx) in _component_tips(visible):
        started = False
        for s in np.arange(RAY_START_PX, RAY_END_PX + 1e-9, RAY_STEP_PX):
            r = int(round(r0 + s * dy))
            c = int(round(c0 + s * dx))
            if r < 0 or c < 0 or r >= H or c >= W:
                break
            if not footprint[r, c]:
                break
            if not d_vis[r, c] > GATE_PX:
                # buffer zone next to the trace's own tip is skipped; a fault hit after emitting ends the ray
                if started:
                    break
                continue
            started = True
            raw[r, c] = True
    # thin: no two kept dots may be 8-adjacent (spacing >= 2 px)
    out = np.zeros((H, W), bool)
    rr, cc = np.nonzero(raw)
    for r, c in zip(rr.tolist(), cc.tolist()):
        if out[max(r - 1, 0) : r + 2, max(c - 1, 0) : c + 2].any():
            continue
        out[r, c] = True
    return out & footprint & (d_vis > GATE_PX)


def random_null(region: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform random dots inside ``region`` with exactly ``n`` samples (no thinning)."""
    yy, xx = np.nonzero(region)
    out = np.zeros(region.shape, bool)
    if n <= 0 or yy.size == 0:
        return out
    pick = rng.choice(yy.size, size=min(n, yy.size), replace=False)
    out[yy[pick], xx[pick]] = True
    return out
