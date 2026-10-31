#!/usr/bin/env python3
"""WBG-8 EXP1c/estimate follow-up: proxy-instrument calibration vs OWNER-REPORTED scores.

Fixes the filename-matching bug in the lane driver's calibration step (n=1) and
refits ``method_c`` of ``evidence/wbg8/score_estimate.json``.  This is an
analysis of already-generated evidence; no new placement, no new raster, no
slot.  Labels: PROXY-DTI is never a score; OWNER-REPORTED values are unverified.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import metric as M  # noqa: E402
from gems57 import offcatalogue as OC  # noqa: E402
from gems57.grid import load_grid  # noqa: E402

EVID = ROOT / "evidence" / "wbg8"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    grid = load_grid(ROOT / "data" / "bridge")
    fp, cat = grid.footprint, grid.catalogue
    proxy, _ = OC.load_proxy_truth(ROOT, grid)
    d_cat = ndi.distance_transform_edt(~cat)

    def proxy_dti(dots):
        r = M.dti_exact(dots.astype(np.float64), proxy, valid=fp, known=cat)
        return float(r["dti"])

    cache = ROOT / ".cache" / "focus_rasters"
    all_files = [p for p in sorted(cache.glob("*.tif"))]
    want = {
        "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros": 0.2778,
        "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros": 0.2750,
        "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan": 0.2710,
        "h27-4-solo-d28-20261004-8acb75e1-nan": 0.2708,
        "h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan": 0.2708,
        "h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan": 0.2707,
        "h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan": 0.2649,
        "h33d-analog-tip-stepover-r30-20261004-cb490425926e": 0.2632,
        "dotted-h19-5-d2-8-20261002-e56ea318af89-nan": 0.2600,
        "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca": 0.2600,
        "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan": 0.2477,
        "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan": 0.2449,
    }
    rows = []
    for stem, score in want.items():
        match = None
        for p in all_files:
            if stem in p.name:
                match = p
                break
        if match is None and stem.startswith("h33-h33-2-b2"):
            match = ROOT / "docs" / "audit" / ("gemsdoe32-" + stem + ".tif")
        if match is None or not match.exists():
            rows.append({"name": stem, "score_owner_reported": score, "error": "missing"})
            continue
        with rasterio.open(match) as ds:
            arr = ds.read(1)
        dots = np.isfinite(arr) & (arr > 0)
        rows.append({
            "name": stem, "score_owner_reported": score,
            "file": match.name, "sha256": sha256_file(match),
            "proxy_dti": proxy_dti(dots), "dots": int(dots.sum()),
            "frac_within3px_cat": float((dots & (d_cat <= 3)).sum()) / max(1, int(dots.sum())),
        })

    ok = [r for r in rows if "proxy_dti" in r]
    result = {"schema": "wbg8-proxy-calibration-v2", "n": len(ok), "rows": rows,
              "label": "OWNER-REPORTED dependent variable; PROXY-DTI is never a score"}
    if len(ok) >= 5:
        xs = np.array([r["proxy_dti"] for r in ok], float)
        ys = np.array([r["score_owner_reported"] for r in ok], float)
        fr = np.array([r["frac_within3px_cat"] for r in ok], float)
        sp = spearmanr(xs, ys)
        spf = spearmanr(fr, ys)
        result["spearman_proxy_dti_vs_owner_reported"] = float(sp.statistic)
        result["spearman_p"] = float(sp.pvalue)
        result["spearman_frac3_vs_owner_reported"] = float(spf.statistic)
        result["spearman_frac3_p"] = float(spf.pvalue)
        A = np.vstack([xs, np.ones_like(xs)]).T
        coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
        resid = ys - A @ coef
        sd = float(np.std(resid, ddof=2))
        result["ols"] = {"coefficients": [float(c) for c in coef], "residual_sd": sd}

        # Refit method_c in the estimate using the delivered candidate.
        cand_name = json.loads((EVID / "run_card.json").read_text())["submission_name"] \
            if (EVID / "run_card.json").exists() else None
        est_path = EVID / "score_estimate.json"
        if cand_name and est_path.exists():
            with rasterio.open(ROOT / "docs" / "downloads" / f"{cand_name}.tif") as ds:
                cdots = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
            cand_proxy = proxy_dti(cdots)
            pred = float(np.array([cand_proxy, 1.0]) @ coef)
            est = json.loads(est_path.read_text())
            est["method_c_proxy_calibrated"].update({
                "n": len(ok), "coefficients": [float(c) for c in coef],
                "residual_sd": sd, "point_estimate": pred,
                "prediction_interval": [pred - 1.96 * sd, pred + 1.96 * sd],
                "spearman": float(sp.statistic), "spearman_p": float(sp.pvalue),
                "caveat": ("grouped families and ±0.0856 score-consistency gaps dominate: "
                           "this interval is MODEL-ESTIMATE only"),
            })
            est_path.write_text(json.dumps(est, indent=2, allow_nan=False) + "\n")
            result["candidate_proxy_dti"] = cand_proxy
            result["candidate_model_estimate"] = pred
    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / "proxy_calibration.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in result if k != "rows"}, indent=1)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
