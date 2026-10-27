#!/usr/bin/env python3
"""Prepare and audit the 66-channel label-free DPGF-1 feature stack on CPU."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbggems1.features import prepare_feature_memmap  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    t0 = time.monotonic()
    meta = prepare_feature_memmap(force=args.force)
    elapsed = round(time.monotonic() - t0, 2)
    print(
        json.dumps(
            {
                "status": "ok",
                "elapsed_seconds": elapsed,
                "shape": meta["shape"],
                "lidar_gap_fraction": meta["lidar_gap_fraction"],
                "hydrothermal_inventory_in_footprint": meta["hydrothermal_inventory_in_footprint"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
