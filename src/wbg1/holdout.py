"""Hide-and-recover holdout context + instruments.

Evaluator id: WBG1-HIDE-RECOVER-v1.0
  * whole fault segments (8-connected components of labels.tif) assigned to one
    of K=5 horizontal strips by centroid row;
  * 5 px (500 m) boundary buffer: labels inside the buffer belong to neither
    visible nor withheld sets (train buffer);
  * withheld truth = strip-k labels minus pixels within 15 px (1.5 km collar)
    of any visible label (kills trivial boundary continuation);
  * every catalogue-based feature (flank exclusion, dist-to-fault) is derived
    ONLY from the visible labels of that fold; label-free transforms are
    fold-independent (documented, not re-derived per fold);
  * visible faults masked pixel-exactly from predictions before scoring;
  * pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel) + 256-block
    spatial cluster-bootstrap 95% CI.

Second instrument WBG1-SGMC-CAL-v1.0: off-catalogue USGS SGMC faults
(>300 m / 3 px from labels.tif) as independent truth proxy, predictions
masked of labels pixel-exactly, same pooled DTI + CI.

Leakage canary: two-sided AUC of each feature alone vs labels[foot];
> 0.90 means leakage until proven otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt, label as cc_label

from . import metric
from .paths import data_dir

EVAL_HIDE = "WBG1-HIDE-RECOVER-v1.0"
EVAL_SGMC = "WBG1-SGMC-CAL-v1.0"
N_FOLDS = 5
BUFFER_PX = 5
COLLAR_PX = 15
SGMC_GAP_PX = 3


@dataclass
class Fold:
    visible: np.ndarray
    withheld: np.ndarray
    n_withheld: int


@dataclass
class HoldoutContext:
    foot: np.ndarray
    labels: np.ndarray
    sgmc_offcat: np.ndarray
    template_path: str
    template_meta: dict
    folds: list[Fold] = field(default_factory=list)

    @property
    def n_withheld_total(self) -> int:
        return int(sum(f.n_withheld for f in self.folds))


def _read_first(path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as s:
        a = s.read(1)
        meta = {
            "shape": tuple(s.shape),
            "crs": str(s.crs),
            "transform": tuple(s.transform),
            "dtype": str(s.dtypes[0]),
            "nodata": s.nodata,
            "path": str(path),
        }
    return a, meta


def load_holdout_context(ddir=None) -> HoldoutContext:
    ddir = data_dir() if ddir is None else ddir
    import pathlib

    ddir = pathlib.Path(ddir)
    sample, sample_meta = _read_first(ddir / "sample_submission.tif")
    foot = np.isfinite(sample).astype(bool)
    del sample
    lab_raw, _ = _read_first(ddir / "labels.tif")
    labels = (lab_raw == 1) & foot
    del lab_raw
    sgmc_raw, _ = _read_first(ddir / "external" / "derived_sgmc_faults_100m_u8.tif")
    sgmc = (np.asarray(sgmc_raw) > 0) & foot
    del sgmc_raw
    d_lab = distance_transform_edt(~labels)
    sgmc_offcat = sgmc & (d_lab > SGMC_GAP_PX) & foot

    folds = _build_folds(labels, foot)
    return HoldoutContext(
        foot=foot,
        labels=labels,
        sgmc_offcat=sgmc_offcat,
        template_path=str(ddir / "sample_submission.tif"),
        template_meta=sample_meta,
        folds=folds,
    )


def _build_folds(labels: np.ndarray, foot: np.ndarray) -> list[Fold]:
    h, w = labels.shape
    comp, n_comp = cc_label(labels, structure=np.ones((3, 3), dtype=int))
    # component id -> centroid row
    comp_rows = np.zeros(n_comp + 1, dtype=np.float64)
    comp_count = np.zeros(n_comp + 1, dtype=np.int64)
    ys, xs = np.nonzero(labels)
    ids = comp[ys, xs]
    np.add.at(comp_rows, ids, ys.astype(np.float64))
    np.add.at(comp_count, ids, 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        centroid = comp_rows / np.maximum(comp_count, 1)
    strip_of = np.minimum((centroid / h * N_FOLDS).astype(int), N_FOLDS - 1)
    strip_of[0] = -1
    # strip boundaries with buffer zones
    edges = [int(round(h * k / N_FOLDS)) for k in range(N_FOLDS + 1)]
    in_buffer = np.zeros(h, dtype=bool)
    for k in range(1, N_FOLDS):
        lo = max(0, edges[k] - BUFFER_PX)
        hi = min(h, edges[k] + BUFFER_PX)
        in_buffer[lo:hi] = True
    comp_strip = strip_of[comp]  # per-pixel strip of its component
    buf2d = np.broadcast_to(in_buffer[:, None], labels.shape)
    folds: list[Fold] = []
    one = np.ones((3, 3), dtype=bool)
    for k in range(N_FOLDS):
        withheld_raw = labels & (comp_strip == k) & ~buf2d
        visible = labels & (comp_strip != k) & ~buf2d
        # 1.5 km collar: drop withheld pixels near visible labels
        if visible.any():
            d_vis = distance_transform_edt(~visible)
            withheld = withheld_raw & (d_vis > COLLAR_PX)
        else:
            withheld = withheld_raw
        folds.append(
            Fold(
                visible=np.ascontiguousarray(visible),
                withheld=np.ascontiguousarray(withheld),
                n_withheld=int(withheld.sum()),
            )
        )
    return folds


def evaluate_hide_and_recover(
    mask: np.ndarray,
    ctx: HoldoutContext,
    flank_exclude_px: float = 0.0,
    n_rep: int = 2000,
    seed: int = 0,
) -> dict:
    """Score a full-grid boolean emission on the strip hide-and-recover folds.

    Per fold: predictions masked of visible labels pixel-exactly; if
    flank_exclude_px > 0, predictions within that distance of VISIBLE labels
    are additionally dropped (mirrors the B-flank emission rule, derived from
    visible faults only). Truth = withheld.
    """
    mask = np.asarray(mask, dtype=bool) & ctx.foot
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for f in ctx.folds:
        pred = mask & ~f.visible
        if flank_exclude_px > 0 and f.visible.any():
            d_vis = distance_transform_edt(~f.visible)
            pred = pred & (d_vis >= flank_exclude_px)
        pairs.append((pred, f.withheld))
    pooled = metric.pooled_with_ci(pairs, ctx.foot, n_rep=n_rep, seed=seed)
    return {
        "evaluator": EVAL_HIDE,
        "n_folds": N_FOLDS,
        "n_withheld_total": ctx.n_withheld_total,
        "emitted_px": int(mask.sum()),
        "flank_exclude_px": flank_exclude_px,
        **pooled,
    }


def evaluate_sgmc(
    mask: np.ndarray,
    ctx: HoldoutContext,
    n_rep: int = 2000,
    seed: int = 0,
) -> dict:
    """Score a full-grid boolean emission vs off-catalogue SGMC faults."""
    mask = np.asarray(mask, dtype=bool) & ctx.foot
    pred = mask & ~ctx.labels  # pixel-exact catalogue masking
    pooled = metric.pooled_with_ci([(pred, ctx.sgmc_offcat)], ctx.foot, n_rep=n_rep, seed=seed)
    return {
        "evaluator": EVAL_SGMC,
        "n_truth": int(ctx.sgmc_offcat.sum()),
        "emitted_px": int(mask.sum()),
        "on_catalogue_px": int((mask & ctx.labels).sum()),
        **pooled,
    }


def canary_auc(feature: np.ndarray, ctx: HoldoutContext) -> dict:
    """Two-sided AUC of one feature alone vs catalogue labels (in footprint)."""
    from sklearn.metrics import roc_auc_score

    x = np.asarray(feature, dtype=np.float64)[ctx.foot]
    y = ctx.labels[ctx.foot].astype(int)
    ok = np.isfinite(x)
    auc = float(roc_auc_score(y[ok], x[ok]))
    two_sided = max(auc, 1.0 - auc)
    return {"auc": auc, "auc_two_sided": two_sided, "leak": bool(two_sided > 0.90)}


def read_binary_tif(path) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float64)
    return np.nan_to_num(a, nan=0.0) > 0.5
