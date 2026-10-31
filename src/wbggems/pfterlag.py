"""PFTL-1: preregistered cross-scale potential-field / terrain edge-lag screen.

This research-only feature uses cached, label-independent raster bands. It does
not read the fault catalogue, registry rasters, holdout labels, site scores, or
submission artifacts while constructing the surface. Shared GEMS57 holdout,
uniqueness, writer, and validator modules remain the only evaluation/output
instruments.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

SIGMAS_PX = (3.0, 8.0)
OFFSETS_YX = np.asarray(
    [(-3, 0), (-2, -2), (0, -3), (2, -2), (3, 0), (2, 2), (0, 3), (-2, 2)],
    dtype=np.int8,
)
EPS = 1e-6


def robust_z(values: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Footprint-only median/MAD scaling; invalid and exterior cells become zero."""
    a = np.asarray(values)
    fp = np.asarray(footprint, dtype=bool)
    if a.ndim != 2 or a.shape != fp.shape:
        raise ValueError("input and footprint must be same-size 2-D arrays")
    valid = fp & np.isfinite(a) & (np.abs(a) < 1e18)
    if not valid.any():
        raise ValueError("no finite in-footprint feature values")
    sample = np.asarray(a[valid], dtype=np.float64)
    median = float(np.median(sample))
    mad = float(np.median(np.abs(sample - median)) * 1.4826)
    if not np.isfinite(mad) or mad <= EPS:
        mad = float(np.std(sample))
    if not np.isfinite(mad) or mad <= EPS:
        raise ValueError("feature has no usable robust scale")
    out = np.zeros(a.shape, dtype=np.float32)
    z = (np.asarray(a[fp], dtype=np.float64) - median) / mad
    z[~np.isfinite(z) | (np.abs(z) >= 1e18)] = 0.0
    out[fp] = np.clip(z, -10.0, 10.0).astype(np.float32)
    return out


def _gradients(z: np.ndarray, sigma: float) -> tuple[np.ndarray, ...]:
    """Scale-normalized Gaussian gradient, magnitude and unit-vector fields."""
    gx = ndi.gaussian_filter(z, sigma=sigma, order=(0, 1), mode="nearest") * sigma
    gy = ndi.gaussian_filter(z, sigma=sigma, order=(1, 0), mode="nearest") * sigma
    mag = np.hypot(gx, gy).astype(np.float32, copy=False)
    ux = np.divide(gx, mag + EPS, dtype=np.float32)
    uy = np.divide(gy, mag + EPS, dtype=np.float32)
    return gx.astype(np.float32, copy=False), gy.astype(np.float32, copy=False), mag, ux, uy


def _lag_gain(
    terrain_unit: tuple[np.ndarray, np.ndarray],
    potential_unit: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Best non-zero shifted absolute cosine gain over co-located alignment.

    The potential-field gradient is sampled at one of the frozen 3-pixel offsets
    while the terrain gradient is held at the target pixel. Offset selection is
    feature-only and independent of labels/registry.
    """
    ty, tx = terrain_unit
    py, px = potential_unit
    h, w = ty.shape
    zero = np.abs(ty * py + tx * px)
    best = np.zeros(ty.shape, dtype=np.float32)
    direction = np.full(ty.shape, -1, dtype=np.int8)
    for index, (dy_raw, dx_raw) in enumerate(OFFSETS_YX):
        dy, dx = int(dy_raw), int(dx_raw)
        dest_y = slice(max(0, -dy), min(h, h - dy))
        dest_x = slice(max(0, -dx), min(w, w - dx))
        src_y = slice(max(0, dy), min(h, h + dy))
        src_x = slice(max(0, dx), min(w, w + dx))
        cosine = np.abs(ty[dest_y, dest_x] * py[src_y, src_x]
                        + tx[dest_y, dest_x] * px[src_y, src_x])
        view = best[dest_y, dest_x]
        update = cosine > view
        view[update] = cosine[update]
        dview = direction[dest_y, dest_x]
        dview[update] = index
    gain = np.maximum(best - zero, 0.0, dtype=np.float32)
    return gain, direction


def _direction_cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Nonnegative cosine between two selected frozen shift directions."""
    ia = np.asarray(a, dtype=np.int16)
    ib = np.asarray(b, dtype=np.int16)
    valid = (ia >= 0) & (ib >= 0)
    out = np.zeros(ia.shape, dtype=np.float32)
    if valid.any():
        va = OFFSETS_YX[ia[valid]].astype(np.float32)
        vb = OFFSETS_YX[ib[valid]].astype(np.float32)
        dot = (va * vb).sum(axis=1)
        denom = np.linalg.norm(va, axis=1) * np.linalg.norm(vb, axis=1)
        out[valid] = np.maximum(dot / np.maximum(denom, EPS), 0.0)
    return out


def _edge_strength(magnitudes: tuple[np.ndarray, ...], footprint: np.ndarray) -> np.ndarray:
    """Geometric-mean local edge strength; each field is q99-clipped."""
    peaks = []
    for mag in magnitudes:
        q99 = float(np.quantile(mag[footprint], 0.99))
        if not np.isfinite(q99) or q99 <= EPS:
            peaks.append(np.zeros(mag.shape, dtype=np.float32))
            continue
        local_peak = ndi.maximum_filter(mag, size=7, mode="nearest")
        peaks.append(np.clip(local_peak / q99, 0.0, 1.0).astype(np.float32))
    product = peaks[0] * peaks[1] * peaks[2]
    return np.cbrt(product, dtype=np.float32)


def build_pfterlag_surface(
    det_elev: np.ndarray,
    iso_grav_anom: np.ndarray,
    tmi: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    """Build the frozen PFTL-1 [0,1] surface and diagnostic feature planes.

    Returns ``(surface, canary_features, normalization_receipt)``. The final
    surface is normalized by its footprint-only 99th percentile. No labels or
    catalogue-derived fields enter this function.
    """
    fp = np.asarray(footprint, dtype=bool)
    if fp.ndim != 2 or not fp.any():
        raise ValueError("footprint must be nonempty and 2-D")
    arrays = {
        "det_elev": robust_z(det_elev, fp),
        "iso_grav_anom": robust_z(iso_grav_anom, fp),
        "tmi": robust_z(tmi, fp),
    }

    features: dict[str, np.ndarray] = dict(arrays)
    gains: dict[tuple[str, float], np.ndarray] = {}
    directions: dict[tuple[str, float], np.ndarray] = {}
    mags_at_300: dict[str, np.ndarray] = {}
    directions_by_scale: dict[float, dict[str, np.ndarray]] = {}

    for sigma in SIGMAS_PX:
        grad: dict[str, tuple[np.ndarray, ...]] = {
            name: _gradients(z, sigma) for name, z in arrays.items()
        }
        for name, (_gx, _gy, mag, _ux, _uy) in grad.items():
            features[f"{name}_gradient_magnitude_sigma{int(sigma)}"] = mag
            if sigma == 3.0:
                mags_at_300[name] = mag
        ty, tx = grad["det_elev"][3], grad["det_elev"][4]
        by_scale: dict[str, np.ndarray] = {}
        for name in ("iso_grav_anom", "tmi"):
            gain, direction = _lag_gain((ty, tx), (grad[name][3], grad[name][4]))
            gains[(name, sigma)] = gain
            directions[(name, sigma)] = direction
            features[f"{name}_lag_gain_sigma{int(sigma)}"] = gain
            by_scale[name] = direction
        directions_by_scale[sigma] = by_scale

    scale_coherence: dict[str, np.ndarray] = {}
    for name in ("iso_grav_anom", "tmi"):
        coh = _direction_cosine(directions[(name, 3.0)], directions[(name, 8.0)])
        scale_coherence[name] = coh
        features[f"{name}_offset_scale_coherence"] = coh
    sensor_coherence: dict[float, np.ndarray] = {}
    for sigma in SIGMAS_PX:
        coh = _direction_cosine(
            directions_by_scale[sigma]["iso_grav_anom"],
            directions_by_scale[sigma]["tmi"],
        )
        sensor_coherence[sigma] = coh
        features[f"gravity_magnetic_offset_coherence_sigma{int(sigma)}"] = coh

    edge = _edge_strength(
        (mags_at_300["det_elev"], mags_at_300["iso_grav_anom"], mags_at_300["tmi"]), fp
    )
    features["edge_strength"] = edge
    gain_product = (
        gains[("iso_grav_anom", 3.0)]
        * gains[("iso_grav_anom", 8.0)]
        * gains[("tmi", 3.0)]
        * gains[("tmi", 8.0)]
    )
    lag_gain = np.power(np.maximum(gain_product, 0.0), 0.25).astype(np.float32)
    coherence = (
        scale_coherence["iso_grav_anom"]
        * scale_coherence["tmi"]
        * np.sqrt(sensor_coherence[3.0] * sensor_coherence[8.0])
    )
    raw_score = (lag_gain * coherence * edge).astype(np.float32)
    raw_score[~fp] = 0.0
    raw_score[~np.isfinite(raw_score)] = 0.0
    q99 = float(np.quantile(raw_score[fp], 0.99))
    if not np.isfinite(q99) or q99 <= EPS:
        surface = np.zeros(fp.shape, dtype=np.float32)
    else:
        surface = np.clip(raw_score / q99, 0.0, 1.0).astype(np.float32)
    surface[~fp] = 0.0
    features["PFTL1_final_score"] = surface
    receipt = {
        "raw_score_q99_footprint": q99,
        "surface_positive_pixels": int(((surface > 0.0) & fp).sum()),
        "surface_unique_values": int(np.unique(surface[fp]).size),
        "surface_mean_footprint": float(surface[fp].mean()),
    }
    return surface, features, receipt
