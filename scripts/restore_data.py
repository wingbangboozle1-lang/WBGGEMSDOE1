#!/usr/bin/env python3
"""Restore core inputs through the unchanged template's hash-pinned GitHub bridge.

A hash match authenticates mirror integrity, NOT organizer origin. No DrivenData
password, token, or weekly submission slot is used. Large inputs remain ignored.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from wbggems.audit import dump_json, sha256, utc_now


def restore():
    spec = importlib.util.spec_from_file_location("pinned_template_prepare", ROOT / "vendor/template57/prepare_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    files = []
    for entry in manifest["files"]:
        if entry["dest"] not in {"training_features.tif", "labels.tif", "sample_submission.tif"}:
            continue
        dest = ROOT / "data" / entry["dest"]
        if not dest.exists() or sha256(dest) != entry["sha256"]:
            if entry["dest"] == "training_features.tif":
                module.assemble_features(ROOT)
                dest.unlink(missing_ok=True)
                dest.symlink_to("official/training_features.tif")
            else:
                source = "example_submission.tif" if entry["dest"] == "sample_submission.tif" else "existing_faults.tif"
                module.fetch_raw(module.BRIDGE_REPO, f"data/bridge/{source}", module.BRIDGE_COMMIT,
                                 dest, entry["sha256"])
        if sha256(dest) != entry["sha256"]:
            raise ValueError(f"integrity mismatch: {dest}")
        files.append({"file": entry["dest"], "bytes": dest.stat().st_size,
                      "sha256": entry["sha256"], "verified": True,
                      "organizer_origin_authenticated": False})
    # load_grid's existing_faults is just the same public catalogue, not new truth.
    alias = ROOT / "data/existing_faults.tif"
    if not alias.exists():
        alias.symlink_to("labels.tif")
    report = {"generated_utc": utc_now(), "files": files, "all_verified": True,
              "evidence_class": "OWNER-MIRROR-INTEGRITY",
              "provenance": "Public owner GitHub bridge, restored using the unmodified pinned template. Not a DrivenData-origin receipt."}
    dump_json(ROOT / "evidence/data_restore.json", report)
    print("Core data integrity verified; organizer-origin authentication remains unavailable.")
    return report


if __name__ == "__main__":
    restore()
