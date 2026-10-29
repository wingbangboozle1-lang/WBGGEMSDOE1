#!/usr/bin/env python3
"""Verified table for the top user-listed file of each focus site (GEMSDOE24/25/27/28/30/31/32/33/36).

Each user-listed name is matched to a raster in the cloned GitHub repository (never guessed):
the match must be unique. Reported scores are copied from the supplied prompt and are labelled
USER-REPORTED (not organizer-confirmed). Measured values are computed here from the raster bytes.

Output: docs/data/focus9_top_table_20261029.json
Usage:  /tmp/venv/bin/python scripts/focus9_top_table_20261029.py --focus /tmp/focus --candidate <tif>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"

# site, user-listed name key (substring of the file stem), user-reported score, URL from the prompt
TOP = [
    ("GEMSDOE24", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477, "https://buffedlizard55-lab.github.io/GEMSDOE24/"),
    ("GEMSDOE25", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600, "https://buffedlizard55-lab.github.io/GEMSDOE25/"),
    ("GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449, "https://buffedlizard55-lab.github.io/GEMSDOE27/"),
    ("GEMSDOE28", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710, "https://buffedlizard55-lab.github.io/GEMSDOE28/"),
    ("GEMSDOE30", "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600, "https://buffedlizard55-lab.github.io/GEMSDOE30/"),
    ("GEMSDOE31", "h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708, "https://buffedlizard55-lab.github.io/GEMSDOE31/docs/"),
    ("GEMSDOE32", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778, "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html"),
    ("GEMSDOE33", "h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632, "https://buffedlizard55-lab.github.io/GEMSDOE33/"),
    ("GEMSDOE36", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750, "https://buffedlizard55-lab.github.io/GEMSDOE36/docs/"),
]


def _name_matches(stem: str, key: str) -> bool:
    """The user-listed name must END the file stem (so '-nanoutside' siblings do not match)."""
    return stem == key or stem.endswith(key) or stem.endswith(key + "-zeros") or stem.endswith(key + "-nan")


def find_unique(site_dir: Path, key: str):
    """Return (repo_relative_path, bytes) for the single raster whose stem matches the listed name."""
    hits = []
    for p in sorted(site_dir.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        if p.suffix.lower() == ".tif" and _name_matches(p.stem, key):
            hits.append((str(p.relative_to(site_dir)), p.read_bytes(), None))
        elif p.suffix.lower() == ".zip" and _name_matches(p.stem, key):
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    if n.lower().endswith(".tif") and _name_matches(Path(n).stem, key):
                        hits.append((f"{p.relative_to(site_dir)}!{n}", z.read(n), n))
    # de-duplicate identical bytes (a .tif and its zip member are the same submission)
    uniq = {}
    for rel, data, _ in hits:
        uniq.setdefault(hashlib.sha256(data).hexdigest(), (rel, data))
    if len(uniq) != 1:
        return None, [h[0] for h in hits]
    (rel, data), = uniq.values()
    return rel, data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", type=Path, default=Path("/tmp/focus"))
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "docs/data/focus9_top_table_20261029.json")
    args = ap.parse_args()

    with rasterio.open(TEMPLATE) as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(LABELS) as s:
        cat = s.read(1) == 1
    d_cat = distance_transform_edt(~cat)
    with rasterio.open(args.candidate) as c:
        carr = c.read(1)
    cand_pos = np.isfinite(carr) & (carr > 0) & foot
    cand_dots = np.argwhere(cand_pos)

    rows = []
    for site, key, reported, url in TOP:
        rel, data = find_unique(args.focus / site, key)
        row = {"site": site, "user_listed_name": key, "user_reported_score": reported,
               "evidence_class": "USER-REPORTED", "page": url}
        if rel is None:
            row.update(status="NO-UNIQUE-MATCH", matches=data)
            rows.append(row)
            continue
        row["repo_path"] = rel
        row["raster_sha256"] = hashlib.sha256(data).hexdigest()
        row["github_raw_url"] = f"https://github.com/buffedlizard55-lab/{site}/blob/main/{rel.split('!')[0]}"
        with rasterio.MemoryFile(data) as mf, mf.open() as ds:
            a = ds.read(1).astype(np.float64)
            row["crs_epsg"] = ds.crs.to_epsg() if ds.crs else None
            row["shape_ok"] = ds.shape == foot.shape
            row["transform_ok"] = tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
            row["dtype"] = ds.dtypes[0]
        out_conv = a[~foot]
        row["outside_convention"] = "nan" if np.isnan(out_conv).all() else ("zero" if (out_conv == 0).all() else "other")
        ins = a[foot]
        row["inside_finite"] = bool(np.isfinite(ins).all())
        row["inside_range_0_1"] = bool(row["inside_finite"] and ins.min() >= 0 and ins.max() <= 1)
        row["binary_0_1"] = bool(np.isin(ins, [0.0, 1.0]).all())
        pos = np.isfinite(a) & (a > 0) & foot
        row["positive_px"] = int(pos.sum())
        if pos.any():
            dd = d_cat[pos]
            row["min_dist_to_catalogue_m"] = float(dd.min() * 100.0)
            row["share_within_200m_of_catalogue"] = float((dd <= 2.0).mean())
            row["share_on_catalogue"] = float(cat[pos].mean())
            dist, _ = cKDTree(np.argwhere(pos)).query(cand_dots, k=1)
            row["overlap_with_candidate_3px"] = float((dist <= 3.0).mean())
            row["candidate_dots_within_3px_of_this"] = int((dist <= 3.0).sum())
        row["status"] = "MEASURED"
        rows.append(row)

    out = {
        "schema": "focus9-top-table-v1",
        "date_utc": "2026-10-29",
        "candidate": args.candidate.name,
        "candidate_dots": int(cand_pos.sum()),
        "rows": rows,
        "notes": [
            "Reported scores are USER-REPORTED from the supplied prompt, not organizer-confirmed.",
            "overlap_with_candidate_3px = share of candidate dots within 3 px of this raster's positive pixels.",
            "The 200 m share is computed against the USGS/INGENIOUS catalogue in data/bridge/labels.tif.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    for r in rows:
        print({k: r.get(k) for k in ("site", "status", "repo_path", "positive_px", "binary_0_1", "outside_convention", "share_within_200m_of_catalogue", "overlap_with_candidate_3px")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
