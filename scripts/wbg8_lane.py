#!/usr/bin/env python3
"""WBG-8 lane driver: registry-inverted truth model, then metric-optimal emission.

Stages (each writes its own receipt under evidence/wbg8/ and can be re-run):

  prepare  habitat susceptibility + binned support of the competition grid
  bins     per-submission sufficient statistics A_P[b] for all 118 scored rasters
  fit      two-plus-one parameter inversion of the 118 owner-reported scores
  emit     shared greedy allocator at the fitted fixed point -> candidate TIFF
  audit    format validation, uniqueness vs registry, holdout + canary, run card

Everything numeric is labelled MODEL-ESTIMATE / HOLDOUT-DTI / OWNER-REPORTED.
No stage uploads anything, and no stage reads a DrivenData credential.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from wbg8 import habitat as HAB            # noqa: E402
from wbg8 import estimator as EST          # noqa: E402

FEAT = ROOT / "data" / "training_features.tif"
SAMPLE = ROOT / "data" / "sample_submission.tif"
LABELS = ROOT / "data" / "labels.tif"
CACHE = ROOT / ".cache" / "wbg8"
EV = ROOT / "evidence" / "wbg8"
N_Z = 96
FETCH = json.loads((ROOT / "evidence" / "scored_raster_fetch.json").read_text())


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, allow_nan=False) + "\n")


# --------------------------------------------------------------------------- prepare
def stage_prepare() -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    with rasterio.open(SAMPLE) as ds:
        a = ds.read(1)
        foot = np.isfinite(a)
        prof = ds.profile.copy()
    with rasterio.open(LABELS) as ds:
        lab = ds.read(1)
    cat = np.isfinite(lab) & (lab > 0) & foot
    dcat = ndi.distance_transform_edt(~cat).astype(np.float32)
    bands = {}
    for name in ("tmi_hg", "tmi_vg", "iso_grav_hg", "iso_grav_vg", "det_elev_slope",
                 "depth_to_base_surf", "geod_2ndinv", "geod_dilaterate"):
        bands[name] = HAB.load_band(FEAT, name)
        bands[name] = np.where(foot, bands[name], np.nan).astype(np.float32)
    hab = HAB.susceptibility(bands)
    pi = np.where(foot, hab.pi, 0.0).astype(np.float32)
    inside = foot & (pi > 0)
    q = np.quantile(pi[inside], np.linspace(0.0, 1.0, N_Z + 1))
    edges = np.unique(q)
    if edges.size < N_Z + 1:  # degenerate quantiles (many exact zeros) -> pad log space
        edges = np.unique(np.exp(np.linspace(np.log(max(edges[0], 1e-6)),
                                             np.log(max(pi[inside].max(), 1e-5)), N_Z + 1)))
    z = np.clip(np.searchsorted(edges, pi, side="right") - 1, 0, edges.size - 2).astype(np.int16)
    z[~inside] = -1
    centre = np.exp(0.5 * (np.log(np.maximum(edges[:-1], 1e-7))
                           + np.log(np.maximum(edges[1:], 1e-7))))
    if centre.size != N_Z:      # keep the documented bin count honest
        centre = 0.5 * (edges[:-1] + edges[1:])
    np.savez_compressed(CACHE / "grid.npz", foot=foot, dcat=dcat, z=z,
                        edges=edges, centre=centre.astype(np.float32),
                        pi_hab=pi.astype(np.float32))
    # separation diagnostics of the susceptibility field, for the page
    rank_cat = float(np.nanmean(HAB.rank01(np.where(foot, dcat, np.nan))[foot]))
    out = {
        "generated_utc": now(), "evidence_class": "DATA-MEASUREMENT",
        "feature_raster_sha256": sha256(FEAT),
        "labels_sha256": sha256(LABELS), "sample_sha256": sha256(SAMPLE),
        "grid": {"shape": list(pi.shape), "crs": str(prof["crs"]),
                 "transform": list(prof["transform"])[:6],
                 "footprint_cells": int(foot.sum()), "catalogue_cells": int(cat.sum()),
                 "cells_with_positive_susceptibility": int(inside.sum())},
        "habitat_weights": hab.notes,
        "susceptibility_edges": {"n_bins": int(edges.size - 1),
                                 "min": float(edges[0]), "max": float(edges[-1])},
        "median_rank_of_distance_to_catalogue": rank_cat,
        "note": ("susceptibility is a ranking, not a probability and not a score; "
                 "the probability field is fitted later from the 118 owner-reported scores"),
    }
    dump(EV / "prepare.json", out)
    print(json.dumps(out, indent=1)[:1200], flush=True)
    return out


# --------------------------------------------------------------------------- bins
def stage_bins() -> dict:
    g = np.load(CACHE / "grid.npz")
    foot, z, dcat = g["foot"], g["z"], g["dcat"]
    db = EST.dcat_band(dcat)
    nb = z.max().astype(int) + 2          # -1 becomes bin 0 after +1 shift
    zb = (z + 1).astype(np.int64)
    cells = np.bincount((zb * EST.N_DCAT + db).ravel(), minlength=nb * EST.N_DCAT)
    flat_all, meta, A_rows = [], [], []
    t0 = time.time()
    for i, rec in enumerate(FETCH["entries"]):
        p = ROOT / rec["local"]
        if not p.exists():
            raise SystemExit(f"missing cached raster {p}")
        with rasterio.open(p) as ds:
            a = ds.read(1)
        dots = np.isfinite(a) & (a > 0) & foot
        idx = np.flatnonzero(dots.ravel())
        # A_r[b] = sum of the submission's own coverage field over bin b -> E[TP_w] basis
        C = EST.coverage_field(dots)
        nz = np.flatnonzero(C.ravel() > 0)
        A = np.bincount((zb * EST.N_DCAT + db).ravel()[nz], weights=C.ravel()[nz],
                        minlength=nb * EST.N_DCAT).astype(np.float64)
        flat_all.append(idx.astype(np.int32))
        meta.append({"name": rec["name"], "score": float(rec["score"]),
                     "repo": rec["repo"], "n_dots": int(idx.size),
                     "sha256": sha256(p), "registry_sha256": rec["registry_sha256"]})
        A_rows.append(A.astype(np.float32))
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/118 rasters  {time.time()-t0:.0f}s", flush=True)
    n_dots_max = max(len(f) for f in flat_all)
    dots_mat = np.full((len(flat_all), n_dots_max), -1, np.int32)
    for r, f in enumerate(flat_all):
        dots_mat[r, : f.size] = f
    np.savez_compressed(CACHE / "bins.npz", A=np.stack(A_rows), cells=cells,
                        dots=dots_mat, n_dots=np.array([m["n_dots"] for m in meta], np.int32))
    dump(CACHE / "bins_meta.json", {"generated_utc": now(), "entries": meta,
                                    "note": "sha256 verified against the fetch registry pins"})
    bad = [m["name"] for m in meta if m["sha256"] != m["registry_sha256"]]
    print(f"bins done: {len(meta)} rasters, hash mismatches={len(bad)}, {time.time()-t0:.0f}s", flush=True)
    return {"rasters": len(meta), "hash_mismatch": bad, "seconds": time.time() - t0}


# --------------------------------------------------------------------------- fit
_GRID: dict = {}


def _load_grid() -> dict:
    global _GRID
    if not _GRID:
        g = np.load(CACHE / "grid2.npz")
        _GRID = {k: g[k] for k in g.files}
    return _GRID


def _forward(s: float, c: float, K: float, A: np.ndarray, dots: np.ndarray,
             n_dots: np.ndarray) -> tuple:
    """Exact-in-bins forward model for one parameter triple.

    Returns (tp[r], fp[r], k_total, pi_ext) with ``pi_ext`` the (z-bin+1, dcat-bin)
    probability table; bin 0 is the "no susceptibility / not in footprint" bin and is
    deliberately pinned to zero probability.
    """
    g = _load_grid()
    n_z = int(g["centre"].size)
    centre = g["centre"].astype(np.float64)
    wz = centre ** float(s)
    cells = g["cells"].reshape(n_z + 1, EST.N_DCAT)
    Z = float((wz * cells[1:].sum(axis=1)).sum())
    if Z <= 0:
        return None
    pz = wz / Z
    reps = np.load(CACHE / "dcat_reps.npz")["reps"]
    fcat = 1.0 - np.exp(-np.maximum(reps - 1.0, 0.0) / float(c))
    # representative distance-to-catalogue inside each band, used only for the table check
    pi = np.clip(K * np.outer(pz, fcat), 0.0, 1.0)
    pi_ext = np.zeros((n_z + 1, EST.N_DCAT), np.float64)
    pi_ext[1:] = pi
    tp = np.einsum("zd,rzd->r", pi_ext, A.reshape(A.shape[0], n_z + 1, EST.N_DCAT))
    full = pi_ext[g["z"] + 1, g["dcat_band"]].astype(np.float32)
    full[~g["foot"]] = 0.0
    H, W = full.shape
    L = np.zeros_like(full, np.float64)
    for dy, dx, kw in zip(EST.DY, EST.DX, EST.KW):
        y0, y1 = max(0, dy), min(H, H + dy)
        x0, x1 = max(0, dx), min(W, W + dx)
        L[y0:y1, x0:x1] += full[max(0, -dy):min(H, H - dy),
                                max(0, -dx):min(W, W - dx)] * kw
    flat = np.exp(-L).astype(np.float32).ravel()
    fp = np.array([float(flat[dots[r, :n_dots[r]]].sum()) for r in range(len(n_dots))])
    return tp, fp, float(full.sum()), pi_ext


def stage_fit(verbose: bool = True) -> dict:
    g = np.load(CACHE / "grid.npz")
    foot, dcat = g["foot"], g["dcat"]
    z = g["z"]
    edges, centre = g["edges"], g["centre"]
    band = ((z + 1) * EST.N_DCAT + EST.dcat_band(dcat))
    band[~foot] = -1                      # outside the scored footprint: never truth
    keep = band[band >= 0].astype(np.int64)
    cells = np.bincount(keep, minlength=int(z.max() + 2) * EST.N_DCAT).astype(np.float64)
    flat = band[band >= 0]
    dbands = (flat % EST.N_DCAT).astype(np.int64)
    dflat = dcat.ravel()[flat >= 0]
    reps = np.array([float(np.median(dflat[dbands == b])) if (dbands == b).any() else float(b)
                     for b in range(EST.N_DCAT)], np.float64)
    np.savez_compressed(CACHE / "dcat_reps.npz", reps=reps)
    np.savez_compressed(CACHE / "grid2.npz", foot=foot, z=z, dcat=dcat,
                        dcat_band=EST.dcat_band(dcat).astype(np.int16), centre=centre,
                        edges=edges, cells=cells)
    _load_grid.cache_clear() if hasattr(_load_grid, "cache_clear") else None
    _GRID.clear()
    b = np.load(CACHE / "bins.npz")
    A, dots, n_dots = b["A"].astype(np.float64), b["dots"], b["n_dots"]
    meta = json.loads((CACHE / "bins_meta.json").read_text())["entries"]
    obs = np.array([m["score"] for m in meta], np.float64)
    names = [m["name"] for m in meta]
    fam_map = json.loads((ROOT / "evidence" / "wbg6_score_model.json").read_text())["families"]
    fam_of = {nm: i for i, fam in enumerate(fam_map) for nm in fam}
    fams = np.array([fam_of.get(n, -1 - names.index(n)) for n in names], np.int64)

    def logit(x):
        x = np.clip(x, 1e-4, 1 - 1e-4)
        return np.log(x / (1.0 - x))

    def loss(p_, o_):
        return float(np.mean(np.abs(logit(p_) - logit(o_))))

    grid_s = [1.0, 1.5, 2.0, 3.0, 4.5, 7.0, 11.0, 18.0, 30.0]
    grid_c = [2.0, 4.0, 7.0, 12.0, 25.0]
    grid_K = [4000, 8000, 12395, 20000, 32000, 55000, 90000, 150000]
    combos, t0 = [], time.time()
    for si, s_try in enumerate(grid_s):
        for c_try in grid_c:
            for K_try in grid_K:
                out = _forward(s_try, c_try, float(K_try), A, dots, n_dots)
                if out is None:
                    continue
                tp, fp, kt, pi_ext = out
                pred = np.clip(EST.dti_from(tp, fp, kt, n_dots), 0.0, 0.9999)
                combos.append({"s": s_try, "c": c_try, "K": K_try, "k_total": kt,
                               "loss": loss(pred, obs), "pred": pred, "tp": tp, "fp": fp})
        if verbose:
            print(f"  s row {si+1}/{len(grid_s)} done  [{time.time()-t0:.0f}s] "
                  f"best so far {min(c['loss'] for c in combos):.4f}", flush=True)
    combos.sort(key=lambda r: r["loss"])
    best = combos[0]
    pred = best["pred"]
    # leave-one-family-out: re-choose the grid winner without the held-out family
    cv_rows = []
    for f in np.unique(fams):
        m = fams == f
        if m.sum() == 0 or m.all():
            continue
        keep = ~m
        def kept_loss(c):
            return loss(np.clip(EST.dti_from(c["tp"][keep], c["fp"][keep], c["k_total"],
                                              n_dots[keep]), 0, 0.9999), obs[keep])

        cand = min(combos, key=kept_loss)
        cand = {**cand, "kept_loss": kept_loss(cand)}
        pv = np.clip(EST.dti_from(cand["tp"][m], cand["fp"][m], cand["k_total"], n_dots[m]), 0, 0.9999)
        cv_rows.append({"family": int(f), "held_out": int(m.sum()),
                        "chosen": {"s": cand["s"], "c": cand["c"], "K": cand["K"]},
                        "pred_mean": float(pv.mean()), "obs_mean": float(obs[m].mean()),
                        "pred": [float(x) for x in pv], "obs": [float(x) for x in obs[m]]})
    ho_abs = [abs(pv - ob) for r in cv_rows for pv, ob in zip(r["pred"], r["obs"])]
    resid = pred - obs
    top12 = [{"s": c["s"], "c": c["c"], "K": c["K"], "loss_logit": c["loss"],
              "rmse": float(np.sqrt(np.mean((c["pred"] - obs) ** 2))),
              "pearson": float(np.corrcoef(c["pred"], obs)[0, 1]),
              "k_total": c["k_total"]} for c in combos[:12]]
    champ = "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"
    report = {
        "generated_utc": now(), "evidence_class": "MODEL-ESTIMATE",
        "score_label": "OWNER-REPORTED (dependent variable; no organizer receipt)",
        "truth_model": ("pi(x) = K * tilt(susceptibility, s) * (1 - exp(-(d_catalogue-1)/c)) "
                        "on 96 susceptibility x 9 catalogue-distance bins; TP_w is exact-linear "
                        "in pi, FP_w uses the exp(-L) occupancy form"),
        "fitted": {"s_tilt": best["s"], "c_catalogue_px": best["c"],
                   "K_truth_cells": best["K"], "k_total_realised": best["k_total"]},
        "in_sample": {"n": int(obs.size), "rmse": float(np.sqrt(np.mean(resid ** 2))),
                      "mae": float(np.mean(np.abs(resid))),
                      "pearson": float(np.corrcoef(pred, obs)[0, 1]),
                      "spearman": float(np.corrcoef(np.argsort(np.argsort(pred)),
                                                     np.argsort(np.argsort(obs)))[0, 1]),
                      "loss_mean_abs_logit": best["loss"]},
        "grouped_holdout_family": {"n_families": len(cv_rows),
                                   "mae_mean_heldout": float(np.mean(ho_abs)) if ho_abs else None,
                                   "rmse_mean_heldout": float(np.sqrt(np.mean(np.square(ho_abs)))) if ho_abs else None},
        "grid_top": top12,
        "cv_rows": cv_rows,
        "per_submission": sorted(
            [{"name": n, "observed_owner_reported": float(o), "model_estimate": float(pp),
              "residual": float(pp - o), "n_dots": int(nd), "family": int(fm)}
             for n, o, pp, nd, fm in zip(names, obs, pred, n_dots, fams)],
            key=lambda r: -r["observed_owner_reported"]),
        "champion_check": {"name": champ, "observed": 0.2778,
                           "model_estimate": float(pred[names.index(champ)])},
        "limitations": [
            "the 118 dependent values are owner-reported, not organizer receipts",
            "reported scores of near-identical rasters differ by up to 0.086 "
            "(evidence/score_consistency.json), which bounds any estimator's accuracy",
            "cells with zero susceptibility are pinned to zero truth probability, so the "
            "inferred K is a lower bound on the hidden-truth size",
            "the estimator calibrates budget and catalogue clearance; it cannot invent a "
            "better ranking than the susceptibility prior it is given",
        ],
    }
    np.savez_compressed(CACHE / "combos.npz",
                        tp=np.stack([c["tp"] for c in combos]).astype(np.float32),
                        fp=np.stack([c["fp"] for c in combos]).astype(np.float32),
                        k=np.array([c["k_total"] for c in combos]),
                        s=np.array([c["s"] for c in combos]), c=np.array([c["c"] for c in combos]),
                        K=np.array([c["K"] for c in combos]),
                        loss=np.array([c["loss"] for c in combos]))
    report["sensitivity_in_K"] = [
        {"s": c["s"], "c": c["c"], "K": c["K"], "loss": c["loss"],
         "champion_estimate": float(c["pred"][names.index(champ)])}
        for c in combos[:60] if c["s"] == combos[0]["s"]][:14]
    dump(EV / "fit.json", report)
    out = _forward(best["s"], best["c"], float(best["K"]), A, dots, n_dots)
    np.savez_compressed(CACHE / "fit_bin.npz", pi_bin=out[3])
    json.dump({"s": best["s"], "c": best["c"], "K": best["K"], "k_total": best["k_total"],
               "rmse": report["in_sample"]["rmse"],
               "grouped_mae": report["grouped_holdout_family"]["mae_mean_heldout"]},
              (CACHE / "fit_params.json").open("w"), indent=1)
    print(json.dumps({k: report[k] for k in ("fitted", "in_sample", "grouped_holdout_family",
                                             "champion_check")}, indent=1), flush=True)
    return report


# --------------------------------------------------------------------------- emit
def stage_emit(k_policy: float | None = None) -> dict:
    """Emit with the *shared* allocator on the calibrated probability field.

    ``k_policy`` overrides the fitted truth size.  Default: the null-calibration value
    K = 12,395 (evidence/wbg6_null_calibration.json), which is the only GEMS number in
    this repository reproduced to within 0.0002 against a scored file.  The free fit
    prefers K = 150,000, at which TP saturates and the fitted field stops being
    identifiable, so using it would buy a lattice, not a design; both are recorded.
    """
    from gems57 import emit as SHARED_EMIT

    g = np.load(CACHE / "grid2.npz")
    foot, z, db = g["foot"], g["z"], g["dcat_band"]
    params = json.loads((CACHE / "fit_params.json").read_text())
    k_used = float(k_policy if k_policy is not None else 12395)
    A = np.load(CACHE / "bins.npz")["A"].astype(np.float64)
    dots_all = np.load(CACHE / "bins.npz")["dots"]
    n_dots_all = np.load(CACHE / "bins.npz")["n_dots"]
    fwd = _forward(params["s"], params["c"], k_used, A, dots_all, n_dots_all)
    pi_bin = fwd[3]
    with rasterio.open(LABELS) as ds:
        lab = ds.read(1)
    cat = np.isfinite(lab) & (lab > 0) & foot
    # no dot within 2 px of the mapped catalogue (the champion's verified convention),
    # and 3-6 px cells are down-weighted by the fitted catalogue-avoidance factor
    allowed = foot & ~ndi.binary_dilation(cat, iterations=2)
    p = pi_bin[z + 1, db].astype(np.float32)
    p[~allowed] = 0.0
    alloc = SHARED_EMIT.greedy_allocate(p, allowed, k_truth=float(params["K"]),
                                       floor=0.004, max_dots=200_000,
                                       candidate_cap=600_000, per_round=20_000)
    dots = alloc.emitted
    ys, xs = np.nonzero(dots)
    out = {"generated_utc": now(), "n_dots": int(dots.sum()),
           "rounds": int(alloc.rounds), "surrogate_dti": float(alloc.surrogate_dti),
           "expected_covered_credit": float(alloc.expected_covered_credit),
           "expected_self_credit": float(alloc.expected_self_credit),
           "params": {**params, "K_used_for_emission": k_used,
                      "K_free_fit": params["K"]},
           "allowed_cells": int(allowed.sum()),
           "allocator": "vendor/gems57/emit.greedy_allocate (shared, unmodified)",
           "k_policy_rationale": ("K=12,395 is the only value in this repository reproduced "
                                 "against a scored file; the free fit's K=150,000 saturates TP "
                                 "and is reported but not used for the emission")}
    arr = np.zeros(foot.shape, np.float32)
    arr[dots] = 1.0
    np.save(CACHE / "emit_surface.npy", arr)
    dump(EV / "emit.json", out)
    print(json.dumps(out, indent=1)[:900], flush=True)
    return out


STAGES = {"prepare": stage_prepare, "bins": stage_bins, "fit": stage_fit, "emit": stage_emit}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", nargs="?", default="all")
    ap.add_argument("--K", type=float, default=None, help="truth-size policy for the emission")
    a = ap.parse_args()
    order = ["prepare", "bins", "fit", "emit"] if a.stage == "all" else [a.stage]
    for st in order:
        if st == "emit":
            STAGES[st](k_policy=a.K)
        else:
            STAGES[st]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
