#!/usr/bin/env python3
"""Literal and density-matched overlap of one candidate TIFF against every local registry raster.

Same definitions as scripts/session_audit_20261031.py (validated against its B2 receipt):
  literal overlap  = share of the candidate's dots within 3 px (Euclidean) of a registry raster's dots
                     (dots = finite & >0, inherited protocol support definition)
  coverage         = share of the footprint within 3 px of that registry raster's dots
  lift             = literal overlap / coverage (density-matched; 1.0 = no better than random placement)
  phi              = Pearson correlation of the two 0/1 dot indicators over the footprint
A registry raster with the identical positive set is reported as an exact positive-set copy.

Usage: .venv/bin/python scripts/candidate_overlap_20261031.py <candidate.tif> <out.json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402
from gems57.metric import RADIUS_PX  # noqa: E402


def main() -> int:
    cand_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    grid = load_grid(ROOT / "data/bridge")
    with rasterio.open(cand_path) as src:
        c = src.read(1)
    m = np.isfinite(c) & (c > 0) & grid.footprint
    n_all = int(grid.footprint.sum())
    n1 = int(m.sum())
    manifest = json.loads((ROOT / "registry/focus_raster_fetch.json").read_text())
    rows = []
    exact_copies = []
    for e in manifest["entries"]:
        if not e.get("local"):
            continue
        with rasterio.open(ROOT / e["local"]) as src:
            r = src.read(1)
        t = np.isfinite(r) & (r > 0) & grid.footprint
        if not t.any():
            continue
        near = distance_transform_edt(~t) <= RADIUS_PX
        coverage = float(near[grid.footprint].mean())
        ov = float(near[m].mean()) if n1 else 0.0
        n2 = int(t.sum())
        n12 = int(np.count_nonzero(m & t))
        den = math.sqrt(float(n1) * float(n_all - n1) * float(n2) * float(n_all - n2))
        phi = float((n_all * n12 - n1 * n2) / den) if den > 0 else 0.0
        identical = bool(np.array_equal(m, t))
        if identical:
            exact_copies.append(f"{e['repo']}/{e['path']}")
        rows.append(dict(repo=e["repo"], path=e["path"], sha256=e["sha256"], n_dots=n2,
                         literal_overlap=ov, coverage=coverage,
                         lift=ov / coverage if coverage else None, phi=phi,
                         identical_positive_set=identical))
    ov = np.array([x["literal_overlap"] for x in rows])
    phis = np.array([x["phi"] for x in rows])
    worst = sorted(rows, key=lambda x: -x["literal_overlap"])[:8]
    result = dict(
        evidence_class="OVERLAP",
        candidate=str(cand_path.name),
        candidate_sha256=__import__("hashlib").sha256(cand_path.read_bytes()).hexdigest(),
        candidate_dots=n1,
        registry_rasters_compared=len(rows),
        rule="PROMPT.md LANE: >70% of dots within 3 px of one registry raster's dots = duplicate",
        max_literal_overlap=float(ov.max()),
        n_rasters_over_70pct_literal=int((ov > 0.70).sum()),
        median_literal_overlap=float(np.median(ov)),
        median_density_matched_lift=float(np.median([x["lift"] for x in rows if x["lift"] is not None])),
        max_phi=float(phis.max()),
        n_rasters_phi_over_0_90=int((phis > 0.90).sum()),
        exact_positive_set_copies=exact_copies,
        worst_eight=worst,
        organizer_confirmed="NONE",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "worst_eight"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
