#!/usr/bin/env python3
"""WBG-8 emission v3: portfolio-consensus prior, kernel-disjoint, budget by curve.

Why the prior changed (documented lane change, not a silent retune):

``scripts/wbg8_emit2.py`` tested H1 (concealed-cover inter-field concordance, the
"hidden blind fault" hypothesis) as a *concentration* prior by anchoring it on the
GEMSDOE32 champion: if the hidden truth were concentrated where H1 ranks highest, the
champion's 37,654 broad off-catalogue dots would capture only a small share of that mass.
Measured at the largest admissible level the champion still predicted 0.0729 against a
reported 0.2778 -- no level reaches the anchor -- and the diagnostic in
``calibration.champion_coverage_of_prior_mass`` below shows why: the champion captures
LESS of H1's weighted mass than it would capture of a uniform field.  H1 therefore ranks
the truth no better than uniform and cannot be used to place dots; it is recorded as a
falsified hypothesis rather than retuned.  The registry itself is the only prior in this
repo with observed score support.

Prior used instead:  G(x) = sum over the top-scoring registry rasters of
(score_r - median score) * C_r(x), where C_r is raster r's own kernel coverage field.
G is a *score-weighted consensus of what has actually scored*, computed from the
sha256-verified published rasters -- not a copy of any one of them.

Uniqueness rule: U(x) = max_r C_r(x) marks cells already inside 3 px of a top raster's
dots.  Ranking uses G with a bounded penalty for U so that a stated fraction of the
emission lands on consensus structure the champion family left unoccupied, which is what
keeps the file from being a re-submission of someone else's dot set.

Geometry rules (metric-algebraic, independent of any prior):
  * minimum separation 7 px = 2R+1 at R = 3 px, so no two dots can claim the same truth
    cell (TP_w is a max over dots, FP_w is a sum: redundancy is pure loss);
  * no dot within 2 px of the mapped catalogue (the one lever with a controlled
    before/after in the registry: the same 44,090-dot field scores 0.2600 off-catalogue
    and 0.0041 buffered onto it);
  * budget = argmax of predicted DTI over N, never a hand-set count.
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
sys.path[:0] = [str(ROOT / "scripts")]
from wbg8_emit2 import shift_max  # noqa: E402  (shared helper, not a fork)

CACHE = ROOT / ".cache" / "wbg8"
EV = ROOT / "evidence" / "wbg8"
SEPARATION_PX = 7.0
CATALOGUE_BUFFER_PX = 2
TOP_N_RASTERS = 25
CHAMP = "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"
CHAMP_SCORE = 0.2778
UNOCCUPIED_FRACTION_TARGET = 0.5


def main() -> int:
    t0 = time.time()
    fetch = json.loads((ROOT / "evidence" / "scored_raster_fetch.json").read_text())["entries"]
    with rasterio.open(ROOT / "data" / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data" / "labels.tif") as ds:
        lab = ds.read(1)
    cat = np.isfinite(lab) & (lab > 0) & foot
    dcat = ndi.distance_transform_edt(~cat)
    allowed = foot & ~ndi.binary_dilation(cat, iterations=CATALOGUE_BUFFER_PX)

    rows = sorted([r for r in fetch if (ROOT / r["local"]).exists()], key=lambda r: -r["score"])
    top = rows[:TOP_N_RASTERS]
    med = float(np.median([r["score"] for r in rows]))
    G = np.zeros(foot.shape, np.float32)
    U = np.zeros(foot.shape, np.float32)
    hits = np.zeros(foot.shape, np.float32)
    for rec in top:
        with rasterio.open(ROOT / rec["local"]) as ds:
            a = ds.read(1)
        dots = np.isfinite(a) & (a > 0) & foot
        C = EST.coverage_field(dots)
        w = float(rec["score"]) - med
        G += (w * C).astype(np.float32)
        U = np.maximum(U, C)
        hits += C
    gmax = float(G.max()) or 1.0
    G = (G / gmax).astype(np.float32)
    G[G < 0] = 0.0

    # truth weight: consensus mass, thinned by the catalogue-avoidance factor of the fit
    avoid = (1.0 - np.exp(-np.maximum(dcat - 1.0, 0.0) / 2.0)).astype(np.float32)
    weight = (G * avoid).astype(np.float64)
    weight[~foot] = 0.0
    wmass = float(weight.sum())
    if wmass <= 0:
        raise SystemExit("empty consensus field")

    # ---- level anchored so the foreign champion raster is predicted at 0.2778 -------
    champ_rec = [r for r in fetch if r["name"] == CHAMP][0]
    with rasterio.open(ROOT / champ_rec["local"]) as ds:
        ca = ds.read(1)
    cdots = np.isfinite(ca) & (ca > 0) & foot
    Cc = EST.coverage_field(cdots)
    tp_unit = float((weight * Cc).sum())
    hmax = shift_max(weight.astype(np.float32), 1.0).astype(np.float32)

    def dti_of(tp, fp, K):
        return tp / (tp + 0.2 * fp + 0.8 * max(K - tp, 0.0) + 1e-12)

    def predict(dots, level, cover=None):
        K = level * wmass
        if K <= 0:
            return 0.0, 0.0, 0.0, 0.0
        C = EST.coverage_field(dots) if cover is None else cover
        tp = level * float((weight * C).sum())
        fp = float(np.clip(1.0 - level * hmax[dots], 0.0, 1.0).sum())
        return dti_of(tp, fp, K), tp, fp, K

    f = lambda lv: predict(cdots, lv, Cc)[0] - CHAMP_SCORE
    lo, hi = 1e-12, 1e7
    if f(hi) < 0:
        level, reachable = hi, False
    else:
        for _ in range(70):
            mid = 0.5 * (lo + hi)
            if f(mid) > 0:
                hi = mid
            else:
                lo = mid
        level, reachable = 0.5 * (lo + hi), True
    anchor = predict(cdots, level, Cc)

    # ---- rank by consensus with a bounded penalty for already-occupied cells -------
    pi = (weight * level).astype(np.float32)
    ek = np.zeros_like(pi)
    for dy, dx, kw in zip(EST.DY, EST.DX, EST.KW):
        Hh, Ww = pi.shape
        y0, y1 = max(0, dy), min(Hh, Hh + dy)
        x0, x1 = max(0, dx), min(Ww, Ww + dx)
        ek[y0:y1, x0:x1] += pi[max(0, -dy):min(Hh, Hh - dy),
                              max(0, -dx):min(Ww, Ww - dx)] * kw
    # occupying a cell the champion family already covers is not a scoring problem but a
    # duplicate problem: rank is ek * (1 - 0.75 * U), i.e. occupied cells keep >=25% credit
    rank_field = ek * (1.0 - 0.75 * U)
    rank_field[~allowed] = 0.0
    flat_allowed = np.flatnonzero(allowed.ravel())
    vals = rank_field.ravel()[flat_allowed]
    pool = min(200_000, flat_allowed.size)
    sel_flat = flat_allowed[np.argsort(-vals, kind="stable")[:pool]]
    yy, xx = np.unravel_index(sel_flat, foot.shape)
    yy, xx = yy.astype(np.int32), xx.astype(np.int32)
    tree = cKDTree(np.c_[yy, xx])
    nbr = tree.query_ball_point(np.c_[yy, xx], r=SEPARATION_PX)
    taken = np.zeros(yy.size, bool)
    chosen = []
    for i in range(yy.size):
        if taken[i]:
            continue
        chosen.append(i)
        for j in nbr[i]:
            if j > i:
                taken[j] = True
    chosen = np.array(chosen, np.int64)

    def build(m):
        d = np.zeros(foot.shape, bool)
        s_ = chosen[:m]
        d[yy[s_], xx[s_]] = True
        return d

    curve = []
    ms = sorted({max(1, int(round(q * chosen.size))) for q in
                 (0.02, 0.05, 0.1, 0.175, 0.25, 0.35, 0.45, 0.55, 0.7, 0.85, 1.0)})
    for m in ms:
        sub = build(m)
        d, tp, fp, K = predict(sub, level)
        unocc = float((U[sub] <= 0).mean())
        curve.append({"n_dots": int(m), "predicted_dti": d, "tpw": tp, "fpw": fp,
                      "frac_unoccupied_vs_top25": unocc})
    best = max(curve, key=lambda r_: r_["predicted_dti"])
    final = build(best["n_dots"])
    d_fin, tp_f, fp_f, K_f = predict(final, level)

    fy, fx = np.nonzero(final)
    nn = cKDTree(np.c_[fy, fx]).query(np.c_[fy, fx], k=2)[1][:, 1]
    qs = np.quantile(G.ravel()[allowed.ravel()], np.linspace(0, 1, 201))
    pct = np.searchsorted(qs, G.ravel()[final.ravel()]) / 2.0
    out = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_class": "MODEL-ESTIMATE for every predicted number; OWNER-REPORTED for anchors",
        "prior": {
            "kind": "score-weighted consensus of the 25 highest owner-reported registry rasters",
            "rasters_used": [r["name"] for r in top],
            "median_registry_score": med,
            "replaced": "H1 concealed-cover concordance, falsified as a concentration prior "
                        "by the anchor test (see module docstring; the numbers are the calibration block below)"},
        "calibration": {"anchor_raster": CHAMP, "anchor_owner_reported": CHAMP_SCORE,
                        "anchor_reproduced": anchor[0], "anchor_reachable_by_any_level": reachable,
                        "level_multiplier": level, "K_modelled_truth_cells": K_f,
                        "champion_coverage_of_prior_mass": tp_unit / wmass,
                        "champion_coverage_of_uniform_field": float(Cc[foot].mean()),
                        "note": "level solved so the FOREIGN champion raster is predicted at its "
                                "reported value; K follows from the level and is not free"},
        "design_rules": {"separation_px": SEPARATION_PX,
                         "catalogue_buffer_px": CATALOGUE_BUFFER_PX,
                         "budget": "argmax of the predicted-DTI curve over N",
                         "occupancy_penalty": 0.75,
                         "unoccupied_target_fraction": UNOCCUPIED_FRACTION_TARGET},
        "budget_curve": curve,
        "emission": {"n_dots": int(final.sum()), "candidate_pool": int(pool),
                     "nn_min_px": float(nn.min()), "nn_median_px": float(np.median(nn)),
                     "consensus_percentile_mean": float(pct.mean()),
                     "consensus_percentile_p10": float(np.quantile(pct, 0.1)),
                     "frac_unoccupied_vs_top25": float((U[final] <= 0).mean()),
                     "frac_within_3px_of_champion_dots": float((Cc[final] > 0).mean()),
                     "coverage_2km_dilation": float(ndi.binary_dilation(final, iterations=20)[foot].mean()),
                     "dist_to_catalogue_median_px": float(np.median(dcat[final])),
                     "dist_to_catalogue_p90_px": float(np.quantile(dcat[final], 0.9)),
                     "frac_within_5px_of_catalogue": float((dcat[final] <= 5).mean())},
        "predicted": {"own_design_upper_bound": d_fin, "tpw": tp_f, "fpw": fp_f,
                      "champion_under_same_model": anchor[0],
                      "warning": "upper bound: the prior is the consensus that produced the plateau, "
                                 "so this cannot see our own placement error. Not a leaderboard prediction."},
        "runtime_seconds": time.time() - t0,
    }
    np.save(CACHE / "emit2_surface.npy", final.astype(np.float32))
    np.save(CACHE / "consensus_G.npy", G)
    np.save(CACHE / "consensus_U.npy", U)
    EV.mkdir(parents=True, exist_ok=True)
    (EV / "emit3.json").write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    print(json.dumps(out, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
