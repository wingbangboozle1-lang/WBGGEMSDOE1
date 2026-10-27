#!/usr/bin/env python
"""Fail-closed, human-free preflight for the WBG-2 submission download.

Re-opens the exact bytes that a user would download and re-derives every claim
independently of the build script. Exits non-zero if any gate fails.

    PYTHONPATH=src .venv/bin/python scripts/verify_wbg2_download.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg2 import uniqueness as U  # noqa: E402

TIF = ROOT / "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif"
ZIP = ROOT / "docs/downloads/wbg2-offcatalogue-density-36k-20261027.zip"
CARD = ROOT / "evidence/wbg2/run_card.json"
LABELS = ROOT / "data/bridge/labels.tif"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"

EXPECT_SHA = "f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    gates: dict[str, bool] = {}
    detail: dict[str, object] = {}

    gates["tif_exists"] = TIF.is_file()
    gates["zip_exists"] = ZIP.is_file()
    if not (gates["tif_exists"] and gates["zip_exists"]):
        print("FAIL: missing artifact")
        return 2

    got = sha256(TIF)
    gates["sha256_matches_pinned"] = got == EXPECT_SHA
    detail["sha256"] = got

    with rasterio.open(TIF) as src:
        gates["single_band"] = src.count == 1
        gates["dtype_float32"] = src.dtypes[0] == "float32"
        gates["shape_3730x3292"] = (src.height, src.width) == (3730, 3292)
        gates["crs_epsg_32611"] = str(src.crs).upper().endswith("32611")
        artifact_grid = (src.shape, src.crs, src.transform)
        tr = src.transform
        gates["pixel_100m"] = abs(tr.a - 100.0) < 1e-9 and abs(abs(tr.e) - 100.0) < 1e-9
        gates["origin_matches"] = abs(tr.c - 243350.0) < 1e-6 and abs(tr.f - 4508550.0) < 1e-6
        a = src.read(1)

    with rasterio.open(SAMPLE) as src:
        sample_grid = (src.shape, src.crs, src.transform)
        footprint = np.isfinite(src.read(1))
    gates["crs_shape_transform_match_sample"] = artifact_grid == sample_grid

    with rasterio.open(LABELS) as src:
        labels_grid = (src.shape, src.crs, src.transform)
        labels = src.read(1)
    gates["labels_grid_matches_sample"] = labels_grid == sample_grid
    catalogue = labels == 1

    gates["no_nan_anywhere"] = not bool(np.isnan(a).any())
    gates["no_inf_anywhere"] = not bool(np.isinf(a).any())
    inside = a[footprint]
    gates["values_in_0_1"] = float(a.min()) >= 0.0 and float(a.max()) <= 1.0
    gates["in_footprint_finite"] = bool(np.isfinite(inside).all())
    gates["in_footprint_range_0_1"] = float(inside.min()) >= 0.0 and float(inside.max()) <= 1.0
    gates["zero_outside_footprint"] = float(np.abs(a[~footprint]).max()) == 0.0
    pos = a > 0
    gates["has_predictions"] = int(pos.sum()) > 0
    detail["positive_pixels"] = int(pos.sum())
    detail["value_max"] = float(inside.max())

    # the 400 m exclusion actually held, in the shipped file
    excl = U.ndi.binary_dilation(catalogue, U.ndi.generate_binary_structure(2, 1), iterations=4)
    gates["zero_on_catalogue"] = int((pos & catalogue).sum()) == 0
    gates["zero_within_400m_of_catalogue"] = int((pos & excl).sum()) == 0

    with zipfile.ZipFile(ZIP) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        gates["zip_single_member"] = len(names) == 1 and names[0].lower().endswith(".tif")
        inner = z.read(names[0]) if names else b""
    gates["zip_bytes_identical"] = hashlib.sha256(inner).hexdigest() == got

    card = json.loads(CARD.read_text())
    gates["card_sha_matches"] = card["raster_sha256"] == got
    # This is a download-integrity check, not a slot selector. A research artifact
    # must remain explicitly unapproved even when its bytes pass every format gate.
    gates["card_marks_do_not_submit"] = card["decision"]["ok_to_submit"] is False
    gates["estimate_withdrawn"] = card["score_estimate"]["valid_for_submission_decision"] is False
    gates["no_comparable_holdout"] = card["eligibility_gates"]["comparable_holdout_dti_available"] is False
    gates["no_selector_authorization"] = card["eligibility_gates"]["authorized_slot_selector_record"] is False
    gates["note_within_140"] = len(card["submission_note"]) <= 140
    gates["audit_all_nine"] = json.loads(
        (ROOT / "evidence/wbg2/nine_site_uniqueness.json").read_text()
    )["n_audited"] == 9

    for k, v in gates.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(f"\npositive pixels: {detail['positive_pixels']:,}  max value: {detail['value_max']}")
    ok = all(gates.values())
    print("\nPREFLIGHT:", "PASS - research artifact integrity verified; DO NOT SUBMIT" if ok else "FAIL - artifact integrity check failed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
