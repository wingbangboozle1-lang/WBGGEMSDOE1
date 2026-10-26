#!/usr/bin/env python3
"""One preregistered H24-MTR1 experiment; shared hide-and-recover + writer.

No upload, no score projections, no private metric, no hyperparameter search.
Run cache_priority_registry.py and prepare_data.py first. A duplicate or canary
failure halts before packaging. A negative scientific result is still published.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import emission, footprint, holdout, magnetic_trough, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

BUDGET_FRACTION = 0.0073
RESULT = ROOT / "evidence/mtr1_experiment.json"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-recorded",
        action="store_true",
        help="Check immutable MTR1 evidence/files; do not run the stopped experiment",
    )
    parser.add_argument(
        "--run-gvc1",
        action="store_true",
        help="Execute the preregistered H24-GVC1 experiment via shared SegmentHoldout + writer",
    )
    parser.add_argument(
        "--verify-gvc1",
        action="store_true",
        help="Verify recorded H24-GVC1 experiment, C2ST receipt, Run Card, and GeoTIFFs",
    )
    parser.add_argument(
        "--verify-tnr1",
        action="store_true",
        help="Verify frozen TNR1 pooled holdout/components and exact TIFFs; never rerun",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("/tmp/gems_work"),
        help="Scratch directory outside tracked workspace for memmaps",
    )
    args = parser.parse_args()
    if args.verify_tnr1:
        from run_tnr1_lane import verify_recorded

        print(
            json.dumps(
                {"verified": True, "experiment_rerun": False, "run_card": verify_recorded()},
                indent=2,
                allow_nan=False,
            )
        )
        return
    if args.verify_recorded:
        from verify_mtr_receipt import verify

        print(json.dumps(verify(), indent=2, allow_nan=False))
        return
    if args.verify_gvc1:
        from run_gvc1_pipeline import verify_gvc1

        print(json.dumps(verify_gvc1(), indent=2, allow_nan=False))
        return
    if args.run_gvc1:
        from run_gvc1_pipeline import run_gvc1

        summary = run_gvc1(work_dir=args.work_dir)
        print(
            json.dumps(
                {
                    "submission_name": summary["submission_name"],
                    "holdout_dti": summary["holdout"]["dti"],
                    "ci95": summary["holdout"]["ci95"]["interval"],
                    "b0_dti": summary["baselines_same_evaluator"]["B0_oof_h24_ridge_dti"],
                    "b1_dti": summary["baselines_same_evaluator"]["B1_oof_base_submod_dti"],
                    "all_technical_gates_passed": summary["all_technical_gates_passed"],
                    "ok_to_download": summary["ok_to_download"],
                    "ok_to_submit": summary["ok_to_submit"],
                    "verdict": summary["verdict"],
                },
                indent=2,
                allow_nan=False,
            )
        )
        return
    if RESULT.exists():
        raise SystemExit(
            "Experiment already recorded and stopped. No implicit rerun/tuning; use --verify-recorded."
        )
    started = time.monotonic()
    fp = footprint.load_footprint()
    template = ROOT / "data/bridge/sample_submission.tif"
    meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    stack_path = ROOT / "data/prepared/features.npy"
    if sha256_file(stack_path) != meta["sha256"]:
        raise SystemExit("Prepared feature-stack checksum mismatch")
    stack = np.load(stack_path, mmap_mode="r")
    fp_ids = np.flatnonzero(fp)
    rtp = np.full(fp.shape, np.nan, np.float32)
    rtp.ravel()[fp_ids] = stack[:, meta["names"].index("rtp")]
    del stack
    ratio_path = ROOT / "data/external/geodawn_extensions_u8.tif"
    ratio_meta = json.loads(ratio_path.with_name("geodawn_extensions.json").read_text())
    if sha256_file(ratio_path) != ratio_meta["product_sha256"]:
        raise SystemExit("Contractor ratio-cache checksum mismatch")
    with rasterio.open(template) as t, rasterio.open(ratio_path) as s:
        if (s.shape, s.crs, s.transform) != (t.shape, t.crs, t.transform):
            raise SystemExit("Ratio grid mismatch")
        thk = s.read(1).astype(np.float32)
    with rasterio.open(ROOT / "data/bridge/labels.tif") as s:
        catalogue = (s.read(1) > 0) & fp
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    surfaces, support = magnetic_trough.build_surfaces(rtp, thk, fp)
    cache = ROOT / "data/prepared/mtr1"
    cache.mkdir(parents=True, exist_ok=True)
    for name, a in surfaces.items():
        np.save(cache / f"{name}.npy", a)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "H24-MTR1 paired magnetic trough with local Th/K depletion",
        "preregistration": "knowledge/09_preregistration_magnetic_trough_2026-10-25.md",
        "preregistration_commit": "3589290",
        "experiment_number": 1,
        "experiments_authorized": 1,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": "hash-pinned owner mirrors; not independently organizer-authenticated",
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (stack_path, ratio_path, template, ROOT / "data/bridge/labels.tif")
        },
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                Path(__file__),
                ROOT / "src/gems/holdout.py",
                ROOT / "src/gems/metric.py",
                ROOT / "src/gems/magnetic_trough.py",
                ROOT / "src/gems/emission.py",
                ROOT / "src/gems/novelty.py",
                ROOT / "src/gems/submission.py",
            )
        },
        "supported_pixels": int(support.sum()),
        "source_features": ["cached rtp", "cached contractor ThK"],
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "provisional: method paragraph absent from brief; promotion blocked",
    }
    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    report["fold_integrity"] = [
        {
            "name": f["name"],
            "withheld_positive_pixels": int(f["truth"].sum()),
            "hidden_whole_components": len(f["hidden_component_ids"]),
            "visible_fault_pixels": int(f["visible"].sum()),
            "train_validation_overlap": bool((f["train"] & f["valid"]).any()),
            "hidden_component_in_visible": bool(
                np.isin(context.components[f["visible"]], f["hidden_component_ids"]).any()
            ),
        }
        for f in context.folds
    ]
    # Test source channels AND every transformed descriptor before joint scoring.
    report["canary"] = context.canary(
        {
            "rtp_source": rtp,
            "ThK_source": thk,
            "valid_support": support.astype(float),
            "magnetic_trough": surfaces["magnetic_trough"],
            "ratio_depletion": surfaces["ratio_depletion"],
        }
    )
    save(report, RESULT)
    if not report["canary"]["passed"]:
        report.update(
            verdict="negative",
            stopped_reason="leakage-canary",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Leakage canary failed; no candidate packaged")
    print("Canaries passed", flush=True)
    # This runs BEFORE the first dot is placed. No registry values modify scores.
    report["surface_novelty"] = novelty.compare_registry(
        surfaces["candidate"], fp, registry["unique_rasters"], ROOT
    )
    save(report, RESULT)
    if not report["surface_novelty"]["passed"]:
        report.update(
            verdict="negative",
            stopped_reason="duplicate-surface",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Duplicate surface; lane stopped before placement")
    print("Surface registry check passed", flush=True)
    results = {}
    for arm in ("magnetic_trough", "candidate"):
        predictions = []
        for f in context.folds:
            # Neither support, normalization nor score reads the catalogue.
            # Only VISIBLE faults may be excluded at placement/evaluation.
            eligible = support & f["valid"] & ~f["visible"]
            predictions.append(
                emission.priority_poisson(
                    surfaces[arm], eligible, round(BUDGET_FRACTION * f["valid"].sum()), min_dist=3
                )
            )
        results[arm] = context.summarize(predictions)
        print(arm, "HOLDOUT-DTI", results[arm]["dti"], results[arm]["ci95"]["interval"], flush=True)
    report["results"] = results
    report["paired_gain_vs_magnetic_only"] = (
        results["candidate"]["dti"] - results["magnetic_trough"]["dti"]
    )
    # A historic precomputed TIFF cannot become an honest OOF comparator by masking
    # a hidden catalogue: its original training and full-catalogue mask remain.
    report["current_best_comparable_holdout_reconstructed"] = False
    report["current_best_gate"] = (
        "BLOCKED: original OOF reconstruction unavailable; historical rasters are comparison-only"
    )
    report["historical_holdout_numbers"] = (
        "Legacy evaluator, no compatible CI: not comparable and not promotion evidence"
    )
    # Final generation uses only the public visible catalogue, never a prior TIFF.
    final = emission.priority_poisson(
        surfaces["candidate"], support & ~catalogue, round(BUDGET_FRACTION * fp.sum()), min_dist=3
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")
    report["final_novelty"] = novelty.compare_registry(
        final.astype(np.float32), fp, registry["unique_rasters"], ROOT, dots=final
    )
    if not report["final_novelty"]["passed"]:
        report.update(
            verdict="negative",
            stopped_reason="duplicate-final-dots",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Duplicate final dots; lane stopped without packaging")
    content_id = submission.scored_content_id(final, fp, catalogue)
    name = submission.make_filename(
        "gems24", "mtr1-paired-magnetic-trough", "20261025", content_id, "zeros"
    )
    downloads = ROOT / "docs/downloads"
    zeros = submission.write_submission(final, template, downloads / name, outside="zero")
    nan_name = name.replace("-zeros.tif", "-nan.tif")
    nan = submission.write_submission(final, template, downloads / nan_name, outside="nan")
    checks = {
        "zero_outside": submission.check_variants(zeros, template),
        "nan_outside": submission.check_variants(nan, template),
    }
    if not all(c["format_valid"] for c in checks.values()):
        raise SystemExit("Exact-file format checks failed; do not publish")
    note = f"GEMS24 MTR1 | paired magnetic trough + local Th/K | independent pixels | research only; DO NOT SUBMIT | {content_id}"
    if len(note) > 140:
        raise AssertionError("Submission note exceeds the 140-character run-card limit")
    note_file = f"note-{name[:-4]}.txt"
    (downloads / note_file).write_text(note + "\n")
    checks_file = f"checks-{name[:-4]}.json"
    save(checks, downloads / checks_file)
    # Format success is NOT permission to upload. No human exception is requested.
    report.update(
        verdict="negative",
        verdict_reasons=[
            "No independent comparable current-best OOF baseline",
            "No explicit assigned lane paragraph",
            "Separate weekly-slot selector not run",
        ],
        pixel_count=int(final.sum()),
        filename=name,
        nan_filename=nan_name,
        raster_sha256=sha256_file(zeros),
        scored_content_id=content_id,
        scored_footprint_sha256=hashlib_footprint(final, fp),
        note=note,
        note_file=note_file,
        checks_file=checks_file,
        validator=checks,
        elapsed_seconds=time.monotonic() - started,
    )
    if report["paired_gain_vs_magnetic_only"] <= 0:
        report["verdict_reasons"].insert(
            0, "Radiometric corroboration did not beat the same-run magnetic-only ablation"
        )
    save(report, RESULT)
    card = {
        "hypothesis": report["hypothesis"],
        "mechanism": "Two-sided signed RTP trough, along-strike persistence, local contractor Th/K depletion; no terrain or old predictions",
        "non_fault_mimic": "Magnetite-poor alluvial paleochannel with K-rich detritus",
        "holdout": results["candidate"],
        "correlation_overlap_vs_registry": {
            "unique_registry_rasters": report["final_novelty"]["registry_unique_rasters"],
            "surface_max_abs_rank_correlation": report["surface_novelty"][
                "max_abs_rank_correlation"
            ],
            "final_max_abs_rank_correlation": report["final_novelty"]["max_abs_rank_correlation"],
            "final_max_overlap_within_3px": report["final_novelty"]["max_dot_overlap"],
            "passed": True,
            "scope": registry["scope"],
            "rank_sample_pixels": 200000,
        },
        "raster_sha256": report["raster_sha256"],
        "validator_output": checks["zero_outside"],
        "submission_name": name,
        "note": note,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "reasons": report["verdict_reasons"],
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
    }
    save(card, ROOT / "evidence/mtr1_run_card.json")
    save(card, ROOT / "docs/data/mtr1_run_card.json")
    download = {
        "file": name,
        "nan_file": nan_name,
        "sha256": report["raster_sha256"],
        "content_id": content_id,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "role": "primary",
        "format_valid": True,
        "ok_to_download": True,
        "ok_to_submit": False,
        "recommended_for_new_slot": False,
        "slot_recommendation": "not_recommended",
        "verdict": "negative",
        "live_dti": None,
        "run_card": "mtr1_run_card.json",
    }
    save(download, ROOT / "docs/data/independent_download.json")
    print(
        json.dumps(
            {
                "file": name,
                "pixels": int(final.sum()),
                "sha256": report["raster_sha256"],
                "note_characters": len(note),
                "verdict": "negative",
                "ok_to_submit": False,
            },
            indent=2,
        ),
        flush=True,
    )


def hashlib_footprint(final, fp):
    import hashlib

    return hashlib.sha256(np.asarray(final[fp], dtype="<f4").tobytes()).hexdigest()


if __name__ == "__main__":
    main()
