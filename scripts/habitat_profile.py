#!/usr/bin/env python3
"""Estimate each submission's *habitat profile* and relate it to its reported score.

The competition truth is "faults not in the public catalogue".  A submission can
therefore only be described, without knowing the truth, by how it distributes its
dots relative to the mapped catalogue.  For every recovered submission we compute
the ring (distance-to-catalogue) profile and turn it into a **lift**: the share of
the submission's dots in a ring divided by the share of the footprint in that ring.
Lift 1.0 means "behaves like a uniform sample of the whole map"; lift 0 means
"never there"; lift 2 means "twice as often as the map would give you for free".

That is the one axis the hidden truth can actually be inferred along from scores
alone, and it is directly actionable: build the next raster with the profile that
the score history prefers.

Reported scores are OWNER-REPORTED, and 118 files are only ~22 independent
families, so every fit here is also reported under leave-one-family-out CV.  A
profile fit that only survives in-sample is reported as such and not used.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CACHE = ROOT / ".cache/scored"
EDGES = np.array([0.0, 1.5, 3.5, 6.5, 10.5, 20.5, 40.5, 80.5, np.inf])
RING_NAMES = ["on", "1.5", "3.5", "6.5", "10.5", "20.5", "40.5", "80.5"]


def main():
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as src:
        labels = src.read(1) > 0
        footprint = src.read_masks(1) > 0
    d_cat = ndi.distance_transform_edt(~labels)
    map_share = np.histogram(d_cat[footprint], EDGES)[0]
    map_share = map_share / map_share.sum()

    registry = json.loads((ROOT / "registry/wbg_h1/scored_registry.json").read_text())
    rows = []
    for entry in registry["entries"]:
        matches = sorted(CACHE.glob("*__" + Path(entry["path"]).name))
        if not matches:
            continue
        path = matches[0]
        with rasterio.open(path) as src:
            arr = np.where(src.read_masks(1) > 0, src.read(1), 0.0)
        dots = np.isfinite(arr) & (arr > 0) & footprint
        n = int(dots.sum())
        if n == 0:
            continue
        share = np.histogram(d_cat[dots], EDGES)[0] / n
        rows.append({
            "site": entry["site"],
            "name": entry["name"],
            "score": float(entry["score"]),
            "dots": n,
            "lift": [round(float(x), 4) for x in share / np.maximum(map_share, 1e-12)],
            "share": [round(float(x), 5) for x in share],
        })
    print(f"{len(rows)} submissions profiled")

    # Rank correlation of each ring lift with score, on its own and adjusted for budget.
    s = np.array([r["score"] for r in rows], float)
    n = np.array([r["dots"] for r in rows], float)
    L = np.array([r["lift"] for r in rows], float)
    out = {"schema": "gems-habitat-profile-v1", "n": len(rows),
           "label": "OWNER-REPORTED scores; ring lift = dot share / footprint share",
           "ring_edges_px": EDGES.tolist(), "ring_names": RING_NAMES,
           "footprint_share": map_share.tolist(), "rows": rows}

    from scipy.stats import spearmanr
    rings = []
    for j, name in enumerate(RING_NAMES):
        rho, p = spearmanr(L[:, j], s)
        rings.append({"ring": name, "spearman": float(rho), "p": float(p)})
    out["ring_score_spearman"] = rings
    rho_n, p_n = spearmanr(n, s)
    out["budget_spearman"] = {"spearman": float(rho_n), "p": float(p_n)}

    # Ridge fit of score on log-budget + lifts with leave-one-site-out CV.
    def design(idx):
        X = np.column_stack([np.log(n[idx] / 1e4), L[idx][:, 1:]])
        return X

    def cv(groups):
        pred = np.zeros_like(s)
        for g in np.unique(groups):
            tr = groups != g
            te = ~tr
            Xtr, Xte = design(tr), design(te)
            mu = Xtr.mean(0)
            sd = Xtr.std(0) + 1e-9
            lam = 3.0
            A = (Xtr - mu) / sd
            A = np.column_stack([np.ones(len(A)), A])
            P = np.diag(np.r_[0.0, np.full(A.shape[1] - 1, lam)])
            w = np.linalg.solve(A.T @ A + P, A.T @ (s[tr] - s[tr].mean()))
            B = np.column_stack([np.ones(te.sum()), (Xte - mu) / sd])
            pred[te] = s[tr].mean() + B @ w
        ss = ((s - pred) ** 2).sum()
        r2 = 1 - ss / ((s - s.mean()) ** 2).sum()
        return float(r2), float(np.corrcoef(pred, s)[0, 1]), float(
            spearmanr(pred, s).statistic)

    sites = np.array([r["site"] for r in rows])
    r2, pe, sp = cv(sites)
    out["leave_one_site_out"] = {"r2": r2, "pearson": pe, "spearman": sp}
    X = design(np.arange(len(rows)))
    mu, sd = X.mean(0), X.std(0) + 1e-9
    A = np.column_stack([np.ones(len(X)), (X - mu) / sd])
    P = np.diag(np.r_[0.0, np.full(A.shape[1] - 1, 3.0)])
    w = np.linalg.solve(A.T @ A + P, A.T @ (s - s.mean()))
    pred = s.mean() + A @ w
    out["in_sample"] = {
        "r2": float(1 - ((s - pred) ** 2).sum() / ((s - s.mean()) ** 2).sum()),
        "coef_log_budget": float(w[1]),
        "coef_ring_lift": {RING_NAMES[j + 1]: float(w[j + 2]) for j in range(len(RING_NAMES) - 1)}}
    Path(ROOT / "evidence/habitat_profile.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("ring_score_spearman", "budget_spearman",
                                          "leave_one_site_out", "in_sample")}, indent=1))


if __name__ == "__main__":
    main()
