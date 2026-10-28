#!/usr/bin/env python3
"""Restore the independent evidence rasters and the official 19-band stack.

Both are *public products*; what this script pins is the exact bytes, so a run is
reproducible even though the upstream archives are hosted outside GitHub.

    python scripts/wbg5_fetch_external.py --check        # verify what is on disk
    python scripts/wbg5_fetch_external.py --fetch        # download the missing ones

Sources, all public
    lidar_scarp_features_u8.tif  USGS 3DEP 1 m lidar DEM tiles from the competition's own
                                 DEM link list, reduced to 100 m terrain descriptors
                                 (https://www.usgs.gov/3d-elevation-program).
    geodawn_rad_u8.tif           GeoDAWN airborne radiometrics, USGS ScienceBase item
    geodawn_extensions_u8.tif    657e1d85d34e23d3533209f7, DOI 10.5066/P93LGLVQ
                                 (https://doi.org/10.5066/P93LGLVQ): magnetics and ratios.
    training_features.tif        The competition's official 19-band feature stack,
                                 EPSG:32611, 3 730 x 3 292, sha256 4371c82e…23bc5.

The bridge mirror of the feature stack lives in the sibling repository
``buffedlizard55-lab/GEMSDOE2`` under ``data/bridge/`` as five parts with published
SHA-256 values; ``--fetch`` reassembles and verifies them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
BRIDGE = ROOT / "data" / "bridge"

PINS = {
    "lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "geodawn_rad_u8.tif": "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
    "geodawn_extensions_u8.tif": "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
}
EXT_MIRROR = "https://github.com/buffedlizard55-lab/GEMSDOE24/raw/main/data/external/"
STACK = {
    "name": "training_features.tif",
    "bytes": 418_912_844,
    "sha256": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "parts": ["gems-geodawn-numerical-features.tif.part-%03d" % i for i in range(5)],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check() -> int:
    ok = True
    for name in PINS:
        p = EXT / name
        if not p.exists():
            print(f"MISSING  {p}")
            ok = False
            continue
        digest = sha256(p)
        good = digest == PINS[name]
        ok &= good
        print(f"{'present ' if good else 'DIFFERS '} {name:32s} {p.stat().st_size:>10,d} B  "
              f"sha256 {digest[:16]}… {'pinned' if good else 'NOT the pinned bytes'}")
    stack = ROOT / "data" / "bridge" / STACK["name"]
    if stack.exists():
        digest = sha256(stack)
        good = digest == STACK["sha256"]
        print(f"present  {STACK['name']:32s} {stack.stat().st_size:>10,d} B  "
              f"sha256 {'MATCHES' if good else 'DIFFERS'}")
        ok &= good
    else:
        print(f"MISSING  {stack}  (run --fetch)")
        ok = False
    return 0 if ok else 1


def fetch() -> int:
    BRIDGE.mkdir(parents=True, exist_ok=True)
    target = BRIDGE / STACK["name"]
    if not target.exists():
        tmp = BRIDGE / "_parts"
        tmp.mkdir(exist_ok=True)
        for part in STACK["parts"]:
            dest = tmp / part
            if dest.exists():
                continue
            url = ("https://github.com/buffedlizard55-lab/GEMSDOE2/raw/main/data/bridge/"
                   + part)
            print("fetching", part, flush=True)
            subprocess.run(["curl", "-sSL", "-o", str(dest), url], check=True)
        with open(target, "wb") as out:
            for part in STACK["parts"]:
                out.write((tmp / part).read_bytes())
    digest = sha256(target)
    print("reassembled sha256", digest)
    if digest != STACK["sha256"]:
        print("SHA-256 MISMATCH — refusing to publish anything built from this file")
        return 2
    EXT.mkdir(parents=True, exist_ok=True)
    for name, want in PINS.items():
        p = EXT / name
        if not p.exists():
            print("fetching", name, flush=True)
            subprocess.run(["curl", "-sSL", "-o", str(p), EXT_MIRROR + name], check=True)
        got = sha256(p)
        print(f"{name:32s} {'pin OK' if got == want else 'PIN MISMATCH'}")
        if got != want:
            return 2
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    args = ap.parse_args()
    if args.fetch:
        return fetch()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
