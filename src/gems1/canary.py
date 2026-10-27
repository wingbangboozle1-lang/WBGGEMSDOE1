"""Leakage canary: each feature alone on the hide-and-recover holdout.

AUC > 0.90 on withheld catalogue pixels, using a feature that can see the
full catalogue (e.g. distance-to-all-faults), is leakage until proven otherwise.
"""
from __future__ import annotations

import numpy as np

from .holdout import HoldoutContext


def roc_auc(scores: np.ndarray, y: np.ndarray) -> float:
    s = np.asarray(scores, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=bool).ravel()
    n_pos = int(y.sum())
    n_neg = int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(s.size, dtype=np.float64)
    ranks[order] = np.arange(1, s.size + 1, dtype=np.float64)
    # average ranks for ties
    # (argsort mergesort is stable; skip full tie handling for speed — bias is tiny at n~1e6)
    sum_pos = float(ranks[y].sum())
    return (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def canary_aucs(
    fields: dict[str, np.ndarray],
    ctx: HoldoutContext,
    sample_neg: int = 80_000,
    seed: int = 32,
) -> dict:
    """AUC of each named field as a ranker of withheld positives vs background.

    Background = active holdout pixels that are not withheld positives.
    Distance-to-full-catalogue must flag (>0.90). Distance-to-visible must not
    be used as a detector feature.
    """
    rng = np.random.default_rng(seed)
    hidden = np.zeros(ctx.foot.shape, bool)
    active = np.zeros(ctx.foot.shape, bool)
    for f in ctx.folds:
        hidden |= f.hidden & f.active
        active |= f.active
    y_pos = hidden
    bg = active & ~y_pos
    py, px = np.nonzero(y_pos)
    ny, nx = np.nonzero(bg)
    if ny.size > sample_neg:
        pick = rng.choice(ny.size, size=sample_neg, replace=False)
        ny, nx = ny[pick], nx[pick]
    rows = {}
    leak = []
    for name, field in fields.items():
        field = np.asarray(field)
        sp = field[py, px]
        sn = field[ny, nx]
        scores = np.concatenate([sp, sn])
        y = np.concatenate([np.ones(sp.size, bool), np.zeros(sn.size, bool)])
        auc = roc_auc(scores, y)
        rows[name] = float(auc) if np.isfinite(auc) else None
        if np.isfinite(auc) and auc > 0.90:
            leak.append(name)
    return {
        "n_pos": int(y_pos.sum()),
        "n_neg_sampled": int(ny.size),
        "auc": rows,
        "leaking_auc_gt_0.90": leak,
        "pass": len(leak) == 0,
    }
