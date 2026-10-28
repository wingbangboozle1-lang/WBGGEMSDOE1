#!/usr/bin/env python3
"""EXP-4: sweep the along-strike continuation length and report every regime.

Fourteen lengths from 4 to 40 px, three independent distal-truncation truths, plus
the adversarial translated truth.  The reported statistic is the official metric,
so the table reads directly in DTI units.  This is the experiment that fixes the
shipped parameter at 15 px.

    python scripts/wbg5_extend_sweep.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
from wbg5 import grid, holdout, structure, trace
from gems.metric import dti_components_exact

LENGTHS = (4, 6, 8, 10, 12, 15, 18, 22, 30, 40)
REGIMES = {"long": (0.30, 0.55), "short": (0.10, 0.30)}


def score(pred, truth, valid, kept) -> float:
    return float(dti_components_exact(pred.astype(np.float32), truth.astype(np.float32),
                                      valid_mask=valid.astype(np.uint8),
                                      catalogue_mask=kept.astype(np.uint8),
                                      alpha=0.2, beta=0.8)["dti"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/data/extend_sweep.json")
    args = ap.parse_args()
    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    acc: dict[tuple[str, int], list] = {}
    for regime, frac in REGIMES.items():
        for seed in (1, 2, 3):
            kept, hidden = holdout.structural_split(cat, seed=seed, frac_range=frac)
            geom = structure.segments_from_mask(kept, min_px=8)
            for ext in LENGTHS:
                tf = trace.tip_traces(geom, cat.shape, extend=ext)
                acc.setdefault((regime, ext), []).append(score(tf.mask, hidden, fp, kept))
            print(f"{regime} seed {seed}", flush=True)
    for seed, (dy, dx) in ((1, (120, -180)), (2, (-160, 140)), (3, (200, 90))):
        truth = holdout.translated_truth(cat, fp, dy, dx)
        geom = structure.segments_from_mask(cat, min_px=8)
        for ext in LENGTHS:
            tf = trace.tip_traces(geom, cat.shape, extend=ext)
            acc.setdefault(("unrelated", ext), []).append(
                score(tf.mask, truth, fp, np.zeros_like(cat)))
    rows = []
    for (regime, ext), v in acc.items():
        d = np.array(v)
        rows.append({"truth": regime, "extend_px": ext,
                     "dti_mean": round(float(d.mean()), 4),
                     "dti_worst": round(float(d.min()), 4)})
    rows.sort(key=lambda r: (r["truth"], r["extend_px"]))
    by_ext: dict[int, list] = {}
    for r in rows:
        if r["truth"] != "unrelated":
            by_ext.setdefault(r["extend_px"], []).append(r["dti_mean"])
    maximin = max(by_ext.items(), key=lambda kv: (min(kv[1]), sum(kv[1])))[0]
    doc = {"schema": "wbg5-extend-sweep-v1",
           "lengths_px": list(LENGTHS), "regimes": list(REGIMES) + ["unrelated"],
           "maximin_length_px": maximin, "rows": rows}
    (ROOT / args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"\n{'truth':10s} " + " ".join(f"{e:>6d}" for e in LENGTHS))
    for regime in list(REGIMES) + ["unrelated"]:
        vals = {r["extend_px"]: r["dti_mean"] for r in rows if r["truth"] == regime}
        print(f"{regime:10s} " + " ".join(f"{vals[e]:6.4f}" for e in LENGTHS))
    print(f"\nmaximin over the two structural regimes: {maximin} px -> shipped")
    print("wrote", ROOT / args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
