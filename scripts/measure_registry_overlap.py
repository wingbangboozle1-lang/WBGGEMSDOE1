#!/usr/bin/env python3
"""Literal 3-px registry overlap for one candidate TIFF against every cached registry raster.

Reuses the shared gate vendor/gems57/uniqueness.dot_overlap (no private fork).
Overlap = share of the candidate's dots lying within 3 px (Euclidean) of one registry raster's dots.
Duplicate rule (user protocol): overlap > 0.70, or rank correlation > 0.90 (not computed here).
Output: JSON receipt with per-raster rows, sorted worst-first. Registry scores are OWNER-REPORTED.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.uniqueness import dot_overlap, OVERLAP_LIMIT  # noqa: E402

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--exclude-sha", action="append", default=[], help="registry sha to skip (self)")
    a = ap.parse_args()
    reg = json.loads((ROOT / "registry/wbg_h1/scored_registry.json").read_text())["entries"]
    with rasterio.open(a.candidate) as ds:
        mine = ds.read(1)
    my_dots = int(np.count_nonzero(np.isfinite(mine) & (mine > 0)))
    rows, seen = [], set()
    for e in reg:
        p = ROOT / ".cache/scored" / f"{e['repo']}__{Path(e['path']).name}"
        if not p.exists():
            rows.append({"submission": e["name"], "error": "missing local cache"}); continue
        digest = sha(p)
        if digest in seen:
            continue
        seen.add(digest)
        if digest in a.exclude_sha:
            continue
        with rasterio.open(p) as ds:
            theirs = ds.read(1)
        ov = dot_overlap(mine, theirs)
        rows.append({"submission": e["name"], "site": e["repo"], "score_owner_reported": e["score"],
                     "sha256": digest, "their_dots": int(np.count_nonzero(theirs > 0)),
                     "my_dots_within_3px_of_theirs": round(ov, 6),
                     "identical_bytes": digest == sha(a.candidate),
                     "duplicate_by_overlap": ov > OVERLAP_LIMIT})
    checked = [r for r in rows if "error" not in r]
    rows.sort(key=lambda r: -r.get("my_dots_within_3px_of_theirs", -1))
    worst = max(checked, key=lambda r: r["my_dots_within_3px_of_theirs"])
    out = {
        "schema": "registry-overlap-measurement-v1",
        "candidate": str(a.candidate.resolve().relative_to(ROOT)),
        "candidate_sha256": sha(a.candidate),
        "my_dots": my_dots,
        "overlap_limit": OVERLAP_LIMIT,
        "registry_rasters_unique_checked": len(checked),
        "rasters_over_limit": sum(r["duplicate_by_overlap"] for r in checked),
        "worst_overlap": worst["my_dots_within_3px_of_theirs"],
        "worst_against": worst["submission"],
        "passes_literal_overlap_gate": not any(r["duplicate_by_overlap"] for r in checked),
        "rows": rows,
        "evidence_class": "REGISTRY-MEASUREMENT (owner-reported registry; not organizer)",
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
