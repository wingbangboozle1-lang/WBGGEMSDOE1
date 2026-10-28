#!/usr/bin/env python3
"""Leakage canary for every WBG-5 feature, tested one at a time.

Protocol rule: a single feature with AUC > 0.90 against the target is treated as
leakage until proven otherwise. The target here is the mapped-fault catalogue,
which is the *proxy* positive class used by the holdout, so a high AUC would mean
the holdout result is an artefact of one channel rather than of the model.

Reported per feature: univariate ROC-AUC and its reverse (1 - AUC), so an
orientation-flipped channel cannot hide, plus the missingness rate.

    python scripts/wbg5_canaries.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg5 import stack  # noqa: E402

CACHE = ROOT / ".cache" / "wbg5"
EVID = ROOT / "evidence" / "wbg5"
LIMIT = 0.90


def main() -> int:
    foot = stack.footprint_mask()
    truth = stack.catalogue()
    static = np.memmap(CACHE / "static_stack.f32", dtype=np.float32, mode="r",
                       shape=(len(stack.STATIC_NAMES), *stack.GRID_SHAPE))

    rng = np.random.default_rng(20261028)
    pos = np.flatnonzero(truth)
    neg = np.flatnonzero(foot & ~truth)
    n = min(len(pos), 40000)
    idx = np.concatenate([
        rng.choice(pos, size=n, replace=False),
        rng.choice(neg, size=n * 5, replace=False),
    ])
    y = np.concatenate([np.ones(n), np.zeros(n * 5)])

    rows = []
    for i, name in enumerate(stack.STATIC_NAMES):
        band = np.asarray(static[i]).ravel()
        x = band[idx]
        finite = np.isfinite(x)
        if finite.sum() < 1000 or len(np.unique(x[finite])) < 3:
            rows.append({"feature": name, "auc": None, "reverse_auc": None,
                         "missing_rate": float(1 - finite.mean()), "verdict": "uninformative"})
            continue
        # Missing values are scored at the feature's own median so the AUC is not
        # dominated by a present/absent split (e.g. LiDAR coverage).
        x_filled = np.where(finite, x, np.nanmedian(x[finite]))
        y_f = y[finite]
        if len(np.unique(y_f)) < 2:
            rows.append({"feature": name, "auc": None, "reverse_auc": None,
                         "missing_rate": float(1 - finite.mean()), "verdict": "degenerate"})
            continue
        auc = float(roc_auc_score(y_f, x_filled[finite]))
        rows.append({
            "feature": name,
            "auc": auc,
            "reverse_auc": 1.0 - auc,
            "orientation_invariant_max": max(auc, 1.0 - auc),
            "missing_rate": float(1 - finite.mean()),
            "verdict": "SUSPECTED LEAKAGE" if max(auc, 1.0 - auc) > LIMIT else "ok",
        })

    scored = [r for r in rows if r.get("orientation_invariant_max") is not None]
    worst = max(scored, key=lambda r: r["orientation_invariant_max"]) if scored else None
    out = {
        "schema": "gemsdoe1-wbg5-canaries-v1",
        "limit": LIMIT,
        "n_samples": int(len(y)),
        "n_positives": int(n),
        "n_negatives": int(n * 5),
        "target": "mapped-fault catalogue (the holdout proxy class)",
        "features": rows,
        "max_orientation_invariant_auc": (worst["orientation_invariant_max"] if worst else None),
        "max_feature": (worst["feature"] if worst else None),
        "suspected_leakage": bool(worst and worst["orientation_invariant_max"] > LIMIT),
        "limitation": ("Univariate screen only; it cannot rule out multivariate or spatial leakage, "
                       "and the catalogue is a proxy class rather than the scored truth."),
    }
    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / "canaries.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{'feature':<20}{'AUC':>8}{'rev':>8}{'miss':>8}  verdict")
    for r in sorted(scored, key=lambda r: -r["orientation_invariant_max"]):
        print(f"{r['feature']:<20}{r['auc']:>8.3f}{r['reverse_auc']:>8.3f}"
              f"{r['missing_rate']:>8.3f}  {r['verdict']}")
    print(f"\nmax orientation-invariant AUC = {out['max_orientation_invariant_auc']:.4f} "
          f"({out['max_feature']}) limit {LIMIT} -> "
          f"{'SUSPECTED LEAKAGE' if out['suspected_leakage'] else 'clean'}")
    return 0 if not out["suspected_leakage"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
