#!/usr/bin/env python3
"""Score any candidate GeoTIFF with the calibrated WBG-8 truth model.

    .venv/bin/python scripts/wbg8_estimate.py <file.tif> [--compare <other.tif> ...]

Prints one labelled JSON object per file: the MODEL-ESTIMATE DTI from
evidence/wbg8/fit.json's fitted truth field, its leave-one-family-out uncertainty,
the emission descriptors that drive it, and the owner-reported value of the closest
registry file by dot overlap. It never claims an organizer score and never uploads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from wbg8 import estimator as EST  # noqa: E402
from gems57.uniqueness import dot_overlap  # noqa: E402

CACHE = ROOT / ".cache" / "wbg8"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def estimate(path: Path, ctx: dict) -> dict:
    with rasterio.open(path) as ds:
        a = ds.read(1)
        crs, transform, shape = str(ds.crs), list(ds.transform)[:6], ds.shape
    foot, grid = ctx["foot"], ctx["grid"]
    if shape != foot.shape:
        raise SystemExit(f"{path.name}: shape {shape} != competition grid {foot.shape}")
    inside = np.isfinite(a)
    vals = a[inside & foot]
    dots = inside & (a > 0) & foot
    n = int(dots.sum())
    if n == 0:
        return {"file": path.name, "error": "no positive finite cell inside the footprint"}
    C = EST.coverage_field(dots)
    nz = np.flatnonzero(C.ravel() > 0)
    A = np.bincount(((grid["z"] + 1) * EST.N_DCAT + grid["dcat_band"]).ravel()[nz],
                     weights=C.ravel()[nz], minlength=(int(grid["z"].max()) + 2) * EST.N_DCAT)
    tp = float((ctx["pi_bin"] * A.reshape(ctx["pi_bin"].shape)).sum())
    fp = float(ctx["exp_neg_L"][dots.ravel()].sum())
    k_tot = ctx["k_total"]
    dti = float(EST.dti_from(np.array([tp]), np.array([fp]), np.array([k_tot]), np.array([n]))[0])
    dv = ctx["dcat"][dots]
    best = {"ov": -1.0, "name": None, "jac": None, "score": None}
    for r in ctx["registry"]:
        their = np.unpackbits(r["dots_packed"]).astype(bool).reshape(dots.shape)
        o = float(dot_overlap(dots, their))
        if o > best["ov"]:
            best = {"ov": o, "name": r["name"], "score": r["score"],
                    "jac": float((dots & their).sum() / max((dots | their).sum(), 1))}
    ov, near_name, near_jac = best["ov"], best["name"], best["jac"]
    near = {"name": best["name"], "score": best["score"]}
    return {
        "file": path.name, "sha256": sha(path),
        "registry_overlap": {"max_frac_within_3px": ov, "against": near_name,
                             "jaccard_dot_sets_against_that_file": near_jac,
                             "literal_limit": 0.70,
                             "note": "dense registry rasters make the literal 3 px rule "
                                     "degenerate (AGENTS.md 0b(ii)); Jaccard is the copy test"},
        "grid": {"crs": crs, "transform": transform, "shape": list(shape),
                 "grid_matches_official_template": bool(
                     crs == ctx["ref"]["crs"] and transform == ctx["ref"]["transform"]
                     and list(shape) == ctx["ref"]["shape"])},
        "format": {"bands": 1, "dtype": str(a.dtype),
                   "values_in_0_1": bool(vals.size and vals.min() >= 0 and vals.max() <= 1),
                   "value_min": float(vals.min()), "value_max": float(vals.max()),
                   "nan_inside_footprint": int((~inside & foot).sum()),
                   "outside_footprint_nonzero": int((a[~foot] > 0).sum() if a[~foot].size else 0)},
        "emission": {"n_dots": n, "frac_on_catalogue": float((dots & ctx["cat"]).sum() / n),
                     "frac_within_3px_of_catalogue": float((dv <= 3).mean()),
                     "dist_median_px": float(np.median(dv)), "dist_p90_px": float(np.quantile(dv, 0.9)),
                     "cluster_frac": float((ndi.convolve(
                         dots.astype(np.float32), np.ones((7, 7), np.float32),
                         mode="constant")[dots] - 1.0 > 3).mean()),
                     "n_components": int(ndi.label(dots, structure=np.ones((3, 3)))[1])},
        "score_estimate": {
            "evidence_class": "MODEL-ESTIMATE", "value": dti,
            "interval": [max(0.0, dti - ctx["mae"]), min(0.999, dti + ctx["mae"])],
            "uncertainty_source": "leave-one-family-out MAE on the 118 owner-reported scores",
            "components": {"tpw": tp, "fpw": fp, "K_truth_cells_modelled": k_tot},
            "not_an_organizer_score": True},
        "nearest_registry_file": {"name": near["name"], "overlap_3px": ov,
                                  "owner_reported": near["score"]},
        "unique_vs_owner_scored_portfolio": bool(ov <= 0.70),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", type=Path, nargs="+")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    g = np.load(CACHE / "grid2.npz")
    fit = json.loads((ROOT / "evidence" / "wbg8" / "fit.json").read_text())
    params = json.loads((CACHE / "fit_params.json").read_text())
    pi_bin = np.load(CACHE / "fit_bin.npz")["pi_bin"]
    with rasterio.open(ROOT / "data" / "sample_submission.tif") as ds:
        smp = ds.read(1)
        ref = {"crs": str(ds.crs), "transform": list(ds.transform)[:6], "shape": list(ds.shape)}
    foot = np.isfinite(smp)
    with rasterio.open(ROOT / "data" / "labels.tif") as ds:
        lab = ds.read(1)
    cat = np.isfinite(lab) & (lab > 0) & foot
    full = pi_bin[g["z"] + 1, g["dcat_band"]].astype(np.float32)
    full[~foot] = 0.0
    H, W = full.shape
    L = np.zeros_like(full, np.float64)
    for dy, dx, kw in zip(EST.DY, EST.DX, EST.KW):
        y0, y1 = max(0, dy), min(H, H + dy)
        x0, x1 = max(0, dx), min(W, W + dx)
        L[y0:y1, x0:x1] += full[max(0, -dy):min(H, H - dy), max(0, -dx):min(W, W - dx)] * kw
    fetch = json.loads((ROOT / "evidence" / "scored_raster_fetch.json").read_text())["entries"]
    registry = []
    for rec in fetch:
        p = ROOT / rec["local"]
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            arr = ds.read(1)
        # 3 GB sandbox: holding 118 float32 rasters is 5.8 GB and gets the process OOM-killed.
        # The only thing the estimator needs from them is the dot mask, so it is stored packed
        # (1.5 MB per raster instead of 49 MB) and unpacked per comparison.
        dots = np.isfinite(arr) & (arr > 0)
        registry.append({"name": rec["name"], "score": float(rec["score"]),
                         "dots_packed": np.packbits(dots.ravel())})
    ctx = {"foot": foot, "cat": cat, "dcat": ndi.distance_transform_edt(~cat), "ref": ref,
           "grid": {"z": g["z"], "dcat_band": g["dcat_band"]}, "pi_bin": pi_bin,
           "exp_neg_L": np.exp(-L).astype(np.float32).ravel(),
           "k_total": float(full.sum()),
           "mae": fit["grouped_holdout_family"]["mae_mean_heldout"] or fit["in_sample"]["mae"],
           "registry": registry}
    out = {"generated_utc": __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": {"fitted": params, "truth_model": fit["truth_model"],
                  "champion_owner_reported": 0.2778,
                  "estimator_value_for_champion": fit["champion_check"]["model_estimate"]},
        "results": [estimate(p, ctx) for p in a.files]}
    text = json.dumps(out, indent=1, allow_nan=False, default=float)
    print(text)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
