#!/usr/bin/env python3
"""E2: emission sweep (budget x spacing) for H1 + champion baselines.

Budgets {30000, 37654, 44090} x spacing {2.0, 2.35, 2.8}, B=2 flank.
Also scores all 9 focus-9 champion rasters on the SAME instruments so the
comparison table is apples-to-apples.

Instrument roles (validated 2026-10-26: the 0.2778 champion scores
HIDE=0.0032, floored): hide-and-recover-vs-catalogue is DIAGNOSTIC ONLY for
B-excluded emissions (dots avoid all catalogue by design, so catalogue-truth
credit is a floor effect and the instrument cannot rank them). The PRIMARY
ranking instrument is SGMC off-catalogue (champion 0.0444, discriminative):
it mimics the hidden test (faults missing from the catalogue).
Outputs: evidence/e2_sweep.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg1 import emission, holdout  # noqa: E402
from wbg1.paths import data_dir, evidence_dir, registry_raster_dir, work_dir  # noqa: E402

BUDGETS = [30000, 37654, 44090]
SPACINGS = [2.0, 2.35, 2.8]
FLANK = 2.0


def main() -> int:
    t0 = time.time()
    ctx = holdout.load_holdout_context(data_dir())
    stack = np.lib.format.open_memmap(work_dir() / "h1_stack.npy", mode="r")
    h1 = np.asarray(stack[6])
    s_topo = np.asarray(stack[3])
    s_mag = np.asarray(stack[2])
    parts = np.asarray(stack[0:5]).astype(np.float64)
    w = np.array([0.1, 0.1, 0.2, 0.5, 0.1])  # geo cond mag topo grav
    h1w_raw = (parts * w[:, None, None]).sum(axis=0) * np.asarray(stack[5])
    from wbg1 import features as _F
    h1w = _F.rank_norm(h1w_raw, ctx.foot)
    del parts, h1w_raw
    surfaces = {"h1": h1, "s_topo": s_topo, "s_mag": s_mag, "h1w": h1w}
    out: dict = {"experiment": "E2", "budgets": BUDGETS, "spacings": SPACINGS,
                 "flank": FLANK, "h1w_weights": {"geo": 0.1, "cond": 0.1, "mag": 0.2,
                 "topo": 0.5, "grav": 0.1}, "h1_grid": {}, "champions": {}}

    print("[E2] surface x budget x spacing sweep (SGMC-primary)", flush=True)
    allowed = emission.flank_allowed(ctx.foot, ctx.labels, FLANK)
    for sname, surf in surfaces.items():
        for b in BUDGETS:
            for s in SPACINGS:
                m = emission.poisson_disk_thin_priority(surf, allowed, s, b, seed=1)
                hr = holdout.evaluate_hide_and_recover(m, ctx, flank_exclude_px=FLANK)
                sg = holdout.evaluate_sgmc(m, ctx)
                key = f"{sname}-B{b}-S{s}"
                out["h1_grid"][key] = {
                    "dots": int(m.sum()),
                    "hide_DTI": hr["pooled"]["DTI"], "hide_ci95": hr["ci"]["ci95"],
                    "hide_per_fold": hr["per_fold_dti"],
                    "sgmc_DTI": sg["pooled"]["DTI"], "sgmc_ci95": sg["ci"]["ci95"],
                }
                print(f"  {key:14s} dots={int(m.sum()):6d} HIDE={hr['pooled']['DTI']:.5f} "
                      f"SGMC={sg['pooled']['DTI']:.5f}", flush=True)

    print("[E2] focus-9 champion baselines (same instruments)", flush=True)
    champs = {
        "G24-d1.5": "g24-d15-nan.tif", "G25-d2.8": "g25-d28-nan.tif",
        "G27-gap": "g27-gap-nan.tif", "G28-rung30": "g28-rung30-nan.tif",
        "G30-poisson": "g30-poisson.tif", "G31-h274solo": "g31-h274solo-nan.tif",
        "G32-h33": "g32-h33-champ-zeros.tif", "G33-analog": "g33-analog.tif",
        "G36-pinn": "g36-pinn-zeros.tif",
    }
    rdir = registry_raster_dir()
    for name, fn in champs.items():
        m = holdout.read_binary_tif(rdir / fn)
        # flank=2.0 for all (live-faithful: near-visible dots are masked live,
        # so per-fold visible-flank masking mimics the portal). HIDE is
        # diagnostic-only; SGMC (primary) is unaffected by this parameter.
        hr = holdout.evaluate_hide_and_recover(m, ctx, flank_exclude_px=2.0)
        sg = holdout.evaluate_sgmc(m, ctx)
        out["champions"][name] = {
            "dots": int(m.sum()),
            "hide_DTI": hr["pooled"]["DTI"], "hide_ci95": hr["ci"]["ci95"],
            "hide_per_fold": hr["per_fold_dti"],
            "sgmc_DTI": sg["pooled"]["DTI"], "sgmc_ci95": sg["ci"]["ci95"],
        }
        print(f"  {name:12s} dots={int(m.sum()):6d} HIDE={hr['pooled']['DTI']:.5f} "
              f"SGMC={sg['pooled']['DTI']:.5f}", flush=True)

    out["elapsed_s"] = round(time.time() - t0, 1)
    p = evidence_dir() / "e2_sweep.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"[E2] wrote {p} ({out['elapsed_s']}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
