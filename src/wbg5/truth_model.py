"""Radial hidden-truth model for the DOE GEMS private label set.

Model
-----
The private truth ``G`` is a set of ``K`` cells (|G| = K) drawn independently with
probability proportional to a radial density ``lam_r`` defined on concentric rings
of distance to the *public* mapped-fault catalogue.  Truth is independent of any
submission, which is what makes it identifiable from many submissions at once.

For a binary dot submission with ``n`` dots:

    TP_w = sum_{g in G} f(g),        f(x) = max_{a in dots} k(|x-a|)
    FP_w = sum_a (1 - h(a)),         h(a) = max_{g in G} k(|a-g|)
    FN_w = K - TP_w
    DTI  = TP_w / (TP_w + ALPHA*FP_w + BETA*FN_w)

``TP_w`` is *linear* in the truth indicator, so its expectation is exact:
``E[TP_w] = sum_r K*w_r*abar_r`` where ``abar_r`` is the mean over ring ``r`` cells
of the submission's own coverage field ``f``.  ``abar_r`` depends only on the
submission, so it is a sufficient statistic computed once per raster.

``FP_w`` needs the max over truth cells.  Under a locally Poisson truth with
density ``lam`` per cell and kernel mass ``S = sum_{d<=R} k(d)``:

    P(no truth inside the kernel) = exp(-S*lam)  =>  E[1 - h(a)] = exp(-S*lam_r(a))

which is the standard ``1 - exp(-rate)`` occupancy form.  Both terms are exact
in the limits ``lam -> 0`` (no truth anywhere) and ``lam -> inf`` (full cover); the
approximation only errs at intermediate density, where it is documented as such
and tested against brute force in ``tests/test_wbg5_truth_model.py``.
"""

from __future__ import annotations

import numpy as np

ALPHA = 0.2          # official FP coefficient (DrivenData page 967)
BETA = 0.8           # official FN coefficient
RADIUS_PX = 3.0      # 300 m triangular kernel support at 100 m cells
EPS = 1e-12

# concentric rings of distance to the nearest mapped-fault cell (pixels = 100 m)
RING_EDGES = (1.0, 3.0, 6.0, 11.0, 21.0, 41.0, 81.0, np.inf)
RING_LABELS = ("d=0", "1-2", "3-5", "6-10", "11-20", "21-40", "41-80", ">80")


def kernel_mass(radius: float = RADIUS_PX) -> float:
    """Discrete mass ``sum_{|d| <= R} max(1 - |d|/R, 0)`` on the 100 m lattice."""
    r = int(np.ceil(radius))
    s = 0.0
    for j in range(-r, r + 1):
        for i in range(-r, r + 1):
            d = float(np.hypot(j, i))
            s += max(1.0 - d / radius, 0.0)
    return s


KERNEL_MASS = kernel_mass()


def ring_ids(dist_px: np.ndarray, edges=RING_EDGES) -> np.ndarray:
    """Ring index per cell; ``-1`` for non-finite distances."""
    d = np.asarray(dist_px, dtype=np.float64)
    idx = np.digitize(d, edges, right=False)
    idx = np.where(np.isfinite(d), idx, -1)
    return idx.astype(np.int16)


def sufficient_statistics(coverage: np.ndarray, rings: np.ndarray, weights: np.ndarray,
                          n_rings: int) -> np.ndarray:
    """Ring means of a submission's coverage field (``abar_r``), weighted by cell area.

    ``weights`` sums to 1 over scored cells, so ``abar`` is the area-weighted mean.
    """
    out = np.zeros(n_rings, np.float64)
    for r in range(n_rings):
        m = rings == r
        if m.any():
            w = weights[m]
            out[r] = float((coverage[m] * w).sum() / w.sum())
    return out


def dti_from_components(tp: float, fp: float, fn: float) -> float:
    """Official distance-weighted Tversky index from its three components."""
    den = tp + ALPHA * fp + BETA * fn + EPS
    return float(tp / den) if den > 0 else 0.0


def dti_components(values: np.ndarray, truth: np.ndarray, kernel: np.ndarray) -> dict:
    """Brute-force reference implementation of the official metric.

    ``kernel`` is a precomputed (2R+1)^2 kernel with a zero centre handled by the
    caller; this helper takes the *distance* transform route to stay simple and is
    used only by tests and final reporting, never inside the optimiser.
    """
    from scipy.ndimage import distance_transform_edt

    p = np.asarray(values, np.float64)
    g = np.asarray(truth, bool)
    if p.shape != g.shape:
        raise ValueError("prediction/truth shape mismatch")
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("prediction must be finite in [0,1]")
    d_to_dot = distance_transform_edt(~(p > 0))
    k_dot = np.maximum(1.0 - d_to_dot / RADIUS_PX, 0.0)
    d_to_truth = distance_transform_edt(~g)
    k_truth = np.maximum(1.0 - d_to_truth / RADIUS_PX, 0.0)
    tp = float(k_dot[g].sum())
    fp = float((p * (1.0 - k_truth)).sum())
    fn = float(g.sum()) - tp
    return {"tp": tp, "fp": fp, "fn": fn, "K": int(g.sum()),
            "dti": dti_from_components(tp, fp, fn)}


def predict_score(abar: np.ndarray, counts: np.ndarray, ring_cells: np.ndarray,
                  w: np.ndarray, K: float) -> float:
    """Expected DTI of one submission under the radial truth model.

    ``abar``      : ring means of the submission coverage field   (n_rings,)
    ``counts``    : submitting dots per ring                      (n_rings,)
    ``ring_cells``: scored cells per ring                         (n_rings,)
    ``w``         : fraction of the hidden truth in each ring     (n_rings,)
    ``K``         : total hidden-truth cells

    ``E[TP] = sum_r (K w_r) abar_r`` is exact (linearity).  ``E[FP]`` uses the
    Poisson occupancy form ``E[1-h] = exp(-S*lam_r)``.
    """
    w = np.asarray(w, float)
    ring_cells = np.maximum(np.asarray(ring_cells, float), 1.0)
    lam = K * w / ring_cells
    tp = float(min((np.asarray(abar, float) * (K * w)).sum(), K))
    fp = float((np.asarray(counts, float) * (1.0 - np.exp(-KERNEL_MASS * lam))).sum())
    fp = float(min(fp, counts.sum()))
    fn = max(K - tp, 0.0)
    return dti_from_components(tp, fp, fn)


class ModelFit:
    """Container for a fitted (K, w) radial truth model plus its diagnostics."""

    def __init__(self, K: float, w: np.ndarray, ring_cells: np.ndarray, **extra):
        K = float(K)
        w = np.asarray(w, float)
        if K <= 0:
            raise ValueError("K must be positive")
        if (w < 0).any():
            raise ValueError("ring weights must be non-negative")
        if not np.isclose(w.sum(), 1.0, atol=1e-6):
            raise ValueError("ring weights must be normalised")
        self.K = K
        self.w = w
        self.ring_cells = np.asarray(ring_cells, float)
        self.extra = extra

    @property
    def lam(self) -> np.ndarray:
        """Truth cells per 100 m cell within each ring."""
        return self.K * self.w / np.maximum(self.ring_cells, 1.0)

    def score(self, abar, counts) -> float:
        return predict_score(abar, counts, self.ring_cells, self.w, self.K)

    def to_dict(self) -> dict:
        return {"K_truth_cells": self.K,
                "ring_edges_px": [float(e) if np.isfinite(e) else None for e in RING_EDGES],
                "ring_labels": list(RING_LABELS),
                "ring_weights": [float(v) for v in self.w],
                "ring_cells": [int(v) for v in self.ring_cells],
                "truth_density_per_ring": [float(v) for v in self.lam],
                **self.extra}
