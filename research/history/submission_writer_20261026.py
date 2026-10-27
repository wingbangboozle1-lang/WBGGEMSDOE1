#!/usr/bin/env python3
"""Shared strict writer for an aligned NPY or GeoTIFF prediction.

This integration wrapper accepts both ``zero`` and inherited ``zeros`` spelling,
never clips invalid science silently, and embeds the complete shared validator
receipt when requested. The exact upstream CLI is retained at
``scripts/template_submission_writer.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import submission  # noqa: E402


def read_prediction(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        return np.load(path, allow_pickle=False)
    if path.suffix.lower() in {".tif", ".tiff"}:
        with rasterio.open(path) as dataset:
            if dataset.count != 1:
                raise ValueError("Prediction GeoTIFF must have one band")
            return dataset.read(1)
    raise ValueError("Prediction must be an aligned .npy, .tif or .tiff")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prediction", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--template", type=Path, default=ROOT / "data/bridge/sample_submission.tif"
    )
    parser.add_argument("--outside", choices=("zero", "zeros", "nan"), default="zero")
    parser.add_argument("--receipt", type=Path, default=None)
    args = parser.parse_args()
    outside = "zero" if args.outside in {"zero", "zeros"} else "nan"
    prediction = read_prediction(args.prediction)
    submission.write_submission(
        prediction, args.template, args.output, outside=outside
    )
    receipt = submission.check_variants(args.output, args.template)
    text = json.dumps(receipt, indent=2, allow_nan=False) + "\n"
    print(text, end="")
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(text)
    return 0 if receipt["format_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
