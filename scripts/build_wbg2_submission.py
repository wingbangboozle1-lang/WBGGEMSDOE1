#!/usr/bin/env python3
"""Retired WBG-2 generator: deliberately cannot create or approve a submission.

The existing WBG-2 TIFF is retained byte-for-byte as a research artifact. The
lane had no assigned single-method paragraph, lacked the required surface
uniqueness preflight, and hit the literal final-dot overlap STOP. Do not run an
old generator or regenerate pixels to get around those gates. Use
``scripts/verify_wbg2_download.py`` to check the preserved research download.

Reactivation requires a separately authorized lane, a completed surface check
with the pinned shared ``gems57`` tools, and a new prospective run card. This
script intentionally performs no writes and always exits non-zero.
"""
from __future__ import annotations

import json


def main() -> int:
    result = {
        "action": "refused",
        "artifact": "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif",
        "download": "research only",
        "submit": "NO",
        "reason": "WBG-2 lane is stopped; regenerating pixels or bypassing the pre-placement/literal overlap gates is not authorized.",
        "use_instead": "python scripts/verify_wbg2_download.py",
        "files_written": [],
    }
    print(json.dumps(result, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
