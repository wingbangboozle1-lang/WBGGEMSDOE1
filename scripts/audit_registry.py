#!/usr/bin/env python3
"""Apply the unchanged literal shared gate to the unplaced research surface.

The audit may continue inventory diagnostics after the first STOP, but no model
experiment, retuning, final dot placement or upload is permitted after that STOP.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
import numpy as np
import rasterio
from gems57 import uniqueness
from wbggems.audit import dump_json, promotion_decision, sha256, utc_now


def stopped_ledger(ledger, first_stop, verified_utc):
    """Diagnostic rechecks must never move the original scientific STOP time."""
    result = dict(ledger)
    result.update(status="negative_stopped",
        stop_utc=first_stop["recorded_utc"] if first_stop else ledger.get("stop_utc", verified_utc),
        last_registry_verification_utc=verified_utc,
        stop_reason="negative paired efficacy and literal surface registry duplicate; no final dot placement")
    return result


def main():
    exp = json.loads((ROOT / "evidence/experiment.json").read_text())
    surface_path = ROOT / exp["surface_file"]
    receipt = json.loads(surface_path.with_suffix(".json").read_text())
    if sha256(surface_path) != exp["surface_sha256"] or receipt["sha256"] != exp["surface_sha256"]:
        raise ValueError("research surface hash differs from the measured experiment")
    with rasterio.open(ROOT / "data/sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
        ref = (src.shape, src.crs, src.transform)
    index = json.loads((ROOT / "registry/focus_inventory.json").read_text())
    # The shared helper's own ROOT is inside vendor/. Resolve portable stored
    # cache paths here; do not alter/fork the shared helper for local layout.
    for row in index["rasters"]:
        path = Path(row["cache_file"])
        if not path.is_absolute():
            row["cache_file"] = str(ROOT / path)
    first_stop_path = ROOT / "evidence/first_registry_stop.json"
    first_stop = [json.loads(first_stop_path.read_text())] if first_stop_path.exists() else []
    # Older diagnostics disabled reverse overlap; their shared helper returned
    # a zero placeholder. Preserve the original STOP time but do not present
    # that placeholder as a measured reverse overlap.
    if first_stop and first_stop[0].get("reverse_overlap_evaluated") is not True:
        first_stop[0]["row"].pop("their_dots_within_3px_of_mine", None)
        first_stop[0]["reverse_overlap_evaluated"] = False
        dump_json(first_stop_path, first_stop[0])
    def progress(done, total, row):
        if not first_stop and (row.get("duplicate_by_rho") or row.get("duplicate_by_overlap") or "error" in row):
            event = {"recorded_utc": utc_now(), "phase": "surface-before-placement", "row": row,
                     "candidate_sha256": exp["surface_sha256"], "reverse_overlap_evaluated": True,
                     "action": "STOP: no further geological experiments, no final dot placement, no retuning or upload. Inventory diagnostics only may finish."}
            first_stop.append(event)
            dump_json(ROOT / "evidence/first_registry_stop.json", event)
            print("Literal registry STOP:", row.get("submission"), flush=True)
        if done % 30 == 0 or done == total:
            print(f"Registry diagnostics {done}/{total}", flush=True)
    report = uniqueness.compare_to_registry(surface_path, index, footprint, expected_grid=ref,
                                           include_reverse=True, progress=progress)
    report.update(generated_utc=utc_now(), phase="surface-before-placement",
                  scope=index["scope"], final_dot_check="NOT RUN: placement prohibited by the surface STOP and negative efficacy screen",
                  no_density_exemption=True, first_stop=first_stop[0] if first_stop else None,
                  complete_all_user_listed_sites=False,
                  note="A complete nine-snapshot accessible scan is not a complete competition or 92-site registry. Same-shape aligned archived surfaces are not exempted.")
    dump_json(ROOT / "evidence/registry_surface_audit.json", report)
    # A witnessed broad-coverage prior is enough to falsify clearance. It is
    # not evidence of geological method identity, nor permission to evade it.
    witness_path = ROOT / ".cache/research/GEMSDOE24/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
    certificate = uniqueness.saturation_certificate(witness_path, footprint, expected_grid=ref)
    certificate["generated_utc"] = utc_now()
    certificate["interpretation_warning"] = "Near saturation is a protocol obstruction, not proof of common geological reasoning. No density/lattice exemption was authorized."
    dump_json(ROOT / "evidence/lattice_coverage_certificate.json", certificate)
    canary = json.loads((ROOT / "evidence/feature_canaries.json").read_text())
    candidate_key = "candidate_19band_plus_commutator_hgb"
    control_key = "control_19band_hgb"
    delta = exp["summary"]["paired_differences"][control_key]
    decision = promotion_decision(
        format_ok=receipt["validator"]["all_checks_passed"], novelty_ok=report["unique"] and report["complete_all_user_listed_sites"],
        canary_ok=not canary["leakage_suspected"], paired_ci95=delta["ci95"],
        same_instrument_best_beaten=False, authorized_lane=False,
        organizer_slot_receipt=None, confirmation_passed=False)
    card = {
        "generated_utc": utc_now(), "hypothesis": "WBG-C1: conductance-depth curvature non-coaxiality",
        "mechanism": "Scale-normalized Hessian commutator at 300/800 m, curvature strength, cross-scale persistence and dilatation support; 19-band spatial OOF HGB plus four new channels.",
        "non_fault_mimic": "Oblique saline-clay basin-fill/lithologic contacts or shared inversion/interpolation artifacts.",
        "lane": "provisional research only; no assigned single-method paragraph supplied",
        "holdout": exp["summary"]["scores"][candidate_key],
        "control_holdout": exp["summary"]["scores"][control_key],
        "paired_delta_holdout": delta,
        "holdout_instrument": {"evaluator_version": exp["evaluator_version"], "split": "buffered-whole-components-loqo-v2", "seed": 71614,
                               "representation": "continuous unplaced OOF confidence surface", "physical_bootstrap_clusters": exp["summary"]["bootstrap"]["clusters"]},
        "leaderboard_estimate": None, "organizer_confirmed_submission_score": None,
        "leakage_canary": {"all_23_features_tested_alone_in_4_folds": True,
                           "maximum_orientation_invariant_auc": canary["maximum_orientation_invariant_auc"],
                           "suspected_leakage": canary["leakage_suspected"]},
        "registry": {"phase": "surface-before-placement", "checked_unique_file_hashes": report["registry_rasters_checked"],
                     "source_paths": index["files_indexed"], "scope": index["scope"],
                     "max_spearman_rho": report["worst_spearman_full_footprint"],
                     "max_forward_3px_overlap": report["worst_dot_overlap"],
                     "byte_unique_among_checked": report["byte_unique_among_checked"],
                     "decoded_pixel_unique_among_checked": report["pixel_unique_among_checked"],
                     "passes_literal_uniqueness": report["unique"], "complete_all_user_listed_sites": False,
                     "final_dots": "NOT GENERATED: surface duplicate STOP; no final-dot clearance claimed"},
        "raster_sha256": receipt["sha256"], "raster_decoded_sha256": exp["surface_decoded_sha256"],
        "validator": {"all_checks_passed": receipt["validator"]["all_checks_passed"],
                      "no_nan_inside_footprint": receipt["validator"]["checks"]["in_footprint_all_finite"],
                      "values_in_0_1": receipt["validator"]["checks"]["in_footprint_range_0_1"],
                      "single_band_float32": receipt["validator"]["checks"]["single_band"] and receipt["validator"]["checks"]["dtype_float32"],
                      "crs_shape_transform_match": receipt["template_report"]["ok"],
                      "range_min": receipt["validator"]["min"], "range_max": receipt["validator"]["max"],
                      "outside_footprint_zero": receipt["validator"]["checks"]["outside_footprint_zero"],
                      "known_fault_support_zero": receipt["validator"]["checks"]["zero_dots_on_mapped_catalogue"]},
        "submission_name": receipt["submission_name"], "submission_note": receipt["note"],
        "artifact": exp["surface_file"], "artifact_role": "newly generated research-surface TIFF; not a final dotted or promoted competition submission",
        "verdict": decision["verdict"], "decision": decision,
        "experiments_completed": 1, "submission_slots_used": 0,
        "next_action": "Keep this negative result. Do not tune around registry holes or copy the historical champion. A separate authorized lane/selector and new untouched confirmation are required before further promotion research."
    }
    dump_json(ROOT / "registry/run_card.json", card)
    dump_json(ROOT / "docs/data/run-card.json", card)
    ledger_path = ROOT / "registry/experiment_ledger.json"
    ledger = json.loads(ledger_path.read_text())
    ledger = stopped_ledger(ledger, first_stop[0] if first_stop else None, report["generated_utc"])
    dump_json(ledger_path, ledger)
    print(json.dumps({"verdict": card["verdict"], "novelty": card["registry"], "download": card["artifact"]}, indent=2))


if __name__ == "__main__":
    main()
