"""WBG-5 feature stack: GeoDAWN geophysics + LiDAR scarp morphology + catalogue context.

Design rules
------------
* Every band is built on the competition grid (3730 x 3292, EPSG:32611, 100 m) from
  hash-pinned inputs under ``.cache/ext`` (see ``scripts/fetch_external_features.py``).
* No competitor prediction raster is ever read here. Features come from published
  USGS GeoDAWN radiometric/magnetic grids (DOI 10.5066/P93LGLVQ) and from terrain
  descriptors of the USGS 3DEP 1 m LiDAR DEM.
* Catalogue-derived features are built by a function that takes the *visible*
  catalogue as an argument, so a holdout fold can only ever see visible faults.
* The stack is memory-mapped on disk: this sandbox has ~2 GB of usable RAM and
  twelve full 100 m grids per copy.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / ".cache" / "ext"
BRIDGE = ROOT / "data" / "bridge"

GRID_SHAPE = (3730, 3292)

# LiDAR scarp channels in file order, with decoding metadata from the mirror's JSON.
LIDAR_CHANNELS = [
    ("ex_max", 1.5, "sqrt"),
    ("ex_mean", 0.3, "sqrt"),
    ("step_max", 1.0, "sqrt"),
    ("lapneg_max", 0.05, "sqrt"),
    ("lappos_max", 0.05, "sqrt"),
    ("downface_max", 1.0, "sqrt"),
    ("upface_max", 1.0, "sqrt"),
    ("cross_max", 1.0, "sqrt"),
    ("relief", 300.0, "sqrt"),
    ("coh100", 1.0, "linear"),
    ("strike", 180.0, "linear"),
]
RAD_CHANNELS = ["K", "Th", "U", "TC"]
MAG_CHANNELS = ["ThK", "UK", "UTh", "TMI_up150"]

STATIC_NAMES = (
    [f"lidar_{c[0]}" for c in LIDAR_CHANNELS]
    + ["lidar_valid_frac"]
    + [f"rad_{c}" for c in RAD_CHANNELS]
    + [f"mag_{c}" for c in MAG_CHANNELS]
    + ["tmi_aniso_s2", "tmi_cos2t_s2", "tmi_sin2t_s2", "tmi_grad_s2"]
    + ["tc_aniso_s5", "tc_cos2t_s5", "tc_sin2t_s5", "tc_grad_s5", "tc_smooth3", "tmi_smooth3"]
    + ["relief_smooth3", "relief_var3", "relief_lap"]
)
CATALOGUE_NAMES = ["cat_dist3", "cat_dist10", "cat_dens3", "cat_dens9", "cat_dens25", "cat_on"]
FEATURE_NAMES = STATIC_NAMES + CATALOGUE_NAMES


def _decode_lidar(q: np.ndarray, xmax: float, transform: str) -> np.ndarray:
    """Invert ``q = 1 + round(254 * t(clip(x/xmax, 0, 1)))``; 0 means no LiDAR."""
    t = np.zeros(q.shape, np.float32)
    good = q > 0
    t[good] = (q[good].astype(np.float32) - 1.0) / 254.0
    if transform == "sqrt":
        t = t * t
    return t * np.float32(xmax)


def structure_tensor(band: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (anisotropy, cos2theta, sin2theta, gradient magnitude) of the gradient tensor."""
    smooth = ndi.gaussian_filter(band, sigma, mode="nearest")
    gy, gx = np.gradient(smooth)
    jxx = ndi.gaussian_filter(gx * gx, sigma, mode="nearest")
    jyy = ndi.gaussian_filter(gy * gy, sigma, mode="nearest")
    jxy = ndi.gaussian_filter(gx * gy, sigma, mode="nearest")
    tr = jxx + jyy
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy**2, 0.0))
    lam1 = 0.5 * (tr + disc)
    lam2 = 0.5 * (tr - disc)
    aniso = (lam1 - lam2) / (lam1 + lam2 + 1e-9)
    cos2t = (jxx - jyy) / (disc + 1e-9)
    sin2t = (2.0 * jxy) / (disc + 1e-9)
    return (
        aniso.astype(np.float32),
        cos2t.astype(np.float32),
        sin2t.astype(np.float32),
        np.hypot(gx, gy).astype(np.float32),
    )


def footprint_mask() -> np.ndarray:
    """Official study-area mask: finite pixels of the organisers' sample submission."""
    with rasterio.open(BRIDGE / "sample_submission.tif") as ds:
        return np.isfinite(ds.read(1))


def catalogue() -> np.ndarray:
    with rasterio.open(BRIDGE / "labels.tif") as ds:
        return ds.read(1) == 1


def build_static_stack(path: Path, *, force: bool = False) -> Path:
    """Write the catalogue-independent bands to a float32 memmap of shape (F, H, W)."""
    path = Path(path)
    if path.exists() and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    foot = footprint_mask()
    n = len(STATIC_NAMES)
    mm = np.memmap(path, dtype=np.float32, mode="w+", shape=(n, *GRID_SHAPE))
    col = 0

    with rasterio.open(EXT / "lidar_scarp_features_u8.tif") as ds:
        raw = ds.read()
    for i, (_name, xmax, tf) in enumerate(LIDAR_CHANNELS):
        mm[col] = ndi.gaussian_filter(_decode_lidar(raw[i], xmax, tf), 1.0, mode="nearest")
        col += 1
    valid = raw[11] > 0
    mm[col] = ndi.uniform_filter(valid.astype(np.float32), 5, mode="nearest")
    col += 1
    relief = _decode_lidar(raw[9], 300.0, "sqrt")
    del raw

    rad = rasterio.open(EXT / "geodawn_rad_u8.tif").read().astype(np.float32)
    rad[:, ~foot] = np.nan
    for i in range(rad.shape[0]):
        mm[col] = rad[i] / 255.0
        col += 1
    mag = rasterio.open(EXT / "geodawn_extensions_u8.tif").read().astype(np.float32)
    mag[:, ~foot] = np.nan
    for i in range(mag.shape[0]):
        mm[col] = mag[i] / 255.0
        col += 1

    tmi = np.nan_to_num(mag[3], nan=float(np.nanmean(mag[3])))
    for arr in structure_tensor(tmi, 2.0):
        mm[col] = arr
        col += 1
    tc = np.nan_to_num(rad[3], nan=float(np.nanmean(rad[3])))
    for arr in structure_tensor(tc, 5.0):
        mm[col] = arr
        col += 1
    mm[col] = ndi.gaussian_filter(tc, 3.0, mode="nearest")
    col += 1
    mm[col] = ndi.gaussian_filter(tmi, 3.0, mode="nearest")
    col += 1
    mm[col] = ndi.gaussian_filter(relief, 3.0, mode="nearest")
    col += 1
    mm[col] = ndi.gaussian_filter(relief**2, 3.0, mode="nearest") - mm[col - 1] ** 2
    col += 1
    mm[col] = ndi.gaussian_filter(np.abs(ndi.laplace(relief)), 1.0, mode="nearest")
    col += 1

    mm.flush()
    if col != n:
        raise AssertionError(f"static stack column mismatch: wrote {col}, expected {n}")
    (path.parent / "static_stack_names.json").write_text(json.dumps(STATIC_NAMES, indent=1) + "\n")
    return path


def catalogue_features(visible: np.ndarray) -> np.ndarray:
    """Six catalogue-derived bands built ONLY from the supplied visible catalogue."""
    visible = np.asarray(visible, bool)
    if visible.shape != GRID_SHAPE:
        raise ValueError("catalogue must be on the competition grid")
    dist = ndi.distance_transform_edt(~visible).astype(np.float32)
    out = np.empty((len(CATALOGUE_NAMES), *GRID_SHAPE), np.float32)
    out[0] = np.minimum(dist, 3.0)
    out[1] = np.minimum(dist, 10.0)
    vf = visible.astype(np.float32)
    for i, size in enumerate((3, 9, 25), start=2):
        out[i] = ndi.uniform_filter(vf, size, mode="nearest") * (size * size)
    out[5] = vf
    return out
