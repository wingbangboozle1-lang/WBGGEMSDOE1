#!/usr/bin/env python3
"""Build the WBG-5 submission GeoTIFF, its one-file ZIP, and the build receipt.

    python scripts/wbg5_build_submission.py --extend 15

Encoding contract, in full
    driver GTiff, single band, float32, LZW, no nodata tag
    EPSG:32611, 3 730 rows x 3 292 cols, 100 m, transform (100, 0, 243350, 0, -100, 4508550)
    value 1.0 on every emitted trace pixel inside the footprint
    value 0.0 on every other pixel, inside and outside the footprint
    => the array is finite everywhere and lies in [0, 1], which is exactly what the
       portal checks when it answers "Predicted values must be in range [0, 1]".
       Writing NaN outside the footprint (the ``-nan`` files in the sibling
       repositories) is what triggers that error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from wbg5 import emission, grid, structure, trace

OUT = ROOT / "docs" / "downloads"
DATA = ROOT / "docs" / "data"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extend", type=int, default=15)
    ap.add_argument("--min-px", type=int, default=8)
    ap.add_argument("--tag", default="ctp3")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    d_cat = distance_transform_edt(~cat).astype(np.float32)

    geom = structure.segments_from_mask(cat, min_px=args.min_px)
    tf = trace.tip_traces(geom, cat.shape, extend=args.extend)
    mask = tf.mask & fp
    pred = np.where(mask, np.float32(1.0), np.float32(0.0))

    feats = emission.geometry_features(mask, d_cat, cat)
    cid = hashlib.sha256(np.packbits(mask).tobytes()).hexdigest()[:12]
    name = (f"wbggemsdoe1-wbg5-{args.tag}-tip-trace-{args.extend}px"
            f"-20261028-{cid}-zeros.tif")
    payload = {
        "segments": tf.n_segments, "tips": tf.n_tips, "trace_px": tf.n_px,
        "emitted_px": int(mask.sum()), "extend_px": args.extend,
        "strike_hist_top": sorted(geom.strike_hist.items(), key=lambda kv: -kv[1])[:5],
        "features": {k: (round(v, 4) if isinstance(v, float) else v)
                     for k, v in feats.items()},
    }
    print(json.dumps(payload, indent=1))
    print("content-id", cid)
    print("filename", name)
    if args.dry_run:
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    tif = OUT / name
    with rasterio.open(tif, "w", driver="GTiff", dtype="float32", count=1,
                       width=grid.WIDTH, height=grid.HEIGHT, crs=grid.CRS,
                       transform=grid.TRANSFORM, compress="lzw", nodata=None) as dst:
        dst.write(pred, 1)
        dst.update_tags(AREA_OR_POINT="Area", SUBMISSION="WBG5-CTP3",
                        DESIGN=trace.DESIGN["description"],
                        NOTE="1.0 on trace pixels, 0.0 elsewhere; all values finite")
    zpath = tif.with_suffix(".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(tif, arcname=tif.name)
    receipt = {"schema": "wbg5-build-v1", "file": name, "zip": zpath.name,
               "bytes": tif.stat().st_size, "zip_bytes": zpath.stat().st_size,
               "design": trace.DESIGN | {"extend_px": args.extend, "min_px": args.min_px},
               "measured": payload,
               "catalogue_sha256": hashlib.sha256(cat.tobytes()).hexdigest()[:16]}
    (DATA / "wbg5_build.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(f"wrote {tif.name} ({tif.stat().st_size:,} B) and {zpath.name} "
          f"({zpath.stat().st_size:,} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
