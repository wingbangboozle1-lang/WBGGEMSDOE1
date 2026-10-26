"""Label-free feature transforms + geothermal anchors + H1 surface.

All surfaces are rank-normalized within the footprint (decode-invariant,
robust to outliers). Catalogue labels are NEVER used here except for the
documented B-flank emission exclusion (handled in emission/holdout with
visible-only faults per fold).

Band index (1-based) in training_features.tif:
 1 mag_anom  2 rtp  3 tmi_hg  4 geod_2ndinv  5 iso_grav_anom_slope  6 tc
 7 geod_shearrate  8 geod_dilaterate  9 tmi_vg  10 deq_n100a15
 11 iso_grav_anom_vg  12 det_elev  13 iso_grav_anom  14 tmi
 15 depth_to_base_surf  16 ieq_n100a15  17 cond_surf  18 iso_grav_anom_hg
 19 det_elev_slope
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.ndimage import distance_transform_edt

BANDS = [
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15",
    "iso_grav_anom_vg", "det_elev", "iso_grav_anom", "tmi",
    "depth_to_base_surf", "ieq_n100a15", "cond_surf", "iso_grav_anom_hg",
    "det_elev_slope",
]
BAND_IDX = {n: i + 1 for i, n in enumerate(BANDS)}
NODATA_TOL = 1e30

LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
               "downface_max", "upface_max", "cross_max", "relief", "coh100",
               "strike", "valid"]
LIDAR_SQRT = {"ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
              "downface_max", "upface_max", "cross_max", "relief"}


def read_band(path: Path, idx: int) -> np.ndarray:
    with rasterio.open(path) as s:
        return s.read(idx).astype(np.float32)


def clean_band(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """NaN/out-of-range -> footprint median (for linear filtering)."""
    a = a.astype(np.float64)
    bad = ~np.isfinite(a) | (np.abs(a) > NODATA_TOL)
    med = float(np.median(a[foot & ~bad])) if (foot & ~bad).any() else 0.0
    a[bad] = med
    return a


def rank_norm(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] within footprint; 0 outside. float32."""
    out = np.zeros(a.shape, dtype=np.float32)
    v = np.asarray(a, dtype=np.float64)[foot]
    ok = np.isfinite(v)
    r = np.zeros_like(v, dtype=np.float64)
    if ok.sum() > 1:
        order = np.argsort(v[ok], kind="mergesort")
        ranks = np.empty(ok.sum(), dtype=np.float64)
        ranks[order] = (np.arange(ok.sum()) + 0.5) / ok.sum()
        r[ok] = ranks
    out[foot] = r.astype(np.float32)
    return out


def gmag(a: np.ndarray, sigma: float) -> np.ndarray:
    gy = ndi.gaussian_filter(a, sigma, order=(1, 0))
    gx = ndi.gaussian_filter(a, sigma, order=(0, 1))
    return np.hypot(gy, gx)


def lap_abs(a: np.ndarray, sigma: float) -> np.ndarray:
    return np.abs(ndi.gaussian_laplace(a, sigma))


def structure_strike(edge: np.ndarray, smooth: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    """Structure-tensor coherence + strike (deg, 0-180) of an edge field."""
    e = ndi.gaussian_filter(edge.astype(np.float64), 1.5)
    gy, gx = np.gradient(e)
    jxx = ndi.gaussian_filter(gx * gx, smooth)
    jyy = ndi.gaussian_filter(gy * gy, smooth)
    jxy = ndi.gaussian_filter(gx * gy, smooth)
    tr = jxx + jyy
    diff = np.sqrt(np.maximum((jxx - jyy) ** 2 / 4 + jxy ** 2, 0))
    l1 = tr / 2 + diff
    l2 = np.maximum(tr / 2 - diff, 0)
    coh = ((l1 - l2) / (l1 + l2 + 1e-12)).astype(np.float32)
    # gradient orientation -> strike (perpendicular), folded to [0,180)
    theta = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy))
    strike = ((theta + 180.0) % 180.0 + 90.0) % 180.0
    return coh.astype(np.float32), strike.astype(np.float32)


def anderson_gate(strike: np.ndarray, targets=(15.0, 140.0), tol: float = 45.0,
                  floor: float = 0.15) -> np.ndarray:
    """Soft gate favouring Andersonian normal-fault strikes for the Walker Lane
    / Basin-and-Range extensional regime (NNE ~15 deg and conjugate ~140 deg).

    Returns multiplicative gate in [floor, 1].
    """
    dev = None
    for t in targets:
        d = np.abs((strike - t + 90.0) % 180.0 - 90.0)
        dev = d if dev is None else np.minimum(dev, d)
    g = 1.0 - np.clip(dev / tol, 0.0, 1.0)
    return (floor + (1.0 - floor) * g).astype(np.float32)


def decode_lidar_u8(q: np.ndarray, name: str) -> np.ndarray:
    """Monotonic decode of lidar uint8 channels; 0 -> NaN (no lidar).

    q = 1 + round(254 * t(x/xmax)); inverse is monotonic in q, so for rank
    purposes any monotonic map works. We use t^-1 for principled units.
    """
    q = np.asarray(q, dtype=np.float64)
    out = np.full(q.shape, np.nan)
    m = q > 0
    v = (q[m] - 1.0) / 254.0
    out[m] = v ** 2 if name in LIDAR_SQRT else v
    return out


def load_lidar(ddir: Path, foot: np.ndarray) -> dict[str, np.ndarray]:
    p = ddir / "external" / "lidar_scarp_features_u8.tif"
    out: dict[str, np.ndarray] = {}
    with rasterio.open(p) as s:
        assert tuple(s.shape) == tuple(foot.shape), (s.shape, foot.shape)
        for i, name in enumerate(LIDAR_BANDS, start=1):
            out[name] = decode_lidar_u8(s.read(i), name)
    return out


def load_rad_ext(ddir: Path, foot: np.ndarray) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    with rasterio.open(ddir / "external" / "geodawn_rad_u8.tif") as s:
        assert tuple(s.shape) == tuple(foot.shape)
        for i, name in enumerate(["K", "Th", "U", "TC"], start=1):
            q = s.read(i).astype(np.float64)
            q[q == 0] = np.nan  # nodata=0
            out[f"rad_{name}"] = q / 255.0
    with rasterio.open(ddir / "external" / "geodawn_extensions_u8.tif") as s:
        assert tuple(s.shape) == tuple(foot.shape)
        for i, name in enumerate(["ThK", "UK", "UTh", "TMI_up150"], start=1):
            q = s.read(i).astype(np.float64)
            q[q == 0] = np.nan
            out[f"ext_{name}"] = q / 255.0
    return out


def rasterize_points(shape, rows, cols, weights) -> np.ndarray:
    img = np.zeros(shape, dtype=np.float64)
    h, w = shape
    for r, c, wt in zip(rows, cols, weights):
        r, c = int(r), int(c)
        if 0 <= r < h and 0 <= c < w and np.isfinite(wt):
            if wt > img[r, c]:
                img[r, c] = wt
    return img


def proximity_halo(pts: np.ndarray, radius_px: float = 10.0) -> np.ndarray:
    """Max-weight halo: (1 - d/radius)+ times nearest-point weight."""
    m = pts > 0
    if not m.any():
        return np.zeros_like(pts)
    dist, idx = distance_transform_edt(~m, return_indices=True)
    w_nearest = pts[tuple(idx)]
    halo = np.maximum(1.0 - dist / radius_px, 0.0) * w_nearest
    return halo


def load_wellspring(ddir: Path, shape) -> dict:
    """Parse INGENIOUS wellspring CSV; dedupe by cell keeping max temp."""
    p = ddir / "external" / "gdr_wellspring_in_footprint.csv"
    best: dict[tuple[int, int], float] = {}
    n_rows = 0
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            n_rows += 1
            try:
                r, c = int(float(row["row"])), int(float(row["col"]))
            except (ValueError, TypeError, KeyError):
                continue
            try:
                temp = float(row.get("temp_c") or "nan")
            except ValueError:
                temp = float("nan")
            tc = (row.get("thermalclass") or "").strip().lower()
            base = 1.0 if tc == "hot" else (0.7 if (np.isfinite(temp) and temp >= 40) else 0.4)
            boost = 0.5 + 0.5 * np.clip(((temp - 25.0) / 75.0) if np.isfinite(temp) else 0.0, 0, 1)
            w = base * boost
            key = (r, c)
            if w > best.get(key, -1):
                best[key] = w
    rows = [k[0] for k in best]
    cols = [k[1] for k in best]
    wts = [best[k] for k in best]
    pts = rasterize_points(shape, rows, cols, wts)
    return {"points": pts, "n_csv_rows": n_rows, "n_cells": len(best)}


def load_vents(ddir: Path, shape) -> dict:
    p = ddir / "external" / "gdr_volcanic_vents_in_footprint.csv"
    rows, cols = [], []
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            try:
                rows.append(int(float(row["row"])))
                cols.append(int(float(row["col"])))
            except (ValueError, TypeError, KeyError):
                continue
    wts = [1.0] * len(rows)
    return {"points": rasterize_points(shape, rows, cols, wts), "n": len(rows)}


def load_paleo(ddir: Path, shape) -> dict:
    """Paleo-geothermal CSV inside zip (already extracted? else read zip)."""
    import zipfile

    zp = ddir / "external" / "paleo_geothermal_regional.zip"
    cols_found: list[str] = []
    pts = np.zeros(shape, dtype=np.float64)
    n = 0
    try:
        with zipfile.ZipFile(zp) as z:
            name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
            with z.open(name) as f:
                import io

                text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
                rdr = csv.DictReader(text)
                cols_found = list(rdr.fieldnames or [])
                _lonlat_T = None
                if ("Long_deg_NAD83" in cols_found
                        and "Lat_deg_NAD83" in cols_found):
                    from pyproj import Transformer
                    _lonlat_T = Transformer.from_crs("EPSG:4269", "EPSG:32611",
                                                     always_xy=True)
                # accept row/col if present, else UTM x/y, else lon/lat
                for row in rdr:
                    r = c = None
                    if "row" in row and "col" in row:
                        try:
                            r, c = int(float(row["row"])), int(float(row["col"]))
                        except (ValueError, TypeError):
                            continue
                    elif "utm_x" in row and "utm_y" in row:
                        try:
                            x, y = float(row["utm_x"]), float(row["utm_y"])
                        except (ValueError, TypeError):
                            continue
                        c, r = int((x - 243350.0) // 100), int((4508550.0 - y) // 100)
                    elif "POINT_X" in row and "POINT_Y" in row:
                        try:
                            x, y = float(row["POINT_X"]), float(row["POINT_Y"])
                        except (ValueError, TypeError):
                            continue
                        c, r = int((x - 243350.0) // 100), int((4508550.0 - y) // 100)
                    elif _lonlat_T is not None:
                        try:
                            lon = float(row["Long_deg_NAD83"])
                            lat = float(row["Lat_deg_NAD83"])
                            x, y = _lonlat_T.transform(lon, lat)
                        except (ValueError, TypeError):
                            continue
                        # NAD83 vs WGS84 differ ~1-2 m, negligible at 100 m cells
                        c, r = int((x - 243350.0) // 100), int((4508550.0 - y) // 100)
                    else:
                        break
                    h, w = shape
                    if 0 <= r < h and 0 <= c < w:
                        pts[r, c] = 1.0
                        n += 1
    except Exception as e:  # documented as unused if unparseable
        return {"points": pts, "n": 0, "columns": cols_found, "error": repr(e)}
    return {"points": pts, "n": n, "columns": cols_found, "error": None}


def build_h1_components(ddir: Path, foot: np.ndarray, work_path: Path) -> dict:
    """Build H1 component rank surfaces; cache as float32 memmap.

    Returns {name: memmap-slice}. Components:
      s_geo  geothermal discharge proximity (wellspring temp-weighted + vents + paleo)
      s_cond MT clay-cap breach edges (cond_surf gmag1 + lap2)
      s_mag  basement magnetic steps (tmi_hg + gmag1(rtp) + gmag1(tmi))
      s_topo lidar scarp composite, det_elev curvature fallback
      s_grav gravity steps (iso_grav_anom_hg + gmag1(iso_grav_anom))
      gate_and Andersonian strike gate (multiplicative, [0.15,1])
      h1     gate * mean(s_geo..s_grav)
      s_h5   strain x seismic conjunction (cheap control lane H5)
    """
    feat_path = ddir / "training_features.tif"
    names = ["s_geo", "s_cond", "s_mag", "s_topo", "s_grav", "gate_and", "h1", "s_h5"]
    h, w = foot.shape
    stack = np.lib.format.open_memmap(
        work_path, mode="w+", dtype=np.float32, shape=(len(names), h, w)
    )

    def need(band_name: str) -> np.ndarray:
        return clean_band(read_band(feat_path, BAND_IDX[band_name]), foot)

    # --- geothermal anchors (no labels involved) ---
    ws = load_wellspring(ddir, foot.shape)
    vn = load_vents(ddir, foot.shape)
    pa = load_paleo(ddir, foot.shape)
    halo = (
        proximity_halo(ws["points"], 10.0)
        + 0.8 * proximity_halo(vn["points"], 10.0)
        + 0.6 * proximity_halo(pa["points"], 10.0)
    )
    stack[0] = rank_norm(halo, foot)
    del halo
    meta_geo = {"wellspring_cells": ws["n_cells"], "vents": vn["n"],
                "paleo_points": pa["n"], "paleo_columns": pa["columns"]}

    # --- cond / mag / grav / topo from the 19-band stack, band-at-a-time ---
    cond = need("cond_surf")
    s_cond = (rank_norm(gmag(cond, 1.0), foot) + rank_norm(lap_abs(cond, 2.0), foot)) / 2
    stack[1] = rank_norm(s_cond, foot)
    del cond, s_cond

    tmi_hg = need("tmi_hg")
    rtp = need("rtp")
    tmi = need("tmi")
    s_mag = (rank_norm(tmi_hg, foot) + rank_norm(gmag(rtp, 1.0), foot)
             + rank_norm(gmag(tmi, 1.0), foot)) / 3
    stack[2] = rank_norm(s_mag, foot)
    g_rtp1 = gmag(rtp, 1.0)
    del tmi_hg, rtp, tmi, s_mag

    grav_hg = need("iso_grav_anom_hg")
    grav = need("iso_grav_anom")
    s_grav = (rank_norm(grav_hg, foot) + rank_norm(gmag(grav, 1.0), foot)) / 2
    stack[4] = rank_norm(s_grav, foot)
    del grav_hg, grav, s_grav

    det = need("det_elev")
    g_det1 = gmag(det, 1.0)
    det_fallback = (rank_norm(lap_abs(det, 2.0), foot) + rank_norm(g_det1, foot)) / 2
    lidar = load_lidar(ddir, foot)
    with np.errstate(invalid="ignore"):
        lcomp = (np.nan_to_num(lidar["ex_max"], nan=0.0)
                 + np.nan_to_num(lidar["step_max"], nan=0.0)
                 + np.nan_to_num(lidar["lapneg_max"], nan=0.0)
                 + np.nan_to_num(lidar["lappos_max"], nan=0.0)) / 4.0
    has_lidar = np.isfinite(lidar["ex_max"]) & foot
    topo = np.where(has_lidar, rank_norm(np.where(has_lidar, lcomp, np.nan), foot),
                    det_fallback)
    stack[3] = rank_norm(topo, foot).astype(np.float32)
    lidar_cov = float(has_lidar.sum() / max(1, foot.sum()))
    del det, det_fallback, lidar, lcomp, topo

    # --- Andersonian gate from combined edge field ---
    edge = (g_rtp1 + g_det1) / 2.0
    del g_rtp1, g_det1
    _coh, strike = structure_strike(edge)
    del edge
    stack[5] = anderson_gate(strike)
    del strike

    # --- H1 consensus + H5 control ---
    parts = stack[0:5].astype(np.float64)  # memmap slice -> RAM (~245 MB)
    h1 = np.mean(parts, axis=0) * stack[5].astype(np.float64)
    stack[6] = rank_norm(h1, foot)
    del parts, h1

    s2 = need("geod_2ndinv")
    dd = need("geod_dilaterate")
    ieq = need("ieq_n100a15")
    deq = need("deq_n100a15")
    h5 = (rank_norm(s2, foot) + rank_norm(np.abs(dd), foot)
          + rank_norm(ieq, foot) + rank_norm(-deq, foot)) / 4
    stack[7] = rank_norm(h5, foot)
    del s2, dd, ieq, deq, h5

    stack.flush()
    return {
        "names": names,
        "path": str(work_path),
        "shape": (len(names), h, w),
        "geo": meta_geo,
        "lidar_coverage": lidar_cov,
    }
