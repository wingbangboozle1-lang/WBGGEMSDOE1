#!/usr/bin/env python3
"""Verify the exact WBG-2 research download and fail closed on eligibility.

Default exit 2 means local format passed but the file is NOT eligible to submit.
Use --expect-negative in CI to assert that this negative decision reproduces.
No upload, prediction placement or scientific experiment is performed.
"""
from __future__ import annotations
import argparse
import sys
from review_wbg2 import audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--expect-negative", action="store_true", help="exit 0 only when the known negative decision is reproduced")
    mode.add_argument("--format-only", action="store_true", help="compatibility alias; format success is not upload approval")
    args = parser.parse_args()
    try:
        result = audit()
    except Exception as error:
        print(f"FAIL: unable to reproduce audit: {error}", file=sys.stderr)
        return 1
    valid = result["validator_output"]["all_checks_passed"] and result["validator_output"]["zip_exact_single_identical_tiff"]
    stopped = (not result["ok_to_submit"] and result["verdict"] == "negative"
               and any(r["duplicate_by_overlap"] or r["duplicate_by_rho"] for r in result["registry"]["rows"]))
    if not (valid and stopped):
        print("FAIL: exact format or required negative decision did not reproduce", file=sys.stderr)
        return 1
    print("FORMAT: PASS (local only) · LITERAL UNIQUENESS: FAIL · HOLDOUT: NOT AVAILABLE")
    print("DOWNLOAD: YES for research · SUBMIT: NO · no weekly slot used")
    return 0 if args.expect_negative or args.format_only else 2


if __name__ == "__main__":
    raise SystemExit(main())
