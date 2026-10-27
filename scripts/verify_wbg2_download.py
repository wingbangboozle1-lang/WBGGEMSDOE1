#!/usr/bin/env python3
"""Verify the preserved WBG-2 research download without regenerating it.

Exit zero means exact-artifact integrity and local format validation passed,
and the stored decision is correctly fail-closed. It does NOT mean uniqueness,
scientific efficacy, organizer acceptance, or approval to submit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
TIF = ROOT / "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif"
ZIP = ROOT / "docs/downloads/wbg2-offcatalogue-density-36k-20261027.zip"
CARD = ROOT / "evidence/wbg2/run_card.json"
NINE = ROOT / "evidence/wbg2/nine_site_uniqueness.json"
EXPECTED_TIF_SHA256 = "f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3"
EXPECTED_ZIP_SHA256 = "b4074f093c43ebb41a2b550b5558cf4c5a38c5f1b0c7b69393575ae12e8005b4"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _shared_validator():
    """Load the project's pinned shared validator entry point."""
    sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]
    spec = importlib.util.spec_from_file_location(
        "wbg2_shared_format_validator", ROOT / "scripts/validate_submission.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load shared submission validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check_tiff


def verify() -> dict:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    if not TIF.is_file() or not ZIP.is_file():
        raise FileNotFoundError("preserved WBG-2 TIFF/ZIP download is missing")

    tif_sha = _sha256(TIF)
    zip_sha = _sha256(ZIP)
    checks["tif_sha256_matches_preserved_artifact"] = tif_sha == EXPECTED_TIF_SHA256
    checks["zip_sha256_matches_preserved_archive"] = zip_sha == EXPECTED_ZIP_SHA256
    details["tif_sha256"] = tif_sha
    details["zip_sha256"] = zip_sha

    check_tiff = _shared_validator()
    tif_report = check_tiff(TIF)
    checks["shared_tif_format_validation"] = bool(tif_report.get("all_checks_passed"))
    details["tif_format_report"] = tif_report

    with zipfile.ZipFile(ZIP) as archive:
        files = [info for info in archive.infolist() if not info.is_dir()]
        checks["zip_contains_exactly_one_tiff"] = (
            len(files) == 1 and Path(files[0].filename).suffix.lower() in {".tif", ".tiff"}
        )
        if len(files) == 1 and Path(files[0].filename).suffix.lower() in {".tif", ".tiff"}:
            raw = archive.read(files[0])
            checks["zip_member_bytes_match_tif"] = hashlib.sha256(raw).hexdigest() == tif_sha
            with tempfile.TemporaryDirectory(prefix="wbg2-verify-") as temp:
                extracted = Path(temp) / Path(files[0].filename).name
                extracted.write_bytes(raw)
                zip_report = check_tiff(extracted)
                checks["shared_zip_member_format_validation"] = bool(
                    zip_report.get("all_checks_passed")
                )
                details["zip_member_format_report"] = zip_report
        else:
            checks["zip_member_bytes_match_tif"] = False
            checks["shared_zip_member_format_validation"] = False

    card = json.loads(CARD.read_text())
    nine = json.loads(NINE.read_text())
    checks["card_tif_identity_matches"] = card.get("raster_sha256") == tif_sha
    checks["card_artifact_paths_match"] = (
        card.get("artifacts", {}).get("tif") == "docs/downloads/" + TIF.name
        and card.get("artifacts", {}).get("zip") == "docs/downloads/" + ZIP.name
    )
    checks["decision_is_explicitly_negative"] = (
        card.get("verdict") == "negative"
        and card.get("decision", {}).get("ok_to_download") is True
        and card.get("decision", {}).get("ok_to_submit") is False
        and card.get("decision", {}).get("eligible_for_separate_selector") is False
        and card.get("decision", {}).get("approved_for_weekly_slot") is False
    )
    checks["no_valid_holdout_score_is_claimed"] = (
        card.get("holdout_dti", {}).get("status") == "NOT MEASURED"
        and card.get("holdout_dti", {}).get("value") is None
        and card.get("score_estimate", {}).get("value") is None
    )
    checks["literal_registry_stop_is_recorded"] = (
        card.get("registry", {}).get("passes_final_dot_gate") is False
        and card.get("registry", {}).get("global_uniqueness_cleared") is False
        and card.get("registry", {}).get("max_forward_3px_overlap") == 1.0
    )
    checks["note_within_140_characters"] = (
        len(card.get("submission_note", "")) <= 140
        and "DO NOT SUBMIT" in card.get("submission_note", "")
    )
    checks["focus_nine_audit_is_scoped_not_global"] = (
        nine.get("n_audited") == 9
        and "NOT_GLOBAL_REGISTRY_CLEARANCE" in nine.get("verdict", "")
        and "not a full registry" in nine.get("scope", "").lower()
    )

    details["artifact_role"] = "research-only download"
    details["download_decision"] = "YES — research only"
    details["submit_decision"] = "NO"
    details["format_is_not_scientific_or_organizer_clearance"] = True
    return {"checks": checks, "details": details, "all_checks_passed": all(checks.values())}


def main() -> int:
    report = verify()
    for name, passed in report["checks"].items():
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
    print(json.dumps(report["details"], indent=2, allow_nan=False))
    if not report["all_checks_passed"]:
        print("\nFORMAT / INTEGRITY CHECK: FAIL. Do not rely on the download.")
        return 1
    print("\nFORMAT / INTEGRITY CHECK: PASS")
    print("DOWNLOAD: YES (research only)  |  SUBMIT: NO")
    print("This pass is not scientific efficacy, full-registry uniqueness, or organizer acceptance.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile, rasterio.errors.RasterioError) as exc:
        print(json.dumps({"all_checks_passed": False, "download": "research-only", "submit": "NO", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
