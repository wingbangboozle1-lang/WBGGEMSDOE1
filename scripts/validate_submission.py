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
    card_path = ROOT / "registry/run_card.json"
    card = json.loads(card_path.read_text()) if card_path.exists() else None
    identity_matches = bool(card and report["sha256"] == card["raster_sha256"])
    report["run_card_matches_exact_tiff"] = identity_matches
    report["promotion_verdict"] = card["verdict"] if identity_matches else "untracked"
    report["ok_to_submit"] = approval_matches(card, report, identity_matches)
    report["warning"] = "FORMAT PASS is not uniqueness, scientific efficacy, organizer acceptance or slot approval."
    print(json.dumps(report, indent=2, allow_nan=False))
    if not report["all_checks_passed"]:
        return 1
    return 2 if args.require_submit_ready and not report["ok_to_submit"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile, rasterio.errors.RasterioError) as error:
        print(json.dumps({"all_checks_passed": False, "ok_to_submit": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
