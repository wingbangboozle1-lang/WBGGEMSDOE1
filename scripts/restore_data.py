#!/usr/bin/env python3
"""Restore and SHA-256 verify competition, external, and comparison registry rasters.

Every restored byte is checked against immutable SHA-256 digests in
``registry/data_manifest.json`` and ``registry/scored_registry.json``.
Registry rasters are strictly comparison-only (for Live-Ledger Inversion calibration,
9-site lineage forensics, and novelty gating); zero pixels are ever copied into a candidate.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbggems1.paths import raw_data_dir  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_github_blob(repo_full: str, path: str, ref: str | None, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    endpoint = f"repos/{repo_full}/contents/{path}" + (f"?ref={ref}" if ref else "")
    try:
        if shutil.which("gh"):
            with tmp.open("wb") as out:
                subprocess.run(
                    ["gh", "api", endpoint, "-H", "Accept: application/vnd.github.raw"],
                    stdout=out,
                    check=True,
                )
        else:
            import urllib.request

            branch = ref or "main"
            url = f"https://raw.githubusercontent.com/{repo_full}/{branch}/{path}"
            req = urllib.request.Request(url, headers={"User-Agent": "WBGGEMSDOE1-Restore/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r, tmp.open("wb") as out:
                shutil.copyfileobj(r, out)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def restore_manifest_entry(entry: dict, target_root: Path) -> dict:
    dest = target_root / entry["dest"]
    if dest.is_file() and sha256_file(dest) == entry["sha256"]:
        return {
            "id": entry["id"],
            "dest": entry["dest"],
            "group": entry["group"],
            "status": "present",
            "bytes": dest.stat().st_size,
            "sha256": entry["sha256"],
        }
    if "parts" in entry:
        tmp = dest.with_suffix(".assembling")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("wb") as out:
            for part in entry["parts"]:
                part_dest = target_root / "_parts" / Path(part).name
                fetch_github_blob(entry["repo"], part, entry["ref"], part_dest)
                with part_dest.open("rb") as src:
                    shutil.copyfileobj(src, out, 1 << 20)
                part_dest.unlink(missing_ok=True)
        got = sha256_file(tmp)
        if got != entry["sha256"]:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"SHA-256 mismatch for {entry['id']}: {got} != {entry['sha256']}")
        tmp.replace(dest)
    else:
        fetch_github_blob(entry["repo"], entry["path"], entry["ref"], dest)
        got = sha256_file(dest)
        if got != entry["sha256"]:
            dest.unlink(missing_ok=True)
            raise RuntimeError(f"SHA-256 mismatch for {entry['id']}: {got} != {entry['sha256']}")
    return {
        "id": entry["id"],
        "dest": entry["dest"],
        "group": entry["group"],
        "status": "restored",
        "bytes": dest.stat().st_size,
        "sha256": entry["sha256"],
    }


def _restore_one_scored(row: dict, reg_root: Path) -> tuple[str, bool, str]:
    rel = row["local"]
    dest = reg_root / rel
    label_name = row.get("name") or row.get("local")
    if dest.is_file() and sha256_file(dest) == row["sha256"]:
        return (label_name, True, "present")
    repo_raw = row.get("repo") or row.get("site")
    repo_full = repo_raw if "/" in repo_raw else f"buffedlizard55-lab/{repo_raw}"
    ref = row.get("ref") or row.get("commit")
    try:
        fetch_github_blob(repo_full, row["path"], ref, dest)
        got = sha256_file(dest)
        if got != row["sha256"]:
            dest.unlink(missing_ok=True)
            return (label_name, False, f"hash_mismatch:{got[:12]}")
        return (label_name, True, "restored")
    except Exception as exc:
        dest.unlink(missing_ok=True)
        return (label_name, False, f"error:{exc}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--group", default="all", choices=["core", "external", "scored", "all"])
    ap.add_argument("--include-registry", action="store_true", help="Also restore scored_registry.json rasters")
    ap.add_argument("--target-dir", type=Path, default=None)
    args = ap.parse_args()

    target_root = args.target_dir or raw_data_dir()
    target_root.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    verified = []
    for entry in manifest["files"]:
        if args.group in ("all", entry["group"]):
            res = restore_manifest_entry(entry, target_root)
            verified.append(res)
            print(f"  [{res['status']:>8}] {entry['dest']:58s} ({res['bytes']:,} B)")

    reg_summary = None
    if args.include_registry:
        scored_reg = json.loads((ROOT / "registry" / "scored_registry.json").read_text())
        peer_reg = json.loads((ROOT / "registry" / "peer_downloads.json").read_text())
        focus9_reg = json.loads((ROOT / "registry" / "focus9_latest_20261026.json").read_text())
        entries = list(scored_reg["entries"]) + list(peer_reg.get("entries", peer_reg))
        reg_root = target_root / "registry_cache"
        reg_root.mkdir(parents=True, exist_ok=True)
        focus_root = target_root / "focus9_latest"
        focus_root.mkdir(parents=True, exist_ok=True)
        ok_count = 0
        fail_rows = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(_restore_one_scored, r, reg_root) for r in entries] + [
                ex.submit(_restore_one_scored, r, focus_root) for r in focus9_reg["entries"]
            ]
            total_jobs = len(futs)
            for fut in concurrent.futures.as_completed(futs):
                name, ok, msg = fut.result()
                if ok:
                    ok_count += 1
                else:
                    fail_rows.append({"name": name, "reason": msg})
        reg_summary = {
            "total_entries": total_jobs,
            "verified_ok": ok_count,
            "failed_or_moved_upstream": len(fail_rows),
            "failures": fail_rows[:25],
        }
        print(f"  [registry] Verified {ok_count}/{total_jobs} registry + peer + focus9 rasters")

    receipt = {
        "schema_version": 1,
        "requested_group": args.group,
        "manifest_verified_count": len(verified),
        "manifest_files": verified,
        "scored_registry": reg_summary,
    }
    (ROOT / "evidence").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence" / "data_restore_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
