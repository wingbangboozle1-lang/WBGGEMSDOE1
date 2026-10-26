#!/usr/bin/env python3
"""CLI: score a GeoTIFF/.npy boolean emission on both holdout instruments.

Labels every number as HOLDOUT-DTI (evaluator id, withheld positives, 95% CI).
Usage:
  PYTHONPATH=src python3 scripts/evaluate_holdout.py --input foo.tif [--flank 2.0]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg1 import holdout  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--flank", type=float, default=0.0)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    p = Path(args.input)
    if p.suffix == ".npy":
        mask = np.load(p).astype(bool)
    else:
        mask = holdout.read_binary_tif(p)
    ctx = holdout.load_holdout_context()
    assert mask.shape == ctx.foot.shape, (mask.shape, ctx.foot.shape)
    hr = holdout.evaluate_hide_and_recover(mask, ctx, flank_exclude_px=args.flank,
                                           n_rep=args.reps, seed=args.seed)
    sg = holdout.evaluate_sgmc(mask, ctx, n_rep=args.reps, seed=args.seed)
    out = {
        "input": str(p),
        "hide_and_recover": {
            "HOLDOUT-DTI": hr["pooled"]["DTI"],
            "ci95": hr["ci"]["ci95"],
            "evaluator": hr["evaluator"],
            "n_withheld_total": hr["n_withheld_total"],
            "per_fold_dti": hr["per_fold_dti"],
            "emitted_px": hr["emitted_px"],
        },
        "sgmc": {
            "HOLDOUT-DTI": sg["pooled"]["DTI"],
            "ci95": sg["ci"]["ci95"],
            "evaluator": sg["evaluator"],
            "n_truth": sg["n_truth"],
            "on_catalogue_px": sg["on_catalogue_px"],
        },
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
