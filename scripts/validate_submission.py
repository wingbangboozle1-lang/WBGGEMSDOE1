#!/usr/bin/env python3
"""Reopen one TIFF / one-TIFF ZIP with the unchanged shared validator.

Exit 0 means local FORMAT pass only. --require-submit-ready additionally
requires a real approval, which this negative research artifact does not have.
No command in this project submits anything to DrivenData.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
import numpy as np
import rasterio
from gems57 import gates
from gems57.grid import SHAPE
from gems57.validate import validate as validate_shared
from wbggems.audit import sha256
# Preserve the pre-existing supplied-reference API for inherited tests/callers.
# It is not the authoritative all-finite writer/validator for WBG-C1.
from gems.legacy_reference_validator import validate as validate


def check_tiff(path):
    # Reject an unexpected raster size before the shared validator reads it.
    # This is a caller resource bound, not a fork of its numerical checks.
    with rasterio.open(path) as ds:
        if ds.shape != SHAPE or ds.count != 1:
            raise ValueError(f"expected one band on the {SHAPE} competition grid")
    footprint = catalogue = None
    sample, labels = ROOT / "data/sample_submission.tif", ROOT / "data/labels.tif"
    # Concurrent main already retains byte-identical small bridge references.
    # Prefer current-lane inputs, then verify bridge fallbacks by the same pins.
    if not sample.exists():
        sample = ROOT / "data/bridge/sample_submission.tif"
    if not labels.exists():
        labels = ROOT / "data/bridge/labels.tif"
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    pins = {r["dest"]: r["sha256"] for r in manifest["files"]}
    reference = None
    if sample.exists():
        if sha256(sample) != pins["sample_submission.tif"]:
            raise ValueError("reference template hash mismatch")
        with rasterio.open(sample) as ds:
            footprint = np.isfinite(ds.read(1))
            reference = (ds.shape, ds.crs, ds.transform)
        if labels.exists():
            if sha256(labels) != pins["labels.tif"]:
                raise ValueError("catalogue reference hash mismatch")
            with rasterio.open(labels) as ds:
                if (ds.shape, ds.crs, ds.transform) != reference:
                    raise ValueError("catalogue/reference grid mismatch")
                catalogue = ds.read(1) > 0
    report = validate_shared(path, footprint, catalogue)
    nodata = report["meta"].get("nodata")
    if nodata is not None and not math.isfinite(nodata):
        # Metadata serialization only, not any repair to prediction pixels.
        report["meta"]["nodata"] = str(nodata)
    if sample.exists():
        template = gates.format_report(path, sample, footprint=footprint)
        report["template_report"] = template
        report["all_checks_passed"] &= template["ok"]
    report["mirrored_reference_available"] = sample.exists()
    report["catalogue_reference_available"] = catalogue is not None
    report["independent_organizer_origin_authenticated"] = False
    return report


def approval_matches(card, report, identity_matches):
    """Format or a single accidentally flipped decision flag cannot approve a file."""
    if not card or not identity_matches or not report.get("all_checks_passed"):
        return False
    decision = card.get("decision", {})
    return bool(card.get("verdict") == "promote"
        and decision.get("verdict") == "promote"
        and decision.get("ok_to_submit") is True
        and decision.get("eligible_for_separate_selector") is True
        and decision.get("approved_for_weekly_slot") is True
        and card.get("registry", {}).get("passes_literal_uniqueness") is True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("reference", type=Path, nargs="?", help="inherited supplied-reference compatibility mode; format only, never approval")
    parser.add_argument("--require-submit-ready", action="store_true")
    args = parser.parse_args()
    if args.reference is not None:
        legacy = validate(args.file, args.reference)
        metadata = legacy.get("checks", {}).get("candidate", {})
        if metadata.get("nodata") is not None and not math.isfinite(metadata["nodata"]):
            metadata["nodata"] = str(metadata["nodata"])
        report = {"all_checks_passed": legacy["ok"], "ok_to_submit": False,
            "compatibility_mode": "inherited supplied-reference format/nodata validator; not WBG-C1 approval",
            "reference_report": legacy}
        print(json.dumps(report, indent=2, allow_nan=False))
        if not legacy["ok"]:
            return 1
        return 2 if args.require_submit_ready else 0
    source = args.file.resolve()
    if source.suffix.lower() == ".zip":
        cache = ROOT / ".cache/validator"
        cache.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source) as z:
            names = z.namelist()
            if len(names) != 1 or Path(names[0]).suffix.lower() not in (".tif", ".tiff"):
                raise ValueError("submission ZIP must contain exactly one TIFF and nothing else")
            if z.getinfo(names[0]).file_size > 512 * 1024**2:
                raise ValueError("unexpectedly large TIFF in ZIP")
            with tempfile.TemporaryDirectory(dir=cache) as directory:
                target = Path(directory) / "contained.tif"
                target.write_bytes(z.read(names[0]))
                report = check_tiff(target)
                report["file"] = source.name + "::" + names[0]
                report["zip_sha256"] = sha256(source)
    elif source.suffix.lower() in (".tif", ".tiff"):
        report = check_tiff(source)
    else:
        raise ValueError("expected a .tif/.tiff or a ZIP with exactly one TIFF")
    # Select only by exact TIFF bytes, not by filename or a format pass. WBG-2 is
    # a known negative: even inconsistent/fabricated future card flags must not
    # unlock those exact bytes without changing this code and its safety review.
    known_negative = "f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3"
    s2_negative = "6992387620fcb2d7f3a06d867b79b6ad770d7006b87d35b131e27a5035c62880"
    paths = (
        "registry/run_card.json",
        "evidence/wbg2/run_card.json",
        "evidence/wbg_s2/run_card.json",
        "evidence/wbg3/run_card.json",
        "evidence/wbg3_spipmr/run_card.json",
    )
    matches = []
    for name in paths:
        card_path = ROOT / name
        if card_path.exists():
            candidate = json.loads(card_path.read_text())
            artifact = candidate.get("artifact")
            nested_sha = artifact.get("tif_sha256") if isinstance(artifact, dict) else None
            if candidate.get("raster_sha256") == report["sha256"] or nested_sha == report["sha256"]:
                matches.append((name, candidate))
    if len(matches) > 1:
        raise ValueError("multiple decision cards claim these exact TIFF bytes")
    card_name, card = matches[0] if matches else (None, None)
    identity_matches = bool(card)
    report["run_card_matches_exact_tiff"] = identity_matches
    report["run_card_path"] = card_name
    report["promotion_verdict"] = card["verdict"] if identity_matches else "untracked"
    report["ok_to_submit"] = approval_matches(card, report, identity_matches)
    if report["sha256"] == known_negative:
        if (not identity_matches or card_name != "evidence/wbg2/run_card.json"
                or card.get("verdict") != "negative" or card.get("decision", {}).get("ok_to_submit") is not False):
            raise ValueError("WBG-2 known-negative decision missing or inconsistent")
        safety = json.loads((ROOT / "evidence/wbg2/safety_audit_20261027.json").read_text())
        witness = safety["already_placed_final_dots_witness"]
        if (safety["existing_tiff_sha256"] != known_negative or safety["passed_literal_gate"] is not False
                or not witness["duplicate_by_overlap"] or witness["my_dots_within_3px_of_theirs"] <= .70):
            raise ValueError("WBG-2 known-negative registry witness missing or inconsistent")
        report["ok_to_submit"] = False
        report["known_negative_registry_overlap"] = witness["my_dots_within_3px_of_theirs"]
    if report["sha256"] == s2_negative:
        decision = card.get("strict_governance_decision", {}) if card else {}
        if (not identity_matches or card_name != "evidence/wbg_s2/run_card.json"
                or card.get("verdict") != "negative" or decision.get("ok_to_submit") is not False
                or decision.get("eligible_for_separate_selector") is not False):
            raise ValueError("WBG-S2 known-negative decision missing or inconsistent")
        safety = json.loads((ROOT / "evidence/wbg_s2/safety_review_20261027.json").read_text())
        rows = safety["witnesses"]
        if (safety["existing_tiff_sha256"] != s2_negative or safety["ok_to_submit"] is not False
                or safety["eligible_for_separate_selector"] is not False or len(rows) != 2
                or [row["sha256"] for row in rows] != [
                    "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2",
                    "8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875"]
                or any(row["duplicate_by_overlap"] is not True
                       or not math.isfinite(row["my_dots_within_3px_of_theirs"])
                       or not .70 < row["my_dots_within_3px_of_theirs"] <= 1 for row in rows)):
            raise ValueError("WBG-S2 known-negative registry witnesses missing or inconsistent")
        report["ok_to_submit"] = False
        report["known_negative_registry_overlap"] = max(row["my_dots_within_3px_of_theirs"] for row in rows)
        report["known_negative_lattice_overlap"] = rows[0]["my_dots_within_3px_of_theirs"]
    report["warning"] = "FORMAT PASS is not uniqueness, scientific efficacy, organizer acceptance or slot approval."
    print(json.dumps(report, indent=2, allow_nan=False))
    if not report["all_checks_passed"]:
        return 1
    return 2 if args.require_submit_ready and not report["ok_to_submit"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, RuntimeError, zipfile.BadZipFile, rasterio.errors.RasterioError) as error:
        print(json.dumps({"all_checks_passed": False, "ok_to_submit": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
