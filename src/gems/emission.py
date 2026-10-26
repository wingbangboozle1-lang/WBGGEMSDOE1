"""Calibrated emission: kernel-cover thinning and truth-density calibration.

Official metric (DrivenData problem page): with kernel ``k(d)=max(1-d/300 m,0)``

    DTI = TPw / (alpha*(TPw + FPw) + beta*|G|),    alpha=0.2, beta=0.8,

because ``TPw + FNw = |G|``.  ``FPw`` is linear in emitted mass.  When the hidden
truth is sparse relative to the emitted pixels, ``0.2*N`` dominates the
denominator and **an emission that keeps most of the kernel credit with far
fewer pixels raises DTI** without any new detector.  This module provides

* ``kernel_cover_thin`` - deterministic greedy facility-location cover of a
  binary raster by a subset, using the exact metric kernel;
* ``random_thin`` - the control with identical pixel count;
* ``lattice_truth_density`` - hidden truth density from the reported score of a
  *blind* uniform lattice (its expected credit is independent of truth layout);
* ``implied_credit`` / ``model_dti`` - the first-order DTI model used to
  extrapolate a thinned raster from a known score.

All of this is a model, not a measurement of hidden labels.  Its assumptions
(blind lattice, FP mass ~ N, stable truth density) are stated by the callers and
recorded in ``evidence/emission_calibration.json``.
"""

from __future__ import annotations

import heapq

import numpy as np
from scipy.ndimage import distance_transform_edt

from .metric import ALPHA, BETA, RADIUS_PX


def kernel_credit(mask: np.ndarray, radius: float = RADIUS_PX) -> np.ndarray:
    """``max_x k(d(x, pixel))`` for every grid cell given binary ``mask`` (empty -> zeros)."""
    mask = np.asarray(mask, bool)
    if not mask.any():
        return np.zeros(mask.shape, np.float64)
    return np.maximum(1.0 - distance_transform_edt(~mask) / radius, 0.0)


def _neighbour_table(ys: np.ndarray, xs: np.ndarray, shape, radius: float):
    h, w = shape
    n = len(ys)
    idxmap = np.full(shape, -1, np.int32)
    idxmap[ys, xs] = np.arange(n, dtype=np.int32)
    r = int(np.ceil(radius))
    offs, kern = [], []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = max(1.0 - float(np.hypot(dy, dx)) / radius, 0.0)
            if k > 0.0:
                offs.append((dy, dx))
                kern.append(k)
    nbr = np.full((n, len(offs)), -1, np.int32)
    for j, (dy, dx) in enumerate(offs):
        yy, xx = ys + dy, xs + dx
        ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
        col = np.full(n, -1, np.int32)
        col[ok] = idxmap[yy[ok], xx[ok]]
        nbr[:, j] = col
    return nbr, np.asarray(kern, np.float64)


def kernel_cover_thin(
    mask: np.ndarray,
    keep_fraction: float,
    *,
    weights: np.ndarray | None = None,
    radius: float = RADIUS_PX,
) -> np.ndarray:
    """Greedy facility-location subset of ``mask`` that maximises triangular-kernel cover.

    Every pixel of ``mask`` is a *demand* point (weight ``weights`` or 1); selecting a pixel
    ``x`` covers demand ``y`` with ``k(d(x,y))``.  The returned subset has
    ``round(keep_fraction * n)`` pixels.  Deterministic: ties are broken by flat index.
    The subset is always contained in ``mask``.
    """
    mask = np.asarray(mask, bool)
    if mask.ndim != 2:
        raise ValueError("2D mask required")
    if not 0.0 < keep_fraction <= 1.0:
        raise ValueError("keep_fraction must be in (0, 1]")
    ys, xs = np.nonzero(mask)
    n = len(ys)
    if n == 0 or keep_fraction >= 1.0:
        return mask.copy()
    target = max(1, int(round(keep_fraction * n)))
    if target >= n:
        return mask.copy()
    nbr, kern = _neighbour_table(ys, xs, mask.shape, radius)
    if weights is None:
        w = np.ones(n, np.float64)
    else:
        weights = np.asarray(weights, np.float64)
        if (
            weights.shape != mask.shape
            or not np.isfinite(weights[mask]).all()
            or (weights[mask] < 0).any()
        ):
            raise ValueError("weights must be a finite nonnegative grid aligned with the mask")
        w = weights[ys, xs]
    valid = nbr >= 0
    safe = np.where(valid, nbr, 0)
    gain0 = (np.where(valid, w[safe], 0.0) * kern[None, :]).sum(axis=1)
    cover = np.zeros(n, np.float64)
    heap = [(-float(g), int(i)) for i, g in enumerate(gain0)]
    heapq.heapify(heap)
    chosen: list[int] = []
    while heap and len(chosen) < target:
        neg, i = heapq.heappop(heap)
        nb = nbr[i]
        ok = nb >= 0
        idx = nb[ok]
        kv = kern[ok]
        gain = float((w[idx] * np.maximum(kv - cover[idx], 0.0)).sum())
        if heap and gain < -heap[0][0] - 1e-12:
            heapq.heappush(heap, (-gain, i))
            continue
        if gain <= 0.0:
            break
        chosen.append(i)
        cover[idx] = np.maximum(cover[idx], kv)
    out = np.zeros_like(mask)
    sel = np.asarray(chosen, np.int64)
    out[ys[sel], xs[sel]] = True
    return out


def random_thin(mask: np.ndarray, keep_fraction: float, seed: int) -> np.ndarray:
    """Uniform random subset with the same pixel count as ``kernel_cover_thin`` (control)."""
    mask = np.asarray(mask, bool)
    if not 0.0 < keep_fraction <= 1.0:
        raise ValueError("keep_fraction must be in (0, 1]")
    ys, xs = np.nonzero(mask)
    n = len(ys)
    out = np.zeros_like(mask)
    if n == 0:
        return out
    target = max(1, int(round(keep_fraction * n)))
    pick = np.random.default_rng(seed).choice(n, size=min(target, n), replace=False)
    out[ys[pick], xs[pick]] = True
    return out


def lattice_truth_density(
    lattice: np.ndarray,
    footprint: np.ndarray,
    known: np.ndarray,
    reported_score: float,
    *,
    alpha: float = ALPHA,
    beta: float = BETA,
    fp_proximity: float = 0.0,
) -> dict[str, float]:
    """Hidden truth density ``tau = |G| / |footprint|`` from a blind lattice's reported DTI.

    ``S = m*tau / (alpha*(m*tau + a*(1-eps)) + beta*tau)`` with ``a`` the emitted off-catalogue
    density, ``m`` the mean kernel credit over off-catalogue footprint cells (the expected credit
    of a truth pixel placed independently of the lattice phase) and ``eps`` the (small) mean
    proximity of lattice pixels to truth.
    """
    lattice = np.asarray(lattice, bool)
    footprint = np.asarray(footprint, bool)
    known = np.asarray(known, bool)
    if not 0.0 < reported_score < 1.0:
        raise ValueError("reported_score must be in (0, 1)")
    emitted = lattice & footprint & ~known
    if not emitted.any():
        raise ValueError("lattice has no off-catalogue pixels")
    area = footprint.sum()
    a = float(emitted.sum() / area)
    credit = kernel_credit(emitted)
    m = float(credit[footprint & ~known].mean())
    denom = (1.0 - alpha * reported_score) * m - beta * reported_score
    if denom <= 0:
        raise ValueError("reported score is not attainable by an unskilled lattice of this density")
    tau = alpha * reported_score * a * (1.0 - fp_proximity) / denom
    return {
        "emitted_px": int(emitted.sum()),
        "emitted_density": a,
        "mean_kernel_credit": m,
        "tau": float(tau),
        "truth_px_equivalent": float(tau * area),
    }


def implied_credit(
    dti: float, n_per_area: float, tau: float, *, phi: float = 0.05, alpha=ALPHA, beta=BETA
) -> float:
    """Kernel-weighted TP per footprint cell implied by a reported DTI under the first-order model.

    ``DTI = TP / (alpha*(TP + N(1-phi)) + beta*tau)`` solved for TP.  ``phi`` is the mean
    kernel proximity of emitted pixels to truth (default 5 %, sensitivity-tested by callers).
    """
    if not 0.0 <= dti < 1.0 / alpha:
        raise ValueError("dti out of range")
    return dti * (alpha * n_per_area * (1.0 - phi) + beta * tau) / (1.0 - alpha * dti)


def model_dti(
    tp_per_area: float, n_per_area: float, tau: float, *, phi: float = 0.05, alpha=ALPHA, beta=BETA
) -> float:
    """First-order DTI for a raster with credit mass ``tp`` and ``n`` emitted pixels per cell."""
    fp = n_per_area * (1.0 - phi)
    return tp_per_area / (alpha * (tp_per_area + fp) + beta * tau)


def extrapolate_variant(
    base_dti: float,
    base_n: int,
    variant_n: int,
    retention: float,
    area: int,
    tau: float,
    *,
    phi: float = 0.05,
) -> float:
    """Model-based DTI of a thinned variant given the base score and kernel-credit retention."""
    if not 0.0 <= retention <= 1.0:
        raise ValueError("retention must be in [0, 1]")
    tp = implied_credit(base_dti, base_n / area, tau, phi=phi)
    return model_dti(retention * tp, variant_n / area, tau, phi=phi)


def priority_poisson(score, eligible, budget, *, min_dist=3.0):
    """Deterministic rank-first Poisson dots from a new physical surface.

    Never adds zero-valued backfill, never reads labels or old predictions.
    Catalogue exclusion is the caller's explicit eligibility mask.
    """
    score, eligible = np.asarray(score), np.asarray(eligible, bool)
    if (
        score.ndim != 2
        or eligible.shape != score.shape
        or not isinstance(budget, (int, np.integer))
        or budget < 0
        or not np.isfinite(min_dist)
        or min_dist < 1
    ):
        raise ValueError("Aligned 2D grids, nonnegative budget and >=1 px spacing required")
    ids = np.flatnonzero(eligible & np.isfinite(score) & (score > 0))
    order = ids[np.lexsort((ids, -score.ravel()[ids]))]
    r = int(np.ceil(min_dist))
    h, w = score.shape
    blocked = np.zeros((h + 2 * r, w + 2 * r), bool)
    result = np.zeros(score.shape, bool)
    offsets = [
        (dy, dx)
        for dy in range(-r, r + 1)
        for dx in range(-r, r + 1)
        if dy * dy + dx * dx < min_dist * min_dist
    ]
    count = 0
    if budget == 0:
        return result
    for i in order:
        y, x = divmod(int(i), w)
        by, bx = y + r, x + r
        if blocked[by, bx]:
            continue
        result[y, x] = True
        count += 1
        for dy, dx in offsets:
            blocked[by + dy, bx + dx] = True
        if count == budget:
            break
    return result
