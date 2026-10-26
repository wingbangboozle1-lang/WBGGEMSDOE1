#!/usr/bin/env python3
"""Assemble the official competition rasters from the GitHub data bridge and pin SHA-256."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "data" / "bridge"

PINS = {
    "example_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "gems-geodawn-numerical-features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    BRIDGE.mkdir(parents=True, exist_ok=True)
    feat = BRIDGE / "gems-geodawn-numerical-features.tif"
    parts = sorted(BRIDGE.glob("gems-geodawn-numerical-features.tif.part-*"))
    if not feat.exists():
        if len(parts) < 5:
            print("Missing feature parts. Run scripts/download_competition_data.sh", file=sys.stderr)
            return 2
        print(f"Assembling {len(parts)} parts -> {feat}")
        with feat.open("wb") as out:
            for p in parts:
                out.write(p.read_bytes())
    ok = True
    for name, pin in PINS.items():
        path = BRIDGE / name
        if not path.exists():
            print(f"MISSING {name}", file=sys.stderr)
            ok = False
            continue
        got = sha256(path)
        match = got == pin
        print(f"{'OK' if match else 'FAIL'} {name} {got}")
        ok = ok and match
    # convenience aliases
    for src, dst in [
        ("example_submission.tif", "sample_submission.tif"),
        ("existing_faults.tif", "labels.tif"),
        ("gems-geodawn-numerical-features.tif", "training_features.tif"),
    ]:
        a, b = BRIDGE / src, BRIDGE / dst
        if a.exists() and not b.exists():
            b.symlink_to(a.name)
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
