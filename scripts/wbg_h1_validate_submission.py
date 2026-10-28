#!/usr/bin/env python3
"""Historical WBG-H1 format diagnostic; never a uniqueness or upload approval.

The former --check-uniqueness option used a private sparse/symmetric subset and
could return success despite a decisive literal all-registry STOP. It is retired.
Use scripts/validate_submission.py for the common exact-file format preflight.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from validate_submission import check_tiff  # noqa: E402
from wbggems1.selector_gate import validate_geotiff_portal_gates  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tif", type=Path, help="Existing research GeoTIFF")
    ap.add_argument("--check-uniqueness", action="store_true", help="Retired: this partial-inventory check cannot clear a lane")
    args = ap.parse_args()
    if args.check_uniqueness:
        print(json.dumps({"uniqueness_cleared": False, "ok_to_submit": False,
            "error": "Retired partial/symmetric novelty gate; use the shared literal registry gate. WBG-H1 is stopped."}))
        return 2
    portal = validate_geotiff_portal_gates(args.tif)
    common = check_tiff(args.tif)
    passed = bool(portal["all_10_gates_passed"] and common["all_checks_passed"])
    print(json.dumps({"historical_format_diagnostic": portal, "common_format_preflight": common,
        "format_passed": passed, "ok_to_submit": False,
        "warning": "Local format only; WBG-H1 is stopped. No registry or slot approval."}, indent=2, allow_nan=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
