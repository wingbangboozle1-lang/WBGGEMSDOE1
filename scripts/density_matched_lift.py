#!/usr/bin/env python3
"""Density-matched overlap lift for the flagged registry rasters (AGENTS.md 0b(ii) diagnostic).

Literal G4 (share of candidate dots within 3 px of a registry dot) is degenerate against dense rasters:
a random field placed on a dense lattice already scores high. The lift divides the literal overlap by
the chance overlap expected for a candidate with the same dot count placed uniformly over the footprint:

    chance = (cells in footprint within 3 px of any registry dot) / (footprint cells)
    lift   = observed_overlap / chance

lift ~ 1 means no more overlap than random placement on the same footprint. Diagnostic only; it does not
replace the literal gate in the receipt, which is reported as-is.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402
from gems57.uniqueness import _dots, _near  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", type=Path)
    ap.add_argument("receipt", type=Path, help="uniqueness receipt JSON from check_uniqueness_full.py")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    fp = load_grid().footprint
    with rasterio.open(a.candidate) as ds:
        mine = ds.read(1)
    my_support = _dots(mine) & fp
    rec = json.loads(a.receipt.read_text())
    rows = []
    for c in rec["closest_registry_rasters"][: a.top]:
        f = ROOT / c["file"]
        with rasterio.open(f) as ds:
            theirs = np.where(np.isfinite(ds.read(1)), ds.read(1), 0.0).astype(np.float32)
        theirs[~fp] = 0
        support = (theirs > 0) & fp
        observed = float(_near(support)[my_support].mean()) if my_support.any() else 0.0
        chance = float(_near(support)[fp].mean()) if support.any() else 0.0
        rows.append({"submission": c["submission"], "repo": c["repo"],
                     "literal_overlap": round(observed, 6),
                     "chance_overlap_same_footprint": round(chance, 6),
                     "lift": round(observed / chance, 4) if chance > 0 else None,
                     "their_dots": int(support.sum())})
    out = {"schema": "density-matched-lift-v1", "candidate": str(a.candidate),
           "candidate_dots": int(my_support.sum()), "rows": rows,
           "note": "diagnostic only; literal G4 is still reported and not waived"}
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
