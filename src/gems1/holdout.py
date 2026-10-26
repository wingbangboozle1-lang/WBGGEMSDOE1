"""Spatially-blocked hide-and-recover holdout (protocol rule 2).

- Withhold whole connected fault segments (not random pixels).
- 15 px (1.5 km) collar so the 300 m kernel does not bleed across the split.
- Catalogue-based exclusion (B-collar) is derived ONLY from visible faults.
- Visible faults are masked pixel-exactly from prediction and evaluation.
- Score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel).
- 95% CI = spatial-block cluster bootstrap.

Evaluator version: WBGGEMSDOE1-HIDE-RECOVER-v1.0
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label

from . import metric as M

EVALUATOR_VERSION = "WBGGEMSDOE1-HIDE-RECOVER-v1.0"

COLLAR_PX = 15
FOLD_NAMES = ("NW", "NE", "SW", "SE")


def quadrant_ids(footprint: np.ndarray) -> np.ndarray:
    yy, xx = np.nonzero(footprint)
    ym, xm = int(np.median(yy)), int(np.median(xx))
    H, W = footprint.shape
    gy, gx = np.ogrid[:H, :W]
    q = np.full((H, W), -1, np.int8)
    q[(gy < ym) & (gx < xm) & footprint] = 0
    q[(gy < ym) & (gx >= xm) & footprint] = 1
    q[(gy >= ym) & (gx < xm) & footprint] = 2
    q[(gy >= ym) & (gx >= xm) & footprint] = 3
    return q


@dataclass
class Fold:
    name: str
    index: int
    visible: np.ndarray
    hidden: np.ndarray
    active: np.ndarray
    d_visible: np.ndarray
    n_hidden: int


@dataclass
class HoldoutContext:
    foot: np.ndarray
    labels: np.ndarray
    quad: np.ndarray
    folds: list[Fold]
    evaluator_version: str = EVALUATOR_VERSION


def build_context(foot: np.ndarray, labels: np.ndarray, collar_px: int = COLLAR_PX) -> HoldoutContext:
    foot = np.asarray(foot, bool)
    labels = np.asarray(labels, bool) & foot
    quad = quadrant_ids(foot)
    comp, n_comp = label(labels, structure=np.ones((3, 3), int))
    # assign each component to the quadrant containing most of its pixels
    comp_fold = np.full(n_comp + 1, -1, np.int8)
    for cid in range(1, n_comp + 1):
        pix = quad[comp == cid]
        if pix.size == 0:
            continue
        counts = np.bincount(pix[pix >= 0], minlength=4)
        comp_fold[cid] = int(np.argmax(counts))
    folds: list[Fold] = []
    for f in range(4):
        hidden = np.zeros_like(labels)
        for cid in np.where(comp_fold == f)[0]:
            hidden |= comp == cid
        visible = labels & ~hidden
        # collar around hidden so kernel cannot see visible faults
        hid_buf = binary_dilation(hidden, iterations=collar_px)
        vis_buf = binary_dilation(visible, iterations=collar_px)
        # drop hidden pixels that sit inside the visible collar (kernel bleed)
        hidden_eval = hidden & ~vis_buf
        d_visible = distance_transform_edt(~visible)
        active = foot & ~visible & ~(hid_buf & vis_buf)
        folds.append(
            Fold(
                name=FOLD_NAMES[f],
                index=f,
                visible=visible,
                hidden=hidden_eval,
                active=active,
                d_visible=d_visible,
                n_hidden=int(hidden_eval.sum()),
            )
        )
    return HoldoutContext(foot=foot, labels=labels, quad=quad, folds=folds)


def evaluate_mask(
    pred: np.ndarray,
    ctx: HoldoutContext,
    b_visible_px: float = 2.0,
    n_boot: int = 1000,
    seed: int = 20261026,
    name: str = "candidate",
) -> dict:
    """Pooled hide-and-recover DTI. Catalogue features/gates use visible faults only."""
    pred = np.asarray(pred, bool) & ctx.foot
    tp = fp = 0.0
    n_truth = 0
    per = {}
    # spatial blocks for CI (16 x 16)
    H, W = pred.shape
    grid_n = 16
    block_tp = np.zeros(grid_n * grid_n, np.float64)
    block_fp = np.zeros(grid_n * grid_n, np.float64)
    block_n = np.zeros(grid_n * grid_n, np.int32)

    for fold in ctx.folds:
        gate = fold.d_visible > float(b_visible_px)
        p = pred & fold.active & gate
        g = fold.hidden & fold.active
        n_t = int(g.sum())
        n_e = int(p.sum())
        if n_t == 0:
            rec = dict(dti=0.0, tp=0.0, fp=float(n_e), n_truth=0, emitted=n_e, coverage=0.0)
            per[fold.name] = rec
            continue
        if n_e == 0:
            rec = dict(dti=0.0, tp=0.0, fp=0.0, n_truth=n_t, emitted=0, coverage=0.0)
            per[fold.name] = rec
            n_truth += n_t
            yy, xx = np.nonzero(g)
            blk = np.minimum((yy * grid_n) // H, grid_n - 1) * grid_n + np.minimum((xx * grid_n) // W, grid_n - 1)
            np.add.at(block_n, blk, 1)
            continue
        dp = distance_transform_edt(~p)
        k_at_g = M.kernel(dp[g])
        tpf = float(k_at_g.sum())
        fnf = float(n_t) - tpf
        dg = distance_transform_edt(~g)
        fpf = float((1.0 - M.kernel(dg[p])).sum())
        dti = tpf / (tpf + M.ALPHA * fpf + M.BETA * fnf + M.EPS)
        per[fold.name] = dict(
            dti=float(dti), tp=tpf, fp=fpf, n_truth=n_t, emitted=n_e, coverage=float(tpf / n_t)
        )
        tp += tpf
        fp += fpf
        n_truth += n_t
        yy, xx = np.nonzero(g)
        blk_g = np.minimum((yy * grid_n) // H, grid_n - 1) * grid_n + np.minimum((xx * grid_n) // W, grid_n - 1)
        np.add.at(block_tp, blk_g, k_at_g)
        np.add.at(block_n, blk_g, 1)
        py, px = np.nonzero(p)
        blk_p = np.minimum((py * grid_n) // H, grid_n - 1) * grid_n + np.minimum((px * grid_n) // W, grid_n - 1)
        fp_pix = 1.0 - M.kernel(dg[p])
        np.add.at(block_fp, blk_p, fp_pix)

    fn = float(n_truth) - tp
    pooled = float(tp / (tp + M.ALPHA * fp + M.BETA * fn + M.EPS)) if n_truth else 0.0
    active = np.where(block_n > 0)[0]
    rng = np.random.default_rng(seed)
    if active.size == 0:
        ci = [0.0, 0.0]
    else:
        boots = []
        k = active.size
        for _ in range(n_boot):
            pick = active[rng.integers(0, k, size=k)]
            btp = float(block_tp[pick].sum())
            bfp = float(block_fp[pick].sum())
            bn = int(block_n[pick].sum())
            bfn = float(bn) - btp
            boots.append(btp / (btp + M.ALPHA * bfp + M.BETA * bfn + M.EPS))
        ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    return {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": ctx.evaluator_version,
        "name": name,
        "pooled_dti": pooled,
        "ci95": ci,
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "n_withheld_positives": int(n_truth),
        "b_visible_px": float(b_visible_px),
        "per_fold": per,
        "ci_method": f"cluster bootstrap over {int((block_n > 0).sum())} of 256 spatial tiles, {n_boot} reps",
    }


def paired_delta(a: dict, b: dict, label: str = "delta") -> dict:
    """Paired difference a - b of pooled DTI. CI is not a paired bootstrap here;
    we report the two CIs and the point delta. Callers should not treat this as
    a paired 95% CI unless they pass bootstrap samples."""
    d = float(a["pooled_dti"] - b["pooled_dti"])
    return {
        "evidence_class": "HOLDOUT-DTI",
        "name": label,
        "delta_point": d,
        "a_dti": a["pooled_dti"],
        "b_dti": b["pooled_dti"],
        "a_ci95": a["ci95"],
        "b_ci95": b["ci95"],
        "note": "point delta of two pooled HOLDOUT-DTI values; not a paired bootstrap CI",
    }
