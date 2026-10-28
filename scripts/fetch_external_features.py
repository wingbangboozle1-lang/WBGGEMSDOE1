#!/usr/bin/env python3
"""Fetch hash-pinned external feature rasters used by the WBG-5 lane.

Provenance
----------
Every product below originates from the official USGS GeoDAWN airborne magnetic and
radiometric release (DOI 10.5066/P93LGLVQ, ScienceBase item 657e1d85d34e23d3533209f7)
and from the USGS 3DEP 1 m LiDAR DEM that the competition distributes as links in
``1m_DEM_links.csv``.

They are *not* downloaded from ``usgs.gov`` in this sandbox (egress allow-list). They are
fetched from a **peer mirror** that re-derived them onto the competition grid, so the
integrity claim proved here is "owner-mirror content hash", **not** independent
organizer-origin authentication. That limitation is recorded in the manifest and must be
repeated anywhere these features are used.

Usage
-----
    python scripts/fetch_external_features.py            # fetch missing, verify pins
    python scripts/fetch_external_features.py --check    # verify only, never write

Nothing outside ``.cache/ext/`` (git-ignored) is written.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "ext"
MIRROR_REPO = "buffedlizard55-lab/GEMSDOE24"
MIRROR_COMMIT = "7790c3b3038e3fb34f2fe844e10d187a02fa3ab4"

# name -> (git blob sha1 in the mirror commit, expected sha256 of the bytes, size, role)
PRODUCTS: dict[str, dict] = {
    "lidar_scarp_features_u8.tif": {
        "blob": "da733b53147efad5c141ffdb96e469ec5b4da8b8",
        "sha256": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
        "bytes": 36943606,
        "role": "11 LiDAR-DEM scarp-morphology channels + valid mask",
        "source": "USGS 3DEP 1 m LiDAR DEM (competition 1m_DEM_links.csv)",
    },
    "geodawn_rad_u8.tif": {
        "blob": "80704748f974ea9dbc002924ddf971a957186ae6",
        "sha256": "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
        "bytes": 26612970,
        "role": "4 channels: K, Th, U, TC (total count) radiometrics",
        "source": "USGS GeoDAWN DOI 10.5066/P93LGLVQ",
    },
    "geodawn_extensions_u8.tif": {
        "blob": "2fb1d57fdd33b0bdea51f2abef58fb5cddf53aa5",
        "sha256": "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
        "bytes": 27132925,
        "role": "4 channels: ThK, UK, UTh, TMI upward-continued 150 m",
        "source": "USGS GeoDAWN DOI 10.5066/P93LGLVQ",
    },
    "tiger_road_distance_m.tif": {
        "blob": None,
        "sha256": None,
        "bytes": None,
        "role": "named non-fault linear mimic control (TIGER roads, metres)",
        "source": "US Census TIGER/Line (public domain)",
    },
    "gdr_qfaults_traces.csv": {
        "blob": "b2e66237d5e3111c113834ead0d209adbae8443e",
        "sha256": None,
        "bytes": 126177,
        "role": "public Quaternary fault traces (same catalogue as labels.tif)",
        "source": "USGS Quaternary Fault and Fold Database / INGENIOUS",
    },
    "gdr_wellspring_in_footprint.csv": {
        "blob": "29182e7a92dddf460afb1e53ecd82c7e2d6219e1",
        "sha256": None,
        "bytes": 2146771,
        "role": "geothermal wells and springs inside the footprint (context, not labels)",
        "source": "USGS/GDR geothermal well and spring inventories",
    },
    "gdr_volcanic_vents_in_footprint.csv": {
        "blob": "37e94f8aadfa253c06bbbc65628974c42d5f4290",
        "sha256": None,
        "bytes": 672,
        "role": "volcanic vents inside the footprint (context)",
        "source": "USGS volcanic vent inventory",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(name: str, blob: str) -> None:
    target = CACHE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    out = subprocess.run(
        ["gh", "api", f"repos/{MIRROR_REPO}/git/blobs/{blob}", "--jq", ".content"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    partial.write_bytes(base64.b64decode("".join(out.split())))
    partial.replace(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    missing = 0
    for name, pin in PRODUCTS.items():
        path = CACHE / name
        if not path.exists():
            if args.check:
                print(f"MISSING {name}")
                missing += 1
                continue
            if not pin["blob"]:
                print(f"SKIP    {name}: no pinned blob, must be supplied locally")
                missing += 1
                continue
            print(f"FETCH   {name} ({pin['bytes']} bytes)", flush=True)
            fetch(name, pin["blob"])
        digest = sha256_file(path)
        size = path.stat().st_size
        ok = pin["sha256"] is None or digest == pin["sha256"]
        if pin["bytes"] is not None and size != pin["bytes"]:
            ok = False
        print(f"{'OK     ' if ok else 'MISMATCH'} {name} {digest} {size}")
        rows.append(
            {
                "name": name,
                "sha256": digest,
                "bytes": size,
                "pin_sha256": pin["sha256"],
                "pin_verified": bool(ok),
                "role": pin["role"],
                "source": pin["source"],
            }
        )

    manifest = {
        "schema": "gemsdoe1-external-feature-fetch-v1",
        "mirror_repo": MIRROR_REPO,
        "mirror_commit": MIRROR_COMMIT,
        "provenance_class": "OWNER-MIRROR (not organizer-authenticated)",
        "limitation": (
            "Hashes prove mirror content identity only. The upstream USGS GeoDAWN DOI "
            "and 3DEP provenance is asserted by the mirror's metadata JSON, not re-verified "
            "against usgs.gov from this sandbox."
        ),
        "products": rows,
    }
    (CACHE / "fetch_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    mismatched = [r for r in rows if not r["pin_verified"]]
    print(f"\n{len(rows)} product(s) inventoried, {len(mismatched)} pin mismatch, {missing} missing")
    return 1 if mismatched or (args.check and missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
