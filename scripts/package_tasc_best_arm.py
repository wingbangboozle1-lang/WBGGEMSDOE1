#!/usr/bin/env python3
"""Package the best-scoring preregistered TASC arm as a separate research TIFF.

This is NOT a new experiment, tuning step or promotion. All three arms were scored
once in ``scripts/run_tasc_lane.py --execute``. Arm A (label-free geophysical response)
had the highest HOLDOUT-DTI of the three; this script simply re-emits that frozen
surface on the full footprint, validates the exact bytes, checks novelty and records
a secondary card. Post-hoc best-arm selection is explicitly NOT a promotion gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("WBG_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data" / "raw"))
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np
import rasterio

from gems import emission, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402
from run_tasc_lane import (  # noqa: E402
    CACHE, DOCS_DATA, DOWNLOADS, EVIDENCE, LABELS, PREREG, REGISTRY, TEMPLATE,
    load_grid, lli_projection, save, utc,
)

FEATURE_RECEIPT = EVIDENCE / "tasc_features_20261027.json"
EXPERIMENT_RECEIPT = EVIDENCE / "tasc_experiment_20261027.json"
SURFACE_NOVELTY = EVIDENCE / "tasc_surface_novelty_20261027.json"
RUN_CARD = EVIDENCE / "tasc_best_arm_run_card_20261027.json"
DOCS_CARD = DOCS_DATA / "run-card-tasc-best-arm-20261027.json"


def main() -> dict:
    if RUN_CARD.exists():
        raise SystemExit("best-arm card already frozen")
    prereg = json.loads(PREREG.read_text())
    features = json.loads(FEATURE_RECEIPT.read_text())
    experiment = json.loads(EXPERIMENT_RECEIPT.read_text())
    surface_novelty = json.loads(SURFACE_NOVELTY.read_text())
    registry = json.loads(REGISTRY.read_text())
    footprint, catalogue = load_grid(prereg)
    surface_path = ROOT / features["feature_arrays"]["A"]["path"]
    if sha256_file(surface_path) != features["feature_arrays"]["A"]["sha256"]:
        raise ValueError("frozen Arm A surface changed")
    surface = np.load(surface_path, mmap_mode="r")
    if not surface_novelty["A"]["passed"]:
        raise RuntimeError("Arm A surface novelty gate did not pass")

    budget_frac = prereg["fixed_constants"]["dot_budget_fraction"]
    spacing = prereg["fixed_constants"]["min_dot_spacing_px"]
    final = emission.priority_poisson(
        surface, footprint & ~catalogue & (surface > 0),
        round(budget_frac * int(footprint.sum())), min_dist=spacing
    )
    content_id = submission.scored_content_id(final.astype(np.float32), footprint, catalogue)
    name = f"wbggemsdoe1-tasc-label-free-physical-response-20261027-{content_id}-zeros.tif"
    artifact = DOWNLOADS / name
    submission.write_submission(final.astype(np.float32), TEMPLATE, artifact, outside="zero")
    zip_path = submission.zip_single(artifact)
    checks = submission.check_variants(artifact, TEMPLATE)
    if not checks["format_valid"] or not checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]:
        raise RuntimeError("exact-file format validation failed")
    note = (f"TASC Arm A label-free physical response | best arm of frozen screen | "
            f"DO NOT SUBMIT | id {content_id}")
    if len(note) > 140:
        raise ValueError("submission note exceeds 140 characters")

    final_novelty = novelty.compare_registry(
        final.astype(np.float32), footprint, registry["entries"], ROOT, dots=final,
        separate_calibration_controls=True,
    )
    save(EVIDENCE / "tasc_best_arm_final_novelty_20261027.json", final_novelty)
    literal_pass = bool(final_novelty["rows"]) and not any(
        r["literal_duplicate"] for r in final_novelty["rows"]
    )
    decoded = hashlib.sha256(np.ascontiguousarray(
        np.asarray(final[footprint], dtype="<f4")).tobytes()).hexdigest()
    projected = lli_projection(artifact, footprint, catalogue)
    arm = experiment["arms"]["A"]

    card = {
        "schema": "gemsdoe1-tasc-best-arm-card-v1",
        "generated_utc": utc(),
        "hypothesis": "Arm A control of the TASC lane: label-free multiscale geophysical edge/strain response.",
        "mechanism": ("300 m Gaussian gradient response of geodetic shear/dilatation, gravity, magnetic "
                      "and basement-depth fields; no catalogue geometry, prior prediction or registry raster."),
        "named_non_fault_mimic": "Lithologic/volcanic contact, flight-line leveling seam, basin-fill edge.",
        "lane": "preregistered control inside the provisional TASC research lane",
        "selection_status": "post-hoc best of three frozen arms; NOT a promotion gate",
        "preregistration": str(PREREG.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": arm["evaluator_version"],
            "dti": arm["dti"],
            "ci95": arm["ci95"]["interval"],
            "withheld_positive_pixels": arm["n_withheld_positive_pixels"],
            "representation": "binary 0/1 dots, 3 px minimum spacing, 0.73% fold budget",
            "tpw": arm["TP_w"], "fpw": arm["FP_w"], "fnw": arm["FN_w"],
        },
        "frozen_baseline_point_dti": prereg["gates"]["baseline_holdout_dti_point"],
        "beats_frozen_baseline_point": bool(arm["dti"] > prereg["gates"]["baseline_holdout_dti_point"]),
        "leaderboard_estimate": {
            "label": projected["label"],
            "projected_value": projected["projected_value"],
            "approx_interval_pm_1mae": projected["approx_interval_pm_1mae"],
            "evidence_class": "LLI-PROJECTION; USER-REPORTED calibration; NOT an organizer score",
            "organizer_confirmed_submission_score": None,
        },
        "correlation_overlap_vs_registry": {
            "surface_passed": surface_novelty["A"]["passed"],
            "surface_max_abs_rank_correlation": surface_novelty["A"]["max_abs_rank_correlation"],
            "final_dots_literal_unseparated_passed": literal_pass,
            "final_dots_competing_method_passed": final_novelty["competing_method_passed"],
            "competing_method_rasters": final_novelty["competing_method_rasters"],
            "calibration_control_rasters": final_novelty["calibration_control_rasters"],
            "max_abs_rank_correlation": final_novelty["max_abs_rank_correlation"],
            "max_literal_dot_overlap_within_3px": final_novelty["max_dot_overlap"],
            "max_competing_dot_overlap_within_3px": final_novelty["max_competing_dot_overlap"],
            "calibration_control_summary": final_novelty["calibration_control_summary"],
            "rank_limit": 0.90, "overlap_limit": 0.70,
            "decoded_pixel_sha256_unique_among_checked": bool(
                decoded not in {r["footprint_sha256"] for r in registry["entries"]}
            ),
            "decoded_pixel_sha256": decoded,
            "scope": registry["scope"],
        },
        "raster_sha256": sha256_file(artifact),
        "zip_sha256": sha256_file(zip_path),
        "decoded_pixel_sha256": decoded,
        "validator_output": checks,
        "submission_name": name,
        "submission_note": note,
        "submission_note_characters": len(note),
        "final_dot_count": int(final.sum()),
        "final_budget": int(round(budget_frac * int(footprint.sum()))),
        "artifact": str(artifact.relative_to(ROOT)),
        "zip_artifact": str(zip_path.relative_to(ROOT)),
        "artifact_role": "best-scoring newly generated unique research TIFF from the 2026-10-27 frozen screen",
        "decision": {
            "verdict": "negative",
            "ok_to_download": True,
            "ok_to_submit": False,
            "eligible_for_separate_selector": False,
            "approved_for_weekly_slot": False,
            "submission_slots_used": 0,
            "reasons": [
                "HOLDOUT-DTI 0.061528 is below the frozen 0.166060 current-best point estimate",
                "literal all-entry 3 px overlap gate fails against the retained spacing-5 calibration lattice",
                "best-arm selection is post-hoc and is not a promotion test",
                "no assigned method lane, authenticated weekly allowance or organizer receipt exists",
            ],
        },
        "verdict": "negative",
        "submission_slots_used": 0,
    }
    save(RUN_CARD, card)
    save(DOCS_CARD, card)
    print(json.dumps({"submission_name": name, "holdout_dti": arm["dti"],
                      "lli_projection": projected["projected_value"],
                      "literal_pass": literal_pass,
                      "competing_pass": final_novelty["competing_method_passed"],
                      "ok_to_submit": False}, indent=2))
    return card


if __name__ == "__main__":
    main()
