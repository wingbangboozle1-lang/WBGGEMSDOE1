#!/usr/bin/env python3
"""Restore the frozen nine-site audit corpus (ignored cache; never model inputs)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wbggems.audit import dump_json, sha256, utc_now


def restore(row):
    repo = row["repo"]
    ref = row["ref"]
    if repo.count("/") != 1 or not repo.startswith("buffedlizard55-lab/") or len(ref) != 40 or any(c not in "0123456789abcdef" for c in ref):
        raise ValueError("invalid repository pin")
    cache = ROOT / ".cache/research"
    destination = cache / repo.split("/")[1]
    marker = destination / ".snapshot-pin"
    if marker.exists() and marker.read_text().strip() == ref:
        return {"repo": repo, "ref": ref, "status": "reused"}
    archive = cache / (repo.split("/")[1] + ".tar.gz")
    temporary = archive.with_suffix(".partial")
    cache.mkdir(parents=True, exist_ok=True)
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    # Fresh archive avoids silently reusing an earlier branch-head tarball.
    try:
        urllib.request.urlretrieve(url, temporary)
        temporary.replace(archive)
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as tar:
            for member in tar:
                parts = Path(member.name).parts[1:]
                if not parts or any(p in ("..", ".", "") for p in parts):
                    continue
                target = destination.joinpath(*parts)
                if not target.resolve().is_relative_to(destination.resolve()):
                    raise ValueError("unsafe archive member")
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as src, target.open("wb") as out:
                        shutil.copyfileobj(src, out)
        marker.write_text(ref + "\n")
        return {"repo": repo, "ref": ref, "status": "restored", "archive_sha256": sha256(archive)}
    finally:
        temporary.unlink(missing_ok=True)


def main():
    pins = json.loads((ROOT / "registry/repository_snapshots.json").read_text())["repositories"]
    rows = list(ThreadPoolExecutor(max_workers=4).map(restore, pins))
    # Recreate tree metadata from immutable git trees if the cache was absent.
    import subprocess
    for pin in pins:
        repo = pin["repo"].split("/")[1]
        tree = ROOT / ".cache/research" / f"{repo}-tree.json"
        cached_tree = json.loads(tree.read_text()) if tree.exists() else {}
        if cached_tree.get("commit_sha") != pin["ref"]:
            commit = json.loads(subprocess.check_output(["gh", "api", f"repos/{pin['repo']}/commits/{pin['ref']}"]))
            if commit["sha"] != pin["ref"]:
                raise ValueError("commit pin did not resolve exactly")
            data = json.loads(subprocess.check_output(["gh", "api", f"repos/{pin['repo']}/git/trees/{commit['commit']['tree']['sha']}?recursive=1"]))
            if data.get("truncated"):
                raise ValueError("truncated tree cannot certify registry completeness")
            data["commit_sha"] = pin["ref"]
            data["resolved_tree_sha"] = commit["commit"]["tree"]["sha"]
            tree.write_text(json.dumps(data, indent=2) + "\n")
    dump_json(ROOT / "evidence/repository_restore.json", {"generated_utc": utc_now(), "rows": rows})
    print("Restored frozen nine-site audit corpus; do not execute its research scripts or use its predictions as training labels.")


if __name__ == "__main__":
    main()
