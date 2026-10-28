"""Hide-and-recover evaluator on *real* fault geometry.

Protocol
--------
1. Decompose the public catalogue into connected components (whole faults).
2. Assign each component (>= ``min_px``) to one of ``n_folds`` spatial folds
   using a blocked split of its centroid, so a fold is a contiguous swath of
   the region.
3. For each fold: the fold's components are hidden.  Every candidate field is
   rebuilt from the *visible* components only.
4. Score with the official distance-weighted Tversky index (alpha=0.2,
   beta=0.8, R=300 m) implemented once in :mod:`gems.metric`.

The evaluator is a *relative* comparator between emission rules on identical
truth.  It is not a leaderboard forecast: the hidden set is catalogue geometry,
not the organisers' expert-labelled new faults.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import label

from gems.metric import dti_components_exact

EIGHT = np.ones((3, 3), bool)


def component_map(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lbl, n = label(mask, structure=EIGHT)
    return lbl, np.bincount(lbl.ravel(), minlength=n + 1)


def spatial_folds(cat: np.ndarray, n_folds: int = 4, min_px: int = 8,
                  blocks: int = 4) -> list[np.ndarray]:
    """Blocked spatial folds of whole catalogue components.

    The centroid of each qualifying component is assigned to one of
    ``blocks x blocks`` geographic blocks; blocks are then dealt round-robin
    into ``n_folds`` folds so every fold spans the whole region.
    """
    lbl, sizes = component_map(cat)
    keep = np.flatnonzero(sizes >= min_px)
    keep = keep[keep > 0]
    if keep.size == 0:
        raise ValueError("catalogue has no components above min_px")
    ys, xs = np.nonzero(cat)
    lid = lbl[ys, xs]
    cy = np.zeros(sizes.size)
    cx = np.zeros(sizes.size)
    np.add.at(cy, lid, ys)
    np.add.at(cx, lid, xs)
    cy /= np.maximum(sizes, 1)
    cx /= np.maximum(sizes, 1)
    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()
    by = np.clip(((cy[keep] - y0) / max(y1 - y0, 1) * blocks).astype(int), 0, blocks - 1)
    bx = np.clip(((cx[keep] - x0) / max(x1 - x0, 1) * blocks).astype(int), 0, blocks - 1)
    block_id = by * blocks + bx
    folds: list[np.ndarray] = []
    fold_of_comp = np.full(sizes.size, -1, int)
    for f in range(n_folds):
        sel = keep[(block_id % n_folds) == f]
        fold_of_comp[sel] = f
    for f in range(n_folds):
        m = np.zeros(cat.shape, bool)
        sel = np.flatnonzero(fold_of_comp == f)
        if sel.size:
            lut = np.zeros(sizes.size, bool)
            lut[sel] = True
            m = lut[lbl]
        folds.append(m)
    return folds


def evaluate(pred: np.ndarray, truth: np.ndarray, valid: np.ndarray,
             catalogue_mask: np.ndarray | None, alpha: float = 0.2,
             beta: float = 0.8) -> dict:
    """Official DTI on the withheld geometry, with and without catalogue masking."""
    comp = dti_components_exact(
        np.asarray(pred, np.float32), truth.astype(np.float32),
        valid_mask=valid.astype(np.uint8), catalogue_mask=None, alpha=alpha, beta=beta,
    )
    out = {"dti": comp["dti"], "TP_w": comp["TP_w"], "FP_w": comp["FP_w"],
           "FN_w": comp["FN_w"], "n_truth": int(comp["n_truth"]),
           "coverage": comp["coverage"]}
    if catalogue_mask is not None:
        comp2 = dti_components_exact(
            np.asarray(pred, np.float32), truth.astype(np.float32),
            valid_mask=valid.astype(np.uint8),
            catalogue_mask=catalogue_mask.astype(np.uint8), alpha=alpha, beta=beta,
        )
        out["dti_catmasked"] = comp2["dti"]
        out["TP_w_catmasked"] = comp2["TP_w"]
    return out


def bootstrap_ci(values: np.ndarray, n_boot: int = 2000, seed: int = 0,
                 alpha: float = 0.05) -> tuple[float, float]:
    v = np.asarray(values, float)
    if v.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, v.size, (n_boot, v.size))].mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


def structural_split(cat: np.ndarray, seed: int = 1, min_px: int = 20,
                     frac_range: tuple[float, float] = (0.30, 0.55)) -> tuple[np.ndarray, np.ndarray]:
    """Hide the distal part of every catalogue component.

    Returns ``(kept, hidden)``: the proximal part of each component stays visible
    and the distal 30-55 % is treated as "the segment the catalogue missed".
    This is the sharpest available analogue of "the public map is incomplete".
    """
    from .structure import _pca

    lbl, n = label(cat, structure=EIGHT)
    W = cat.shape[1]
    idx = np.flatnonzero(cat.ravel())
    comp = lbl.ravel()[idx]
    o = np.argsort(comp, kind="stable")
    idx, comp = idx[o], comp[o]
    b = np.searchsorted(comp, np.arange(1, n + 2))
    rng = np.random.default_rng(seed)
    kept = np.zeros(cat.shape, bool)
    hidden = np.zeros(cat.shape, bool)
    for k in range(n):
        sel = idx[b[k]:b[k + 1]]
        if len(sel) < min_px:
            continue
        ys, xs = (sel // W).astype(float), (sel % W).astype(float)
        cy, cx, dy, dx = _pca(ys, xs)
        t = (ys - cy) * dy + (xs - cx) * dx
        thr = np.quantile(t, 1 - rng.uniform(*frac_range))
        hid = t >= thr
        if (~hid).sum() < 6 or hid.sum() < 5:
            continue
        kept.ravel()[sel[~hid]] = True
        hidden.ravel()[sel[hid]] = True
    return kept, hidden


def translated_truth(cat: np.ndarray, footprint: np.ndarray, dy: int, dx: int,
                     guard_px: float = 3.0) -> np.ndarray:
    """Adversarial truth model: the network rigidly translated, as if the new
    faults were unrelated structures elsewhere in the region."""
    H, W = cat.shape
    s = np.zeros_like(cat)
    y0, y1 = max(0, dy), min(H, H + dy)
    x0, x1 = max(0, dx), min(W, W + dx)
    s[y0:y1, x0:x1] = cat[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    from .emission import dilate

    return s & footprint & ~dilate(cat, guard_px)
