"""Competition grid constants and the pinned footprint loader."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

WIDTH, HEIGHT = 3292, 3730
CRS = "EPSG:32611"
TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
PIXEL_M = 100.0
KERNEL_RADIUS_PX = 3.0
ALPHA = 0.2
BETA = 0.8


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def bridge_path(name: str) -> Path:
    """Locate a small pinned competition raster (labels / sample submission)."""
    candidates = [_root() / "data" / name, _root() / "data" / "bridge" / name]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"missing pinned competition raster {name}; see data/README.md")


def load_catalogue() -> np.ndarray:
    """Public mapped-fault catalogue as a boolean grid (60,988 positives)."""
    with rasterio.open(bridge_path("existing_faults.tif")) as ds:
        return ds.read(1) > 0


def load_footprint() -> np.ndarray:
    """Finite pixels of the official sample submission (5,167,373 px)."""
    with rasterio.open(bridge_path("sample_submission.tif")) as ds:
        return np.isfinite(ds.read(1))
