#!/usr/bin/env python3
"""Is the consensus signal real, or an artefact of near-duplicate families?

Three tests:
 1. Linear model score ~ support, with leave-one-out validation.
 2. Partial correlations of the geometry descriptors given support.
 3. Family-level test: group submissions whose dot sets overlap >70% within 3 px
    into one family, then ask whether family-mean support still predicts
    family-mean score (so the effect is not just "identical files score alike").
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]


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
    support = np.zeros(foot.shape, np.uint16)
    for d in dots:
        support += d.astype(np.uint16)

    names = [r["name"] for r in fetch["entries"]]
    scores = np.array([r["score"] for r in fetch["entries"]], float)
    sup = np.array([support[d].mean() for d in dots])

    # --- 1. simple regression + LOO ---------------------------------------
    Z = np.c_[np.ones(len(sup)), sup]
    beta = np.linalg.lstsq(Z, scores, rcond=None)[0]
    loo = np.empty_like(scores)
    for i in range(len(scores)):
        m = np.ones(len(scores), bool); m[i] = False
        loo[i] = Z[i] @ np.linalg.lstsq(Z[m], scores[m], rcond=None)[0]
    r2loo = 1 - ((scores - loo) ** 2).sum() / ((scores - scores.mean()) ** 2).sum()
    print(f"score ~ support: R2={1-((scores-Z@beta)**2).sum()/((scores-scores.mean())**2).sum():.3f} "
          f"LOO R2={r2loo:.3f} LOO Pearson={pearsonr(scores,loo)[0]:.3f}")

    # --- 2. partial correlations given support -----------------------------
    def resid(v):
        A = np.c_[np.ones(len(v)), sup]
        return v - A @ np.linalg.lstsq(A, v, rcond=None)[0]
    print("\npartial correlation with score, controlling for support:")
    for k in ("roi_coverage_frac", "dist_p90_px", "n", "mean_neighbour_dots",
              "frac_within_3px", "mean_local_cat_density"):
        v = np.array([desc[n][k] for n in names], float)
        v = v if k != "n" else np.log(v)
        r = pearsonr(resid(v), resid(scores))
        print(f"  {k:24s} r={r.statistic:+.3f} (p={r.pvalue:.2g})")

    # --- 3. family-level test ---------------------------------------------
    n = len(dots)
    near = [ndi.binary_dilation(d, structure=np.ones((7, 7), bool)) for d in dots]
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            if dots[j].sum() and near[j][dots[i]].mean() > 0.70:
                parent[find(i)] = find(j)
    fam = {}
    for i in range(n):
        fam.setdefault(find(i), []).append(i)
    fams = list(fam.values())
    fs = np.array([scores[v].mean() for v in fams])
    fu = np.array([sup[v].mean() for v in fams])
    fn = np.array([len(v) for v in fams])
    print(f"\n{n} submissions collapse to {len(fams)} families "
          f"(largest {fn.max()}, singletons {int((fn==1).sum())})")
    print(f"family-level: Spearman(support, score) = {spearmanr(fu, fs).statistic:+.3f} "
          f"(p={spearmanr(fu, fs).pvalue:.2g}), Pearson = {pearsonr(fu, fs)[0]:+.3f}")
    big = fn >= 2
    print(f"  families with >=2 members only (n={int(big.sum())}): "
          f"Spearman {spearmanr(fu[big], fs[big]).statistic:+.3f} "
          f"(p={spearmanr(fu[big], fs[big]).pvalue:.2g})")
    out = {"schema": "wbg-consensus-partial-v1", "n": n,
           "r2_loo_support_only": float(r2loo),
           "n_families": len(fams), "largest_family": int(fn.max()),
           "family_spearman": float(spearmanr(fu, fs).statistic),
           "family_spearman_p": float(spearmanr(fu, fs).pvalue),
           "families": [{"members": [names[i] for i in v], "score": float(scores[v].mean()),
                         "support": float(sup[v].mean())} for v in fams]}
    (ROOT / "evidence/consensus_partial.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
