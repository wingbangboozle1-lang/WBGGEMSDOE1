#!/usr/bin/env python3
"""E1: build H1 component surfaces + leakage canary + per-component holdout.

Lane (single method paragraph): blind geothermal-discharge-anchored fault
inference. Hidden faults are predicted ONLY from label-free multi-scale
lineament transforms of the 19-band GeoDAWN stack + 1 m LiDAR scarp +
radiometric externals, ranked by coincidence with independent geothermal
discharge evidence (INGENIOUS wellspring temperatures, volcanic vents,
paleo-geothermal sites) and gated softly by Andersonian strike. No
catalogue-derived feature (no distance-to-catalogue, no SGMC prior), no prior
submission raster, no dotted-thinning of H19-5 enters the surface. Emission is
priority Poisson-disk thinning with a B=2 (200 m) catalogue-flank exclusion;
budget/spacing chosen on the hide-and-recover holdout.

Outputs: work/h1_stack.npy (memmap .npy), evidence/e1_surface.json
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
    ddir, wdir = data_dir(), work_dir()
    print("[E1] loading holdout context", flush=True)
    ctx = holdout.load_holdout_context(ddir)
    print(f"[E1] foot={int(ctx.foot.sum())} labels={int(ctx.labels.sum())} "
          f"sgmc_offcat={int(ctx.sgmc_offcat.sum())} "
          f"withheld={[f.n_withheld for f in ctx.folds]}", flush=True)

    print("[E1] building H1 components (band-at-a-time)", flush=True)
    stack_path = wdir / "h1_stack.npy"
    meta = features.build_h1_components(ddir, ctx.foot, stack_path)
    print(f"[E1] stack: {meta['names']} lidar_cov={meta['lidar_coverage']:.3f} "
          f"geo={meta['geo']}", flush=True)

    stack = np.lib.format.open_memmap(stack_path, mode="r")
    out = {"experiment": "E1", "meta": meta, "canary": {}, "components": {},
           "elapsed_s": 0.0}

    print("[E1] leakage canary (feature-alone AUC)", flush=True)
    for i, name in enumerate(meta["names"]):
        c = holdout.canary_auc(np.asarray(stack[i]), ctx)
        out["canary"][name] = c
        print(f"  {name:8s} auc={c['auc']:.4f} two_sided={c['auc_two_sided']:.4f} "
              f"leak={c['leak']}", flush=True)

    print(f"[E1] per-component holdout (budget={BUDGET}, spacing={SPACING}, flank={FLANK})",
          flush=True)
    for i, name in enumerate(meta["names"]):
        if name == "gate_and":
            continue
        surf = np.asarray(stack[i])
        allowed = emission.flank_allowed(ctx.foot, ctx.labels, FLANK)
        mask = emission.poisson_disk_thin_priority(surf, allowed, SPACING, BUDGET, seed=1)
        hr = holdout.evaluate_hide_and_recover(mask, ctx, flank_exclude_px=FLANK)
        sg = holdout.evaluate_sgmc(mask, ctx)
        out["components"][name] = {
            "dots": int(mask.sum()),
            "hide_DTI": hr["pooled"]["DTI"], "hide_ci95": hr["ci"]["ci95"],
            "hide_per_fold": hr["per_fold_dti"],
            "sgmc_DTI": sg["pooled"]["DTI"], "sgmc_ci95": sg["ci"]["ci95"],
        }
        print(f"  {name:8s} dots={int(mask.sum()):6d} "
              f"HIDE={hr['pooled']['DTI']:.5f} [{hr['ci']['ci95'][0]:.5f},{hr['ci']['ci95'][1]:.5f}] "
              f"SGMC={sg['pooled']['DTI']:.5f}", flush=True)

    out["elapsed_s"] = round(time.time() - t0, 1)
    p = evidence_dir() / "e1_surface.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"[E1] wrote {p} ({out['elapsed_s']}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
