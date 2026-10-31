#!/usr/bin/env python3
"""HOLDOUT-DTI for the eleven named focus-site rasters, plus a rank check against the user-reported scores.

Shared evaluator, unchanged: gems57.holdout.build_holdout + evaluate (seeds 20,21; mode "all";
alpha 0.2, beta 0.8, 300 m triangular kernel). Label: HOLDOUT-DTI. CI = percentile bootstrap over
the 8 fold cells (2 seeds x 4 quadrants). It is NOT the 20 km block CI of evaluate_holdout.py.

The user-reported scores are OWNER-REPORTED; they are used only to test rank agreement.
Usage: .venv/bin/python scripts/holdout_focus_20261031.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import build_holdout, evaluate  # noqa: E402

OUT = ROOT / "evidence/session_20261031/holdout_focus.json"
# (label, SHA-256 prefix, user-reported score as listed in the 29 Oct summary)
NAMED = [
    ("GEMSDOE32 B2", "c55bafc470054e82", 0.2778),
    ("GEMSDOE36 pinn", "e15891020b9c5705", 0.2750),
    ("GEMSDOE28 rung30", "5556aa1438fd6737", 0.2710),
    ("GEMSDOE28 solo D2.8", "ab02300152248fdd", 0.2708),
    ("GEMSDOE31 solo D28", "07b6db440535404b", 0.2708),
    ("GEMSDOE28 hf-euler", "81d5b87bc8424f16", 0.2707),
    ("GEMSDOE33 analog-tip", "87f857d505e23247", 0.2632),
    ("GEMSDOE25 D2.8", "91eae1ca42ec845e", 0.2600),
    ("GEMSDOE30 poisson", "8cf893ead5667df2", 0.2600),
    ("GEMSDOE24 H25-1", "68d0e2e4fcc594f9", 0.2477),
    ("GEMSDOE27 topo-gap", "33003374335d84bf", 0.2449),
]


def main() -> int:
    grid = load_grid(ROOT / "data/bridge")
    manifest = json.loads((ROOT / "registry/focus_raster_fetch.json").read_text())
    entries = [e for e in manifest["entries"] if e.get("local")]
    ctx = build_holdout(grid, seeds=(20, 21), modes=("all",))
    rows = []
    for label, prefix, user_score in NAMED:
        hits = [e for e in entries if e["sha256"].startswith(prefix)]
        e = hits[0]
        path = ROOT / e["local"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != e["sha256"]:
            raise SystemExit(f"hash mismatch {label}")
        with rasterio.open(path) as src:
            a = src.read(1)
        dots = np.isfinite(a) & (a > 0)
        res = evaluate(dots, ctx)
        cells = list(res["folds"].values())
        tp = np.array([c["tp"] for c in cells])
        fp = np.array([c["fp"] for c in cells])
        fn = np.array([c["fn"] for c in cells])
        rng = np.random.default_rng(20261031)
        boots = []
        for _ in range(2000):
            idx = rng.integers(0, len(cells), len(cells))
            t, f, n = tp[idx].sum(), fp[idx].sum(), fn[idx].sum()
            boots.append(t / (t + 0.2 * f + 0.8 * n + 1e-12))
        lo, hi = np.quantile(boots, [0.025, 0.975])
        rows.append(dict(
            site=label, sha256=digest, repo=e["repo"], path=e["path"], n_dots=int(dots.sum()),
            user_reported_score=user_score, score_label="USER-REPORTED (not organizer-confirmed)",
            evidence_class="HOLDOUT-DTI", evaluator="gems57.holdout.evaluate, seeds 20,21, mode all",
            evaluator_sha256=hashlib.sha256((ROOT / "vendor/gems57/holdout.py").read_bytes()).hexdigest(),
            holdout_dti=float(res["pooled_dti"]), n_withheld_positives=int(res["pooled_n_truth"]),
            ci95_fold_bootstrap=[float(lo), float(hi)], fold_cells=len(cells),
            on_visible_catalogue=int(res["on_visible_catalogue"]),
        ))
        print(f"{label:24s} n_dots={int(dots.sum()):6d} HOLDOUT-DTI={res['pooled_dti']:.4f} "
              f"CI=[{lo:.4f},{hi:.4f}] n={res['pooled_n_truth']}", flush=True)

    user = np.array([r["user_reported_score"] for r in rows])
    hold = np.array([r["holdout_dti"] for r in rows])
    rho, p = spearmanr(user, hold)
    summary = dict(
        spearman_user_vs_holdout=float(rho), spearman_p=float(p), n_files=len(rows),
        note=("Spearman between user-reported scores and holdout DTI across the 11 named files. "
              "Ties exist in the user scores. A negative or near-zero value means the holdout does not "
              "reproduce the reported ordering."),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(rows=rows, rank_check=summary), indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
