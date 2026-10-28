#!/usr/bin/env python3
"""How reproducible is a reported score for a nearly-identical raster?

If the owner-reported history is internally consistent, two submissions whose dot
sets overlap heavily must report similar scores.  The overlap-vs-|score gap| curve
therefore measures the *noise floor* of the reported history, and hence the finest
score difference any estimator calibrated on it can resolve.

Also reports the single largest inconsistency (an irregularity for human review).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        foot = np.isfinite(src.read(1))
    dots, names, scores = [], [], []
    for rec in fetch["entries"]:
        with rasterio.open(ROOT / rec["local"]) as src:
            a = src.read(1)
        d = np.isfinite(a) & (a > 0) & foot
        dots.append(d)
        names.append(rec["name"])
        scores.append(float(rec["score"]))
    scores = np.array(scores)
    n = len(dots)
    near = [ndi.binary_dilation(d, structure=np.ones((7, 7), bool)) for d in dots]
    ov = np.zeros((n, n))
    for i in range(n):
        if dots[i].sum() == 0:
            continue
        for j in range(n):
            if i == j:
                ov[i, j] = 1.0
            elif dots[j].sum():
                ov[i, j] = near[j][dots[i]].mean()
    sym = 0.5 * (ov + ov.T)
    iu = np.triu_indices(n, 1)
    o = sym[iu]
    gap = np.abs(scores[iu[0]] - scores[iu[1]])
    bins = [(0.30, 0.50), (0.50, 0.70), (0.70, 0.85), (0.85, 0.95), (0.95, 1.01)]
    print(f"{'overlap band':>14s} {'pairs':>6s} {'median |dscore|':>16s} {'p90':>7s} {'max':>7s}")
    rows = []
    for lo, hi in bins:
        m = (o >= lo) & (o < hi)
        if m.sum():
            print(f"  [{lo:.2f},{hi:.2f}) {m.sum():6d} {np.median(gap[m]):16.4f} "
                  f"{np.quantile(gap[m],0.9):7.4f} {gap[m].max():7.4f}")
            rows.append({"overlap_lo": lo, "overlap_hi": hi, "pairs": int(m.sum()),
                         "median_gap": float(np.median(gap[m])),
                         "p90_gap": float(np.quantile(gap[m], 0.9)),
                         "max_gap": float(gap[m].max())})
    k = int(np.argmax(np.where(o >= 0.95, gap, -1)))
    i, j = iu[0][k], iu[1][k]
    print(f"\nlargest inconsistency at overlap {sym[i,j]:.4f}:")
    print(f"  {names[i]}  score {scores[i]:.4f}")
    print(f"  {names[j]}  score {scores[j]:.4f}")
    out = {"schema": "wbg-score-consistency-v1", "n": n, "bands": rows,
           "largest_inconsistency": {"a": names[i], "b": names[j],
                                     "overlap": float(sym[i, j]),
                                     "score_a": float(scores[i]), "score_b": float(scores[j])}}
    (ROOT / "evidence/score_consistency.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
