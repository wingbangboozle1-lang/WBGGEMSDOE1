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
from gems.validator import sha256_file  # noqa: E402


def read_prediction(path: Path, template: Path | None = None) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        return np.load(path, allow_pickle=False)
    if path.suffix.lower() in {".tif", ".tiff"}:
        with rasterio.open(path) as dataset:
            if dataset.count != 1:
                raise ValueError("Prediction GeoTIFF must have one band")
            if template is None:
                raise ValueError("A reference template is required for GeoTIFF prediction input")
            with rasterio.open(template) as ref:
                if (dataset.shape, dataset.crs, dataset.transform) != (ref.shape, ref.crs, ref.transform):
                    raise ValueError("Prediction GeoTIFF CRS/shape/transform must match the template; metadata cannot be discarded")
                footprint = np.isfinite(ref.read(1))
                mask = submission.raster_mask_report(dataset, footprint)
                if not mask["inside_all_valid"]:
                    raise ValueError("Prediction GeoTIFF has masked values inside the footprint; no silent mask removal")
                if not mask["self_contained"]:
                    raise ValueError("Prediction GeoTIFF depends on sidecar files and is not a single self-contained TIFF")
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
    protected = {args.prediction.resolve(), args.template.resolve()}
    if args.output.resolve() in protected:
        raise ValueError("Output must not overwrite the prediction or reference template")
    if args.receipt and args.receipt.resolve() in protected | {args.output.resolve()}:
        raise ValueError("Receipt must not overwrite a raster input or output")
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    pin = next(row["sha256"] for row in manifest["files"] if row["dest"] == "sample_submission.tif")
    if not args.template.is_file() or sha256_file(args.template) != pin:
        raise ValueError("Reference template is unavailable or does not match the pinned owner mirror")
    prediction = read_prediction(args.prediction, args.template)
    submission.write_submission(
        prediction, args.template, args.output, outside=outside
    )
    receipt = submission.check_variants(args.output, args.template)
    strict = receipt["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    receipt["portal_safe_local_policy"] = bool(receipt["format_valid"] and strict)  # legacy local-only key
    receipt["mirrored_reference_hash_verified"] = True
    receipt["independent_organizer_origin_authenticated"] = False
    receipt["submission_authorized"] = False
    receipt["warning"] = "Local finite-range policy only; organizer acceptance and upload authorization are not established."
    text = json.dumps(receipt, indent=2, allow_nan=False) + "\n"
    print(text, end="")
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(text)
    # NaN compatibility exports are research twins, not strict all-finite local passes.
    return 0 if receipt["portal_safe_local_policy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
