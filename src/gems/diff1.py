"""DIFF1: diffusion-shape scarp-lobe morphology (LiDAR-only, catalogue-free).

Preregistered 2026-10-28 in ``research/06_wbg5_diff1_preregistration_20261028.md``
as hypothesis **WBG-5 / DIFF1** (the ranked-#3 untested candidate). It is deliberately
distinct from every reviewed lane:

* TIP1 measures a *directional derivative of coherence along strike* (terminal damage).
* The catalogue-based lanes (H19-5, D2.8/B2, S3DEP1, ...) read the public fault catalogue.
* DIFF1 reads **only** the 1 m-LiDAR-derived 100 m scarp-morphology stack and measures a
  *scale-consistent symmetric curvature-lobe / scarp-height ratio*: a diffusion-degraded
  normal-fault scarp keeps paired convex/concave lobes whose curvature amplitude scales
  with the scarp height, independently of coherence or any catalogue geometry.

No parameter is tuned on the holdout. Every transform is fixed before scoring.
"""

from __future__ import annotations

import numpy as np

from . import tip1

# Channels consumed (1-based rasterio band numbers, matching tip1.BANDS / the pinned
# ``data/external/lidar_scarp_features.json`` band order).
BANDS = {
    "step_max": (3, 1.0, "sqrt"),
    "lapneg_max": (4, 0.05, "sqrt"),
    "lappos_max": (5, 0.05, "sqrt"),
    "downface_max": (6, 1.0, "sqrt"),
    "upface_max": (7, 1.0, "sqrt"),
    "cross_max": (8, 1.0, "sqrt"),
    "relief": (9, 1.0, "sqrt"),
    "valid": (12, 1.0, "linear"),
}

ARM_NAMES = {
    "A": "amplitude_control",
    "B": "diff1_primary_symmetric_lobe",
    "C": "asymmetry_ablation",
}


def lobe_amplitude(step: np.ndarray, relief: np.ndarray) -> np.ndarray:
    """Scarp-height proxy: sqrt(step) * sqrt(relief), both already decoded."""
    step = np.asarray(step, np.float32)
    relief = np.asarray(relief, np.float32)
    if step.shape != relief.shape or not np.isfinite(step).all() or not np.isfinite(relief).all():
        raise ValueError("Finite aligned decoded step and relief required")
    if np.any(step < 0) or np.any(relief < 0):
        raise ValueError("Nonnegative decoded step and relief required")
    return np.sqrt(step) * np.sqrt(relief)


def arm_surfaces(
    balance: np.ndarray,
    amplitude: np.ndarray,
    veto: np.ndarray,
    support: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return the three preregistered surfaces, clipped to the LiDAR support."""
    arrays = [np.asarray(x, np.float32) for x in (balance, amplitude, veto)]
    ok = np.asarray(support, bool)
    if any(x.shape != ok.shape or not np.isfinite(x).all() for x in arrays):
        raise ValueError("Finite footprint-aligned DIFF1 factors required")
    balance, amplitude, veto = arrays
    base = amplitude * veto
    result = {
        # A: amplitude control - no curvature-symmetry term.
        "A": base,
        # B: primary - symmetric paired curvature lobes.
        "B": balance * base,
        # C: asymmetry ablation - a single dominant lobe.
        "C": (1.0 - balance) * base,
    }
    return {
        arm: np.where(ok, np.clip(surface, 0.0, None), 0.0).astype(np.float32)
        for arm, surface in result.items()
    }


def fixed_support(encoded: dict[str, np.ndarray], footprint: np.ndarray) -> np.ndarray:
    """Require every DIFF1 channel and >0.5 valid LiDAR support in the cell.

    Deliberately narrower than :func:`gems.tip1.fixed_support`: DIFF1 consumes only the
    scarp-morphology channels, so it does not require the coherence/strike channels.
    """
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
            support &= tip1.decode(q, maximum, encoding) > 0.5
    return support


def decode_stack(encoded: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Decode every DIFF1 channel with the fixed pinned quantization."""
    return {
        name: tip1.decode(encoded[name], maximum, encoding)
        for name, (_band, maximum, encoding) in BANDS.items()
    }
