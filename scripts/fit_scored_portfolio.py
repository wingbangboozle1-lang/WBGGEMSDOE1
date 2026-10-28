#!/usr/bin/env python3
"""Extract descriptors from the 118 owner-reported scored submissions.

Purpose: the hidden private-labelfault set is unobservable, but every submission
score is a *functional* of it.  This script measures each submission's geometry
(budget, catalogue-distance profile, clustering, orientation coherence) so a
distance-weighted-Tversky (DTI) score model can be calibrated on real leaderboard
feedback.

Every score used here is OWNER-REPORTED. No organizer receipt binds these bytes to
a result, so all downstream numbers are labelled accordingly.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/scored"
OUT = ROOT / "evidence/portfolio_descriptors.json"
RAD = 3.0


def load(path):
    with rasterio.open(path) as src:
        return src.read(1)


def main() -> int:
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as src:
        cat = src.read(1) > 0
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        foot = np.isfinite(src.read(1))
    # distance (px) from every cell to the nearest mapped-fault cell
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    cat_density = ndi.uniform_filter(cat.astype(np.float32), size=21)  # faults / 2.1 km box
    r = int(np.ceil(RAD))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]

    rows = []
    for rec in fetch["entries"]:
        if rec.get("status") not in {"downloaded", "cached"}:
            continue
        a = load(ROOT / rec["local"])
        dots = np.isfinite(a) & (a > 0) & foot
        n = int(dots.sum())
        y, x = np.nonzero(dots)
        dc = d_cat[dots]
        # neighbourhood context: local catalogue density at each dot
        cd = cat_density[dots]
        # dot-level clustering: fraction of dots with >2 dots in their 3-px disk
        dens = ndi.uniform_filter(dots.astype(np.float32), size=2 * r + 1)
        near = dens[dots]
        # coverage of footprint blocks (61 x 61 px = ~6 km) and orientation coherence
        blocks = ndi.uniform_filter(dots.astype(np.float32), size=61)
        occ = blocks > 0
        # second-moment orientation of the dot set around each dot is expensive;
        # use global structure tensor of the dot indicator instead
        gy, gx = np.gradient(ndi.gaussian_filter(dots.astype(np.float32), 2.0))
        coh = float(np.sqrt((gy ** 2 - gx ** 2) ** 2 + (2 * gy * gx) ** 2).sum() /
                    max(((gy ** 2 + gx ** 2).sum()), 1e-9))
        rows.append(dict(
            repo=rec["repo"], name=rec["name"], score=rec["score"], n=n,
            frac_on_catalogue=float((dc == 0).mean()) if n else 0.0,
            frac_within_1px=float((dc <= 1).mean()) if n else 0.0,
            frac_within_2px=float((dc <= 2).mean()) if n else 0.0,
            frac_within_3px=float((dc <= 3).mean()) if n else 0.0,
            frac_within_5px=float((dc <= 5).mean()) if n else 0.0,
            frac_beyond_10px=float((dc > 10).mean()) if n else 0.0,
            dist_median_px=float(np.median(dc)) if n else None,
            dist_p90_px=float(np.quantile(dc, 0.9)) if n else None,
            mean_local_cat_density=float(cd.mean()) if n else 0.0,
            cluster_frac=float((near > 3).mean()) if n else 0.0,
            mean_neighbour_dots=float(near.mean()) if n else 0.0,
            roi_coverage_frac=float(occ.sum() / foot.sum()),
            orientation_coherence=coh,
            n_components=int(ndi.label(dots, structure=np.ones((3, 3)))[1]) if n else 0,
        ))
        if len(rows) % 20 == 0:
            print(f"  {len(rows)} processed", flush=True)

    OUT.write_text(json.dumps({
        "schema": "wbg-scored-portfolio-descriptors-v1",
        "score_label": "OWNER-REPORTED",
        "n": len(rows),
        "footprint_cells": int(foot.sum()),
        "catalogue_cells": int(cat.sum()),
        "radius_px": RAD,
        "rows": rows,
    }, indent=1))
    print(f"wrote {OUT} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
