#!/usr/bin/env python3
"""Fetch hash-pinned competitor anchor rasters for calibration and uniqueness checks.

Purpose
-------
The nine focus sites only publish an OWNER-REPORTED score, never a receipt that
binds a score to bytes. To compare our raster against them we need the bytes, and
to compare honestly we need them at an immutable commit. Every anchor below is
listed in ``registry/focus_files.json`` with its ``sha256`` and ``git_blob_sha``;
this script re-downloads by blob SHA and re-verifies the SHA-256 before use.

Anchors are used for two things only:
  1. a *relative* score estimate (same evaluator, same holdout), and
  2. a novelty screen (Spearman of surfaces + 3 px dot overlap).

They are never used as model features, training labels or a source of pixels for
a generated submission.

    python scripts/fetch_anchor_rasters.py          # fetch + verify
    python scripts/fetch_anchor_rasters.py --check  # verify only
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "anchors"

# name -> (repo, blob sha, owner-reported score, what the score is)
# The authoritative SHA-256 for every blob comes from registry/focus_files.json.
ANCHORS = {
    "gemsdoe32-h33-b2-zeros": (
        "buffedlizard55-lab/GEMSDOE32",
        "17a76895f68174cc93f3cb1597d25686f6d6bc67",
        0.2778,
        "highest OWNER-REPORT in the nine focus sites",
    ),
    "gemsdoe32-h33-b2-nan": (
        "buffedlizard55-lab/GEMSDOE32",
        "c00c2ca916c046544baeb6e40d1e782bf46f50c0",
        0.2778,
        "same dot set, NaN-outside convention",
    ),
    "gemsdoe25-dotted-d2-8-nan": (
        "buffedlizard55-lab/GEMSDOE24",
        "c8d3a46481152bbdfd61b113484be979fde9d4c6",
        0.2600,
        "GEMSDOE25 d2.8 (byte-identical to the GEMSDOE30 d28-poisson clone)",
    ),
    "gemsdoe24-dotted-d1-5-nan": (
        "buffedlizard55-lab/GEMSDOE24",
        "cc1752f2ea48b23bd41232c1fdcdceb5f439e401",
        0.2477,
        "GEMSDOE24 h25-1 dotted d1.5",
    ),
    "gemsdoe31-h27-4-solo-d28-nan": (
        "buffedlizard55-lab/GEMSDOE31",
        "36c2aa32e0bba3d976d1ba76f3fb14903199262d",
        0.2708,
        "GEMSDOE31 h27-4 solo d28",
    ),
    "gemsdoe28-h36-1-rung30-nan": (
        "buffedlizard55-lab/GEMSDOE28",
        "d0fc9ebbda0b15c31208022dbd124d4b9b112108",
        0.2710,
        "GEMSDOE28 h36-1 rung30 blind",
    ),
    "gemsdoe28-h38-1-hf-euler-nan": (
        "buffedlizard55-lab/GEMSDOE28",
        "c20459cd43667af1404447362c8cb8e81696871e",
        0.2707,
        "GEMSDOE28 h38-1 HF euler",
    ),
    "gemsdoe28-h27-4-r1-solo-nan": (
        "buffedlizard55-lab/GEMSDOE28",
        "12b0a4ddf1cf76f2552621b8a8b1a1b88d783786",
        0.2708,
        "GEMSDOE28 h27-4 r1 solo d2.8",
    ),
    "gemsdoe28-h32-1-prethin-nan": (
        "buffedlizard55-lab/GEMSDOE28",
        "6d9717d75f144ccbd3c8ec7886000fae95af312e",
        0.2649,
        "GEMSDOE28 h32-1 prethin tip euler",
    ),
    "gemsdoe36-anderson-pinn-nan": (
        "buffedlizard55-lab/GEMSDOE36",
        "366095dcdb3c71c1a84cdcb840c0f90c4047cc48",
        0.2750,
        "GEMSDOE36 Anderson geothermal PINN",
    ),
    "gemsdoe33-h33d-analog-nanoutside": (
        "buffedlizard55-lab/GEMSDOE33",
        "c6e73d35a5ee8a36abdd06b7314bf79646c5d7f9",
        0.2632,
        "GEMSDOE33 h33d analog tip stepover r30",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def focus_sha256() -> dict[str, str]:
    """authoritative sha256 values from the immutable registry."""
    data = json.loads((ROOT / "registry" / "focus_files.json").read_text())
    return {row["git_blob_sha"]: row["sha256"] for row in data["files"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    pins = focus_sha256()

    rows = []
    for name, (repo, blob, score, note) in ANCHORS.items():
        expected = pins.get(blob)
        if expected is None:
            print(f"SKIP {name}: blob {blob} is not in registry/focus_files.json")
            continue
        path = CACHE / f"{name}.tif"
        if not path.exists() and not args.check:
            out = subprocess.run(
                ["gh", "api", f"repos/{repo}/git/blobs/{blob}", "--jq", ".content"],
                check=True, capture_output=True, text=True,
            ).stdout
            path.write_bytes(base64.b64decode("".join(out.split())))
        if not path.exists():
            print(f"MISSING {name}")
            continue
        digest = sha256_file(path)
        ok = digest == expected
        print(f"{'OK  ' if ok else 'FAIL'} {name} {digest[:16]} (registry {expected[:16]})")
        rows.append({
            "name": f"{name}.tif",
            "repo": repo,
            "git_blob_sha": blob,
            "sha256": digest,
            "sha256_verified": bool(ok),
            "owner_reported_score": score,
            "score_label": "OWNER-REPORTED / UNVERIFIED (no organizer receipt)",
            "note": note,
        })

    (CACHE / "anchors.json").write_text(json.dumps({
        "schema": "gemsdoe1-wbg5-anchors-v1",
        "usage": "relative score calibration and novelty screen only; never model features",
        "anchors": rows,
    }, indent=1) + "\n")
    bad = [r for r in rows if not r["sha256_verified"]]
    print(f"\n{len(rows)} anchors verified, {len(bad)} mismatched")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
