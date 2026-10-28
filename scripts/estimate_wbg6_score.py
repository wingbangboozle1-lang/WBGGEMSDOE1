#!/usr/bin/env python3
"""Score estimate for the WBG-6 submission, and the limits of that estimate.

Two numbers are reported, never mixed:

  NULL-FLOOR   the ensemble-mean DTI of the raster against the calibrated
               uniform-truth null (K = 12,415 cells in catalogue-like segments,
               uniformly placed).  This is a *validated* forward model: it
               reproduces the reported 0.0904 of the uniform 5 px lattice to
               within 0.0001.  Any raster with no localisation skill lands here.

  MODEL-ESTIMATE  the null prediction multiplied by the *localisation uplift*
               measured on the reported history (reported score / null
               prediction).  The uplift is what a real fault prior buys, and it
               is not a property of geometry -- it cannot be derived from a raster
               without the hidden labels.  Its spread over the history is the
               honest uncertainty of the estimate.

No number here is an organizer result.
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

NAME = "wbg6-qmh-kdisjoint-30000-20261028"


def main() -> int:
    cal = json.loads((ROOT / "evidence/wbg6_null_calibration.json").read_text())
    K = int(cal["K_star"])
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as s:
        cat = s.read(1) > 0
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "docs/downloads" / f"{NAME}.tif") as s:
        mine = s.read(1)

    null = expected_dti(mine, cat, foot, K, draws=40, seed=101)
    rows = [r for r in cal["validation"] if r["predicted"] > 0]
    uplift = np.array([r["reported"] / r["predicted"] for r in rows])
    out = {
        "schema": "wbg6-score-estimate-v1",
        "submission": NAME,
        "K_star_truth_cells": K,
        "null_floor": null,
        "uplift_history": {
            "n": int(len(uplift)), "min": float(uplift.min()),
            "median": float(np.median(uplift)), "max": float(uplift.max()),
            "note": "reported score divided by the null prediction, per history entry"},
        "model_estimate": {
            "central": float(null["mean"] * np.median(uplift)),
            "low": float(null["mean"] * uplift.min()),
            "high": float(null["mean"] * uplift.max()),
            "method": "null prediction x localisation uplift; uplift is inherited "
                      "from the reported history, not measured for this file"},
        "labels": "NULL-FLOOR and MODEL-ESTIMATE only; no ORGANIZER-CONFIRMED value",
    }
    (ROOT / "evidence/wbg6_score_estimate.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
