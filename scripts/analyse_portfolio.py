#!/usr/bin/env python3
"""Leave-one-out calibration of a score model on the 118 owner-reported scores.

Two questions:
  1. Which measurable geometric properties of a submission predict its leaderboard
     score?  (OLS on standardized descriptors, LOO-validated.)
  2. Is the historical search clustered in a few places, i.e. how much of the
     footprint has *never* been proposed?  (Per-cell submission-support map.)

Scores are OWNER-REPORTED; the fit is a regression, never an organizer result.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def load_dots(rec):
    with rasterio.open(ROOT / rec["local"]) as src:
        a = src.read(1)
        return np.isfinite(a) & (a > 0)


def main() -> int:
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())
    desc = json.loads((ROOT / "evidence/portfolio_descriptors.json").read_text())
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        foot = np.isfinite(src.read(1))

    rows = desc["rows"]
    y = np.array([r["score"] for r in rows], float)
    fdat = {r["name"]: r for r in fetch["entries"]}

    # ---- per-cell submission support -------------------------------------
    support = np.zeros(foot.shape, np.uint8)
    for r in rows:
        support += load_dots(fdat[r["name"]]).astype(np.uint8)
    inside = foot
    support_vals = support[inside]
    uncovered = int((support_vals == 0).sum())
    print(f"footprint cells          : {int(inside.sum()):,}")
    print(f"cells proposed by >=1 sub: {int((support_vals >= 1).sum()):,} "
          f"({(support_vals >= 1).mean()*100:.2f}%)")
    print(f"cells never proposed     : {uncovered:,} ({uncovered/inside.sum()*100:.2f}%)")
    print(f"cells proposed by >=10   : {int((support_vals >= 10).sum()):,} "
          f"({(support_vals >= 10).mean()*100:.2f}%)")

    np.save(ROOT / ".cache/support.npy", support)

    # ---- LOO-validated linear model --------------------------------------
    def feat(r):
        n = max(r["n"], 1)
        return [np.log(n), r["roi_coverage_frac"], np.log1p(r["dist_p90_px"]),
                np.log1p(r["mean_neighbour_dots"] * 100), r["frac_within_3px"],
                np.log1p(r["n_components"] / n), r["mean_local_cat_density"]]

    names = ["log_n", "coverage", "log_p90", "log_cluster", "frac_cat3",
             "log_comp_per_dot", "local_cat_density"]
    X = np.array([feat(r) for r in rows], float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]

    def ols(A, b, lam=1e-6):
        return np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ b)

    beta = ols(Z, y)
    pred = Z @ beta
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    loo = np.empty_like(y)
    for i in range(len(y)):
        m = np.ones(len(y), bool)
        m[i] = False
        loo[i] = Z[i] @ ols(Z[m], y[m])
    r2loo = 1 - ((y - loo) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    from scipy.stats import pearsonr, spearmanr
    print(f"\nin-sample R^2 = {r2:.3f}   LOO R^2 = {r2loo:.3f}")
    print(f"LOO Pearson  = {pearsonr(y, loo)[0]:.3f}   "
          f"LOO Spearman = {spearmanr(y, loo)[0]:.3f}")
    print(f"LOO RMSE     = {np.sqrt(((y-loo)**2).mean()):.4f} "
          f"(score sd = {y.std():.4f})")
    print(f"{'term':22s} {'standardised coef':>18s}")
    for nm, b in zip(["intercept"] + names, beta):
        print(f"{nm:22s} {b:18.4f}")

    out = {
        "schema": "wbg-portfolio-score-model-v1",
        "score_label": "OWNER-REPORTED (dependent variable only)",
        "n": int(len(y)), "r2_in_sample": float(r2), "r2_loo": float(r2loo),
        "loo_pearson": float(pearsonr(y, loo)[0]),
        "loo_spearman": float(spearmanr(y, loo)[0]),
        "loo_rmse": float(np.sqrt(((y - loo) ** 2).mean())),
        "score_sd": float(y.std()),
        "terms": names, "coefficients": [float(b) for b in beta],
        "feature_mean": [float(v) for v in mu], "feature_sd": [float(v) for v in sd],
        "support": {"footprint_cells": int(inside.sum()),
                    "cells_never_proposed": uncovered,
                    "cells_ge10_submissions": int((support_vals >= 10).sum())},
        "loo_predictions": [{"name": r["name"], "score": float(r["score"]),
                             "loo_pred": float(p)}
                            for r, p in zip(rows, loo)],
    }
    (ROOT / "evidence/portfolio_score_model.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
