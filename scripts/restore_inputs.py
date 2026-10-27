#!/usr/bin/env python3
"""Restore the exact cached LiDAR feature stack without committing its 37 MB blob."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/buffedlizard55-lab/GEMSDOE24.git"
COMMIT = "7790c3b3038e3fb34f2fe844e10d187a02fa3ab4"
SOURCE_PATH = "data/external/lidar_scarp_features_u8.tif"
EXPECTED_SHA256 = "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568"
EXPECTED_BYTES = 36_943_606
DESTINATION = ROOT / SOURCE_PATH


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def valid(path: Path) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == EXPECTED_BYTES
        and sha256(path) == EXPECTED_SHA256
    )


def restore(force: bool = False) -> Path:
    if valid(DESTINATION) and not force:
        print(f"OK already restored: {DESTINATION.relative_to(ROOT)} sha256={EXPECTED_SHA256}")
        return DESTINATION

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gemsdoe1-input-") as temporary:
        checkout = Path(temporary) / "source"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-checkout",
                "--filter=blob:none",
                REPOSITORY,
                str(checkout),
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(checkout), "fetch", "--quiet", "--depth=1", "origin", COMMIT],
            check=True,
        )
        payload = subprocess.run(
            ["git", "-C", str(checkout), "show", f"{COMMIT}:{SOURCE_PATH}"],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        candidate = Path(temporary) / "payload.tif"
        candidate.write_bytes(payload)
        if not valid(candidate):
            raise RuntimeError(
                f"restored input failed integrity check: bytes={candidate.stat().st_size}, "
                f"sha256={sha256(candidate)}"
            )
        shutil.copyfile(candidate, DESTINATION)

    print(f"OK restored: {DESTINATION.relative_to(ROOT)} sha256={EXPECTED_SHA256}")
    return DESTINATION


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace even a valid local copy")
    args = parser.parse_args()
    restore(args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
