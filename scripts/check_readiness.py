#!/usr/bin/env python3
"""Inspect actual inputs, the cached feature stack and the saved TIFF, fail closed.

Readiness has THREE different meanings: pinned mirror input integrity, local
GeoTIFF format, and scientific/slot approval. A valid research TIFF is not an
approved contest entry. No data are downloaded, trained on or silently repaired.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ("training_features.tif", "labels.tif", "sample_submission.tif")
TOOLS = ("scripts/evaluate_holdout.py", "scripts/submission_writer.py")


def load(relative: str) -> dict:
    """Read a registry JSON relative to this checkout (legacy review API)."""
    return json.loads((ROOT / relative).read_text())


def sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def inspect_core(root: Path, manifest: dict) -> dict:
    pins = {row["dest"]: row for row in manifest["files"]}
    rows = {}
    for name in CORE:
        path = root / "data" / name
        exists = path.is_file()
        digest = sha256(path) if exists else None
        rows[name] = {"present": exists, "verified_to_owner_mirror_pin": digest == pins[name]["sha256"],
                      "sha256": digest, "expected_sha256": pins[name]["sha256"]}
    return rows


def inspect_template(root: Path) -> dict:
    """A cached input is not usable with an altered shared evaluator or writer."""
    pin = json.loads((root / "registry/shared_template.json").read_text())
    result = {"verified": False, "files_checked": 0, "expected_files": len(pin["files"])}
    for row in pin["files"]:
        path = (root / row["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha256(path) != row["sha256"]:
            result["error"] = f"shared template missing or modified: {row['path']}"
            return result
        result["files_checked"] += 1
    result["verified"] = True
    return result


def inspect_cache(root: Path, core: dict) -> dict:
    """Do not trust an old receipt without checking every current cache byte."""
    receipt_file = root / "data/template57/evidence/feature_cache.json"
    pins = json.loads((root / "registry/template_pins.json").read_text())
    expected = pins["cached_feature_stack_reference"]["expected_band_sha256"]
    result = {"status": "NOT_PREPARED", "bands_checked": 0, "expected_bands": len(expected),
              "verified": False, "organizer_origin_authenticated": False}
    if not receipt_file.is_file():
        return result
    try:
        receipt = json.loads(receipt_file.read_text())
        bands = receipt["bands"]
        if len(bands) != len(expected) or receipt["source_sha256"] != core["training_features.tif"]["sha256"]:
            raise ValueError("cache source hash or band count differs from pinned core input")
        cache_root = (root / "data/template57").resolve()
        for index, (row, digest) in enumerate(zip(bands, expected, strict=True), start=1):
            if row["band"] != index or row["cache_file"] != f".cache/features/band-{index:02d}.npy":
                raise ValueError(f"cache band {index} index or path differs from pinned stack order")
            path = (cache_root / row["cache_file"]).resolve()
            if not path.is_relative_to(cache_root) or not path.is_file() or sha256(path) != digest or row["sha256"] != digest:
                raise ValueError(f"cache band {row['band']} missing or hash mismatch")
            result["bands_checked"] += 1
        result.update(status="PINNED_19_BANDS_VERIFIED", verified=True)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        result.update(status="CACHE_INTEGRITY_FAILURE", error=str(exc)[:200])
    return result


def inspect_artifact(root: Path, card: dict) -> dict:
    path = root / card["artifact"]
    result = {"present": path.is_file(), "sha256_matches_frozen_card": False,
              "local_format_passed": False, "zip_contains_same_tiff": False,
              "submission_approved": False}
    if not result["present"]:
        return result
    result["sha256_matches_frozen_card"] = sha256(path) == card["raster_sha256"]
    if not result["sha256_matches_frozen_card"]:
        result["error"] = "exact TIFF bytes differ from frozen card"
        return result
    for kind, candidate in (("tiff", path), ("zip", path.with_suffix(".zip"))):
        if not candidate.is_file():
            result["error"] = f"{kind} missing"
            return result
        try:
            process = subprocess.run([sys.executable, str(root / "scripts/validate_submission.py"), str(candidate)],
                                     cwd=root, capture_output=True, text=True, timeout=90, check=False)
            if process.returncode:
                result["error"] = f"{kind} strict validator failed (exit {process.returncode}): {process.stderr[:180]}"
                return result
            report = json.loads(process.stdout)
            if report["sha256"] != card["raster_sha256"] or not report["all_checks_passed"] or report["ok_to_submit"]:
                result["error"] = f"{kind} integrity, format or negative-decision mismatch"
                return result
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
            result["error"] = f"{kind} validation failed: {str(exc)[:180]}"
            return result
        if kind == "tiff":
            result["local_format_passed"] = True
        else:
            # ZIP validator reopens the contained TIFF and records both hashes.
            result["zip_contains_same_tiff"] = True
    return result


def inspect(root: Path = ROOT) -> dict:
    manifest = json.loads((root / "registry/data_manifest.json").read_text())
    card = json.loads((root / "registry/run_card.json").read_text())
    core = inspect_core(root, manifest)
    cache = inspect_cache(root, core)
    template = inspect_template(root)
    tools = {name: (root / name).is_file() for name in TOOLS}
    artifact = inspect_artifact(root, card)
    csv = root / "data/1m_DEM_links.csv"
    inputs_ready = all(row["verified_to_owner_mirror_pin"] for row in core.values())
    methods_ready = inputs_ready and cache["verified"] and template["verified"] and all(tools.values())
    integrity_failed = (any(row["present"] and not row["verified_to_owner_mirror_pin"] for row in core.values())
                        or cache["status"] == "CACHE_INTEGRITY_FAILURE" or not template["verified"]
                        or bool(artifact.get("error")))
    artifact_passes = artifact["local_format_passed"] and artifact["zip_contains_same_tiff"]
    scientific_screen_recorded = bool(card.get("holdout", {}).get("dti") is not None
                                      and card.get("leakage_canary") and card.get("registry"))
    stopped = (card.get("verdict") == "negative" and card.get("decision", {}).get("ok_to_submit") is False
               and card.get("registry", {}).get("passes_literal_uniqueness") is False)
    return {
        "status": "INTEGRITY_FAILURE" if integrity_failed else
                  "INPUTS_READY_LANE_STOPPED" if methods_ready and stopped else
                  "RESTORE_REQUIRED" if not methods_ready else "REVIEW_REQUIRED",
        "input_provenance": "OWNER-MIRROR-INTEGRITY; not independently authenticated organizer data",
        "core_inputs": core, "core_input_hashes_passed": inputs_ready,
        "optional_1m_dem_links_csv": {"present": csv.is_file(), "required_for_cached_19_band_method": False,
            "official_data_tab": "https://www.drivendata.org/competitions/306/competition-doe-gems/data/",
            "access": "login required"},
        "shared_template_tools": tools, "shared_template_pins": template,
        "feature_cache": cache, "cached_19_band_pipeline_inputs_ready": methods_ready,
        "research_artifact": artifact, "submission_tif_generated": artifact["present"] and artifact["sha256_matches_frozen_card"],
        "submission_tif_locally_format_validated": artifact_passes,
        "scientific_screen_recorded": scientific_screen_recorded, "scientific_gates_passed": False,
        "current_lane_stopped": stopped, "weekly_slot_used_here": False,
        "ok_to_download_for_research": artifact_passes, "ok_to_submit": False,
        "next_action": "STOP: investigate the failed digest/validator against its pinned source; do not bypass or overwrite the pin."
            if integrity_failed else "Retain this negative research TIFF; do not re-run or retune the stopped lane."
            if methods_ready else "Run bash scripts/download_competition_data.sh and .venv/bin/python scripts/prepare_data.py on an authorized machine; never change pinned bytes to force a pass.",
        "limit": "File presence or a local format pass cannot establish an organizer receipt, literal new-dot novelty, a better holdout, or current account allowance.",
    }


def build_report() -> dict:
    """Compatibility view for the separate frozen-release review, never an approval.

    Keep the richer three-way inspect report intact. A research input ready flag
    does NOT mean the stopped scientific pipeline is ready to resume.
    """
    report = inspect(ROOT)
    ledger = json.loads((ROOT / "registry/experiment_ledger.json").read_text())
    card = json.loads((ROOT / "registry/run_card.json").read_text())
    stopped = report["current_lane_stopped"] and ledger.get("status") == "negative_stopped"
    return {**report,
        "schema": "wbg-readiness-v3",
        "inspection_status": report["status"],
        "status": "BLOCKED_SCIENTIFIC" if report["cached_19_band_pipeline_inputs_ready"] else "BLOCKED_INPUTS",
        "inputs_integrity_verified": report["cached_19_band_pipeline_inputs_ready"],
        "organizer_origin_authenticated": False,
        "lane_stopped": stopped, "experiment_ledger_status": ledger.get("status"),
        "pipeline_ready": False, "artifact": report["research_artifact"],
        "artifact_role": card["artifact_role"],
    }


def main() -> int:
    report = inspect()
    print(json.dumps(report, indent=2, allow_nan=False))
    # Exit 2 means this stopped lane is NOT approved to resume/submit even when
    # its research inputs and downloadable format-validated TIFF are present.
    if not report["shared_template_pins"]["verified"] or report["feature_cache"]["status"] == "CACHE_INTEGRITY_FAILURE" or any(
        row["present"] and not row["verified_to_owner_mirror_pin"] for row in report["core_inputs"].values()
    ) or report["research_artifact"].get("error"):
        return 1
    return 2  # No state of data placement can resume a stopped scientific lane.


if __name__ == "__main__":
    raise SystemExit(main())
