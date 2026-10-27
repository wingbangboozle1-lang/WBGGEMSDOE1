"""Historical WBG-2 mathematical primitives, not an authorized lane runner.

WBG-2 failed the literal registry overlap gate. Do not use these primitives to
regenerate its placement or tune around registry entries. The catalogue mirror
is hash-pinned but not independently authenticated to the organizer.
The previous synthetic experiments do not establish a valid WBG-2 holdout.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

#: Gaussian bandwidth for the catalogue-density prior, in pixels (100 m each).
KDE_SIGMA_PX = 15.0
#: Cells closer than this to a mapped fault are excluded outright.
CATALOGUE_BUFFER_PX = 4
#: Historical budget, below (not inside) the cited calibration range.
#: The corresponding regression is not a valid leaderboard forecast.
DEFAULT_BUDGET = 36000


def catalogue_buffer(mask: np.ndarray, radius_px: int = CATALOGUE_BUFFER_PX) -> np.ndarray:
    """Cells in a Manhattan (four-connected) diamond, not a Euclidean disk."""
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
