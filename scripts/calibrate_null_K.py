#!/usr/bin/env python3
"""Calibrate the hidden-truth size K on a provably uniform submission, then
validate the null-truth estimator against the reported history.

Step 1. ``r13-lattice-s5`` is a 5 px lattice: its distance-to-catalogue quantiles
        match the footprint's to within 0.1 px, so its score is a function of K
        alone.  Bisect K until the ensemble-mean DTI reproduces the reported 0.0904.
Step 2. With that K, predict the reported score of every other submission sample
        and measure the rank agreement.  This is the estimator's external check.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from wbg6.null_model import expected_dti  # noqa: E402


def load(name, fetch, foot):
    for r in fetch["entries"]:
        if r["name"] == name:
            with rasterio.open(ROOT / r["local"]) as s:
                a = s.read(1)
            v = np.where(foot, np.nan_to_num(a, nan=0.0), 0.0).astype(np.float32)
            return v, float(r["score"])
    raise KeyError(name)


def main() -> int:
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as s:
        cat = s.read(1) > 0
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())

    r13, s13 = load("20261001_r13-lattice-s5_v2_nan-outside", fetch, foot)
    print(f"target: reported {s13:.4f} for a uniform lattice", flush=True)
    curve = []
    lo, hi = 4000, 40000
    for _ in range(5):
        K = int(round(np.sqrt(lo * hi)))
        r = expected_dti(r13, cat, foot, K, draws=24, seed=17)
        curve.append({"K": K, **r})
        print(f"  K={K:6d} -> DTI {r['mean']:.4f} +/- {r['se']:.4f}", flush=True)
        if r["mean"] > s13:
            hi = K
        else:
            lo = K
    # linear interpolation in log K on the bracket
    pts = sorted([(c["K"], c["mean"]) for c in curve])
    Kstar = int(round(np.exp(np.interp(s13, [p[1] for p in pts], np.log([p[0] for p in pts])))))
    print(f"\nK* ~ {Kstar:,} hidden-truth cells", flush=True)

    rep = expected_dti(r13, cat, foot, Kstar, draws=40, seed=23)
    print(f"  r13 check: predicted {rep['mean']:.4f} +/- {rep['se']:.4f} vs reported {s13:.4f}")

    sample = [
        "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
        "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros",
        "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan",
        "h27-4-solo-d28-20261004-8acb75e1-nan",
        "h33d-analog-tip-stepover-r30-20261004-cb490425926e",
        "dotted-h19-5-d2-8-20261002-e56ea318af89-nan",
        "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan",
        "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan",
        "gate_ortho_w0.25-40k-20261006T213721Z-nan",
        "gems70-p5-dual-submod300-oof38k-20261020",
        "h19-4-reference-20260930-691e4dfa",
        "gems-submission-20260925T001403Z-7f00890a",
        "h28-dotted-ridge-20260928T020256236880Z-6452ae1d00",
        "lidarscarp-ridge-top2pct-36c3a3f341c8",
    ]
    rows = []
    for nm in sample:
        v, s = load(nm, fetch, foot)
        r = expected_dti(v, cat, foot, Kstar, draws=18, seed=31)
        rows.append({"name": nm, "reported": s, "predicted": r["mean"],
                     "se": r["se"], "n_dots": int((v > 0).sum())})
        print(f"  {nm[:52]:52s} reported {s:.4f}  predicted {r['mean']:.4f} "
              f"+/- {r['se']:.4f}", flush=True)
    from scipy.stats import pearsonr, spearmanr
    a = np.array([r["reported"] for r in rows])
    b = np.array([r["predicted"] for r in rows])
    print(f"\nvalidation (n={len(rows)}): Pearson {pearsonr(a,b)[0]:+.3f}, "
          f"Spearman {spearmanr(a,b)[0]:+.3f}")
    out = {"schema": "wbg6-null-calibration-v1", "K_star": Kstar,
           "calibration_curve": curve, "r13_check": rep,
           "r13_reported": s13, "validation": rows,
           "pearson": float(pearsonr(a, b)[0]), "spearman": float(spearmanr(a, b)[0]),
           "assumption": "truth = K fault cells in catalogue-like segments, uniform "
                         "location/orientation, never on a mapped fault cell",
           "evidence_class": "MODEL-ESTIMATE"}
    (ROOT / "evidence/wbg6_null_calibration.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
