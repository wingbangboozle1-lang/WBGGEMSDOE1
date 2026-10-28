#!/usr/bin/env python3
"""Score all 118 recovered submissions against the shared segment holdout, two ways.

The shared evaluator (``gems.holdout.SegmentHoldout``) scores predictions with the
visible catalogue masked out of the active domain.  That is right for a *detector*
being fitted fold-by-fold: it must not be punished for dots it placed on a fault it
was allowed to read.  It is wrong for *this* question.  The competition truth is
defined as faults that are NOT in the public catalogue, so in the real metric every
dot that is not near hidden truth is a false positive - including dots on the
mapped catalogue.  A catalogue-following submission therefore looks good under the
forgiving rule and bad under the real one.

This script measures both:

* ``catalogue_forgiven`` - the repo's rule (``known = visible``).
* ``catalogue_penalised`` - the organiser's rule (``known = nothing``): a dot on the
  mapped catalogue is a false positive, exactly as on the leaderboard.

It then reports whether either version ranks the 118 owner-reported scores.  This
is an instrument-validity test, not a score estimate: the withheld positives are
mapped faults standing in for unmapped ones.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems1.metric import EPS, kernel  # noqa: E402
from gems.holdout import SegmentHoldout  # noqa: E402

CACHE = ROOT / ".cache/scored"
REG = ROOT / "registry/wbg_h1/scored_registry.json"


def load_stack():
    """(examples, footprint, labels) from the nine-site audit bridge."""
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as src:
        labels = src.read(1) > 0
        footprint = src.read_masks(1) > 0
    return labels, footprint


def score_variants(pred, folds):
    """Pooled exact-DTI components under both known-mask rules."""
    out = {"catalogue_forgiven": [0.0, 0.0, 0.0], "catalogue_penalised": [0.0, 0.0, 0.0]}
    for fold in folds:
        valid, truth, visible = fold["valid"], fold["truth"], fold["visible"]
        p = pred & valid
        g = truth & valid
        n = int(g.sum())
        if n == 0:
            continue
        if not p.any():
            for key, active in (
                ("catalogue_forgiven", valid & ~visible),
                ("catalogue_penalised", valid),
            ):
                out[key][2] += float((truth & active).sum())
            continue
        dp = ndi.distance_transform_edt(~p)
        kp = kernel(dp)
        dg = ndi.distance_transform_edt(~g)
        kg = kernel(dg)
        for key, active in (
            ("catalogue_forgiven", valid & ~visible),
            ("catalogue_penalised", valid),
        ):
            ag = truth & active
            ap = pred & active
            tp = float(kp[ag].sum())
            out[key][0] += tp
            out[key][1] += float((1.0 - kg[ap]).sum())
            out[key][2] += float(ag.sum()) - tp
    return {k: dict(zip(("tp", "fp", "fn"), v)) for k, v in out.items()}


def dti(c):
    return c["tp"] / (c["tp"] + 0.2 * c["fp"] + 0.8 * c["fn"] + EPS)


def main():
    labels, footprint = load_stack()
    ctx = SegmentHoldout(footprint, labels, buffer_px=15)
    registry = json.loads(REG.read_text())["entries"]
    rows = []
    for i, entry in enumerate(registry, 1):
        matches = sorted(CACHE.glob("*__" + Path(entry["path"]).name))
        if not matches:
            print(f"  skip (missing) {entry['path']}")
            continue
        path = matches[0]
        with rasterio.open(path) as src:
            arr = np.where(src.read_masks(1) > 0, src.read(1), 0.0)
        pred = np.isfinite(arr) & (arr > 0) & footprint
        comp = score_variants(pred, ctx.folds)
        rows.append({
            "name": entry["name"],
            "reported_score": float(entry["score"]),
            "dots": int(pred.sum()),
            "catalogue_forgiven": dti(comp["catalogue_forgiven"]),
            "catalogue_penalised": dti(comp["catalogue_penalised"]),
            "components": comp,
        })
        if i % 20 == 0:
            print(f"  {i}/{len(registry)}", flush=True)

    s = np.array([r["reported_score"] for r in rows])
    report = {"schema": "gems-proxy-holdout-portfolio-v2", "n": len(rows),
              "label": "INSTRUMENT TEST - not a score estimate",
              "protocol": "segment holdout, whole components hidden, 15 px collar, "
                          "pooled TP/FP/FN, alpha 0.2 beta 0.8 R 3 px; predictions are "
                          "pre-built rasters, so withheld components were visible to "
                          "their authors - every number here is an upper bound on detector skill",
              "rows": rows}
    for key in ("catalogue_forgiven", "catalogue_penalised"):
        x = np.array([r[key] for r in rows])
        report[key] = {
            "spearman": float(spearmanr(x, s).statistic),
            "spearman_p": float(spearmanr(x, s).pvalue),
            "pearson": float(pearsonr(x, s)[0]),
            "pearson_p": float(pearsonr(x, s)[1]),
        }
    # Does penalising catalogue dots repair the ranking?
    best = max(report["catalogue_forgiven"]["spearman"],
               report["catalogue_penalised"]["spearman"])
    report["verdict"] = (
        "penalising catalogue dots does not repair external validity"
        if report["catalogue_penalised"]["spearman"] < 0.35
        else "penalising catalogue dots improves external validity"
    )
    out = ROOT / "evidence/proxy_holdout_portfolio_v2.json"
    out.write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in
                      ("catalogue_forgiven", "catalogue_penalised", "verdict")}, indent=1))
    print("wrote", out, "n=", report["n"], "max_spearman=", round(best, 3))


if __name__ == "__main__":
    main()
