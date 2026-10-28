#!/usr/bin/env python3
"""Family-grouped calibration of the WBG-6 score model.

118 reported scores are not 118 independent observations: near-duplicate rasters
inherit near-identical scores.  This script groups submissions whose dot sets
overlap >70% within 3 px (transitively) and validates by *leave-one-family-out*
cross-validation, which is the honest generalisation estimate.

Model (per submission i):
    score_i ~ b0 + sum_k b_k * z_ik
with z the standardised measurable geometry:
    log n, footprint coverage, log p90 distance to the mapped catalogue,
    log mean 3-px dot neighbourhood, fraction of dots within 3 px of the
    catalogue, and mean local catalogue density under the dots.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
TERMS = ["log_n", "coverage", "log_p90", "log_cluster", "frac_cat3", "cat_density"]


def features(d: dict) -> list[float]:
    n = max(d["n"], 1.0)
    return [float(np.log(n)), float(d["roi_coverage_frac"]),
            float(np.log1p(d["dist_p90_px"])),
            float(np.log1p(d["mean_neighbour_dots"] * 100.0)),
            float(d["frac_within_3px"]), float(d["mean_local_cat_density"])]


def families(dots, thresh=0.70):
    n = len(dots)
    near = [ndi.binary_dilation(d, structure=np.ones((7, 7), bool)) for d in dots]
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        if not dots[i].any():
            continue
        for j in range(i + 1, n):
            if not dots[j].any():
                continue
            if near[j][dots[i]].mean() > thresh:
                parent[find(i)] = find(j)
    roots = {}
    for i in range(n):
        roots.setdefault(find(i), []).append(i)
    return list(roots.values())


def ols(A, b, lam=1e-8):
    return np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ b)


def main() -> int:
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())
    desc = {r["name"]: r for r in json.loads(
        (ROOT / "evidence/portfolio_descriptors.json").read_text())["rows"]}
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        foot = np.isfinite(src.read(1))
    dots = []
    for rec in fetch["entries"]:
        with rasterio.open(ROOT / rec["local"]) as src:
            a = src.read(1)
        dots.append(np.isfinite(a) & (a > 0) & foot)
    fams = families(dots)
    fam_of = np.empty(len(dots), int)
    for k, v in enumerate(fams):
        for i in v:
            fam_of[i] = k

    names = [r["name"] for r in fetch["entries"]]
    y = np.array([r["score"] for r in fetch["entries"]], float)
    X = np.array([features(desc[n]) for n in names], float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]

    beta = ols(Z, y)
    pred = Z @ beta
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    loo = np.empty_like(y)
    for i in range(len(y)):
        m = np.ones(len(y), bool)
        m[i] = False
        loo[i] = Z[i] @ ols(Z[m], y[m])

    gof = np.empty_like(y)
    for k in range(len(fams)):
        m = fam_of != k
        beta_k = ols(Z[m], y[m])
        gof[~m] = Z[~m] @ beta_k

    def stats(p, label):
        print(f"{label:22s} R2={1-((y-p)**2).sum()/((y-y.mean())**2).sum():+.3f}  "
              f"Pearson={pearsonr(y,p)[0]:+.3f}  Spearman={spearmanr(y,p)[0]:+.3f}  "
              f"RMSE={np.sqrt(((y-p)**2).mean()):.4f}")

    print(f"{len(y)} submissions -> {len(fams)} families "
          f"(largest {max(len(v) for v in fams)})")
    stats(pred, "in-sample")
    stats(loo, "leave-one-out")
    stats(gof, "leave-one-FAMILY-out")
    print(f"\nscore sd = {y.std():.4f}")
    print("\nstandardised coefficients (in-sample):")
    for nm, b in zip(["intercept"] + TERMS, beta):
        print(f"  {nm:14s} {b:+.4f}")

    resid_sd = float(np.std(y - gof))
    out = {"schema": "wbg6-score-model-v2",
           "score_label": "OWNER-REPORTED (dependent variable only)",
           "evidence_class": "MODEL-ESTIMATE",
           "n_submissions": int(len(y)), "n_families": int(len(fams)),
           "largest_family": int(max(len(v) for v in fams)),
           "terms": TERMS,
           "coefficients_standardised": [float(b) for b in beta],
           "feature_mean": [float(v) for v in mu], "feature_sd": [float(v) for v in sd],
           "r2_in_sample": float(r2),
           "r2_loo": float(1 - ((y - loo) ** 2).sum() / ((y - y.mean()) ** 2).sum()),
           "pearson_loo": float(pearsonr(y, loo)[0]),
           "pearson_grouped": float(pearsonr(y, gof)[0]),
           "spearman_grouped": float(spearmanr(y, gof)[0]),
           "r2_grouped": float(1 - ((y - gof) ** 2).sum() / ((y - y.mean()) ** 2).sum()),
           "rmse_grouped": float(np.sqrt(((y - gof) ** 2).mean())),
           "residual_sd_grouped": resid_sd,
           "score_sd": float(y.std()),
           "families": [[names[i] for i in v] for v in fams]}
    (ROOT / "evidence/wbg6_score_model.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
