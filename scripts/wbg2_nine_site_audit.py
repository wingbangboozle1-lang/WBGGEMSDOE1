#!/usr/bin/env python3
"""Compatibility entry point: delegate to the shared literal WBG-2 safety audit.

The former script's Manhattan/enrichment diagnostic was not a valid gate and
is retired. This command does not overwrite historical records or train/place.
"""
from audit_wbg2_safety import main

if __name__ == '__main__':
    raise SystemExit(main())
