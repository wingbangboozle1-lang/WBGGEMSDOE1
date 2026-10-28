#!/usr/bin/env python3
"""Sweep HGB/DCOC blend weights; report overlap vs peers and this repo's priors."""
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


def norm01(a, foot):
    a = np.where(foot, a, 0.0)
    mx = np.nanmax(a[foot]) if foot.any() else 1.0
    return (a / mx).astype(np.float32) if mx > 0 else a.astype(np.float32)


def cap_budget(dots, s, budget):
    n = int(dots.sum())
    if n <= budget:
        return dots
    ys, xs = np.nonzero(dots)
    vals = s[ys, xs]
    keep = np.argpartition(-vals, budget - 1)[:budget]
    out = np.zeros(dots.shape, np.float32)
    out[ys[keep], xs[keep]] = 1.0
    return out


surf_n = norm01(surf, foot)
dcoc_n = norm01(dcoc, foot)

comparators = []
for s in ("24", "25", "27", "28", "30", "31", "32", "33", "36"):
    comparators.append((f"GEMSDOE{s}", Path(f"/tmp/reg9/GEMSDOE{s}.tif")))
for lp in [ROOT / "docs/downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif",
           ROOT / "docs/downloads/wbggemsdoe1-wbg4-csjf1-edti-35135-20261027-b3dacd59-zeros.tif",
           ROOT / "docs/downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.tif",
           ROOT / "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif",
           ROOT / "docs/downloads/wbggemsdoe1-wbg-s2-exp3-mksf-vierbeincoulomb-20261027-e9b4a3c09065-zeros.tif",
           ROOT / "docs/downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif"]:
    if lp.exists():
        comparators.append((lp.stem[:30], lp))

t0 = time.time()
out = {}
for w in [0.0, 0.15, 0.25, 0.35, 0.5, 0.65, 0.75, 1.0]:
    s = ((1 - w) * surf_n + w * dcoc_n).astype(np.float32)
    a = greedy_allocate(s, allowed, K_TRUTH, floor=0.02, max_dots=60000)
    dots = cap_budget(a.emitted.astype(np.float32), s, BUDGET)
    peer = []; allv = []
    for label, p in comparators:
        with rasterio.open(p) as ds:
            theirs = np.nan_to_num(ds.read(1), nan=0.0)
        ov = dot_overlap(dots, theirs)
        (peer if label.startswith("GEMSDOE") else allv).append((label, ov))
    pm = max(v for _, v in peer); am = max(v for _, v in allv)
    worst = max(allv, key=lambda x: x[1])
    out[f"w={w}"] = {"dots": int(dots.sum()), "peer_max": pm, "all_max": am,
                     "worst": worst[0], "pass_both": pm <= 0.70 and am <= 0.70}
    print(f"w={w:.2f} dots={int(dots.sum()):6d} peer={pm:.4f} all={am:.4f} "
          f"worst={worst[0][:24]} pass_both={pm<=0.70 and am<=0.70}")
print(f"elapsed {time.time()-t0:.0f}s")
(WORK / "blend_sweep.json").write_text(json.dumps(out, indent=1))
