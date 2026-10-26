#!/usr/bin/env python3
"""Fail-closed readiness report for the GEMS training/validation/submission workflow.

This script only checks file placement. It does not download, infer, or fabricate data.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "competition_data": [
        "data/training_features.tif",
        "data/labels.tif",
        "data/sample_submission.tif",
        "data/1m_DEM_links.csv",
    ],
    "shared_template_tools": [
        "scripts/evaluate_holdout.py",
        "scripts/submission_writer.py",
    ],
}


def main() -> int:
    groups: dict[str, dict[str, list[str]]] = {}
    for group, relative_paths in REQUIRED.items():
        present, missing = [], []
        for relative in relative_paths:
            (present if (ROOT / relative).is_file() else missing).append(relative)
        groups[group] = {"present": present, "missing": missing}

    prerequisites_present = all(not result["missing"] for result in groups.values())
    report = {
        "status": "INPUTS_AND_TOOLS_PRESENT" if prerequisites_present else "BLOCKED",
        "root": str(ROOT),
        "checks": groups,
        "submission_tif_generated": False,
        "pipeline_ready": False,
        "scientific_gates_checked": False,
        "reason": None if prerequisites_present else "Required competition data and/or shared template tools are absent.",
        "next_action": (
            "Run the shared workflow, then validate holdout, leakage, novelty, and saved TIFF; file presence alone is not submission approval."
            if prerequisites_present
            else "Place authorized competition data in data/ and restore/configure the shared template tools; do not generate a placeholder TIFF."
        ),
        "limitations": [
            "This check only tests file presence; it does not verify file integrity, cache readiness, raster alignment, registry completeness, or scientific gates.",
            "No submission is authorized by this report.",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if prerequisites_present else 2


if __name__ == "__main__":
    raise SystemExit(main())
