#!/usr/bin/env python3
"""Automated DrivenData Portal & Registry Uniqueness Validator for WBGGEMSDOE1 GeoTIFFs.

Exits 0 iff all 10 portal preflight gates (`float32`, `EPSG:32611`, `3730x3292`, exact
affine geotransform, `0` NaN, `0` Inf, whole-array `[0.0, 1.0]`, `0` exterior nonzeros,
`nodata=None`, `0` `<=200 m` dead-collar waste pixels) pass. Optionally runs full
registry uniqueness (`--check-uniqueness`).
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

from wbggems1.paths import raw_data_dir  # noqa: E402
from wbggems1.selector_gate import (  # noqa: E402
    check_post_placement_uniqueness,
    validate_geotiff_portal_gates,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tif", type=Path, help="Path to single-band submission GeoTIFF")
    ap.add_argument("--check-uniqueness", action="store_true", help="Also run 207-raster uniqueness audit")
    args = ap.parse_args()

    portal = validate_geotiff_portal_gates(args.tif)
    out: dict = {"portal_preflight": portal}

    if args.check_uniqueness:
        with rasterio.open(raw_data_dir() / "sample_submission.tif") as tmpl:
            fp_mask = np.isfinite(tmpl.read(1))
        with rasterio.open(args.tif) as ds:
            arr = ds.read(1)
        uniq = check_post_placement_uniqueness(arr, fp_mask)
        out["uniqueness"] = {
            "passed_competing_and_focus9": uniq["passed_competing_and_focus9"],
            "focus_9_sparse_scope": uniq["focus_9_sparse_scope"],
            "sparse_dot_peers_le_100k_scope": uniq["sparse_dot_peers_le_100k_scope"],
            "competing_methods_scope": uniq["competing_methods_scope"],
            "literal_unseparated_scope": uniq["literal_unseparated_scope"],
        }

    print(json.dumps(out, indent=2))
    if not portal["all_10_gates_passed"]:
        raise SystemExit(1)
    if args.check_uniqueness and not out["uniqueness"]["passed_competing_and_focus9"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
