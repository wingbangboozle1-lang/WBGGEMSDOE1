"""Compatibility adapter to the pinned shared distance-weighted metric.

No independent evaluator is maintained for WBG-2. This adapter is useful for
small arithmetic tests only; holdout results must use the shared holdout
instrument and visible-only fold-specific features.
"""
from pathlib import Path
import sys
import numpy as np

VENDOR = Path(__file__).resolve().parents[2] / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
from gems57 import metric as shared  # noqa: E402

ALPHA, BETA, EPS = shared.ALPHA, shared.BETA, shared.EPS
R_PIXELS, R_METRES, PIXEL_METRES = shared.RADIUS_PX, shared.R_M, shared.PIXEL_M
triangular_kernel = shared.kernel


def dti(prediction, truth, footprint=None, alpha=ALPHA, beta=BETA, profile=False):
    p = np.asarray(prediction, dtype=np.float64)
    g = np.asarray(truth, dtype=bool)
    if p.ndim != 2 or p.shape != g.shape:
        raise ValueError("prediction and truth must be matching two-dimensional arrays")
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("prediction must be finite in [0, 1]")
    valid = np.ones(p.shape, dtype=bool) if footprint is None else np.asarray(footprint, dtype=bool)
    if valid.shape != p.shape:
        raise ValueError("footprint shape mismatch")
    result = shared.dti_exact(p, g, valid=valid, alpha=alpha, beta=beta)
    if not profile:
        return result["dti"]
    components = {"tp_w": result["tp"], "fp_w": result["fp"], "fn_w": result["fn"],
                  "denominator": result["tp"] + alpha * result["fp"] + beta * result["fn"] + EPS,
                  "gt_pixels": result["n_truth"], "predicted_pixels": result["n_emitted"],
                  "alpha": alpha, "beta": beta, "r_pixels": R_PIXELS}
    return result["dti"], components
