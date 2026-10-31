#!/usr/bin/env python3
"""Literal uniqueness of each nine-site top file against EVERY cached registry raster (self excluded).

Writes evidence/h2_lag/focus_vs_registry_overlap_20261031.json. Uses the shared gems57 comparator.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import uniqueness
from gems57.grid import load_grid

spec = importlib.util.spec_from_file_location("b", ROOT / "scripts/build_h2_candidate_20261031.py")
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
grid = load_grid(); fp = grid.footprint
idx = b.registry_index()
audit = json.loads((ROOT / "docs/data/nine_site_audit_20261029.json").read_text())
best = {}
for f in audit["files"]:
    if f["site"] not in best or f["user_reported_score"] > best[f["site"]]["user_reported_score"]:
        best[f["site"]] = f
with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ref:
    expected = (ref.shape, ref.crs, ref.transform)
out = {}
for site, f in sorted(best.items()):
    hits = [r for r in idx["rasters"] if r["sha256"] == f["sha256"]]
    assert len(hits) == 1, (f["name"], len(hits))
    p = Path(hits[0]["cache_file"])
    with rasterio.open(p) as ds:
        arr = ds.read(1).astype(np.float32)
    arr = np.where(np.isfinite(arr), arr, 0.0)
    arr[~fp] = 0
    rep = uniqueness.compare_array_to_registry(arr, idx, fp, expected_grid=expected)
    rows = [r for r in rep["rows"] if r.get("sha256") != f["sha256"] and "my_dots_within_3px_of_theirs" in r]
    worst = max(rows, key=lambda r: r["my_dots_within_3px_of_theirs"])
    n70 = [r["submission"] for r in rows if r["my_dots_within_3px_of_theirs"] > 0.70]
    out[site] = {"file": f["name"], "sha256": f["sha256"], "self_excluded_rows": len(rows),
                 "max_literal_overlap_vs_registry": round(worst["my_dots_within_3px_of_theirs"], 6),
                 "max_overlap_registry_entry": worst["submission"],
                 "registry_entries_over_70pct": n70,
                 "max_spearman_vs_registry": round(max(r["spearman_full_footprint"] for r in rows), 6),
                 "unique_literal_vs_registry": len(n70) == 0}
    print(site, out[site]["max_literal_overlap_vs_registry"], out[site]["max_overlap_registry_entry"], len(n70), flush=True)
(ROOT / "evidence/h2_lag/focus_vs_registry_overlap_20261031.json").write_text(
    json.dumps({"schema": "focus-vs-registry-literal-v1", "registry_entries": len(idx["rasters"]),
                "scope": "owner-repository inventory, not organizer-complete", "sites": out},
               indent=2, allow_nan=False) + "\n")
