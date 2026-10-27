"""TIP1: catalogue-independent, orientation-following scarp-tip response.

This module implements the three fixed arms preregistered before implementation in
``research/00_ranked_hypotheses.md``. It never reads a catalogue or an older
prediction. The catalogue belongs only to the shared holdout evaluator.
"""

from __future__ import annotations

import numpy as np

BANDS = {
    "step_max": (3, 1.0, "sqrt"),
    "lapneg_max": (4, 0.05, "sqrt"),
    "lappos_max": (5, 0.05, "sqrt"),
    "downface_max": (6, 1.0, "sqrt"),
    "upface_max": (7, 1.0, "sqrt"),
    "cross_max": (8, 1.0, "sqrt"),
    "coh100": (10, 1.0, "linear"),
    "strike": (11, 180.0, "linear"),
    "valid": (12, 1.0, "linear"),
}
ARM_NAMES = {
    "A": "amplitude_control",
    "B": "tip_gradient_primary",
    "C": "scale_persistence_ablation",
}


def decode(q: np.ndarray, maximum: float, encoding: str) -> np.ndarray:
    """Invert the fixed uint8 quantization documented by the source metadata."""
    q = np.asarray(q)
    if q.dtype != np.uint8 or maximum <= 0 or encoding not in {"sqrt", "linear"}:
        raise ValueError("uint8 input, positive maximum and a known encoding are required")
    unit = np.clip((q.astype(np.float32) - 1.0) / 254.0, 0.0, 1.0)
    if encoding == "sqrt":
        unit *= unit
    value = unit * np.float32(maximum)
    value[q == 0] = 0.0
    return value.astype(np.float32, copy=False)


def fixed_support(encoded: dict[str, np.ndarray], footprint: np.ndarray) -> np.ndarray:
    """Require all locked channels and >50% valid LiDAR support in the cell."""
    fp = np.asarray(footprint)
    if fp.ndim != 2 or fp.dtype != bool or not fp.any():
        raise ValueError("Nonempty 2D boolean footprint required")
    support = fp.copy()
    for name, (_band, maximum, encoding) in BANDS.items():
        q = np.asarray(encoded[name])
        if q.shape != fp.shape or q.dtype != np.uint8:
            raise ValueError(f"Aligned uint8 source required: {name}")
        support &= q > 0
        if name == "valid":
            support &= decode(q, maximum, encoding) > 0.5
    return support


def axial_delta(
    coherence: np.ndarray,
    strike_degrees: np.ndarray,
    support: np.ndarray,
    offset_px: int,
    *,
    chunk_rows: int = 256,
) -> np.ndarray:
    """Absolute end-to-end coherence contrast at ±offset along local axial strike.

    Strike is treated as an axial bearing clockwise from grid north. Integer-cell
    nearest sampling is deliberate: inputs are 100 m cell aggregates, and the
    registered offsets are integer cells. A response is zero unless both endpoints
    have complete LiDAR support, preventing coverage-edge artifacts.
    """
    coh = np.asarray(coherence, np.float32)
    strike = np.asarray(strike_degrees, np.float32)
    ok = np.asarray(support, bool)
    if (
        coh.shape != strike.shape
        or coh.shape != ok.shape
        or coh.ndim != 2
        or isinstance(offset_px, bool)
        or not isinstance(offset_px, int)
        or offset_px < 1
        or chunk_rows < 1
        or not np.isfinite(coh).all()
        or not np.isfinite(strike).all()
    ):
        raise ValueError("Finite aligned 2D arrays and positive integer offset required")
    h, w = coh.shape
    result = np.zeros((h, w), dtype=np.float32)
    columns = np.arange(w, dtype=np.int32)[None, :]
    for start in range(0, h, chunk_rows):
        stop = min(start + chunk_rows, h)
        rows = np.arange(start, stop, dtype=np.int32)[:, None]
        angle = np.deg2rad(strike[start:stop])
        # Image rows increase south; grid-north is negative row direction.
        dr = np.rint(-offset_px * np.cos(angle)).astype(np.int32)
        dc = np.rint(offset_px * np.sin(angle)).astype(np.int32)
        rp, cp = rows + dr, columns + dc
        rm, cm = rows - dr, columns - dc
        in_bounds = (
            (rp >= 0)
            & (rp < h)
            & (rm >= 0)
            & (rm < h)
            & (cp >= 0)
            & (cp < w)
            & (cm >= 0)
            & (cm < w)
        )
        rp_clip, rm_clip = np.clip(rp, 0, h - 1), np.clip(rm, 0, h - 1)
        cp_clip, cm_clip = np.clip(cp, 0, w - 1), np.clip(cm, 0, w - 1)
        pair_ok = in_bounds & ok[rp_clip, cp_clip] & ok[rm_clip, cm_clip]
        delta = np.abs(coh[rp_clip, cp_clip] - coh[rm_clip, cm_clip])
        result[start:stop] = np.where(pair_ok & ok[start:stop], delta, 0.0)
    return result


def curvature_balance(lapneg: np.ndarray, lappos: np.ndarray) -> np.ndarray:
    """Symmetric crest/base balance in [0,1]."""
    negative = np.asarray(lapneg, np.float32)
    positive = np.asarray(lappos, np.float32)
    if negative.shape != positive.shape or np.any(negative < 0) or np.any(positive < 0):
        raise ValueError("Aligned nonnegative curvature amplitudes required")
    return np.clip(
        2.0 * np.sqrt(negative * positive) / (negative + positive + 1e-8), 0.0, 1.0
    ).astype(np.float32)


def channel_bank_veto(
    cross: np.ndarray, upface: np.ndarray, downface: np.ndarray
) -> np.ndarray:
    """Smoothly suppress cross-slope channel banks relative to strongest scarp face.

    ``max(upface, downface) / (max(upface, downface) + cross_max)`` has no tuned
    threshold and remains in [0,1]. A cross-gradient-only edge receives zero weight.
    """
    cross = np.asarray(cross, np.float32)
    upface = np.asarray(upface, np.float32)
    downface = np.asarray(downface, np.float32)
    if cross.shape != upface.shape or cross.shape != downface.shape:
        raise ValueError("Aligned channel-veto inputs required")
    if np.any(cross < 0) or np.any(upface < 0) or np.any(downface < 0):
        raise ValueError("Nonnegative channel-veto inputs required")
    face = np.maximum(upface, downface)
    return np.divide(face, face + cross, out=np.zeros_like(face), where=(face + cross) > 0)


def arm_surfaces(
    coherence: np.ndarray,
    delta2: np.ndarray,
    delta4: np.ndarray,
    balance: np.ndarray,
    root_step: np.ndarray,
    veto: np.ndarray,
    support: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return preregistered A/B/C surfaces without normalization or tuning."""
    arrays = [np.asarray(x, np.float32) for x in (coherence, delta2, delta4, balance, root_step, veto)]
    ok = np.asarray(support, bool)
    if any(x.shape != ok.shape or not np.isfinite(x).all() for x in arrays):
        raise ValueError("Finite footprint-aligned factors required")
    coherence, delta2, delta4, balance, root_step, veto = arrays
    common = balance * root_step * veto
    result = {
        "A": coherence * common,
        "B": np.maximum(delta2, delta4) * common,
        "C": np.sqrt(delta2 * delta4) * common,
    }
    return {
        arm: np.where(ok, np.clip(surface, 0.0, None), 0.0).astype(np.float32)
        for arm, surface in result.items()
    }
