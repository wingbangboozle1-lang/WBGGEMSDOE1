"""Retained WBG-2 primitives for retrospective audit only.

The WBG-2 lane is stopped. These functions describe the already-generated
artifact and do not grant permission to place or retune dots. Historic claims
of a validated holdout and a forecast were withdrawn: no reproducible
visible-only holdout or file-specific organizer receipt was found.

The buffer uses repeated four-connected dilation (Manhattan distance), not
Chebyshev distance or a Euclidean disc. See the safety audit for measured
Euclidean distances of the existing dots to the catalogue.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

#: Gaussian bandwidth for the catalogue-density prior, in pixels (100 m each).
KDE_SIGMA_PX = 15.0
#: Four-connected Manhattan steps from a mapped catalogue cell.
CATALOGUE_BUFFER_PX = 4
#: Historical budget; retained for reproducing the recorded prior, not for a new run.
DEFAULT_BUDGET = 36000


def catalogue_buffer(mask: np.ndarray, radius_px: int = CATALOGUE_BUFFER_PX) -> np.ndarray:
    """Cells within ``radius_px`` four-connected steps (Manhattan distance)."""
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
