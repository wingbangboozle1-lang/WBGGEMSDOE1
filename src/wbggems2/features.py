"""Label-free 81-channel Multi-Resolution `MKSF-1` feature builder (`WBG-S2`).

Combines:
  1. 19 competition geophysical / geodetic / seismic / topographic bands (`data/template57/`,
     treating Band 6 strictly as GeoDAWN radiometric Total Count per verified Spearman=0.999953).
  2. 12 seamless 100%-coverage USGS 3DEP 1/3 arc-second (~10 m) DEM channels (`data/dem10/`).
  3. 13 USGS 3DEP 1 m LiDAR scarp derivatives (`lidar_scarp_features_u8.tif`, encoding missing
     tiles natively as NaN + explicit `lid_valid` completeness indicator).
  4. 8 USGS GeoDAWN airborne radiometric & upward-continued magnetic channels (`K, Th, U, TC,
     ThK, UK, UTh, TMI_up150`).
  5. 14 `PJMF` Transgressive Piedmont-Junction Monoclinal Flexure & Anti-Mimic De-Confounding
     channels (contour-obliquity Lake Lahontan shoreline suppression, US Census TIGER 2024
     highway/railroad embankment damping, thalweg convexity, 8-azimuth directional worms,
     Frangi 2D Hessian ridge anisotropy, active Walker Lane strain-seismicity coupling).
  6. 15 `CGMD` Gallardo-Meju Potential-Field Cross-Gradient, Argillic Magnetite-Destruction
     Trough & DOE GDR #1391 Hydrothermal Conduit channels (`dist_known_fault_px` stripped).

Zero catalogue (`labels.tif` / `existing_faults.tif`) or `derived_sgmc_faults_100m_u8.tif` pixels
are ever read in this module.
"""
from __future__ import annotations

import gc
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter

from wbggems.audit import dump_json, sha256, utc_now
from wbggems1.features import build_hydrothermal_grids

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
WORK_DIR = DATA_DIR / "wbg_s2_work"

ORG_19_NAMES: list[str] = [
    "org_mag_anom",
    "org_rtp",
    "org_tmi_hg",
    "org_geod_2ndinv",
    "org_iso_grav_slope",
    "org_rad_tc_band6",
    "org_geod_shearrate",
    "org_geod_dilaterate",
    "org_tmi_vg",
    "org_deq_n100a15",
    "org_iso_grav_vg",
    "org_det_elev",
    "org_iso_grav",
    "org_tmi",
    "org_depth_to_base",
    "org_ieq_n100a15",
    "org_cond_surf",
    "org_iso_grav_hg",
    "org_det_elev_slope",
]

DEM10_12_NAMES: list[str] = [
    "dem10_slope_max",
    "dem10_slope_mean",
    "dem10_slope_std",
    "dem10_hgm20_max",
    "dem10_hgm50_max",
    "dem10_hgm200_mean",
    "dem10_steep_ratio_max",
    "dem10_resid_std",
    "dem10_resid_range",
    "dem10_curv_absmax",
    "dem10_onesided",
    "dem10_onesided3",
]

LIDAR_13_NAMES: list[str] = [
    "lid_ex_max",
    "lid_ex_mean",
    "lid_step_max",
    "lid_lapneg_max",
    "lid_lappos_max",
    "lid_downface_max",
    "lid_upface_max",
    "lid_cross_max",
    "lid_relief",
    "lid_coh100",
    "lid_strike_sin2",
    "lid_strike_cos2",
    "lid_valid",
]

GEODAWN_8_NAMES: list[str] = [
    "gd_rad_k",
    "gd_rad_th",
    "gd_rad_u",
    "gd_rad_tc",
    "gd_ext_thk",
    "gd_ext_uk",
    "gd_ext_uth",
    "gd_ext_tmi_up150",
]

PJMF_14_NAMES: list[str] = [
    "pjmf_mono_flex_10m",
    "pjmf_bajada_break_10m",
    "pjmf_contour_obliquity",
    "pjmf_transgressive_scarp",
    "pjmf_tiger_logdist",
    "pjmf_road_clean_scarp",
    "pjmf_thalweg_convexity",
    "pjmf_strike_worm_10m_600m",
    "pjmf_strike_worm_10m_1400m",
    "pjmf_frangi_aniso_10m",
    "pjmf_relief_500m",
    "pjmf_hypsometric_pos",
    "pjmf_seis_strain_aniso",
    "pjmf_transtension_dilate",
]

CGMD_15_NAMES: list[str] = [
    "cgmd_grav_resid_hp",
    "cgmd_grav_blakely_crest",
    "cgmd_mag_vert_atten",
    "cgmd_mag_hp_trough",
    "cgmd_mt_claycap_hp",
    "cgmd_mt_grad_crest",
    "cgmd_basement_step",
    "cgmd_crossgrad_grav_mag",
    "cgmd_crossgrad_grav_mt",
    "cgmd_updip_grav_700m",
    "cgmd_hyd_sinter_throat",
    "cgmd_hyd_probe2m_f2mdab",
    "cgmd_hyd_wellspring_geotherm",
    "cgmd_hyd_k_th_alteration",
    "cgmd_blind_conduit_index",
]

FEATURE_NAMES: list[str] = (
    ORG_19_NAMES
    + DEM10_12_NAMES
    + LIDAR_13_NAMES
    + GEODAWN_8_NAMES
    + PJMF_14_NAMES
    + CGMD_15_NAMES
)
N_FEATURES = len(FEATURE_NAMES)  # 81
IDX: dict[str, int] = {name: i for i, name in enumerate(FEATURE_NAMES)}


def _clean_2d(arr: np.ndarray, fp: np.ndarray, fill_outside: float = 0.0) -> np.ndarray:
    out = np.asarray(arr, dtype=np.float32).copy()
    bad = (~np.isfinite(out)) | (np.abs(out) > 1e20)
    if np.any(bad & fp):
        med = float(np.nanmedian(np.where(bad, np.nan, out)[fp]))
        if not math.isfinite(med):
            med = 0.0
        out[bad & fp] = np.float32(med)
    out[~fp] = np.float32(fill_outside)
    return out


def _robust_z_pos(arr_2d: np.ndarray, fp: np.ndarray, clip_max: float = 6.0) -> np.ndarray:
    vals = arr_2d[fp]
    med = float(np.median(vals))
    iqr = float(np.percentile(vals, 75) - np.percentile(vals, 25))
    scale = max(iqr / 1.349, 1e-5)
    z = np.clip((arr_2d - med) / scale, 0.0, clip_max).astype(np.float32)
    z[~fp] = 0.0
    return z


def _robust_z_signed(arr_2d: np.ndarray, fp: np.ndarray, clip_abs: float = 6.0) -> np.ndarray:
    vals = arr_2d[fp]
    med = float(np.median(vals))
    iqr = float(np.percentile(vals, 75) - np.percentile(vals, 25))
    scale = max(iqr / 1.349, 1e-5)
    z = np.clip((arr_2d - med) / scale, -clip_abs, clip_abs).astype(np.float32)
    z[~fp] = 0.0
    return z


def _fp_vec_to_2d(vec: np.ndarray, fp: np.ndarray, fp_ids: np.ndarray, fill: float = 0.0) -> np.ndarray:
    grid = np.full(fp.shape, fill, dtype=np.float32)
    grid.ravel()[fp_ids] = vec.astype(np.float32)
    return grid


def _hessian_ridge_crest(field_2d: np.ndarray, sigma: float, fp: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (-lambda_min)+ Blakely-Simpson crest strength and Frangi ridge anisotropy."""
    sm = gaussian_filter(field_2d.astype(np.float32), sigma=sigma)
    gy, gx = np.gradient(sm)
    gyy, gyx = np.gradient(gy)
    _, gxx = np.gradient(gx)
    tr = gxx + gyy
    det_disc = np.sqrt(np.maximum(0.0, (gxx - gyy) ** 2 + 4.0 * gyx * gyx))
    lam1 = 0.5 * (tr + det_disc)
    lam2 = 0.5 * (tr - det_disc)
    # Most negative curvature eigenvalue = convex ridge crest
    neg_curv = np.maximum(0.0, -np.minimum(lam1, lam2)).astype(np.float32)
    abs_max = np.maximum(np.abs(lam1), np.abs(lam2))
    abs_min = np.minimum(np.abs(lam1), np.abs(lam2))
    aniso = (neg_curv * (1.0 - abs_min / (abs_max + 1e-6))).astype(np.float32)
    neg_curv[~fp] = 0.0
    aniso[~fp] = 0.0
    return neg_curv, aniso


def _shift_bilinear(arr_2d: np.ndarray, dy_field: np.ndarray, dx_field: np.ndarray) -> np.ndarray:
    """Fast vectorized bilinear resample at `(r + dy_field, c + dx_field)`."""
    h, w = arr_2d.shape
    rr, cc = np.indices((h, w), dtype=np.float32)
    ry = np.clip(rr + dy_field, 0.0, float(h - 1.001))
    cx = np.clip(cc + dx_field, 0.0, float(w - 1.001))
    r0 = np.floor(ry).astype(np.int32)
    c0 = np.floor(cx).astype(np.int32)
    r1 = np.minimum(r0 + 1, h - 1)
    c1 = np.minimum(c0 + 1, w - 1)
    wy = ry - r0
    wx = cx - c0
    return (
        (1.0 - wy) * (1.0 - wx) * arr_2d[r0, c0]
        + (1.0 - wy) * wx * arr_2d[r0, c1]
        + wy * (1.0 - wx) * arr_2d[r1, c0]
        + wy * wx * arr_2d[r1, c1]
    ).astype(np.float32)


def _directional_worm_radius(
    field_2d: np.ndarray, half_px: int, ortho_penalty: float = 0.35
) -> tuple[np.ndarray, np.ndarray]:
    """8-azimuth directional line integral over `[-half_px, +half_px]` minus orthogonal background."""
    h, w = field_2d.shape
    pad = half_px
    padded = np.pad(np.nan_to_num(field_2d, nan=0.0).astype(np.float32), pad, mode="edge")
    n_az = 8
    taps_list: list[list[tuple[int, int, float]]] = []
    steps = [-half_px, -max(1, half_px // 2), 0, max(1, half_px // 2), half_px]
    wts = [0.16, 0.22, 0.24, 0.22, 0.16]
    for k in range(n_az):
        theta = k * (math.pi / n_az)
        uy, ux = math.sin(theta), math.cos(theta)
        taps = [(int(round(s * uy)), int(round(s * ux)), wt) for s, wt in zip(steps, wts)]
        taps_list.append(taps)

    resp = np.empty((n_az, h, w), dtype=np.float32)
    for k, taps in enumerate(taps_list):
        acc = np.zeros((h, w), dtype=np.float32)
        for dy, dx, wt in taps:
            acc += np.float32(wt) * padded[pad + dy : pad + dy + h, pad + dx : pad + dx + w]
        resp[k] = acc
    del padded

    best = np.full((h, w), -1e30, dtype=np.float32)
    best_k = np.zeros((h, w), dtype=np.int16)
    for k in range(n_az):
        cand = resp[k] - np.float32(ortho_penalty) * resp[(k + 4) % n_az]
        m = cand > best
        best = np.where(m, cand, best)
        best_k = np.where(m, k, best_k)
    del resp
    strike_deg = best_k.astype(np.float32) * np.float32(180.0 / n_az)
    return np.maximum(best, 0.0).astype(np.float32), strike_deg


def build_mksf_feature_memmap(*, force: bool = False) -> dict[str, Any]:
    """Build or verify the 81-channel float32 memmap in `data/wbg_s2_work/`."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    mmap_path = WORK_DIR / "mksf_features_81ch.npy"
    meta_path = WORK_DIR / "mksf_features_81ch_meta.json"
    if mmap_path.exists() and meta_path.exists() and not force:
        meta = json.loads(meta_path.read_text())
        if meta.get("n_features") == N_FEATURES and meta.get("feature_names") == FEATURE_NAMES:
            return meta

    with rasterio.open(DATA_DIR / "sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
        transform = ds.transform
    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = int(fp_ids.size)
    assert n_fp == 5_167_373, f"Unexpected footprint pixel count: {n_fp}"

    mm = np.lib.format.open_memmap(
        mmap_path, mode="w+", dtype=np.float32, shape=(n_fp, N_FEATURES)
    )

    # 1. Block A: 19 Competition bands from verified template57 cache
    cache_manifest = json.loads((ROOT / "evidence" / "shared_feature_cache.json").read_text())
    keep_2d: dict[str, np.ndarray] = {}
    for b_idx, (row, cname) in enumerate(zip(cache_manifest["bands"], ORG_19_NAMES)):
        arr = np.load(DATA_DIR / "template57" / row["cache_file"], mmap_mode="r")
        vec = np.asarray(arr, dtype=np.float32).ravel()[fp_ids].copy()
        bad = (~np.isfinite(vec)) | (np.abs(vec) > 1e20)
        # Preserve true NaN only if rare missingness, but store clean finite for 2D spatial ops
        vec_clean = vec.copy()
        if np.any(bad):
            med = float(np.nanmedian(np.where(bad, np.nan, vec)))
            vec_clean[bad] = np.float32(med if math.isfinite(med) else 0.0)
        mm[:, IDX[cname]] = vec_clean
        if cname in {
            "org_rtp",
            "org_geod_2ndinv",
            "org_geod_shearrate",
            "org_geod_dilaterate",
            "org_det_elev",
            "org_iso_grav",
            "org_depth_to_base",
            "org_ieq_n100a15",
            "org_cond_surf",
            "org_iso_grav_hg",
            "org_det_elev_slope",
        }:
            keep_2d[cname] = _fp_vec_to_2d(vec_clean, fp, fp_ids, fill=0.0)
        del vec, vec_clean
    gc.collect()

    # 2. Block B: 12 Seamless 10 m USGS 3DEP channels (100.00% footprint coverage!)
    dem10_2d: dict[str, np.ndarray] = {}
    for cname in DEM10_12_NAMES:
        vec = np.load(DATA_DIR / "dem10" / f"{cname}.f32.npy").astype(np.float32)
        if vec.shape != (n_fp,):
            raise ValueError(f"Unexpected shape for {cname}: {vec.shape}")
        if not np.isfinite(vec).all():
            raise ValueError(f"Non-finite values in seamless 10m channel {cname}")
        mm[:, IDX[cname]] = vec
        if cname in {
            "dem10_slope_max",
            "dem10_slope_mean",
            "dem10_hgm50_max",
            "dem10_steep_ratio_max",
            "dem10_onesided3",
        }:
            dem10_2d[cname] = _fp_vec_to_2d(vec, fp, fp_ids, fill=0.0)
        del vec
    gc.collect()

    # 3. Block C: 13 USGS 3DEP 1 m LiDAR channels (native NaN inside 24.63% gap + lid_valid)
    with rasterio.open(DATA_DIR / "external" / "lidar_scarp_features_u8.tif") as ds:
        lid_valid_2d = (ds.read(12) > 0) & fp
        lid_valid_fp = lid_valid_2d.ravel()[fp_ids]
        mm[:, IDX["lid_valid"]] = lid_valid_fp.astype(np.float32)
        np.save(WORK_DIR / "lid_valid_fp.npy", lid_valid_fp)

        raw_lid_names = [
            "lid_ex_max",
            "lid_ex_mean",
            "lid_step_max",
            "lid_lapneg_max",
            "lid_lappos_max",
            "lid_downface_max",
            "lid_upface_max",
            "lid_cross_max",
            "lid_relief",
            "lid_coh100",
        ]
        for band_i, cname in enumerate(raw_lid_names, start=1):
            v = ds.read(band_i).ravel()[fp_ids].astype(np.float32) / np.float32(255.0)
            v[~lid_valid_fp] = np.nan
            mm[:, IDX[cname]] = v
            del v
        # Band 11 is strike azimuth quantized 0..255 -> 0..180 deg; convert to periodic sin(2*theta), cos(2*theta)
        st_u8 = ds.read(11).ravel()[fp_ids].astype(np.float32)
        theta_rad = (st_u8 / np.float32(255.0)) * np.float32(math.pi)
        s2 = np.sin(2.0 * theta_rad).astype(np.float32)
        c2 = np.cos(2.0 * theta_rad).astype(np.float32)
        s2[~lid_valid_fp] = np.nan
        c2[~lid_valid_fp] = np.nan
        mm[:, IDX["lid_strike_sin2"]] = s2
        mm[:, IDX["lid_strike_cos2"]] = c2
        del st_u8, theta_rad, s2, c2
    gc.collect()

    # 4. Block D: 8 USGS GeoDAWN radiometric & magnetic extension channels
    with rasterio.open(DATA_DIR / "external" / "geodawn_rad_u8.tif") as ds:
        rad_names = ["gd_rad_k", "gd_rad_th", "gd_rad_u", "gd_rad_tc"]
        rad_2d: dict[str, np.ndarray] = {}
        for bi, cname in enumerate(rad_names, start=1):
            b2d = ds.read(bi).astype(np.float32)
            valid_b = (b2d > 0) & fp
            v = b2d.ravel()[fp_ids] / np.float32(255.0)
            v[~valid_b.ravel()[fp_ids]] = np.nan
            mm[:, IDX[cname]] = v
            if cname == "gd_rad_k":
                rad_2d[cname] = _robust_z_pos(_clean_2d(np.where(valid_b, b2d, np.nan), fp), fp)
            del b2d, valid_b, v

    with rasterio.open(DATA_DIR / "external" / "geodawn_extensions_u8.tif") as ds:
        ext_names = ["gd_ext_thk", "gd_ext_uk", "gd_ext_uth", "gd_ext_tmi_up150"]
        ext_2d: dict[str, np.ndarray] = {}
        for bi, cname in enumerate(ext_names, start=1):
            b2d = ds.read(bi).astype(np.float32)
            valid_b = (b2d > 0) & fp
            v = b2d.ravel()[fp_ids] / np.float32(255.0)
            v[~valid_b.ravel()[fp_ids]] = np.nan
            mm[:, IDX[cname]] = v
            if cname in {"gd_ext_thk", "gd_ext_tmi_up150"}:
                ext_2d[cname] = _clean_2d(np.where(valid_b, b2d, np.nan), fp)
            del b2d, valid_b, v
    gc.collect()

    # 5. Block E: 14 PJMF Transgressive Piedmont-Junction Flexure & Anti-Mimic channels
    det_el = keep_2d["org_det_elev"]
    el_reg = gaussian_filter(det_el, sigma=15.0).astype(np.float32)
    gy_reg, gx_reg = np.gradient(el_reg)
    gnorm_reg = np.hypot(gy_reg, gx_reg) + np.float32(1e-5)
    # Unit upslope vector pointing from basin toward mountain block
    uy_up = (gy_reg / gnorm_reg).astype(np.float32)
    ux_up = (gx_reg / gnorm_reg).astype(np.float32)

    gy_loc, gx_loc = np.gradient(gaussian_filter(det_el, sigma=1.0).astype(np.float32))
    gnorm_loc = np.hypot(gy_loc, gx_loc) + np.float32(1e-5)
    # Cross-product sin^2(angle(grad z_100m, grad z_1.5km)): vanishes on contour-parallel shorelines!
    cross_sin = np.abs(gy_loc * ux_up - gx_loc * uy_up) / gnorm_loc
    obliq = np.clip(cross_sin * cross_sin, 0.0, 1.0).astype(np.float32)
    obliq[~fp] = 0.0
    del gy_loc, gx_loc, gnorm_loc, cross_sin

    mono_flex = (
        dem10_2d["dem10_onesided3"]
        * np.log1p(np.maximum(dem10_2d["dem10_steep_ratio_max"], 0.0))
        * dem10_2d["dem10_hgm50_max"]
    ).astype(np.float32)
    mono_flex[~fp] = 0.0

    sl10 = dem10_2d["dem10_slope_mean"]
    sl_up = _shift_bilinear(gaussian_filter(sl10, 2.0), 3.5 * uy_up, 3.5 * ux_up)
    sl_dn = _shift_bilinear(gaussian_filter(sl10, 2.0), -3.5 * uy_up, -3.5 * ux_up)
    bajada_break = np.maximum(0.0, sl_up - sl_dn) * (
        1.0 / (1.0 + np.maximum(0.0, sl10 - 24.0) / 10.0)
    )
    bajada_break[~fp] = 0.0
    del sl_up, sl_dn

    contour_obliq_feat = (obliq * np.sqrt(np.maximum(dem10_2d["dem10_hgm50_max"], 0.0))).astype(np.float32)
    transgressive_scarp = (mono_flex * (0.25 + 0.75 * obliq)).astype(np.float32)

    with rasterio.open(DATA_DIR / "external" / "tiger_road_distance_m.tif") as ds:
        tiger_m = _clean_2d(ds.read(1), fp, fill_outside=0.0)
    tiger_logdist = np.log1p(np.maximum(tiger_m, 0.0) / np.float32(100.0)).astype(np.float32)
    tiger_gate = np.clip((tiger_m - 120.0) / 280.0, 0.15, 1.0).astype(np.float32)
    road_clean_scarp = (transgressive_scarp * tiger_gate).astype(np.float32)
    road_clean_scarp[~fp] = 0.0
    del tiger_m, tiger_gate

    # Thalweg convexity: positive on convex scarp crests, negative in V-shaped fluvial canyons
    thalweg_conv = (det_el - gaussian_filter(det_el, sigma=1.6)).astype(np.float32)
    thalweg_conv[~fp] = 0.0

    worm_600, _ = _directional_worm_radius(
        dem10_2d["dem10_hgm50_max"] * dem10_2d["dem10_onesided3"], half_px=4, ortho_penalty=0.35
    )
    worm_1400, _ = _directional_worm_radius(road_clean_scarp, half_px=8, ortho_penalty=0.38)
    worm_600[~fp] = 0.0
    worm_1400[~fp] = 0.0

    _, frangi_10m = _hessian_ridge_crest(dem10_2d["dem10_hgm50_max"], sigma=1.4, fp=fp)

    relief_500m = (maximum_filter(det_el, size=5) - minimum_filter(det_el, size=5)).astype(np.float32)
    relief_500m[~fp] = 0.0

    el_m20 = gaussian_filter(det_el, sigma=20.0)
    el_mad20 = gaussian_filter(np.abs(det_el - el_m20), sigma=20.0) + np.float32(10.0)
    hypso = np.clip((det_el - el_m20) / el_mad20, -4.0, 4.0).astype(np.float32)
    hypso[~fp] = 0.0
    del el_m20, el_mad20

    seis_strain = (
        np.log1p(np.maximum(keep_2d["org_ieq_n100a15"], 0.0))
        * (0.5 * keep_2d["org_geod_shearrate"] + 0.5 * keep_2d["org_geod_2ndinv"])
    ).astype(np.float32)
    seis_strain[~fp] = 0.0

    transtension = (keep_2d["org_geod_dilaterate"] * keep_2d["org_geod_shearrate"]).astype(np.float32)
    transtension[~fp] = 0.0

    pjmf_map = {
        "pjmf_mono_flex_10m": mono_flex,
        "pjmf_bajada_break_10m": bajada_break,
        "pjmf_contour_obliquity": contour_obliq_feat,
        "pjmf_transgressive_scarp": transgressive_scarp,
        "pjmf_tiger_logdist": tiger_logdist,
        "pjmf_road_clean_scarp": road_clean_scarp,
        "pjmf_thalweg_convexity": thalweg_conv,
        "pjmf_strike_worm_10m_600m": worm_600,
        "pjmf_strike_worm_10m_1400m": worm_1400,
        "pjmf_frangi_aniso_10m": frangi_10m,
        "pjmf_relief_500m": relief_500m,
        "pjmf_hypsometric_pos": hypso,
        "pjmf_seis_strain_aniso": seis_strain,
        "pjmf_transtension_dilate": transtension,
    }
    for cname, arr2d in pjmf_map.items():
        mm[:, IDX[cname]] = arr2d.ravel()[fp_ids].astype(np.float32)
    del pjmf_map, mono_flex, bajada_break, contour_obliq_feat, transgressive_scarp
    del tiger_logdist, road_clean_scarp, thalweg_conv, worm_600, worm_1400, frangi_10m, relief_500m, hypso
    gc.collect()

    # 6. Block F: 15 CGMD Cross-Gradient, Magnetite-Destruction & GDR 1391 Hydrothermal channels
    iso_g = keep_2d["org_iso_grav"]
    rtp = keep_2d["org_rtp"]
    cond = keep_2d["org_cond_surf"]
    dbase = keep_2d["org_depth_to_base"]
    iso_ghg = keep_2d["org_iso_grav_hg"]

    grav_resid_hp = (iso_g - gaussian_filter(iso_g, sigma=18.0)).astype(np.float32)
    grav_resid_hp[~fp] = 0.0
    grav_blakely, _ = _hessian_ridge_crest(iso_ghg, sigma=1.8, fp=fp)

    # Argillic magnetite-destruction trough: upward-continued 150m TMI minus surface RTP
    z_up150 = _robust_z_signed(ext_2d["gd_ext_tmi_up150"], fp)
    z_rtp = _robust_z_signed(rtp, fp)
    mag_vert_atten = np.maximum(0.0, z_up150 - z_rtp).astype(np.float32)
    mag_vert_atten[~fp] = 0.0
    del z_up150, z_rtp

    mag_hp_trough = np.maximum(0.0, gaussian_filter(rtp, 6.0) - gaussian_filter(rtp, 1.2)).astype(np.float32)
    mag_hp_trough[~fp] = 0.0

    mt_claycap_hp = (cond - gaussian_filter(cond, sigma=22.0)).astype(np.float32)
    mt_claycap_hp[~fp] = 0.0

    cy, cx = np.gradient(gaussian_filter(cond, sigma=1.5))
    mt_grad_crest = np.hypot(cy, cx).astype(np.float32)
    mt_grad_crest[~fp] = 0.0

    by, bx = np.gradient(gaussian_filter(dbase, sigma=1.5))
    basement_step = np.hypot(by, bx).astype(np.float32)
    basement_step[~fp] = 0.0
    del by, bx

    # Gallardo-Meju structural collinearity: cos^2(angle) * geometric-mean gradient magnitude
    ggy, ggx = np.gradient(gaussian_filter(iso_g, sigma=1.8))
    mgy, mgx = np.gradient(gaussian_filter(rtp, sigma=1.8))
    gn = np.hypot(ggy, ggx) + np.float32(1e-6)
    mn = np.hypot(mgy, mgx) + np.float32(1e-6)
    cn = mt_grad_crest + np.float32(1e-6)

    cos2_gm = ((ggy * mgy + ggx * mgx) / (gn * mn)) ** 2
    crossgrad_gm = (cos2_gm * np.sqrt( _robust_z_pos(gn, fp) * _robust_z_pos(mn, fp) )).astype(np.float32)
    crossgrad_gm[~fp] = 0.0

    cos2_gc = ((ggy * cy + ggx * cx) / (gn * cn)) ** 2
    crossgrad_gc = (cos2_gc * np.sqrt( _robust_z_pos(gn, fp) * _robust_z_pos(cn, fp) )).astype(np.float32)
    crossgrad_gc[~fp] = 0.0
    del ggy, ggx, mgy, mgx, cy, cx, gn, mn, cn, cos2_gm, cos2_gc

    # 700 m updip projection of hanging-wall gravity horizontal gradient onto surface fault trace
    updip_grav_700m = _shift_bilinear(gaussian_filter(iso_ghg, 1.5), -7.0 * uy_up, -7.0 * ux_up)
    updip_grav_700m[~fp] = 0.0

    # Reuse verified label-free GDR 1391 hydrothermal parser (with dist_known_fault_px stripped!)
    _, geopot_strike_deg = _directional_worm_radius(
        _robust_z_pos(iso_ghg, fp) + _robust_z_pos(mt_grad_crest, fp), half_px=6, ortho_penalty=0.35
    )
    updip_subsurf_z = 0.5 * _robust_z_pos(updip_grav_700m, fp) + 0.5 * _robust_z_pos(basement_step, fp)
    ext_thk_z = _robust_z_signed(ext_2d["gd_ext_thk"], fp)

    hyd_grids, hyd_stats = build_hydrothermal_grids(
        raw_dir=DATA_DIR,
        fp=fp,
        transform=transform,
        uy=uy_up,
        ux=ux_up,
        strike_deg=geopot_strike_deg,
        rad_k_z=rad_2d["gd_rad_k"],
        ext_thk_z=ext_thk_z,
        rtp_filled=rtp,
        updip_subsurf_z=updip_subsurf_z,
    )

    upflow_composite = (
        0.26 * hyd_grids["hyd_sinter_throat"]
        + 0.26 * hyd_grids["hyd_probe2m_f2mdab"]
        + 0.22 * hyd_grids["hyd_geotherm_updip"]
        + 0.14 * _robust_z_pos(np.maximum(mt_claycap_hp, 0.0), fp)
        + 0.12 * _robust_z_pos(mag_hp_trough, fp)
    )
    struct_composite = (
        0.40 * _robust_z_pos(grav_blakely, fp)
        + 0.35 * _robust_z_pos(basement_step, fp)
        + 0.25 * _robust_z_pos(crossgrad_gm, fp)
    )
    # Damp isotropic volcanic plug centers unless elongated structure is strong
    volc_damp = 1.0 / (1.0 + 0.25 * hyd_grids["hyd_volc_dike_worm"])
    blind_conduit = (np.sqrt(np.maximum(0.0, upflow_composite * struct_composite)) * volc_damp).astype(np.float32)
    blind_conduit[~fp] = 0.0

    cgmd_map = {
        "cgmd_grav_resid_hp": grav_resid_hp,
        "cgmd_grav_blakely_crest": grav_blakely,
        "cgmd_mag_vert_atten": mag_vert_atten,
        "cgmd_mag_hp_trough": mag_hp_trough,
        "cgmd_mt_claycap_hp": mt_claycap_hp,
        "cgmd_mt_grad_crest": mt_grad_crest,
        "cgmd_basement_step": basement_step,
        "cgmd_crossgrad_grav_mag": crossgrad_gm,
        "cgmd_crossgrad_grav_mt": crossgrad_gc,
        "cgmd_updip_grav_700m": updip_grav_700m,
        "cgmd_hyd_sinter_throat": hyd_grids["hyd_sinter_throat"],
        "cgmd_hyd_probe2m_f2mdab": hyd_grids["hyd_probe2m_f2mdab"],
        "cgmd_hyd_wellspring_geotherm": hyd_grids["hyd_geotherm_updip"],
        "cgmd_hyd_k_th_alteration": hyd_grids["hyd_rad_k_th_adularia"],
        "cgmd_blind_conduit_index": blind_conduit,
    }
    for cname, arr2d in cgmd_map.items():
        mm[:, IDX[cname]] = arr2d.ravel()[fp_ids].astype(np.float32)

    mm.flush()
    del cgmd_map, hyd_grids, keep_2d, dem10_2d, rad_2d, ext_2d
    gc.collect()

    meta = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "lane_id": "WBG-S2",
        "n_footprint_pixels": n_fp,
        "n_features": N_FEATURES,
        "feature_names": FEATURE_NAMES,
        "lidar_valid_pixels": int(lid_valid_fp.sum()),
        "lidar_gap_pixels": int((~lid_valid_fp).sum()),
        "lidar_gap_fraction": float((~lid_valid_fp).mean()),
        "dem10_coverage_fraction": 1.0,
        "hydrothermal_point_counts": hyd_stats,
        "zero_catalogue_pixels_touched": True,
        "sgmc_used_in_features": False,
        "banned_columns_stripped": ["dist_known_fault_px", "fault_id", "qfault_id"],
        "memmap_sha256": sha256(mmap_path),
    }
    dump_json(meta_path, meta)
    return meta
