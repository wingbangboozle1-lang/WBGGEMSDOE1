#!/usr/bin/env python3
"""WBGGEMSDOE1 catalogue tip-continuation: holdout experiment, submission build, run card.

One preregistered experiment (E1, 2026-10-29) with the shared evaluator
``gems1.holdout`` (WBGGEMSDOE1-HIDE-RECOVER-v1.0) and metric ``gems1.metric``.

Evidence labels used in the output:
  HOLDOUT-DTI  = catalogue hide-and-recover with the shared evaluator (NOT the
                 organizer's hidden test set; it scores recovery of withheld
                 USGS/INGENIOUS segments).
  ORGANIZER-CONFIRMED = none exists for this file.

Outputs
  evidence/tip_continuation_20261029/holdout.json   fold-wise and null results
  evidence/tip_continuation_20261029/run_card.json  JSON run card
  docs/downloads/<name>-zeros.tif|.zip   all-finite zero exterior (top-submission convention)
  docs/downloads/<name>-nan.tif|.zip     NaN exterior (official-rules literal)
Usage:  /tmp/venv/bin/python scripts/run_tip_continuation_20261029.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems.submission import check_variants, write_submission, zip_single  # noqa: E402
from gems1 import holdout as H  # noqa: E402
from gems1.tip_continuation import generate_dots, random_null, GATE_PX  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
EVID = ROOT / "evidence/tip_continuation_20261029"
DOWN = ROOT / "docs/downloads"
NULL_SEEDS = 20
N_BOOT = 200


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC (no sklearn). Ties count 0.5."""
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    allv = np.concatenate([pos, neg])
    ranks = allv.argsort().argsort().astype(np.float64) + 1.0
    # average ranks for ties
    _, inv, counts = np.unique(allv, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    avg = sums / counts
    r = avg[inv]
    r_pos = r[: pos.size].sum()
    return float((r_pos - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    with rasterio.open(TEMPLATE) as s:
        samp = s.read(1)
    with rasterio.open(LABELS) as s:
        lab = s.read(1)
    foot = lab != -1
    if not np.array_equal(foot, np.isfinite(samp)):
        raise SystemExit("footprint mismatch between labels and sample grid")
    labels_fault = lab == 1
    ctx = H.build_context(foot, labels_fault)

    # ---- E1: per-fold, visible-only candidate ---------------------------------
    pred_by_fold, null_by_fold_seed, fold_rows = {}, {s: {} for s in range(NULL_SEEDS)}, []
    feat_pos, feat_neg = [], []
    for fold in ctx.folds:
        cand = generate_dots(fold.visible, foot)
        pred_by_fold[fold.index] = cand
        region = foot & fold.active & (fold.d_visible > GATE_PX)
        for s in range(NULL_SEEDS):
            rng = np.random.default_rng(1000 + s * 17 + fold.index)
            null_by_fold_seed[s][fold.index] = random_null(region, int(cand.sum()), rng)
        # leakage canary, feature alone: distance to VISIBLE faults, hidden truth vs active background
        act = fold.active & (fold.d_visible > GATE_PX)
        truth = fold.hidden & act
        feat_pos.append(fold.d_visible[truth])
        feat_neg.append(fold.d_visible[act & ~truth])
        fold_rows.append(
            {"fold": fold.name, "n_hidden_positives": int(fold.n_hidden), "candidate_dots": int(cand.sum())}
        )

    cand_res = H.evaluate_mask(None, ctx, b_visible_px=GATE_PX, n_boot=N_BOOT, name="tipcont-E1", pred_by_fold=pred_by_fold)
    null_dtis = []
    for s in range(NULL_SEEDS):
        r = H.evaluate_mask(None, ctx, b_visible_px=GATE_PX, n_boot=20, name=f"null-{s}", pred_by_fold=null_by_fold_seed[s])
        null_dtis.append(r["pooled_dti"])
    null_dtis = np.asarray(null_dtis)
    leak_auc = auc(np.concatenate(feat_pos), np.concatenate(feat_neg))

    # ---- full-catalogue candidate for the file --------------------------------
    full = generate_dots(labels_fault, foot)
    dig = hashlib.sha256(np.packbits(full).tobytes()).hexdigest()[:8]
    stem = f"wbggemsdoe1-tipcont-catalogue-strike-20261029-{dig}"
    tif_zero = DOWN / f"{stem}-zeros.tif"
    tif_nan = DOWN / f"{stem}-nan.tif"
    pred = full.astype(np.float32)
    write_submission(pred, TEMPLATE, tif_zero, outside="zero")
    write_submission(pred, TEMPLATE, tif_nan, outside="nan")
    zip_single(tif_zero)
    zip_single(tif_nan)
    chk_zero = check_variants(tif_zero, TEMPLATE)
    chk_nan = check_variants(tif_nan, TEMPLATE)

    p_hold = float(cand_res["pooled_dti"])
    null_lo, null_med, null_hi = np.percentile(null_dtis, [2.5, 50, 97.5]).tolist()
    beat_null = bool(p_hold > null_hi and cand_res["ci95"][0] > null_med)
    verdict = "promote-candidate" if beat_null and leak_auc <= 0.90 else "negative"

    holdout = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": ctx.evaluator_version,
        "withheld_positives": int(cand_res["n_withheld_positives"]),
        "pooled_dti": p_hold,
        "ci95": cand_res["ci95"],
        "per_fold": cand_res["per_fold"],
        "matched_random_null": {
            "seeds": NULL_SEEDS,
            "dti_min": float(null_dtis.min()),
            "dti_p2_5": float(null_lo),
            "dti_median": float(null_med),
            "dti_p97_5": float(null_hi),
            "dti_max": float(null_dtis.max()),
        },
        "leakage_canary": {"feature": "distance_to_visible_fault_px", "auc_hidden_vs_active": leak_auc, "threshold": 0.90, "pass": bool(leak_auc <= 0.90)},
        "fold_rows": fold_rows,
    }
    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / "holdout.json").write_text(json.dumps(holdout, indent=2, allow_nan=False) + "\n")

    note = (
        "WBG-8 catalogue strike-tip rays 200m-1.5km, >200m off catalogue; holdout-only; "
        "no organizer score; not approved"
    )
    card = {
        "run_card_version": "gems-run-card-v1",
        "date_utc": "2026-10-29",
        "experiment": "E1 catalogue tip-continuation vs matched random null",
        "hypothesis": "Unmapped strike-continuations of mapped fault traces lie along the strike of elongated traces beyond their mapped ends.",
        "mechanism": "Elongated catalogue traces (PCA eigenvalue ratio >=3, >=8 px) are extended outward from each end in 0.5 px steps from 2 px to 15 px, stopped at footprint edge or within 2 px of a visible fault; thinned to non-8-adjacent dots.",
        "named_non_fault_mimic": "Strike-parallel cultural or hydrological lineaments (roads, pipelines, canals, drainage, claim boundaries) and stratigraphic contacts that share the trace trend and end where the mapped fault ends.",
        "holdout": {k: holdout[k] for k in ("evidence_class", "evaluator_version", "withheld_positives", "pooled_dti", "ci95")},
        "matched_null": holdout["matched_random_null"],
        "leakage_canary_auc": leak_auc,
        "correlation_overlap_vs_registry": "see evidence/tip_continuation_20261029/uniqueness.json (produced by scripts/focus_inventory_20261029.py)",
        "raster_sha256": {"zeros_tif": sha256(tif_zero), "nan_tif": sha256(tif_nan)},
        "artifact": {"tif_sha256": sha256(tif_zero), "nan_tif_sha256": sha256(tif_nan), "name": stem},
        "decision": {
            "verdict": verdict,
            "ok_to_submit": False,
            "eligible_for_separate_selector": False,
            "approved_for_weekly_slot": False,
        },
        "registry": {"passes_literal_uniqueness": False, "rule": "70% 3 px overlap; rho 0.90"},
        "dots": int(full.sum()),
        "validator": {
            "zeros": {k: chk_zero["checks"][k]["pass"] for k in chk_zero["checks"]} if "checks" in chk_zero else chk_zero,
            "nan": {k: chk_nan["checks"][k]["pass"] for k in chk_nan["checks"]} if "checks" in chk_nan else chk_nan,
        },
        "submission_name": stem,
        "submission_note": note,
        "note_length": len(note),
        "verdict": verdict,
        "submit_recommendation": "NOT CLEARED. Holdout is catalogue-proxy only; no organizer receipt.",
    }
    (EVID / "run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False, default=str) + "\n")
    print(json.dumps({"dots": int(full.sum()), "pooled_dti": p_hold, "ci95": cand_res["ci95"], "null": holdout["matched_random_null"], "leak_auc": leak_auc, "verdict": verdict, "stem": stem}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
