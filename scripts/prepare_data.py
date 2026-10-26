#!/usr/bin/env python3
"""Verify data/raw hashes + grid spec; write registry/data_manifest.json.

Pins (sha256 of restored bytes; mirror consistency, NOT organizer auth):
  training_features.tif 4371c82e...
  labels.tif            7ba308cc...
  sample_submission.tif 2176d08e...
Grid: (3730, 3292), EPSG:32611, 100 m, origin (243350, 4508550).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wbg1.paths import data_dir, registry_dir  # noqa: E402

PINS = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
}
EXPECTED = {"shape": (3730, 3292), "crs": "EPSG:32611",
            "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ddir = data_dir()
    manifest = {"schema": 1, "pins": PINS, "files": {}, "ok": True}
    for name, pin in PINS.items():
        p = ddir / name
        row: dict = {"path": str(p), "exists": p.exists()}
        if not p.exists():
            row["ok"] = False
            manifest["ok"] = False
            manifest["files"][name] = row
            print(f"MISSING {name}")
            continue
        h = sha256(p)
        row.update({"sha256": h, "bytes": p.stat().st_size,
                    "hash_ok": h == pin})
        with rasterio.open(p) as s:
            row.update({"shape": list(s.shape), "count": s.count,
                        "crs": str(s.crs), "transform": list(s.transform),
                        "dtype": s.dtypes[0], "nodata": s.nodata})
            grid_ok = (tuple(s.shape) == EXPECTED["shape"]
                       and str(s.crs) == EXPECTED["crs"]
                       and tuple(s.transform)[:6] == EXPECTED["transform"])
            row["grid_ok"] = grid_ok
        row["ok"] = row["hash_ok"] and grid_ok
        manifest["ok"] = manifest["ok"] and row["ok"]
        manifest["files"][name] = row
        print(f"{name}: hash_ok={row['hash_ok']} grid_ok={grid_ok} bytes={row['bytes']}")
    # externals inventory (hash-recorded, not gate-blocking)
    ext = {}
    for p in sorted((ddir / "external").glob("*")):
        if p.is_file():
            ext[p.name] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    manifest["external"] = ext
    print(f"externals: {len(ext)} files")
    out = registry_dir() / "data_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {out} ok={manifest['ok']}")
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
