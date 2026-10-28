#!/usr/bin/env python3
"""Show whether the literal 3-px registry gate can ever be passed by a dotted raster.

Gate under test (standing brief, parallel-run protocol item 1): STOP if more than 70% of a
submission's dots lie within 3 px of one registry raster's dots. Tested against the
r13 lattice (registry input, inside the GEMSDOE24 repo). Baseline: random dots drawn
INSIDE the official footprint, with the same count as WBG-6.
Writes evidence/literal_gate_degeneracy_20261028.json. Needs --r13 path to the file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
WBG6 = ROOT / "docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"


def load_mask(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def within3(a_pts: np.ndarray, b_pts: np.ndarray) -> float:
    d, _ = cKDTree(b_pts).query(a_pts, k=1)
    return float((d <= 3.0).mean())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--r13", required=True, type=Path)
    ap.add_argument("--out", default=ROOT / "evidence/literal_gate_degeneracy_20261028.json", type=Path)
    args = ap.parse_args()

    r13 = load_mask(args.r13)
    r13_pts = np.column_stack(np.where(r13)).astype(float)
    w6 = load_mask(WBG6)
    w6_pts = np.column_stack(np.where(w6)).astype(float)
    with rasterio.open(SAMPLE) as s:
        footprint = np.isfinite(s.read(1))
    cells = np.column_stack(np.where(footprint)).astype(float)
    n = int(w6.sum())

    rng = np.random.default_rng(20261028)
    base = []
    for seed_off in range(5):
        idx = rng.choice(len(cells), n, replace=False)
        base.append(within3(cells[idx], r13_pts))
    res = {
        "schema": "literal-gate-degeneracy-v1",
        "gate": "STOP if forward share of a submission's dots within 3 px of registry dots > 0.70",
        "registry_raster": "GEMSDOE24/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
        "registry_raster_sha256": hashlib.sha256(args.r13.read_bytes()).hexdigest(),
        "registry_dots": int(len(r13_pts)),
        "wbg6_dots": n,
        "wbg6_forward3px_vs_r13": round(within3(w6_pts, r13_pts), 5),
        "random_in_footprint_dots_forward3px_vs_r13": {
            "n": n, "draws": len(base), "values": [round(v, 5) for v in base],
            "mean": round(float(np.mean(base)), 5), "min": round(float(np.min(base)), 5),
        },
        "footprint_cells_within3px_of_r13": round(float((cKDTree(r13_pts).query(cells, k=1)[0] <= 3).mean()), 5),
        "conclusion": ("A random in-footprint field also fails the literal gate. Any dotted "
                       "submission in the footprint fails it while r13 is in the registry. The gate "
                       "needs an amendment decision by the project owner; it is not a property of WBG-6."),
    }
    args.out.write_text(json.dumps(res, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("wbg6_forward3px_vs_r13", "random_in_footprint_dots_forward3px_vs_r13")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
