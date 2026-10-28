"""Minimal-mass isolated-dot emitter and measurable emission geometry."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label, uniform_filter

from .grid import KERNEL_RADIUS_PX


def ring(d_cat: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Annulus of catalogue distance: the collar that pays and the halo that does not."""
    return (d_cat >= lo) & (d_cat <= hi)


def masked_rank(score: np.ndarray, support: np.ndarray) -> np.ndarray:
    """Percentile rank of ``score`` restricted to ``support`` (0 outside)."""
    out = np.zeros(score.shape, np.float32)
    v = score[support]
    if v.size == 0:
        return out
    order = np.argsort(v, kind="stable")
    r = np.empty(v.size, np.float32)
    r[order] = np.linspace(0.0, 1.0, v.size, dtype=np.float32)
    out[support] = r
    return out


def select_isolated(
    score: np.ndarray,
    support: np.ndarray,
    budget: int,
    min_sep: float = 3.0,
    seed: int = 0,
    tile_cap: int | None = None,
    tile: int = 160,
) -> np.ndarray:
    """Greedy top-score selection with a hard minimum separation (no clumping).

    ``min_sep`` is Euclidean in pixels.  Ties are broken by a fixed RNG so the
    result is reproducible.  ``tile_cap`` optionally caps emissions per
    ``tile x tile`` window, which forces the field to spread instead of
    saturating the single best ridge.
    """
    H, W = score.shape
    ids = np.flatnonzero(support & np.isfinite(score))
    if ids.size == 0 or budget <= 0:
        return np.zeros((H, W), bool)
    rng = np.random.default_rng(seed)
    jitter = rng.random(ids.size) * 1e-6
    key = -score.ravel()[ids] + jitter
    order = ids[np.argsort(key, kind="stable")]
    taken = np.zeros((H, W), bool)
    blocked = np.zeros((H, W), bool)
    counts: dict[tuple[int, int], int] = {}
    r = int(np.ceil(min_sep))
    n_taken = 0
    for pid in order:
        y, x = divmod(int(pid), W)
        if blocked[y, x]:
            continue
        if tile_cap is not None:
            k = (y // tile, x // tile)
            if counts.get(k, 0) >= tile_cap:
                continue
        taken[y, x] = True
        n_taken += 1
        if tile_cap is not None:
            k = (y // tile, x // tile)
            counts[k] = counts.get(k, 0) + 1
        y0, y1 = max(0, y - r), min(H, y + r + 1)
        x0, x1 = max(0, x - r), min(W, x + r + 1)
        yy, xx = np.ogrid[y0 - y:y1 - y, x0 - x:x1 - x]
        blocked[y0:y1, x0:x1] |= (yy * yy + xx * xx) <= min_sep * min_sep
        if n_taken >= budget:
            break
    return taken


def geometry_features(pred: np.ndarray, d_cat: np.ndarray, cat: np.ndarray) -> dict:
    """The seven measurable emission-geometry features used by the fleet score model."""
    pos = np.asarray(pred, bool)
    m = int(pos.sum())
    if m == 0:
        raise ValueError("cannot describe an empty emission")
    dc = d_cat[pos]
    dd = distance_transform_edt(~pos)
    lbl, ncomp = label(pos, structure=np.ones((3, 3), bool))
    nb = np.rint(uniform_filter(pos.astype(np.float32), size=3, mode="constant") * 9.0 - 1.0)[pos]
    return dict(
        n_dots=m,
        frac_le3=float((dc <= 3).mean()),
        frac_le15=float((dc <= 15).mean()),
        cat_cov3=float((dd[cat] <= 3).mean()),
        dist_p50=float(np.median(dc)),
        dist_p90=float(np.percentile(dc, 90)),
        n_comp=int(ncomp),
        clump=float((nb >= 3).mean()),
        areal_cov3=float((dd <= KERNEL_RADIUS_PX).mean() > 0) * 0.0
        + float(((dd <= KERNEL_RADIUS_PX).sum()) / dd.size),
        within3=float((dd <= KERNEL_RADIUS_PX).sum()),
    )


def halo_covered(truth: np.ndarray, pred: np.ndarray, radius: float = KERNEL_RADIUS_PX) -> float:
    """Fraction of truth pixels within ``radius`` of an emitted pixel."""
    dd = distance_transform_edt(~np.asarray(pred, bool))
    return float((dd[np.asarray(truth, bool)] <= radius).mean())


def dilate(mask: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    r = int(np.ceil(radius))
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    disk = (yy * yy + xx * xx) <= radius * radius
    return binary_dilation(mask, structure=disk)


#: Radial budget of the incumbent 0.2778 raster (measured, see docs/data/fsm1-training.json).
INCUMBENT_RADIAL = np.array([0.0428, 0.0860, 0.1101, 0.1054, 0.1617, 0.1347, 0.1595, 0.2000])
RADIAL_EDGES = (0, 3, 5, 8, 12, 20, 30, 50, 10_000)


def stratified_emission(field, support, d_cat, footprint, total=40000, min_sep=3.0,
                        radial=INCUMBENT_RADIAL, edges=RADIAL_EDGES, seed=0,
                        exclude=None):
    """Emit ``total`` isolated dots with a prescribed catalogue-distance budget.

    The radial quota comes from the measured budget of the best public raster;
    *which* pixels are taken inside each distance band is decided by ``field``.
    This separates "how much mass at each distance" (a public-score-derived
    prior) from "where exactly" (our own structural ranking).
    """
    blocked = np.zeros(field.shape, bool)
    taken = np.zeros(field.shape, bool)
    radial = np.asarray(radial, float)
    radial = radial / radial.sum()
    for b in range(len(edges) - 1):
        lo, hi = edges[b], edges[b + 1]
        band = (d_cat >= lo) & (d_cat < hi) & support & ~blocked
        if exclude is not None:
            band &= ~exclude
        k = int(round(radial[b] * total))
        if k <= 0:
            continue
        sel = select_isolated(field, band, k, min_sep=min_sep, seed=seed + b)
        taken |= sel
        blocked |= dilate(sel, min_sep)
    return taken


def dash_emit(rank, theta, support, budget, half=10.0, step=3.2, seed=0, min_sep=1.0):
    """Grain-aligned dashed emission: seeds walk the local strike at fixed spacing.

    A dot field that ignores the regional grain spends mass on directions in which
    faults do not run.  Walking ``2 * half`` pixels along the local strike from the
    best remaining seed produces short dashes whose length scale (about 21 px,
    2.1 km) is that of a mapped fault segment, and the metric's kernel then credits
    every pixel of that dash's own trace instead of a single point.
    Gates ``support``, the seed rank and the dashes are all deterministic given
    ``seed``.
    """
    H, W = rank.shape
    out = np.zeros((H, W), bool)
    blocked = np.zeros((H, W), bool)
    ids = np.flatnonzero(support & (rank > 0))
    if ids.size == 0 or budget <= 0:
        return out
    rng = np.random.default_rng(seed)
    order = ids[np.argsort(-rank.ravel()[ids] + rng.random(ids.size) * 1e-6)]
    ts = np.arange(-half, half + 1e-9, step)
    n = 0
    q = max(1, int(np.ceil(min_sep)))
    for pid in order:
        if n >= budget:
            break
        y, x = divmod(int(pid), W)
        if blocked[y, x]:
            continue
        th = float(theta[y, x])
        ys = np.rint(y + ts * np.sin(th)).astype(int)
        xs = np.rint(x + ts * np.cos(th)).astype(int)
        ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
        ys, xs = ys[ok], xs[ok]
        keep = ~blocked[ys, xs]
        if not keep.any():
            continue
        ys, xs = ys[keep], xs[keep]
        out[ys, xs] = True
        r = int(max(0, round(min_sep) - 1))
        for yv, xv in zip(ys, xs):
            blocked[max(0, yv - r):yv + r + 1, max(0, xv - r):xv + r + 1] = True
        n += int(len(ys))
    return out
