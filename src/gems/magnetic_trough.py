"""H24-MTR1: fixed paired magnetic troughs, not prior-submission postprocessing.

All transforms are label-free. Units of the radiometric channel are quantized
contractor Th/K ranks; no absolute concentration or geothermal diagnosis is inferred.
See the committed preregistration for the physical hypothesis and confounder.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, shift

SUPPORT_MARGIN_PX = 72
NORMAL_ANGLES = (0, 45, 90, 135)


def _filled(a, valid):
    a = np.asarray(a, np.float32)
    valid = np.asarray(valid, bool) & np.isfinite(a)
    if a.ndim != 2 or valid.shape != a.shape or not valid.any():
        raise ValueError("A nonempty finite aligned 2D source is required")
    indices = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return a[tuple(indices)]


def _offset(a, dy, dx):
    # No np.roll: an opposite edge of the survey is not a physical neighbour.
    return shift(a, (-dy, -dx), order=1, mode="nearest", prefilter=False)


def _local_sd(smoothed):
    residual = smoothed - gaussian_filter(smoothed, 8, truncate=4)
    return np.maximum(np.sqrt(gaussian_filter(residual * residual, 8, truncate=4)), 1e-6)


def paired_trough(rtp, valid):
    """Two positive magnetic shoulders with a low centre and tangent persistence."""
    a = gaussian_filter(_filled(rtp, valid), 1, truncate=4)
    sd = _local_sd(a)
    best = np.zeros(a.shape, np.float32)
    for angle in NORMAL_ANGLES:
        theta = np.deg2rad(angle)
        ny, nx = np.sin(theta), np.cos(theta)
        left, right = _offset(a, -3 * ny, -3 * nx), _offset(a, 3 * ny, 3 * nx)
        trough = np.maximum(np.minimum(left - a, right - a), 0) / sd
        # Tangent = normal rotated by 90 degrees.
        along = 0.5 * (_offset(trough, 4 * nx, -4 * ny) + _offset(trough, -4 * nx, 4 * ny))
        np.maximum(best, np.minimum(trough, along), out=best)
    return (-np.expm1(-best)).astype(np.float32)


def ratio_depletion(thk, valid):
    """Local Th/K depletion; a relative proxy, not a measured alteration class."""
    a = gaussian_filter(_filled(thk, valid), 1, truncate=4)
    low = np.maximum(gaussian_filter(a, 8, truncate=4) - a, 0) / _local_sd(a)
    return (-np.expm1(-low)).astype(np.float32)


def build_surfaces(rtp, thk, footprint):
    rtp, thk, footprint = np.asarray(rtp), np.asarray(thk), np.asarray(footprint, bool)
    if rtp.shape != footprint.shape or thk.shape != footprint.shape:
        raise ValueError("Source grids must match the footprint")
    valid = footprint & np.isfinite(rtp) & np.isfinite(thk) & (thk > 0)
    # The margin is the frozen, conservative domain restriction, not a fitted
    # catalogue-distance feature. Missing support is excluded, never scored high.
    padded = np.pad(valid, 1, constant_values=False)
    distance = distance_transform_edt(padded)[1:-1, 1:-1]
    support = distance > SUPPORT_MARGIN_PX
    magnetic = paired_trough(rtp, valid)
    radiometric = ratio_depletion(thk, valid)
    magnetic[~support] = 0
    radiometric[~support] = 0
    candidate = magnetic * (0.5 + 0.5 * radiometric)
    return {
        "magnetic_trough": magnetic,
        "ratio_depletion": radiometric,
        "candidate": candidate.astype(np.float32),
    }, support
