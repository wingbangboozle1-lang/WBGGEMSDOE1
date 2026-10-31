#!/usr/bin/env python3
"""WBG-8 emission v2: champion-anchored calibration + kernel-disjoint budget scan.

Two things were wrong with a naive allocation and both are fixed here, in the open:

1. *Level.* The shared allocator's accept bar is ``alpha*DTI/(1-alpha*DTI)`` evaluated on
   the surrogate's own running DTI.  With an uncalibrated probability level that surrogate
   DTI is ~0.003, the bar is ~0.0006 and every cell with any credit is accepted: the run in
   ``evidence/wbg8/emit.json`` emitted 27,356 dots whose nearest neighbour was 1 px away
   (a redundant blob, 7% area coverage).  Redundant dots are provably pure loss, because
   ``TP_w`` takes a *max* over dots while ``FP_w`` *sums* over them.
2. *Self-reference.* A truth model built from a susceptibility ranking scores its own
   ranking optimally by construction.  The level is therefore anchored on a *foreign*
   raster (the GEMSDOE32 champion, owner-reported 0.2778) and the model is used to compare
   budgets; the number it returns for our own emission is an upper bound, never a
   leaderboard prediction.

Design rules that are actually used:
  * cells ranked by expected kernel credit ``E[k]`` of the calibrated truth field;
  * no two dots within 7 px (= 2R+1 at R = 3 px): closer than that, two dots compete for
    the same truth cell and the pair wastes 0.2 of false-positive weight for nothing;
  * the budget is the argmax of the predicted-DTI curve over N, not a hand-set 37,654;
  * no dot within 2 px of the mapped catalogue (the champion's verified convention).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from wbg8 import estimator as EST  # noqa: E402

r = int(np.ceil(EST.RADIUS_PX))

CACHE = ROOT / ".cache" / "wbg8"
EV = ROOT / "evidence" / "wbg8"
SEPARATION_PX = 7.0
CATALOGUE_BUFFER_PX = 2
CHAMP = "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"
CHAMP_SCORE = 0.2778


def shift_max(a: np.ndarray, k: float) -> np.ndarray:
    """max over the kernel neighbourhood of ``a`` (no wraparound, unlike np.roll)."""
    H, W = a.shape
    out = np.zeros_like(a)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = float(np.hypot(dy, dx))
            w = max(1.0 - d / EST.RADIUS_PX, 0.0)
            if w <= 0:
                continue
            y0, y1 = max(0, -dy), min(H, H - dy)
            x0, x1 = max(0, -dx), min(W, W - dx)
            ty0, ty1 = max(0, dy), min(H, H + dy)
            tx0, tx1 = max(0, dx), min(W, W + dx)
            out[ty0:ty1, tx0:tx1] = np.maximum(out[ty0:ty1, tx0:tx1], a[y0:y1, x0:x1] * w)
    return out


def main() -> int:
    t0 = time.time()
    g = np.load(CACHE / "grid2.npz")
    gh = np.load(CACHE / "grid.npz")
    foot, z, centre, hab = g["foot"], g["z"], g["centre"], gh["pi_hab"]
    with rasterio.open(ROOT / "data" / "labels.tif") as ds:
        lab = ds.read(1)
    cat = np.isfinite(lab) & (lab > 0) & foot
    dcat = ndi.distance_transform_edt(~cat)
    allowed = foot & ~ndi.binary_dilation(cat, iterations=CATALOGUE_BUFFER_PX)

    s = float(json.loads((CACHE / "fit_params.json").read_text())["s"])
    cells_z = np.bincount((z + 1)[foot], minlength=centre.size + 1).astype(np.float64)
    wz = centre.astype(np.float64) ** s
    Z = float((wz * cells_z[1:]).sum())
    shape = np.zeros(centre.size + 1, np.float64)
    shape[1:] = wz / max(Z, 1e-12)
    weight = shape[z + 1] * (1.0 - np.exp(-np.maximum(dcat - 1.0, 0.0) / 2.0))
    weight[~foot] = 0.0
    weight = np.where(weight > 0, weight, 0.0).astype(np.float64)

    with rasterio.open(ROOT / "data" / "sample_submission.tif") as ds:
        n_foot = int(np.isfinite(ds.read(1)).sum())
    mass = float(weight.sum())
    if mass <= 0:
        raise SystemExit("empty weight field")

    hmax = shift_max(weight.astype(np.float32), 1.0).astype(np.float32)
    wmass = float(weight.sum())

    def predict(dots: np.ndarray, level: float, cover: np.ndarray | None = None):
        """DTI of ``dots`` under pi = level * weight.

        ``max`` commutes with a positive scalar, so the neighbourhood field is
        ``H = level * hmax`` and only the coverage field has to be rebuilt per design.
        """
        K = level * wmass
        if K <= 0:
            return 0.0, 0.0, 0.0, 0.0
        C = EST.coverage_field(dots) if cover is None else cover
        tp = level * float((weight * C).sum())
        fp = float(np.clip(1.0 - level * hmax[dots], 0.0, 1.0).sum())
        den = tp + 0.2 * fp + 0.8 * max(K - tp, 0.0) + 1e-12
        return tp / den, tp, fp, K

    # ---- anchor: level such that the champion raster scores its reported value ----
    rec = [r for r in json.loads((ROOT / "evidence" / "scored_raster_fetch.json").read_text())
           ["entries"] if r["name"] == CHAMP][0]
    with rasterio.open(ROOT / rec["local"]) as ds:
        ca = ds.read(1)
    cdots = np.isfinite(ca) & (ca > 0) & foot
    Cc = EST.coverage_field(cdots)
    lo, hi = 1e-12, 1.0e7
    f = lambda lv: predict(cdots, lv, Cc)[0] - CHAMP_SCORE
    if f(hi) < 0:
        level = hi
    else:
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if f(mid) > 0:
                hi = mid
            else:
                lo = mid
        level = 0.5 * (lo + hi)
    anchor = predict(cdots, level, Cc)

    # ---- rank cells by expected kernel credit, then thin to kernel-disjointness ---
    pi_full = weight.astype(np.float32)
    ek = np.zeros_like(pi_full)
    for dy, dx, kw in zip(EST.DY, EST.DX, EST.KW):
        y0, y1 = max(0, dy), min(foot.shape[0], foot.shape[0] + dy)
        x0, x1 = max(0, dx), min(foot.shape[1], foot.shape[1] + dx)
        ek[y0:y1, x0:x1] += pi_full[max(0, -dy):min(foot.shape[0], foot.shape[0] - dy),
                                    max(0, -dx):min(foot.shape[1], foot.shape[1] - dx)] * kw
    ek[~allowed] = 0.0
    flat_allowed = np.flatnonzero(allowed.ravel())
    vals = ek.ravel()[flat_allowed]
    n_max = min(120_000, flat_allowed.size)
    sel_flat = flat_allowed[np.argsort(-vals, kind="stable")[:n_max]]
    yy, xx = np.unravel_index(sel_flat, foot.shape)
    yy, xx = yy.astype(np.int32), xx.astype(np.int32)
    tree = cKDTree(np.c_[yy, xx])
    nbr = tree.query_ball_point(np.c_[yy, xx], r=SEPARATION_PX)
    taken = np.zeros(n_max, bool)
    chosen = []
    for i in range(n_max):
        if taken[i]:
            continue
        chosen.append(i)
        for j in nbr[i]:
            if j > i:
                taken[j] = True
    chosen = np.array(chosen, np.int64)

    def build(m: int) -> np.ndarray:
        d = np.zeros(foot.shape, bool)
        s_ = chosen[:m]
        d[yy[s_], xx[s_]] = True
        return d

    curve = []
    for m in sorted({max(1, int(round(q * chosen.size))) for q in
                     (0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0)}):
        sub = build(m)
        d, tp, fp, K = predict(sub, level)
        curve.append({"n_dots": int(m), "predicted_dti": d, "tpw": tp, "fpw": fp,
                      "K_modelled_truth_cells": K})
    best = max(curve, key=lambda r_: r_["predicted_dti"])
    final = build(best["n_dots"])
    d_fin, tp_f, fp_f, K_f = predict(final, level)
    champion_estimate_same_curve = anchor[0]

    fy, fx = np.nonzero(final)
    nn = cKDTree(np.c_[fy, fx]).query(np.c_[fy, fx], k=2)[1][:, 1]
    habf = hab.ravel()
    qs = np.quantile(habf[allowed.ravel()], np.linspace(0, 1, 201))
    pct = np.searchsorted(qs, habf[final.ravel()]) / 2.0
    out = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_class": "MODEL-ESTIMATE for every predicted number",
        "calibration": {"anchor_raster": CHAMP, "anchor_owner_reported": CHAMP_SCORE,
                        "anchor_reproduced_by_model": champion_estimate_same_curve,
                        "level_multiplier": level, "susceptibility_mass": mass,
                        "K_modelled_truth_cells": K_f, "tilt_s": s,
                        "note": ("level solved by bisection so the foreign champion raster is "
                                 "predicted at its reported value; K follows, it is not free")},
        "design_rules": {"separation_px": SEPARATION_PX,
                         "separation_rationale": "2R+1 at R=3 px makes the kernels disjoint, so no two dots compete for one truth cell",
                         "catalogue_buffer_px": CATALOGUE_BUFFER_PX,
                         "budget": "argmax of the predicted-DTI curve over N",
                         "shared_allocator_status": ("measured and rejected for this field; see "
                                                      "evidence/wbg8/emit.json")},
        "budget_curve": curve,
        "emission": {"n_dots": int(final.sum()),
                     "candidate_pool_top_n": int(n_max),
                     "nn_min_px": float(nn.min()), "nn_median_px": float(np.median(nn)),
                     "habitat_percentile_mean": float(pct.mean()),
                     "habitat_percentile_p10": float(np.quantile(pct, 0.1)),
                     "coverage_2km_dilation": float(ndi.binary_dilation(final, iterations=20)[foot].mean()),
                     "dist_to_catalogue_median_px": float(np.median(dcat[final])),
                     "dist_to_catalogue_p90_px": float(np.quantile(dcat[final], 0.9)),
                     "frac_within_5px_of_catalogue": float((dcat[final] <= 5).mean()),
                     "footprint_cells": n_foot},
        "predicted": {"own_design_upper_bound": d_fin, "tpw": tp_f, "fpw": fp_f,
                      "champion_same_model": champion_estimate_same_curve,
                      "warning": ("upper bound: the truth field is built from the same ranking used "
                                  "to place these dots, so the estimator cannot see our own "
                                  "placement error. Not a leaderboard prediction.")},
        "runtime_seconds": time.time() - t0,
    }
    np.save(CACHE / "emit2_surface.npy", final.astype(np.float32))
    EV.mkdir(parents=True, exist_ok=True)
    (EV / "emit2.json").write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    print(json.dumps(out, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
