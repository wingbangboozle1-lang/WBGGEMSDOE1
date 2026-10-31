#!/usr/bin/env python3
"""Build the H2 research candidate (31 Oct 2026) with the SAME protocol as the holdout arm.

Protocol parity with scripts/run_h2_lag_corroboration.py --arms full:
  * surface = sqrt(edge_mag * edge_grav) * coherence (catalogue-free, potential fields only);
  * quadrant quota K/4 per NW/NE/SW/SE quadrant (same quota as the holdout);
  * dots keep >= 3 px from the catalogue (here the FULL mapped catalogue: the competition
    grants the catalogue, so no fold hiding applies to the deliverable);
  * greedy 3-px spacing, deterministic.

Writes through the shared writer gems57.submission_writer.write_submission (TIFF + one-TIFF ZIP +
receipt; refuses overwrites) and runs the shared literal uniqueness gate against the 117 cached
owner-reported registry rasters. No holdout score is written here; that lives in the experiment JSON.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import holdout as H
from gems57 import submission_writer, uniqueness
from gems57.grid import load_grid

spec = importlib.util.spec_from_file_location("h2", ROOT / "scripts/run_h2_lag_corroboration.py")
h2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h2)

NAME = "wbggemsdoe1-h2-edgecorr-avoid3-37654-20261031"
NOTE = "H2 potential-field edge corroboration, 3px catalogue avoidance; research only, NOT approved for upload"
OUT_DIR = ROOT / "docs/downloads"
REG = ROOT / "registry/wbg_h1/scored_registry.json"
CACHE = ROOT / ".cache/scored"


def build() -> np.ndarray:
    grid = load_grid()
    fp = grid.footprint
    quad = H.quadrant_ids(fp)
    comps = h2.components(fp)
    surface = h2.score_surface(comps, "full")
    avoid = ndi.distance_transform_edt(~grid.catalogue) <= h2.AVOID_PX
    em = np.zeros(fp.shape, bool)
    k_q = int(round(h2.K_TOTAL / 4))
    for qi in range(4):
        em |= h2.place(surface, (quad == qi) & fp, avoid, k_q)
    assert not (em & grid.catalogue).any(), "dot on mapped catalogue"
    assert not (em & ~fp).any(), "dot outside footprint"
    return em.astype(np.float32)


def registry_index() -> dict:
    entries = json.loads(REG.read_text())["entries"]
    rasters = []
    missing = []
    for e in entries:
        f = CACHE / f"{e['repo']}__{Path(e['path']).name}"
        if not f.exists():
            missing.append(e["name"])
            continue
        rasters.append(dict(repo_first=e["repo"], sources=[e["name"]], cache_file=str(f), sha256=e["sha256"]))
    return dict(rasters=rasters, complete_accessible_scan=False,
                errors=[f"not cached: {m}" for m in missing],
                note="owner-repository inventory; NOT organizer-complete")


def main() -> int:
    em = build()
    grid = load_grid()
    fp = grid.footprint
    n_dots = int(em.sum())
    # The shared writer refuses to overwrite and runs the shared format validator.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tif = OUT_DIR / f"{NAME}.tif"
    pred = em  # 0/1 float32, zeros outside footprint (portal-scored convention in this repo)
    receipt = submission_writer.write_submission(
        tif, pred, ROOT / "data/bridge/sample_submission.tif", fp,
        note=NOTE, name=NAME, catalogue=grid.catalogue,
        metadata={"method": "H2 potential-field edge corroboration + 3px catalogue avoidance",
                  "dots": n_dots, "k_budget": h2.K_TOTAL,
                  "holdout_evidence": "evidence/h2_lag/experiment_20261031.json"})
    # Shared literal uniqueness gate against the cached owner-reported registry rasters.
    idx = registry_index()
    import rasterio
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ref:
        expected = (ref.shape, ref.crs, ref.transform)
    report = uniqueness.compare_array_to_registry(pred, idx, fp, expected_grid=expected)
    summary = {k: report[k] for k in report if k not in ("rows",)}
    out = ROOT / "evidence/h2_lag/candidate_uniqueness_20261031.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"name": NAME, "dots": n_dots, "registry_inventory_size": len(idx["rasters"]),
                               "gate": summary, "receipt_sha256": receipt["sha256"]},
                              indent=2, default=str, allow_nan=False) + "\n")
    print(json.dumps({"name": NAME, "dots": n_dots, "sha256": receipt["sha256"],
                      "validator_ok": receipt["validator"]["checks"] and all(receipt["validator"]["checks"].values())},
                     indent=2))
    print("uniqueness summary:", json.dumps({k: summary[k] for k in summary if not isinstance(summary[k], list)}, default=str)[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
