#!/usr/bin/env python3
"""Byte-level check of the nine focus-site files named in the standing brief.

Reads the nine GEMSDOE public repositories (shallow clones, passed as --clones DIR,
each named exactly like its GitHub repo, e.g. DIR/GEMSDOE32) plus the WBG-6 file and
the pinned mapped-fault catalogue. For every named file it records SHA-256, dot count,
outside-footprint convention, pixel-exact subset relations, catalogue proximity, and
the literal and density-free uniqueness overlaps. Writes a JSON receipt.

Scores are NOT computed here. The 0.xxxx values are USER-REPORTED (not
ORGANIZER-CONFIRMED) and are copied from the standing brief as labels only.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]

# (site, user-reported score label, glob inside clone for the exact named file)
NAMED = [
    ("GEMSDOE24", "0.2477", "*h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
    ("GEMSDOE25", "0.2600", "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
    ("GEMSDOE27", "0.2449", "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"),
    ("GEMSDOE28", "0.2710", "gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif"),
    ("GEMSDOE28", "0.2708", "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif"),
    ("GEMSDOE30", "0.2600", "gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif"),
    ("GEMSDOE31", "0.2708", "gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif"),
    ("GEMSDOE32", "0.2778", "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"),
    ("GEMSDOE33", "0.2632", "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e-nanoutside.tif"),
    ("GEMSDOE36", "0.2750", "gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif"),
]
WBG6 = ROOT / "docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif"
CATALOGUE = ROOT / "data/bridge/labels.tif"          # label==1 is the mapped fault catalogue
FOOTPRINT = ROOT / "data/bridge/sample_submission.tif"  # NaN outside the GeoDAWN footprint
SAMPLE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
R13 = "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"  # inside GEMSDOE24


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        return ds.read(1).astype("float64")


def dot_pixels(a: np.ndarray) -> np.ndarray:
    return np.column_stack(np.where(np.isfinite(a) & (a > 0))).astype(float)


def forward_within3(a: np.ndarray, b: np.ndarray) -> float:
    """Share of dots in `a` with a dot of `b` within 3 px (Euclidean <= 3)."""
    if len(a) == 0 or len(b) == 0:
        return 0.0
    d, _ = cKDTree(b).query(a, k=1)
    return float((d <= 3.0).mean())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clones", required=True, type=Path)
    ap.add_argument("--out", default=ROOT / "evidence/nine_sites_bytes_20261028.json", type=Path)
    args = ap.parse_args()

    assert sha256(FOOTPRINT) == SAMPLE_SHA, "footprint sample hash changed; refuse to run"
    fp = np.isfinite(read(FOOTPRINT))
    cat = np.column_stack(np.where(read(CATALOGUE) == 1)).astype(float)
    cat_tree = cKDTree(cat)
    w6 = read(WBG6)
    w6_pts = dot_pixels(w6)
    r13_path = args.clones / "GEMSDOE24" / R13
    r13_pts = dot_pixels(read(r13_path)) if r13_path.exists() else None

    rows: list[dict] = []
    bool_masks: dict[str, np.ndarray] = {}   # keyed by named-file label for subset tests
    pts_by_label: dict[str, np.ndarray] = {}
    for site, score, pattern in NAMED:
        label = f"{site}:{score}:{pattern}"
        hits = sorted(glob.glob(str(args.clones / site / "**" / pattern), recursive=True))
        if len(hits) != 1:
            rows.append({"site": site, "user_reported_score": score, "pattern": pattern,
                         "status": f"NOT FOUND or ambiguous ({len(hits)} matches)"})
            continue
        p = Path(hits[0])
        a = read(p)
        pts = dot_pixels(a)
        pts_by_label[label] = pts
        bool_masks[label] = np.isfinite(a) & (a > 0)
        fin = np.isfinite(a)
        outside = ~fp
        d_cat, _ = cat_tree.query(pts, k=1)
        rows.append({
            "site": site,
            "user_reported_score": score,
            "label": "USER-REPORTED (not ORGANIZER-CONFIRMED)",
            "file": str(p.relative_to(args.clones)),
            "sha256": sha256(p),
            "nan_pixels": int(np.isnan(a).sum()),
            "outside_footprint_all_nan": bool(np.isnan(a[outside]).all()),
            "outside_footprint_all_zero": bool((a[outside] == 0).all()),
            "footprint_matches_sample": bool(np.array_equal(fin, fp)),
            "min": float(np.nanmin(a)), "max": float(np.nanmax(a)),
            "unique_values": sorted(float(v) for v in np.unique(a[fin])),
            "dots": int(len(pts)),
            "on_catalogue_exact": int((d_cat == 0).sum()),
            "within3px_of_catalogue": round(float((d_cat <= 3).mean()), 4),
            "_label": label,
        })

    ref_label = next((k for k in bool_masks if k.startswith("GEMSDOE32:")), None)  # the 0.2778 file
    for r in rows:
        if "_label" not in r:
            continue
        label = r.pop("_label")
        pts = pts_by_label[label]
        r["forward3px_vs_WBG6"] = round(forward_within3(pts, w6_pts), 4)  # this file's dots near a WBG-6 dot
        r["WBG6_dots_within3px_of_this_file"] = round(forward_within3(w6_pts, pts), 4)
        if r13_pts is not None:
            r["forward3px_vs_r13_lattice"] = round(forward_within3(pts, r13_pts), 5)
        if ref_label is not None and not label.startswith("GEMSDOE32:"):
            r["forward3px_vs_GEMSDOE32_0.2778"] = round(forward_within3(pts, pts_by_label[ref_label]), 4)
            ref_m, this_m = bool_masks[ref_label], bool_masks[label]
            r["pixel_exact_share_of_GEMSDOE32_dots_present_here"] = round(float((ref_m & this_m).sum() / ref_m.sum()), 4)
            r["pixel_exact_share_of_this_file_dots_in_GEMSDOE32"] = round(float((ref_m & this_m).sum() / this_m.sum()), 4)

    receipt = {
        "schema": "nine-sites-bytes-v1",
        "generated_by": "scripts/verify_nine_sites_bytes.py",
        "label_note": "Scores are copied user-reported labels. Overlaps are measured on the bytes.",
        "literal_gate": "forward share of a file's dots within 3 px of a registry raster's dots; STOP if > 0.70",
        "r13_reference": "GEMSDOE24/" + R13,
        "wbg6": {"file": str(WBG6.relative_to(ROOT)), "sha256": sha256(WBG6), "dots": int(len(w6_pts)),
                 "within3px_of_catalogue": round(float((cat_tree.query(w6_pts, k=1)[0] <= 3).mean()), 4),
                 "forward3px_vs_r13_lattice": round(forward_within3(w6_pts, r13_pts), 5) if r13_pts is not None else None},
        "files": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out} with {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
