#!/usr/bin/env python3
"""Uniqueness + format audit of GeoTIFF candidates against the GEMSDOE focus-site corpus.

Corpus = every .tif/.tiff inside the nine focus-site repositories (GEMSDOE24, 25,
27, 28, 30, 31, 32, 33, 36 on github.com/buffedlizard55-lab), each cloned with
``git clone --depth 1`` and recorded by commit SHA. Repo-local downloads are
added as a second corpus. Nothing here is a leaderboard score.

Per (candidate, registry raster) pair:
  * sha256 identity and normalised-pixel identity (exact duplicate),
  * Spearman rank correlation on 400k sampled footprint pixels (LANE rule: > 0.90 = duplicate),
  * dot overlap: share of candidate dots within 3 px of a registry dot (LANE rule: > 70% = duplicate).
  Dots: pixels == 1 for binary files; otherwise the top-N pixels, N = candidate dot count.

Format audit per file: CRS, shape, transform, count, dtype, NaN count, min/max, binary?.
Usage: python scripts/audit_focus_registry.py --corpus /tmp/focus --out evidence/uniqueness/x.json <candidate.tif> ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
GRID_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
GRID_SHAPE = (3730, 3292)
GRID_CRS = "EPSG:32611"
DOT_RADIUS = 3
_yy, _xx = np.mgrid[-DOT_RADIUS:DOT_RADIUS + 1, -DOT_RADIUS:DOT_RADIUS + 1]
DISK3 = (_yy ** 2 + _xx ** 2) <= DOT_RADIUS ** 2
SPEARMAN_N = 400_000
DUP_RHO = 0.90
DUP_OVERLAP = 0.70


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def format_facts(path: Path) -> dict:
    with rasterio.open(path) as s:
        a = s.read(1)
        crs = s.crs.to_string() if s.crs else None
        facts = {
            "count": s.count, "dtype": s.dtypes[0], "crs": crs, "shape": [s.height, s.width],
            "transform": [round(v, 6) for v in s.transform[:6]],
            "nodata": s.nodata,
        }
    fin = np.isfinite(a)
    facts.update({
        "nan_count": int((~fin).sum()),
        "min": float(np.nanmin(a)) if fin.any() else None,
        "max": float(np.nanmax(a)) if fin.any() else None,
        "in_0_1": bool(fin.all() and (a >= 0).all() and (a <= 1).all()),
        "binary": bool(fin.all() and np.isin(a, (0.0, 1.0)).all()),
        "nonzero": int((a != 0).sum()),
    })
    facts["format_pass"] = bool(
        facts["count"] == 1 and facts["dtype"] == "float32" and facts["crs"] == GRID_CRS
        and tuple(facts["shape"]) == GRID_SHAPE and facts["transform"] == list(GRID_TRANSFORM)
        and facts["nan_count"] == 0 and facts["in_0_1"])
    return facts, a


def dot_mask(a: np.ndarray, n_target: int | None) -> np.ndarray:
    if np.isin(a, (0.0, 1.0)).all():
        return a == 1.0
    n = n_target or 36800
    flat = a.ravel()
    idx = np.argpartition(-flat, min(n, flat.size - 1))[:n]
    m = np.zeros(flat.shape, bool)
    m[idx] = True
    return m.reshape(a.shape)


def compare(cand: np.ndarray, cand_dots: np.ndarray, reg: np.ndarray, rng_idx: np.ndarray) -> dict:
    reg_dots = dot_mask(reg, int(cand_dots.sum()))
    if reg_dots.any():
        # Equivalent to EDT(~reg_dots) <= 3: a candidate dot is hit when a registry
        # dot lies inside the Euclidean disk of radius 3 px around it.
        # KD-tree over registry dot coordinates: exact Euclidean test d <= 3 px.
        reg_pts = np.argwhere(reg_dots).astype(np.float64)
        cand_pts = np.argwhere(cand_dots).astype(np.float64)
        if cand_pts.size:
            d, _ = cKDTree(reg_pts).query(cand_pts, distance_upper_bound=DOT_RADIUS + 1e-6)
            overlap = float((d <= DOT_RADIUS + 1e-9).mean())
        else:
            overlap = float("nan")
    else:
        overlap = float("nan")
    rho = spearmanr(cand.ravel()[rng_idx], reg.ravel()[rng_idx]).statistic
    rho = float(rho) if rho == rho else float("nan")
    identical = bool(np.array_equal(cand, reg))
    return {"spearman_sample": rho, "dot_overlap_3px": overlap, "pixel_identical": identical}


def discover(corpus: Path) -> list[dict]:
    out = []
    for repo in sorted(corpus.glob("G*")):
        if not repo.is_dir():
            continue
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        for p in sorted(list(repo.rglob("*.tif")) + list(repo.rglob("*.tiff"))):
            if ".git" in p.parts:
                continue
            out.append({"path": p, "repo": repo.name, "commit": head})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("candidates", nargs="+", type=Path)
    args = ap.parse_args()

    corpus = discover(args.corpus)
    rng = np.random.default_rng(2026)
    fp_idx = None
    cands = []
    for c in args.candidates:
        facts, a = format_facts(c)
        cands.append({"path": c, "sha256": sha256(c), "facts": facts, "array": a,
                      "dots": dot_mask(a, None)})
    # Footprint sampling indices: the common grid is 3730 x 3292.
    n_px = GRID_SHAPE[0] * GRID_SHAPE[1]
    fp_idx = rng.choice(n_px, size=SPEARMAN_N, replace=False)

    # Stream the corpus once: never hold more than one registry raster in memory.
    reg_rows = []
    pairs = []
    for item in corpus:
        p = item["path"]
        rel = str(p.relative_to(args.corpus))
        try:
            f, a = format_facts(p)
        except Exception as e:  # unreadable or unexpected file
            reg_rows.append({"path": rel, "repo": item["repo"], "commit": item["commit"], "error": str(e)})
            continue
        shp = sha256(p)
        reg_rows.append({"path": rel, "repo": item["repo"], "commit": item["commit"], "sha256": shp, "facts": f})
        for c in cands:
            if a.shape != c["array"].shape or p.resolve() == c["path"].resolve():
                continue
            r = compare(c["array"], c["dots"], a, fp_idx)
            r.update({"registry_path": rel, "registry_sha256": shp, "sha256_identical": shp == c["sha256"]})
            rho_hit = r["spearman_sample"] == r["spearman_sample"] and r["spearman_sample"] > DUP_RHO
            ov_hit = r["dot_overlap_3px"] == r["dot_overlap_3px"] and r["dot_overlap_3px"] > DUP_OVERLAP
            r["duplicate_by_rule"] = bool(r["sha256_identical"] or r["pixel_identical"] or rho_hit or ov_hit)
            pairs.append({"candidate": str(c["path"]), **r})
        del a
    summary = {}
    for c in cands:
        mine = [p for p in pairs if p["candidate"] == str(c["path"])]
        worst_rho = max(mine, key=lambda p: (p["spearman_sample"] if p["spearman_sample"] == p["spearman_sample"] else -9))
        worst_ov = max(mine, key=lambda p: (p["dot_overlap_3px"] if p["dot_overlap_3px"] == p["dot_overlap_3px"] else -9))
        dups = [p for p in mine if p["duplicate_by_rule"]]
        summary[str(c["path"])] = {
            "sha256": c["sha256"], "format": c["facts"], "dots": int(c["dots"].sum()),
            "registry_rasters_compared": len(mine),
            "max_spearman": {"value": worst_rho["spearman_sample"], "registry": worst_rho["registry_path"]},
            "max_dot_overlap_3px": {"value": worst_ov["dot_overlap_3px"], "registry": worst_ov["registry_path"]},
            "duplicate_hits": len(dups),
            "duplicate_examples": [d["registry_path"] for d in dups[:10]],
            "unique_by_lane_rule": len(dups) == 0,
        }
    out = {
        "schema": "gemsdoe1-focus-registry-audit-v1",
        "date_utc": "2026-10-29",
        "corpus_root": "focus-site clones (github.com/buffedlizard55-lab/GEMSDOE{24,25,27,28,30,31,32,33,36}, depth 1)",
        "rules": {"duplicate_if": f"sha256 or pixel identical, or Spearman > {DUP_RHO}, or 3px dot overlap > {DUP_OVERLAP}",
                  "spearman_sample_n": SPEARMAN_N, "dot_radius_px": DOT_RADIUS},
        "registry_rasters": len(reg_rows),
        "registry_format_pass": sum(1 for r in reg_rows if r.get("facts", {}).get("format_pass")),
        "candidates": summary,
        "registry": reg_rows,
        "pairs": pairs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, default=float) + "\n")
    for k, v in summary.items():
        print(k, "unique_by_lane_rule=", v["unique_by_lane_rule"], "dups=", v["duplicate_hits"],
              "max_rho=", round(v["max_spearman"]["value"], 4), "max_ov=", round(v["max_dot_overlap_3px"]["value"], 4),
              "compared=", v["registry_rasters_compared"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
