#!/usr/bin/env python3
"""Read-only geometry of the nine top focus-site files against the public catalogue.

Measures, for each file: dot count, share of dots on mapped catalogue pixels,
median and 90th-percentile Euclidean distance (px, 100 m) from each dot to the
nearest catalogue pixel, and the share of dots within 3 px of the catalogue.
No score is computed here; this only explains how each file sits relative to the
known faults. Usage: python scripts/focus_site_geometry.py <out.json> <tif> [<tif> ...]
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
cat = rasterio.open(ROOT / "data/bridge/existing_faults.tif").read(1) > 0
d_cat = ndi.distance_transform_edt(~cat)
out = []
for p in sys.argv[2:]:
    with rasterio.open(p) as s:
        a = s.read(1)
    dots = (a == 1.0) if np.isin(a, (0.0, 1.0)).all() else None
    if dots is None:
        n = 36800
        flat = a.ravel(); idx = np.argpartition(-flat, n)[:n]
        dots = np.zeros(a.shape, bool); dots.ravel()[idx] = True
    dd = d_cat[dots]
    out.append({"file": Path(p).name, "dots": int(dots.sum()),
                "on_catalogue_share": round(float(cat[dots].mean()), 4),
                "median_dist_to_catalogue_px": round(float(np.median(dd)), 2),
                "p90_dist_to_catalogue_px": round(float(np.percentile(dd, 90)), 2),
                "share_within_3px_of_catalogue": round(float((dd <= 3).mean()), 4),
                "share_within_10px_of_catalogue": round(float((dd <= 10).mean()), 4)})
    print(json.dumps(out[-1]))
Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
Path(sys.argv[1]).write_text(json.dumps({"schema": "gemsdoe1-focus-geometry-v1", "rows": out}, indent=1) + "\n")
