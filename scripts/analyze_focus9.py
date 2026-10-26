#!/usr/bin/env python3
"""Recompute focus-9 lineage relations from exact bytes.

Writes evidence/focus9_lineage.json: dot counts, on-catalogue counts,
exact intersections, directed 3px overlaps, rank correlations.
All claims about 'duplicate' vs 'unique' in this repo trace to this file.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg1.paths import data_dir, evidence_dir, registry_dir, registry_raster_dir  # noqa: E402


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def binary(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        a = s.read(1).astype(np.float64)
    return np.nan_to_num(a, nan=0.0) > 0.5


def main() -> int:
    ddir = data_dir()
    with rasterio.open(ddir / "labels.tif") as s:
        lab = (s.read(1) == 1)
    with rasterio.open(ddir / "sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    focus = json.loads((registry_dir() / "focus9.json").read_text())
    rdir = registry_raster_dir()
    masks, info = {}, {}
    for r in focus["rasters"]:
        p = rdir / r["file"]
        m = binary(p) & foot
        masks[r["id"]] = m
        info[r["id"]] = {"dots": int(m.sum()),
                         "on_catalogue": int((m & lab).sum()),
                         "sha256": sha256(p),
                         "sha_match": sha256(p) == r["sha256"],
                         "owner_reported": r["owner_reported"]}
        print(f"{r['id']:12s} dots={int(m.sum()):6d} sha_match={info[r['id']]['sha_match']}",
              flush=True)
    ids = list(masks)
    pairs = {}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = masks[ids[i]], masks[ids[j]]
            inter = int((a & b).sum())
            dil_b = binary_dilation(b, iterations=3)
            dil_a = binary_dilation(a, iterations=3)
            ov_ab = float((a & dil_b).sum() / max(1, int(a.sum())))
            ov_ba = float((b & dil_a).sum() / max(1, int(b.sum())))
            x, y = a[foot].astype(float), b[foot].astype(float)
            corr = float(np.corrcoef(x, y)[0, 1])
            pairs[f"{ids[i]}x{ids[j]}"] = {
                "exact_inter": inter,
                "frac_of_min": inter / max(1, min(int(a.sum()), int(b.sum()))),
                "overlap_3px_ab": ov_ab, "overlap_3px_ba": ov_ba,
                "rank_corr": corr,
                "subset_or_equal": int(a.sum()) == inter or int(b.sum()) == inter,
            }
    out = {"rasters": info, "pairs": pairs,
           "footprint_px": int(foot.sum()), "labels_px": int(lab.sum())}
    p = evidence_dir() / "focus9_lineage.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"wrote {p}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
