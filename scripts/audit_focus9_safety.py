#!/usr/bin/env python3
"""Recheck the existing Focus-9 random null; never place dots or select a slot."""
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

CARD = ROOT / "evidence/focus9_exec/run_card.json"
C1_CARD = ROOT / "registry/run_card.json"
TIF = ROOT / "docs/downloads/wbggemsdoe1-focus9-exec-20261027-unique-36k-zeros.tif"
EXPECTED = "e8c4bf7607cec72c54981b90aa60e7e85163b429b58ebd6f2a7c3126e8c1e351"
C1 = ROOT / "docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif"
C1_SHA = "8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875"
INVENTORY = ROOT / "registry/focus_files.json"
DECODED_AUDIT = ROOT / "evidence/registry_surface_audit.json"
OUT = ROOT / "evidence/focus9_exec/safety_review_20261028.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit() -> dict:
    card = json.loads(CARD.read_text())
    c1_card = json.loads(C1_CARD.read_text())
    if (digest(TIF) != EXPECTED or card["raster_sha256"] != EXPECTED
            or digest(C1) != C1_SHA or c1_card["raster_sha256"] != C1_SHA):
        raise ValueError("Focus-9 or registered C1 witness hash changed")
    report = check_tiff(TIF)
    with zipfile.ZipFile(TIF.with_suffix(".zip")) as archive:
        names = archive.namelist()
        zip_ok = names == [TIF.name] and hashlib.sha256(archive.read(names[0])).hexdigest() == EXPECTED
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as dataset:
        footprint = np.isfinite(dataset.read(1))
        grid = (dataset.shape, dataset.crs, dataset.transform)
    refs = [{"file": str(C1), "repo": "WBGGEMSDOE1", "submission": "C1 continuous research surface", "sha256": C1_SHA}]
    result = uniqueness.compare_to_registry(TIF, refs, footprint, expected_grid=grid, include_reverse=False)
    if len(result["rows"]) != 1 or "error" in result["rows"][0]:
        raise ValueError("C1 witness comparison did not complete")
    witness = result["rows"][0]
    if (not report["all_checks_passed"] or not zip_ok or not witness["duplicate_by_overlap"]
            or not result["stop_required"] or card["decision"]["ok_to_submit"] is not False
            or card["holdout_dti"]["dti"] is not None):
        raise ValueError("the expected exact-file negative or witness STOP did not reproduce")

    inventory = json.loads(INVENTORY.read_text())["files"]
    prior = json.loads(DECODED_AUDIT.read_text())
    rows = prior["rows"]
    if (len(inventory) != 377 or len(rows) != 360 or not prior["complete_accessible_scan"]
            or any(not row.get("sha256") or not row.get("decoded_sha256") for row in rows)):
        raise ValueError("historical hash inventory incomplete or changed")
    file_matches = sum(row["sha256"] == EXPECTED for row in inventory)
    decoded = result["candidate_decoded_sha256"]
    pixel_matches = sum(row["decoded_sha256"] == decoded for row in rows)
    if file_matches or pixel_matches:
        raise ValueError("Focus-9 identical-byte or decoded-pixel historical inventory match")
    return {
        "schema": "focus9-random-null-literal-safety-v1",
        "review_date_utc": "2026-10-28",
        "phase": "Existing final dots; forensic remeasurement only, no evidence of required pre-placement clearance.",
        "hypothesis": "A synthetic uniform-random null for download and local-format testing, not a geological discovery model.",
        "mechanism": "36,800 off-catalogue random dots; no geophysical features, learning or holdout evaluation.",
        "named_non_fault_mimic": card["named_non_fault_mimic"],
        "artifact": str(TIF.relative_to(ROOT)), "raster_sha256": EXPECTED,
        "candidate_decoded_sha256": decoded,
        "existing_positive_pixels": report["emitted_positive_pixels"],
        "validator": {"local_format_passed": report["all_checks_passed"],
                      "mask_report": report["mask_report"],
                      "whole_array_min": report["min"], "whole_array_max": report["max"],
                      "n_nan": report["n_nan"], "n_infinite": report["n_infinite"],
                      "crs": report["meta"]["crs"], "shape": report["meta"]["shape"],
                      "transform": report["meta"]["transform"], "zip_single_member_identical": zip_ok},
        "witness": {key: witness[key] for key in ("repo", "submission", "sha256", "their_dots",
                    "my_dots_within_3px_of_theirs", "spearman_full_footprint", "duplicate_by_overlap", "duplicate_by_rho")},
        "historical_hash_table_check": {
            "scope": "Recorded hashes from nine frozen owner snapshots; not all current, private, or organizer artifacts. Source TIFFs were not re-fetched in this check.",
            "inventory_sha256": digest(INVENTORY), "inventory_source_paths": len(inventory),
            "byte_hash_matches": file_matches, "decoded_audit_sha256": digest(DECODED_AUDIT),
            "decoded_hash_rows": len(rows), "decoded_hash_matches": pixel_matches,
            "not_a_surface_or_dot_novelty_audit": True,
        },
        "scope": "One registered C1 raster remeasured; one STOP is decisive. Not a complete registry surface/dot scan or evidence of copying.",
        "holdout": {"evidence_class": "NOT MEASURED", "evaluator_version": None, "dti": None,
                    "ci95": None, "withheld_positive_pixels": None},
        "leaderboard_estimate": None,
        "corrections": [
            "The historical card's raster_decoded_sha256 repeats the TIFF byte hash; use the decoded fingerprint in this review.",
            "Competing-sparse overlap was not measured; expectations based on a different file are not a uniqueness result.",
            "A random null is not a geological method, leakage canary or evidence of competitive holdout performance.",
            "The owner's mirrored 19-band cache was restored and hash-checked in the current integration, not independently authenticated organizer data.",
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
            raise ValueError("Focus-9 safety receipt changed: " + "; ".join(differences[:10]))
    print(json.dumps({"verdict": result["verdict"], "ok_to_submit": False,
                      "c1_forward_overlap": result["witness"]["my_dots_within_3px_of_theirs"]}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, rasterio.errors.RasterioError) as error:
        print(json.dumps({"ok_to_submit": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
