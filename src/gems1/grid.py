"""Competition grid geometry and raster IO.

All geometry is read from the official rasters (byte-verified SHA-256 pins), never invented:

    EPSG:32611, 100 m, 3730 x 3292, origin (243350, 4508550)
    example_submission.tif sha256 2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc
    existing_faults.tif    sha256 7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093
    features               sha256 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio

NODATA_F32 = np.float32(-3.4028234663852886e38)
HEIGHT = 3730
WIDTH = 3292
EPSG = "EPSG:32611"
TRANSFORM6 = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)

BAND_NAMES = {
    1: "mag_anom",
    2: "rtp",
    3: "tmi_hg",
    4: "geod_2ndinv",
    5: "iso_grav_anom_slope",
    6: "tc",
    7: "geod_shearrate",
    8: "geod_dilaterate",
    9: "tmi_vg",
    10: "deq_n100a15",
    11: "iso_grav_anom_vg",
    12: "det_elev",
    13: "iso_grav_anom",
    14: "tmi",
    15: "depth_to_base_surf",
    16: "ieq_n100a15",
    17: "cond_surf",
    18: "iso_grav_anom_hg",
    19: "det_elev_slope",
}

SHA256_PINS = {
    "example_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "gems-geodawn-numerical-features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
}


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def data_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    bridge = root / "data" / "bridge"
    if (bridge / "example_submission.tif").exists():
        return bridge
    return root / "data"


def read_template(path: str | Path | None = None):
    path = Path(path) if path else data_dir() / "example_submission.tif"
    with rasterio.open(path) as s:
        arr = s.read(1)
        meta = dict(
            driver="GTiff",
            dtype="float32",
            count=1,
            crs=s.crs,
            transform=s.transform,
            width=s.width,
            height=s.height,
            nodata=None,
        )
    foot = np.isfinite(arr)
    return arr, foot, meta


def read_labels(path: str | Path | None = None) -> np.ndarray:
    path = Path(path) if path else data_dir() / "existing_faults.tif"
    with rasterio.open(path) as s:
        a = s.read(1)
    return a >= 1


def read_band(path: str | Path, band: int) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(path) as s:
        a = s.read(band).astype(np.float32)
    valid = np.isfinite(a) & (a > NODATA_F32 * np.float32(0.5))
    return a, valid


def fill_nearest(raw: np.ndarray, valid: np.ndarray) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt

    if valid.all():
        return raw.astype(np.float32, copy=False)
    filled = raw.astype(np.float32, copy=True)
    _, idx = distance_transform_edt(~valid, return_distances=True, return_indices=True)
    bad = ~valid
    filled[bad] = filled[idx[0][bad], idx[1][bad]]
    return filled


def write_geotiff(
    mask: np.ndarray,
    out_path: str | Path,
    template_path: str | Path | None = None,
    footprint: np.ndarray | None = None,
    outside: str = "zeros",
) -> Path:
    """Write a portal-safe single-band float32 GeoTIFF.

    outside='zeros' fills every cell with a finite value in [0, 1] (fixes
    DrivenData error \"Predicted values must be in range [0, 1]\").
    outside='nan' matches the sample-submission convention (NaN outside footprint).
    """
    _, foot, meta = read_template(template_path)
    if footprint is not None:
        foot = np.asarray(footprint, bool)
    out = np.asarray(mask, dtype=np.float32)
    if out.shape != (meta["height"], meta["width"]):
        raise ValueError(f"shape {out.shape} != {(meta['height'], meta['width'])}")
    inside = np.where(foot, out, np.float32(0.0))
    if not np.isfinite(inside[foot]).all():
        raise ValueError("non-finite value inside the footprint")
    if (inside[foot] < 0).any() or (inside[foot] > 1).any():
        raise ValueError("value outside [0, 1] inside the footprint")
    if outside == "zeros":
        written = np.where(foot, inside, np.float32(0.0))
        meta["nodata"] = None
    else:
        written = np.where(foot, inside, np.float32(np.nan))
        meta["nodata"] = np.nan
    meta["compress"] = "deflate"
    meta["tiled"] = True
    meta["zlevel"] = 9
    meta["predictor"] = 3
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **meta) as dst:
        dst.write(written, 1)
    return out_path
