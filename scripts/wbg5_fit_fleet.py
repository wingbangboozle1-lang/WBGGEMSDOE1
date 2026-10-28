#!/usr/bin/env python3
"""Fit the fleet-wide geometry → live-DTI model on every scored raster we can reach.

Source of truth
    ``<repo>/docs/score-ledger.csv`` in the sibling GEMSDOE repositories, rows with
    ``evidence_class`` in {user-report, owner-report, official-snapshot,
    organizer-public-leaderboard} and a numeric score.  Those are owner-reported
    DrivenData evaluations, not organizer receipts — the LOO residuals in the output
    are the honest size of that caveat.

Rasters
    ``/tmp/recon/*/docs/downloads/*.tif`` (sparse clones of the network; not part of
    this repository).  ``--rasters`` overrides the root.

    python scripts/wbg5_fit_fleet.py --rasters /tmp/recon
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from wbg5 import fleet, grid

SITE_PREFIX = tuple(f"gemsdoe{i}-" for i in range(1, 100))


def norm(s: str) -> str:
    s = os.path.basename(s).lower()
    for ext in (".tif", ".zip"):
        if s.endswith(ext):
            s = s[: -len(ext)]
    for pre in SITE_PREFIX:
        if s.startswith(pre):
            s = s[len(pre):]
    return s


def collect(recon: Path) -> list[tuple[float, str]]:
    rows = []
    for p in glob.glob(str(recon / "*/docs/score-ledger.csv")):
        try:
            with open(p, newline="") as f:
                for r in csv.DictReader(f):
                    sc = (r.get("score") or "").strip()
                    if not sc or not sc.replace(".", "", 1).isdigit():
                        continue
                    rows.append((float(sc), r.get("submission", "")))
        except Exception:
            continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rasters", default="/tmp/recon")
    ap.add_argument("--out", default="docs/data/fleet-score-model.json")
    ap.add_argument("--cache", default="/tmp/lab/fleet_features.json")
    args = ap.parse_args()

    cat = grid.load_catalogue()
    n_cat = int((cat > 0).sum())
    d_cat = distance_transform_edt(~cat).astype(np.float32)

    rasters = {norm(p): p for p in glob.glob(str(Path(args.rasters) / "*/docs/downloads/*.tif"))}
    pairs = []
    seen = set()
    for score, sub in collect(Path(args.rasters)):
        k = norm(sub)
        if not k or k in seen:
            continue
        hit = [p for s, p in rasters.items() if k in s or s in k]
        if len(hit) == 0:
            continue
        seen.add(k)
        pairs.append({"key": k, "file": hit[0], "score": score})
    print(f"{len(pairs)} scored rasters matched", flush=True)

    cache = Path(args.cache)
    table = json.loads(cache.read_text()) if cache.exists() else {}
    rows = []
    for i, rec in enumerate(pairs):
        key = rec["file"]
        if key in table:
            feats = table[key]
        else:
            try:
                with rasterio.open(rec["file"]) as ds:
                    a = ds.read(1)
                if a.shape != cat.shape:
                    continue
                m = np.isfinite(a) & (a > 0)
                if m.sum() < 100:
                    continue
                feats = fleet.geometry(m, d_cat, cat, n_cat)
                feats["continuous"] = bool(np.any((a[m] > 0) & (a[m] < 1)))
                table[key] = feats
            except Exception as exc:  # noqa: BLE001
                print("skip", rec["file"], exc)
                continue
        rows.append({**feats, "score": rec["score"], "file": os.path.basename(rec["file"])})
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(pairs)}", flush=True)
    cache.write_text(json.dumps(table) + "\n")

    y = np.array([r["score"] for r in rows])
    X = fleet.to_matrix(rows)
    pack = fleet.fit(X, y)
    print("LOO comparison:", json.dumps(pack["table"], indent=1))
    print(f"selected {pack['name']}  LOO RMSE {pack['loo_rmse']:.4f}  n={len(y)}")

    pred = pack["model"].predict(X)
    order = np.argsort(-pred)
    print("\ntop 8 by model, with their real scores:")
    for i in order[:8]:
        print(f"  est {pred[i]:.4f}  actual {y[i]:.4f}  {rows[i]['file'][:66]}")

    doc = {"schema": "wbg5-fleet-score-model-v1", "n": int(len(y)),
           "target": "live DrivenData DTI, owner-reported",
           "features": list(fleet.FEATURES), "loo": pack["table"],
           "selected": pack["name"], "loo_rmse": round(pack["loo_rmse"], 4),
           "rows": [{"file": r["file"], "score": r["score"],
                     **{f: round(float(r[f]), 5) for f in fleet.FEATURES}} for r in rows]}
    out = ROOT / args.out
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
