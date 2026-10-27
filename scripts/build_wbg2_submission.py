#!/usr/bin/env python3
"""Retired WBG-2 generator. The lane stopped on the literal registry gate.

The old builder placed dots before checking novelty, exempted dense references,
and issued unsupported approvals.  It must not run again, overwrite the TIFF,
create a new raster, or consume a slot. The original output remains available as
an explicitly negative research artifact; see ``scripts/audit_wbg2_safety.py``.
"""
import sys


def main() -> int:
    print('STOP: WBG-2 failed the literal registry gate. No TIFF was generated; DO NOT SUBMIT.', file=sys.stderr)
    print('Audit only: python scripts/audit_wbg2_safety.py --fetch', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
