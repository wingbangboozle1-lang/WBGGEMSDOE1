#!/usr/bin/env python3
"""Canonical hide-and-recover holdout CLI (protocol rule 2)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems1 import grid, holdout  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--b-visible-px", type=float, default=2.0)
    ap.add_argument("--name", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    _, foot, _ = grid.read_template()
    labels = grid.read_labels()
    ctx = holdout.build_context(foot, labels)
    with rasterio.open(args.candidate) as ds:
        arr = ds.read(1)
    mask = np.isfinite(arr) & (arr > 0) & foot
    rec = holdout.evaluate_mask(
        mask, ctx, b_visible_px=args.b_visible_px, name=args.name or args.candidate.stem
    )
    text = json.dumps(rec, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
