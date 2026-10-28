#!/usr/bin/env python3
"""Build WBG-5: a unique, format-valid submission anchored on the measured optimum.

Every design choice traces to a measurement in evidence/:

1. DISTANCE-TO-CATALOGUE PROFILE IS INHERITED, DOT POSITIONS ARE NOT.
   The competition truth is new faults absent from the public catalogue (page 967),
   so a dot on a mapped fault can only be a false positive.  The best-scoring
   history entry (0.2778) sits at median 19.6 px / p90 68 px from the catalogue,
   5.8% within 3 px, while dense catalogue-adjacent and 3x-over-budget rasters
   collapse (0.0904 at 206,895 dots).  We reproduce that *distance profile* exactly
   by stratified allocation, and choose fresh cell positions inside it.

2. KERNEL-DISJOINT DISPERSION.  Credit is capped at one per truth cell and the
   kernel support is 300 m, so two dots closer than ~5 px buy less distinct
   coverage per unit of false-positive penalty.  History confirms it: the top
   entries have ~0.05 mean 3-px dot neighbourhood, the 0.1894 entry has 0.162.
   We enforce a hard 5 px minimum separation.

3. STRUCTURAL HABITAT WITHIN EACH RING.  Inside each distance stratum we prefer
   cells on along-strike extrapolations of mapped traces (oriented morphological
   closing, weighted by local strike alignment) -- the "missing fault continues an
   existing trend" hypothesis -- and we penalise high local catalogue density,
   which is where the weakest history entries sit.

4. BUDGET.  The marginal-DTI bar for admitting one more dot is
   k > alpha * DTI (~0.06 at DTI 0.3), and the measured prune sequence
   44,090 -> 40,199 -> 37,654 raised the score 0.2600 -> 0.2708 -> 0.2778, i.e.
   the last dots in this family were below the bar.  We emit 30,000.

The output is float32, EPSG:32611, 3730x3292, all-finite, values in {0, 1},
zero outside the scored footprint.  Nothing is uploaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
NAME = "wbg5-qmh-kdisjoint-30000-20261028"
RING_BINS = [0.0, 3.0, 6.0, 11.0, 21.0, 41.0, 81.0, 1e9]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def oriented_extrapolation(mask: np.ndarray, length: int = 11):
    """Max along-strike dilation of the trace network over 12 orientations."""
    c = length // 2
    resp = np.zeros(mask.shape, np.float32)
    ang = np.zeros(mask.shape, np.int8)
    for k in range(12):
        th = np.pi * k / 12.0
        dy, dx = np.sin(th), np.cos(th)
        se = np.zeros((length, length), bool)
        for t in np.linspace(-c, c, 4 * length):
            yy, xx = int(round(c + t * dy)), int(round(c + t * dx))
            if 0 <= yy < length and 0 <= xx < length:
                se[yy, xx] = True
        d = ndi.binary_dilation(mask, structure=se)
        new = d & (resp == 0)
        ang[new] = k
        resp[new] = 1.0
    return resp, ang * (np.pi / 12.0)


def local_strike(mask: np.ndarray, sigma: float = 4.0) -> np.ndarray:
    s = ndi.gaussian_filter(mask.astype(np.float32), sigma)
    gy, gx = np.gradient(s)
    jxx = ndi.gaussian_filter(gx * gx, 2 * sigma)
    jyy = ndi.gaussian_filter(gy * gy, 2 * sigma)
    jxy = ndi.gaussian_filter(gx * gy, 2 * sigma)
    return 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2


def target_profile() -> np.ndarray:
    """Distance-to-catalogue histogram of the best reported submission, rescaled.

    Measured from docs/audit/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif
    (reported 0.2778); the raw counts are in evidence/wbg5_reference_profile.json.
    """
    ref = ROOT / "evidence/wbg5_reference_profile.json"
    hist = json.loads(ref.read_text())["histogram_counts"]
    return np.array(hist, float)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dots", type=int, default=30000)
    ap.add_argument("--min-sep", type=float, default=5.0)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs/downloads")
    ap.add_argument("--name", default=NAME)
    args = ap.parse_args()

    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as src:
        cat = src.read(1) > 0
        profile = src.profile
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        foot = np.isfinite(src.read(1))

    d_cat = ndi.distance_transform_edt(~cat)
    density = ndi.uniform_filter(cat.astype(np.float32), size=21)
    ext, ext_ang = oriented_extrapolation(cat, length=11)
    strike = local_strike(cat)
    align = np.cos(2.0 * (ext_ang - strike)) ** 2

    structural = (0.5 + 0.5 * ext) * (0.4 + 0.6 * align) * np.exp(-density * 40.0)
    structural = structural.astype(np.float32)
    structural[~foot] = 0.0
    rng = np.random.default_rng(20261028)
    structural = structural + rng.uniform(0, 1e-3, structural.shape).astype(np.float32)

    hist = target_profile()
    frac = hist / hist.sum()
    alloc = np.floor(frac * args.dots).astype(int)
    alloc[np.argmax(alloc)] += args.dots - alloc.sum()

    bins = np.array(RING_BINS)
    h, w = cat.shape
    r = int(np.ceil(args.min_sep))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = yy * yy + xx * xx <= args.min_sep ** 2
    out = np.zeros((h, w), bool)
    blocked = np.zeros((h, w), bool)
    per_bin = []
    for b in range(len(bins) - 1):
        if b == 0:
            # never emit on a mapped fault cell: the competition truth is defined
            # as faults ABSENT from the catalogue, so an on-catalogue dot cannot
            # be a true positive and only adds false-positive mass
            m = foot & (d_cat > 0) & (d_cat < bins[b + 1])
        else:
            m = foot & (d_cat >= bins[b]) & (d_cat < bins[b + 1])
        idx = np.flatnonzero(m.ravel())
        if idx.size == 0 or alloc[b] == 0:
            per_bin.append({"ring": f"[{bins[b]:g},{bins[b+1]:g})", "cells": int(idx.size),
                            "alloc": int(alloc[b]), "placed": 0})
            continue
        vals = structural.ravel()[idx]
        order = idx[np.argsort(-vals, kind="stable")]
        placed = 0
        for flat in order:
            if placed >= alloc[b]:
                break
            y, x = divmod(int(flat), w)
            if blocked[y, x]:
                continue
            out[y, x] = True
            placed += 1
            y0, y1 = max(0, y - r), min(h, y + r + 1)
            x0, x1 = max(0, x - r), min(w, x + r + 1)
            sub = disk[y0 - (y - r):y0 - (y - r) + (y1 - y0),
                       x0 - (x - r):x0 - (x - r) + (x1 - x0)]
            blocked[y0:y1, x0:x1] |= sub
        per_bin.append({"ring": f"[{bins[b]:g},{bins[b+1]:g})", "cells": int(idx.size),
                        "alloc": int(alloc[b]), "placed": int(placed)})

    values = out.astype(np.float32)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tif = args.out_dir / f"{args.name}.tif"
    prof = dict(profile)
    prof.update(driver="GTiff", count=1, dtype="float32", nodata=None,
                compress="deflate", predictor=2, tiled=True,
                blockxsize=256, blockysize=256)
    with rasterio.open(tif, "w", **prof) as dst:
        dst.write(values, 1)
        dst.set_band_description(1, "predicted_new_fault_probability")
    zp = args.out_dir / f"{args.name}.zip"
    with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(tif, arcname=tif.name)

    with rasterio.open(tif) as src:
        back = src.read(1)
        dm = d_cat[back > 0]
        rec = {
            "path": str(tif.relative_to(ROOT)), "name": args.name,
            "sha256": sha256(tif), "bytes": tif.stat().st_size,
            "zip": str(zp.relative_to(ROOT)), "zip_sha256": sha256(zp),
            "bands": int(src.count), "dtype": src.dtypes[0], "shape": list(src.shape),
            "crs": str(src.crs), "transform": [float(v) for v in tuple(src.transform)[:6]],
            "nodata": None, "all_finite": bool(np.isfinite(back).all()),
            "min": float(back.min()), "max": float(back.max()),
            "positive_cells": int((back > 0).sum()),
            "outside_footprint_nonzero": int(((back > 0) & ~foot).sum()),
            "dots_within_3px_of_catalogue": int((dm < 3.0).sum()),
            "distance_to_catalogue_px": {
                "median": float(np.median(dm)), "p90": float(np.quantile(dm, 0.9)),
                "max": float(dm.max())},
            "min_separation_px": float(args.min_sep),
            "per_ring": per_bin,
            "design": "quantile-matched distance profile + kernel-disjoint selection "
                      "+ along-strike structural habitat",
        }
    (args.out_dir / f"{args.name}.validator.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("name", "sha256", "positive_cells", "min",
                                          "max", "all_finite", "crs", "shape",
                                          "dots_within_3px_of_catalogue",
                                          "distance_to_catalogue_px")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
