#!/usr/bin/env python3
"""Fail-closed readiness report for the current GEMS research workflow.

This script only checks file placement and hash-pinned tool presence. It does
not download, infer, or fabricate data, and it never authorizes a submission.

``1m_DEM_links.csv`` is intentionally **not** required by the current lane: the
frozen TASC / WBG-C1 / TIP1 experiments use the hash-pinned 19-band feature
cache and precomputed 3DEP-derived LiDAR aggregate, not raw 1 m DEM tiles. The
official raw-tile index remains listed as optional external data for future
DIFF1 work; its absence is not a blocker for the current CPU pipeline.
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
    ],
    "shared_template_tools": [
        "scripts/evaluate_holdout.py",
        "scripts/submission_writer.py",
    ],
}
OPTIONAL_EXTERNAL = [
    "data/1m_DEM_links.csv",
    "data/external/lidar_scarp_features_u8.tif",
]


def main() -> int:
    groups: dict[str, dict[str, list[str]]] = {}
    for group, relative_paths in REQUIRED.items():
        present, missing = [], []
        for relative in relative_paths:
            (present if (ROOT / relative).is_file() else missing).append(relative)
        groups[group] = {"present": present, "missing": missing}
    optional = {p: bool((ROOT / p).is_file()) for p in OPTIONAL_EXTERNAL}

    prerequisites_present = all(not result["missing"] for result in groups.values())
    report = {
        "status": "INPUTS_AND_TOOLS_PRESENT" if prerequisites_present else "BLOCKED",
        "root": str(ROOT),
        "checks": groups,
        "optional_external_data": optional,
        "optional_data_note": (
            "1m_DEM_links.csv is an official raw-DEM index for future raw-tile work only; "
            "the current lane uses the verified 19-band cache and pinned LiDAR aggregate."
        ),
        "submission_tif_generated": False,
        "pipeline_ready": False,
        "scientific_gates_checked": False,
        "reason": None if prerequisites_present else "Required competition data and/or shared template tools are absent.",
        "next_action": (
            "Run the shared workflow, then validate holdout, leakage, novelty, and saved TIFF; "
            "file presence alone is not submission approval."
            if prerequisites_present
            else "Place authorized competition data in data/ and restore/configure the shared template tools; "
                 "do not generate a placeholder TIFF."
        ),
        "limitations": [
            "This check only tests file presence; it does not verify file integrity, cache readiness, "
            "raster alignment, registry completeness, or scientific gates.",
            "No submission is authorized by this report.",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if prerequisites_present else 2


if __name__ == "__main__":
    raise SystemExit(main())
