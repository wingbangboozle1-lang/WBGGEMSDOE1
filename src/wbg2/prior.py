"""Placement prior and rendering for WBG-2.

The prior uses ONLY the organizer-provided catalogue (`labels.tif`) and the
competition footprint. It does not read, sample or imitate any other project's
predictions.

Measured basis (all locally measured this session, see docs/research):

* Gaussian KDE of mapped-fault density, sampled at 1.5 km bandwidth, beat a
  uniform draw over the same admissible cells by 1.7-2.2x in DTI on a four-fold
  spatially blocked hide-and-recover test (/tmp/exp4 -> evidence wbg2).
* Strike-aligned "runs" beat scattered dots ONLY when the true local strike is
  known (0.936 vs 0.140). With a guessed or random strike they are WORSE than
  scattering (0.090 vs 0.140). We therefore scatter: we do not claim to know
  the trace direction.
* At a fixed number of true hits, reducing the number of predicted pixels
  raises DTI monotonically until the hit count starts to fall. This is why the
  field is kept small.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

#: Gaussian bandwidth for the catalogue-density prior, in pixels (100 m each).
KDE_SIGMA_PX = 15.0
#: Cells closer than this to a mapped fault are excluded outright.
CATALOGUE_BUFFER_PX = 4
#: Default predicted-pixel budget.
#:
#: The nine focus-site artifacts span 37,654-61,328 positive pixels with an
#: organizer-reported score for each. 36,000 sits just inside that observed
#: range, so the calibrated estimate stays an interpolation rather than an
#: extrapolation into a region where the metric has not been demonstrated.
DEFAULT_BUDGET = 36000


def catalogue_buffer(mask: np.ndarray, radius_px: int = CATALOGUE_BUFFER_PX) -> np.ndarray:
    """Cells within `radius_px` (Chebyshev, 8-connected) of a True cell."""
    if radius_px <= 0:
        return np.zeros_like(mask, dtype=bool)
    return ndi.binary_dilation(
        mask, ndi.generate_binary_structure(2, 1), iterations=radius_px
    )


def density_prior(catalogue: np.ndarray, sigma_px: float = KDE_SIGMA_PX) -> np.ndarray:
    """Isotropic Gaussian KDE of mapped-fault density, normalised to max 1."""
    d = ndi.gaussian_filter(catalogue.astype(np.float32), sigma_px)
    peak = float(d.max())
    if peak <= 0.0:
        return np.zeros_like(d)
    return (d / peak).astype(np.float32)


def place(
    prior: np.ndarray,
    admissible: np.ndarray,
    budget: int,
    seed: int,
) -> np.ndarray:
    """Weighted sample without replacement over `admissible` cells.

    Returns an int32 array of (row, col) pairs, shape (n, 2).
    """
    flat = np.nonzero(admissible.ravel())[0]
    if flat.size == 0:
        raise ValueError("no admissible cells")
    w = prior.ravel()[flat].astype(np.float64)
    if not np.isfinite(w).all() or w.sum() <= 0:
        w = np.ones(flat.size, dtype=np.float64)
    w = w / w.sum()
    n = int(min(budget, flat.size))
    rng = np.random.default_rng(seed)
    pick = rng.choice(flat, size=n, replace=False, p=w)
    rows, cols = np.divmod(pick, prior.shape[1])
    return np.column_stack([rows, cols]).astype(np.int32)


def render(shape, cells: np.ndarray, dtype=np.float32) -> np.ndarray:
    """Binary p=1 surface on a zero background."""
    out = np.zeros(shape, dtype=dtype)
    out[cells[:, 0], cells[:, 1]] = 1.0
    return out
