#!/usr/bin/env python3
"""Re-encode the WBG-6 submission with the official outside-footprint convention.

The official rules (docs.nlr.gov 96647, page 967 "Submission format") say the submitted
GeoTIFF must have "data outside the bounds ... null or nan". The pinned sample submission
(data/bridge/sample_submission.tif, sha256 2176d08e...) uses NaN for the 7,111,787 cells
outside the GeoDAWN footprint. This script copies the WBG-6 dots and values byte-for-byte
inside the footprint and writes NaN outside it, then re-opens the result and checks it.

No new dots are placed and no score is produced. The output has the same dot set as
WBG-6, so its uniqueness and literal-gate results are identical to WBG-6's.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif"
SRC_SHA = "e9111de909c6c9669baf71321539e2b30e742334a7dbc66c8ea021d5539401e9"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"
SAMPLE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
OUT_NAME = "wbg6-qmh-kdisjoint-30000-20261028-nan"
OUT = ROOT / "docs/downloads" / f"{OUT_NAME}.tif"
OUT_ZIP = ROOT / "docs/downloads" / f"{OUT_NAME}.zip"
RECEIPT = ROOT / "docs/downloads" / f"{OUT_NAME}.validator.json"
EXPECT_SHAPE = (3730, 3292)
EXPECT_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    assert sha256(SRC) == SRC_SHA, "WBG-6 source bytes changed"
    assert sha256(SAMPLE) == SAMPLE_SHA, "sample submission bytes changed"

    with rasterio.open(SAMPLE) as s:
        footprint = np.isfinite(s.read(1))
        sample_profile = s.profile
    with rasterio.open(SRC) as src:
        a = src.read(1).astype("float32")
        profile = src.profile.copy()
        src_crs, src_tr = src.crs, src.transform
    assert a.shape == EXPECT_SHAPE and footprint.shape == EXPECT_SHAPE
    assert not (a[~footprint] != 0).any(), "WBG-6 has non-zero values outside the footprint"
    assert ((a >= 0) & (a <= 1)).all() and np.isfinite(a).all()

    out = a.copy()
    out[~footprint] = np.nan
    profile.update(dtype="float32", nodata=np.nan, count=1, compress="deflate",
                   tiled=True, blockxsize=256, blockysize=256)
    profile.pop("nodata", None)
    profile["nodata"] = float("nan")
    with rasterio.open(OUT, "w", **profile) as dst:
        dst.write(out, 1)
    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(OUT, arcname=OUT.name)

    # Re-open and verify from the written bytes only.
    with rasterio.open(OUT) as ds:
        b = ds.read(1)
        checks = {
            "single_band": ds.count == 1,
            "dtype_float32": ds.dtypes[0] == "float32",
            "crs_epsg_32611": ds.crs is not None and ds.crs.to_epsg() == 32611,
            "shape_matches_sample": ds.shape == EXPECT_SHAPE,
            "transform_matches_sample": tuple(ds.transform)[:6] == EXPECT_TRANSFORM,
            "transform_matches_source": ds.transform == src_tr,
            "footprint_nan_matches_sample": bool(np.array_equal(np.isnan(b), ~footprint)),
            "no_nan_inside_footprint": bool(np.isfinite(b[footprint]).all()),
            "values_in_0_1_inside_footprint": bool(((b[footprint] >= 0) & (b[footprint] <= 1)).all()),
            "no_inf": not np.isinf(b).any(),
            "positives_equal_source": int((b[footprint] > 0).sum()) == int((a > 0).sum()),
            "dots_identical_to_source": bool(np.array_equal(np.nan_to_num(b, nan=0.0) > 0, a > 0)),
        }
    with zipfile.ZipFile(OUT_ZIP) as z:
        members = z.namelist()
        member_ok = members == [OUT.name] and z.read(OUT.name) == OUT.read_bytes()
    checks["zip_exactly_one_identical_member"] = member_ok
    receipt = {
        "name": OUT_NAME,
        "tif": f"docs/downloads/{OUT.name}",
        "tif_sha256": sha256(OUT),
        "tif_bytes": OUT.stat().st_size,
        "zip": f"docs/downloads/{OUT_ZIP.name}",
        "zip_sha256": sha256(OUT_ZIP),
        "source_tif": "docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif",
        "source_sha256": SRC_SHA,
        "footprint_source": "data/bridge/sample_submission.tif (sha256 pinned, NaN outside footprint)",
        "positives": int((a > 0).sum()),
        "outside_footprint_convention": "NaN (official rules p.967: 'data outside the bounds is null or nan')",
        "sample_profile_nodata": str(sample_profile.get("nodata")),
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "label": "FORMAT-CONVENTION VARIANT OF WBG-6; same dots; NOT a new scientific result; NOT cleared to submit",
        "note": "Score unknown. Portal acceptance unknown. Uniqueness identical to WBG-6 (literal 3-px gate fails vs r13, see evidence/literal_gate_degeneracy_20261028.json).",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"all_checks_pass": receipt["all_checks_pass"], "tif_sha256": receipt["tif_sha256"]}, indent=2))
    return 0 if receipt["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
