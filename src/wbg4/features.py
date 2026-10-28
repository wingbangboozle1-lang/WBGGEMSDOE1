"""Label-free 78-channel Multi-Physics Feature Builder for Lane WBG-4 (`CSJF-1`).

Implements:
  - Block 1 (`0..18`, 19 ch): Official cached competition stack (`data/template57/`, SHA-256 verified;
    Band 6 treated strictly as GeoDAWN radiometric Total Count).
  - Block 2 (`19..30`, 12 ch): Seamless 100%-coverage USGS 3DEP 10 m terrain channels (`data/dem10/`).
  - Block 3 (`31..43`, 13 ch): USGS 3DEP 1 m LiDAR scarp channels (native NaN outside tiles; strictly
    excluded from the Seamless specialist so missing tiles never induce survey-boundary cliffs).
  - Block 4 (`44..51`, 8 ch): USGS GeoDAWN radiometric (`K, Th, U, TC, ThK, UK, UTh`) & `TMI_up150`.
  - Block 5 (`52..59`, 8 ch): NEW `DALBP` 2-Step Midpoint Listric Hanging-Wall Vector Back-Projection
    warping gravity HGM, Thurston-Smith local wavenumber `k_SPI`, MT conductivity gradient, and
    moving-window gravity-magnetic Poisson decorrelation from the hanging-wall basement cutoff back
    onto the updip surface fault trace using `depth_to_base_surf`.
  - Block 6 (`60..69`, 10 ch): NEW `CSJT` Multi-Scale Gradient Structure-Tensor Minor Eigenvalue
    `sqrt(lambda_2(J_sigma))` (conjugate fault-intersection & Y-branch detector), `BFRC-1` thin-plate
    biharmonic basement rollover hinge `nabla^4(Z_b)`, and `RGFD-1` directional strike-termination
    offset detectors.
  - Block 7 (`70..77`, 8 ch): Anti-mimic de-confounding (Lake Lahontan contour obliquity, US Census
    TIGER 2024 road/rail embankment damping, canyon thalweg convexity), Walker Lane transtensional
    strain, and label-free OpenEI GDR #1391 hydrothermal conduits (`dist_known_fault_px` stripped).

STRICT ANTI-LEAKAGE GUARANTEE:
  Zero catalogue rasters (`labels.tif`, `existing_faults.tif`, `derived_sgmc_faults_100m_u8.tif`,
  `gdr_qfaults_traces.csv`) and zero peer prediction rasters are ever read in this module.
"""

from __future__ import annotations

import gc
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

from wbggems.audit import dump_json, sha256, utc_now
from wbggems1.features import build_hydrothermal_grids

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
WORK_DIR = DATA_DIR / "wbg4_work"

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
    "org_det_elev_slope",
    "org_depth_to_base",
    "org_ieq_n100a15",
    "org_cond_surf",
    "org_iso_grav_hg",
    "org_geod_maxshear",
]

DEM10_12_NAMES: list[str] = [
    "dem10_slope_max",
    "dem10_slope_mean",
    "dem10_slope_std",
    "dem10_hgm20_max",
    "dem10_hgm50_max",
    "dem10_hgm200_mean",
    "dem10_steep_ratio_max",
    "dem10_curv_absmax",
    "dem10_resid_range",
    "dem10_resid_std",
    "dem10_onesided",
    "dem10_onesided3",
]

LID_13_NAMES: list[str] = [
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

GD_8_NAMES: list[str] = [
    "gd_rad_k",
    "gd_rad_th",
    "gd_rad_u",
    "gd_rad_tc",
    "gd_ext_thk",
    "gd_ext_uk",
    "gd_ext_uth",
    "gd_ext_tmi_up150",
]

DALBP_8_NAMES: list[str] = [
    "dalbp_offset_px",
    "dalbp_grav_hg_updip",
    "dalbp_kspi_grav_updip",
    "dalbp_kspi_mag_updip",
    "dalbp_mt_grad_updip",
    "dalbp_poisson_decorr_updip",
    "dalbp_coaxial_scarp_coupling",
    "dalbp_blind_playa_conduit",
]

CSJT_10_NAMES: list[str] = [
    "csjt_minor_eig_dem10_300m",
    "csjt_minor_eig_dem10_800m",
    "csjt_minor_eig_grav_updip_600m",
    "csjt_minor_eig_mag_600m",
    "csjt_multiphysics_junction",
    "csjt_coh_dem10_400m",
    "csjt_coh_subsurf_700m",
    "bfrc_biharmonic_rollover",
    "rgfd_strike_termination_10m",
    "rgfd_strike_termination_mag",
]

ANTI_HYD_8_NAMES: list[str] = [
    "anti_contour_obliquity",
    "anti_tiger_logdist",
    "anti_thalweg_convexity",
    "tect_walker_transtension",
    "hyd_sinter_throat",
    "hyd_probe2m_f2mdab",
    "hyd_wellspring_geotherm",
    "hyd_junction_upflow_index",
]

FEATURE_NAMES: list[str] = (
    ORG_19_NAMES
    + DEM10_12_NAMES
    + LID_13_NAMES
    + GD_8_NAMES
    + DALBP_8_NAMES
    + CSJT_10_NAMES
    + ANTI_HYD_8_NAMES
)
N_FEATURES = len(FEATURE_NAMES)  # 78
assert N_FEATURES == 78

IDX: dict[str, int] = {name: i for i, name in enumerate(FEATURE_NAMES)}
ORG_19_INDICES: list[int] = [IDX[c] for c in ORG_19_NAMES]
LIDAR_INDICES_SET = {IDX[c] for c in LID_13_NAMES}
SEAMLESS_65_INDICES: list[int] = [i for i in range(N_FEATURES) if i not in LIDAR_INDICES_SET]


def _fp_vec_to_2d(vec: np.ndarray, fp: np.ndarray, fp_ids: np.ndarray, fill: float = 0.0) -> np.ndarray:
    grid = np.full(fp.shape, fill, dtype=np.float32)
    grid.ravel()[fp_ids] = vec.astype(np.float32)
    return grid


def _clean_2d(arr: np.ndarray, fp: np.ndarray, fill_outside: float = 0.0) -> np.ndarray:
    out = arr.astype(np.float32, copy=True)
    valid = fp & np.isfinite(out) & (np.abs(out) < 1e20)
    med = float(np.median(out[valid])) if np.any(valid) else 0.0
    out[fp & (~valid)] = np.float32(med)
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


def _shift_bilinear(arr_2d: np.ndarray, dy_field: np.ndarray, dx_field: np.ndarray) -> np.ndarray:
    """Vectorized bilinear sample of `arr_2d` at `(r + dy_field, c + dx_field)`."""
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


def _structure_tensor_eigs(
    field_2d: np.ndarray,
    fp: np.ndarray,
    *,
    grad_sigma: float = 1.0,
    window_sigma: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute gradient outer-product structure tensor J_sigma = G_w * (grad u grad u^T).

    Returns:
      sqrt_lam2 : Harris-Forstner minor-eigenvalue root (high ONLY at 2D conjugate fault
                  intersections, Y-branches, and sharp stepover corners).
      coherence : Linear coherence ((lam1 - lam2)/(lam1 + lam2 + eps)) * sqrt(lam1)
                  (high along planar 1D fault strands).
      strike_rad: Dominant fault-strike azimuth in [0, pi) perpendicular to principal gradient.
    """
    sm = gaussian_filter(field_2d.astype(np.float32), sigma=grad_sigma)
    gy, gx = np.gradient(sm)
    jxx = gaussian_filter(gx * gx, sigma=window_sigma)
    jyy = gaussian_filter(gy * gy, sigma=window_sigma)
    jxy = gaussian_filter(gx * gy, sigma=window_sigma)
    del sm, gy, gx

    tr = jxx + jyy
    disc = np.sqrt(np.maximum(0.0, (jxx - jyy) ** 2 + 4.0 * jxy * jxy))
    lam1 = np.maximum(0.0, 0.5 * (tr + disc))
    lam2 = np.maximum(0.0, 0.5 * (tr - disc))

    sqrt_lam2 = np.sqrt(lam2).astype(np.float32)
    coh = ((lam1 - lam2) / (lam1 + lam2 + np.float32(1e-7)) * np.sqrt(lam1)).astype(np.float32)
    # Principal gradient angle phi = 0.5 * atan2(2*jxy, jxx - jyy); strike is phi + pi/2 mod pi
    grad_phi = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    strike_rad = np.mod(grad_phi + 0.5 * math.pi, math.pi).astype(np.float32)

    sqrt_lam2[~fp] = 0.0
    coh[~fp] = 0.0
    strike_rad[~fp] = 0.0
    return sqrt_lam2, coh, strike_rad


def _strike_termination_asymmetry(field_2d: np.ndarray, fp: np.ndarray, half_px: int = 6) -> np.ndarray:
    """Rank #3 (RGFD-1): 8-azimuth half-line envelope termination |L+_theta - L-_theta|.

    Fires where a strong linear ridge or potential-field gradient abruptly terminates or
    steps laterally across an unmapped accommodation/transfer zone.
    """
    h, w = field_2d.shape
    pad = half_px
    padded = np.pad(np.maximum(field_2d, 0.0).astype(np.float32), pad, mode="edge")
    n_az = 8
    steps = [2, max(3, half_px // 2), half_px]
    wts = [0.38, 0.34, 0.28]

    best_term = np.zeros((h, w), dtype=np.float32)
    for k in range(n_az):
        theta = k * (math.pi / n_az)
        uy, ux = math.sin(theta), math.cos(theta)
        pos_acc = np.zeros((h, w), dtype=np.float32)
        neg_acc = np.zeros((h, w), dtype=np.float32)
        for s, wt in zip(steps, wts):
            dy = int(round(s * uy))
            dx = int(round(s * ux))
            pos_acc += np.float32(wt) * padded[pad + dy : pad + dy + h, pad + dx : pad + dx + w]
            neg_acc += np.float32(wt) * padded[pad - dy : pad - dy + h, pad - dx : pad - dx + w]
        # High when one half-ray is strong AND opposite half-ray terminates abruptly
        asym = np.abs(pos_acc - neg_acc) * np.sqrt(np.maximum(pos_acc, neg_acc) + np.float32(1e-6))
        best_term = np.maximum(best_term, asym)
    del padded
    best_term[~fp] = 0.0
    return best_term.astype(np.float32)


def _local_wavenumber_spi(hg_2d: np.ndarray, vg_2d: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Thurston & Smith (1997) Source Parameter Imaging local wavenumber k_SPI."""
    h_sm = gaussian_filter(np.maximum(hg_2d, 0.0).astype(np.float32), sigma=1.4)
    v_sm = gaussian_filter(vg_2d.astype(np.float32), sigma=1.4)
    hy, hx = np.gradient(h_sm)
    vy, vx = np.gradient(v_sm)
    num = np.sqrt(hx * hx + hy * hy + vx * vx + vy * vy)
    den = np.hypot(h_sm, v_sm) + np.float32(1e-3)
    k_spi = np.log1p(np.maximum(0.0, num / den)).astype(np.float32)
    k_spi[~fp] = 0.0
    return k_spi


def build_csjf1_feature_memmap(*, force: bool = False) -> dict[str, Any]:
    """Build or verify the 78-channel float32 memmap in `data/wbg4_work/`."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    mmap_path = WORK_DIR / "csjf1_features_78ch.npy"
    meta_path = WORK_DIR / "csjf1_features_78ch_meta.json"
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

    # ------------------------------------------------------------------
    # Block 1: 19 Competition bands (SHA-256 verified against shared_feature_cache)
    # ------------------------------------------------------------------
    cache_manifest = json.loads((ROOT / "evidence" / "shared_feature_cache.json").read_text())
    keep_2d: dict[str, np.ndarray] = {}
    needed_2d = {
        "org_rtp",
        "org_tmi_hg",
        "org_tmi_vg",
        "org_geod_2ndinv",
        "org_geod_shearrate",
        "org_geod_dilaterate",
        "org_iso_grav_vg",
        "org_det_elev",
        "org_iso_grav",
        "org_depth_to_base",
        "org_ieq_n100a15",
        "org_cond_surf",
        "org_iso_grav_hg",
    }
    for row, cname in zip(cache_manifest["bands"], ORG_19_NAMES):
        band_path = DATA_DIR / "template57" / row["cache_file"]
        if sha256(band_path) != row["sha256"]:
            raise RuntimeError(f"Template57 SHA-256 mismatch on {band_path}")
        arr = np.load(band_path, mmap_mode="r")
        vec = np.asarray(arr, dtype=np.float32).ravel()[fp_ids].copy()
        bad = (~np.isfinite(vec)) | (np.abs(vec) > 1e20)
        if np.any(bad):
            med = float(np.nanmedian(np.where(bad, np.nan, vec)))
            vec[bad] = np.float32(med if math.isfinite(med) else 0.0)
        mm[:, IDX[cname]] = vec
        if cname in needed_2d:
            keep_2d[cname] = _fp_vec_to_2d(vec, fp, fp_ids, fill=0.0)
        del vec
    gc.collect()

    # ------------------------------------------------------------------
    # Block 2: 12 Seamless 10 m USGS 3DEP channels (100% coverage)
    # ------------------------------------------------------------------
    dem10_2d: dict[str, np.ndarray] = {}
    for cname in DEM10_12_NAMES:
        vec = np.load(DATA_DIR / "dem10" / f"{cname}.f32.npy").astype(np.float32)
        if vec.shape != (n_fp,) or not np.isfinite(vec).all():
            raise ValueError(f"Invalid seamless 10m DEM channel: {cname}")
        mm[:, IDX[cname]] = vec
        if cname in {"dem10_slope_mean", "dem10_hgm50_max", "dem10_steep_ratio_max", "dem10_onesided3"}:
            dem10_2d[cname] = _fp_vec_to_2d(vec, fp, fp_ids, fill=0.0)
        del vec
    gc.collect()

    # ------------------------------------------------------------------
    # Block 3: 13 USGS 3DEP 1 m LiDAR channels (isolated in Full specialist)
    # ------------------------------------------------------------------
    with rasterio.open(DATA_DIR / "external" / "lidar_scarp_features_u8.tif") as ds:
        lid_valid_2d = (ds.read(12) > 0) & fp
        lid_valid_fp = lid_valid_2d.ravel()[fp_ids]
        mm[:, IDX["lid_valid"]] = lid_valid_fp.astype(np.float32)
        np.save(WORK_DIR / "lid_valid_fp.npy", lid_valid_fp)

        raw_lid = [
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
        for bi, cname in enumerate(raw_lid, start=1):
            v = ds.read(bi).ravel()[fp_ids].astype(np.float32) / np.float32(255.0)
            v[~lid_valid_fp] = np.nan
            mm[:, IDX[cname]] = v
            del v
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

    # ------------------------------------------------------------------
    # Block 4: 8 USGS GeoDAWN radiometric & magnetic extension channels
    # ------------------------------------------------------------------
    rad_k_z: np.ndarray
    ext_thk_z: np.ndarray
    with rasterio.open(DATA_DIR / "external" / "geodawn_rad_u8.tif") as ds:
        for bi, cname in enumerate(["gd_rad_k", "gd_rad_th", "gd_rad_u", "gd_rad_tc"], start=1):
            b2d = ds.read(bi).astype(np.float32)
            vb = (b2d > 0) & fp
            v = b2d.ravel()[fp_ids] / np.float32(255.0)
            v[~vb.ravel()[fp_ids]] = np.nan
            mm[:, IDX[cname]] = v
            if cname == "gd_rad_k":
                rad_k_z = _robust_z_pos(_clean_2d(np.where(vb, b2d, np.nan), fp), fp)
            del b2d, vb, v

    with rasterio.open(DATA_DIR / "external" / "geodawn_extensions_u8.tif") as ds:
        for bi, cname in enumerate(["gd_ext_thk", "gd_ext_uk", "gd_ext_uth", "gd_ext_tmi_up150"], start=1):
            b2d = ds.read(bi).astype(np.float32)
            vb = (b2d > 0) & fp
            v = b2d.ravel()[fp_ids] / np.float32(255.0)
            v[~vb.ravel()[fp_ids]] = np.nan
            mm[:, IDX[cname]] = v
            if cname == "gd_ext_thk":
                clean_thk = _clean_2d(np.where(vb, b2d, np.nan), fp)
                vals = clean_thk[fp]
                iqr = max(float(np.percentile(vals, 75) - np.percentile(vals, 25)) / 1.349, 1e-5)
                ext_thk_z = np.clip((clean_thk - float(np.median(vals))) / iqr, -6.0, 6.0).astype(np.float32)
                ext_thk_z[~fp] = 0.0
                del clean_thk
            del b2d, vb, v
    gc.collect()

    # ------------------------------------------------------------------
    # Block 5: 8 NEW DALBP 2-Step Midpoint Listric Hanging-Wall Back-Projection channels
    # ------------------------------------------------------------------
    zb_raw = np.maximum(keep_2d["org_depth_to_base"], 0.0).astype(np.float32)
    zb_sm = gaussian_filter(zb_raw, sigma=3.5).astype(np.float32)
    zby, zbx = np.gradient(zb_sm)
    zb_gnorm = np.hypot(zby, zbx) + np.float32(1e-4)
    # Unit vector pointing down-dip into the deeper hanging-wall basin
    gzy = (zby / zb_gnorm).astype(np.float32)
    gzx = (zbx / zb_gnorm).astype(np.float32)

    # Effective listric dip angle: 58 deg near surface shallowing to 46 deg in >=2.5 km deep basins
    dip_deg_0 = 58.0 - 12.0 * np.clip(zb_sm / 2500.0, 0.0, 1.0)
    cot_0 = 1.0 / np.tan(np.deg2rad(dip_deg_0))
    dp_0 = (np.clip(zb_sm, 0.0, 2200.0) / 100.0 * cot_0).astype(np.float32)

    # 2-Step Midpoint Lagrangian Ray-Trace to sample hanging-wall midpoint depth & dip direction
    zb_mid = _shift_bilinear(zb_sm, 0.5 * dp_0 * gzy, 0.5 * dp_0 * gzx)
    gzy_mid = _shift_bilinear(gzy, 0.5 * dp_0 * gzy, 0.5 * dp_0 * gzx)
    gzx_mid = _shift_bilinear(gzx, 0.5 * dp_0 * gzy, 0.5 * dp_0 * gzx)
    gn_mid = np.hypot(gzy_mid, gzx_mid) + np.float32(1e-5)
    gzy_mid /= gn_mid
    gzx_mid /= gn_mid

    dip_deg_mid = 58.0 - 12.0 * np.clip(zb_mid / 2500.0, 0.0, 1.0)
    cot_mid = 1.0 / np.tan(np.deg2rad(dip_deg_mid))
    dp_listric = np.clip(np.clip(zb_mid, 0.0, 2200.0) / 100.0 * cot_mid, 0.0, 21.5).astype(np.float32)
    dp_listric[~fp] = 0.0

    shift_y = (dp_listric * gzy_mid).astype(np.float32)
    shift_x = (dp_listric * gzx_mid).astype(np.float32)
    del dip_deg_0, cot_0, dp_0, zb_mid, dip_deg_mid, cot_mid, gn_mid

    iso_ghg = keep_2d["org_iso_grav_hg"]
    iso_gvg = keep_2d["org_iso_grav_vg"]
    tmi_hg = keep_2d["org_tmi_hg"]
    tmi_vg = keep_2d["org_tmi_vg"]
    cond = keep_2d["org_cond_surf"]
    rtp = keep_2d["org_rtp"]
    iso_g = keep_2d["org_iso_grav"]

    kspi_grav = _local_wavenumber_spi(iso_ghg, iso_gvg, fp)
    kspi_mag = _local_wavenumber_spi(tmi_hg, tmi_vg, fp)

    cy, cx = np.gradient(gaussian_filter(cond, sigma=1.5))
    mt_grad = np.hypot(cy, cx).astype(np.float32)
    mt_grad[~fp] = 0.0
    del cy, cx

    # Moving-window Poisson gravity-magnetic decorrelation (high where hydrothermal alteration destroys magnetite along a density boundary)
    ggy, ggx = np.gradient(gaussian_filter(iso_g, sigma=1.8))
    mgy, mgx = np.gradient(gaussian_filter(rtp, sigma=1.8))
    gn = np.hypot(ggy, ggx) + np.float32(1e-5)
    mn = np.hypot(mgy, mgx) + np.float32(1e-5)
    cos2_gm = gaussian_filter(((ggy * mgy + ggx * mgx) / (gn * mn)) ** 2, sigma=2.5)
    poisson_decorr = (_robust_z_pos(gn, fp) * (1.0 - np.clip(cos2_gm, 0.0, 1.0))).astype(np.float32)
    poisson_decorr[~fp] = 0.0
    del ggy, ggx, mgy, mgx, gn, mn, cos2_gm

    # Sample hanging-wall subsurface fields back onto the updip surface fault trace!
    dalbp_grav_hg = _shift_bilinear(gaussian_filter(iso_ghg, 1.2), shift_y, shift_x)
    dalbp_kspi_g = _shift_bilinear(kspi_grav, shift_y, shift_x)
    dalbp_kspi_m = _shift_bilinear(kspi_mag, shift_y, shift_x)
    dalbp_mt_grad = _shift_bilinear(mt_grad, shift_y, shift_x)
    dalbp_poisson = _shift_bilinear(poisson_decorr, shift_y, shift_x)
    for a in (dalbp_grav_hg, dalbp_kspi_g, dalbp_kspi_m, dalbp_mt_grad, dalbp_poisson):
        a[~fp] = 0.0
    del kspi_grav, kspi_mag, poisson_decorr, shift_y, shift_x

    # Coaxial alignment between 10m piedmont flexure gradient and updip basement dip vector
    dem_flex = (
        dem10_2d["dem10_onesided3"]
        * np.log1p(np.maximum(dem10_2d["dem10_steep_ratio_max"], 0.0))
        * dem10_2d["dem10_hgm50_max"]
    ).astype(np.float32)
    dem_flex[~fp] = 0.0
    dfy, dfx = np.gradient(gaussian_filter(dem10_2d["dem10_hgm50_max"], sigma=1.2))
    dfn = np.hypot(dfy, dfx) + np.float32(1e-5)
    coax_cos2 = ((dfy * gzy_mid + dfx * gzx_mid) / dfn) ** 2
    dalbp_coaxial = (
        (0.35 + 0.65 * coax_cos2)
        * np.sqrt(_robust_z_pos(dem_flex, fp) * _robust_z_pos(dalbp_grav_hg, fp))
    ).astype(np.float32)
    dalbp_coaxial[~fp] = 0.0
    del dfy, dfx, dfn, coax_cos2, gzy_mid, gzx_mid

    # Concealed zero-scarp playa conduit index (updip geophysical step in low-slope basin interior)
    playa_weight = np.exp(-np.square(np.maximum(dem10_2d["dem10_slope_mean"], 0.0) / 5.5)).astype(np.float32)
    dalbp_playa = (
        playa_weight
        * (0.45 * _robust_z_pos(dalbp_grav_hg, fp) + 0.35 * _robust_z_pos(dalbp_mt_grad, fp) + 0.20 * _robust_z_pos(dalbp_kspi_g, fp))
    ).astype(np.float32)
    dalbp_playa[~fp] = 0.0

    for cname, arr2d in [
        ("dalbp_offset_px", dp_listric),
        ("dalbp_grav_hg_updip", dalbp_grav_hg),
        ("dalbp_kspi_grav_updip", dalbp_kspi_g),
        ("dalbp_kspi_mag_updip", dalbp_kspi_m),
        ("dalbp_mt_grad_updip", dalbp_mt_grad),
        ("dalbp_poisson_decorr_updip", dalbp_poisson),
        ("dalbp_coaxial_scarp_coupling", dalbp_coaxial),
        ("dalbp_blind_playa_conduit", dalbp_playa),
    ]:
        mm[:, IDX[cname]] = arr2d.ravel()[fp_ids].astype(np.float32)
    del dp_listric, dalbp_kspi_g, dalbp_kspi_m, dalbp_poisson, dalbp_coaxial
    gc.collect()

    # ------------------------------------------------------------------
    # Block 6 & Block 7: Anti-Mimic De-Confounding + CSJT + BFRC + RGFD + GDR 1391 Hydrothermal
    # ------------------------------------------------------------------
    det_el = keep_2d["org_det_elev"]
    el_reg = gaussian_filter(det_el, sigma=15.0).astype(np.float32)
    gy_reg, gx_reg = np.gradient(el_reg)
    gn_reg = np.hypot(gy_reg, gx_reg) + np.float32(1e-5)
    uy_up = (gy_reg / gn_reg).astype(np.float32)
    ux_up = (gx_reg / gn_reg).astype(np.float32)
    del el_reg, gy_reg, gx_reg, gn_reg

    gy_loc, gx_loc = np.gradient(gaussian_filter(det_el, sigma=1.0).astype(np.float32))
    gn_loc = np.hypot(gy_loc, gx_loc) + np.float32(1e-5)
    cross_sin = np.abs(gy_loc * ux_up - gx_loc * uy_up) / gn_loc
    obliq = np.clip(cross_sin * cross_sin, 0.0, 1.0).astype(np.float32)
    obliq[~fp] = 0.0
    del gy_loc, gx_loc, gn_loc, cross_sin

    with rasterio.open(DATA_DIR / "external" / "tiger_road_distance_m.tif") as ds:
        tiger_m = _clean_2d(ds.read(1), fp, fill_outside=0.0)
    tiger_logdist = np.log1p(np.maximum(tiger_m, 0.0) / np.float32(100.0)).astype(np.float32)
    tiger_gate = np.clip((tiger_m - 120.0) / 280.0, 0.15, 1.0).astype(np.float32)
    road_clean_scarp = (dem_flex * (0.25 + 0.75 * obliq) * tiger_gate).astype(np.float32)
    road_clean_scarp[~fp] = 0.0
    del tiger_m, tiger_gate, dem_flex

    thalweg_conv = (det_el - gaussian_filter(det_el, sigma=1.6)).astype(np.float32)
    thalweg_conv[~fp] = 0.0

    # CSJT: Multi-Physics Gradient Structure Tensor Minor Eigenvalues sqrt(lambda_2(J_sigma))
    j_dem_300, coh_dem_400, strike_dem_rad = _structure_tensor_eigs(
        dem10_2d["dem10_hgm50_max"], fp, grad_sigma=1.0, window_sigma=3.0
    )
    j_dem_800, _, _ = _structure_tensor_eigs(road_clean_scarp, fp, grad_sigma=1.4, window_sigma=8.0)
    j_grav_600, coh_sub_700, strike_sub_rad = _structure_tensor_eigs(
        _robust_z_pos(dalbp_grav_hg, fp) + 0.7 * _robust_z_pos(dalbp_mt_grad, fp),
        fp,
        grad_sigma=1.4,
        window_sigma=6.5,
    )
    j_mag_600, _, _ = _structure_tensor_eigs(tmi_hg, fp, grad_sigma=1.4, window_sigma=6.0)

    # Tectonic strain gate separating active conjugate fault intersections from passive fan channel forks
    strain_gate = (
        0.5
        + 0.5
        * np.tanh(
            0.5 * _robust_z_pos(keep_2d["org_geod_dilaterate"], fp)
            + 0.5 * _robust_z_pos(keep_2d["org_geod_shearrate"], fp)
        )
    ).astype(np.float32)
    multiphys_junction = (
        strain_gate
        * np.power(
            np.maximum(0.0, _robust_z_pos(j_dem_800, fp) + 0.25)
            * np.maximum(0.0, _robust_z_pos(j_grav_600, fp) + 0.25)
            * np.maximum(0.0, _robust_z_pos(j_mag_600, fp) + 0.25),
            1.0 / 3.0,
        )
    ).astype(np.float32)
    multiphys_junction[~fp] = 0.0

    # Rank #2 (BFRC-1): Thin-plate flexural basement rollover biharmonic hinge nabla^4(Z_b)
    zb_flex = gaussian_filter(zb_raw, sigma=4.0).astype(np.float32)
    lap1_y, lap1_x = np.gradient(zb_flex)
    lap1 = np.gradient(lap1_y)[0] + np.gradient(lap1_x)[1]
    lap2_y, lap2_x = np.gradient(gaussian_filter(lap1, sigma=2.0))
    biharm_zb = np.abs(np.gradient(lap2_y)[0] + np.gradient(lap2_x)[1]).astype(np.float32)
    bfrc_hinge = (
        _robust_z_pos(biharm_zb, fp) * (0.4 + 0.6 * np.tanh(_robust_z_pos(dalbp_mt_grad, fp)))
    ).astype(np.float32)
    bfrc_hinge[~fp] = 0.0
    del zb_raw, zb_sm, zb_flex, lap1_y, lap1_x, lap1, lap2_y, lap2_x, biharm_zb

    # Rank #3 (RGFD-1): Directional strike-termination offset detectors
    rgfd_10m = _strike_termination_asymmetry(road_clean_scarp, fp, half_px=6)
    rgfd_mag = _strike_termination_asymmetry(_robust_z_pos(tmi_hg, fp), fp, half_px=7)

    for cname, arr2d in [
        ("csjt_minor_eig_dem10_300m", j_dem_300),
        ("csjt_minor_eig_dem10_800m", j_dem_800),
        ("csjt_minor_eig_grav_updip_600m", j_grav_600),
        ("csjt_minor_eig_mag_600m", j_mag_600),
        ("csjt_multiphysics_junction", multiphys_junction),
        ("csjt_coh_dem10_400m", coh_dem_400),
        ("csjt_coh_subsurf_700m", coh_sub_700),
        ("bfrc_biharmonic_rollover", bfrc_hinge),
        ("rgfd_strike_termination_10m", rgfd_10m),
        ("rgfd_strike_termination_mag", rgfd_mag),
    ]:
        mm[:, IDX[cname]] = arr2d.ravel()[fp_ids].astype(np.float32)

    # Save 2D subsurface-junction composite & dominant strike for Stage-2 visible-only tip stress gating
    subsurf_gate_2d = (
        0.38 * _robust_z_pos(dalbp_grav_hg, fp)
        + 0.24 * _robust_z_pos(dalbp_mt_grad, fp)
        + 0.22 * _robust_z_pos(multiphys_junction, fp)
        + 0.16 * _robust_z_pos(bfrc_hinge, fp)
    ).astype(np.float32)
    subsurf_gate_2d[~fp] = 0.0

    # Block 7: Label-free GDR #1391 hydrothermal conduits (`dist_known_fault_px` stripped!)
    strike_deg = np.rad2deg(strike_sub_rad).astype(np.float32)
    hyd_grids, hyd_stats = build_hydrothermal_grids(
        raw_dir=DATA_DIR,
        fp=fp,
        transform=transform,
        uy=uy_up,
        ux=ux_up,
        strike_deg=strike_deg,
        rad_k_z=rad_k_z,
        ext_thk_z=ext_thk_z,
        rtp_filled=rtp,
        updip_subsurf_z=subsurf_gate_2d,
    )

    transtension = (
        keep_2d["org_geod_dilaterate"] * keep_2d["org_geod_shearrate"]
        + 0.25 * np.log1p(np.maximum(keep_2d["org_ieq_n100a15"], 0.0)) * keep_2d["org_geod_2ndinv"]
    ).astype(np.float32)
    transtension[~fp] = 0.0

    hyd_upflow = (
        0.36 * hyd_grids["hyd_sinter_throat"]
        + 0.34 * hyd_grids["hyd_probe2m_f2mdab"]
        + 0.30 * hyd_grids["hyd_geotherm_updip"]
    )
    volc_damp = 1.0 / (1.0 + 0.25 * hyd_grids["hyd_volc_dike_worm"])
    junction_upflow = (
        np.sqrt(np.maximum(0.0, hyd_upflow * (0.55 * multiphys_junction + 0.45 * dalbp_playa))) * volc_damp
    ).astype(np.float32)
    junction_upflow[~fp] = 0.0

    # Save label-free Regime-B intrabasinal/junction mask & Stage-2 subsurface+hydrothermal gate
    regime_b_prior_2d = (
        0.42 * _robust_z_pos(dalbp_playa, fp)
        + 0.30 * _robust_z_pos(junction_upflow, fp)
        + 0.28 * _robust_z_pos(multiphys_junction, fp)
    ).astype(np.float32)
    np.save(WORK_DIR / "regime_b_prior_fp.npy", regime_b_prior_2d.ravel()[fp_ids])
    np.save(
        WORK_DIR / "stage2_subsurf_hydro_gate_fp.npy",
        (0.60 * subsurf_gate_2d + 0.40 * _robust_z_pos(junction_upflow, fp)).ravel()[fp_ids].astype(np.float32),
    )
    np.save(WORK_DIR / "dem_strike_rad_fp.npy", strike_dem_rad.ravel()[fp_ids].astype(np.float32))

    contour_obliq = (obliq * np.sqrt(np.maximum(dem10_2d["dem10_hgm50_max"], 0.0))).astype(np.float32)
    contour_obliq[~fp] = 0.0

    for cname, arr2d in [
        ("anti_contour_obliquity", contour_obliq),
        ("anti_tiger_logdist", tiger_logdist),
        ("anti_thalweg_convexity", thalweg_conv),
        ("tect_walker_transtension", transtension),
        ("hyd_sinter_throat", hyd_grids["hyd_sinter_throat"]),
        ("hyd_probe2m_f2mdab", hyd_grids["hyd_probe2m_f2mdab"]),
        ("hyd_wellspring_geotherm", hyd_grids["hyd_geotherm_updip"]),
        ("hyd_junction_upflow_index", junction_upflow),
    ]:
        mm[:, IDX[cname]] = arr2d.ravel()[fp_ids].astype(np.float32)

    mm.flush()
    del keep_2d, dem10_2d, hyd_grids
    gc.collect()

    meta = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "lane_id": "WBG-4",
        "method_code": "CSJF-1",
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
        "peer_rasters_used_in_features": False,
        "banned_columns_stripped": ["dist_known_fault_px", "fault_id", "qfault_id"],
        "memmap_sha256": sha256(mmap_path),
    }
    dump_json(meta_path, meta)
    return meta
