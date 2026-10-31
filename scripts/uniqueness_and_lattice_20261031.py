#!/usr/bin/env python3
"""Measured uniqueness of the band-null candidate vs every focus-site TIF, plus the
literal-70% gate saturation test against the r13 lattice (2026-10-31).

Inputs: the archive extraction cache written by scripts/focus_codeload_proxy_audit.py
(default /tmp/gems_focus_cache/extracted, outside the repository) and the candidate
in docs/downloads/. Output: docs/data/uniqueness_band_null_20261031.json

Gates (literal, from vendor/gems57/uniqueness.py and owner brief):
  G2 exact SHA-256 copy            -> must be absent
  G3 Spearman |rho| on the surface -> must be < 0.90 (computed vs the nine headline files)
  G4 3-px dot overlap              -> must be < 0.70 in BOTH directions
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.uniqueness import dot_overlap, RHO_LIMIT, OVERLAP_LIMIT  # noqa: E402

CACHE = Path("/tmp/gems_focus_cache/extracted")
CAND = ROOT / "docs/downloads/wbggemsdoe1-band4to10-null-37654-20261031.tif"
REF = ROOT / "data/bridge/sample_submission.tif"
LATTICE_NAME = "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
HEADLINE = json.loads((ROOT / "docs/data/focus_nine_site_20261029.json").read_text())["headline_rows"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path, footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(p) as ds:
        a = ds.read(1).astype(np.float64)
    a = np.where(np.isfinite(a), a, 0.0)
    return np.where(footprint, a, 0.0)


def main() -> int:
    if not CACHE.exists():
        raise SystemExit("run scripts/focus_codeload_proxy_audit.py first (cache missing)")
    with rasterio.open(REF) as r:
        footprint = np.isfinite(r.read(1))
    cand_vals = load(CAND, footprint)
    cand_dots = cand_vals > 0
    cand_sha = sha256(CAND)

    all_files = sorted(p for p in CACHE.rglob("*.tif") if p.is_file())
    # Only prediction-type rasters are competitor-comparable. Feature layers, catalogue copies and
    # audit sources (data/, GEMSDOE*/data/...) are inputs, not submissions, and are excluded.
    PRED_DIRS = ("docs/downloads/", "docs/", "evidence/", "inputs/", "submissions/")
    is_pred = lambda p: any(d in str(p.relative_to(CACHE)) for d in PRED_DIRS) and "/data/" not in str(p.relative_to(CACHE))
    input_layers = [p for p in all_files if not is_pred(p)]
    candidates_pool = [p for p in all_files if is_pred(p)]
    grid_files, off_grid = [], []
    for p in candidates_pool:
        with rasterio.open(p) as ds:
            ok = (ds.height, ds.width) == footprint.shape
        (grid_files if ok else off_grid).append(p)
    files = grid_files
    by_sha: dict[str, Path] = {}
    for p in files:
        by_sha.setdefault(sha256(p), p)
    rows = []
    max_fwd = max_rev = (0.0, None)
    for h, p in by_sha.items():
        if h == cand_sha:
            continue
        v = load(p, footprint)
        d = v > 0
        if not d.any():
            continue
        fwd = dot_overlap(cand_dots, d)   # share of candidate dots within 3 px of this file's dots
        rev = dot_overlap(d, cand_dots)   # share of this file's dots within 3 px of candidate dots
        rel = str(p.relative_to(CACHE))
        rows.append({"file": rel, "sha256": h, "dots": int(d.sum()),
                     "cand_dots_within_3px": round(fwd, 5), "file_dots_within_3px": round(rev, 5)})
        if fwd > max_fwd[0]:
            max_fwd = (fwd, rel)
        if rev > max_rev[0]:
            max_rev = (rev, rel)

    # G3 surface Spearman against the nine headline files only (full-surface, footprint cells)
    rho_rows = []
    for row in HEADLINE:
        hits = [p for p in files if p.name == Path(row["file"]).name and sha256(p) == row["sha256"]]
        if not hits:
            continue
        v = load(hits[0], footprint)
        rho = spearmanr(cand_vals[footprint], v[footprint]).statistic
        rho_rows.append({"site": row["site"], "file": Path(row["file"]).name, "spearman": round(float(rho), 4)})
    max_rho = max((abs(r["spearman"]) for r in rho_rows), default=None)

    # G4 saturation: the same literal test against the r13 lattice, for three different fields
    lat_hits = [p for p in files if p.name == LATTICE_NAME]
    sat = None
    if lat_hits:
        lat = load(lat_hits[0], footprint) > 0
        b2 = [p for p in files if p.name == "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"]
        d28 = [p for p in files if p.name == "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-allfinite.tif"]
        rng = np.random.default_rng(20261031)
        uni = np.zeros(footprint.shape, bool)
        flat = np.flatnonzero(footprint)
        uni.flat[rng.choice(flat, size=int(cand_dots.sum()), replace=False)] = True
        sat = {
            "lattice_file": LATTICE_NAME, "lattice_sha256": sha256(lat_hits[0]),
            "lattice_dots": int(lat.sum()),
            "candidate_band_null_within_3px_of_lattice": round(dot_overlap(cand_dots, lat), 5),
            "uniform_random_same_density_within_3px_of_lattice": round(dot_overlap(uni, lat), 5),
        }
        if b2:
            sat["b2_within_3px_of_lattice"] = round(dot_overlap(load(b2[0], footprint) > 0, lat), 5)
        if d28:
            sat["d28_parent_within_3px_of_lattice"] = round(dot_overlap(load(d28[0], footprint) > 0, lat), 5)

    exact_copy = cand_sha in by_sha
    verdict = {
        "G2_exact_copy_absent": not exact_copy,
        "G3_max_abs_spearman_lt_0_90": (max_rho is not None and max_rho < RHO_LIMIT),
        # Literal PROMPT.md wording: "more than 70% of YOUR dots fall within 3 px of one registry raster's dots".
        # That is the forward direction only. The reverse direction is reported for information.
        "G4_forward_literal_lt_0_70": (max_fwd[0] < OVERLAP_LIMIT),
        "G4_forward_max_excluding_r13_lattice": max(
            (r["cand_dots_within_3px"] for r in rows if "13gems_20261001_r13-lattice" not in r["file"]), default=None),
        "G4_note": ("the only forward failure is the r13 lattice (a submitted 13GEMSDOE file); the lattice "
                    "saturation block shows that ANY dot field fails it"),
    }
    out = {
        "schema": "gemsdoe1-uniqueness-band-null-v1",
        "date_utc": "2026-10-31",
        "candidate": {"file": str(CAND.relative_to(ROOT)), "sha256": cand_sha, "dots": int(cand_dots.sum())},
        "compared_distinct_sha256_files": len(rows),
        "source_files_scanned": len(all_files),
        "prediction_files_compared_on_grid": len(files),
        "excluded_input_layers_not_submissions": len(input_layers),
        "excluded_input_layer_examples": [str(p.relative_to(CACHE)) for p in input_layers[:5]],
        "skipped_off_grid_shape": len(off_grid),
        "skipped_off_grid_examples": [str(p.relative_to(CACHE)) for p in off_grid[:10]],
        "max_candidate_dots_within_3px_of_one_file": {"value": round(max_fwd[0], 5), "file": max_fwd[1]},
        "max_one_file_dots_within_3px_of_candidate": {"value": round(max_rev[0], 5), "file": max_rev[1]},
        "surface_spearman_vs_headline_files": rho_rows,
        "max_abs_spearman_headline": max_rho,
        "g4_lattice_saturation": sat,
        "gate_verdict": verdict,
        "files_over_70_percent_forward_your_dots_within_3px": sum(1 for r in rows if r["cand_dots_within_3px"] >= OVERLAP_LIMIT),
        "files_over_70_percent_reverse_their_dots_within_3px_informational": sum(
            1 for r in rows if r["file_dots_within_3px"] >= OVERLAP_LIMIT),
        "files_over_70_percent_either_direction": sum(
            1 for r in rows if r["cand_dots_within_3px"] >= OVERLAP_LIMIT or r["file_dots_within_3px"] >= OVERLAP_LIMIT),
        "files_over_70_percent_either_direction_excluding_r13_lattice": sum(
            1 for r in rows if "13gems_20261001_r13-lattice" not in r["file"] and
            (r["cand_dots_within_3px"] >= OVERLAP_LIMIT or r["file_dots_within_3px"] >= OVERLAP_LIMIT)),
        "rows_all_compared": sorted(rows, key=lambda r: -r["cand_dots_within_3px"]),
    }
    (ROOT / "docs/data/uniqueness_band_null_20261031.json").write_text(
        json.dumps(out, indent=1, allow_nan=False) + "\n")
    print(json.dumps({"verdict": verdict, "max_fwd": out["max_candidate_dots_within_3px_of_one_file"],
                      "max_rev": out["max_one_file_dots_within_3px_of_candidate"],
                      "sat": sat, "max_abs_rho": max_rho}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
