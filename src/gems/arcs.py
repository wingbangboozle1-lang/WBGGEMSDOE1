"""H24-2A: label-free, direction-aware annular gradient transforms.

A ring of radial gradients supports a curved contact, not necessarily a fault.
Intrusions, volcanic rims, drainage and erosion are alternative explanations.
No catalogue centers, roads, field-work sites or labels enter this transform.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, minimum_filter
from scipy.signal import fftconvolve

RADII_PX = (6, 12, 24)  # 0.6, 1.2, 2.4 km at the competition's 100 m grid.


def annular_kernels(radius: int, width: float = 1.5) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if radius < 2 or width <= 0:
        raise ValueError("Annular radius >= 2 and positive width required")
    size = int(np.ceil(radius + width))
    y, x = np.mgrid[-size : size + 1, -size : size + 1]
    r = np.hypot(x, y)
    ring = (np.abs(r - radius) <= width / 2).astype(np.float32)
    if not ring.any():
        raise ValueError("Empty annular kernel")
    ring /= ring.sum()
    return ring, ring * x / np.maximum(r, 1), ring * y / np.maximum(r, 1)


def radial_coherence(
    field: np.ndarray, valid: np.ndarray, radius: int
) -> tuple[np.ndarray, np.ndarray]:
    """Normalized annular radial-gradient agreement and valid center mask.

    C(c) = |sum_j grad F(c+r_j) dot u_j| / sum_j |grad F(c+r_j)|.
    The absolute value admits either polarity, but not an arbitrary sum of edges.
    FFT convolution reverses the odd kernels; the final absolute value cancels it.
    A complete valid halo is required; no reflected/sentinel border can make a ring.
    """
    a = np.asarray(field, dtype=np.float32)
    valid = np.asarray(valid, bool) & np.isfinite(a)
    if a.ndim != 2 or a.shape != valid.shape:
        raise ValueError("field and valid must be equal-shaped 2D arrays")
    a = gaussian_filter(np.where(valid, a, 0), 1.0)
    gy, gx = np.gradient(a)
    ring, kx, ky = annular_kernels(radius)
    radial = fftconvolve(gx, kx, mode="same") + fftconvolve(gy, ky, mode="same")
    energy = fftconvolve(np.hypot(gx, gy), ring, mode="same")
    center_valid = (
        minimum_filter(valid.astype(np.uint8), size=2 * (radius + 5) + 1, mode="constant", cval=0)
        > 0
    )
    floor = max(float(np.max(energy)) * 1e-6, 1e-12)
    c = np.clip(np.abs(radial) / np.maximum(energy, floor), 0, 1)
    c[~center_valid | (energy < floor)] = 0
    return c.astype(np.float32), center_valid


def arc_rim_support(
    field: np.ndarray, valid: np.ndarray, radii: tuple[int, ...] = RADII_PX
) -> np.ndarray:
    """Back-project valid centers onto their rims and weight by local edge strength.

    Center detection by itself is NOT a fault-location raster. The annular
    back-projection is essential to place evidence at contacts, not basin centers.
    Max over the fixed radii is an uncalibrated descriptor for a held-out model.
    """
    a = np.asarray(field, dtype=np.float32)
    good = np.asarray(valid, bool) & np.isfinite(a)
    smooth = gaussian_filter(np.where(good, a, 0), 1.0)
    gy, gx = np.gradient(smooth)
    grad = np.hypot(gx, gy)
    scale = float(np.quantile(grad[good], 0.95)) if good.any() else 0
    edge = np.clip(grad / max(scale, 1e-12), 0, 3)
    support = np.zeros(a.shape, np.float32)
    for radius in radii:
        c, _ = radial_coherence(a, good, radius)
        ring = annular_kernels(radius)[0]
        rim = np.maximum(fftconvolve(c, ring, mode="same"), 0)
        support = np.maximum(support, rim * edge)
    support[~good] = np.nan
    return support.astype(np.float32)
