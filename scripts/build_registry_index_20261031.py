#!/usr/bin/env python3
"""Build the complete 118-raster uniqueness index used by the shared gems57 gates.

Source of truth: registry/wbg_h1/scored_registry.json (owner-reported scored GitHub
rasters, each with a SHA-256). Each cached file in .cache/scored is re-hashed against
that SHA-256 before it enters the index; any mismatch aborts the build (fail closed).

Output: evidence/uniqueness/registry_index_20261031.json in the format expected by
vendor/gems57/uniqueness.py::records_from_index (``rasters`` list + completeness flag).
Scores in the index are OWNER-REPORTED labels, never organizer confirmations.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry/wbg_h1/scored_registry.json"
CACHE = ROOT / ".cache/scored"
OUT = ROOT / "evidence/uniqueness/registry_index_20261031.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    entries = json.loads(REG.read_text())["entries"]
    rasters, errors = [], []
    seen_sha = {}
    for e in entries:
        cache_file = CACHE / f"{e['repo']}__{Path(e['path']).name}"
        if not cache_file.exists():
            errors.append(f"missing cache: {cache_file.name}")
            continue
        digest = sha256(cache_file)
        if digest != e["sha256"]:
            errors.append(f"sha mismatch: {cache_file.name}")
            continue
        rel = str(cache_file.relative_to(ROOT))
        rasters.append(dict(repo_first=e["repo"], sources=[e["name"]], cache_file=rel,
                            sha256=digest, site=e["site"], owner_reported_score=e["score"],
                            score_label="OWNER-REPORTED"))
        seen_sha.setdefault(digest, []).append(e["name"])
    duplicates = {k: v for k, v in seen_sha.items() if len(v) > 1}
    doc = dict(schema="gems-registry-index-v1", description=__doc__.split("\n")[0],
               n_entries=len(entries), complete_accessible_scan=(not errors and len(rasters) == len(entries)),
               errors=errors, identical_bytes_groups=len(duplicates), rasters=rasters,
               registry_source=str(REG.relative_to(ROOT)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, allow_nan=False) + "\n")
    print(f"rasters={len(rasters)}/{len(entries)} complete={doc['complete_accessible_scan']} errors={len(errors)}")
    return 0 if doc["complete_accessible_scan"] else 1


if __name__ == "__main__":
    sys.exit(main())
