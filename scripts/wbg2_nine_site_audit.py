#!/usr/bin/env python3
"""Retired partial audit: use scripts/review_wbg2.py --check instead.

The previous script checked one selected artifact per site, silently skipped
missing/misaligned files, used an incomplete registry, and treated a chance
adjustment as a gate exemption. It cannot grant uniqueness. Historical rows are
kept as scoped diagnostics, not as a promotion audit.
"""
import sys


def main() -> int:
    print("STOP: the nine-champion diagnostic is incomplete and cannot establish uniqueness. Run scripts/review_wbg2.py --check.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
