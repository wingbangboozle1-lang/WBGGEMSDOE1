#!/usr/bin/env python3
"""Full G1-G4 receipt for one candidate GeoTIFF against every locally cached registry raster.

Gates (AGENTS / user protocol):
  G1 format      : vendor/gems57/validate.py (single band, float32, 3730x3292, EPSG:32611,
                   training-grid transform, values in [0,1], no NaN/inf/sentinels, zero outside footprint,
                   zero dots on the mapped catalogue).
  G2 exact copy  : identical bytes or identical decoded predictions to any registry raster.
  G3 rank        : Spearman (tied ranks, full footprint) < 0.90 against every registry raster.
  G4 overlap     : literal share of candidate dots within 3 px of a registry raster's dots, must be < 70%.
                   Reported literally. A degenerate-lattice caveat is reported separately, not waived.

Inputs: the shared comparator vendor/gems57/uniqueness.compare_to_registry (not forked).
Registry: the union of the owner-scored rasters (registry/wbg_h1/scored_registry.json, fetched by
scripts/fetch_scored_rasters.py) and the focus-site rasters (registry/focus_files.json, fetched by
scripts/fetch_focus_rasters.py). Every file is SHA-256 verified by its fetch script; this script
re-verifies the SHA-256 against the registry pins before comparing. Scores are OWNER-REPORTED.

Usage: .venv/bin/python scripts/check_uniqueness_full.py <candidate.tif> --out <receipt.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57.grid import load_grid  # noqa: E402
from gems57.uniqueness import compare_to_registry, OVERLAP_LIMIT, RHO_LIMIT  # noqa: E402
from gems57.validate import validate  # noqa: E402


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_index() -> dict:
    """Deduplicated registry index in the schema expected by gems57.uniqueness.records_from_index."""
    pins = {}
    for e in json.loads((ROOT / "registry/wbg_h1/scored_registry.json").read_text())["entries"]:
        pins.setdefault(e["sha256"], {"repo": e["repo"], "source": "owner-scored", "name": e["name"]})
    for f in json.loads((ROOT / "registry/focus_files.json").read_text())["files"]:
        pins.setdefault(f["sha256"], {"repo": f["repo"], "source": "focus-site", "name": Path(f["path"]).name})
    rasters, seen, missing = [], set(), []
    for d in (".cache/scored", ".cache/focus_rasters"):
        for name in sorted(os.listdir(ROOT / d)):
            p = ROOT / d / name
            h = sha256(p)
            if h in seen:
                continue
            if h not in pins:
                missing.append(str(p.relative_to(ROOT)))
                continue
            seen.add(h)
            rasters.append({"repo_first": pins[h]["repo"], "sources": [pins[h]["name"]],
                            "cache_file": str(p.relative_to(ROOT)), "sha256": h,
                            "source": pins[h]["source"]})
    return {"complete_accessible_scan": not missing,
            "errors": [f"cache file not in any pin: {m}" for m in missing],
            "rasters": rasters}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    grid = load_grid()
    fmt = validate(a.candidate, footprint=grid.footprint, catalogue=grid.catalogue)
    index = build_index()
    res = compare_to_registry(a.candidate, index, grid.footprint)
    rows = [r for r in res.get("rows", res.get("registry_rows", [])) if "error" not in r]
    max_rho = max((r["spearman_full_footprint"] for r in rows
                   if r.get("spearman_full_footprint") is not None), default=None)
    max_ov = max((r["my_dots_within_3px_of_theirs"] for r in rows), default=None)
    exact = [r for r in rows if r.get("identical_bytes") or r.get("identical_decoded_predictions")]
    g = {
        "G1_format_all_checks": fmt["all_checks_passed"],
        "G2_no_exact_copy": len(exact) == 0,
        "G3_spearman_max_lt_0_90": (max_rho is not None and max_rho < RHO_LIMIT),
        "G4_literal_overlap_max_lt_0_70": (max_ov is not None and max_ov < OVERLAP_LIMIT),
    }
    receipt = {
        "schema": "uniqueness-full-receipt-v1",
        "candidate": str(a.candidate.resolve().relative_to(ROOT)),
        "candidate_file_sha256": fmt["sha256"],
        "format_receipt": {k: fmt[k] for k in ("checks", "all_checks_passed", "min", "max",
                                                "emitted_positive_pixels", "n_nan", "on_catalogue_positive_pixels",
                                                "in_footprint_positive_pixels")},
        "registry_index_rasters": len(index["rasters"]),
        "registry_index_complete_accessible_scan": index["complete_accessible_scan"],
        "registry_rasters_compared": len(rows),
        "max_spearman_full_footprint": max_rho,
        "max_literal_3px_overlap": max_ov,
        "gates": g,
        "all_gates_passed": all(g.values()),
        "comparator_summary": {k: v for k, v in res.items() if k not in ("rows", "registry_rows")},
        "closest_registry_rasters": sorted(
            [{k: r.get(k) for k in ("submission", "repo", "file", "spearman_full_footprint",
                                     "my_dots_within_3px_of_theirs", "their_dots_within_3px_of_mine",
                                     "jaccard_dot_sets")} for r in rows],
            key=lambda r: -(r["my_dots_within_3px_of_theirs"] or 0))[:10],
        "scope": ("Hash-verified accessible owner/focus rasters in this checkout; not a complete organizer "
                  "registry. Scores in these rows are OWNER-REPORTED where present."),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(receipt, indent=2, default=float) + "\n")
    print(json.dumps({"gates": g, "max_spearman": max_rho, "max_literal_overlap": max_ov,
                      "compared": len(rows)}, indent=2))
    return 0 if receipt["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
