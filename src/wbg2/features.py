"""Feature construction for WBG-2 from official external data.

Inputs (all on the exact competition grid: EPSG:32611, 3730x3292, 100 m,
transform origin 243350/4508550):

  geodawn_rad_u8.tif            4 bands: K, Th, U, TC
      Source: USGS GeoDAWN airborne radiometric survey, ScienceBase item
      657e1d85d34e23d3533209f7, DOI 10.5066/P93LGLVQ -- the same item the
      competition links from its problem description. Rights: USGS, no use
      restriction.
  lidar_scarp_features_u8.tif  12 bands: ex_max, ex_mean, step_max, lapneg_max,
      lappos_max, downface_max, upface_max, cross_max, relief, coh100, strike,
      valid -- USGS 3DEP 1 m DEM terrain descriptors aggregated to 100 m.
      Rights: USGS 3DEP, no use restriction (acknowledge USGS NGP).

Both are 8-bit quantised. Quantisation rule (per the sidecar JSON shipped with
the product): q = 1 + round(254 * t(clip(x/xmax,0,1))), t in {sqrt, linear},
0 = absent. We invert it to recover a [0,1] proxy scale. The inverse is
monotone, so ranks and any rank-based detector are unaffected by the exact
inverse; absolute physical units are NOT recovered and are never asserted.

Hypothesis WBG-2
----------------
Fault scarps are *antisymmetric* steps: a steep free face on the uplifted side
and a gentler surface on the other. They are also *elongated*: locally 1-D.
A detector that requires BOTH a strong short-wavelength step AND high linear
coherence AND an up-facing/down-facing asymmetry should preferentially select
scarps.

Named non-fault mimic (required by the run-card protocol)
---------------------------------------------------------
Ephemeral channels and washes, terrace risers, paleo-shorelines, landslides,
quarry/mine benches and roads all produce strong short-wavelength steps and can
be locally linear. Channels in particular produce the *opposite* asymmetry
(steep face pointing down-slope, i.e. channel banks). We therefore keep the
signed asymmetry term and do not take its absolute value. This is a mitigation,
not a proof: a road cut on a hillside is antisymmetric and will pass.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

RAD_BANDS = ("K", "Th", "U", "TC")
LIDAR_BANDS = (
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
    "downface_max", "upface_max", "cross_max", "relief", "coh100",
    "strike", "valid",
)

#: xmax used by the shipped quantisation table (lidar_scarp_features.json).
LIDAR_XMAX = {
    "ex_max": 1.5, "ex_mean": 0.3, "step_max": 1.0, "lapneg_max": 0.05,
    "lappos_max": 0.05, "downface_max": 1.0, "upface_max": 1.0,
    "cross_max": 1.0, "relief": 300.0, "coh100": 1.0, "strike": 180.0,
    "valid": 1.0,
}
#: Which lidar channels were sqrt-quantised (vs linear).
LIDAR_SQRT = {
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
    "downface_max", "upface_max", "cross_max", "relief",
}

#: Radiometric quantisation is undocumented in the sidecar we hold; we only use
#: percentile ranks of these bands, so the unknown scale cancels.
RAD_UNKNOWN_SCALE = True


def decode_lidar(q: np.ndarray, name: str) -> np.ndarray:
    """Invert q = 1 + round(254*t(x/xmax)) on the *scale-free* level t.

    Returns t in [0,1] (0 means "no lidar here"). Because t is monotone in x we
    use t as a proxy for physical strength and never report physical units.
    """
    t = (np.asarray(q, dtype=np.float32) - 1.0) / 254.0
    np.clip(t, 0.0, 1.0, out=t)
    if name in LIDAR_SQRT:
        return t * t  # invert sqrt
    return t


def normalize_robust(a: np.ndarray, mask: np.ndarray, lo=1.0, hi=99.0) -> np.ndarray:
    """Percentile normalisation to [0,1] over `mask`; 0 outside `mask`."""
    out = np.zeros_like(a, dtype=np.float32)
    if not mask.any():
        return out
    v = a[mask]
    p_lo, p_hi = np.percentile(v, [lo, hi])
    if p_hi <= p_lo:
        return out
    np.clip((a - p_lo) / (p_hi - p_lo), 0.0, 1.0, out=out)
    out[~mask] = 0.0
    return out


def structure_tensor(
    intensity: np.ndarray, mask: np.ndarray, sigma: float = 2.0, rho: float = 4.0
):
    """Structure tensor and derived line-likeness/orientation.

    Returns (line_likeness, energy, theta) where theta is the *structure*
    orientation (direction of elongation) in radians, measured on the
    doubled-angle representation and halved back.
    """
    i = np.where(mask, intensity, 0.0).astype(np.float64)
    gy, gx = np.gradient(i)
    jxx = ndi.gaussian_filter(gx * gx, sigma)
    jyy = ndi.gaussian_filter(gy * gy, sigma)
    jxy = ndi.gaussian_filter(gx * gy, sigma)
    # smooth the tensor components to get the *local* average orientation
    jxx = ndi.gaussian_filter(jxx, rho)
    jyy = ndi.gaussian_filter(jyy, rho)
    jxy = ndi.gaussian_filter(jxy, rho)

    tmp = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy ** 2)
    l1 = 0.5 * (jxx + jyy + tmp)
    l2 = 0.5 * (jxx + jyy - tmp)
    energy = l1 + l2
    with np.errstate(invalid="ignore", divide="ignore"):
        line_likeness = np.where(energy > 0, (l1 - l2) / (energy + 1e-12), 0.0)
    # gradient orientation is the dominant eigenvector direction; the structure
    # (elongation) direction is perpendicular to the gradient
    grad_theta = 0.5 * np.arctan2(2.0 * jxy, (jxx - jyy))
    theta = grad_theta - np.pi / 2.0
    line_likeness = np.where(mask, line_likeness, 0.0).astype(np.float32)
    return line_likeness, energy.astype(np.float32), theta.astype(np.float32)


def scarp_asymmetry(upface: np.ndarray, downface: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Signed asymmetry in [0,1]: 1 = strongly up-facing (scarp-like), 0 = channel-like.

    A fault scarp exposes a free face with a consistent facing. Channels put the
    steep face on the opposite side, so the sign carries information. We map the
    signed difference to [0,1] rather than taking |.|, deliberately keeping the
    channels-mimic discrimination that an absolute value would destroy.
    """
    d = upface - downface
    out = 0.5 * (d + 1.0)
    return np.where(mask, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)


def radiometric_alteration(k, th, u, mask) -> np.ndarray:
    """Hydrothermal alteration proxy: relative K (+U) enrichment against Th.

    Faults in the Great Basin commonly focus hydrothermal fluids that enrich K
    and deplete Th in wall rock. We use a *relative* index so the unknown
    radiometric scale cancels:

        A = rank(K) - rank(Th) + 0.5*(rank(U) - rank(Th))

    which is 0.5-centred. High values = K,U rich relative to Th.
    """
    rk = _rank01(k, mask)
    rt = _rank01(th, mask)
    ru = _rank01(u, mask)
    a = rk - rt + 0.5 * (ru - rt)
    return np.where(mask, np.clip(0.5 + a / 2.0, 0.0, 1.0), 0.0).astype(np.float32)


def _rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] over `mask` (0 outside)."""
    out = np.zeros(a.shape, dtype=np.float32)
    if not mask.any():
        return out
    v = a[mask].astype(np.float64)
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=np.float64)
    ranks[order] = np.arange(v.size, dtype=np.float64)
    out[mask] = (ranks / max(1, v.size - 1)).astype(np.float32)
    return out


def fault_evidence(rad: np.ndarray, lidar: np.ndarray, footprint: np.ndarray):
    """Combine the official layers into a fault-likeness score in [0,1].

    Returns (score, line_likeness, theta, valid_mask, terms) so the caller can
    audit each contribution.
    """
    if rad.shape[0] != 4 or lidar.shape[0] != 12:
        raise ValueError(f"expected 4 rad and 12 lidar bands, got {rad.shape[0]}/{lidar.shape[0]}")

    L = {name: decode_lidar(lidar[i], name) for i, name in enumerate(LIDAR_BANDS)}
    # Lidar coverage: `valid` > 0 marks cells with at least some 3DEP samples.
    valid = (lidar[LIDAR_BANDS.index("valid")] > 0) & footprint
    # `coh100` further filters cells where the 2 m mosaic was coherent.
    coh = normalize_robust(L["coh100"], valid)

    # 1. short-wavelength step strength (scarp free face)
    step = normalize_robust(np.maximum(L["step_max"], L["ex_max"]), valid)
    # 2. crest convexity (scarp crest)
    crest = normalize_robust(L["lapneg_max"], valid)
    # 3. signed asymmetry
    asym = scarp_asymmetry(L["upface_max"], L["downface_max"], valid)
    # 4. lineament geometry from the step field
    line_lik, energy, theta = structure_tensor(step, valid, sigma=2.0, rho=5.0)
    line_lik_n = normalize_robust(line_lik, valid)
    # 5. radiometric alteration (available wherever the survey covers)
    rad_mask = footprint
    alter = radiometric_alteration(rad[0], rad[1], rad[2], rad_mask)

    terms = {
        "step": step,
        "crest": crest,
        "asym": asym,
        "line_likeness": line_lik_n,
        "alteration": alter,
        "coherence": coh,
    }
    # Multiplicative gating: a cell must be step-like AND linear AND covered.
    # Weighting is a prior, fixed before scoring (see registry/preregistration).
    score = (
        np.power(np.clip(step, 0, 1), 0.5)
        * np.clip(line_lik_n, 0, 1)
        * (0.5 + 0.5 * np.clip(asym, 0, 1))
        * (0.6 + 0.4 * np.clip(alter, 0, 1))
        * (0.5 + 0.5 * np.clip(coh, 0, 1))
    )
    score = np.where(valid, score, 0.0).astype(np.float32)
    return score, line_lik_n, theta, valid, terms


def thin_to_centerline(score: np.ndarray, theta: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Non-maximum suppression across the ridge normal.

    For a ridge elongated along `theta`, the normal is theta + pi/2. We keep a
    cell only if its score is >= both neighbours along that normal, sampled at
    +/-1 px with bilinear interpolation. This converts blobs into 1-px curves.
    """
    ny = -np.sin(theta)  # normal direction (unit)
    nx = np.cos(theta)
    coords = np.indices(score.shape, dtype=np.float32)

    def sample(dy, dx):
        return ndi.map_coordinates(
            score, [coords[0] + dy, coords[1] + dx], order=1, mode="nearest"
        )

    fwd = sample(ny, nx)
    bwd = sample(-ny, -nx)
    keep = (score >= fwd) & (score >= bwd) & (score > 0) & mask
    return keep
