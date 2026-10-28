#!/usr/bin/env python3
"""EXP-5 (decisive): thin along-strike traces vs dotted rarefaction, on three truths.

Truth models
    ``long``   distal 30-55 % of every catalogue component withheld
    ``short``  distal 10-30 % withheld
    ``unrelated`` the whole network rigidly translated (adversarial: assumes the
               missed faults are structures elsewhere, not continuations)

Candidates (all built from the *kept* catalogue only)
    TRACE-15     1-px along-strike extension, 15 px beyond every tip
    TRACE-30     the same at 30 px
    HEDGE        1-px traces at 15 px plus 25 000 collar dots (5-40 px)
    DOTS-40K     the dotted rarefaction the nine public sites use
    UNIFORM      area-filling null

The reported number is the official metric, so every row is directly comparable
to a leaderboard value in units of DTI — but it is a HOLDOUT-DTI on a synthetic
truth, never a forecast of an organizer score.

    python scripts/wbg5_exp5_decisive.py
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
from wbg5 import emission, grid, holdout, structure
from gems.metric import dti_components_exact


def traces(geom, shape, extend: float = 15.0) -> np.ndarray:
    H, W = shape
    out = np.zeros((H, W), np.float32)
    for seg in geom.segments:
        dy, dx = seg.unit
        for (ty, tx), sgn in ((seg.tip_a, 1.0), (seg.tip_b, -1.0)):
            for k in range(1, int(extend) + 1):
                y = int(round(ty + sgn * k * dy))
                x = int(round(tx + sgn * k * dx))
                if 0 <= y < H and 0 <= x < W:
                    out[y, x] = 1.0
    return out


def dti(pred, truth, valid, kept):
    c = dti_components_exact(pred.astype(np.float32), truth.astype(np.float32),
                             valid_mask=valid.astype(np.uint8),
                             catalogue_mask=kept.astype(np.uint8), alpha=0.2, beta=0.8)
    return float(c["dti"]), float(c["coverage"]), int(pred.sum())


def build_candidates(kept, geom, fp, seed):
    dk = distance_transform_edt(~kept).astype(np.float32)
    near, nc = structure.tip_corridors(geom, kept.shape, extend_px=60, start_px=0)
    far, fc = structure.tip_corridors(geom, kept.shape, extend_px=140, start_px=0, decay=1.0)
    corr = emission.masked_rank(np.maximum(near, far), nc | fc)
    t15 = traces(geom, kept.shape, 15)
    t30 = traces(geom, kept.shape, 30)
    collar = emission.select_isolated(corr, fp & (dk >= 5) & (dk <= 40), 25000, 3.2, seed)
    dots = emission.select_isolated(corr, fp & (dk >= 4), 40000, 3.2, seed + 1)
    u = np.zeros(kept.shape, np.float32)
    u[fp] = np.random.default_rng(90 + seed).random(int(fp.sum())).astype(np.float32)
    return {
        "TRACE-15": t15,
        "TRACE-30": t30,
        "HEDGE_trace15+25k_collar": np.maximum(t15, collar.astype(np.float32)),
        "DOTS-40K": dots.astype(np.float32),
        "UNIFORM": emission.select_isolated(u, fp, 40000, 3.2, seed + 2).astype(np.float32),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/data/exp5_decisive.json")
    args = ap.parse_args()
    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    acc: dict[tuple[str, str], list] = {}
    for regime, frac in (("long", (0.30, 0.55)), ("short", (0.10, 0.30))):
        for seed in (1, 2, 3):
            kept, hidden = holdout.structural_split(cat, seed=seed, frac_range=frac)
            geom = structure.segments_from_mask(kept, min_px=8)
            for name, pred in build_candidates(kept, geom, fp, seed).items():
                d, cov, mass = dti(pred, hidden, fp, kept)
                acc.setdefault((regime, name), []).append((d, cov, mass))
            print(f"structural {regime} seed {seed}", flush=True)
    for seed, (dy, dx) in ((1, (120, -180)), (2, (-160, 140)), (3, (200, 90))):
        truth = holdout.translated_truth(cat, fp, dy, dx)
        kept = cat
        geom = structure.segments_from_mask(cat, min_px=8)
        for name, pred in build_candidates(kept, geom, fp, seed).items():
            d, cov, mass = dti(pred, truth, fp, np.zeros_like(cat))
            acc.setdefault(("unrelated", name), []).append((d, cov, mass))
        print(f"unrelated seed {seed}", flush=True)

    rows = []
    for (regime, name), v in acc.items():
        d = np.array([x[0] for x in v])
        rows.append({"truth": regime, "candidate": name,
                     "holdout_dti": round(float(d.mean()), 4),
                     "worst": round(float(d.min()), 4),
                     "coverage": round(float(np.mean([x[1] for x in v])), 4),
                     "mass_px": int(np.mean([x[2] for x in v]))})
    rows.sort(key=lambda r: (r["truth"], -r["holdout_dti"]))
    doc = {"schema": "wbg5-exp5-decisive-v1",
           "metric": "gems.metric.dti_components_exact, alpha 0.2, beta 0.8, R = 3 px",
           "caveat": ("structural truths are along-strike continuations by construction and "
                      "therefore favour TRACE; the unrelated truth is the opposite extreme. "
                      "Both are reported because a submission is taken once."),
           "rows": rows}
    out = ROOT / args.out
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"\n{'truth':10s} {'candidate':26s} {'DTI':>7s} {'worst':>7s} {'cov':>6s} {'mass':>8s}")
    for r in rows:
        print(f"{r['truth']:10s} {r['candidate']:26s} {r['holdout_dti']:7.4f} "
              f"{r['worst']:7.4f} {r['coverage']:6.3f} {r['mass_px']:8d}")
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
