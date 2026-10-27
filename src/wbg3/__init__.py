"""WBG-3 (SPI-PMR-WCS-1): Crustal Source-Parameter Imaging, Poisson Magnetite-Destruction,
2D Riesz Monogenic Phase Congruency, and Fold-Safe Visible Crack-Tip / Relay Inversion.
"""

from .physics import (
    STATIC_FEATURE_NAMES,
    WCS_FEATURE_NAMES,
    ALL_FEATURE_NAMES,
    build_static_feature_memmap,
    compute_visible_wcs_channels,
)

__all__ = [
    "STATIC_FEATURE_NAMES",
    "WCS_FEATURE_NAMES",
    "ALL_FEATURE_NAMES",
    "build_static_feature_memmap",
    "compute_visible_wcs_channels",
]
