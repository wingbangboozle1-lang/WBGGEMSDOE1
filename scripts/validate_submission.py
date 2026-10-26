#!/usr/bin/env python3
"""Validate a GEMS prediction GeoTIFF against the official sample grid.

Usage:
    python scripts/validate_submission.py candidate.tif sample_submission.tif

The sample raster is used as the authoritative grid and footprint reference. A
successful structural validation is not a score estimate, scientific validation,
or proof of uniqueness. This script never edits the candidate file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(candidate_path: Path, reference_path: Path) -> dict[str, Any]:
    try:
        import numpy as np
        import rasterio
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency. Install requirements with: "
            "python -m pip install -r requirements.txt"
        ) from exc

    errors: list[str] = []
    checks: dict[str, Any] = {}
    if not candidate_path.is_file():
        return {"ok": False, "errors": [f"Candidate file not found: {candidate_path}"]}
    if not reference_path.is_file():
        return {"ok": False, "errors": [f"Reference file not found: {reference_path}"]}

    try:
        with rasterio.open(reference_path) as ref, rasterio.open(candidate_path) as pred:
            ref_data = ref.read(1, masked=False)
            ref_mask = ref.read_masks(1) > 0
            ref_valid = ref_mask & np.isfinite(ref_data)

            checks["candidate"] = {
                "path": str(candidate_path),
                "sha256": sha256_file(candidate_path),
                "crs": pred.crs.to_string() if pred.crs else None,
                "shape": [pred.height, pred.width],
                "transform": list(pred.transform)[:6],
                "band_count": pred.count,
                "dtype": pred.dtypes[0] if pred.count else None,
                "nodata": pred.nodata,
            }
            checks["reference"] = {
                "path": str(reference_path),
                "crs": ref.crs.to_string() if ref.crs else None,
                "shape": [ref.height, ref.width],
                "transform": list(ref.transform)[:6],
                "band_count": ref.count,
                "dtype": ref.dtypes[0] if ref.count else None,
                "footprint_pixels": int(ref_valid.sum()),
            }

            same_crs = pred.crs == ref.crs and pred.crs is not None
            same_shape = (pred.height, pred.width) == (ref.height, ref.width)
            same_transform = pred.transform == ref.transform
            reference_epsg = ref.crs.to_epsg() if ref.crs else None
            pixel_size_100m = (
                abs(abs(ref.transform.a) - 100.0) < 1e-6
                and abs(abs(ref.transform.e) - 100.0) < 1e-6
                and abs(ref.transform.b) < 1e-9
                and abs(ref.transform.d) < 1e-9
            )
            reference_single_band = ref.count == 1
            reference_float32 = ref.dtypes[0] == "float32" if ref.count else False
            checks["reference_single_band"] = reference_single_band
            checks["reference_float32"] = reference_float32
            checks["official_crs_epsg_32611"] = reference_epsg == 32611
            checks["official_resolution_100m"] = pixel_size_100m
            checks["reference_footprint_nonempty"] = bool(ref_valid.any())
            if not reference_single_band or not reference_float32:
                errors.append("Reference must be the official single-band float32 submission grid/template.")
            if reference_epsg != 32611:
                errors.append("Reference grid must use the official EPSG:32611 CRS.")
            if not pixel_size_100m:
                errors.append("Reference grid must use an unrotated 100 m pixel grid.")
            if not ref_valid.any():
                errors.append("Reference raster has no finite, valid footprint pixels.")
            checks["crs_match"] = bool(same_crs)
            checks["shape_match"] = bool(same_shape)
            checks["transform_match"] = bool(same_transform)
            if not same_crs:
                errors.append("CRS must be defined and match the reference raster.")
            if not same_shape:
                errors.append("Raster width and height must match the reference raster.")
            if not same_transform:
                errors.append("Affine transform must exactly match the reference raster.")
            if pred.count != 1:
                errors.append("Candidate must have exactly one raster band.")
            if pred.count != 1:
                checks["band_count_match"] = False
                checks["dtype_is_float32"] = False
                checks["range_0_1_inside_footprint"] = False
                checks["no_nan_inside_footprint"] = False
                checks["mask_valid_inside_footprint"] = False
                checks["outside_footprint_is_null_or_nan"] = False
            else:
                checks["band_count_match"] = True
                checks["dtype_is_float32"] = pred.dtypes[0] == "float32"
                if not checks["dtype_is_float32"]:
                    errors.append("Candidate band dtype must be float32.")

                if same_shape:
                    pred_data = pred.read(1, masked=False)
                    pred_mask = pred.read_masks(1) > 0
                    inside = ref_valid
                    outside = ~inside
                    finite_inside = np.isfinite(pred_data[inside])
                    inside_mask_valid = bool(pred_mask[inside].all())
                    no_nan_inside = bool(finite_inside.all())
                    in_range = bool(
                        finite_inside.all()
                        and inside_mask_valid
                        and (pred_data[inside] >= 0).all()
                        and (pred_data[inside] <= 1).all()
                    )
                    # The footprint exterior must be null/nodata or NaN; infinity
                    # is rejected. A valid-mask exclusion covers declared nodata.
                    outside_ok = bool(
                        ((~pred_mask[outside]) | np.isnan(pred_data[outside])).all()
                        and (~np.isinf(pred_data[outside])).all()
                    )
                    checks["no_nan_inside_footprint"] = no_nan_inside
                    checks["mask_valid_inside_footprint"] = inside_mask_valid
                    checks["range_0_1_inside_footprint"] = in_range
                    checks["outside_footprint_is_null_or_nan"] = outside_ok
                    checks["finite_inside_pixels"] = int(finite_inside.sum())
                    checks["inside_footprint_pixels"] = int(inside.sum())
                    if not no_nan_inside:
                        errors.append("Inside the reference footprint, every prediction must be finite (no NaN/Inf).")
                    if not inside_mask_valid:
                        errors.append("Candidate must not mark any inside-footprint pixel as nodata/masked.")
                    if not in_range:
                        errors.append("Inside the reference footprint, every prediction must be in [0, 1].")
                    if not outside_ok:
                        errors.append("Outside the reference footprint, values must be nodata/null or NaN, not finite predictions or infinity.")
                else:
                    checks["no_nan_inside_footprint"] = None
                    checks["mask_valid_inside_footprint"] = None
                    checks["range_0_1_inside_footprint"] = None
                    checks["outside_footprint_is_null_or_nan"] = None
                    errors.append("Value/footprint checks skipped because candidate and reference shapes differ.")
    except Exception as exc:
        return {
            "ok": False,
            "errors": [f"Unable to read or inspect GeoTIFF: {type(exc).__name__}: {exc}"],
            "candidate_path": str(candidate_path),
            "reference_path": str(reference_path),
        }

    return {"ok": not errors, "errors": errors, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Prediction GeoTIFF to validate (not modified)")
    parser.add_argument("reference", type=Path, help="Official sample submission or equivalent template raster")
    args = parser.parse_args()
    try:
        result = validate(args.candidate, args.reference)
    except RuntimeError as exc:
        result = {"ok": False, "errors": [str(exc)]}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
