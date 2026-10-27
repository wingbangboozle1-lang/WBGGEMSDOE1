#!/usr/bin/env python3
"""Fail-closed validation of the frozen TIP1 artifact, evidence packet and site."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "evidence/tip1_run_card_20261026.json"
SITE_CARD_PATH = ROOT / "docs/data/tip1_run_card.json"
NINE_PATH = ROOT / "evidence/nine_site_executive_summary_20261026.json"
REGISTRY_PATH = ROOT / "registry/registry.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
OUTPUT = ROOT / "evidence/release_validation.json"
DOCS_OUTPUT = ROOT / "docs/data/release_validation.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add(checks: dict, name: str, passed: bool, detail: str) -> None:
    checks[name] = {"pass": bool(passed), "detail": detail}


def main() -> int:
    card = json.loads(CARD_PATH.read_text())
    site_card = json.loads(SITE_CARD_PATH.read_text())
    nine = json.loads(NINE_PATH.read_text())
    registry = json.loads(REGISTRY_PATH.read_text())
    artifact = ROOT / "docs/downloads" / card["submission_name"]
    checks: dict[str, dict] = {}

    add(checks, "run_card_site_copy_identity", site_card == card, "evidence card equals docs card")
    add(
        checks,
        "artifact_sha256",
        artifact.is_file() and sha256(artifact) == card["raster_sha256"],
        card["raster_sha256"],
    )
    with rasterio.open(TEMPLATE) as template:
        fp = np.isfinite(template.read(1))
        grid = (template.shape, template.crs, template.transform)
    with rasterio.open(artifact) as dataset:
        array = dataset.read(1)
        artifact_grid = (dataset.shape, dataset.crs, dataset.transform)
        metadata = {
            "driver": dataset.driver,
            "count": dataset.count,
            "dtype": dataset.dtypes[0],
            "crs": dataset.crs.to_string() if dataset.crs else None,
            "shape": list(dataset.shape),
            "transform": list(dataset.transform)[:6],
            "nodata": dataset.nodata,
        }
    add(checks, "grid_identity", artifact_grid == grid, str(metadata))
    add(
        checks,
        "one_float32_band",
        metadata["count"] == 1 and metadata["dtype"] == "float32",
        f"count={metadata['count']}, dtype={metadata['dtype']}",
    )
    add(
        checks,
        "whole_array_finite",
        bool(np.isfinite(array).all()),
        f"nonfinite={int(np.count_nonzero(~np.isfinite(array)))}",
    )
    add(
        checks,
        "whole_array_range_0_1",
        bool(np.isfinite(array).all() and array.min() >= 0 and array.max() <= 1),
        f"min={float(np.nanmin(array))}, max={float(np.nanmax(array))}",
    )
    add(
        checks,
        "footprint_dot_count",
        int(np.count_nonzero(array[fp] > 0)) == card["final_dot_count"],
        f"observed={int(np.count_nonzero(array[fp] > 0))}, receipt={card['final_dot_count']}",
    )
    add(
        checks,
        "strict_shared_validator",
        bool(
            card["validator_output"]["format_valid"]
            and card["validator_output"]["checks"][
                "variant_strict_whole_array_no_nan_allowed"
            ]["pass"]
        ),
        "full shared validator output is embedded in run card",
    )
    add(
        checks,
        "note_at_most_140_chars",
        1 <= len(card["submission_note"]) <= 140,
        f"length={len(card['submission_note'])}",
    )
    add(
        checks,
        "negative_verdict_is_unambiguous",
        card["verdict"] == "negative"
        and card["promote"] is False
        and card["ok_to_submit"] is False
        and "DO NOT SUBMIT" in card["submission_note"],
        card["stopped_reason"],
    )
    add(
        checks,
        "experiment_and_slot_budget",
        card["experiments_run"] == 3
        and card["elapsed_seconds"] <= card["time_limit_seconds"]
        and card["submission_slots_used"] == 0,
        f"experiments={card['experiments_run']}, seconds={card['elapsed_seconds']:.3f}, slots={card['submission_slots_used']}",
    )
    add(
        checks,
        "registry_complete",
        registry["rejected_count"] == 0
        and registry["unique_rasters"] == len(registry["entries"])
        and registry["retained_spacing_5_lattice_present"],
        f"unique={registry['unique_rasters']}, rejected={registry['rejected_count']}",
    )
    add(
        checks,
        "nine_site_table_complete",
        len(nine["sites"]) == 9
        and {row["site"] for row in nine["sites"]}
        == {f"GEMSDOE{x}" for x in (24, 25, 27, 28, 30, 31, 32, 33, 36)},
        f"rows={len(nine['sites'])}",
    )
    add(
        checks,
        "historical_score_labels",
        all(
            row["score_evidence_label"] == "OWNER-REPORTED / UNVERIFIED"
            and row["organizer_receipt_present"] is False
            for row in nine["sites"]
        ),
        "all historical values remain unverified",
    )
    required_site_files = [
        ROOT / "docs/index.html",
        ROOT / "docs/submission-instructions.html",
        ROOT / "docs/research.html",
        ROOT / "docs/methodology.html",
        ROOT / "docs/assets/style.css",
        ROOT / "docs/data/feed.json",
    ]
    add(
        checks,
        "site_packet_present",
        all(path.is_file() and path.stat().st_size > 0 for path in required_site_files),
        ", ".join(str(path.relative_to(ROOT)) for path in required_site_files),
    )

    result = {
        "schema": "gemsdoe1-release-validation-v1",
        "generated_utc": card["generated_utc"],
        "artifact": str(artifact.relative_to(ROOT)),
        "artifact_sha256": card["raster_sha256"],
        "raster_metadata": metadata,
        "checks": checks,
        "passed": all(row["pass"] for row in checks.values()),
        "verdict": "negative",
        "ok_to_download": bool(card["ok_to_download"]),
        "ok_to_submit": False,
    }
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    OUTPUT.write_text(text)
    DOCS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUTPUT.write_text(text)
    print(text, end="")
    if not result["passed"]:
        raise SystemExit("Release validation failed closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
