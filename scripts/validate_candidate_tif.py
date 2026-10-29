"""Independent format validator for candidate GeoTIFFs (rasterio only; no builder code).

Usage: python scripts/validate_candidate_tif.py FILE.tif [FILE2.tif ...]
Writes nothing unless --out is given. Exit code 0 only if every file passes all checks.
Checks mirror the official rules: float32 single band, EPSG:32611, reference shape and
transform (data/bridge/sample_submission.tif), no NaN/inf inside the reference footprint,
values in [0, 1] inside the footprint, outside cells zero or NaN, and a submission note
of at most 140 characters when a run card is present.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data/bridge/sample_submission.tif"


def validate(path: Path) -> dict:
    with rasterio.open(REF) as r:
        ref_transform, ref_shape = tuple(r.transform), (r.height, r.width)
        foot = np.isfinite(r.read(1))
    with rasterio.open(path) as d:
        a = d.read(1)
        checks = {
            "single_band_float32": d.count == 1 and d.dtypes[0] == "float32",
            "crs_epsg_32611": d.crs is not None and d.crs.to_epsg() == 32611,
            "shape_matches_reference": (d.height, d.width) == ref_shape,
            "transform_matches_reference": tuple(d.transform) == ref_transform,
            "no_inf_anywhere": bool(np.isfinite(a[np.isfinite(a) | np.isnan(a)]).all()),
            "no_nan_inside_footprint": int(np.isnan(a[foot]).sum()) == 0,
            "values_in_0_1_inside_footprint": bool(((a[foot] >= 0) & (a[foot] <= 1)).all()),
            "outside_footprint_zero_or_nan": bool(np.all((a[~foot] == 0) | np.isnan(a[~foot]))),
        }
    card = path.with_suffix(".json")
    note_ok = True
    if card.exists():
        note = json.loads(card.read_text()).get("submission_note", "")
        checks["note_len_le_140"] = len(note) <= 140
    return {
        "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "positives_in_footprint": int((a[foot] > 0).sum()),
        "checks": checks,
        "all_pass": all(checks.values()) and note_ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    results = [validate(p) for p in args.files]
    text = json.dumps(results, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    return 0 if all(r["all_pass"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
