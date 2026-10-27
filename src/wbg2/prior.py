"""Archived WBG-2 research prior and point-field renderer.

The existing output is a research-only spatial prior based on mapped-fault
locations; it is not a geological detector or an authorized submission. The
WBG-2 lane is stopped. The generator is retired, and no run should be started
without a separately authorized lane, a shared-tool surface check before
placement, and a prospective review card.

The previously published claims of a four-fold DTI advantage over uniform
placement and synthetic strike-trace comparisons were not supported by a
committed reproducible WBG-2 holdout record. They are withdrawn and are not
used by this module or its documentation. The existing measured PROXY-DTI
against the mapped catalogue is not a holdout score.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

#: Gaussian bandwidth for the archived catalogue-density prior, in pixels.
KDE_SIGMA_PX = 15.0
#: L1-neighborhood iterations used by the historical renderer; diagnostic only.
CATALOGUE_BUFFER_PX = 4
#: Historical positive-cell budget of the preserved research artifact.
#: This is below the smallest focus-site count and carries no calibrated score.
DEFAULT_BUDGET = 36000


def catalogue_buffer(mask: np.ndarray, radius_px: int = CATALOGUE_BUFFER_PX) -> np.ndarray:
    """Historical L1 dilation used to build the archived research prior.

    This is not the shared 3-pixel novelty kernel and must not be used as a
    substitute for the protocol's shared catalogue masking or uniqueness gate.
    """
    if radius_px <= 0:
        return np.zeros_like(mask, dtype=bool)
    return ndi.binary_dilation(
        mask, ndi.generate_binary_structure(2, 1), iterations=radius_px
    )


def density_prior(catalogue: np.ndarray, sigma_px: float = KDE_SIGMA_PX) -> np.ndarray:
    """Compute the archived KDE diagnostic from the visible mapped catalogue."""
    if sigma_px <= 0:
        raise ValueError("sigma_px must be positive")
    smoothed = ndi.gaussian_filter(np.asarray(catalogue, dtype=np.float32), sigma_px)
    maximum = float(smoothed.max())
    return (smoothed / maximum).astype(np.float32) if maximum > 0 else smoothed.astype(np.float32)


def place(intensity: np.ndarray, admissible: np.ndarray, budget: int, seed: int) -> np.ndarray:
    """Deterministically sample cells for the archived research artifact."""
    intensity = np.asarray(intensity, dtype=np.float64)
    admissible = np.asarray(admissible, dtype=bool)
    if intensity.shape != admissible.shape:
        raise ValueError("intensity/admissible grid mismatch")
    cells = np.flatnonzero(admissible.ravel())
    if budget < 0 or budget > len(cells):
        raise ValueError("budget exceeds admissible cells")
    weights = np.maximum(intensity.ravel()[cells], 0.0)
    if weights.sum() <= 0:
        weights = np.ones(len(cells), dtype=np.float64)
    rng = np.random.default_rng(seed)
    chosen = rng.choice(cells, size=budget, replace=False, p=weights / weights.sum())
    return np.column_stack(np.unravel_index(chosen, intensity.shape)).astype(np.int32)


def render(shape: tuple[int, int], cells: np.ndarray) -> np.ndarray:
    """Render a binary point field; retained for historical unit tests only."""
    result = np.zeros(shape, dtype=np.float32)
    if len(cells):
        result[cells[:, 0], cells[:, 1]] = 1.0
    return result
