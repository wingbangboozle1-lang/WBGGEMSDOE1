"""Independent evidence fields and their official provenance.

Everything this module reads is a *published, publicly documented* US product that
was derived outside the competition's label set:

``lidar_scarp_features_u8.tif`` (12 bands, uint8, 100 m)
    Slope/curvature/step descriptors computed from USGS 3DEP 1 m lidar DEM tiles
    listed in the competition's own DEM link list.  USGS 3DEP data are public and
    carry no use restrictions; USGS asks for acknowledgement of the National
    Geospatial Program (https://www.usgs.gov/3d-elevation-program).
    Channel definitions are documented in the sidecar JSON.

``geodawn_rad_u8.tif`` / ``geodawn_extensions_u8.tif`` (4 bands each, uint8, 100 m)
    GeoDAWN airborne radiometrics (K, Th, U, total count) and magnetics
    (Th/K, U/K, U/Th, TMI upward-continued to 150 m), from USGS ScienceBase item
    657e1d85d34e23d3533209f7, DOI 10.5066/P93LGLVQ (https://doi.org/10.5066/P93LGLVQ).

Both rasters are *owner mirrors* of those public products, fetched from the
sibling repository that built them; the SHA-256 of each file is recorded in the
run card so the exact bytes used are auditable.  Coverage is partial by nature
(lidar 31.7 % of the raster, radiometrics 42.0 %), which is a stated limitation,
not a hidden one.

Nothing here is a competition label, a peer prediction, or a function of the
scarp raster's own builder's scores.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

LIDAR = "lidar_scarp_features_u8.tif"
RAD = "geodawn_rad_u8.tif"
EXT = "geodawn_extensions_u8.tif"

#: band order inside lidar_scarp_features_u8.tif (from its sidecar JSON)
LIDAR_BANDS = ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "strike", "valid")
#: the five channels that respond to a *scarp* rather than to general roughness
SCARP = ("ex_max", "step_max", "lapneg_max", "upface_max", "cross_max")

PROVENANCE = {
    LIDAR: {
        "product": "LiDAR scarp / terrain-descriptor stack, 100 m, 12 bands",
        "source": "USGS 3DEP 1 m DEM tiles from the competition DEM link list",
        "rights": "USGS 3DEP: public domain, no use restrictions",
        "url": "https://www.usgs.gov/3d-elevation-program",
        "derived_by": "sibling-repository terrain pipeline (owner mirror of a public product)",
        "quantisation": "q = 1 + round(254 t), t monotone in the descriptor; q = 0 means no lidar",
    },
    RAD: {
        "product": "GeoDAWN airborne radiometrics, 100 m, 4 bands (K, Th, U, TC)",
        "source": "USGS ScienceBase 657e1d85d34e23d3533209f7",
        "doi": "10.5066/P93LGLVQ",
        "url": "https://doi.org/10.5066/P93LGLVQ",
        "derived_by": "sibling-repository GeoDAWN pipeline (owner mirror of a public product)",
    },
    EXT: {
        "product": "GeoDAWN magnetic/radiometric ratios + TMI upward-continued 150 m, 4 bands",
        "source": "USGS ScienceBase 657e1d85d34e23d3533209f7",
        "doi": "10.5066/P93LGLVQ",
        "url": "https://doi.org/10.5066/P93LGLVQ",
        "derived_by": "sibling-repository GeoDAWN pipeline (owner mirror of a public product)",
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(directory: Path, name: str) -> tuple[np.ndarray, dict]:
    p = directory / name
    if not p.exists():
        raise FileNotFoundError(
            f"{p} is missing. Re-run scripts/wbg5_fetch_external.py to restore the "
            f"documented public products, or build the structural variant with --no-evidence.")
    with rasterio.open(p) as ds:
        arr = ds.read().astype("float32")
        meta = {"shape": list(ds.shape), "bands": ds.count, "crs": str(ds.crs),
                "transform": [round(float(v), 6) for v in ds.transform][:6],
                "sha256": sha256_file(p), "bytes": p.stat().st_size}
    return arr, meta


def pct_rank(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(values.shape, np.float32)
    v = values[mask]
    if v.size == 0:
        return out
    order = np.argsort(v, kind="stable")
    r = np.empty(v.size, np.float32)
    r[order] = np.linspace(0.0, 1.0, v.size, dtype=np.float32)
    out[mask] = r
    return out


def scarp_composite(directory: Path, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, dict]:
    """Mean percentile rank of the five scarp-sharpness channels."""
    arr, meta = _read(directory, LIDAR)
    if tuple(arr.shape[1:]) != tuple(shape):
        raise ValueError(f"lidar grid {arr.shape[1:]} != {shape}")
    valid = arr[LIDAR_BANDS.index("valid")] > 0
    comp = np.zeros(shape, np.float32)
    parts = {}
    for name in SCARP:
        t = np.clip((arr[LIDAR_BANDS.index(name)] - 1.0) / 254.0, 0.0, 1.0)
        r = pct_rank(t, valid)
        parts[name] = r
        comp += r
    comp /= len(SCARP)
    meta["channels"] = list(SCARP)
    meta["coverage"] = round(float(valid.mean()), 4)
    return comp.astype(np.float32), valid, meta


def radiometric_texture(directory: Path, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, dict]:
    """Local radiometric contrast: |K, Th, U - 6 px blur|, percentile-ranked."""
    from scipy.ndimage import gaussian_filter

    arr, meta = _read(directory, RAD)
    if tuple(arr.shape[1:]) != tuple(shape):
        raise ValueError("radiometric grid mismatch")
    valid = arr[3] > 0
    acc = np.zeros(shape, np.float32)
    for i in (0, 1, 2):
        t = np.clip((arr[i] - 1.0) / 254.0, 0.0, 1.0)
        acc += pct_rank(np.abs(t - gaussian_filter(t, 6)), valid)
    acc /= 3.0
    meta["coverage"] = round(float(valid.mean()), 4)
    return acc.astype(np.float32), valid, meta


def magnetic_texture(directory: Path, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, dict]:
    """Curvature of the upward-continued TMI: |Laplacian| percentile rank."""
    from scipy.ndimage import laplace

    arr, meta = _read(directory, EXT)
    if tuple(arr.shape[1:]) != tuple(shape):
        raise ValueError("extensions grid mismatch")
    valid = np.ones(shape, bool)
    t = np.clip((arr[3] - 1.0) / 254.0, 0.0, 1.0)
    lap = np.abs(laplace(t)).astype(np.float32)
    meta["coverage"] = round(float((arr[3] > 0).mean()), 4)
    return pct_rank(lap, valid), valid, meta


def describe(directory: Path) -> dict:
    out = {}
    for name, meta in PROVENANCE.items():
        rec = dict(meta)
        p = directory / name
        if p.exists():
            with rasterio.open(p) as ds:
                rec.update({"present": True, "bytes": p.stat().st_size,
                            "sha256": sha256_file(p), "bands": ds.count,
                            "shape": [ds.height, ds.width], "crs": str(ds.crs)})
        else:
            rec["present"] = False
        out[name] = rec
    return out
