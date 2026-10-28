#!/usr/bin/env python3
"""EXP-2: does the independent evidence carry fault-location skill at all?

For each external field the question is narrow and checkable: on the pixels where
that product has data, do mapped faults rank higher than ordinary ground?  A field
with AUC ~ 0.5 is decorative and must not be fused into a submission; a field with
AUC clearly above 0.5 is usable evidence.

The catalogue is the *only* independent truth available, so this is a
"can the surface expression find a mapped fault" test.  It deliberately excludes
12 of the 16 lattice blocks from the statistics and repeats on the other 4, so an
AUC cannot come from one unusually well-mapped corner of the map.

    python scripts/wbg5_test_evidence.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
from scipy.ndimage import distance_transform_edt
from wbg5 import detect, fields, grid

EXT = ROOT / "data" / "external"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/data/exp2_evidence.json")
    args = ap.parse_args()

    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    blocks = detect.block_id()
    rng = np.random.default_rng(3)

    field_set = {}
    comp, valid, meta = fields.scarp_composite(EXT, cat.shape)
    field_set["lidar_scarp_composite"] = (comp, valid, meta)
    for name, fn in (("radiometric_texture", fields.radiometric_texture),
                     ("magnetic_texture", fields.magnetic_texture)):
        try:
            f, v, m = fn(EXT, cat.shape)
            field_set[name] = (f, v, m)
        except FileNotFoundError:
            pass

    # controls: the catalogue-distance prior itself (trivially predictive of the
    # catalogue) and a pure noise field (the null).
    field_set["_control_ring_prior"] = (
        np.exp(-0.5 * (d_cat / 20.0) ** 2).astype(np.float32), fp,
        {"product": "d_cat Gaussian, control only"})
    field_set["_control_noise"] = (
        rng.random(cat.shape).astype(np.float32), fp, {"product": "uniform noise"})

    out = {"schema": "wbg5-evidence-skill-v1",
           "question": "do mapped faults rank higher than ordinary ground on this product?",
           "protocol": ("4 spatial folds; in each, one quarter of the 4x4 lattice is "
                        "scored and the other 12 blocks are ignored; AUC per fold and "
                        "pooled AUC over 250 000 sampled valid pixels per fold"),
           "rows": []}
    pos_all = cat & fp
    for name, (f, valid, meta) in field_set.items():
        support = valid & fp
        rows = []
        ys, ps = [], []
        for b in range(4):
            sel = support & (blocks % 4 == b)
            idx = np.flatnonzero(sel.ravel())
            if idx.size == 0:
                continue
            take = idx[rng.random(idx.size) < min(1.0, 250_000 / idx.size)]
            y = pos_all.ravel()[take].astype(np.int8)
            p = f.ravel()[take]
            ys.append(y)
            ps.append(p)
            rows.append({"block_group": b, "n": int(take.size), "pos": int(y.sum()),
                         "auc": round(detect.auc(y, p), 4)})
        y, p = np.concatenate(ys), np.concatenate(ps)
        pooled = round(detect.auc(y, p), 4)
        rec = {"field": name, "product": meta.get("product"),
               "coverage_of_footprint": round(float((valid & fp).sum() / fp.sum()), 4),
               "auc_by_block_group": rows, "auc_pooled": pooled,
               "auc_mean": round(float(np.nanmean([r["auc"] for r in rows])), 4),
               "n_sampled": int(len(y)), "n_positive": int(y.sum())}
        if not name.startswith("_"):
            rec["verdict"] = ("usable evidence" if pooled >= 0.60 else
                              "weak evidence (below the 0.60 floor)" if pooled >= 0.55 else
                              "no usable skill")
        out["rows"].append(rec)
        print(f"{name:28s} pooled AUC {pooled:.4f}  coverage "
              f"{rec['coverage_of_footprint']:.3f}", flush=True)
    outp = ROOT / args.out
    outp.write_text(json.dumps(out, indent=1) + "\n")
    print("\nwrote", outp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
