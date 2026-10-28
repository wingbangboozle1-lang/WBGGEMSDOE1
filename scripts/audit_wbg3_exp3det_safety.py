#!/usr/bin/env python3
"""Recheck an already-placed EXP3DET TIFF against one registered STOP witness.

Forensic remeasurement only: no model fit, new dots, raster regeneration, slot
selection or upload. One literal duplicate is decisive; this is not a complete
registry audit or evidence that the two methods copied one another.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness  # noqa: E402
from validate_submission import check_tiff  # noqa: E402
from verify_wbg2_download import compare_audit  # noqa: E402

CARD = ROOT / "evidence/wbg3/run_card.json"
C1_CARD = ROOT / "registry/run_card.json"
TIF = ROOT / "docs/downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif"
EXPECTED = "30901f894a84f6150a65a86e6556d3b4d3b3f5054dd4f8f3b597d754115447c1"
C1 = ROOT / "docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif"
C1_SHA = "8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875"
OUT = ROOT / "evidence/wbg3/exp3det_safety_review_20261027.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit() -> dict:
    card = json.loads(CARD.read_text())
    c1_card = json.loads(C1_CARD.read_text())
    if (digest(TIF) != EXPECTED or card["raster_sha256"] != EXPECTED
            or digest(C1) != C1_SHA or c1_card["raster_sha256"] != C1_SHA):
        raise ValueError("EXP3DET or registered C1 witness hash changed")
    report = check_tiff(TIF)
    with zipfile.ZipFile(TIF.with_suffix(".zip")) as archive:
        names = archive.namelist()
        zip_ok = names == [TIF.name] and hashlib.sha256(archive.read(names[0])).hexdigest() == EXPECTED
    sample = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(sample) as dataset:
        footprint = np.isfinite(dataset.read(1))
        grid = (dataset.shape, dataset.crs, dataset.transform)
    refs = [{"file": str(C1), "repo": "WBGGEMSDOE1", "submission": "C1 continuous research surface", "sha256": C1_SHA}]
    result = uniqueness.compare_to_registry(TIF, refs, footprint, expected_grid=grid, include_reverse=False)
    if len(result["rows"]) != 1 or "error" in result["rows"][0]:
        raise ValueError("C1 witness comparison did not complete")
    witness = result["rows"][0]
    if (not report["all_checks_passed"] or not zip_ok or not witness["duplicate_by_overlap"]
            or not result["stop_required"] or card["decision"]["ok_to_submit"] is not False):
        raise ValueError("the expected exact-file negative or witness STOP did not reproduce")
    h = card["holdout"]
    return {
        "schema": "wbg3-exp3det-literal-safety-v1",
        "review_date_utc": "2026-10-27",
        "phase": "Final dots already existed; forensic remeasurement only. No surface-before-placement clearance is established.",
        "evidence_class": "REGISTRY-MEASUREMENT",
        "hypothesis": card["hypothesis"], "mechanism": card["mechanism"],
        "named_non_fault_mimic": card["named_non_fault_mimic"],
        "artifact": str(TIF.relative_to(ROOT)),
        "raster_sha256": EXPECTED,
        "existing_positive_pixels": report["emitted_positive_pixels"],
        "validator": {"local_format_passed": report["all_checks_passed"],
                      "mask_report": report["mask_report"],
                      "whole_array_min": report["min"], "whole_array_max": report["max"],
                      "n_nan": report["n_nan"], "n_infinite": report["n_infinite"],
                      "crs": report["meta"]["crs"], "shape": report["meta"]["shape"],
                      "transform": report["meta"]["transform"], "zip_single_member_identical": zip_ok},
        "witness": {key: witness[key] for key in ("repo", "submission", "sha256", "their_dots",
                    "my_dots_within_3px_of_theirs", "spearman_full_footprint", "duplicate_by_overlap", "duplicate_by_rho")},
        "scope": "One registered raster. One STOP is decisive; not a complete registry audit or proof of common geology or copying.",
        "holdout": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": h["evaluator_version"],
                    "dti": h["dti"], "ci95": h["ci95"], "withheld_positive_pixels": h["withheld_positive_pixels"],
                    "status": "Recorded parallel result; not rerun or independently confirmed in this review."},
        "leaderboard_estimate": None,
        "corrections": [
            "The old two-anchor model projection is withdrawn; it is not a measured leaderboard result.",
            "The nine-focus-site diagnostic is not a complete registry audit. The literal C1 witness exceeds the 70% stop threshold.",
            "The cause of the user's portal range error is unverified; all-finite output is only a local policy.",
        ],
        "submission_name": card["submission_name"], "submission_note": card["submission_note"],
        "verdict": "negative", "ok_to_submit": False, "eligible_for_separate_selector": False,
        "new_experiments": 0, "submission_slots_used": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.record:
        OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    else:
        differences = compare_audit(result, json.loads(OUT.read_text()))
        if differences:
            raise ValueError("EXP3DET safety receipt changed: " + "; ".join(differences[:10]))
    print(json.dumps({"verdict": result["verdict"], "ok_to_submit": False,
                      "c1_forward_overlap": result["witness"]["my_dots_within_3px_of_theirs"]}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, rasterio.errors.RasterioError) as error:
        print(json.dumps({"ok_to_submit": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
