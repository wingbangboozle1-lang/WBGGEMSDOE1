#!/usr/bin/env python3
"""Line-by-line audit of the nine GEMSDOE focus sites, from their GitHub archives.

What it does (all reproducible, nothing hand-typed):

1. Downloads each focus repository as a source archive from ``codeload.github.com``
   (an allowed host in this sandbox) into a cache directory OUTSIDE the repo.
2. Extracts every ``.tif`` and hashes it (SHA-256, bytes, footprint statistics).
3. Matches each user-reported filename key (``registry/focus_user_reported_scores.json``)
   to a file on disk and checks the recorded SHA-256 of the nine headline rows
   (``docs/data/focus_nine_site_20261029.json``).
4. Computes a **PROXY-DTI** with the shared metric (``vendor/gems57/metric.py``,
   ``dti_exact``), truth = SGMC-derived off-catalogue proxy. This is NOT an organizer
   score and NOT a HOLDOUT-DTI. It is a labelled, catalogue-disjoint proxy only.
5. Tests whether the proxy ranks the user-reported scores (Spearman), and tests the
   mechanism behind GEMSDOE32 B2 (exact deletion of 6,436 catalogue-adjacent parent dots).

Outputs (small JSON only; no rasters are committed):
    docs/data/focus_codeload_manifest_20261031.json
    docs/data/focus_proxy_audit_20261031.json

Usage: python scripts/focus_codeload_proxy_audit.py [--cache /tmp/gems_focus_cache]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import metric  # noqa: E402  (shared evaluator, not a fork)
from gems57.uniqueness import dot_overlap  # noqa: E402  (shared overlap definition)

OWNER = "buffedlizard55-lab"
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
REF = ROOT / "data/bridge/sample_submission.tif"
CAT = ROOT / "data/bridge/labels.tif"
DERIVED_SGMC_MEMBER = "data/external/derived_sgmc_faults_100m_u8.tif"
DERIVED_SGMC_SITE = "GEMSDOE30"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(site: str, cache: Path) -> Path:
    """Download the default-branch archive; fall back to HEAD. Returns the tarball path."""
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{site}.tgz"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    urls = [
        f"https://codeload.github.com/{OWNER}/{site}/tar.gz/refs/heads/main",
        f"https://codeload.github.com/{OWNER}/{site}/tar.gz/HEAD",
    ]
    last_err = None
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=300) as resp, dest.open("wb") as out:
                out.write(resp.read())
            return dest
        except Exception as exc:  # noqa: BLE001 - recorded, not hidden
            last_err = exc
    raise RuntimeError(f"could not fetch {site}: {last_err}")


def extract_tifs(tgz: Path, site: str, out: Path) -> list[dict]:
    """Extract every .tif in the archive and return one record per member."""
    out.mkdir(parents=True, exist_ok=True)
    records = []
    with tarfile.open(tgz, "r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile() or not member.name.lower().endswith((".tif", ".tiff")):
                continue
            rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
            target = out / site / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(member) as src, target.open("wb") as dst:
                dst.write(src.read())
            records.append({"site": site, "repo_path": rel, "local": target})
    return records


def read_prediction(path: Path, footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float64)
    a = np.where(np.isfinite(a), a, 0.0)
    a = np.where(footprint, a, 0.0)
    return a


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path("/tmp/gems_focus_cache"))
    args = ap.parse_args()
    cache = args.cache
    extract_root = cache / "extracted"

    with rasterio.open(REF) as r:
        ref_transform = tuple(r.transform)
        ref_shape = (r.height, r.width)
        footprint = np.isfinite(r.read(1))
    with rasterio.open(CAT) as c:
        catalogue = c.read(1) > 0
    catalogue &= footprint

    # ------------------------------------------------------------ 1-2 fetch + hash
    records: list[dict] = []
    fetch_log = {}
    for site in SITES:
        tgz = fetch(site, cache)
        fetch_log[site] = {"archive_bytes": tgz.stat().st_size,
                           "archive_sha256": sha256(tgz),
                           "url": f"https://codeload.github.com/{OWNER}/{site}/tar.gz/(refs/heads/main|HEAD)"}
        records += extract_tifs(tgz, site, extract_root)
    for rec in records:
        p = rec["local"]
        rec["bytes"] = p.stat().st_size
        rec["sha256"] = sha256(p)
        del rec["local"]
    by_hash: dict[str, list[str]] = {}
    for rec in records:
        by_hash.setdefault(rec["sha256"], []).append(f'{rec["site"]}/{rec["repo_path"]}')
    cross_site_dupes = [v for v in by_hash.values() if len({x.split("/")[0] for x in v}) > 1]

    # ------------------------------------------------------------ 3 registry checks
    nine = json.loads((ROOT / "docs/data/focus_nine_site_20261029.json").read_text())
    headline_checks = []
    for row in nine["headline_rows"]:
        fname = Path(row["file"]).name
        matches = [rec for rec in records if Path(rec["repo_path"]).name == fname]
        on_disk_hash_ok = any(m["sha256"] == row["sha256"] for m in matches)
        headline_checks.append({
            "site": row["site"], "user_reported_score": row["user_reported_score"],
            "file": fname, "registry_sha256": row["sha256"],
            "found_in_archives": [f'{m["site"]}/{m["repo_path"]}' for m in matches],
            "registry_sha256_matches_archive": on_disk_hash_ok,
        })

    reported = json.loads((ROOT / "registry/focus_user_reported_scores.json").read_text())["entries"]
    matched_reported = []
    for e in reported:
        cands = [rec for rec in records if e["key"] in Path(rec["repo_path"]).name]
        same_site = [c for c in cands if c["site"] == e["site"]]
        pick = (same_site or cands or [None])[0]
        matched_reported.append({"site": e["site"], "key": e["key"], "score": e["score"],
                                 "match": None if pick is None else f'{pick["site"]}/{pick["repo_path"]}',
                                 "sha256": None if pick is None else pick["sha256"],
                                 "n_candidates": len(cands)})

    # ------------------------------------------------------------ 4 proxy truth
    sgmc_path = next((extract_root / DERIVED_SGMC_SITE).rglob("derived_sgmc_faults_100m_u8.tif"), None)
    if sgmc_path is None:
        raise RuntimeError("derived SGMC layer not extracted")
    with rasterio.open(sgmc_path) as s:
        sgmc = s.read(1) > 0
        sgmc_shape = (s.height, s.width)
        sgmc_crs = s.crs.to_string()
        sgmc_transform_ok = tuple(s.transform) == ref_transform
    proxy = sgmc & ~catalogue & footprint
    proxy_meta = {
        "source": f"{DERIVED_SGMC_SITE}/{DERIVED_SGMC_MEMBER}",
        "source_sha256": sha256(sgmc_path),
        "source_provenance": "USGS State Geologic Map Compilation (NV, CA) rasterised; see registry/data_manifest.json",
        "shape_ok": sgmc_shape == ref_shape, "crs": sgmc_crs, "transform_ok": sgmc_transform_ok,
        "proxy_definition": "derived_sgmc > 0 AND NOT catalogue AND footprint",
        "caveat": ("derived layer is a ~1 px dilation of SGMC and still contains catalogue pixels "
                   "(IR-57-SGMC-01, vendor/gems57/offcatalogue.py); proxy removes them; "
                   "raw sgmc_faults_100m.tif is not in this sandbox (mrdata.usgs.gov not allowed)"),
        "proxy_pixels": int(proxy.sum()), "catalogue_pixels": int(catalogue.sum()),
        "footprint_cells": int(footprint.sum()),
    }
    quads = {
        "NW": (slice(0, ref_shape[0] // 2), slice(0, ref_shape[1] // 2)),
        "NE": (slice(0, ref_shape[0] // 2), slice(ref_shape[1] // 2, None)),
        "SW": (slice(ref_shape[0] // 2, None), slice(0, ref_shape[1] // 2)),
        "SE": (slice(ref_shape[0] // 2, None), slice(ref_shape[1] // 2, None)),
    }

    def proxy_dti(pred_bool: np.ndarray) -> dict:
        full = metric.dti_exact(pred_bool.astype(np.float64), proxy, valid=footprint)
        per_quad = []
        for name, (ys, xs) in quads.items():
            qv = np.zeros_like(footprint)
            qv[ys, xs] = True
            qd = metric.dti_exact(pred_bool.astype(np.float64), proxy, valid=footprint & qv)
            per_quad.append({"quadrant": name, "dti": round(qd["dti"], 6), "n_truth": qd["n_truth"]})
        return {"dti": round(full["dti"], 6), "tp": round(full["tp"], 3), "fp": round(full["fp"], 3),
                "fn": round(full["fn"], 3), "n_truth": full["n_truth"],
                "n_emitted": int(full["n_emitted"]), "quadrants": per_quad}

    # ------------------------------------------------------------ 5 score each matched file
    proxy_rows = []
    cache_pred: dict[str, dict] = {}
    for m in matched_reported:
        if m["match"] is None:
            proxy_rows.append({**m, "status": "NOT_FOUND"})
            continue
        if m["sha256"] not in cache_pred:
            site, rel = m["match"].split("/", 1)
            path = extract_root / site / rel
            pred = read_prediction(path, footprint)
            if (pred < 0).any() or (pred > 1).any():
                cache_pred[m["sha256"]] = {"status": "OUT_OF_RANGE"}
            else:
                cache_pred[m["sha256"]] = {"status": "OK", **proxy_dti(pred > 0)}
        r = cache_pred[m["sha256"]]
        proxy_rows.append({**m, **r})

    ok_rows = [r for r in proxy_rows if r.get("status") == "OK"]
    rho = spearmanr([r["score"] for r in ok_rows], [r["dti"] for r in ok_rows]) if len(ok_rows) > 2 else None

    # mechanism test: B2 (exact deletion from D2.8 parent) vs its parent
    b2_name = "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
    d28_name = "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-allfinite.tif"
    b2_rec = next((r for r in records if Path(r["repo_path"]).name == b2_name), None)
    d28_rec = next((r for r in records if Path(r["repo_path"]).name == d28_name), None)
    mech = {"b2": b2_name, "parent": d28_name}
    if b2_rec and d28_rec:
        b2 = read_prediction(extract_root / b2_rec["site"] / b2_rec["repo_path"], footprint) > 0
        d28 = read_prediction(extract_root / d28_rec["site"] / d28_rec["repo_path"], footprint) > 0
        removed = d28 & ~b2
        mech.update({
            "parent_dots": int(d28.sum()), "b2_dots": int(b2.sum()),
            "b2_is_subset_of_parent": bool((b2 & ~d28).sum() == 0),
            "removed_dots": int(removed.sum()),
            "proxy_b2": proxy_dti(b2), "proxy_parent": proxy_dti(d28),
        })
        from scipy.ndimage import distance_transform_edt
        dist_px = distance_transform_edt(~catalogue)
        mech["removed_dist_to_catalogue_px_max"] = float(dist_px[removed].max()) if removed.any() else None
        mech["removed_dist_to_catalogue_px_min"] = float(dist_px[removed].min()) if removed.any() else None
        mech["proxy_delta_b2_minus_parent"] = round(mech["proxy_b2"]["dti"] - mech["proxy_parent"]["dti"], 6)
    else:
        mech["status"] = "FILES_NOT_FOUND"

    # 9-headline pairwise 3-px overlap of dots (shared definition) and exact pixel duplicates
    heads = {}
    for row in nine["headline_rows"]:
        rec = next((r for r in records if r["sha256"] == row["sha256"]), None)
        if rec:
            heads[f'{row["site"]}:{Path(row["file"]).name}'] = read_prediction(
                extract_root / rec["site"] / rec["repo_path"], footprint) > 0
    names = list(heads)
    overlap = {a: {b: round(dot_overlap(heads[a], heads[b]), 4) for b in names} for a in names}

    manifest = {
        "schema": "gemsdoe1-focus-codeload-manifest-v1",
        "generated_by": "scripts/focus_codeload_proxy_audit.py",
        "date_utc": "2026-10-31",
        "source_host": "codeload.github.com (archive download; sandbox allowlist)",
        "fetch": fetch_log,
        "n_tif_members": len(records),
        "n_distinct_sha256": len(by_hash),
        "cross_site_byte_duplicates": cross_site_dupes,
        "headline_checks": headline_checks,
        "files": sorted(records, key=lambda r: (r["site"], r["repo_path"])),
    }
    audit = {
        "schema": "gemsdoe1-focus-proxy-audit-v1",
        "label": "PROXY-DTI (NOT organizer-confirmed; NOT HOLDOUT-DTI). Truth = SGMC-derived "
                 "off-catalogue proxy. Evaluator: vendor/gems57/metric.py::dti_exact (DTI alpha 0.2, "
                 "beta 0.8, 300 m triangular kernel). No CI computed; quadrant spread reported.",
        "proxy": proxy_meta,
        "reference_grid_sha256": sha256(REF),
        "catalogue_sha256": sha256(CAT),
        "matched_reported_files": proxy_rows,
        "spearman_proxy_vs_user_reported": None if rho is None else {
            "rho": round(float(rho.statistic), 4), "p": round(float(rho.pvalue), 4), "n": len(ok_rows),
            "note": "user-reported scores are OWNER-REPORTED; ties and near-identical files included"},
        "mechanism_test_b2_vs_parent": mech,
        "nine_headline_dot_overlap_3px": overlap,
    }
    out_m = ROOT / "docs/data/focus_codeload_manifest_20261031.json"
    out_a = ROOT / "docs/data/focus_proxy_audit_20261031.json"
    out_m.write_text(json.dumps(manifest, indent=1) + "\n")
    out_a.write_text(json.dumps(audit, indent=1, allow_nan=False) + "\n")
    print(json.dumps({"tif_members": len(records), "distinct_sha256": len(by_hash),
                      "cross_site_byte_dupe_groups": len(cross_site_dupes),
                      "spearman": audit["spearman_proxy_vs_user_reported"],
                      "mechanism_delta": mech.get("proxy_delta_b2_minus_parent"),
                      "wrote": [str(out_m.relative_to(ROOT)), str(out_a.relative_to(ROOT))]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
