"""Feature construction for the WBG-D1 radiometric alteration lane.

Inputs are the hash-pinned USGS GeoDAWN-derived radiometric uint8 grids and the
shared 19-band float32 cache (RTP band 2, TMI band 14). Every derived channel is
computed from raw measurements only; no catalogue geometry, prior prediction,
or registry raster enters any feature.

Channels (frozen in registry/preregistration_wbg_d1.json):
    K_hp5, K_hp10, potassic_hp5, ThK_edge5, K_edge5, UTh_edge5, tmi_shallow
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage.feature import peak_local_max

RAD_BANDS = {"K": 1, "Th": 2, "U": 3, "TC": 4}
EXT_BANDS = {"ThK": 1, "UK": 2, "UTh": 3, "TMIup150": 4}
CHANNEL_NAMES = (
    "K_hp5",
    "K_hp10",
    "Potassic_hp5",
    "ThK_edge5",
    "K_edge5",
    "UTh_edge5",
    "tmi_shallow",
)
DOT_BUDGET = 37_654
NMS_SEP_PX = 3


def robust_z(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Median/MAD standardization estimated only on ``mask`` cells; float32."""
    a = np.asarray(a, np.float32)
    x = a[mask]
    med = np.median(x)
    mad = np.median(np.abs(x - med)) * 1.4826 + 1e-6
    return ((a - med) / mad).astype(np.float32)


def _smoothed_z(values: np.ndarray, valid: np.ndarray, footprint: np.ndarray,
                sigma: float) -> np.ndarray:
    """Robust z on valid cells, zero-filled outside the footprint before smoothing."""
    z = robust_z(np.where(values > 0, values, 0.0), valid & footprint)
    z = np.where(footprint, z, 0.0).astype(np.float32)
    return ndi.gaussian_filter(z, sigma, mode="nearest").astype(np.float32)


def _high_pass(values: np.ndarray, valid: np.ndarray, footprint: np.ndarray,
               sigma: float) -> np.ndarray:
    z = robust_z(np.where(values > 0, values, 0.0), valid & footprint)
    z = np.where(footprint, z, 0.0).astype(np.float32)
    blur = ndi.gaussian_filter(z, sigma, mode="nearest")
    return (z - blur).astype(np.float32)


def _edge(values: np.ndarray, valid: np.ndarray, footprint: np.ndarray,
          sigma: float) -> np.ndarray:
    smooth = _smoothed_z(values, valid, footprint, sigma)
    gy, gx = np.gradient(smooth)
    return np.hypot(gy, gx).astype(np.float32)


def build_radiometric_channels(rad_path: str | Path, ext_path: str | Path,
                               tmi_path: str | Path, footprint: np.ndarray,
                               catalogue: np.ndarray) -> dict[str, np.ndarray]:
    """Build the seven preregistered channels on the full competition grid.

    ``catalogue`` is accepted only to assert the feature builder never reads it;
    it is not used in any arithmetic.
    """
    if catalogue.shape != footprint.shape:
        raise ValueError("footprint/catalogue shape mismatch")
    footprint = np.asarray(footprint, bool)
    import rasterio

    with rasterio.open(rad_path) as ds:
        grids = {name: ds.read(b) for name, b in RAD_BANDS.items()}
        rad_nodata = ds.nodata
    with rasterio.open(ext_path) as ds:
        ext = {name: ds.read(b) for name, b in EXT_BANDS.items()}
    valid = (grids["K"] > 0) & (ext["ThK"] > 0) & footprint

    K_hp5 = _high_pass(grids["K"], valid, footprint, 5.0)
    K_hp10 = _high_pass(grids["K"], valid, footprint, 10.0)
    ThK_hp5 = _high_pass(ext["ThK"], valid, footprint, 5.0)
    potassic_hp5 = (K_hp5 - ThK_hp5).astype(np.float32)
    ThK_edge5 = _edge(ext["ThK"], valid, footprint, 5.0)
    K_edge5 = _edge(grids["K"], valid, footprint, 5.0)
    UTh_edge5 = _edge(ext["UTh"], valid, footprint, 5.0)

    tmi = np.load(tmi_path, mmap_mode="r")
    tmi = np.nan_to_num(np.asarray(tmi, np.float32)).astype(np.float32)
    tmi_z = np.where(footprint, robust_z(tmi, footprint), 0.0).astype(np.float32)
    tmiup_z = _smoothed_z(ext["TMIup150"], valid, footprint, 1.0)
    tmi_shallow = (tmi_z - tmiup_z).astype(np.float32)

    channels = {
        "K_hp5": K_hp5,
        "K_hp10": K_hp10,
        "Potassic_hp5": potassic_hp5,
        "ThK_edge5": ThK_edge5,
        "K_edge5": K_edge5,
        "UTh_edge5": UTh_edge5,
        "tmi_shallow": tmi_shallow,
    }
    # Gaussian mode='nearest' smoothing leaks across the footprint boundary;
    # outside cells are never scored and must stay exactly zero.
    for name, arr in channels.items():
        arr[~footprint] = 0.0
    # Defensive invariants: no NaN/inf inside footprint; zeros outside it.
    for name, arr in channels.items():
        if not np.isfinite(arr[footprint]).all():
            raise ValueError(f"non-finite channel inside footprint: {name}")
        if np.any(arr[~footprint] != 0.0):
            raise ValueError(f"channel mass outside footprint: {name}")
    channels["_meta"] = {  # type: ignore[dict-item]
        "radiometric_nodata_value": rad_nodata,
        "valid_coverage": float(valid.mean()),
    }
    return channels


def rtp_edge(rtp_path: str | Path, footprint: np.ndarray, sigma: float = 3.0) -> np.ndarray:
    """Gradient magnitude of robust-z smoothed RTP (band 2), used by EXP-1."""
    rtp = np.nan_to_num(np.asarray(np.load(rtp_path, mmap_mode="r"), np.float32))
    z = np.where(footprint, robust_z(rtp, footprint), 0.0).astype(np.float32)
    smooth = ndi.gaussian_filter(z, sigma, mode="nearest")
    gy, gx = np.gradient(smooth)
    out = np.hypot(gy, gx).astype(np.float32)
    out[~footprint] = 0.0
    return out


def deterministic_composite(channels: dict[str, np.ndarray], rtp_edge3: np.ndarray,
                            footprint: np.ndarray) -> np.ndarray:
    """Frozen EXP-1 score (preregistration formula); no fitted parameters."""
    score = (
        0.5 * channels["Potassic_hp5"]
        + 0.3 * channels["K_hp10"]
        + 0.4 * np.tanh(rtp_edge3 / 2.0)
        + 0.3 * np.tanh(channels["ThK_edge5"] / 2.0)
    ).astype(np.float64)
    score[~footprint] = -1e9
    return score


def nms_dots(score: np.ndarray, allowed: np.ndarray, budget: int = DOT_BUDGET,
             min_distance: int = NMS_SEP_PX) -> np.ndarray:
    """Fixed-budget local-maxima emission with >= 3 px Chebyshev separation."""
    if score.shape != allowed.shape:
        raise ValueError("score/allowed shape mismatch")
    s = np.asarray(score, np.float64).copy()
    s[~np.asarray(allowed, bool)] = -1e9
    finite = np.isfinite(s)
    if not finite.all():
        raise ValueError("score contains non-finite values inside the allowed mask")
    peaks = peak_local_max(
        s, min_distance=min_distance, threshold_abs=-1e8,
        num_peaks=budget, exclude_border=False)
    dots = np.zeros(allowed.shape, dtype=bool)
    if peaks.size:
        dots[peaks[:, 0], peaks[:, 1]] = True
    dots &= np.asarray(allowed, bool)
    return dots
