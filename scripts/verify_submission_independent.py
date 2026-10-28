#!/usr/bin/env python3
"""Independent re-check of a candidate submission GeoTIFF against the official template.

Deliberately does NOT import the repo's shared validator (vendor/gems57/validate.py), so a
defect in that validator cannot hide a defect in the file. Every check is a plain rasterio/numpy
comparison to the official template rules quoted in the receipt. A PASS here is a local format
check, not organizer acceptance and not a uniqueness clearance.

Usage:
    .venv/bin/python scripts/verify_submission_independent.py <tif> [--out evidence/x.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
OFFICIAL_RULE = (
    "Your submission contains a single layer with datatype of 32-bit float (`float32`) with values "
    "between 0 and 1 ...; Your submission has the same bounds as the training data, and data outside "
    "the bounds is null or nan."
)
OFFICIAL_SOURCES = [
    "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
    "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tif", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    with rasterio.open(args.tif) as ds, rasterio.open(TEMPLATE) as tp, rasterio.open(LABELS) as lb:
        a = ds.read(1)
        tmpl = tp.read(1)
        labels = lb.read(1)
        meta = {
            "count": ds.count,
            "dtype": ds.dtypes[0],
            "crs": str(ds.crs),
            "shape": [ds.height, ds.width],
            "transform": list(ds.transform)[:6],
            "nodata": ds.nodata,
        }
        template_meta = {
            "crs": str(tp.crs),
            "shape": [tp.height, tp.width],
            "transform": list(tp.transform)[:6],
        }

    template_footprint = ~np.isnan(tmpl)  # official template: NaN marks outside-bounds
    labels_footprint = labels != -1  # labels raster: -1 marks outside (checked below)
    footprint_agrees = bool(np.array_equal(template_footprint, labels_footprint))

    finite = np.isfinite(a)
    inside = template_footprint
    checks = {
        "single_band_float32": meta["count"] == 1 and meta["dtype"] == "float32",
        "crs_matches_template": meta["crs"] == template_meta["crs"],
        "shape_matches_template": meta["shape"] == template_meta["shape"],
        "transform_matches_template": np.allclose(meta["transform"], template_meta["transform"]),
        "no_inf": bool(not np.isinf(a).any()),
        "inside_footprint_all_finite": bool(finite[inside].all()),
        "inside_footprint_in_0_1": bool(((a[inside] >= 0) & (a[inside] <= 1)).all()),
        # Either convention is accepted; the file must use exactly one of them consistently.
        "outside_footprint_consistent_nan_or_zero": bool(
            np.isnan(a[~inside]).all() or (a[~inside] == 0).all()
        ),
        "footprint_mask_labels_equals_template": footprint_agrees,
    }
    catalogue_pos = int((a[labels > 0] > 0).sum())
    outside_convention = (
        "nan" if np.isnan(a[~inside]).all() else ("zero" if (a[~inside] == 0).all() else "mixed")
    )
    result = {
        "file": str(args.tif),
        "sha256": sha256(args.tif),
        "bytes": args.tif.stat().st_size,
        "meta": meta,
        "template_meta": template_meta,
        "inside_footprint_cells": int(inside.sum()),
        "positive_cells": int((a > 0).sum()),
        "n_nan_total": int(np.isnan(a).sum()),
        "min_inside": float(np.nanmin(a[inside])) if inside.any() else None,
        "max_inside": float(np.nanmax(a[inside])) if inside.any() else None,
        "positives_on_public_catalogue": catalogue_pos,
        "outside_footprint_convention": outside_convention,
        "checks": checks,
        "checks_pass_locally": bool(all(checks.values())),
        "template_convention_note": (
            "Official template marks outside-bounds cells NaN. Zero outside is accepted here only as a "
            "consistent alternative; NaN outside matches the official template exactly. Manual review."
        ),
        "official_rule_quoted": OFFICIAL_RULE,
        "official_sources": OFFICIAL_SOURCES,
        "validation_class": "independent local format check; not organizer acceptance, not uniqueness",
    }

    # Irregularity probe on the mirrored sample: the official page calls it an all-absence sample.
    tmpl_ones = int(((tmpl == 1)).sum())
    result["template_mirror_probe"] = {
        "template_cells_equal_1": tmpl_ones,
        "labels_positive_cells": int((labels > 0).sum()),
        "template_ones_equal_public_catalogue": bool(np.array_equal(tmpl == 1, labels > 0)),
        "irregularity": (
            "Official page says the sample predicts total fault absence, yet the mirrored sample's 1-cells "
            "coincide exactly with the public catalogue. Verify against the organizer's own file."
        ),
    }

    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    print(text, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    return 0 if result["checks_pass_locally"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
