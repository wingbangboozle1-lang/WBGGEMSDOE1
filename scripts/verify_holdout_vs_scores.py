#!/usr/bin/env python3
"""Re-test whether the shared hide-and-recover holdout ranks owner-reported scores.

Uses the repo's own evaluator (``gems1.holdout``, evaluator version WBGGEMSDOE1-HIDE-RECOVER-v1.0)
on every owner-scored raster in ``registry/wbg_h1/scored_registry.json`` that is cached locally.
Prediction mask = finite & >0 & footprint (binary dots), as in scripts/evaluate_holdout.py.

Reports Spearman rho between HOLDOUT-DTI and OWNER-REPORTED score. This is a validity check of
the estimator, not a score. Output: evidence/focus_uniqueness/holdout_vs_owner_scores.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems1 import holdout  # noqa: E402

REG = ROOT / "registry/wbg_h1/scored_registry.json"
FETCH = ROOT / "registry/focus_raster_fetch.json"
OUT = ROOT / "evidence/focus_uniqueness/holdout_vs_owner_scores.json"


def main() -> int:
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as f:
        foot = np.isfinite(f.read(1))
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as f:
        labels = f.read(1) == 1
    ctx = holdout.build_context(foot, labels)
    fetch = {e["sha256"]: e for e in json.loads(FETCH.read_text())["entries"]}
    rows = []
    for e in json.loads(REG.read_text())["entries"]:
        local = fetch.get(e["sha256"], {}).get("local")
        if not local or not (ROOT / local).exists():
            rows.append({"name": e["name"], "status": "not_cached"})
            continue
        with rasterio.open(ROOT / local) as ds:
            a = ds.read(1)
        mask = np.isfinite(a) & (a > 0) & foot
        res = holdout.evaluate_mask(mask, ctx, b_visible_px=2.0, n_boot=200, name=e["name"])
        rows.append({"name": e["name"], "site": e["site"], "owner_score": e["score"],
                     "holdout_dti": res["pooled_dti"], "ci95": res["ci95"],
                     "n_withheld_positives": res["n_withheld_positives"],
                     "dots": int(mask.sum()), "status": "ok"})
        print(f"{len(rows)}: {e['name'][:50]} owner={e['score']} holdout={res['pooled_dti']:.4f}", file=sys.stderr)
    ok = [r for r in rows if r.get("status") == "ok"]
    x = np.array([r["owner_score"] for r in ok])
    y = np.array([r["holdout_dti"] for r in ok])
    rho, p = spearmanr(x, y)
    out = {
        "schema": "gemsdoe1-holdout-vs-owner-v1",
        "evaluator_version": ctx.evaluator_version,
        "evidence_class": "HOLDOUT-DTI vs OWNER-REPORTED",
        "n_ok": len(ok), "n_total": len(rows),
        "spearman_rho": float(rho), "p_value": float(p),
        "interpretation": "A holdout that does not rank owner scores cannot be used as a leaderboard estimate.",
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("n_ok", "n_total", "spearman_rho", "p_value")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
