#!/usr/bin/env python3
"""Build the compact uniqueness registry from every obtainable peer raster.

The heavy GeoTIFFs stay outside the repository.  What is committed is a
loss-free sparse encoding of each emission mask (delta + zlib + base64), which
is what the Tier A / Tier B gates actually need.  Round-trip is verified before
the file is written.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
import rasterio
from wbg5 import gates


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True,
                    help="JSON list of {stem, site, score, path} for scored peer rasters")
    ap.add_argument("--extra", nargs="*", default=[],
                    help="additional rasters to register without a score")
    ap.add_argument("--extra-site", default="WBGGEMSDOE1")
    ap.add_argument("--out", default=str(ROOT / "docs/data/registry-fingerprints.json"))
    args = ap.parse_args()

    reg: dict[str, dict] = {}
    shape = None
    for row in json.loads(Path(args.labels).read_text()):
        p = Path(row["path"])
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            arr = ds.read(1).astype("float32")
            shape = arr.shape
        mask = np.isfinite(arr) & (arr > 0)
        if not mask.any():
            continue
        key = row["stem"]
        if key in reg:
            continue
        blob = gates.encode_mask(mask)
        if not np.array_equal(gates.decode_mask(blob, mask.shape), mask):
            raise SystemExit(f"round-trip mismatch for {key}")
        reg[key] = {"site": row.get("site", "?"), "score": row.get("score"),
                    "n_dots": int(mask.sum()), "mask": blob,
                    "mask_sha256": gates.mask_sha(mask),
                    "source_path": str(p.name)}
    for extra in args.extra:
        p = Path(extra)
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            arr = ds.read(1).astype("float32")
            shape = arr.shape
        mask = np.isfinite(arr) & (arr > 0)
        if not mask.any() or p.stem in reg:
            continue
        reg[p.stem] = {"site": args.extra_site, "score": None, "n_dots": int(mask.sum()),
                       "mask": gates.encode_mask(mask), "mask_sha256": gates.mask_sha(mask),
                       "source_path": p.name}

    doc = {
        "schema": "wbg5-registry-fingerprints-v1",
        "grid_shape": list(shape) if shape else None,
        "encoding": "delta-encoded flat pixel indices, zlib, base64 (loss-free)",
        "scored_rasters": sum(1 for r in reg.values() if r["score"] is not None),
        "rasters": reg,
        "scope": ("Every peer raster this sandbox could download and match to a recorded "
                  "owner-reported score, plus explicitly listed extras. Not the organisers' "
                  "full submission history; scores are OWNER-REPORTED."),
    }
    Path(args.out).write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    size = Path(args.out).stat().st_size
    print(f"wrote {args.out} — {len(reg)} rasters, {doc['scored_rasters']} scored, {size/1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
