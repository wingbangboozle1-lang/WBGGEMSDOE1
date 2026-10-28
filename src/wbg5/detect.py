"""Spatially-blocked fault detection on the official 19-band stack.

Protocol
--------
The catalogue is split into a 4 x 4 lattice of geographic blocks (about
823 x 932 px, i.e. 82 x 93 km at 100 m).  A model trained on 12 blocks is scored
on the held-out blocks; the block never appears in training in any form.  This is
the only protocol in this repository that answers the question the competition
actually asks — *can the geophysics find a fault the catalogue does not list?* —
without letting catalogue geometry in through a side door.

Two truth definitions are scored on the held-out blocks:

``catalogue``
    the mapped fault pixels in the block (the model must recover geometry it has
    not seen, from features only).
``hidden-tail``
    the distal 30-55 % of every component, using :meth:`wbg5.holdout.structural_split`
    on the union of all blocks (a strictly harder, "the map stops early" truth).

Reported diagnostics: AUC, average precision, leakage canary (each single feature
alone), and — the number that decides the submission — the realised
``gems.metric`` DTI of a dotted emission built from the held-out probabilities.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

from . import grid

N_BLOCKS = 4
SEED = 20261028


def block_id() -> np.ndarray:
    """(H, W) int8 lattice id 0..15, aligned to the footprint bounding box."""
    H, W = grid.HEIGHT, grid.WIDTH
    by = np.minimum((np.arange(H) * N_BLOCKS) // H, N_BLOCKS - 1)
    bx = np.minimum((np.arange(W) * N_BLOCKS) // W, N_BLOCKS - 1)
    return (by[:, None] * N_BLOCKS + bx[None, :]).astype(np.int8)


def _rows_for(b: int) -> tuple[int, int]:
    H = grid.HEIGHT
    return (b // N_BLOCKS) * H // N_BLOCKS, (b // N_BLOCKS + 1) * H // N_BLOCKS


def training_rows(fold_block: int) -> tuple[int, int]:
    return _rows_for(fold_block)


def fit_fold(X, y, seed: int = SEED):
    from sklearn.ensemble import HistGradientBoostingClassifier

    clf = HistGradientBoostingClassifier(
        max_iter=180, learning_rate=0.08, max_leaf_nodes=48, min_samples_leaf=40,
        l2_regularization=1.0, early_stopping=True, validation_fraction=0.12,
        random_state=seed, max_bins=128)
    clf.fit(X, y)
    return clf


def auc(y, p) -> float:
    from sklearn.metrics import roc_auc_score
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, p))


def average_precision(y, p) -> float:
    from sklearn.metrics import average_precision_score
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(average_precision_score(y, p))


def emit_from_prob(prob: np.ndarray, footprint: np.ndarray, block_mask: np.ndarray,
                   n_dots: int, min_sep: float = 3.0, floor: float = 0.0,
                   seed: int = 0) -> np.ndarray:
    """Greedy non-maximum-suppressed peak picking of ``n_dots`` isolated pixels."""
    from .emission import select_isolated

    score = np.where(block_mask & footprint & (prob >= floor), prob, 0.0).astype(np.float32)
    return select_isolated(score, score > 0, n_dots, min_sep=min_sep, seed=seed)


def score_emission(pred: np.ndarray, truth: np.ndarray, footprint: np.ndarray,
                   catalogue: np.ndarray, mask_catalogue: bool = True) -> dict:
    from gems.metric import dti_components_exact

    comp = dti_components_exact(pred.astype(np.float32), truth.astype(np.float32),
                                valid_mask=footprint.astype(np.uint8),
                                catalogue_mask=catalogue.astype(np.uint8) if mask_catalogue else None,
                                alpha=0.2, beta=0.8)
    return {"dti": float(comp["dti"]), "TP": float(comp["TP_w"]), "FP": float(comp["FP_w"]),
            "FN": float(comp["FN_w"]), "n_truth": int(comp["n_truth"]),
            "coverage": float(comp["coverage"])}


def coverage_of_truth(truth: np.ndarray, pred: np.ndarray, radius: float = 3.0) -> float:
    if truth.sum() == 0:
        return 0.0
    d = distance_transform_edt(~pred)
    return float(((d <= radius) & truth).sum() / truth.sum())
