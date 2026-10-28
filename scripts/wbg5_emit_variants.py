#!/usr/bin/env python3
"""WBG-5 emission variants: measure overlap vs comparators for several surfaces."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path("/home/user/WBGGEMSDOE1")
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "vendor"))
from gems57.emit import greedy_allocate
from gems57.uniqueness import dot_overlap

WORK = Path("/tmp/wbg5")
LABELS = ROOT / "data/bridge/labels.tif"
K_TRUTH = 12366.0
BUDGET = 37654

with rasterio.open(LABELS) as s:
    lab = s.read(1)
foot = lab != -1
cat = lab == 1
allowed = foot & ~cat

surf = np.load(WORK / "surface_wbg5.npy")
feats = np.lib.format.open_memmap(WORK / "wbg5_features.npy", mode="r", dtype="float32",
                                  shape=(46, lab.shape[0], lab.shape[1]))
dcoc = np.asarray(feats[41]).copy()
dcoc_off = np.asarray(feats[42]).copy()


def norm01(a, foot):
    a = np.where(foot, a, 0.0)
    mx = np.nanmax(a[foot]) if foot.any() else 1.0
    return (a / mx).astype(np.float32) if mx > 0 else a.astype(np.float32)


def cap_budget(dots, surf, budget):
    n = int(dots.sum())
    if n <= budget:
        return dots
    ys, xs = np.nonzero(dots)
    vals = surf[ys, xs]
    keep = np.argpartition(-vals, budget - 1)[:budget]
    out = np.zeros(dots.shape, np.float32)
    out[ys[keep], xs[keep]] = 1.0
    return out


def measure(dots, tag):
    rows = []
    for s in ("24", "25", "27", "28", "30", "31", "32", "33", "36"):
        p = Path(f"/tmp/reg9/GEMSDOE{s}.tif")
        with rasterio.open(p) as ds:
            theirs = np.nan_to_num(ds.read(1), nan=0.0)
        rows.append((f"GEMSDOE{s}", dot_overlap(dots, theirs)))
    priors = [
        ROOT / "docs/downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif",
        ROOT / "docs/downloads/wbggemsdoe1-wbg4-csjf1-edti-35135-20261027-b3dacd59-zeros.tif",
    ]
    for lp in priors:
        if lp.exists():
            with rasterio.open(lp) as ds:
                theirs = np.nan_to_num(ds.read(1), nan=0.0)
            rows.append((lp.stem[:34], dot_overlap(dots, theirs)))
    peer_max = max(v for k, v in rows if k.startswith("GEMSDOE"))
    all_max = max(v for _, v in rows)
    print(f"{tag:28s} dots={int(dots.sum()):6d} peer_max={peer_max:.4f} all_max={all_max:.4f}")
    return peer_max, all_max


dcoc_n = norm01(dcoc, foot)
surf_n = norm01(surf, foot)

t0 = time.time()
variants = {
    "A_hgb": surf_n.copy(),
    "B_blend50": (0.5 * surf_n + 0.5 * dcoc_n).astype(np.float32),
    "C_dcoc": dcoc_n.copy(),
    "D_blend75": (0.25 * surf_n + 0.75 * dcoc_n).astype(np.float32),
}
results = {}
for tag, s in variants.items():
    a = greedy_allocate(s, allowed, K_TRUTH, floor=0.02, max_dots=60000)
    dots = a.emitted.astype(np.float32)
    dots = cap_budget(dots, s, BUDGET)
    results[tag] = measure(dots, tag)

# dip-refined: shift each dot by its DCOC best offset
a = greedy_allocate(surf_n, allowed, K_TRUTH, floor=0.02, max_dots=60000)
dots = a.emitted.astype(np.float32)
dots = cap_budget(dots, surf_n, BUDGET)
ys, xs = np.nonzero(dots)
off = dcoc_off[ys, xs].astype(int)
dy = (off // 10); dx = (off % 10)
ny = np.clip(ys + dy, 0, lab.shape[0] - 1)
nx = np.clip(xs + dx, 0, lab.shape[1] - 1)
valid = foot[ny, nx] & ~cat[ny, nx]
shifted = np.zeros(dots.shape, np.float32)
shifted[ny[valid], nx[valid]] = 1.0
# keep unshifted dots that failed the shift
fail = ~valid
shifted[ys[fail], xs[fail]] = 1.0
results["E_dipshift"] = measure(shifted, "E_dipshift")
print(f"elapsed {time.time()-t0:.0f}s")
print(json.dumps({k: {"peer_max": v[0], "all_max": v[1]} for k, v in results.items()}, indent=1))
