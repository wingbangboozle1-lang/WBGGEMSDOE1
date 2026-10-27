"""Physical feature operators for WBG-3 (SPI-PMR-WCS-1).

Strict Anti-Leakage Contract:
  - Static 36-channel stack reads ONLY `data/template57/` (19 cached official bands),
    `data/external/geodawn_rad_u8.tif`, `data/external/geodawn_extensions_u8.tif`,
    and OpenEI GDR 1391 point compilations with all fault-distance/label columns stripped.
  - Zero channels from `lidar_scarp_features_u8.tif`, `labels.tif`, `existing_faults.tif`,
    `derived_sgmc_faults_100m_u8.tif`, or any prior submission raster enter the static stack.
  - Dynamic 4-channel `wcs_*` structural mechanics receive ONLY a fold's `visible` fault mask.
"""

from __future__ import annotations

import csv
import gc
import io
import math
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer
from scipy.fft import irfft2, rfft2
from scipy.ndimage import (
    convolve,
    distance_transform_edt,
    gaussian_filter,
    label as ndi_label,
)
from scipy.spatial import cKDTree

from wbggems1.features import BAND_ORDER, BANNED_CSV_COLUMNS, SENTINEL_CUT, _parse_dbf_records

ORG_NAMES: tuple[str, ...] = tuple(f"org_{b}" for b in BAND_ORDER)

SPI_NAMES: tuple[str, ...] = (
    "spi_mag_k",
    "spi_grav_k",
    "spi_joint_coherence",
    "spi_shallow_mag_decay",
    "spi_basement_hinge",
)

PPDR_NAMES: tuple[str, ...] = (
    "ppdr_mag_destruction",
    "ppdr_clay_alteration_x",
    "ppdr_k_th_metasomatism",
    "ppdr_u_th_redox",
)

PC_NAMES: tuple[str, ...] = (
    "pc_elev_step",
    "pc_elev_coherence",
    "pc_strike_cos2",
    "pc_strike_sin2",
    "pc_basement_step",
)

HYD_NAMES: tuple[str, ...] = (
    "hyd_thermal_spring_req",
    "hyd_probe2m_sinter_req",
    "hyd_strain_conduit_x",
)

STATIC_FEATURE_NAMES: tuple[str, ...] = ORG_NAMES + SPI_NAMES + PPDR_NAMES + PC_NAMES + HYD_NAMES

WCS_FEATURE_NAMES: tuple[str, ...] = (
    "wcs_wing_crack_lobe",
    "wcs_relay_stepover",
    "wcs_echelon_halo",
    "wcs_orphan_hydro_boost",
)

ALL_FEATURE_NAMES: tuple[str, ...] = STATIC_FEATURE_NAMES + WCS_FEATURE_NAMES


def _nearest_fill(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Label-free nearest-neighbor continuation outside valid cells for FFT/derivative stencils."""
    if valid.all():
        return arr.astype(np.float32, copy=False)
    inds = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return arr[tuple(inds)].astype(np.float32)


def _robust_z(arr: np.ndarray, valid: np.ndarray, clip: float = 8.0) -> np.ndarray:
    vals = arr[valid & np.isfinite(arr)]
    if vals.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    med = float(np.median(vals))
    iqr = float(np.percentile(vals, 75.0) - np.percentile(vals, 25.0))
    scale = max(iqr / 1.349, 1e-6)
    z = (np.nan_to_num(arr, nan=med) - med) / scale
    return np.clip(z, -clip, clip).astype(np.float32)


def _pos_z(arr: np.ndarray, valid: np.ndarray, clip: float = 8.0) -> np.ndarray:
    return np.maximum(_robust_z(arr, valid, clip=clip), 0.0).astype(np.float32)


def _grad_mag(arr: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    sm = gaussian_filter(arr.astype(np.float32), sigma) if sigma > 0 else arr.astype(np.float32)
    gy, gx = np.gradient(sm)
    return np.hypot(gy, gx).astype(np.float32)


def _edge_taper(shape: tuple[int, int], width: int = 24) -> np.ndarray:
    """Cosine border apodization preventing wrap-around ringing in 2D FFT operators."""
    h, w = shape
    wy = np.ones(h, dtype=np.float32)
    wx = np.ones(w, dtype=np.float32)
    t = 0.5 * (1.0 - np.cos(np.pi * np.arange(width, dtype=np.float32) / float(width)))
    wy[:width] = t
    wy[-width:] = t[::-1]
    wx[:width] = t
    wx[-width:] = t[::-1]
    return wy[:, None] * wx[None, :]


def _fft_radial_grids(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return radial angular wavenumber K (rad/px) and Riesz multipliers (Ry, Rx) for rfft2."""
    h, w = shape
    ky = (2.0 * np.pi * np.fft.fftfreq(h)).astype(np.float32)[:, None]
    kx = (2.0 * np.pi * np.fft.rfftfreq(w)).astype(np.float32)[None, :]
    k_rad = np.hypot(ky, kx).astype(np.float32)
    inv_k = 1.0 / np.maximum(k_rad, 1e-6)
    inv_k[0, 0] = 0.0
    ry = (-1j * ky * inv_k).astype(np.complex64)
    rx = (-1j * kx * inv_k).astype(np.complex64)
    return k_rad, ry, rx


def compute_monogenic_pc(
    field_filled: np.ndarray,
    fp: np.ndarray,
    wavelengths_px: tuple[float, ...],
    *,
    sigma_on_f: float = 0.55,
    k_noise_mult: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """2D FFT Log-Gabor Riesz Monogenic Phase Congruency (Morrone & Owens 1987; Kovesi 1999).

    Returns (pc_step, pc_total, cos2_strike, sin2_strike) as float32 grids.
    """
    h, w = field_filled.shape
    detrended = field_filled - gaussian_filter(field_filled, max(wavelengths_px) * 1.5)
    tapered = (detrended * _edge_taper((h, w), 24)).astype(np.float32)
    F = rfft2(tapered, workers=2).astype(np.complex64)
    k_rad, ry, rx = _fft_radial_grids((h, w))
    log_denom = 2.0 * (math.log(sigma_on_f) ** 2)

    sum_e = np.zeros((h, w), dtype=np.float32)
    sum_oy = np.zeros((h, w), dtype=np.float32)
    sum_ox = np.zeros((h, w), dtype=np.float32)
    sum_amp = np.zeros((h, w), dtype=np.float32)
    noise_t = 0.0

    for idx, wl in enumerate(wavelengths_px):
        w0 = 2.0 * math.pi / float(wl)
        with np.errstate(divide="ignore"):
            lg = np.where(
                k_rad > 0.0,
                np.exp(-((np.log(np.maximum(k_rad, 1e-9) / w0)) ** 2) / log_denom),
                0.0,
            ).astype(np.float32)
        lg[0, 0] = 0.0
        band_f = F * lg
        even = irfft2(band_f, s=(h, w), workers=2).astype(np.float32)
        odd_y = irfft2(band_f * ry, s=(h, w), workers=2).astype(np.float32)
        odd_x = irfft2(band_f * rx, s=(h, w), workers=2).astype(np.float32)
        amp = np.sqrt(even * even + odd_y * odd_y + odd_x * odd_x)
        if idx == 0:
            # Kovesi Rayleigh median-energy noise threshold on finest scale
            med_a = float(np.median(amp[fp]))
            tau = med_a / math.sqrt(math.log(4.0))
            noise_t = k_noise_mult * tau * (1.0 - (0.5 ** len(wavelengths_px))) / 0.5
        sum_e += even
        sum_oy += odd_y
        sum_ox += odd_x
        sum_amp += amp
        del lg, band_f, even, odd_y, odd_x, amp

    odd_mag = np.hypot(sum_oy, sum_ox)
    even_abs = np.abs(sum_e)
    energy_total = np.hypot(sum_e, odd_mag)
    denom = sum_amp + 1e-4

    # Asymmetric step phase congruency: odd > |even| isolates step scarps & suppresses symmetric washes
    pc_step = np.clip((odd_mag - 0.65 * even_abs - noise_t) / denom, 0.0, 1.0).astype(np.float32)
    pc_total = np.clip((energy_total - noise_t) / denom, 0.0, 1.0).astype(np.float32)

    # Strike direction is perpendicular to the odd Riesz gradient vector (sum_oy, sum_ox)
    # If grad = (oy, ox), strike = (-ox, oy), so cos(2*strike) = (ox^2 - oy^2)/|o|^2? Wait:
    # Let strike angle alpha from East (x-axis): tx = -oy/|o|, ty = ox/|o|.
    # Then cos(2*alpha) = tx^2 - ty^2 = (oy^2 - ox^2)/|o|^2, sin(2*alpha) = 2*tx*ty = -2*ox*oy/|o|^2.
    o_sq = np.maximum(odd_mag * odd_mag, 1e-8)
    cos2 = ((sum_oy * sum_oy - sum_ox * sum_ox) / o_sq).astype(np.float32)
    sin2 = ((-2.0 * sum_ox * sum_oy) / o_sq).astype(np.float32)
    return pc_step, pc_total, cos2, sin2


def compute_spi_and_ppdr(
    kept: dict[str, np.ndarray],
    tmi_up150_filled: np.ndarray,
    rad_k: np.ndarray,
    rad_th: np.ndarray,
    rad_u: np.ndarray,
    fp: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute Thurston-Smith (1997) SPI local wavenumber and Cordell-Taylor (1971) PPDR channels."""
    h, w = fp.shape

    # 1. Magnetic SPI local wavenumber k_mag = |grad atan2(VG, HG)|
    mag_hg = np.maximum(kept["tmi_hg"], 0.0)
    mag_vg = kept["tmi_vg"]
    theta_mag = np.arctan2(
        gaussian_filter(mag_vg, 1.0),
        np.maximum(gaussian_filter(mag_hg, 1.0), 1e-4),
    ).astype(np.float32)
    spi_mag_k = _pos_z(_grad_mag(theta_mag, sigma=0.8), fp)
    del theta_mag

    # 2. Isostatic gravity SPI local wavenumber k_grav = |grad atan2(VG, HG)|
    grav_hg = np.maximum(kept["iso_grav_anom_hg"], 0.0)
    grav_vg = kept["iso_grav_anom_vg"]
    theta_grav = np.arctan2(
        gaussian_filter(grav_vg, 1.0),
        np.maximum(gaussian_filter(grav_hg, 1.0), 1e-4),
    ).astype(np.float32)
    spi_grav_k = _pos_z(_grad_mag(theta_grav, sigma=0.8), fp)
    del theta_grav

    # 3. Upward-continued 150 m TMI local wavenumber for shallow crustal fault decay
    up_det = (tmi_up150_filled - gaussian_filter(tmi_up150_filled, 40.0)) * _edge_taper((h, w), 24)
    k_rad, _, _ = _fft_radial_grids((h, w))
    F_up = rfft2(up_det.astype(np.float32), workers=2).astype(np.complex64)
    up_vg = irfft2(F_up * k_rad, s=(h, w), workers=2).astype(np.float32)
    up_hg = _grad_mag(tmi_up150_filled, sigma=1.2)
    theta_up = np.arctan2(gaussian_filter(up_vg, 1.0), np.maximum(up_hg, 1e-5)).astype(np.float32)
    spi_up_k = _pos_z(_grad_mag(theta_up, sigma=0.8), fp)
    spi_shallow_mag_decay = _pos_z(np.maximum(spi_mag_k - 0.80 * spi_up_k, 0.0), fp)
    del up_det, F_up, up_vg, up_hg, theta_up, spi_up_k

    # 4. Co-located magnetic x gravity SPI contact coherence & basement hinge
    spi_joint_coherence = _pos_z(np.sqrt(np.maximum(spi_mag_k * spi_grav_k, 0.0)), fp)
    base_sm = gaussian_filter(kept["depth_to_base_surf"], 2.0)
    byy = np.gradient(np.gradient(base_sm, axis=0), axis=0)
    bxx = np.gradient(np.gradient(base_sm, axis=1), axis=1)
    bxy = np.gradient(np.gradient(base_sm, axis=0), axis=1)
    kmax_base = 0.5 * np.abs(byy + bxx) + np.hypot(0.5 * (byy - bxx), bxy)
    spi_basement_hinge = _pos_z(
        _pos_z(kmax_base.astype(np.float32), fp) * (0.4 + 0.6 * np.tanh(spi_grav_k / 2.0)), fp
    )
    del base_sm, byy, bxx, bxy, kmax_base

    # 5. Cordell-Taylor FFT Poisson Pseudogravity from RTP: g_pseudo = IFFT[ FFT(RTP) / (|k| + k0) ]
    rtp_det = (kept["rtp"] - gaussian_filter(kept["rtp"], 60.0)) * _edge_taper((h, w), 24)
    F_rtp = rfft2(rtp_det.astype(np.float32), workers=2).astype(np.complex64)
    k0 = float(2.0 * math.pi / 400.0)  # 40 km regional stabilization wavelength (400 px)
    inv_poisson = (1.0 / (k_rad + k0)).astype(np.float32)
    inv_poisson[0, 0] = 0.0
    g_pseudo = irfft2(F_rtp * inv_poisson, s=(h, w), workers=2).astype(np.float32)
    g_pseudo_hg_z = _pos_z(_grad_mag(g_pseudo, sigma=1.5), fp)
    grav_hg_z = _pos_z(grav_hg, fp)

    ppdr_mag_destruction = _pos_z(np.maximum(grav_hg_z - 0.75 * g_pseudo_hg_z, 0.0), fp)
    cond_z = _pos_z(kept["cond_surf"], fp)
    ppdr_clay_alteration_x = _pos_z(np.sqrt(np.maximum(ppdr_mag_destruction * cond_z, 0.0)), fp)

    k_th_lr = _pos_z(np.log((np.maximum(rad_k, 0.0) + 0.03) / (np.maximum(rad_th, 0.0) + 0.03)), fp)
    u_th_lr = _pos_z(np.log((np.maximum(rad_u, 0.0) + 0.03) / (np.maximum(rad_th, 0.0) + 0.03)), fp)
    ppdr_k_th_metasomatism = _pos_z(
        k_th_lr * (0.40 + 0.60 * np.tanh(ppdr_mag_destruction / 2.0)), fp
    )
    ppdr_u_th_redox = u_th_lr
    del rtp_det, F_rtp, inv_poisson, g_pseudo, g_pseudo_hg_z, grav_hg_z, cond_z, k_th_lr, k_rad

    return {
        "spi_mag_k": spi_mag_k,
        "spi_grav_k": spi_grav_k,
        "spi_joint_coherence": spi_joint_coherence,
        "spi_shallow_mag_decay": spi_shallow_mag_decay,
        "spi_basement_hinge": spi_basement_hinge,
        "ppdr_mag_destruction": ppdr_mag_destruction,
        "ppdr_clay_alteration_x": ppdr_clay_alteration_x,
        "ppdr_k_th_metasomatism": ppdr_k_th_metasomatism,
        "ppdr_u_th_redox": ppdr_u_th_redox,
    }


def _splat_points(shape: tuple[int, int], pts: list[tuple[int, int, float]]) -> np.ndarray:
    grid = np.zeros(shape, dtype=np.float32)
    h, w = shape
    for r, c, wt in pts:
        if 0 <= r < h and 0 <= c < w and wt > grid[r, c]:
            grid[r, c] = np.float32(wt)
    return grid


def compute_hydrothermal_channels(
    data_dir: Path,
    fp: np.ndarray,
    transform: rasterio.Affine,
    geod_2ndinv_filled: np.ndarray,
    deq_filled: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    """Build 3 label-free OpenEI GDR 1391 hydrothermal conduit requirement fields."""
    h, w = fp.shape
    nad83_to_utm11 = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
    inv_tr = ~transform

    def lonlat_to_rc(lon: float, lat: float) -> tuple[int, int]:
        ex, ny = nad83_to_utm11.transform(lon, lat)
        col_f, row_f = inv_tr * (ex, ny)
        return int(math.floor(row_f)), int(math.floor(col_f))

    # 1. Springs & wells temperature + chemical geothermometers (strip dist_known_fault_px)
    ws_pts: list[tuple[int, int, float]] = []
    with (data_dir / "external" / "gdr_wellspring_in_footprint.csv").open(
        "r", encoding="utf-8", errors="replace"
    ) as f:
        reader = csv.DictReader(f)
        safe_fields = [fn for fn in (reader.fieldnames or []) if fn.lower() not in BANNED_CSV_COLUMNS]
        assert "dist_known_fault_px" not in safe_fields
        for raw_row in reader:
            row = {k: raw_row[k] for k in safe_fields}
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError):
                continue
            if not (0 <= r < h and 0 <= c < w and fp[r, c]):
                continue
            temps = []
            for tk in ("temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                try:
                    tv = float(row.get(tk, "nan"))
                    if math.isfinite(tv) and 25.0 <= tv < 350.0:
                        temps.append(tv)
                except ValueError:
                    pass
            if temps and max(temps) >= 30.0:
                ws_pts.append((r, c, min(math.log1p((max(temps) - 25.0) / 15.0), 3.0)))

    ws_imp = _splat_points((h, w), ws_pts)
    hyd_thermal_spring_req = _pos_z(
        0.55 * gaussian_filter(ws_imp, 5.0) + 0.45 * gaussian_filter(ws_imp, 14.0), fp
    )
    del ws_imp

    # 2. 2 m temperature probes + paleo-geothermal sinter/travertine/silicified breccia
    ps_pts: list[tuple[int, int, float]] = []
    with zipfile.ZipFile(
        data_dir / "external" / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    ) as zf:
        dbf_bytes = zf.read(
            "2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf"
        )
        for rec in _parse_dbf_records(dbf_bytes):
            try:
                lon = float(rec["LongDegree"])
                lat = float(rec["LatDegreeN"])
                dab = float(rec["F2mDAB"])
            except (KeyError, ValueError):
                continue
            if math.isfinite(dab) and dab >= 1.0:
                r, c = lonlat_to_rc(lon, lat)
                if 0 <= r < h and 0 <= c < w and fp[r, c]:
                    ps_pts.append((r, c, min(math.log1p(dab), 3.0)))

    with zipfile.ZipFile(data_dir / "external" / "paleo_geothermal_regional.zip") as zf:
        txt = zf.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
        for row in csv.DictReader(io.StringIO(txt)):
            for k in list(row.keys()):
                if k and k.lower() in BANNED_CSV_COLUMNS:
                    del row[k]
            try:
                lon = float(row["Long_deg_NAD83"])
                lat = float(row["Lat_deg_NAD83"])
            except (KeyError, ValueError):
                continue
            r, c = lonlat_to_rc(lon, lat)
            if not (0 <= r < h and 0 <= c < w and fp[r, c]):
                continue
            dtype = (row.get("Deposit_type") or "").strip()
            comments = (row.get("Comments") or "").lower()
            if dtype in {"Sinter", "Explosion craters", "Silicified fault breccia"}:
                wt = 2.2
            elif dtype == "Tufa" and "lahontan" in comments:
                wt = 0.25
            else:
                wt = 1.1
            ps_pts.append((r, c, wt))

    ps_imp = _splat_points((h, w), ps_pts)
    hyd_probe2m_sinter_req = _pos_z(
        0.60 * gaussian_filter(ps_imp, 4.5) + 0.40 * gaussian_filter(ps_imp, 12.0), fp
    )
    del ps_imp

    # 3. Active strain x hydrothermal upflow interaction
    strain_z = 0.65 * _pos_z(geod_2ndinv_filled, fp) + 0.35 * _pos_z(deq_filled, fp)
    hyd_sum = 0.55 * hyd_thermal_spring_req + 0.45 * hyd_probe2m_sinter_req
    hyd_strain_conduit_x = _pos_z(np.sqrt(np.maximum(strain_z * hyd_sum, 0.0)), fp)

    return (
        {
            "hyd_thermal_spring_req": hyd_thermal_spring_req,
            "hyd_probe2m_sinter_req": hyd_probe2m_sinter_req,
            "hyd_strain_conduit_x": hyd_strain_conduit_x,
        },
        {"wellspring_points": len(ws_pts), "probe_and_paleo_points": len(ps_pts)},
    )


def compute_visible_wcs_channels(
    visible_mask: np.ndarray,
    fp: np.ndarray,
    strain_mod: np.ndarray,
    hyd_union: np.ndarray,
    *,
    min_trunk_px: int = 8,
) -> dict[str, np.ndarray]:
    """Compute 4 fold-safe structural relay & orphan-hydrothermal channels strictly from `visible_mask`.

    Never reads hidden truth or any global catalogue mask.
    """
    vis = np.asarray(visible_mask, dtype=bool) & fp
    h, w = fp.shape
    d_vis = distance_transform_edt(~vis).astype(np.float32)

    # 1. Extract visible trunks (>= min_trunk_px) and their morphological tips + outward tangents
    comp, n_comp = ndi_label(vis, structure=np.ones((3, 3), dtype=np.int8))
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)
    keep_comp = sizes >= min_trunk_px
    keep_comp[0] = False
    trunks = keep_comp[comp]

    # Count 8-connected neighbors among trunk pixels
    nbr_k = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int16)
    nbr_cnt = convolve(trunks.astype(np.int16), nbr_k, mode="constant", cval=0)
    tip_mask = trunks & (nbr_cnt == 1)
    ty_arr, tx_arr = np.nonzero(tip_mask)

    wing_grid = np.zeros((h, w), dtype=np.float32)
    relay_grid = np.zeros((h, w), dtype=np.float32)

    tips_yx: list[tuple[int, int, float, float]] = []
    for ty, tx in zip(ty_arr.tolist(), tx_arr.tolist()):
        cid = int(comp[ty, tx])
        y0, y1 = max(0, ty - 6), min(h, ty + 7)
        x0, x1 = max(0, tx - 6), min(w, tx + 7)
        sub_y, sub_x = np.nonzero(comp[y0:y1, x0:x1] == cid)
        if sub_y.size < 3:
            continue
        cy = float(y0 + sub_y.mean())
        cx = float(x0 + sub_x.mean())
        vy = float(ty) - cy
        vx = float(tx) - cx
        norm = math.hypot(vy, vx)
        if norm < 0.5:
            continue
        tips_yx.append((ty, tx, vy / norm, vx / norm))

    # Prebuild local coordinate mesh [-24..24] for fast wing-crack lobe stamping
    R = 24
    oy, ox = np.mgrid[-R : R + 1, -R : R + 1].astype(np.float32)
    rr = np.hypot(oy, ox)
    rad_env = np.where((rr >= 2.5) & (rr <= 24.0), np.exp(-rr / 10.0), 0.0).astype(np.float32)

    for ty, tx, uy, ux in tips_yx:
        u = oy * uy + ox * ux
        v = -oy * ux + ox * uy
        psi = np.abs(np.arctan2(v, np.maximum(u, 1e-5)))
        # Pollard-Segall off-axis tensile wing-crack lobes peak at +-30 deg (pi/6 rad) ahead of tip
        lobe = np.where(
            u > 0.5,
            rad_env * np.exp(-((psi - (math.pi / 6.0)) ** 2) / (2.0 * (0.38 ** 2))),
            0.0,
        ).astype(np.float32)
        y0, y1 = max(0, ty - R), min(h, ty + R + 1)
        x0, x1 = max(0, tx - R), min(w, tx + R + 1)
        ly0, ly1 = y0 - (ty - R), R + (y1 - ty)
        lx0, lx1 = x0 - (tx - R), R + (x1 - tx)
        patch = wing_grid[y0:y1, x0:x1]
        np.maximum(patch, lobe[ly0:ly1, lx0:lx1], out=patch)

    # Modulate wing-crack stress by geodetic shear/dilatation rate and suppress inside <=2 px collar
    wing_grid *= (0.45 + 0.55 * strain_mod) * (d_vis > 2.0).astype(np.float32)

    # 2. En-echelon relay-ramp step-over bridges between visible tips within [4, 35] px (0.4 - 3.5 km)
    if len(tips_yx) >= 2:
        pts = np.array([(t[0], t[1]) for t in tips_yx], dtype=np.float32)
        vecs = np.array([(t[2], t[3]) for t in tips_yx], dtype=np.float32)
        tree = cKDTree(pts)
        pairs = tree.query_pairs(r=35.0, output_type="ndarray")
        for i, j in pairs:
            dy = pts[j, 0] - pts[i, 0]
            dx = pts[j, 1] - pts[i, 1]
            dist = float(math.hypot(dy, dx))
            if dist < 4.0:
                continue
            align = abs(float(vecs[i, 0] * vecs[j, 0] + vecs[i, 1] * vecs[j, 1]))
            if align < 0.45:
                continue
            # Check lateral step-over offset perpendicular to mean strike
            lat = abs(dy * (-vecs[i, 1]) + dx * vecs[i, 0])
            if not (2.0 <= lat <= 20.0):
                continue
            # Deposit points along the relay bridge
            n_steps = max(int(dist), 4)
            strength = float(align * math.exp(-dist / 18.0))
            for s in range(1, n_steps):
                frac = s / float(n_steps)
                ry_i = int(round(pts[i, 0] + frac * dy))
                rx_i = int(round(pts[i, 1] + frac * dx))
                if 0 <= ry_i < h and 0 <= rx_i < w and strength > relay_grid[ry_i, rx_i]:
                    relay_grid[ry_i, rx_i] = strength
        relay_grid = gaussian_filter(relay_grid, 2.2) * (d_vis > 2.0).astype(np.float32)

    wcs_wing = _pos_z(wing_grid, fp) if np.any(wing_grid > 0) else wing_grid
    wcs_relay = _pos_z(relay_grid, fp) if np.any(relay_grid > 0) else relay_grid

    # 3. Off-catalogue synthetic/antithetic echelon damage corridor peaking at ~800 m (8 px)
    wcs_halo = (
        np.exp(-((d_vis - 8.0) ** 2) / (2.0 * (6.0 ** 2))) * (d_vis > 2.2) * fp
    ).astype(np.float32)

    # 4. Orphan hydrothermal anomaly amplifier (thermal anomaly far from visible faults requires unmapped fault)
    wcs_orphan = (
        hyd_union * np.tanh(np.maximum(d_vis - 3.0, 0.0) / 8.0) * (d_vis > 2.0) * fp
    ).astype(np.float32)

    return {
        "wcs_wing_crack_lobe": wcs_wing,
        "wcs_relay_stepover": wcs_relay,
        "wcs_echelon_halo": wcs_halo,
        "wcs_orphan_hydro_boost": wcs_orphan,
    }


def build_static_feature_memmap(
    data_dir: Path,
    work_dir: Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Build or verify the 36-channel static float32 footprint memmap in `work_dir`."""
    work_dir.mkdir(parents=True, exist_ok=True)
    mmap_path = work_dir / "wbg3_static_36ch.npy"

    with rasterio.open(data_dir / "sample_submission.tif") as tmpl:
        assert tmpl.crs.to_epsg() == 32611 and (tmpl.height, tmpl.width) == (3730, 3292)
        transform = tmpl.transform
        fp = np.isfinite(tmpl.read(1))

    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = int(fp_ids.size)
    n_cols = len(STATIC_FEATURE_NAMES)

    if mmap_path.exists() and not force:
        mm = np.load(mmap_path, mmap_mode="r")
        if mm.shape == (n_fp, n_cols):
            return {"mmap_path": str(mmap_path), "n_fp": n_fp, "n_cols": n_cols, "cached": True}

    tmp_path = work_dir / "wbg3_static_36ch.partial.npy"
    mm = np.lib.format.open_memmap(tmp_path, mode="w+", dtype=np.float32, shape=(n_fp, n_cols))

    kept: dict[str, np.ndarray] = {}
    sentinel_counts: dict[str, int] = {}

    # Columns 0..18: 19 official competition bands from verified shared cache (`data/template57/`)
    cache_dir = data_dir / "template57"
    for i, bname in enumerate(BAND_ORDER):
        band_file = cache_dir / f"band_{i + 1:02d}_{bname}.npy"
        if band_file.exists():
            raw = np.load(band_file).astype(np.float32)
        else:
            with rasterio.open(data_dir / "training_features.tif") as ds:
                raw = ds.read(i + 1).astype(np.float32)
        valid = fp & np.isfinite(raw) & (raw > SENTINEL_CUT)
        sentinel_counts[bname] = int((fp & ~valid).sum())
        filled = _nearest_fill(np.where(valid, raw, np.nan).astype(np.float32), valid)
        mm[:, i] = filled.ravel()[fp_ids]
        if bname in {
            "rtp",
            "tmi_hg",
            "tmi_vg",
            "iso_grav_anom",
            "iso_grav_anom_hg",
            "iso_grav_anom_vg",
            "depth_to_base_surf",
            "cond_surf",
            "det_elev",
            "geod_shearrate",
            "geod_dilaterate",
            "geod_2ndinv",
            "deq_n100a15",
        }:
            kept[bname] = filled
        del raw

    # External GeoDAWN radiometrics + 150 m upward-continued TMI
    with rasterio.open(data_dir / "external" / "geodawn_rad_u8.tif") as ds:
        rad_arrs = []
        for b_idx in (1, 2, 3):  # K, Th, U
            q = ds.read(b_idx)
            v = fp & (q > 0)
            a = np.where(v, (q.astype(np.float32) - 1.0) / 254.0, np.nan).astype(np.float32)
            rad_arrs.append(_nearest_fill(a, v))
            del q, a
    rad_k, rad_th, rad_u = rad_arrs

    with rasterio.open(data_dir / "external" / "geodawn_extensions_u8.tif") as ds:
        q = ds.read(4)  # gd_TMI_up150
        v = fp & (q > 0)
        tmi_up150 = _nearest_fill(
            np.where(v, (q.astype(np.float32) - 1.0) / 254.0, np.nan).astype(np.float32), v
        )
        del q

    # Columns 19..27: SPI (5) + PPDR (4)
    spi_ppdr = compute_spi_and_ppdr(kept, tmi_up150, rad_k, rad_th, rad_u, fp)
    col = 19
    for cname in SPI_NAMES + PPDR_NAMES:
        mm[:, col] = spi_ppdr[cname].ravel()[fp_ids]
        col += 1
    del spi_ppdr, rad_k, rad_th, rad_u, tmi_up150
    gc.collect()

    # Columns 28..32: 2D FFT Riesz Monogenic Phase Congruency (5)
    pc_step, pc_tot, pc_cos2, pc_sin2 = compute_monogenic_pc(
        kept["det_elev"], fp, wavelengths_px=(3.0, 6.0, 12.0)
    )
    pc_base_step, _, _, _ = compute_monogenic_pc(
        kept["depth_to_base_surf"], fp, wavelengths_px=(6.0, 15.0, 30.0)
    )
    for arr in (pc_step, pc_tot, pc_cos2, pc_sin2, pc_base_step):
        mm[:, col] = arr.ravel()[fp_ids]
        col += 1
    del pc_step, pc_tot, pc_cos2, pc_sin2, pc_base_step
    gc.collect()

    # Columns 33..35: GDR 1391 Hydrothermal Conduit Requirement (3)
    hyd_dict, hyd_stats = compute_hydrothermal_channels(
        data_dir, fp, transform, kept["geod_2ndinv"], kept["deq_n100a15"]
    )
    for cname in HYD_NAMES:
        mm[:, col] = hyd_dict[cname].ravel()[fp_ids]
        col += 1
    assert col == n_cols

    mm.flush()
    del mm
    tmp_path.replace(mmap_path)
    return {
        "mmap_path": str(mmap_path),
        "n_fp": n_fp,
        "n_cols": n_cols,
        "sentinel_counts": sentinel_counts,
        "hydrothermal_point_counts": hyd_stats,
        "cached": False,
    }
