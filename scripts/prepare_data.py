#!/usr/bin/env python3
"""Reuse and verify the unchanged shared template cache (never train on sample values)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = ROOT / "data/template57"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_template():
    pin = json.loads((ROOT / "registry/shared_template.json").read_text())
    for row in pin["files"]:
        path = ROOT / row["path"]
        if not path.exists() or sha256(path) != row["sha256"]:
            raise ValueError(f"shared template missing or modified: {row['path']}")
    return pin


def prepare():
    pin = verify_template()
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    selected = {"training_features.tif", "labels.tif", "sample_submission.tif"}
    for row in manifest["files"]:
        if row["dest"] not in selected:
            continue
        source = ROOT / "data" / row["dest"]
        if not source.exists() or sha256(source) != row["sha256"]:
            raise ValueError(f"raw owner-mirror missing or hash mismatch: {source}")
        destination = CACHE_ROOT / "data/official" / row["dest"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            destination.symlink_to(os.path.relpath(source, destination.parent))
    evidence = CACHE_ROOT / "evidence/feature_cache.json"
    expected_bands = json.loads((ROOT / "registry/template_pins.json").read_text())[
        "cached_feature_stack_reference"]["expected_band_sha256"]
    reusable = False
    if evidence.exists():
        receipt = json.loads(evidence.read_text())
        reusable = (receipt["source_sha256"] == sha256(ROOT / "data/training_features.tif")
                    and len(receipt["bands"]) == len(expected_bands)
                    and all(sha256(CACHE_ROOT / row["cache_file"]) == expected
                            for row, expected in zip(receipt["bands"], expected_bands)))
    if not reusable:
        spec = importlib.util.spec_from_file_location("pinned_template57_prepare", ROOT / "vendor/template57/prepare_data.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        receipt = module.cache_bands(CACHE_ROOT)
    actual = [row["sha256"] for row in receipt["bands"]]
    if actual != expected_bands:
        raise ValueError("band hashes do not match the shared template cache; do not train")
    receipt = {**receipt, "shared_template_repository": pin["repository"],
               "shared_template_ref": pin["ref"], "all_19_template_band_hashes_match": True,
               "cache_reused": reusable,
               "organizer_origin_authenticated": False,
               "provenance": "Hash-pinned public owner mirror; not independently authenticated organizer data."}
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/shared_feature_cache.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(f"{'Reused' if reusable else 'Prepared'} 19 template bands; all 19 hashes match", flush=True)
    return receipt


if __name__ == "__main__":
    prepare()
