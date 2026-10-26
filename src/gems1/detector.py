"""Lane detectors. Primary lane: TSML (no DEM-ridge / H19-5 family).

Physical basis (Walker Lane / western Great Basin):
  USGS QFaults preferentially maps range-front normal scarps. Expert-labeled
  hidden test faults are expected to include intra-basin and Walker Lane
  structures whose surface expression is weak but whose basement contact and
  current loading are visible in magnetics, gravity, and geodetic strain.

  We do NOT use det_elev or det_elev_slope as the ridge source (that is the
  H19-5 Hessian-NMS family). Catalogue distance is a mask, never a feature.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from . import grid
from .emission import nms_ridge, poisson_priority, top_quantile


def _sm(a, s):
    return ndimage.gaussian_filter(a, s, mode="nearest")


def _hessian_ridge(a, sigma):
    axx = ndimage.gaussian_filter(a, sigma, order=(0, 2), mode="nearest")
    ayy = ndimage.gaussian_filter(a, sigma, order=(2, 0), mode="nearest")
    axy = ndimage.gaussian_filter(a, sigma, order=(1, 1), mode="nearest")
    tmp = np.sqrt(np.maximum(((axx - ayy) * 0.5) ** 2 + axy ** 2, 0.0))
    l1 = (axx + ayy) * 0.5 + tmp
    l2 = (axx + ayy) * 0.5 - tmp
    big = np.where(np.abs(l1) >= np.abs(l2), l1, l2)
    small = np.where(np.abs(l1) >= np.abs(l2), l2, l1)
    return -small * (big < 0).astype(np.float32)


def _structure_tensor(a, sigma):
    gx = ndimage.gaussian_filter(a, sigma, order=(0, 1), mode="nearest")
    gy = ndimage.gaussian_filter(a, sigma, order=(1, 0), mode="nearest")
    jxx = _sm(gx * gx, sigma)
    jyy = _sm(gy * gy, sigma)
    jxy = _sm(gx * gy, sigma)
    tr = jxx + jyy + 1e-12
    coh = np.sqrt(np.maximum(((jxx - jyy) * 0.5) ** 2 + jxy ** 2, 0.0)) / tr
    return coh.astype(np.float32), gx.astype(np.float32), gy.astype(np.float32)


def _z01(a, foot):
    v = a[foot]
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    if hi <= lo:
        return np.zeros_like(a, dtype=np.float32)
    out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    return np.where(foot, out, 0.0).astype(np.float32)


def load_filled_bands(features_path, bands, footprint):
    filled = {}
    for b in bands:
        raw, valid = grid.read_band(features_path, b)
        valid = valid & footprint
        filled[b] = grid.fill_nearest(raw, valid)
    return filled


def tsml_field(features_path, footprint) -> dict:
    """Transtensional strain-gated magnetic-contact lineaments.

    Layers: tmi_hg (3), geod_2ndinv (4), geod_shearrate (7), geod_dilaterate (8),
            iso_grav_anom_slope (5), depth_to_base_surf (15), rtp (2).
    Signature: Hessian ridges of magnetic horizontal-gradient magnitude, corroborated
    by gravity slope and basement-depth gradient, gated to extensional high-strain
    corridors (dilatation > 0 and elevated 2nd invariant).
    """
    foot = np.asarray(footprint, bool)
    B = load_filled_bands(features_path, (2, 3, 4, 5, 7, 8, 15), foot)
    tmi_hg = B[3]
    inv = B[4]
    dil = B[8]
    grav_s = B[5]
    depth = B[15]
    rtp = B[2]

    # Strain gate: currently loading AND extensional (transtension / Basin-Range).
    dil_pos = dil > 0.0
    inv01 = _z01(inv, foot)
    strain_gate = foot & dil_pos & (inv01 >= np.quantile(inv01[foot], 0.40))

    ridge = 0.65 * _hessian_ridge(tmi_hg, 1.6) + 0.35 * _hessian_ridge(tmi_hg, 2.8)
    ridge = np.maximum(ridge, 0.0)
    coh, gx, gy = _structure_tensor(tmi_hg, 2.0)
    depth_g = np.hypot(*np.gradient(_sm(depth, 2.0)))
    grav01 = _z01(grav_s, foot)
    depth01 = _z01(depth_g, foot)
    rtp_edge = _z01(np.abs(ndimage.gaussian_laplace(rtp, 1.8)), foot)

    score = (
        _z01(ridge, foot)
        * (0.25 + 0.75 * coh)
        * (0.50 + 0.50 * grav01)
        * (0.50 + 0.50 * depth01)
        * (0.70 + 0.30 * rtp_edge)
    )
    score = np.where(strain_gate, score, score * np.float32(0.15))
    score = np.where(foot, score.astype(np.float32), np.float32(0.0))
    nms = nms_ridge(score, gy, gx) & foot & (score > 0)
    return dict(score=score, nms=nms, strain_gate=strain_gate, coh=coh, gy=gy, gx=gx)


def mvgz_field(features_path, footprint) -> dict:
    """Magnetic vertical-gradient zero-crossing contacts (Blakely-style).

    Layers: tmi_vg (9), tmi_hg (3), geod_2ndinv (4). Zero-crossings of the
    vertical derivative mark contacts; weighted by horizontal-gradient magnitude.
    """
    foot = np.asarray(footprint, bool)
    B = load_filled_bands(features_path, (3, 4, 9), foot)
    vg = B[9]
    hg = B[3]
    inv = B[4]
    zc = np.zeros(vg.shape, bool)
    zc[:, 1:] |= (vg[:, 1:] * vg[:, :-1]) <= 0
    zc[1:, :] |= (vg[1:, :] * vg[:-1, :]) <= 0
    zc &= foot
    score = zc.astype(np.float32) * _z01(hg, foot) * (0.4 + 0.6 * _z01(inv, foot))
    gy, gx = np.gradient(_sm(hg, 1.5))
    nms = nms_ridge(score + 1e-6 * hg, gy, gx) & zc
    return dict(score=score.astype(np.float32), nms=nms, strain_gate=zc, gy=gy, gx=gx)


def emit_from_field(
    field: dict,
    footprint: np.ndarray,
    labels: np.ndarray,
    d_visible: np.ndarray | None,
    min_dist: float = 3.2,
    n_max: int = 38000,
    support_q: float = 0.012,
    b_px: float = 2.0,
) -> np.ndarray:
    score = field["score"]
    nms = field["nms"]
    support = nms & top_quantile(score, support_q, footprint)
    if d_visible is None:
        from scipy.ndimage import distance_transform_edt

        d_visible = distance_transform_edt(~np.asarray(labels, bool))
    support = support & (d_visible > float(b_px)) & footprint & ~np.asarray(labels, bool)
    return poisson_priority(score, support, min_dist=min_dist, n_max=n_max)
