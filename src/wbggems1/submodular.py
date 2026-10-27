"""Exact 300 m DTI Triangular-Kernel CELF (Minoux Lazy-Greedy) Submodular Emitter.

Official DTI kernel at 100 m pixel spacing has radius R = 300 m = 3.0 px:
    k(d) = max(0.0, 1.0 - d / 3.0)
On integer grid offsets (dr, dc), k(sqrt(dr^2 + dc^2)) > 0 iff dr^2 + dc^2 < 9,
which is strictly the 5x5 neighborhood (dr in -2..2, dc in -2..2; 25 offsets).

Given pixelwise posterior weights w(g) >= 0 (zeroed outside footprint and inside
the dead <= 200 m catalogue collar where hidden positives cannot occur), placing
a unit dot p(x) = 1.0 at x increases expected weighted true positives by:
    Delta(x | C) = sum_{(dr,dc) in 5x5} w(x + (dr,dc)) * max(0, k(dr,dc) - C(x + (dr,dc)))
which is monotone non-decreasing and submodular in the selected set S.
Minoux (1978) accelerated lazy-greedy on a max-heap finds the exact greedy
sequence orders of magnitude faster than naive recomputation.
"""

from __future__ import annotations

import heapq
from typing import Tuple

import numpy as np

# Precompute the exact 25-offset 5x5 positive kernel stencil for R = 3.0 px (300 m).
_STENCIL_DR: list[int] = []
_STENCIL_DC: list[int] = []
_STENCIL_K: list[float] = []
for _dr in range(-2, 3):
    for _dc in range(-2, 3):
        _d = float(np.hypot(_dr, _dc))
        _k = max(0.0, 1.0 - _d / 3.0)
        if _k > 0.0:
            _STENCIL_DR.append(_dr)
            _STENCIL_DC.append(_dc)
            _STENCIL_K.append(_k)

STENCIL_SIZE = len(_STENCIL_DR)  # 25


def initial_marginal_gains(weight_grid: np.ndarray, coverage_grid: np.ndarray | None = None) -> np.ndarray:
    """Vectorized exact marginal gain Delta(x | C) across the full (H, W) grid."""
    h, w = weight_grid.shape
    w_pad = np.pad(np.nan_to_num(weight_grid, nan=0.0).astype(np.float32), 2, mode="constant", constant_values=0.0)
    if coverage_grid is None:
        gains = np.zeros((h, w), dtype=np.float32)
        for dr, dc, kv in zip(_STENCIL_DR, _STENCIL_DC, _STENCIL_K):
            gains += kv * w_pad[2 + dr : 2 + dr + h, 2 + dc : 2 + dc + w]
        return gains

    c_pad = np.pad(coverage_grid.astype(np.float32), 2, mode="constant", constant_values=0.0)
    gains = np.zeros((h, w), dtype=np.float32)
    for dr, dc, kv in zip(_STENCIL_DR, _STENCIL_DC, _STENCIL_K):
        rem = np.maximum(0.0, np.float32(kv) - c_pad[2 + dr : 2 + dr + h, 2 + dc : 2 + dc + w])
        gains += w_pad[2 + dr : 2 + dr + h, 2 + dc : 2 + dc + w] * rem
    return gains


def emit_celf_submodular(
    score_grid: np.ndarray,
    eligible_mask: np.ndarray,
    budget_dots: int,
    *,
    weight_grid: np.ndarray | None = None,
    coverage_init: np.ndarray | None = None,
    min_separation_px: float = 2.25,
    candidate_oversample: int = 9,
) -> Tuple[np.ndarray, np.ndarray]:
    """Select up to `budget_dots` unit dots via Minoux lazy-greedy 300 m kernel coverage.

    Parameters
    ----------
    score_grid:
        (H, W) float32 candidate priority/probability surface used when ranking
        eligible candidates (`eligible_mask == True`).
    eligible_mask:
        (H, W) bool mask of pixels allowed to host dots (e.g. `valid & (d_cat > 2.0)`).
    budget_dots:
        Exact target number of binary `{0.0, 1.0}` dots to place.
    weight_grid:
        Optional (H, W) float32 objective mass `w(g)` over pixels whose coverage
        is rewarded. Defaults to `np.clip(score_grid, 0, None)` inside footprint
        with dead collar zeroed.
    coverage_init:
        Optional (H, W) float32 pre-existing 300 m kernel coverage in `[0, 1]`
        (used by Regime B so it never duplicates Regime A's 300 m disks).
    min_separation_px:
        Hard minimum Euclidean separation between placed dots (`1.45 px` forbids
        8-adjacent clumping while letting CELF adapt spacing from `2.0 px` along
        high-probability scarps up to `4+ px` on diffuse corridors).
    candidate_oversample:
        Pool size multiplier (`budget_dots * candidate_oversample`) admitted into
        the CELF priority queue for fast exact selection.

    Returns
    -------
    emitted : (H, W) float32 binary `{0.0, 1.0}` raster.
    coverage : (H, W) float32 updated 300 m kernel coverage in `[0.0, 1.0]`.
    """
    h, w = score_grid.shape
    emitted = np.zeros((h, w), dtype=np.float32)
    cov = np.zeros((h, w), dtype=np.float32) if coverage_init is None else coverage_init.astype(np.float32).copy()
    if budget_dots <= 0:
        return emitted, cov

    obj_w = (
        np.where(np.isfinite(score_grid), np.maximum(score_grid, 0.0), 0.0).astype(np.float32)
        if weight_grid is None
        else np.where(np.isfinite(weight_grid), np.maximum(weight_grid, 0.0), 0.0).astype(np.float32)
    )
    gains = initial_marginal_gains(obj_w, cov)

    cand_mask = eligible_mask & (gains > 0.0) & np.isfinite(score_grid) & (score_grid > 0.0)
    cand_flat = np.flatnonzero(cand_mask.ravel())
    if cand_flat.size == 0:
        return emitted, cov

    cand_gains = gains.ravel()[cand_flat]
    pool_cap = min(cand_flat.size, max(budget_dots * candidate_oversample, budget_dots + 5000))
    if cand_flat.size > pool_cap:
        top_idx = np.argpartition(cand_gains, -pool_cap)[-pool_cap:]
        cand_flat = cand_flat[top_idx]
        cand_gains = cand_gains[top_idx]

    # Precompute exclusion offsets for min_separation_px
    excl_offsets: list[tuple[int, int]] = []
    if min_separation_px > 0.0:
        rad = int(np.ceil(min_separation_px))
        r2 = min_separation_px * min_separation_px
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                if dr * dr + dc * dc < r2:
                    excl_offsets.append((dr, dc))

    blocked = ~eligible_mask.copy()
    if coverage_init is not None and min_separation_px > 0.0:
        # Block exact centers where coverage_init == 1.0 (dots already placed in Regime A)
        prev_r, prev_c = np.nonzero(coverage_init >= 0.9999)
        for dr, dc in excl_offsets:
            rr = np.clip(prev_r + dr, 0, h - 1)
            cc = np.clip(prev_c + dc, 0, w - 1)
            blocked[rr, cc] = True

    # Build padded arrays (+2 border) to avoid inner-loop boundary branches!
    hp, wp = h + 4, w + 4
    w_pad = np.zeros((hp, wp), dtype=np.float32)
    w_pad[2 : 2 + h, 2 : 2 + w] = obj_w
    c_pad = np.zeros((hp, wp), dtype=np.float32)
    c_pad[2 : 2 + h, 2 : 2 + w] = cov

    w_flat = w_pad.ravel()
    c_flat = c_pad.ravel()
    stencil_flat_dk = [
        (dr * wp + dc, float(kv))
        for dr, dc, kv in zip(_STENCIL_DR, _STENCIL_DC, _STENCIL_K)
    ]

    # Minoux max-heap using negative gain; tie-break deterministically by flat index
    heap: list[tuple[float, int]] = [
        (-float(g), int(idx)) for g, idx in zip(cand_gains, cand_flat)
    ]
    heapq.heapify(heap)

    blocked_u8 = blocked.view(np.uint8)
    selected_count = 0

    while heap and selected_count < budget_dots:
        neg_g, flat_idx = heapq.heappop(heap)
        r = flat_idx // w
        c = flat_idx - r * w
        if blocked_u8[r, c]:
            continue

        p_idx = (r + 2) * wp + (c + 2)
        cur_gain = 0.0
        for d_off, kv in stencil_flat_dk:
            q_idx = p_idx + d_off
            rem = kv - c_flat[q_idx]
            if rem > 0.0:
                cur_gain += w_flat[q_idx] * rem

        if cur_gain <= 0.0:
            continue

        # Lazy-greedy optimality check: is cur_gain >= upper bound of next heap top?
        if not heap or (-cur_gain <= heap[0][0] + 1e-12):
            emitted[r, c] = 1.0
            selected_count += 1
            for d_off, kv in stencil_flat_dk:
                q_idx = p_idx + d_off
                if kv > c_flat[q_idx]:
                    c_flat[q_idx] = kv
            for dr, dc in excl_offsets:
                rr = r + dr
                cc = c + dc
                if 0 <= rr < h and 0 <= cc < w:
                    blocked_u8[rr, cc] = 1
        else:
            heapq.heappush(heap, (-cur_gain, flat_idx))

    cov[:, :] = c_pad[2 : 2 + h, 2 : 2 + w]
    return emitted, cov


def emit_two_regime_submodular(
    score_grid: np.ndarray,
    regime_b_score_grid: np.ndarray,
    eligible_mask: np.ndarray,
    regime_a_mask: np.ndarray,
    total_budget_dots: int,
    *,
    regime_a_fraction: float = 0.72,
    min_separation_px: float = 2.25,
) -> Tuple[np.ndarray, dict[str, int]]:
    """Two-regime sequential 300 m CELF submodular allocation.

    Regime A (`regime_a_fraction`, default 72%): dip-coupled piedmont & scarp ridges.
    Regime B (`1 - regime_a_fraction`, default 28%): low-relief intrabasin, 3DEP LiDAR
    gaps, and hydrothermal transfer zones, conditioned on Regime A's exact `C(g)` grid
    so zero dots are wasted inside already-covered 300 m disks.
    """
    budget_a = int(round(total_budget_dots * regime_a_fraction))

    elig_a = eligible_mask & regime_a_mask
    emit_a, cov_a = emit_celf_submodular(
        score_grid,
        elig_a,
        budget_a,
        weight_grid=score_grid,
        coverage_init=None,
        min_separation_px=min_separation_px,
    )
    n_a = int(np.count_nonzero(emit_a > 0))
    rem_budget = max(0, int(total_budget_dots) - n_a)

    elig_b = eligible_mask & (~regime_a_mask) & (emit_a == 0)
    emit_b, cov_ab = emit_celf_submodular(
        regime_b_score_grid,
        elig_b,
        rem_budget,
        weight_grid=regime_b_score_grid,
        coverage_init=cov_a,
        min_separation_px=min_separation_px,
    )
    combined = np.maximum(emit_a, emit_b).astype(np.float32)
    n_b = int(np.count_nonzero(emit_b > 0))

    # Top-up from remaining global eligible pool if Regime B had fewer candidates than budget_b
    still_needed = int(total_budget_dots) - (n_a + n_b)
    n_topup = 0
    if still_needed > 0:
        emit_top, _ = emit_celf_submodular(
            score_grid,
            eligible_mask & (combined == 0),
            still_needed,
            weight_grid=score_grid,
            coverage_init=cov_ab,
            min_separation_px=min_separation_px,
        )
        combined = np.maximum(combined, emit_top).astype(np.float32)
        n_topup = int(np.count_nonzero(emit_top > 0))

    return combined, {
        "target_total": int(total_budget_dots),
        "regime_a_dots": n_a,
        "regime_b_dots": n_b,
        "topup_dots": n_topup,
        "emitted_total": int(np.count_nonzero(combined > 0)),
    }
