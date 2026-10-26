"""WBG-C1: catalogue-blind conductance/depth curvature non-coaxiality.

The operator is a research hypothesis, not an established fault or vent detector.
Physical units of the mirror's `cond_surf` descriptor have not been independently
verified; each field is robust-scaled before taking derivatives. No catalogue or
prior submission is accepted by this module.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

SCALES_PX = (3.0, 8.0)
CHANNELS = (
    "commutator_300m",
    "commutator_800m",
    "commutator_scale_persistence",
    "commutator_dilatation_support",
)


def normalized_commutator(a, b):
    """Return |[A,B]_01| / (||A||_F ||B||_F) for symmetric 2x2 tensors.

    Input tuples are (xx, xy, yy), broadcastable, real and finite. This is the
    commutator Frobenius norm divided by sqrt(2) times the norm product, bounded
    by one. Shared eigendirections, isotropic tensors, or a zero tensor give zero.
    """
    aa, ab, ac = (np.asarray(x, dtype=np.float32) for x in a)
    bd, be, bf = (np.asarray(x, dtype=np.float32) for x in b)
    if not all(np.isfinite(x).all() for x in (aa, ab, ac, bd, be, bf)):
        raise ValueError("commutator tensors must be finite")
    numerator = np.abs(be * (aa - ac) + ab * (bf - bd))
    denominator = np.sqrt(aa * aa + 2 * ab * ab + ac * ac) * np.sqrt(
        bd * bd + 2 * be * be + bf * bf)
    result = np.divide(numerator, denominator, out=np.zeros_like(numerator),
                       where=denominator > 1e-12)
    # Analytic bound; clipping only removes float-roundoff of a derived feature,
    # never repairs predictions or a malformed submission.
    return np.clip(result, 0, 1).astype(np.float32)


def robust_field(raw, valid):
    """Robust-scale from valid measurements only and nearest-fill before filtering."""
    raw = np.asarray(raw, np.float32)
    valid = np.asarray(valid, bool) & np.isfinite(raw) & (np.abs(raw) < 1e30)
    if raw.ndim != 2 or valid.shape != raw.shape or not valid.any():
        raise ValueError("a nonempty aligned 2-D measurement mask is required")
    lo, median, hi = np.quantile(raw[valid], [.05, .5, .95])
    span = max(float(hi - lo), 1e-6)
    out = np.zeros_like(raw)
    out[valid] = np.clip((raw[valid] - median) / span, -4, 4)
    if not valid.all():
        indices = ndi.distance_transform_edt(~valid, return_distances=False, return_indices=True)
        missing = ~valid
        out[missing] = out[indices[0][missing], indices[1][missing]]
    return out, {"p05": float(lo), "median": float(median), "p95": float(hi)}


def hessian(field, sigma):
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    return tuple((sigma * sigma * ndi.gaussian_filter(
        field, sigma=sigma, order=order, mode="nearest", truncate=3.0)).astype(np.float32)
        for order in ((0, 2), (1, 1), (2, 0)))


def features(conductance, depth, dilatation, footprint):
    """Build four deterministic, catalogue-free feature planes and a small receipt."""
    footprint = np.asarray(footprint, bool)
    if any(np.asarray(x).shape != footprint.shape for x in (conductance, depth, dilatation)):
        raise ValueError("physical-layer grid mismatch")
    valid = footprint & np.isfinite(conductance) & np.isfinite(depth)
    valid &= (np.abs(conductance) < 1e30) & (np.abs(depth) < 1e30)
    c, cstats = robust_field(conductance, valid)
    z, zstats = robust_field(depth, valid)
    # Gaussian support is explicitly truncated at 3 sigma. Do not mistake
    # interpolation across the footprint or internal no-data holes for a fault.
    safe = valid & (ndi.distance_transform_edt(valid) > 3 * max(SCALES_PX))
    planes, curvature_stats = [], []
    for sigma in SCALES_PX:
        hc, hz = hessian(c, sigma), hessian(z, sigma)
        angle = normalized_commutator(hc, hz)
        cn = np.sqrt(hc[0]**2 + 2 * hc[1]**2 + hc[2]**2)
        zn = np.sqrt(hz[0]**2 + 2 * hz[1]**2 + hz[2]**2)
        cq = max(float(np.quantile(cn[safe], .9)) if safe.any() else 0, 1e-8)
        zq = max(float(np.quantile(zn[safe], .9)) if safe.any() else 0, 1e-8)
        strength = np.sqrt(np.minimum(cn / cq, 1) * np.minimum(zn / zq, 1))
        response = np.where(safe, angle * strength, 0).astype(np.float32)
        planes.append(response)
        curvature_stats.append({"sigma_px": sigma, "conductance_norm_p90": cq, "depth_norm_p90": zq})
    persistent = np.sqrt(planes[0] * planes[1]).astype(np.float32)
    d = np.asarray(dilatation, np.float32)
    dvalid = footprint & np.isfinite(d) & (np.abs(d) < 1e30)
    dq = max(float(np.quantile(np.maximum(d[dvalid], 0), .9)) if dvalid.any() else 0, 1e-6)
    strain = np.zeros_like(d)
    strain[dvalid] = np.clip(np.maximum(d[dvalid], 0) / dq, 0, 1)
    planes.extend((persistent, (persistent * strain).astype(np.float32)))
    receipt = {"channels": list(CHANNELS), "scales_px": list(SCALES_PX),
               "conductance_scaling": cstats, "depth_scaling": zstats,
               "curvature_scaling": curvature_stats, "dilatation_positive_p90": dq,
               "safe_feature_pixels": int(safe.sum()), "footprint_pixels": int(footprint.sum()),
               "catalogue_features_used": False, "prior_prediction_pixels_used": False,
               "warning": "Curvature disagreement can be a non-fault basin-fill/lithologic boundary or an inversion artifact."}
    return planes, receipt
