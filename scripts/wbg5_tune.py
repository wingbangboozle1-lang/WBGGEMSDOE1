#!/usr/bin/env python3
"""EXP-4: choose the emission geometry with the fleet score model as the objective.

The objective is fitted on 72 real, owner-reported DrivenData evaluations
(``docs/data/fleet-score-model.json``), so it is a statement about what has
actually scored on the live leaderboard — not about what our own holdout likes.
Every candidate here is produced by the same physical generator; only four
parameters move (dot budget, dash spacing, ring shape, corridor weight).

    python scripts/wbg5_tune.py --max-combos 24
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
from scipy.ndimage import distance_transform_edt
from wbg5 import emission, fleet, grid, structure


def ring_weight(d, lo, plo, phi, hi):
    w = np.zeros(d.shape, np.float32)
    a = (d >= lo) & (d < plo)
    w[a] = (d[a] - lo) / max(1e-6, plo - lo)
    w[(d >= plo) & (d <= phi)] = 1.0
    b = (d > phi) & (d <= hi)
    w[b] = (hi - d[b]) / max(1e-6, hi - phi)
    return w


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-combos", type=int, default=24)
    ap.add_argument("--out", default="docs/data/exp4_tuning.json")
    args = ap.parse_args()

    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    n_cat = int((cat > 0).sum())
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    geom = structure.segments_from_mask(cat, min_px=8)
    theta, _ = structure.strike_field(cat.shape, geom)
    near, nc = structure.tip_corridors(geom, cat.shape, extend_px=60, start_px=0)
    far, fc = structure.tip_corridors(geom, cat.shape, extend_px=140, start_px=0, decay=1.0)
    corridor = emission.masked_rank(np.maximum(near, far), nc | fc)

    doc = json.loads((ROOT / "docs/data/fleet-score-model.json").read_text())
    rows = doc["rows"]
    y = np.array([r["score"] for r in rows])
    X = fleet.to_matrix(rows)
    pack = fleet.fit(X, y)
    print(f"objective: {pack['name']} LOO RMSE {pack['loo_rmse']:.4f} on n={len(y)}")

    dots = (42000, 52000)
    spacing = (4.5, 5.5, 6.5)
    rings = ((6, 20, 55, 150), (8, 28, 70, 170), (10, 35, 85, 200))
    corr_w = (0.25, 0.45)
    combos = list(itertools.product(dots, spacing, rings, corr_w))[: args.max_combos]
    out = []
    for i, (nd, sp, ring, cw) in enumerate(combos):
        rw = ring_weight(d_cat, *ring)
        prior = cw * rw + (1 - cw) * corridor
        prior = prior / max(1e-6, prior.max())
        support = fp & (d_cat >= ring[0] * 0.8)
        rank = np.where(support, prior, 0.0).astype(np.float32)
        mask = emission.dash_emit(rank, theta, support & (rank > 0), nd, half=12.0,
                                  step=sp, seed=0, min_sep=sp)
        feats = fleet.geometry(mask, d_cat, cat, n_cat)
        est = fleet.predict(pack, feats)
        rec = {"dots": nd, "spacing": sp, "ring": list(ring), "corridor_weight": cw,
               "n_dots": int(mask.sum()), "estimate": est["estimate"],
               "interval_95": est["interval_95"],
               "line_coherence": round(feats["line_coherence"], 4),
               "nn_p90": round(feats["nn_p90"], 3),
               "clump_frac": round(feats["clump_frac"], 4),
               "frac_le15": round(feats["frac_le15"], 4),
               "frac_le60": round(feats["frac_le60"], 4),
               "dist_p50": round(float(np.median(d_cat[mask])), 2)}
        out.append(rec)
        print(f"{i+1:2d}/{len(combos)} dots={nd} sp={sp} ring={ring} cw={cw}"
              f" -> est {est['estimate']:.4f}  lc {feats['line_coherence']:.3f}"
              f" p50 {rec['dist_p50']:.1f} le15 {rec['frac_le15']:.2f}"
              f" le60 {rec['frac_le60']:.2f}", flush=True)

    out.sort(key=lambda r: -r["estimate"])
    (ROOT / args.out).write_text(json.dumps(
        {"schema": "wbg5-exp4-tuning-v1", "objective": doc["selected"],
         "loo_rmse": doc["loo_rmse"], "combos": out}, indent=1) + "\n")
    print(f"\nbest: {out[0]}")
    print("wrote", ROOT / args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
