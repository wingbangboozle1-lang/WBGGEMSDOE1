#!/usr/bin/env python3
"""EXP-1..3: what emission rule recovers real withheld fault geometry?

Truth models
    S  structural : the distal 30-55 % of every catalogue component is hidden
                    ("the public map is incomplete"); candidates are rebuilt from
                    the kept parts only.
    U  unrelated  : the whole network rigidly translated, as if the missed faults
                    were unrelated structures.  Adversarial control.

Comparators (identical 40,000-dot budget unless stated)
    UNIFORM      uniform random over the footprint           (uninformed null)
    RING         uniform random at 5-30 px from the catalogue (collar null)
    EVIDENCE     top of the LiDAR-scarp composite alone
    TIP          top of the tip/step-over corridor field
    WBG5-CTP2    the shipped artifact
    0.2778 CHAMP the public champion raster, scored as-is

Run:  python scripts/wbg5_run_experiments.py [--tif <shipped artifact>]
Writes docs/data/exp2_holdout.json
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
from scipy.ndimage import distance_transform_edt
from wbg5 import emission, grid, holdout, structure

CHAMP = ROOT / "docs" / "audit" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
SEEDS = {1: (120, -180), 2: (-160, 140), 3: (200, 90)}
BUDGET = 40000


def candidates(cat, fp, kept, d_keep, seed):
    g = structure.segments_from_mask(kept, min_px=8)
    corr, csupp = structure.tip_corridors(g, cat.shape, extend_px=45, start_px=0)
    noch = ~emission.dilate(cat, 1.0)
    u = np.zeros(cat.shape, np.float32)
    u[fp] = np.random.default_rng(500 + seed).random(int(fp.sum())).astype(np.float32)
    out = {
        "UNIFORM": emission.select_isolated(u, fp, BUDGET, 3.0, seed),
        "RING": emission.select_isolated(u, emission.ring(d_keep, 5, 30) & fp, BUDGET, 3.0, seed + 1),
        "TIP": emission.select_isolated(corr, csupp & fp & noch, BUDGET, 3.0, seed + 2),
    }
    try:
        from wbg5.fields import scarp_composite
        lid, ok, _meta = scarp_composite(ROOT / "data" / "external", cat.shape)
        out["EVIDENCE"] = emission.select_isolated(np.where(ok, lid, 0.0), fp & ok, BUDGET, 3.0, seed + 3)
    except FileNotFoundError:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", default=None)
    args = ap.parse_args()

    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    shipped = None
    if args.tif:
        tif = Path(args.tif)
        tif = tif if tif.is_absolute() else ROOT / tif
        with rasterio.open(tif) as ds:
            a = ds.read(1)
        shipped = (np.isfinite(a) & (a > 0), tif.name)
    champ = None
    if CHAMP.exists():
        with rasterio.open(CHAMP) as ds:
            a = ds.read(1)
        champ = np.isfinite(a) & (a > 0)

    acc: dict[str, dict[str, list]] = {}
    for seed, (dy, dx) in SEEDS.items():
        kept, hidden = holdout.structural_split(cat, seed=seed)
        d_keep = distance_transform_edt(~kept).astype(np.float32)
        truth_u = holdout.translated_truth(cat, fp, dy, dx)
        cands = candidates(cat, fp, kept, d_keep, seed)
        if shipped is not None:
            cands[f"WBG5-CTP2 ({shipped[1]})"] = shipped[0]
        if champ is not None:
            cands["0.2778 CHAMPION"] = champ
        for name, pred in cands.items():
            rs = holdout.evaluate(pred, hidden, fp, kept)
            ru = holdout.evaluate(pred, truth_u, fp, kept)
            acc.setdefault(name, {"S": [], "U": [], "cov": [], "halo": []})
            acc[name]["S"].append(rs["dti"])
            acc[name]["U"].append(ru["dti"])
            acc[name]["cov"].append(rs["coverage"])
            acc[name]["halo"].append(emission.halo_covered(hidden, pred))
        print(f"seed {seed}: S truth {int(hidden.sum()):,} px, U truth {int(truth_u.sum()):,} px",
              flush=True)

    rows = []
    for name, v in acc.items():
        s = np.array(v["S"])
        lo, hi = holdout.bootstrap_ci(s, seed=0)
        rows.append({"candidate": name, "structural_dti": round(float(s.mean()), 5),
                     "structural_ci95": [round(lo, 5), round(hi, 5)],
                     "structural_coverage": round(float(np.mean(v["cov"])), 4),
                     "structural_halo_coverage": round(float(np.mean(v["halo"])), 4),
                     "unrelated_dti": round(float(np.mean(v["U"])), 5),
                     "n_replicates": len(v["S"])})
    rows.sort(key=lambda r: -r["structural_dti"])
    doc = {
        "schema": "wbg5-exp2-holdout-v1",
        "evaluator": "gems.metric.dti_components_exact (alpha 0.2, beta 0.8, R = 3 px = 300 m)",
        "truth_models": {
            "structural": "distal 30-55 % of every catalogue component >= 20 px is hidden; "
                          "emitters rebuilt from kept parts only",
            "unrelated": "catalogue translated (dy,dx). Arbitrary adversarial control.",
        },
        "caveat": ("The structural model is favourable to along-strike continuation by "
                   "construction: the hidden tail is collinear with the kept tail. It measures "
                   "'can we recover a structurally removed segment', not the organisers' labels."),
        "rows": rows,
    }
    out = ROOT / "docs" / "data" / "exp2_holdout.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print("\n%-46s %10s %10s" % ("candidate", "S structural", "U unrelated"))
    for r in rows:
        print("%-46s %10.4f %10.4f" % (r["candidate"][:46], r["structural_dti"], r["unrelated_dti"]))
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
