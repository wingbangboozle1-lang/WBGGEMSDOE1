#!/usr/bin/env python3
"""E1b (same experiment as E1): add paleo-geothermal halo to s_geo + rebuild h1.

E1 shipped s_geo from wellspring+vents only (paleo CSV carries lat/lon, which
needed pyproj). This patch recomputes stack slices [0] (s_geo) and [6] (h1)
with the paleo halo included and re-evaluates exactly those two components.
Writes evidence/e1b_paleo.json and updates the stack memmap in place.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg1 import emission, features, holdout  # noqa: E402
from wbg1.paths import data_dir, evidence_dir, work_dir  # noqa: E402

BUDGET = 37654
SPACING = 2.35
FLANK = 2.0


def main() -> int:
    t0 = time.time()
    ddir = data_dir()
    ctx = holdout.load_holdout_context(ddir)
    stack = np.lib.format.open_memmap(work_dir() / "h1_stack.npy", mode="r+")
    ws = features.load_wellspring(ddir, ctx.foot.shape)
    vn = features.load_vents(ddir, ctx.foot.shape)
    pa = features.load_paleo(ddir, ctx.foot.shape)
    halo = (features.proximity_halo(ws["points"], 10.0)
            + 0.8 * features.proximity_halo(vn["points"], 10.0)
            + 0.6 * features.proximity_halo(pa["points"], 10.0))
    stack[0] = features.rank_norm(halo, ctx.foot)
    parts = np.asarray(stack[0:5]).astype(np.float64)
    h1 = np.mean(parts, axis=0) * np.asarray(stack[5]).astype(np.float64)
    stack[6] = features.rank_norm(h1, ctx.foot)
    stack.flush()
    print(f"[E1b] paleo_points_in_footprint={pa['n']} (of 709 regional)",
          flush=True)

    out: dict = {"experiment": "E1b", "paleo": {"n": pa["n"]}, "components": {}}
    for idx, name in ((0, "s_geo"), (6, "h1")):
        surf = np.asarray(stack[idx])
        c = holdout.canary_auc(surf, ctx)
        allowed = emission.flank_allowed(ctx.foot, ctx.labels, FLANK)
        mask = emission.poisson_disk_thin_priority(surf, allowed, SPACING, BUDGET, seed=1)
        hr = holdout.evaluate_hide_and_recover(mask, ctx, flank_exclude_px=FLANK)
        sg = holdout.evaluate_sgmc(mask, ctx)
        out["components"][name] = {
            "canary": c, "dots": int(mask.sum()),
            "hide_DTI": hr["pooled"]["DTI"], "hide_ci95": hr["ci"]["ci95"],
            "sgmc_DTI": sg["pooled"]["DTI"], "sgmc_ci95": sg["ci"]["ci95"],
        }
        print(f"[E1b] {name}: canary={c['auc_two_sided']:.4f} "
              f"HIDE={hr['pooled']['DTI']:.5f} SGMC={sg['pooled']['DTI']:.5f}", flush=True)
    out["elapsed_s"] = round(time.time() - t0, 1)
    (evidence_dir() / "e1b_paleo.json").write_text(json.dumps(out, indent=2))
    print(f"[E1b] done ({out['elapsed_s']}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
