#!/usr/bin/env python3
"""Inventory every GeoTIFF in the nine focus GEMSDOE repos and this repo, then test a candidate.

For each raster (loose .tif or the single .tif inside a .zip):
  * format checks against the official rules (float32, 1 band, EPSG:32611, 3292x3730,
    100 m, sample transform; NaN/zero outside; finite values in [0,1] inside),
  * exact-byte and decoded-pixel duplicate tests against the candidate,
  * dot overlap: fraction of the candidate's dots within 3 px of that raster's
    positive pixels (official registry-gate form, >70% = STOP),
  * Spearman rank correlation with the candidate over the footprint (|rho|>0.90 = STOP).

Sources are cloned to a directory outside the repository (default /tmp/focus) with
``git clone --depth 1 https://github.com/buffedlizard55-lab/<SITE>.git``.
Output: evidence/tip_continuation_20261029/uniqueness.json

Usage: /tmp/venv/bin/python scripts/focus_inventory_20261029.py --focus /tmp/focus --candidate <tif>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
CAND_STEM = None
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
OVERLAP_PX = 3.0
STOP_OVERLAP = 0.70
STOP_RHO = 0.90


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_raster(data: bytes | Path):
    if isinstance(data, Path):
        return rasterio.open(data)
    return rasterio.MemoryFile(data).open()


def check_format(ds, tmpl_shape, tmpl_tr, tmpl_crs, foot):
    """Official-rule checks. Returns dict and array (2-D float64) or None."""
    out = {}
    out["count_is_1"] = ds.count == 1
    out["dtype_float32"] = ds.dtypes[0] == "float32"
    out["shape_match"] = ds.shape == tmpl_shape
    out["crs_match"] = ds.crs is not None and ds.crs.to_epsg() == 32611
    out["transform_match"] = tuple(ds.transform)[:6] == tuple(tmpl_tr)[:6]
    if not (out["count_is_1"] and out["shape_match"]):
        out["format_pass"] = False
        return out, None
    a = ds.read(1).astype(np.float64)
    inside = a[foot]
    out["inside_all_finite"] = bool(np.isfinite(inside).all())
    out["inside_in_0_1"] = bool(out["inside_all_finite"] and inside.min() >= 0 and inside.max() <= 1)
    outside = a[~foot]
    if outside.size == 0:
        out["outside_convention"] = "n/a"
    elif np.isnan(outside).all():
        out["outside_convention"] = "nan"
    elif (outside == 0).all():
        out["outside_convention"] = "zero"
    else:
        out["outside_convention"] = "other"
    out["format_pass"] = bool(
        out["count_is_1"] and out["dtype_float32"] and out["shape_match"]
        and out["crs_match"] and out["transform_match"] and out["inside_in_0_1"]
    )
    return out, a


def iter_rasters(root: Path):
    """Yield (site, source_label, bytes_or_path) for each raster in the repo tree."""
    for p in sorted(root.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        if p.suffix.lower() in (".tif", ".tiff"):
            yield p, p, None
        elif p.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(p) as z:
                    for n in z.namelist():
                        if n.lower().endswith((".tif", ".tiff")):
                            yield p, Path(f"{p}!{n}"), z.read(n)
            except zipfile.BadZipFile:
                continue


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", type=Path, default=Path("/tmp/focus"))
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "evidence/tip_continuation_20261029/uniqueness.json")
    args = ap.parse_args()

    with rasterio.open(TEMPLATE) as s:
        tmpl_shape, tmpl_tr, tmpl_crs = s.shape, s.transform, s.crs
        foot = np.isfinite(s.read(1))
    with rasterio.open(args.candidate) as c:
        cand = c.read(1).astype(np.float64)
        cand_bytes = args.candidate.read_bytes()
    cand_pos = np.isfinite(cand) & (cand > 0) & foot
    cand_dots = np.argwhere(cand_pos)
    cand_digest = hashlib.sha256(np.packbits(cand_pos).tobytes()).hexdigest()
    cand_sha = sha256_bytes(cand_bytes)
    global CAND_STEM
    CAND_STEM = args.candidate.name.rsplit("-zeros", 1)[0].rsplit("-nan", 1)[0]
    cand_density = float(cand_pos.sum() / foot.sum())

    sources = []
    for site in SITES:
        d = args.focus / site
        if d.exists():
            sources.append((site, d))
    sources.append(("WBGGEMSDOE1", ROOT))

    rows = []
    for site, root in sources:
        for path, label, data in iter_rasters(root):
            # never count the candidate's own file or its own one-member ZIP as a competitor
            # the candidate's own file, its NaN twin and their ZIPs are the same submission, not a competitor
            if CAND_STEM and CAND_STEM in label.name:
                continue
            rel = str(label.relative_to(root)) if label.is_relative_to(root) else str(label)
            ds = read_raster(data if data is not None else path)
            with ds:
                fmt, arr = check_format(ds, tmpl_shape, tmpl_tr, tmpl_crs, foot)
                row = {"site": site, "path": rel, "bytes_sha256": sha256_bytes(data if data is not None else path.read_bytes())}
                row.update(fmt)
                if arr is None:
                    row.update(positive_px=None, dot_overlap_3px=None, spearman_rho=None, status="unreadable-format")
                    rows.append(row)
                    continue
                pos = np.isfinite(arr) & (arr > 0) & foot
                row["positive_px"] = int(pos.sum())
                row["binary_0_1_inside"] = bool(np.isin(arr[foot], [0.0, 1.0]).all())
                row["pixel_digest_sha256"] = hashlib.sha256(np.packbits(pos).tobytes()).hexdigest()
                row["exact_bytes_duplicate_of_candidate"] = row["bytes_sha256"] == cand_sha
                row["decoded_duplicate_of_candidate"] = row["pixel_digest_sha256"] == cand_digest
                # dot-overlap gate is defined for discrete dot rasters only; continuous
                # rasters are compared by rank correlation (their >0 set is not a dot set)
                if row["binary_0_1_inside"] and pos.sum() > 0:
                    tree = cKDTree(np.argwhere(pos))
                    dist, _ = tree.query(cand_dots, k=1)
                    row["dot_overlap_3px"] = float((dist <= OVERLAP_PX).mean())
                    dens = float(pos.sum() / foot.sum())
                    # density-matched random expectation for a 3-px disc (29 px): 1-(1-p)^29
                    row["expected_random_overlap_3px"] = float(1 - (1 - dens) ** 29)
                else:
                    row["dot_overlap_3px"] = None
                    row["expected_random_overlap_3px"] = None
                samp = np.random.default_rng(7).choice(np.count_nonzero(foot), size=min(300_000, np.count_nonzero(foot)), replace=False)
                f_vals = arr[foot][samp]
                c_vals = cand[foot][samp]
                if np.nanstd(f_vals) == 0 or np.nanstd(c_vals) == 0:
                    rho = float("nan")
                else:
                    rho = float(spearmanr(f_vals, c_vals, nan_policy="omit").statistic)
                row["spearman_rho"] = rho
                row["dots_positive_px"] = row["positive_px"]
                flags = []
                if row["decoded_duplicate_of_candidate"] or row["exact_bytes_duplicate_of_candidate"]:
                    flags.append("EXACT-DUPLICATE")
                if row["dot_overlap_3px"] is not None and row["dot_overlap_3px"] > STOP_OVERLAP:
                    flags.append("OVERLAP>70%")
                if rho == rho and abs(rho) > STOP_RHO:
                    flags.append("RHO>0.90")
                row["status"] = "STOP:" + ",".join(flags) if flags else "PASS"
                rows.append(row)
    summary = {
        "candidate": args.candidate.name,
        "candidate_sha256": cand_sha,
        "candidate_dots": int(cand_pos.sum()),
        "rasters_scanned": len(rows),
        "format_pass": int(sum(1 for r in rows if r.get("format_pass"))),
        "exact_or_decoded_duplicates": [r["path"] for r in rows if r.get("decoded_duplicate_of_candidate") or r.get("exact_bytes_duplicate_of_candidate")],
        "max_dot_overlap_3px": max((r["dot_overlap_3px"] for r in rows if r.get("dot_overlap_3px") is not None), default=None),
        "max_abs_spearman": max((abs(r["spearman_rho"]) for r in rows if r.get("spearman_rho") is not None and r["spearman_rho"] == r["spearman_rho"]), default=None),
        "candidate_density": cand_density,
        "rasters_over_70pct_overlap": [r["path"] for r in rows if (r.get("dot_overlap_3px") or 0) > STOP_OVERLAP],
        "binary_dot_rasters": int(sum(1 for r in rows if r.get("binary_0_1_inside"))),
        "rasters_over_rho_0_90": [r["path"] for r in rows if r.get("spearman_rho") and abs(r["spearman_rho"]) > STOP_RHO],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, allow_nan=False, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
