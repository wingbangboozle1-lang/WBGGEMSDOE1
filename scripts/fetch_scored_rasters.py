#!/usr/bin/env python3
"""Fetch the owner-reported scored GEMSDOE rasters from their immutable GitHub commits.

Why: the 118 scored submissions are the only observations we have of the hidden
private test set.  Reconstructing them locally lets us calibrate a distance-weighted
Tversky (DTI) score estimator against real leaderboard feedback without spending a
submission slot.

Provenance discipline:
  * sources are the public GitHub blobs recorded in registry/wbg_h1/scored_registry.json;
  * every download is sha256-checked against that registry and rejected on mismatch;
  * scores stay labelled OWNER-REPORTED (no organizer receipt binds them).

No organizer data is downloaded here and nothing is uploaded.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry/wbg_h1/scored_registry.json"
CACHE = ROOT / ".cache/scored"


def gh_contents(repo: str, path: str) -> bytes:
    """Raw blob through the contents API (api.github.com is the allowed host)."""
    out = subprocess.run(
        ["gh", "api", f"repos/buffedlizard55-lab/{repo}/contents/{path}",
         "-H", "Accept: application/vnd.github.raw"],
        capture_output=True, check=True,
    ).stdout
    if not out:
        raise RuntimeError(f"empty response for {repo}:{path}")
    return out


def main() -> int:
    entries = json.loads(REG.read_text())["entries"]
    CACHE.mkdir(parents=True, exist_ok=True)
    ok = fail = cached = 0
    report = []
    for i, e in enumerate(entries):
        dest = CACHE / f"{e['repo']}__{Path(e['path']).name}"
        rec = {"repo": e["repo"], "path": e["path"], "name": e["name"],
               "score": e["score"], "registry_sha256": e["sha256"]}
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == e["sha256"]:
            rec.update(local=str(dest.relative_to(ROOT)), status="cached")
            cached += 1
            report.append(rec)
            continue
        try:
            blob = gh_contents(e["repo"], e["path"])
        except subprocess.CalledProcessError as exc:
            rec.update(status="download_failed",
                       detail=(exc.stderr or b"").decode()[:200])
            fail += 1
            report.append(rec)
            print(f"[{i+1}/{len(entries)}] FAIL {e['repo']}:{e['path']}", file=sys.stderr)
            continue
        got = hashlib.sha256(blob).hexdigest()
        if got != e["sha256"]:
            rec.update(status="sha256_mismatch", got=got)
            fail += 1
            report.append(rec)
            print(f"[{i+1}/{len(entries)}] HASH MISMATCH {e['repo']}:{e['path']}",
                  file=sys.stderr)
            continue
        dest.write_bytes(blob)
        rec.update(local=str(dest.relative_to(ROOT)), status="downloaded", bytes=len(blob))
        ok += 1
        report.append(rec)
        if (i + 1) % 20 == 0:
            print(f"[{i+1}/{len(entries)}] {ok} downloaded, {cached} cached, {fail} failed",
                  file=sys.stderr)
    out = {"schema": "wbg-scored-raster-fetch-v1",
           "score_label": "OWNER-REPORTED (never ORGANIZER-CONFIRMED)",
           "registry": str(REG.relative_to(ROOT)),
           "n_entries": len(entries), "downloaded": ok, "cached": cached, "failed": fail,
           "entries": report}
    (ROOT / "evidence/scored_raster_fetch.json").parent.mkdir(exist_ok=True)
    (ROOT / "evidence/scored_raster_fetch.json").write_text(json.dumps(out, indent=1))
    print(f"downloaded={ok} cached={cached} failed={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
