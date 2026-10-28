#!/usr/bin/env python3
"""WBGGEMSDOE1 Holdout CLI Wrapper over Shared `gems.holdout.SegmentHoldout`.

Reuses `src/gems/holdout.py` (`EVALUATOR_VERSION = "gems-segment-pooled-v1"`) and
`scripts/submission_writer.py` without modification (Parallel-Run Protocol Rule 2).

Modes:
  --verify-recorded : Verify immutable SHA-256 locks, 66-ch canary, portal gates, and Run Card.
  --canary          : Run standalone 66-channel `SegmentHoldout.canary()` leakage audit.
  --run-wbg-h1      : Execute the frozen 3-experiment `WBG-H1` (`DPGF-1`) protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbggems1.canary import run_all_feature_canaries  # noqa: E402
from wbggems1.selector_gate import validate_geotiff_portal_gates  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_recorded() -> dict:
    rc_path = ROOT / "evidence" / "wbg_h1" / "run_card.json"
    exp_path = ROOT / "evidence" / "wbg_h1" / "wbg_h1_experiments.json"
    canary_path = ROOT / "evidence" / "wbg_h1" / "leakage_canary_66ch.json"
    prereg_path = ROOT / "evidence" / "wbg_h1" / "preregistration_20261026.json"

    rc = json.loads(rc_path.read_text())
    exp = json.loads(exp_path.read_text())
    canary = json.loads(canary_path.read_text())
    prereg = json.loads(prereg_path.read_text())

    md_sha = _sha256(ROOT / prereg["markdown_path"])
    assert md_sha == prereg["markdown_sha256"], "Preregistration Markdown SHA-256 mismatch"
    assert canary["passed"] is True and canary["max_symmetric_auc"] <= 0.90, "Canary check failed"

    tif_path = ROOT / rc["raster_sha256"]["tif_file"]
    zip_path = ROOT / rc["raster_sha256"]["zip_file"]
    assert _sha256(tif_path) == rc["raster_sha256"]["tif_sha256"], "GeoTIFF SHA-256 mismatch"
    assert _sha256(zip_path) == rc["raster_sha256"]["zip_sha256"], "ZIP SHA-256 mismatch"

    portal = validate_geotiff_portal_gates(tif_path)
    assert portal["all_10_gates_passed"] is True, "Portal 10-gate check failed"
    assert len(rc["submission_note"]) <= 140, "Submission note exceeds 140 characters"

    return {
        "verified": True,
        "preregistration_markdown_sha256": md_sha,
        "canary_max_symmetric_auc": canary["max_symmetric_auc"],
        "selected_arm": exp["selected_arm"],
        "holdout_dti_label": rc["holdout_dti"]["label"],
        "portal_10_gates_passed": portal["all_10_gates_passed"],
        "tif_sha256": rc["raster_sha256"]["tif_sha256"],
        "verdict": rc["verdict"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true", help="Verify recorded WBG-H1 evidence & GeoTIFF")
    ap.add_argument("--canary", action="store_true", help="Run standalone 66-channel leakage canary")
    ap.add_argument("--run-wbg-h1", action="store_true", help="Run frozen 3-experiment WBG-H1 protocol")
    args = ap.parse_args()

    if args.canary:
        print(json.dumps(run_all_feature_canaries(), indent=2))
        return
    if args.run_wbg_h1:
        subprocess.run([sys.executable, "-u", str(ROOT / "scripts" / "run_wbg_h1_experiment.py")], check=True)
        return
    print(json.dumps(verify_recorded(), indent=2))


if __name__ == "__main__":
    main()
