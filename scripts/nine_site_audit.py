#!/usr/bin/env python3
"""Reproducible audit of the nine focus-site GEMS submissions (GEMSDOE24/25/27/28/30/31/32/33/36).

What it measures (all from the raster bytes, no organizer data):
  * SHA-256, grid, CRS, transform, dtype, nodata, NaN footprint and value range of each named file;
  * positive-cell counts and how many positives lie within 1, 2 and 3 pixels (100 m each) of the
    public INGENIOUS/USGS catalogue (data/bridge/labels.tif, >0 cells);
  * pairwise identity (exact positive-set equality), Jaccard overlap and the registry-style
    "fraction of A within 3 px of B" statistic.

What it does NOT measure: any score. The user-reported scores are carried through only as
labelled USER-REPORTED values. Nothing here is a HOLDOUT-DTI or an organizer result.

Usage:
    .venv/bin/python scripts/nine_site_audit.py            # downloads pinned GitHub snapshots into .cache/
    .venv/bin/python scripts/nine_site_audit.py --offline  # requires the cached tarballs already present

Outputs docs/data/nine_site_audit_20261029.json.
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
from scipy import ndimage
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "nine_sites"
OUT = ROOT / "docs" / "data" / "nine_site_audit_20261029.json"
CATALOGUE = ROOT / "data" / "bridge" / "labels.tif"
OFFICIAL_SAMPLE = ROOT / "data" / "bridge" / "sample_submission.tif"
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)

# Each entry: site, GitHub repo, pinned commit (the commit cited by docs/executive-summary.md),
# path inside the repo, and the USER-REPORTED score supplied in the session prompt.
SITES = [
    dict(site="GEMSDOE32", commit="07806249f4ed3efe70b4fbf866183c32392b7853",
         path="docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
         name="h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", user_reported=0.2778),
    dict(site="GEMSDOE36", commit="05979971df4775aadad34ae6749b0a7ac56d7832",
         path="docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
         name="anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", user_reported=0.2750),
    dict(site="GEMSDOE28", commit="2c839d10f57ec9b074829e93c84bc39935f52896",
         path="docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif",
         name="h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", user_reported=0.2710),
    dict(site="GEMSDOE28", commit="2c839d10f57ec9b074829e93c84bc39935f52896",
         path="docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif",
         name="h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan", user_reported=0.2708),
    dict(site="GEMSDOE31", commit="776bf4668a8c10631908c9bba9443a8f11ce5036",
         path="docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif",
         name="h27-4-solo-d28-20261004-8acb75e1-nan", user_reported=0.2708),
    dict(site="GEMSDOE28", commit="2c839d10f57ec9b074829e93c84bc39935f52896",
         path="docs/downloads/gems28-h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan.tif",
         name="h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan", user_reported=0.2707),
    dict(site="GEMSDOE33", commit="1d99d73fe14d9a87126ffca2db52c69336d6099b",
         path="docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
         name="h33d-analog-tip-stepover-r30-20261004-cb490425926e", user_reported=0.2632),
    dict(site="GEMSDOE25", commit="af2b6f2543e5422a7e917638b70e038e6fd91cad",
         path="docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
         name="dotted-h19-5-d2-8-20261002-e56ea318af89-nan", user_reported=0.2600),
    dict(site="GEMSDOE30", commit="9c0d637c0171407196b61b780444bc772ce75438",
         path="docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
         name="d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", user_reported=0.2600),
    dict(site="GEMSDOE27", commit="bef7ae8e8f63b69d299c9214c75988c8f5055f9c",
         path="docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif",
         name="topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", user_reported=0.2449),
    dict(site="GEMSDOE24", commit="7ab1c8f77f0b4b8644e3929403a0dab65838b008",
         path="docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
         name="h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", user_reported=0.2477),
]
REPO_FOR_SITE = {s: f"buffedlizard55-lab/{s}" for s in
                 ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                  "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]}


def tarball_path(site: str, commit: str) -> Path:
    return CACHE / f"{site}-{commit}.tgz"


def ensure_tarball(site: str, commit: str, offline: bool) -> Path:
    dest = tarball_path(site, commit)
    if dest.exists():
        return dest
    if offline:
        raise FileNotFoundError(f"{dest} missing; run without --offline")
    CACHE.mkdir(parents=True, exist_ok=True)
    url = f"https://codeload.github.com/{REPO_FOR_SITE[site]}/tar.gz/{commit}"
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:  # noqa: S310
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return dest


def extract_member(tgz: Path, path: str) -> bytes:
    """Return the bytes of `path` (relative to the repo root) from a GitHub codeload tarball."""
    with tarfile.open(tgz, "r:gz") as tf:
        for member in tf.getmembers():
            parts = member.name.split("/", 1)
            if len(parts) == 2 and parts[1] == path:
                return tf.extractfile(member).read()
    raise FileNotFoundError(f"{path} not in {tgz.name}")


def decode(raw: bytes, tmp: Path) -> tuple[np.ndarray, dict]:
    tmp.write_bytes(raw)
    with rasterio.open(tmp) as ds:
        arr = ds.read(1).astype("float64")
        meta = dict(crs_epsg=ds.crs.to_epsg(), shape=list(ds.shape), dtype=ds.dtypes[0],
                    nodata=None if ds.nodata is None or np.isnan(ds.nodata) else float(ds.nodata),
                    nodata_is_nan=bool(ds.nodata is not None and np.isnan(ds.nodata)),
                    transform=list(ds.transform)[:6], bands=ds.count)
    return arr, meta


def stats_for(arr: np.ndarray, meta: dict, raw: bytes, catalogue: np.ndarray,
              cat_dist: np.ndarray, sample_finite: np.ndarray) -> dict:
    finite = np.isfinite(arr)
    values = arr[finite]
    positive = finite & (arr > 0)
    d = cat_dist[positive]
    return dict(
        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), **meta,
        transform_matches_official=tuple(meta["transform"]) == EXPECTED_TRANSFORM,
        n_nan=int((~finite).sum()), n_finite=int(finite.sum()),
        nan_mask_matches_official_sample=bool(np.array_equal(finite, sample_finite)),
        value_min=float(values.min()), value_max=float(values.max()),
        n_outside_0_1=int(((values < 0) | (values > 1)).sum()),
        n_distinct_values=int(np.unique(values).size),
        n_positive=int(positive.sum()),
        n_positive_on_catalogue=int((catalogue & positive).sum()),
        n_positive_within_1px=int((d <= 1).sum()),
        n_positive_within_2px=int((d <= 2).sum()),
        n_positive_within_3px=int((d <= 3).sum()),
        frac_positive_within_3px=float((d <= 3).mean()) if d.size else None,
    )


def pairwise(masks: dict[str, np.ndarray]) -> list[dict]:
    names = list(masks)
    dist = {n: ndimage.distance_transform_edt(~masks[n]) for n in names}
    rows = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, B = masks[a], masks[b]
            inter = int((A & B).sum())
            union = int((A | B).sum())
            rows.append(dict(
                a=a, b=b, identical_positive_sets=bool(np.array_equal(A, B)),
                jaccard=round(inter / union, 6) if union else None,
                frac_a_within_3px_of_b=round(float((dist[b][A] <= 3).mean()), 6),
                frac_b_within_3px_of_a=round(float((dist[a][B] <= 3).mean()), 6),
            ))
    return rows


def run(offline: bool) -> dict:
    with rasterio.open(CATALOGUE) as ds:
        catalogue = ds.read(1) == 1
    with rasterio.open(OFFICIAL_SAMPLE) as ds:
        sample_finite = np.isfinite(ds.read(1))
    cat_dist = ndimage.distance_transform_edt(~catalogue)
    results, masks = [], {}
    tmp = CACHE / "_scratch.tif"
    CACHE.mkdir(parents=True, exist_ok=True)
    for s in SITES:
        tgz = ensure_tarball(s["site"], s["commit"], offline)
        raw = extract_member(tgz, s["path"])
        arr, meta = decode(raw, tmp)
        st = stats_for(arr, meta, raw, catalogue, cat_dist, sample_finite)
        key = f'{s["site"]}:{s["name"]}'
        masks[key] = np.isfinite(arr) & (arr > 0)
        pos_sha = hashlib.sha256(np.packbits(masks[key]).tobytes()).hexdigest()
        results.append(dict(key=key, site=s["site"], repo=REPO_FOR_SITE[s["site"]], positive_set_sha256=pos_sha,
                            commit=s["commit"], path=s["path"], name=s["name"],
                            user_reported_score=s["user_reported"],
                            user_reported_label="USER-REPORTED (not organizer-confirmed)", **st))
    tmp.unlink(missing_ok=True)
    pairs = pairwise(masks)
    # Deduplicate identical positive sets: duplicates must not be counted as independent evidence.
    seen, distinct = set(), []
    for r in results:
        if r["positive_set_sha256"] in seen:
            continue
        seen.add(r["positive_set_sha256"])
        distinct.append(r)
    rho, p = spearmanr([r["frac_positive_within_3px"] for r in distinct],
                       [r["user_reported_score"] for r in distinct])
    return dict(
        schema="gemsdoe1-nine-site-audit-v1", generated_utc="2026-10-29",
        catalogue="data/bridge/labels.tif (positives = value 1)",
        official_format_reference="data/bridge/sample_submission.tif (official-sample NaN footprint)",
        score_policy="No score is measured here. user_reported_score is copied from the session prompt and is NOT organizer-confirmed.",
        n_files=len(results), files=results, pairwise=pairs,
        descriptive_spearman_frac_within_3px_vs_user_reported=dict(
            rho=round(float(rho), 4), p_value=float(f"{p:.3g}"), n_distinct_positive_sets=len(distinct),
            distinct_files=[r["key"] for r in distinct],
            caveat=("Descriptive only. n is the number of DISTINCT positive sets with a USER-REPORTED score; "
                    "the scores are unverified, the files are one related family, and this is not a "
                    "causal or predictive claim.")),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="use cached tarballs only")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    report = run(args.offline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {args.out.relative_to(ROOT)} ({report['n_files']} files, {len(report['pairwise'])} pairs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
