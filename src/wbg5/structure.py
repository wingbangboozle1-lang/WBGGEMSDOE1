"""Catalogue structural geometry: components, tips, strike and tip/step-over corridors.

Why this exists
---------------
Normal faults in the Great Basin are segmented.  Where the publicly mapped
catalogue is incomplete, unmapped (expert-added) faults are expected
preferentially at (i) along-strike continuations beyond a mapped tip and
(ii) en-echelon step-overs / relay zones between overlapping segments
(Caine et al. 1996, damage zones; Faulds & Varga 1998, step-overs and fluid
flow; Kim & Sanderson 2005, fault linkage).  This module turns that qualitative
geology into a deterministic field computed only from *visible* catalogue
geometry, so it can be tested with hide-and-recover.

Nothing here reads labels, hidden data or another submission's pixels.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import gaussian_filter, label
from scipy.spatial import cKDTree

EIGHT = np.ones((3, 3), bool)


@dataclass
class Segment:
    label_id: int
    n_px: int
    centroid: tuple[float, float]
    unit: tuple[float, float]
    strike_deg: float
    tip_a: tuple[int, int]
    tip_b: tuple[int, int]
    length_px: float


@dataclass
class Geometry:
    segments: list[Segment]
    strike_hist: dict[str, int] = field(default_factory=dict)


def _pca(ys: np.ndarray, xs: np.ndarray) -> tuple[float, float, float, float]:
    cy, cx = float(ys.mean()), float(xs.mean())
    dy, dx = ys - cy, xs - cx
    cov = np.cov(np.vstack([dy, dx])) if len(ys) > 1 else np.eye(2)
    w, v = np.linalg.eigh(cov)
    u = v[:, int(np.argmax(w))]
    if u[0] < 0 or (u[0] == 0 and u[1] < 0):
        u = -u
    return cy, cx, float(u[0]), float(u[1])


def segments_from_mask(mask: np.ndarray, min_px: int = 8) -> Geometry:
    """Decompose a binary fault mask into line segments with two tips each."""
    lbl, n = label(mask, structure=EIGHT)
    if n == 0:
        return Geometry(segments=[])
    W = mask.shape[1]
    idx = np.flatnonzero(mask.ravel())
    comp = lbl.ravel()[idx]
    order = np.argsort(comp, kind="stable")
    idx, comp = idx[order], comp[order]
    bounds = np.searchsorted(comp, np.arange(1, n + 2))
    segs: list[Segment] = []
    strikes: list[float] = []
    for k in range(n):
        sel = idx[bounds[k]:bounds[k + 1]]
        if len(sel) < min_px:
            continue
        ys, xs = (sel // W).astype(float), (sel % W).astype(float)
        cy, cx, dy, dx = _pca(ys, xs)
        t = (ys - cy) * dy + (xs - cx) * dx
        i0, i1 = int(np.argmin(t)), int(np.argmax(t))
        strike = float(np.degrees(np.arctan2(dx, -dy))) % 180.0
        segs.append(Segment(k + 1, int(len(sel)), (cy, cx), (dy, dx), strike,
                            (int(ys[i1]), int(xs[i1])), (int(ys[i0]), int(xs[i0])),
                            float(t.max() - t.min())))
        strikes.append(strike)
    hist = {}
    if strikes:
        bins = np.histogram(strikes, bins=np.arange(0, 181, 15))[0]
        hist = {f"{i * 15:03d}-{i * 15 + 15:03d}": int(c) for i, c in enumerate(bins)}
    return Geometry(segments=segs, strike_hist=hist)


def _splat_add(f: np.ndarray, y: np.ndarray, x: np.ndarray, w: np.ndarray) -> None:
    """Vectorised bilinear splat with a bounds-safe clip (weights may repeat)."""
    H, W = f.shape
    ok = (y >= 0) & (y < H - 1) & (x >= 0) & (x < W - 1)
    if not np.any(ok):
        return
    y, x, w = y[ok], x[ok], w[ok]
    y0, x0 = np.floor(y).astype(np.int64), np.floor(x).astype(np.int64)
    fy, fx = y - y0, x - x0
    flat = f.reshape(-1)
    base = y0 * W + x0
    for dy, dx, wt in ((0, 0, (1 - fy) * (1 - fx)), (0, 1, (1 - fy) * fx),
                       (1, 0, fy * (1 - fx)), (1, 1, fy * fx)):
        np.add.at(flat, base + dy * W + dx, w * wt)


def tip_corridors(
    geom: Geometry,
    shape: tuple[int, int],
    extend_px: float = 30.0,
    start_px: float = 0.0,
    perp_sigma: float = 1.5,
    gap_min_px: float = 4.0,
    gap_max_px: float = 30.0,
    angle_tol_deg: float = 40.0,
    decay: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Field maximal at mapped tips, decaying along strike; plus relay bridges.

    Returns ``(field, support)`` with values in [0, 1] and a boolean support mask.
    ``start_px`` suppresses the first few pixels beyond a tip: a mapped fault's
    own mapping tolerance is not a new fault.
    """
    H, W = shape
    f = np.zeros((H, W), np.float32)
    norm = np.zeros((H, W), np.float32)
    if not geom.segments:
        return f, norm > 0

    tips, dirs, comps = [], [], []
    for s in geom.segments:
        cy, cx = s.centroid
        for tip in (s.tip_a, s.tip_b):
            vy, vx = tip[0] - cy, tip[1] - cx
            n = float(np.hypot(vy, vx)) or 1.0
            tips.append((tip[0], tip[1]))
            dirs.append((vy / n, vx / n))
            comps.append(s.label_id)
    tips = np.asarray(tips, float)
    dirs = np.asarray(dirs, float)
    comps = np.asarray(comps)

    # along-strike continuation
    t = np.arange(start_px, extend_px + 1.0)
    if t.size == 0:
        t = np.asarray([extend_px], float)
    w_t = np.exp(-decay * (t - start_px) / max(extend_px - start_px, 1.0))
    offs = np.arange(-3, 4, dtype=float)
    w_o = np.exp(-0.5 * (offs / perp_sigma) ** 2)
    perp_y, perp_x = -dirs[:, 1], dirs[:, 0]
    for i in range(tips.shape[0]):
        if w_t[0] <= 0:
            continue
        ys = tips[i, 0] + dirs[i, 0] * t[:, None] + perp_y[i] * offs[None, :]
        xs = tips[i, 1] + dirs[i, 1] * t[:, None] + perp_x[i] * offs[None, :]
        ws = np.broadcast_to(w_t[:, None] * w_o[None, :], ys.shape)
        _splat_add(f, ys.ravel(), xs.ravel(), ws.ravel())
        _splat_add(norm, ys.ravel(), xs.ravel(), np.broadcast_to(w_o[None, :], ys.shape).ravel())

    # en-echelon step-overs / relay zones between different segments
    tree = cKDTree(tips)
    pairs = tree.query_pairs(r=gap_max_px, output_type="ndarray")
    if len(pairs):
        d = np.hypot(*(tips[pairs[:, 0]] - tips[pairs[:, 1]]).T)
        keep = (d >= gap_min_px) & (comps[pairs[:, 0]] != comps[pairs[:, 1]])
        dot = np.abs(np.sum(dirs[pairs[:, 0]] * dirs[pairs[:, 1]], axis=1))
        keep &= dot >= np.cos(np.deg2rad(90 - angle_tol_deg))
        for i, j in pairs[keep]:
            k = np.linspace(0, 1, max(int(2 * np.hypot(*(tips[j] - tips[i]))), 4))
            ys = tips[i, 0] + (tips[j, 0] - tips[i, 0]) * k
            xs = tips[i, 1] + (tips[j, 1] - tips[i, 1]) * k
            ws = 0.6 * np.sin(np.pi * k)
            _splat_add(f, ys, xs, ws)
            _splat_add(norm, ys, xs, np.ones_like(ws))
    out = np.where(norm > 1e-6, f / np.maximum(norm, 1e-6), 0.0)
    peak = float(out.max())
    return ((out / peak) if peak > 0 else out).astype(np.float32), norm > 0


def strike_density(geom: Geometry, shape: tuple[int, int], sigma: float = 12.0) -> np.ndarray:
    """Smoothed, strike-weighted density of mapped segments in [0, 1]."""
    H, W = shape
    dens = np.zeros((H, W), np.float32)
    hist = geom.strike_hist or {"000-015": 1}
    total = max(sum(hist.values()), 1)
    for s in geom.segments:
        key = f"{int(s.strike_deg // 15) * 15:03d}-{int(s.strike_deg // 15) * 15 + 15:03d}"
        y, x = int(s.centroid[0]), int(s.centroid[1])
        if 0 <= y < H and 0 <= x < W:
            dens[y, x] += hist.get(key, 1) / total * s.n_px
    dens = gaussian_filter(dens, sigma)
    m = float(dens.max())
    return (dens / m if m > 0 else dens).astype(np.float32)


def strike_field(shape: tuple[int, int], geom=None, block: int = 8, sigma: float = 3.0):
    """Smoothed local grain orientation (double-angle vector field) and its strength.

    Every catalogue segment contributes ``length * (cos 2θ, sin 2θ)`` to the block
    containing it, so the result is a length-weighted mean orientation that does
    not blow up where many short segments disagree.  Returned angles are in
    radians measured from +x (east) counter-clockwise in array coordinates
    (row index grows southward, matching the GeoTIFF's north-up transform).
    """
    H, W = shape
    nb_y, nb_x = H // block + 2, W // block + 2
    C = np.zeros((nb_y, nb_x), np.float64)
    S = np.zeros((nb_y, nb_x), np.float64)
    for seg in geom.segments:
        (ay, ax), (by, bx) = seg.tip_a, seg.tip_b
        y0, x0, y1, x1 = ay / block, ax / block, by / block, bx / block
        n = int(max(abs(y1 - y0), abs(x1 - x0))) + 1
        ys = np.linspace(y0, y1, n).astype(int).clip(0, nb_y - 1)
        xs = np.linspace(x0, x1, n).astype(int).clip(0, nb_x - 1)
        th = np.arctan2(seg.unit[0], seg.unit[1])
        C[ys, xs] += seg.length_px * np.cos(2 * th)
        S[ys, xs] += seg.length_px * np.sin(2 * th)
    Cs = gaussian_filter(C, sigma, mode="nearest")
    Ss = gaussian_filter(S, sigma, mode="nearest")
    strength = np.hypot(Cs, Ss)
    theta = 0.5 * np.arctan2(Ss, Cs)
    # upsample block grid to pixels
    yy = np.minimum((np.arange(H) // block), nb_y - 1)
    xx = np.minimum((np.arange(W) // block), nb_x - 1)
    return theta[yy][:, xx].astype(np.float32), strength[yy][:, xx].astype(np.float32)
