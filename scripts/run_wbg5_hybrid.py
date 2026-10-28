#!/usr/bin/env python3
"""WBG-5 hybrid arm: physics likelihood + mask-aware catalogue proximity.

Why this arm exists
-------------------
The physics-only arm never reads the catalogue, so it cannot exploit the one
scoring fact the organizers stated in writing: pixels on mapped faults are
*excluded* from scoring, and therefore cost nothing. The reverse also holds — a
prediction 100-300 m off a mapped fault is in an unmasked pixel and is charged
the full false-positive price, while its chance of sitting on a *new* fault is
low. The GEMSDOE32 B2 file is the natural experiment: it deletes 6,436 dots that
all lie within 200 m of the catalogue and its owner-reported score rises
0.2600 -> 0.2778.

So the hybrid multiplies the physics surface by a proximity term for legitimate
off-catalogue candidates and refuses to emit inside the exclusion ring:

    score = physics * (1 + w * exp(-d_cat / d0)),   eligible = d_cat >= ring_px

``w`` = 0 reproduces the physics-only arm. Everything is scored on the same
four-quadrant holdout, with the catalogue block rebuilt from visible faults only.

    python scripts/run_wbg5_hybrid.py --stage sweep
    python scripts/run_wbg5_hybrid.py --stage final
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems.holdout import SegmentHoldout  # noqa: E402
from wbg5 import place  # noqa: E402

import run_wbg5_lane as lane  # noqa: E402

CACHE = ROOT / ".cache" / "wbg5"
EVID = ROOT / "evidence" / "wbg5"

WEIGHTS = (0.0, 0.25, 0.6)
DECAY_PX = 6.0
RING_PX = 3.0
D_MIN = 2.0
BUDGET = 55000


def hybrid_score(physics: np.ndarray, visible: np.ndarray, w: float) -> tuple[np.ndarray, np.ndarray]:
    dist = distance_transform_edt(~visible).astype(np.float32)
    score = np.where(np.isfinite(physics), physics, 0.0).astype(np.float32)
    if w > 0:
        score = score * (1.0 + w * np.exp(-dist / DECAY_PX))
    eligible = dist >= RING_PX
    return score, eligible


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("sweep", "final"), default="sweep")
    parser.add_argument("--out", type=Path, default=CACHE / "final_prediction_hybrid.npy")
    args = parser.parse_args()

    foot, truth = lane.load_grid()
    hold = SegmentHoldout(foot, truth, buffer_px=15)

    if args.stage == "sweep":
        rows = []
        masks: dict[float, list[np.ndarray]] = {w: [] for w in WEIGHTS}
        for fold in hold.folds:
            path = CACHE / f"surface_blind_fold{fold['id']}.f32"
            if not path.exists():
                raise SystemExit(f"missing blind surface {path}; run the blind sweep first")
            physics = np.fromfile(path, dtype=np.float32).reshape(foot.shape)
            for w in WEIGHTS:
                score, eligible = hybrid_score(physics, fold["visible"], w)
                order = place.suppression_order(
                    score, foot & eligible & ~fold["visible"],
                    d_min=D_MIN, max_n=BUDGET, keep_frac=0.05,
                )
                dots = place.dots_from_order(order, BUDGET, foot.shape)
                res = lane.fold_dti(dots, fold)
                masks[w].append(dots)
                rows.append({"fold": fold["name"], "w": w, **res})
        grid = []
        for w in WEIGHTS:
            sub = [r for r in rows if r["w"] == w]
            grid.append({"w": w, **lane.pooled(sub)})
        grid.sort(key=lambda r: -r["dti"])
        summary = hold.summarize(masks[grid[0]["w"]])
        ci = summary["ci95"]["interval"]
        print(f"\n95% spatial-block CI for w={grid[0]['w']}: "
              f"HOLDOUT-DTI {summary['dti']:.6f} [{ci[0]:.6f}, {ci[1]:.6f}]"
              f"  n_withheld={summary['n_withheld_positive_pixels']:,}")
        print(f"{'w':>5} {'dots':>8} {'coverage':>9} {'DTI':>8}")
        for r in grid:
            print(f"{r['w']:>5.2f} {r['n_emitted']:>8d} {r['coverage']:>9.4f} {r['dti']:>8.4f}")
        out = {"schema": "gemsdoe1-wbg5-hybrid-sweep-v1", "weights": list(WEIGHTS),
               "decay_px": DECAY_PX, "ring_px": RING_PX, "d_min": D_MIN, "budget": BUDGET,
               "grid": grid, "per_fold": rows,
               "best_summary": summary,
               "interpretation": (
                   "w = 0 is the physics-only arm. A positive w trades a little holdout "
                   "recovery of mapped faults for mask-aware placement off the catalogue "
                   "ring, which is the only zone the organizer leaves unpunished and the "
                   "only zone where a new fault can be found."
               )}
        (EVID / "hybrid_sweep.json").write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nbest w = {grid[0]['w']}")
        return 0

    # ---------------------------------------------------------------- final
    sweep = json.loads((EVID / "hybrid_sweep.json").read_text())
    w = float(sweep["grid"][0]["w"])
    physics_path = CACHE / "surface_final_blind.f32"
    if not physics_path.exists():
        raise SystemExit("missing surface_final_blind.f32; run "
                         "scripts/run_wbg5_lane.py --stage final --blind")
    physics = np.fromfile(physics_path, dtype=np.float32).reshape(foot.shape)
    score, eligible = hybrid_score(physics, truth, w)
    order = place.suppression_order(score, foot & eligible & ~truth,
                                   d_min=D_MIN, max_n=BUDGET, keep_frac=0.05)
    dots = place.dots_from_order(order, BUDGET, foot.shape)
    pred = np.where(foot, np.where(dots, np.float32(1.0), np.float32(0.0)), np.nan).astype(np.float32)
    np.save(args.out, pred)
    dist = distance_transform_edt(~truth)
    print(json.dumps({
        "w": w, "dots": int(dots.sum()), "budget": BUDGET,
        "on_catalogue": int((dots & truth).sum()),
        "inside_ring_lt_3px": int((dist[dots] < RING_PX).sum()),
        "median_dist_to_catalogue_px": float(np.median(dist[dots])),
        "out": str(args.out),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
