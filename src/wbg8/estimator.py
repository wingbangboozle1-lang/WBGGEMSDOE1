"""Registry-inversion DTI estimator (WBG-8 lane).

Why this estimator is *identifiable at all*
-------------------------------------------
For a truth indicator field ``T(x) in {0,1}`` and any submission whose dot set is
``P``, the official distance-weighted Tversky numerator is **exactly linear in T**:

    TP_w(P) = sum_{g in G} max_{y in P} k(d(y, g))
            = sum_x T(x) * C_P(x),        C_P(x) := max_{y in P} k(d(y, x)).

``C_P`` depends only on the submission, so one raster contributes the vector
``A_P[b] = sum_{x in bin b} C_P(x)`` and any candidate truth model ``pi`` gives

    E[TP_w] = sum_b pi_b * A_P[b]                      (no approximation beyond binning)

The false-positive term needs the *complement*: a dot pays ``1 - max_g k`` which
under a locally independent truth becomes the standard occupancy form
``exp(-L(y))`` with ``L = conv(pi, k)``.  Then

    DTI_hat(P) = TP / (TP + alpha*FP + beta*(K - TP)),   K = sum_x pi(x).

Fitting ``pi`` to the 118 owner-reported scores is therefore a low-dimensional
inverse problem in a *known* linear forward operator -- unlike the inherited
linear descriptor ridge (``evidence/wbg6_score_model.json``, grouped-CV R^2 -0.85)
or the 8-ring radial model that collapsed (``evidence/wbg6_truth_fit.json``).
Two parameters are fitted: a tilt exponent ``s`` (how concentrated the truth is
on the susceptibility ranking) and a catalogue-avoidance length ``c``.  Every
number it returns is a MODEL-ESTIMATE, never an organizer score.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
EPS = 1e-12

# distance-to-catalogue bands (pixels) used as the truth-model's support basis
DCAT_EDGES = (1.0, 2.0, 3.0, 6.0, 11.0, 21.0, 41.0, 81.0)
DCAT_LABELS = ("0", "1", "2", "3-5", "6-10", "11-20", "21-40", "41-80", ">80")
N_DCAT = len(DCAT_LABELS)


def dcat_band(dist_px: np.ndarray) -> np.ndarray:
    d = np.asarray(dist_px, np.float64)
    out = np.digitize(d, DCAT_EDGES, right=False).astype(np.int16)
    return np.where(np.isfinite(d), out, N_DCAT - 1).astype(np.int16)


def kernel_offsets(radius: float = RADIUS_PX):
    r = int(np.ceil(radius))
    dy, dx, kw = [], [], []
    for j in range(-r, r + 1):
        for i in range(-r, r + 1):
            k = max(1.0 - float(np.hypot(j, i)) / radius, 0.0)
            if k > 0.0:
                dy.append(j); dx.append(i); kw.append(k)
    return np.array(dy), np.array(dx), np.array(kw)


DY, DX, KW = kernel_offsets()


def coverage_field(dots: np.ndarray) -> np.ndarray:
    """C_P(x) = max kernel weight to any dot -- the submission's own cover field."""
    from scipy import ndimage as ndi

    d = ndi.distance_transform_edt(~dots)
    return np.maximum(1.0 - d / RADIUS_PX, 0.0).astype(np.float32)


def pi_field(z: np.ndarray, zedges: np.ndarray, s: float, fcat: np.ndarray,
             n_z: int) -> tuple[np.ndarray, np.ndarray]:
    """Truth probability field from a binned susceptibility tilt.

    ``pi = (pi_hab ** s) * fcat`` is evaluated per susceptibility bin; the bin
    representative is the bin's median susceptibility, so the whole fit runs on
    ``n_z`` numbers per raster instead of 12.3 M cells.
    """
    centre = np.array([0.0] * n_z, np.float64)
    lo = np.log(np.maximum(zedges[:-1], 1e-6))
    hi = np.log(np.maximum(zedges[1:], 1e-6))
    centre = np.exp(0.5 * (lo + hi))
    pi_z = centre ** float(s)
    pi = (pi_z[z] * fcat).astype(np.float32)
    return pi, pi_z


def dti_from(tp: np.ndarray, fp: np.ndarray, k_total: np.ndarray, n_dots: np.ndarray):
    """Vectorised DTI for many rasters from its three components."""
    den = tp + ALPHA * fp + BETA * np.maximum(k_total - tp, 0.0) + EPS
    return tp / den


@dataclass
class Fit:
    s: float
    c: float
    rmse: float
    mae: float
    pearson: float
    spearman: float
    r2: float
    n: int
    k_total: float
    cv: dict


def logit(p, lo=1e-4, hi=1 - 1e-4):
    p = np.clip(p, lo, hi)
    return np.log(p / (1.0 - p))
