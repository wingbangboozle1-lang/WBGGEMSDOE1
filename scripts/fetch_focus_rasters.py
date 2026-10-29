#!/usr/bin/env python3
"""Fetch every registry-listed focus-site raster into a git-ignored cache, sha256-verified.

Why: the uniqueness gate must compare a candidate against the actual previously
submitted rasters, not against a summary. The inputs are the immutable GitHub
blobs recorded in ``registry/focus_files.json`` (377 TIFFs from the nine focus
sites, GEMSDOE24/25/27/28/30/31/32/33/36) and ``registry/wbg_h1/scored_registry.json``
(118 owner-reported scored rasters).

Provenance discipline:
  * each download goes through the GitHub contents API (api.github.com, allow-listed);
  * every file is sha256-checked against the registry and rejected on mismatch;
  * nothing is committed: the cache lives under ``.cache/`` (git-ignored) and can be
    rebuilt from the registry at any time.

Usage: ``.venv/bin/python scripts/fetch_focus_rasters.py``
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOCUS = ROOT / "registry/focus_files.json"
SCORED = ROOT / "registry/wbg_h1/scored_registry.json"
CACHE = ROOT / ".cache/focus_rasters"
MANIFEST = ROOT / "registry/focus_raster_fetch.json"


def gh_raw(owner_repo: str, path: str, ref: str) -> bytes:
    out = subprocess.run(
        ["gh", "api", f"repos/{owner_repo}/contents/{path}?ref={ref}",
         "-H", "Accept: application/vnd.github.raw"],
        capture_output=True, check=True,
    ).stdout
    if not out:
        raise RuntimeError(f"empty response for {owner_repo}:{path}")
    return out


def collect() -> list[dict]:
    items: dict[tuple[str, str], dict] = {}
    for f in json.loads(FOCUS.read_text())["files"]:
        items[(f["repo"], f["path"])] = {
            "repo": f["repo"], "path": f["path"], "sha256": f["sha256"],
            "ref": f["ref"], "source": "focus_files",
        }
    snaps = json.loads(FOCUS.read_text())["snapshots"]
    for e in json.loads(SCORED.read_text())["entries"]:
        key = (e["repo"], e["path"])
        if key in items:
            continue
        # scored-registry entries have no pinned commit; they are fetched at the
        # default branch, and the sha256 must still match the registry pin.
        if e["repo"] in snaps:
            ref = snaps[e["repo"]]
        else:
            ref = None
        items[key] = {
            "repo": e["repo"], "path": e["path"], "sha256": e["sha256"],
            "ref": ref, "source": "scored_registry", "score": e.get("score"),
            "name": e.get("name"),
        }
    return list(items.values())


def fetch_one(item: dict) -> dict:
    repo_name = item["repo"]
    owner_repo = f"buffedlizard55-lab/{repo_name}"
    dest = CACHE / f"{repo_name}__{Path(item['path']).name}"
    rec = {k: item.get(k) for k in ("repo", "path", "sha256", "source", "score", "name")}
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == item["sha256"]:
        rec.update(status="cached", local=str(dest.relative_to(ROOT)))
        return rec
    ref = item.get("ref")
    try:
        blob = gh_raw(owner_repo, item["path"], ref) if ref else gh_raw(owner_repo, item["path"], "HEAD")
    except subprocess.CalledProcessError as exc:
        rec.update(status="download_failed", detail=(exc.stderr or b"").decode()[:200])
        return rec
    got = hashlib.sha256(blob).hexdigest()
    if got != item["sha256"]:
        rec.update(status="sha256_mismatch", got=got)
        return rec
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(blob)
    rec.update(status="downloaded", local=str(dest.relative_to(ROOT)), bytes=len(blob))
    return rec


def main() -> int:
    items = collect()
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        recs = list(pool.map(fetch_one, items))
    counts: dict[str, int] = {}
    for r in recs:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    MANIFEST.write_text(json.dumps({
        "schema": "gemsdoe1-focus-raster-fetch-v1",
        "score_label": "OWNER-REPORTED (never ORGANIZER-CONFIRMED)",
        "counts": counts,
        "entries": recs,
    }, indent=1) + "\n")
    print(json.dumps(counts))
    bad = [r for r in recs if r["status"] not in ("cached", "downloaded")]
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
