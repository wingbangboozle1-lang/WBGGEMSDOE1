#!/usr/bin/env python3
"""Write a portal-safe zeros-mode GeoTIFF and run the strict validator."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems1 import grid, validate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mask_npy", type=Path, help="boolean or float32 HxW array")
    ap.add_argument("out_tif", type=Path)
    ap.add_argument("--outside", choices=("zeros", "nan"), default="zeros")
    ap.add_argument("--receipt", type=Path, default=None)
    args = ap.parse_args()
    mask = np.load(args.mask_npy)
    if mask.dtype == np.bool_ or mask.dtype == bool:
        mask = mask.astype(np.float32)
    else:
        mask = np.clip(mask.astype(np.float32), 0.0, 1.0)
    _, foot, _ = grid.read_template()
    labels = grid.read_labels()
    path = grid.write_geotiff(mask, args.out_tif, footprint=foot, outside=args.outside)
    rec = validate.validate_submission(
        path, footprint=foot, labels=labels, require_all_finite=(args.outside == "zeros")
    )
    print(json.dumps(rec, indent=2))
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(rec, indent=2))
    return 0 if rec["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
