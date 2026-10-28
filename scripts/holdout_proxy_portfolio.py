#!/usr/bin/env python3
"""Holdout fault-prior proxy for the 118 owner-reported submissions.

Reuses the shared hide-and-recover evaluator (vendor/gems57/holdout.py) unchanged:
whole catalogue segments are withheld inside each spatial quadrant, the visible
catalogue is masked out pixel-exactly, and pooled DTI (alpha 0.2, beta 0.8, 300 m
triangular kernel) is measured against the withheld pixels.

IMPORTANT LIMITATION, stated up front: the submissions were built from the *full*
catalogue, so a withheld segment is still inside the geometric pattern the method
used.  This proxy therefore measures how strongly a submission follows fault
structure -- a leakage-inflated upper bound -- not how well it would find an
unmapped fault.  It is used only to test whether the proxy carries rank
information about the real hidden score.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid           # noqa: E402
from gems57.holdout import build_holdout, evaluate  # noqa: E402


def main() -> int:
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())
    grid = load_grid(ROOT / "data/bridge")
    print("building fold cells ...", flush=True)
    ctx = build_holdout(grid, seeds=(20, 21), modes=("all",))
    print(f"{len(ctx.cells)} fold cells", flush=True)
    rows = []
    for i, rec in enumerate(fetch["entries"]):
        with rasterio.open(ROOT / rec["local"]) as src:
            a = src.read(1)
        emitted = np.isfinite(a) & (a > 0)
        res = evaluate(emitted, ctx)
        rows.append({"repo": rec["repo"], "name": rec["name"], "score": float(rec["score"]),
                     "holdout_dti": float(res["pooled_dti"]),
                     "holdout_coverage": float(res["pooled_coverage"]),
                     "on_visible_catalogue": int(res["on_visible_catalogue"]),
                     "n_dots": int(emitted.sum())})
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(fetch['entries'])}", flush=True)
    from scipy.stats import pearsonr, spearmanr
    s = np.array([r["score"] for r in rows])
    h = np.array([r["holdout_dti"] for r in rows])
    rho = spearmanr(h, s)
    r = pearsonr(h, s)
    print(f"\nproxy vs reported score: Spearman {rho.statistic:.3f} (p={rho.pvalue:.2g}), "
          f"Pearson {r.statistic:.3f} (p={r.pvalue:.2g})")
    out = {"schema": "wbg-holdout-proxy-portfolio-v1",
           "evaluator": "gems57.hide-and-recover (modes=all, seeds=20,21)",
           "score_label": "OWNER-REPORTED",
           "proxy_limitation": "leakage-inflated upper bound; see module docstring",
           "spearman": float(rho.statistic), "spearman_p": float(rho.pvalue),
           "pearson": float(r.statistic), "pearson_p": float(r.pvalue),
           "rows": rows}
    (ROOT / "evidence/holdout_proxy_portfolio.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
