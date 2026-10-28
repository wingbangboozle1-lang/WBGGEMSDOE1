#!/usr/bin/env python3
"""How redundant is the existing nine-site fleet, and how novel is the new file?

The parallel-run protocol stops a lane when more than 70 % of its dots fall within
3 px of one registry raster.  That rule is only meaningful if the registry itself
passes it.  This script measures, with the same code path:

1. pairwise forward 3 px overlap among the nine focus-site best submissions;
2. the same statistic against every localised emission in the registry;
3. the fraction of the new artifact's pixels that no registry raster explains.

Output: docs/data/redundancy.json
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
from scipy.ndimage import distance_transform_edt
from wbg5 import gates, grid

#: the nine focus sites and the submission each one actually reports as its best
NINE = {
    "GEMSDOE24": "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan",
    "GEMSDOE25": "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan",
    "GEMSDOE27": "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan",
    "GEMSDOE28": "gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan",
    "GEMSDOE30": "gems30-MSDB1-edge44090-20261025-e7856ec3f14a",
    "GEMSDOE31": "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan",
    "GEMSDOE32": "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
    "GEMSDOE33": "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e",
    "GEMSDOE36": "gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros",
}


def main() -> int:
    reg = gates.load_registry()["rasters"]
    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    shape = cat.shape

    masks = {k: gates.decode_mask(v["mask"], shape) for k, v in reg.items()}
    present = {site: key for site, key in NINE.items()
               if any(key in k for k in masks)}
    print(f"nine-site best submissions located in the registry: {len(present)}/9")

    pairs = []
    for (s1, k1), (s2, k2) in itertools.permutations(present.items(), 2):
        key1 = next(k for k in masks if k1 in k)
        key2 = next(k for k in masks if k2 in k)
        ov = gates.forward_overlap(masks[key1], masks[key2])
        pairs.append({"from": s1, "to": s2, "forward_overlap_3px": round(ov, 4)})
    vals = [p["forward_overlap_3px"] for p in pairs]
    summary = {
        "n_pairs": len(pairs),
        "median": round(float(np.median(vals)), 4) if vals else None,
        "max": round(float(np.max(vals)), 4) if vals else None,
        "min": round(float(np.min(vals)), 4) if vals else None,
        "pairs_over_0_70": int(sum(v > 0.70 for v in vals)),
        "pairs_over_0_95": int(sum(v > 0.95 for v in vals)),
    }
    print("nine-site internal redundancy:", json.dumps(summary))

    novelty = None
    tif = ROOT / "docs/downloads/wbggemsdoe1-wbg5-ctp3-tip-trace-15px-20261028-60fbe04ce3c1-zeros.tif"
    if tif.exists():
        import rasterio
        with rasterio.open(tif) as ds:
            arr = ds.read(1)
        cand = np.isfinite(arr) & (arr > 0)
        dt = distance_transform_edt(~cand)
        per = {}
        for k, m in masks.items():
            per[k] = float((dt[m] <= gates.HALO_PX).sum() / max(1, int(m.sum())))
        union = np.zeros(shape, bool)
        for m in masks.values():
            union |= distance_transform_edt(~m) <= gates.HALO_PX
        novelty = {
            "candidate_px": int(cand.sum()),
            "explained_by_registry_union": round(float(union[cand].mean()), 4),
            "novel_fraction": round(float(1 - union[cand].mean()), 4),
            "registry_union_footprint_coverage": round(float(union[fp].mean()), 4),
        }
        print("candidate novelty:", json.dumps(novelty))

    doc = {"schema": "wbg5-redundancy-v1",
           "rule": "forward 3 px overlap (fraction of the first raster's pixels within 3 px)",
           "nine_site_best": present, "pairwise": pairs, "summary": summary,
           "candidate_novelty": novelty}
    out = ROOT / "docs/data/redundancy.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
