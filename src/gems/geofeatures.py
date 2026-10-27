"""Full-band geophysical feature stack + terrain derivatives.

Built from the assembled competition feature raster (data/training_features.tif
— the 19 official training bands, float32, -3.4e38 null sentinels handled here)
plus derived transforms of the competition's *own* band 12 (det_elev). Every
derived layer's formula is stated in ``band_semantics()``. Outputs under
data/geofeat/ (float32 GeoTIFFs, footprint grid):

  band_<name>.tif   source band, sentinel-imputed (median of valid 3x3 after
                    5x5 valid-mean seeding)
  openness.tif      sky openness of det_elev: 1 - mean_theta/(pi/2), 32 rays
                    x 16 steps of 100 m, edge-clamped, NaN if any endpoint invalid
  asmag.tif         openness anisotropy magnitude in [0,1] (mean resultant
                    length of ray openness on the 2-theta circle)
  aphase.tif        openness anisotropy orientation (deg, half-angle, 0-180)
  slope.tif         det_elev gradient magnitude, degrees

``build_stack()`` then quantizes every layer to per-column u16 ranks in
data/geofeat/featstack_u16.npy (H*W, n_feat) — ~1.2 GB on disk, page-cache
friendly for our 3 GB RAM; tree models need order, not scale.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import rasterio

from .paths import DATA_DIR

FEAT_DIR = DATA_DIR / "geofeat"
STACK_PATH = FEAT_DIR / "featstack_u16.npy"
FEATLIST_PATH = FEAT_DIR / "featlist.json"
BAND_ORDER = [
    "mag_anom",
    "rtp",
    "tmi_hg",
    "geod_2ndinv",
    "iso_grav_anom_slope",
    "tc",
    "geod_shearrate",
    "geod_dilaterate",
    "tmi_vg",
    "deq_n100a15",
    "iso_grav_anom_vg",
    "det_elev",
    "iso_grav_anom",
    "tmi",
    "depth_to_base_surf",
    "ieq_n100a15",
    "cond_surf",
    "iso_grav_anom_hg",
    "det_elev_slope",
]
SENTINEL = -1e30


def band_semantics() -> dict:
    return {
        "bands_source": (
            "DrivenData #306 competition page/967 band list; order verified against "
            "/tmp/gems/GEMSDOE-sparse/data/bridge/TRAINING_FEATURES_BANDS.md; raster assembled by "
            "scripts/assemble_features.py from SHA-pinned parts"
        ),
        "openness": (
            "O = 1 - mean_j(theta_jk)/(pi/2) averaged per ray over the 16 valid steps, then over rays; "
            "theta_jk = atan2(h_endpoint - h_center, 100*j m); 32 azimuths k, edge-clamped; NaN where any endpoint invalid"
        ),
        "asmag": "abs(sum_k O_k * exp(i*2*t_k)) / sum_k |O_k| in [0,1]; aphase = 0.5*atan2 mod 180 deg",
        "slope": "degrees(atan(|grad det_elev| / 100 m)) central differences",
        "imputation": "invalid = non-finite or < -1e30; replaced by median of valid 3x3 neighborhood after 5x5 valid-mean seeding; pixels with no valid 5x5 neighbor stay NaN",
        "quantization": "per-column ranks of finite values -> u16 in [0, 65534]; non-finite -> 0",
    }


def _valid(a: np.ndarray) -> np.ndarray:
    return np.isfinite(a) & (a > SENTINEL)


def _impute(a: np.ndarray, v: np.ndarray) -> np.ndarray:
    from scipy.ndimage import median_filter, uniform_filter

    filled = a.copy()
    bad = ~v
    w = v.astype(np.float32)
    vs = np.where(v, a, 0.0).astype(np.float32)
    cnt = uniform_filter(w, size=5)
    mean5 = uniform_filter(vs, size=5) / np.clip(cnt, 1e-6, None)
    filled[bad] = mean5[bad]
    out = median_filter(filled, size=3, mode="nearest")
    out[v] = a[v]
    out[bad & (cnt <= 0)] = np.nan
    return out.astype(np.float32)


def _write_tif(path: Path, arr: np.ndarray, prof: dict) -> None:
    with rasterio.open(path, "w", **prof) as d:
        d.write(arr, 1)


def build_layers(force: bool = False) -> dict:
    FEAT_DIR.mkdir(parents=True, exist_ok=True)
    man_p = FEAT_DIR / "layers_manifest.json"
    if man_p.exists() and not force:
        return json.loads(man_p.read_text())
    src = DATA_DIR / "training_features.tif"
    if not src.exists():
        raise SystemExit(f"missing {src} — run scripts/assemble_features.py first")
    with rasterio.open(src) as s:
        prof = {**s.profile, "count": 1, "dtype": "float32", "nodata": None, "compress": "zstd"}
        H, W = s.height, s.width
        data = s.read()  # (19,H,W) float32 ~896 MB, held once
    man: dict = {"semantics": band_semantics(), "layers": {}}
    dem_i = None
    for i, name in enumerate(BAND_ORDER):
        a = data[i]
        v = _valid(a)
        ai = _impute(a, v)
        if name == "det_elev":
            dem_i = ai
        _write_tif(FEAT_DIR / f"band_{name}.tif", ai, prof)
        man["layers"][f"band_{name}"] = {
            "valid_frac": round(float(v.mean()), 4),
            "imputed_frac": round(float((~v).mean()), 4),
        }
        del a
    del data
    gy, gx = np.gradient(dem_i, 100.0)
    slope = np.degrees(np.arctan(np.hypot(gx, gy))).astype(np.float32)
    nray, nstep = 32, 16
    ang = 2 * np.pi * np.arange(nray) / nray
    rows, cols = np.arange(H), np.arange(W)
    o_sum = np.zeros((H, W), np.float32)  # sum over rays of ray-mean theta
    n_ok = np.zeros((H, W), np.float32)  # count of valid (ray,step) endpoints
    c2 = np.zeros((H, W), np.float32)
    s2 = np.zeros((H, W), np.float32)
    oabs = np.zeros((H, W), np.float32)
    for k in range(nray):
        dy = np.round(math.sin(ang[k]) * np.arange(1, nstep + 1)).astype(int)
        dx = np.round(math.cos(ang[k]) * np.arange(1, nstep + 1)).astype(int)
        th_sum = np.zeros((H, W), np.float32)
        th_cnt = np.zeros((H, W), np.float32)
        ok_k = np.ones((H, W), bool)
        for j in range(nstep):
            ys = np.clip(rows + dy[j], 0, H - 1)
            xs = np.clip(cols + dx[j], 0, W - 1)
            hj = dem_i[np.ix_(ys, xs)]
            good = np.isfinite(hj) & np.isfinite(dem_i)
            theta = np.where(good, np.arctan2(hj - dem_i, 100.0 * (j + 1)), 0.0).astype(np.float32)
            th_sum += theta
            th_cnt += good
            ok_k &= good
        ray_o = th_sum / np.maximum(th_cnt, 1)  # mean elevation angle per pixel
        o_sum += np.where(ok_k, ray_o, 0.0)
        c2 += np.where(ok_k, np.cos(2 * ang[k]) * ray_o, 0.0)
        s2 += np.where(ok_k, np.sin(2 * ang[k]) * ray_o, 0.0)
        oabs += np.where(ok_k, np.abs(ray_o), 0.0)
        n_ok += ok_k * nstep
        del hj, theta, th_sum, th_cnt
    bad_rays = n_ok < nray * nstep
    openness = (1.0 - (o_sum / nray) / (np.pi / 2)).astype(np.float32)
    openness[bad_rays] = np.nan
    asmag = (np.hypot(c2, s2) / np.clip(oabs, 1e-9, None)).astype(np.float32)
    asmag[bad_rays] = np.nan
    aphase = (0.5 * np.degrees(np.arctan2(s2, c2)) % 180.0).astype(np.float32)
    aphase[bad_rays] = np.nan
    for nm, arr in (("openness", openness), ("asmag", asmag), ("aphase", aphase), ("slope", slope)):
        _write_tif(FEAT_DIR / f"{nm}.tif", arr, prof)
        man["layers"][nm] = {
            "valid_frac": round(float(np.isfinite(arr).mean()), 4),
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
        }
    man_p.write_text(json.dumps(man, indent=2))
    return man


def list_features() -> list[str]:
    return [f"band_{b}" for b in BAND_ORDER] + ["openness", "asmag", "aphase", "slope"]


def _rank_u16(col: np.ndarray) -> np.ndarray:
    fin = np.isfinite(col)
    out = np.zeros(col.shape, np.uint16)
    v = col[fin]
    if v.size > 1:
        sv = np.sort(v)
        r = np.searchsorted(sv, v, side="right") - 1
        out[fin] = (r / (sv.size - 1) * 65534).astype(np.uint16)
    return out


def build_stack(force: bool = False) -> Path:
    feats = list_features()
    if STACK_PATH.exists() and FEATLIST_PATH.exists() and not force:
        return STACK_PATH
    layers = {}
    for nm in feats:
        p = FEAT_DIR / (f"band_{nm[5:]}.tif" if nm.startswith("band_") else f"{nm}.tif")
        with rasterio.open(p) as d:
            layers[nm] = d.read(1)
        H, W = layers[nm].shape
        break
    stack = np.lib.format.open_memmap(
        STACK_PATH, mode="w+", dtype=np.uint16, shape=(H * W, len(feats))
    )
    for i, nm in enumerate(feats):
        a = layers.pop(nm) if nm in layers else None
        if a is None:
            p = FEAT_DIR / (f"band_{nm[5:]}.tif" if nm.startswith("band_") else f"{nm}.tif")
            with rasterio.open(p) as d:
                a = d.read(1)
        stack[:, i] = _rank_u16(a.ravel())
        del a
        print(f"stack col {i + 1}/{len(feats)} {nm}", flush=True)
    stack.flush()
    del stack
    FEATLIST_PATH.write_text(
        json.dumps(
            {"features": feats, "shape": [int(H), int(W)], "semantics": band_semantics()}, indent=2
        )
    )
    return STACK_PATH


def open_stack() -> tuple[np.ndarray, list[str], tuple[int, int]]:
    meta = json.loads(FEATLIST_PATH.read_text())
    H, W = meta["shape"]
    stack = np.load(STACK_PATH, mmap_mode="r")
    return stack, meta["features"], (int(H), int(W))
