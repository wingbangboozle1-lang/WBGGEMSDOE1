#!/usr/bin/env python3
"""Report current input integrity AND the stopped scientific lane, independently.

Never download, prepare, train, reset a ledger or authorize a submission here.
A historical receipt is not evidence that ignored input files still exist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def check_file(relative, expected):
    path = ROOT / relative
    actual = None
    if path.is_file():
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=relative, present=actual is not None, sha256=actual,
                expected_sha256=expected, integrity_verified=actual == expected)


def build_report():
    manifest = load("registry/data_manifest.json")
    core = [check_file("data/" + r["dest"], r["sha256"]) for r in manifest["files"]
            if r["dest"] in {"training_features.tif", "labels.tif", "sample_submission.tif"}]
    tools = [check_file(r["path"], r["sha256"]) for r in load("registry/shared_template.json")["files"]]
    cache = []
    receipt_path = ROOT / "data/template57/evidence/feature_cache.json"
    expected = load("registry/template_pins.json")["cached_feature_stack_reference"]["expected_band_sha256"]
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        for r, pin in zip(receipt["bands"], expected):
            path = (ROOT / "data/template57" / r["cache_file"]).resolve()
            # Reject path traversal in a local receipt, including symlink escapes.
            if not path.is_relative_to((ROOT / "data/template57").resolve()):
                raise ValueError("Feature-cache path escapes its root")
            cache.append(check_file(str(path.relative_to(ROOT)), pin))
    inputs_ok = (len(core) == 3 and len(cache) == len(expected) == 19
                 and bool(tools) and all(r["integrity_verified"] for r in core + tools + cache))
    card = load("registry/run_card.json")
    ledger = load("registry/experiment_ledger.json")
    artifact = check_file(card["artifact"], card["raster_sha256"])
    stopped = ledger["status"] == "negative_stopped"
    return dict(schema="wbg-readiness-v2", status="BLOCKED_SCIENTIFIC" if inputs_ok else "BLOCKED_INPUTS",
                core_inputs=core, shared_template=tools, cached_bands=cache,
                inputs_integrity_verified=inputs_ok, organizer_origin_authenticated=False,
                submission_tif_generated=artifact["integrity_verified"], artifact=artifact,
                artifact_role=card["artifact_role"], lane_stopped=stopped,
                experiment_ledger_status=ledger["status"],
                pipeline_ready=False, ok_to_submit=False,
                reason="Existing lane is stopped; no authorized lane/current-best confirmation/slot approval. Data placement alone cannot clear scientific gates.",
                next_action="Retain negative result. Resolve lane and registry protocol centrally; do not rerun or tune the stopped method.",
                limitations=["Input integrity is checked now; holdout and registry results are frozen records, not new measurements.",
                             "The DEM-links CSV is not consumed by the nineteen-band WBG-C1 workflow and is not a prerequisite for this readiness check.",
                             "Owner-mirror hash matches do not establish independent organizer provenance or a competition score."])


def main():
    print(json.dumps(build_report(), indent=2, allow_nan=False))
    return 2  # No state of file placement authorizes resuming this stopped lane.


if __name__ == "__main__":
    raise SystemExit(main())
