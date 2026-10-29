#!/usr/bin/env python3
"""Leakage re-check for the blind-fault-adjacency lane (Experiment 1 of the session budget).

The original run card (docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-...run-card.json)
flags that its dots were placed from the FULL mapped catalogue, which includes the
faults the hide-and-recover holdout withholds. This script:

1. Reproduces the original HOLDOUT-DTI with the shared evaluator (gems1.holdout.evaluate_mask)
   on the archived raster, to confirm the evaluator path is unchanged.
2. Rebuilds the SAME placement method (scripts/generate_unique_submission.py: build_surface +
   place_dots) once per fold, using ONLY that fold's visible catalogue. Each fold's dots are
   scored with the shared evaluator on a single-fold context; pooled tp/fp/fn are summed
   exactly as the shared evaluator pools them.
3. Runs a single-feature leakage canary (AUC on the holdout) for the emission surface.

No new evaluator is written. Pooled DTI is re-derived from summed evaluator counts. The
spatial-tile bootstrap CI is NOT recomputed for the per-fold pooled number (the shared
evaluator's tile CI needs the full context); this is stated in the output.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems1.grid import read_template, read_labels  # noqa: E402
from gems1.holdout import build_context, evaluate_mask, HoldoutContext  # noqa: E402
from gems1 import metric as M  # noqa: E402

spec = importlib.util.spec_from_file_location("gen", ROOT / "scripts/generate_unique_submission.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

BRIDGE = ROOT / "data" / "bridge"
TEMPLATE = BRIDGE / "sample_submission.tif"
LABELS = BRIDGE / "existing_faults.tif"
ARCHIVED = ROOT / "docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif"
OUT = ROOT / "evidence/per_fold_recheck_blind_adjacency.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pooled(counts: list[dict]) -> float:
    tp = sum(c["tp"] for c in counts)
    fp = sum(c["fp"] for c in counts)
    fn = sum(c["fn"] for c in counts)
    return float(tp / (tp + M.ALPHA * fp + M.BETA * fn + M.EPS))


def main() -> int:
    _, footprint, _ = read_template(TEMPLATE)
    labels = read_labels(LABELS)
    footprint = np.asarray(footprint, bool)
    labels = np.asarray(labels, bool) & footprint
    ctx = build_context(footprint, labels, collar_px=15)

    # 1. Reproduce the archived leaky number with the shared evaluator.
    with rasterio.open(ARCHIVED) as ds:
        archived = ds.read(1) > 0
    leaky = evaluate_mask(archived, ctx, b_visible_px=2.0, n_boot=1000,
                          seed=20261026, name="archived-full-catalogue")

    # 2. Per-fold rebuild of the same method on visible-only catalogue.
    per_fold = []
    fold_counts = []
    fold_preds = {}
    for fold in ctx.folds:
        surface_f = gen.build_surface(fold.visible, footprint)
        dots_f = gen.place_dots(surface_f, footprint, fold.visible)
        fold_preds[fold.name] = (dots_f, surface_f)
        single = HoldoutContext(foot=ctx.foot, labels=ctx.labels, quad=ctx.quad, folds=[fold])
        r = evaluate_mask(dots_f, single, b_visible_px=2.0, n_boot=200,
                          seed=20261026, name=f"perfold-{fold.name}")
        fold_counts.append(dict(tp=r["tp"], fp=r["fp"], fn=r["fn"]))
        per_fold.append(dict(fold=fold.name, n_withheld_positives=r["n_withheld_positives"],
                             n_dots=int(dots_f.sum()), dti_single_fold=r["pooled_dti"],
                             tp=r["tp"], fp=r["fp"], fn=r["fn"]))

    pooled_perfold = pooled(fold_counts)

    # Sanity: summing per-fold counts for the leaky raster reproduces the shared pooled value.
    leaky_counts = []
    for fold in ctx.folds:
        single = HoldoutContext(foot=ctx.foot, labels=ctx.labels, quad=ctx.quad, folds=[fold])
        r = evaluate_mask(archived, single, b_visible_px=2.0, n_boot=1, name="sum-check")
        leaky_counts.append(dict(tp=r["tp"], fp=r["fp"], fn=r["fn"]))
    sum_check = pooled(leaky_counts)

    # 3. Single-feature leakage canary: emission surface alone, pooled over folds.
    feat, lab = [], []
    dist_feat, dist_lab = [], []
    for fold in ctx.folds:
        _, surface_f = fold_preds[fold.name]
        gate = fold.d_visible > 2.0
        m = fold.active & gate
        feat.append(surface_f[m].astype(np.float64))
        lab.append(fold.hidden[m].astype(np.int8))
        dist_feat.append(-fold.d_visible[m].astype(np.float64))
        dist_lab.append(fold.hidden[m].astype(np.int8))
    feat = np.concatenate(feat)
    lab = np.concatenate(lab)
    auc_surface = float(roc_auc_score(lab, feat)) if lab.min() != lab.max() else None
    auc_dist = float(roc_auc_score(np.concatenate(dist_lab), np.concatenate(dist_feat)))

    result = dict(
        schema="gemsdoe1-per-fold-recheck-v1",
        question="Does the blind-fault-adjacency DTI survive visible-only (per-fold) placement?",
        evaluator="gems1.holdout.evaluate_mask (shared, unchanged), EVALUATOR_VERSION WBGGEMSDOE1-HIDE-RECOVER-v1.0",
        archived_raster=str(ARCHIVED.relative_to(ROOT)),
        archived_raster_sha256=sha256(ARCHIVED),
        archived_full_catalogue=dict(
            evidence_class="HOLDOUT-DTI (leaky placement: full catalogue)",
            pooled_dti=leaky["pooled_dti"], ci95=leaky["ci95"],
            n_withheld_positives=leaky["n_withheld_positives"],
            original_run_card_value=0.46570455816360007),
        per_fold_visible_only=dict(
            evidence_class="HOLDOUT-DTI (visible-only placement, per fold)",
            pooled_dti=pooled_perfold,
            ci95="NOT RECOMPUTED (fold-level pooling; see per_fold list)",
            n_withheld_positives=int(sum(p["n_withheld_positives"] for p in per_fold)),
            folds=per_fold),
        sum_check_pooled_from_fold_counts_on_archived=sum_check,
        leakage_canary=dict(
            evidence_class="HOLDOUT-DTI canary (single feature)",
            auc_emission_surface_alone=auc_surface,
            auc_negative_visible_distance_alone=auc_dist,
            threshold=0.90,
            status="PASS" if max(auc_surface or 0, auc_dist) <= 0.90 else "FAIL (leakage until proven otherwise)"),
        verdict="NEGATIVE" if pooled_perfold <= 0.1661 else "CANDIDATE-FOR-REVIEW (beats 0.1661 same-evaluator benchmark on point estimate; CI missing)",
        benchmark="0.166060 HOLDOUT-DTI (GEMSDOE24 S3DEP1, per docs/executive-summary-20261028.md)",
        submission_slots_used=0,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("archived_full_catalogue", "per_fold_visible_only",
                                              "sum_check_pooled_from_fold_counts_on_archived",
                                              "leakage_canary", "verdict")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
