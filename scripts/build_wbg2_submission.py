#!/usr/bin/env python3
"""Blocked historical entry point: WBG-2 failed the literal registry gate.

This command cannot regenerate, overwrite, promote or authorize the frozen
artifact. For a reproducible forensic recheck run `python scripts/review_wbg2.py
--check`. The superseded code is preserved as non-executable audit text under
`research/history/wbg2_20261027/`; it is not a supported alternative pipeline.
"""
import sys


def main() -> int:
    print("STOP: WBG-2 is a negative, duplicate-gate research result; no placement or submission is authorized.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
