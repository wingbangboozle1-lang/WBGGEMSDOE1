"""WBG-D1 research lane: radiometric alteration + shallow magnetic edge detector.

Self-declared, preregistered provisional lane (registry/preregistration_wbg_d1.json).
All scientific arithmetic reuses the shared vendor/gems57 instrument; this package
only contributes new radiometric feature construction, a frozen deterministic
composite, and fixed-budget non-maximum emission. No prior prediction pixels are
ever read as inputs.
"""

from .features import (
    CHANNEL_NAMES,
    build_radiometric_channels,
    deterministic_composite,
    nms_dots,
    robust_z,
)

__all__ = [
    "CHANNEL_NAMES",
    "build_radiometric_channels",
    "deterministic_composite",
    "nms_dots",
    "robust_z",
]
