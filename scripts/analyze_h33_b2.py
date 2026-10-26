#!/usr/bin/env python3
"""Reproduce the evidence-bounded H33-B2 ancestry and catalogue-halo audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry/registry.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
CATALOGUE = ROOT / "data/bridge/labels.tif"
OUTPUT = ROOT / "evidence/h33_b2_forensics.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def choose(entries: list[dict], token: str) -> dict:
    matches = [row for row in entries if token in row["file"]]
    if not matches:
        raise ValueError(f"Missing registry comparator: {token}")
    return matches[0]


def read_dots(entry: dict, footprint: np.ndarray) -> np.ndarray:
    path = ROOT / entry["cache_path"]
    if sha256(path) != entry["sha256"]:
        raise ValueError(f"Raster checksum mismatch: {entry['file']}")
    with rasterio.open(path) as dataset:
        array = dataset.read(1)
    if array.shape != footprint.shape or not np.isfinite(array[footprint]).all():
        raise ValueError(f"Invalid comparator grid: {entry['file']}")
    content = hashlib.sha256(np.asarray(array[footprint], dtype="<f4").tobytes()).hexdigest()
    if content != entry["footprint_sha256"]:
        raise ValueError(f"Footprint checksum mismatch: {entry['file']}")
    return footprint & (array > 0)


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    with rasterio.open(TEMPLATE) as dataset:
        footprint = np.isfinite(dataset.read(1))
    with rasterio.open(CATALOGUE) as dataset:
        catalogue = footprint & (dataset.read(1) > 0)

    parent_entry = choose(registry["entries"], "d2-8-20261002-e56ea318af89")
    b2_entry = choose(registry["entries"], "h33-h33-2-b2-20261004T220000Z-e5eb6e7e")
    parent = read_dots(parent_entry, footprint)
    b2 = read_dots(b2_entry, footprint)
    removed = parent & ~b2
    added = b2 & ~parent
    distance_px = distance_transform_edt(~catalogue)[removed]

    report = {
        "schema": "gemsdoe1-h33-b2-forensics-v1",
        "inputs": {
            "parent": {
                "file": parent_entry["file"],
                "sha256": parent_entry["sha256"],
                "positive_pixels": int(parent.sum()),
            },
            "h33_b2": {
                "file": b2_entry["file"],
                "sha256": b2_entry["sha256"],
                "positive_pixels": int(b2.sum()),
            },
            "catalogue_sha256": sha256(CATALOGUE),
            "registry_sha256": sha256(REGISTRY),
        },
        "exact_ancestry": {
            "b2_is_exact_subset_of_parent": bool(not added.any()),
            "removed_parent_dots": int(removed.sum()),
            "added_dots": int(added.sum()),
            "unchanged_kept_dots": int((parent & b2).sum()),
            "all_removed_within_200m_of_public_catalogue": bool(
                len(distance_px) and np.all(distance_px <= 2.0)
            ),
            "removed_distance_to_catalogue_px": {
                "minimum": float(distance_px.min()),
                "maximum": float(distance_px.max()),
                "mean": float(distance_px.mean()),
                "within_1px": int(np.count_nonzero(distance_px <= 1.0)),
                "within_2px": int(np.count_nonzero(distance_px <= 2.0)),
            },
        },
        "score_evidence": {
            "h33_b2_value": 0.2778,
            "parent_d2_8_value": 0.2600,
            "difference": 0.0178,
            "label": "OWNER-REPORTED / UNVERIFIED",
            "organizer_receipt_present": False,
            "limitation": (
                "No artifact-linked DrivenData submission receipt or hidden labels are present; "
                "the values cannot be upgraded to ORGANIZER-CONFIRMED."
            ),
        },
        "mechanism_interpretation": {
            "metric_identity": "DTI = TPw / (TPw + 0.2*FPw + 0.8*FNw)",
            "evidence_supported_statement": (
                "B2 added no geological detections. It removed exactly 6,436 parent dots, all "
                "within 200 m of the public catalogue. If those dots had zero hidden-truth "
                "credit, deleting them reduces the weighted false-positive denominator and "
                "raises DTI; this is a plausible precision-cleanup mechanism."
            ),
            "not_proven": (
                "Hidden TPw/FPw/FNw contributions and the uploaded file are unavailable, so "
                "the deletion cannot be asserted to have caused the owner-reported value."
            ),
            "scientific_uniqueness": (
                "Not scientifically distinct from D2.8: it is a strict deletion-only subset."
            ),
        },
    }
    ancestry = report["exact_ancestry"]
    if not (
        ancestry["b2_is_exact_subset_of_parent"]
        and ancestry["removed_parent_dots"] == 6436
        and ancestry["added_dots"] == 0
        and ancestry["unchanged_kept_dots"] == 37654
        and ancestry["all_removed_within_200m_of_public_catalogue"]
    ):
        raise ValueError("H33-B2 ancestry no longer matches the pinned evidence")
    OUTPUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
