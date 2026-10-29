#!/usr/bin/env python3
"""Structure audit of the owner-reported scored GEMSDOE rasters (118 registry entries).

Purpose: explain *why* the high-scoring files score high, using only quantities that can
be recomputed from the locally pinned rasters, the restored public catalogue, and the
owner-reported scores. Nothing here is an organizer receipt or a leaderboard forecast.

Outputs
-------
evidence/focus_structure_audit.json   per-raster features, rank correlations (bootstrap CI),
                                      and pairwise overlap among the nine focus-site files.

Every number is labelled:
  * scores      -> OWNER-REPORTED (registry brief; never ORGANIZER-CONFIRMED)
  * features    -> COMPUTED from the pinned rasters and the owner-mirror catalogue
  * correlation -> descriptive only (n = 118 files, ~22 families; not a predictive claim)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57.grid import load_grid  # noqa: E402  (shared template loader, unchanged)
from gems57.uniqueness import dot_overlap  # noqa: E402  (shared literal overlap rule)

REG = ROOT / "registry/wbg_h1/scored_registry.json"
FETCH = ROOT / "evidence/scored_raster_fetch.json"
OUT = ROOT / "evidence/focus_structure_audit.json"
FOCUS_SITES = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
               "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def features_for(path: Path, cat: np.ndarray, footprint: np.ndarray, dist_cat: np.ndarray) -> dict:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        transform_ok = tuple(ds.transform)[:6] == EXPECTED_TRANSFORM
        crs_ok = str(ds.crs) == "EPSG:32611"
        shape_ok = (ds.height, ds.width) == cat.shape
    finite = np.isfinite(arr)
    pos = finite & (arr > 0)
    n_pos = int(pos.sum())
    rec = dict(
        n_positive=n_pos,
        n_finite=int(finite.sum()),
        has_nan=bool((~finite).any()),
        nan_outside_only=bool(np.array_equal(finite, footprint)),
        transform_matches_pin=bool(transform_ok),
        crs_matches_pin=bool(crs_ok),
        shape_matches_pin=bool(shape_ok),
        min=float(np.nanmin(arr)),
        max=float(np.nanmax(arr)),
        binary_positive=bool(np.all(arr[pos] == 1.0)) if n_pos else False,
        positive_outside_footprint=int((pos & ~footprint).sum()),
    )
    if n_pos == 0 or not shape_ok:
        return rec
    d = dist_cat[pos]  # distance (px) from every dot to nearest visible-catalogue pixel
    rec.update(
        on_catalogue=int((pos & cat).sum()),
        frac_within_1px_catalogue=float((d <= 1.0).mean()),
        frac_within_3px_catalogue=float((d <= 3.0).mean()),
        frac_beyond_5px_catalogue=float((d > 5.0).mean()),
        median_dist_catalogue_px=float(np.median(d)),
        mean_dist_catalogue_px=float(d.mean()),
        frac_zero_credit_gt_300m=float((d > 3.0).mean()),
    )
    return rec


def bootstrap_spearman(x: np.ndarray, y: np.ndarray, n_boot: int = 2000, seed: int = 20261029):
    rng = np.random.default_rng(seed)
    n = len(x)
    point = float(spearmanr(x, y).statistic)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if np.ptp(x[idx]) == 0 or np.ptp(y[idx]) == 0:
            continue
        boots.append(float(spearmanr(x[idx], y[idx]).statistic))
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return point, [float(lo), float(hi)]


def main() -> int:
    grid = load_grid(ROOT / "data")
    cat, fp = grid.catalogue, grid.footprint
    dist_cat = distance_transform_edt(~cat).astype(np.float64)
    entries = json.loads(REG.read_text())["entries"]
    fetch = {e["name"]: e for e in json.loads(FETCH.read_text())["entries"]}
    rows = []
    rasters = {}
    for e in entries:
        local = fetch.get(e["name"], {}).get("local")
        if not local:
            rows.append(dict(site=e["site"], name=e["name"], score=e["score"], status="missing_local"))
            continue
        path = ROOT / local
        digest = sha256_file(path)
        rec = dict(site=e["site"], name=e["name"], score=e["score"], file=local, sha256=digest,
                   sha256_matches_registry=(digest == e["sha256"]))
        rec.update(features_for(path, cat, fp, dist_cat))
        rows.append(rec)
        rasters[e["name"]] = path

    scored = [r for r in rows if "score" in r and r.get("n_positive") is not None and r.get("on_catalogue") is not None]
    x_names = ["n_positive", "frac_within_1px_catalogue", "frac_within_3px_catalogue",
               "frac_beyond_5px_catalogue", "median_dist_catalogue_px", "on_catalogue"]
    y = np.array([r["score"] for r in scored], float)
    corr = {}
    for name in x_names:
        x = np.array([r[name] for r in scored], float)
        rho, ci = bootstrap_spearman(x, y)
        corr[name] = dict(spearman_rho=rho, bootstrap95=ci, n=len(scored),
                          evidence_class="COMPUTED-vs-OWNER-REPORTED", caveat="descriptive; n=118 with family dependence")

    # pairwise overlap among the nine focus-site files (literal 3-px rule, both directions)
    focus = [r for r in rows if r["site"] in FOCUS_SITES and "file" in r]
    pairs = []
    for i, a in enumerate(focus):
        for b in focus[i + 1:]:
            pa = ROOT / a["file"]
            pb = ROOT / b["file"]
            with rasterio.open(pa) as da, rasterio.open(pb) as db:
                A, B = da.read(1), db.read(1)
            if A.shape != B.shape:
                continue
            ov_ab = dot_overlap(A, B)
            ov_ba = dot_overlap(B, A)
            pairs.append(dict(a=a["name"], b=b["name"], overlap_a_to_b=ov_ab, overlap_b_to_a=ov_ba,
                              identical_positive_support=bool(np.array_equal((A > 0) & np.isfinite(A),
                                                                             (B > 0) & np.isfinite(B)))))
    out = dict(
        schema="focus-structure-audit-v1",
        score_label="OWNER-REPORTED (registry brief 2026-10-25; not ORGANIZER-CONFIRMED)",
        feature_label="COMPUTED from pinned rasters + owner-mirror catalogue (labels.tif)",
        registry=str(REG.relative_to(ROOT)),
        n_entries=len(entries),
        n_scored_rasters_available=len(scored),
        rows=rows,
        spearman_score_vs_feature=corr,
        focus_pairwise_overlap=pairs,
        limitations=[
            "Scores are owner-reported and not organizer receipts.",
            "Owner-mirror catalogue is used as the reference; the organizer's hidden test set is not available.",
            "Spearman correlations are descriptive; many registry files come from ~22 families and are not independent.",
            "Overlap is the literal 3-px rule; against dense registry rasters it is nearly universal (see shared uniqueness.py).",
        ],
    )
    OUT.write_text(json.dumps(out, indent=1, allow_nan=False, default=float) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} rows, {len(pairs)} focus pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
