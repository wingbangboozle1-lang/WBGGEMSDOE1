"""Label-free, memory-safe 66-channel DPGF-1 feature engineering for WBGGEMSDOE1.

Implements the pre-registered WBG-H1 (DPGF-1) physical operators:
  1. Updip Subsurface-to-Surface Back-Projection (DipShift 500 m / 600 m / 1,000 m)
     compensating for 50-65 deg basinward fault dip so subsurface gravity, magnetic
     tilt, and MT conductance steps align with surface fault traces within the 300 m
     DTI kernel.
  2. Tectonic-to-Fluvial Scarp Discrimination Index (TFSDI) & Graben Dipole using
     3DEP 1 m LiDAR upface_max, downface_max, cross_max, lapneg_max, lappos_max, coh100.
  3. 0 -> 150 m Upward-Continued Magnetic Persistence (with E-W flight-line notch),
     MT Smectite Clay-Cap Lateral Perimeter, Walker Lane Transtensional Obliquity,
     8-Azimuth 1.5 km Strike-Anisotropy Worms, and OpenEI GDR 1391 INGENIOUS
     Hydrothermal Upflow Back-Projection.

Strict Anti-Leakage Contract:
  - Never reads labels.tif, existing_faults.tif, derived_sgmc_faults_100m_u8.tif,
    gdr_qfaults_traces.csv, or any registry/scored submission raster.
  - Explicitly refuses/strips `dist_known_fault_px` when parsing GDR CSVs.
"""

from __future__ import annotations

import csv
import gc
import io
import json
import math
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

from gems.geofeatures import BAND_ORDER
from wbggems1.paths import raw_data_dir, repo_root, work_dir

SENTINEL_CUT = -1e30
N_AZIMUTHS = 8
WORM_HALF_PX = 7  # 15 px = 1.5 km lineament stencil

LIDAR_SPECS: list[tuple[str, float, str]] = [
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
]

RAD_NAMES = ("gd_K", "gd_Th", "gd_U", "gd_TC")
EXT_NAMES = ("gd_ThK", "gd_UK", "gd_UTh", "gd_TMI_up150")

MS_NAMES = (
    "ms_det_local_relief_500m",
    "ms_det_local_relief_1500m",
    "ms_piedmont_inflection",
    "ms_mag_miller_tilt",
    "ms_mag_tilt_grad",
    "ms_grav_miller_tilt",
    "ms_grav_tilt_grad",
    "ms_mag_persist_150m",
    "ms_basement_step_grad",
    "ms_mt_claycap_perim",
)

DPGF_NAMES = (
    "dpgf_grav_updip_500m",
    "dpgf_grav_updip_1000m",
    "dpgf_mag_updip_600m",
    "dpgf_mt_updip_600m",
    "dpgf_dip_surface_coupling",
    "dpgf_tfsdi_scarp",
    "dpgf_graben_crest_base",
    "dpgf_transtens_obliq",
    "dpgf_worm_subsurf_1p5km",
    "dpgf_worm_piedmont_1p5km",
)

HYD_NAMES = (
    "hyd_sinter_throat",
    "hyd_apron_updip",
    "hyd_probe2m_f2mdab",
    "hyd_geotherm_updip",
    "hyd_volc_dike_worm",
    "hyd_rad_k_th_adularia",
    "hyd_conduit_subsurf_x",
)

FEATURE_NAMES: tuple[str, ...] = (
    tuple(f"org_{b}" for b in BAND_ORDER)
    + tuple(f"lid_{n}" for n, _, _ in LIDAR_SPECS)
    + ("lid_cos2strike", "lid_sin2strike")
    + RAD_NAMES
    + EXT_NAMES
    + MS_NAMES
    + DPGF_NAMES
    + HYD_NAMES
)

BASELINE_31_INDICES: tuple[int, ...] = tuple(range(31))

BANNED_CSV_COLUMNS = frozenset(
    {"dist_known_fault_px", "fault_dist", "dist_fault", "label", "labels", "existing_faults"}
)


def _nearest_fill(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Label-free nearest-neighbor edge continuation for spatial derivative stencils."""
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


def _grad_mag(arr_filled: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    sm = gaussian_filter(arr_filled.astype(np.float32), sigma) if sigma > 0 else arr_filled
    gy, gx = np.gradient(sm)
    return np.hypot(gy, gx).astype(np.float32)


def _advect_updip(field_2d: np.ndarray, uy: np.ndarray, ux: np.ndarray, shift_px: float) -> np.ndarray:
    """Evaluate a subsurface hanging-wall anomaly shifted `shift_px` updip onto the surface trace.

    If a dipping fault trace at pixel (y, x) dips basinward along (-uy, -ux), its subsurface
    contact at depth h plots down-dip at (y - shift_px * uy, x - shift_px * ux). Sampling the
    subsurface contact at that down-dip coordinate maps the hanging-wall geophysical anomaly
    updip onto the surface fault trace (y, x).
    """
    h, w = field_2d.shape
    yy, xx = np.meshgrid(
        np.arange(h, dtype=np.float32),
        np.arange(w, dtype=np.float32),
        indexing="ij",
    )
    sy = np.clip(yy - np.float32(shift_px) * uy, 0.0, float(h - 1))
    sx = np.clip(xx - np.float32(shift_px) * ux, 0.0, float(w - 1))
    del yy, xx
    return map_coordinates(field_2d.astype(np.float32), [sy, sx], order=1, mode="nearest").astype(
        np.float32
    )


def _advect_upslope_from_plume(
    plume_2d: np.ndarray, uy: np.ndarray, ux: np.ndarray, shift_px: float
) -> np.ndarray:
    """Back-project a downslope outflow spring/probe plume upslope onto its feeder conduit.

    If a feeder fault at (y, x) discharges fluid downslope along (-uy, -ux), the observed
    spring/travertine/2m-probe anomaly sits downslope at (y - shift_px * uy, x - shift_px * ux).
    """
    return _advect_updip(plume_2d, uy, ux, shift_px)


def _build_line_taps(theta_deg: float, half_len: int = WORM_HALF_PX) -> list[tuple[int, int, float]]:
    rad = math.radians(theta_deg)
    dr = -math.cos(rad)
    dc = math.sin(rad)
    weights: dict[tuple[int, int], float] = {}
    for t in range(-half_len, half_len + 1):
        ry = t * dr
        cx = t * dc
        r0 = math.floor(ry)
        c0 = math.floor(cx)
        wy = ry - r0
        wx = cx - c0
        for ir, wr in ((r0, 1.0 - wy), (r0 + 1, wy)):
            for ic, wc in ((c0, 1.0 - wx), (c0 + 1, wx)):
                wt = wr * wc
                if wt > 1e-6:
                    ir_c = max(-half_len, min(half_len, ir))
                    ic_c = max(-half_len, min(half_len, ic))
                    weights[(ir_c, ic_c)] = weights.get((ir_c, ic_c), 0.0) + wt
    tot = sum(weights.values())
    return [(r, c, float(w / tot)) for (r, c), w in sorted(weights.items())]


_LINE_TAPS_8 = tuple(
    _build_line_taps(k * (180.0 / N_AZIMUTHS), WORM_HALF_PX) for k in range(N_AZIMUTHS)
)


def directional_worm_anisotropy(
    field_2d: np.ndarray, ortho_penalty: float = 0.55
) -> tuple[np.ndarray, np.ndarray]:
    """8-azimuth 1.5 km strike-lineament anisotropy & dominant strike azimuth [0, 180)."""
    h, w = field_2d.shape
    pad = WORM_HALF_PX
    padded = np.pad(np.nan_to_num(field_2d, nan=0.0).astype(np.float32), pad, mode="edge")
    resp = np.empty((N_AZIMUTHS, h, w), dtype=np.float32)
    for k, taps in enumerate(_LINE_TAPS_8):
        acc = np.zeros((h, w), dtype=np.float32)
        for dy, dx, wt in taps:
            acc += np.float32(wt) * padded[pad + dy : pad + dy + h, pad + dx : pad + dx + w]
        resp[k] = acc
    del padded

    best = np.full((h, w), -1e30, dtype=np.float32)
    best_k = np.zeros((h, w), dtype=np.int16)
    half = N_AZIMUTHS // 2
    for k in range(N_AZIMUTHS):
        cand = resp[k] - np.float32(ortho_penalty) * resp[(k + half) % N_AZIMUTHS]
        m = cand > best
        best = np.where(m, cand, best)
        best_k = np.where(m, k, best_k)
    del resp
    strike_deg = best_k.astype(np.float32) * np.float32(180.0 / N_AZIMUTHS)
    return np.maximum(best, 0.0).astype(np.float32), strike_deg


def _parse_dbf_records(dbf_bytes: bytes) -> list[dict[str, str]]:
    numrec, lenheader, lenrec = struct.unpack("<4xIHH20x", dbf_bytes[:32])
    fields = []
    pos = 32
    while pos < lenheader - 1 and dbf_bytes[pos] != 0x0D:
        f = dbf_bytes[pos : pos + 32]
        name = f[:11].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        flen = f[16]
        fields.append((name, flen))
        pos += 32
    rows: list[dict[str, str]] = []
    offset = lenheader
    for _ in range(numrec):
        if offset + lenrec > len(dbf_bytes):
            break
        rec = dbf_bytes[offset : offset + lenrec]
        offset += lenrec
        if rec[0:1] == b"*":
            continue
        p = 1
        d: dict[str, str] = {}
        for name, flen in fields:
            if name.lower() not in BANNED_CSV_COLUMNS:
                d[name] = rec[p : p + flen].decode("utf-8", errors="replace").strip()
            p += flen
        rows.append(d)
    return rows


def _splat_points(
    shape: tuple[int, int], rows_cols_weights: list[tuple[int, int, float]]
) -> np.ndarray:
    grid = np.zeros(shape, dtype=np.float32)
    h, w = shape
    for r, c, wt in rows_cols_weights:
        if 0 <= r < h and 0 <= c < w and wt > 0:
            if wt > grid[r, c]:
                grid[r, c] = np.float32(wt)
    return grid


def build_hydrothermal_grids(
    raw_dir: Path,
    fp: np.ndarray,
    transform: rasterio.Affine,
    uy: np.ndarray,
    ux: np.ndarray,
    strike_deg: np.ndarray,
    rad_k_z: np.ndarray,
    ext_thk_z: np.ndarray,
    rtp_filled: np.ndarray,
    updip_subsurf_z: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    """Build 7 label-free OpenEI GDR 1391 INGENIOUS + GeoDAWN hydrothermal channels."""
    h, w = fp.shape
    nad83_to_utm11 = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
    inv_tr = ~transform

    def lonlat_to_rc(lon: float, lat: float) -> tuple[int, int]:
        ex, ny = nad83_to_utm11.transform(lon, lat)
        col_f, row_f = inv_tr * (ex, ny)
        return int(math.floor(row_f)), int(math.floor(col_f))

    # 1. Paleo-geothermal deposits (sinter/breccia throats vs travertine/tufa outflow aprons)
    throat_pts: list[tuple[int, int, float]] = []
    apron_pts: list[tuple[int, int, float]] = []
    with zipfile.ZipFile(raw_dir / "external" / "paleo_geothermal_regional.zip") as zf:
        txt = zf.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(txt))
        for row in reader:
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
                throat_pts.append((r, c, 2.0))
            elif dtype in {"Alteration", "Sulfur", "Calcite-qtz veins", "Silica vein", "Quartzite"}:
                throat_pts.append((r, c, 1.3))
            elif dtype == "Tufa":
                # Deweight pluvial Lake Lahontan shoreline tufa mimic
                wt = 0.25 if "lahontan" in comments else 0.55
                apron_pts.append((r, c, wt))
            else:
                apron_pts.append((r, c, 1.0))

    throat_imp = _splat_points((h, w), throat_pts)
    apron_imp = _splat_points((h, w), apron_pts)
    hyd_sinter_throat = _pos_z(
        0.65 * gaussian_filter(throat_imp, 4.0) + 0.35 * gaussian_filter(throat_imp, 11.0), fp
    )
    apron_smooth = gaussian_filter(apron_imp, 5.0)
    hyd_apron_updip = _pos_z(
        0.5 * apron_smooth + 0.5 * _advect_upslope_from_plume(apron_smooth, uy, ux, 8.0), fp
    )
    del throat_imp, apron_imp, apron_smooth

    # 2. 2-meter shallow temperature probes (F2mDAB degrees above background)
    probe_pts: list[tuple[int, int, float]] = []
    with zipfile.ZipFile(
        raw_dir / "external" / "2m_temperature_probe_INGENIOUS_regional_data.zip"
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
            if not math.isfinite(dab) or dab <= 0.5:
                continue
            r, c = lonlat_to_rc(lon, lat)
            if 0 <= r < h and 0 <= c < w and fp[r, c]:
                probe_pts.append((r, c, min(math.log1p(dab), 3.0)))

    probe_imp = _splat_points((h, w), probe_pts)
    probe_sm = gaussian_filter(probe_imp, 4.5)
    hyd_probe2m_f2mdab = _pos_z(
        0.55 * probe_sm + 0.45 * _advect_upslope_from_plume(probe_sm, uy, ux, 6.0), fp
    )
    del probe_imp, probe_sm

    # 3. Well & spring temperature + quartz/chalcedony/cation geothermometry (label column stripped!)
    ws_pts: list[tuple[int, int, float]] = []
    with (raw_dir / "external" / "gdr_wellspring_in_footprint.csv").open(
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
                    if math.isfinite(tv) and 25.0 < tv < 350.0:
                        temps.append(tv)
                except ValueError:
                    pass
            if not temps:
                continue
            score_t = max(temps)
            if score_t >= 37.0:
                ws_pts.append((r, c, min(math.log1p((score_t - 35.0) / 15.0), 3.0)))

    ws_imp = _splat_points((h, w), ws_pts)
    ws_sm = gaussian_filter(ws_imp, 6.0)
    hyd_geotherm_updip = _pos_z(
        0.45 * ws_sm + 0.55 * _advect_upslope_from_plume(ws_sm, uy, ux, 8.0), fp
    )
    del ws_imp, ws_sm

    # 4. Quaternary volcanic vents projected along local geophysical strike
    vv_pts: list[tuple[int, int, float]] = []
    with (raw_dir / "external" / "gdr_volcanic_vents_in_footprint.csv").open(
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
            if 0 <= r < h and 0 <= c < w and fp[r, c]:
                vv_pts.append((r, c, 1.5))

    vv_imp = gaussian_filter(_splat_points((h, w), vv_pts), 3.0)
    pad = WORM_HALF_PX
    vv_pad = np.pad(vv_imp, pad, mode="constant", constant_values=0.0)
    k_idx = np.rint(strike_deg / (180.0 / N_AZIMUTHS)).astype(np.int16) % N_AZIMUTHS
    vv_proj = np.zeros((h, w), dtype=np.float32)
    for k, taps in enumerate(_LINE_TAPS_8):
        sel = k_idx == k
        if not sel.any():
            continue
        acc = np.zeros((h, w), dtype=np.float32)
        for dy, dx, wt in taps:
            acc += np.float32(wt) * vv_pad[pad + dy : pad + dy + h, pad + dx : pad + dx + w]
        vv_proj = np.where(sel, acc, vv_proj)
    hyd_volc_dike_worm = _pos_z(vv_proj, fp)
    del vv_imp, vv_pad, vv_proj

    # 5. GeoDAWN K/Th adularia alteration + RTP hydrothermal magnetite-destruction trough
    rtp_trough = np.maximum(gaussian_filter(rtp_filled, 6.0) - gaussian_filter(rtp_filled, 1.2), 0.0)
    rtp_trough_z = _pos_z(rtp_trough, fp)
    k_alter = np.maximum(rad_k_z - 0.65 * ext_thk_z, 0.0)
    hyd_rad_k_th_adularia = _pos_z(0.6 * k_alter + 0.4 * k_alter * np.minimum(rtp_trough_z, 3.0), fp)
    del rtp_trough, rtp_trough_z, k_alter

    # 6. Multiplicative concealed hydrothermal conduit x updip-projected basement step
    upflow_sum = (
        0.30 * hyd_sinter_throat
        + 0.20 * hyd_apron_updip
        + 0.25 * hyd_probe2m_f2mdab
        + 0.25 * hyd_geotherm_updip
        + 0.20 * hyd_rad_k_th_adularia
    )
    hyd_conduit_subsurf_x = _pos_z(np.sqrt(np.maximum(upflow_sum * updip_subsurf_z, 0.0)), fp)

    stats = {
        "paleo_throat_points": len(throat_pts),
        "paleo_apron_points": len(apron_pts),
        "probe_2m_hot_points": len(probe_pts),
        "wellspring_thermal_points": len(ws_pts),
        "volcanic_vent_points": len(vv_pts),
    }
    return (
        {
            "hyd_sinter_throat": hyd_sinter_throat,
            "hyd_apron_updip": hyd_apron_updip,
            "hyd_probe2m_f2mdab": hyd_probe2m_f2mdab,
            "hyd_geotherm_updip": hyd_geotherm_updip,
            "hyd_volc_dike_worm": hyd_volc_dike_worm,
            "hyd_rad_k_th_adularia": hyd_rad_k_th_adularia,
            "hyd_conduit_subsurf_x": hyd_conduit_subsurf_x,
        },
        stats,
    )


def prepare_feature_memmap(*, force: bool = False) -> dict[str, Any]:
    """Build or verify the 66-channel memory-mapped float32 feature stack on work_dir()."""
    rdir = raw_data_dir()
    wdir = work_dir()
    wdir.mkdir(parents=True, exist_ok=True)
    feat_mmap_path = wdir / "dpgf_features.npy"
    lidar_mask_path = wdir / "has_lidar_fp.npy"
    meta_path = repo_root() / "evidence" / "prepared_features_manifest.json"

    tmpl_path = rdir / "sample_submission.tif"
    src_path = rdir / "training_features.tif"
    lid_path = rdir / "external" / "lidar_scarp_features_u8.tif"
    rad_path = rdir / "external" / "geodawn_rad_u8.tif"
    ext_path = rdir / "external" / "geodawn_extensions_u8.tif"

    with rasterio.open(tmpl_path) as tmpl:
        assert tmpl.crs.to_epsg() == 32611
        assert (tmpl.height, tmpl.width) == (3730, 3292)
        tr = tmpl.transform
        fp = np.isfinite(tmpl.read(1))

    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = int(len(fp_ids))
    n_cols = len(FEATURE_NAMES)

    if feat_mmap_path.exists() and lidar_mask_path.exists() and meta_path.exists() and not force:
        meta = json.loads(meta_path.read_text())
        mm = np.load(feat_mmap_path, mmap_mode="r")
        if mm.shape == (n_fp, n_cols) and meta.get("feature_names") == list(FEATURE_NAMES):
            return meta

    tmp_mmap_path = wdir / "dpgf_features.partial.npy"
    mm = np.lib.format.open_memmap(
        tmp_mmap_path, mode="w+", dtype=np.float32, shape=(n_fp, n_cols)
    )

    kept: dict[str, np.ndarray] = {}
    sentinel_counts: dict[str, int] = {}

    # --- Block A: 19 official training_features.tif bands (cols 0..18) ---
    with rasterio.open(src_path) as ds:
        assert (ds.height, ds.width) == fp.shape and ds.count == 19
        for i, bname in enumerate(BAND_ORDER):
            raw = ds.read(i + 1).astype(np.float32)
            valid = fp & np.isfinite(raw) & (raw > SENTINEL_CUT)
            sentinel_counts[bname] = int((fp & ~valid).sum())
            clean = np.where(valid, raw, np.nan).astype(np.float32)
            mm[:, i] = clean.ravel()[fp_ids]
            if bname in {
                "det_elev",
                "det_elev_slope",
                "rtp",
                "tmi",
                "tmi_hg",
                "tmi_vg",
                "iso_grav_anom",
                "iso_grav_anom_hg",
                "iso_grav_anom_vg",
                "depth_to_base_surf",
                "cond_surf",
                "geod_dilaterate",
                "geod_shearrate",
                "geod_2ndinv",
                "ieq_n100a15",
            }:
                kept[bname] = _nearest_fill(clean, valid)
            del raw, clean

    # --- Block B: 12 USGS 3DEP 1 m LiDAR scarp features (cols 19..30, NaN outside coverage) ---
    col = 19
    lid_deq: dict[str, np.ndarray] = {}
    with rasterio.open(lid_path) as ds:
        assert (ds.height, ds.width) == fp.shape and ds.count == 12
        lid_valid = fp & (ds.read(12) > 0)
        np.save(lidar_mask_path, lid_valid.ravel()[fp_ids])
        for b_idx, (lname, xmax, mode) in enumerate(LIDAR_SPECS, start=1):
            q = ds.read(b_idx).astype(np.float32)
            u = np.clip((q - 1.0) / 254.0, 0.0, 1.0)
            phys = (u * u * xmax) if mode == "sqrt" else (u * xmax)
            arr = np.where(lid_valid, phys, np.nan).astype(np.float32)
            mm[:, col] = arr.ravel()[fp_ids]
            col += 1
            if lname in {
                "upface_max",
                "downface_max",
                "cross_max",
                "lapneg_max",
                "lappos_max",
                "coh100",
                "step_max",
            }:
                lid_deq[lname] = arr
            del q, u, phys
        q_strike = ds.read(11).astype(np.float32)
        theta = np.clip((q_strike - 1.0) / 254.0, 0.0, 1.0) * np.float32(math.pi)
        for trig in (np.cos(2.0 * theta), np.sin(2.0 * theta)):
            arr = np.where(lid_valid, trig, np.nan).astype(np.float32)
            mm[:, col] = arr.ravel()[fp_ids]
            col += 1
        del q_strike, theta

    # --- Block C: 8 GeoDAWN radiometric & upward-continued magnetic channels (cols 31..38) ---
    with rasterio.open(rad_path) as ds:
        for b_idx in range(1, 5):
            q = ds.read(b_idx)
            v = fp & (q > 0)
            arr = np.where(v, (q.astype(np.float32) - 1.0) / 254.0, np.nan).astype(np.float32)
            mm[:, col] = arr.ravel()[fp_ids]
            if b_idx == 1:
                rad_k_z = _robust_z(_nearest_fill(arr, v), fp)
            col += 1
            del q, arr

    with rasterio.open(ext_path) as ds:
        for b_idx in range(1, 5):
            q = ds.read(b_idx)
            v = fp & (q > 0)
            arr = np.where(v, (q.astype(np.float32) - 1.0) / 254.0, np.nan).astype(np.float32)
            mm[:, col] = arr.ravel()[fp_ids]
            if b_idx == 1:
                ext_thk_z = _robust_z(_nearest_fill(arr, v), fp)
            elif b_idx == 4:
                tmi_up150_filled = _nearest_fill(arr, v)
            col += 1
            del q, arr

    assert col == 39

    # --- Regional topographic unit updip vector u = grad(G_15(det_elev)) / ||grad|| ---
    det = kept["det_elev"]
    det_reg15 = gaussian_filter(det, 15.0)
    gy_reg, gx_reg = np.gradient(det_reg15)
    gnorm = np.hypot(gy_reg, gx_reg) + np.float32(1e-5)
    uy = (gy_reg / gnorm).astype(np.float32)
    ux = (gx_reg / gnorm).astype(np.float32)
    del gy_reg, gx_reg, gnorm

    # --- Block D: 10 Multi-Scale Geomorphic & Potential-Field Physics channels (cols 39..48) ---
    det_loc5 = (det - gaussian_filter(det, 5.0)).astype(np.float32)
    det_loc15 = (det - det_reg15).astype(np.float32)
    del det_reg15

    det_sm3 = gaussian_filter(det, 3.0)
    d2y = np.gradient(np.gradient(det_sm3, axis=0), axis=0)
    d2x = np.gradient(np.gradient(det_sm3, axis=1), axis=1)
    lap_pos = np.maximum(d2y + d2x, 0.0)
    slp = kept["det_elev_slope"]
    slp_p55 = float(np.percentile(slp[fp], 55.0))
    slp_iqr = max(float(np.percentile(slp[fp], 80.0) - np.percentile(slp[fp], 25.0)), 1e-4)
    pied_gate = np.exp(-0.5 * ((slp - slp_p55) / slp_iqr) ** 2).astype(np.float32)
    ms_piedmont_inflection = _pos_z(lap_pos * pied_gate, fp)
    del det_sm3, d2y, d2x, lap_pos

    mag_tilt = np.arctan2(
        kept["tmi_vg"], np.sqrt(kept["tmi_hg"] ** 2 + np.float32(1e-6))
    ).astype(np.float32)
    mag_tilt_grad = _grad_mag(mag_tilt, sigma=1.2)

    grav_tilt = np.arctan2(
        kept["iso_grav_anom_vg"], np.sqrt(kept["iso_grav_anom_hg"] ** 2 + np.float32(1e-6))
    ).astype(np.float32)
    grav_tilt_grad = _grad_mag(grav_tilt, sigma=1.5)

    # E-W (azimuth 90) flight-line notch via anisotropic vertical smoothing (sigma_y=2.2, sigma_x=0.8)
    tmi0_notch = gaussian_filter(kept["tmi"], sigma=(2.2, 0.8))
    tmi150_notch = gaussian_filter(tmi_up150_filled, sigma=(2.2, 0.8))
    g0 = _pos_z(_grad_mag(tmi0_notch, sigma=0.8), fp) + np.float32(0.15)
    g150 = _pos_z(_grad_mag(tmi150_notch, sigma=0.8), fp) + np.float32(0.15)
    ms_mag_persist_150m = np.log(g150 / g0).astype(np.float32)
    del tmi0_notch, tmi150_notch, g0, g150, tmi_up150_filled

    base_pos = np.log1p(np.maximum(kept["depth_to_base_surf"], 0.0))
    ms_basement_step_grad = _pos_z(_grad_mag(base_pos, sigma=1.5), fp)
    del base_pos

    cond_pos = np.log1p(np.maximum(kept["cond_surf"], 0.0))
    ms_mt_claycap_perim = _pos_z(_grad_mag(cond_pos, sigma=1.5), fp)
    del cond_pos

    block_d = [
        det_loc5,
        det_loc15,
        ms_piedmont_inflection,
        mag_tilt,
        mag_tilt_grad,
        grav_tilt,
        grav_tilt_grad,
        ms_mag_persist_150m,
        ms_basement_step_grad,
        ms_mt_claycap_perim,
    ]
    for arr in block_d:
        mm[:, col] = arr.ravel()[fp_ids]
        col += 1
    assert col == 49
    del det_loc5, det_loc15, mag_tilt, grav_tilt
    gc.collect()

    # --- Block E: 10 WBG-H1 Core Novel Operators (cols 49..58) ---
    grav_edge_comp = 0.55 * _pos_z(kept["iso_grav_anom_hg"], fp) + 0.45 * _pos_z(grav_tilt_grad, fp)
    dpgf_grav_updip_500m = _advect_updip(grav_edge_comp, uy, ux, 5.0)
    dpgf_grav_updip_1000m = _advect_updip(grav_edge_comp, uy, ux, 10.0)

    mag_edge_comp = (
        0.45 * _pos_z(mag_tilt_grad, fp)
        + 0.30 * _pos_z(kept["tmi_hg"], fp)
        + 0.25 * ms_basement_step_grad
    )
    dpgf_mag_updip_600m = _advect_updip(mag_edge_comp, uy, ux, 6.0)

    mt_edge_comp = 0.60 * ms_mt_claycap_perim + 0.40 * ms_basement_step_grad
    dpgf_mt_updip_600m = _advect_updip(mt_edge_comp, uy, ux, 6.0)

    updip_subsurf_z = (
        0.40 * dpgf_grav_updip_500m
        + 0.25 * dpgf_grav_updip_1000m
        + 0.20 * dpgf_mag_updip_600m
        + 0.15 * dpgf_mt_updip_600m
    ).astype(np.float32)

    lid_step_filled = np.where(lid_valid, _pos_z(np.nan_to_num(lid_deq["step_max"]), lid_valid), 0.0)
    surf_break = np.maximum(
        0.55 * ms_piedmont_inflection + 0.45 * _pos_z(slp, fp),
        0.70 * lid_step_filled + 0.30 * ms_piedmont_inflection,
    )
    dpgf_dip_surface_coupling = _pos_z(np.sqrt(np.maximum(updip_subsurf_z * surf_break, 0.0)), fp)
    del grav_edge_comp, mag_edge_comp, mt_edge_comp, lid_step_filled, surf_break

    # Tectonic-to-Fluvial Scarp Discrimination Index (strictly NaN outside 3DEP LiDAR!)
    upf = lid_deq["upface_max"]
    dnf = lid_deq["downface_max"]
    crf = lid_deq["cross_max"]
    coh = lid_deq["coh100"]
    tfsdi_raw = np.log((1.0 + 1.5 * upf + 1.0 * dnf) / (1.0 + 1.2 * crf)) * coh
    dpgf_tfsdi_scarp = np.where(lid_valid, tfsdi_raw, np.nan).astype(np.float32)

    graben_raw = np.sqrt(np.maximum(lid_deq["lapneg_max"] * lid_deq["lappos_max"], 0.0)) * coh
    dpgf_graben_crest_base = np.where(lid_valid, graben_raw, np.nan).astype(np.float32)
    del upf, dnf, crf, coh, tfsdi_raw, graben_raw, lid_deq

    shear_abs = np.abs(kept["geod_shearrate"])
    dil_abs = np.abs(kept["geod_dilaterate"])
    obliq_ratio = shear_abs / (shear_abs + dil_abs + np.float32(1e-6))
    strain_z = _pos_z(kept["geod_2ndinv"], fp)
    seis_z = _pos_z(kept["ieq_n100a15"], fp)
    aseis_def = np.maximum(np.log1p(strain_z) - 0.7 * np.log1p(seis_z), 0.0)
    dpgf_transtens_obliq = _pos_z(obliq_ratio * (0.5 + aseis_def), fp)
    del shear_abs, dil_abs, obliq_ratio, strain_z, seis_z, aseis_def

    dpgf_worm_subsurf_1p5km, strike_subsurf = directional_worm_anisotropy(updip_subsurf_z)
    pied_comp = 0.55 * ms_piedmont_inflection + 0.45 * _pos_z(slp, fp) * pied_gate
    dpgf_worm_piedmont_1p5km, _ = directional_worm_anisotropy(pied_comp)
    del pied_comp, pied_gate

    block_e = [
        dpgf_grav_updip_500m,
        dpgf_grav_updip_1000m,
        dpgf_mag_updip_600m,
        dpgf_mt_updip_600m,
        dpgf_dip_surface_coupling,
        dpgf_tfsdi_scarp,
        dpgf_graben_crest_base,
        dpgf_transtens_obliq,
        dpgf_worm_subsurf_1p5km,
        dpgf_worm_piedmont_1p5km,
    ]
    for arr in block_e:
        mm[:, col] = arr.ravel()[fp_ids]
        col += 1
    assert col == 59
    del block_e
    gc.collect()

    # --- Block F: 7 INGENIOUS Hydrothermal Upflow & GeoDAWN Alteration channels (cols 59..65) ---
    hyd_dict, hyd_stats = build_hydrothermal_grids(
        rdir,
        fp,
        tr,
        uy,
        ux,
        strike_subsurf,
        rad_k_z,
        ext_thk_z,
        kept["rtp"],
        updip_subsurf_z,
    )
    for hname in HYD_NAMES:
        mm[:, col] = hyd_dict[hname].ravel()[fp_ids]
        col += 1
    assert col == n_cols
    mm.flush()
    del mm, hyd_dict, kept, uy, ux, strike_subsurf, updip_subsurf_z
    gc.collect()

    tmp_mmap_path.replace(feat_mmap_path)

    meta = {
        "schema_version": 1,
        "shape": [n_fp, n_cols],
        "dtype": "float32",
        "grid_shape": [3730, 3292],
        "crs": "EPSG:32611",
        "transform": [float(v) for v in tuple(tr)[:6]],
        "footprint_pixels": n_fp,
        "lidar_covered_pixels": int(lid_valid.sum()),
        "lidar_gap_pixels": int(n_fp - int(lid_valid.sum())),
        "lidar_gap_fraction": round(float(1.0 - lid_valid.sum() / n_fp), 6),
        "feature_names": list(FEATURE_NAMES),
        "catalogue_features": [],
        "banned_columns_stripped": sorted(BANNED_CSV_COLUMNS),
        "sentinel_in_footprint_counts": sentinel_counts,
        "hydrothermal_inventory_in_footprint": hyd_stats,
    }
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta
