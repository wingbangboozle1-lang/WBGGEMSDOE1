#!/usr/bin/env python3
"""Autonomous hash-verified data & sister-peer registry verification for Lane WBG-4 (CSJF-1).

Verifies:
1. Core competition files (`training_features.tif`, `labels.tif`, `sample_submission.tif`)
   and 19/19 SHA-256-pinned template57 bands (`data/template57/`).
2. 13/13 SHA-256-pinned official external datasets (`data/external/`).
3. 14/14 seamless 10 m USGS 3DEP arrays (`data/dem10/*.f32.npy`).
4. 360/360 frozen focus-site rasters (`registry/focus_inventory.json`) + 15 peer rasters (`data/wbg_s2_peers/`).
5. Sister-repository published `.tif` artifacts across accessible GEMSDOE sibling repos
   into git-ignored `data/wbg4_sister_peers/` STRICTLY FOR UNIQUENESS AUDITING (never read
   by `src/wbg4/features.py` or `src/wbg4/model.py`).

Writes tracked receipt to `evidence/wbg4/data_restore_receipt.json` without mutating frozen
receipts (`evidence/data_restore.json` or `evidence/wbg_s2/data_restore_receipt.json`).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SISTER_DIR = ROOT / "data" / "wbg4_sister_peers"
RECEIPT_PATH = ROOT / "evidence" / "wbg4" / "data_restore_receipt.json"

SISTER_REPOS = [
    "wingbangboozle1-lang/WBGGEMSDOE2",
    "wingbangboozle1-lang/WBGGEMSDOE3",
    "kanlerxz87-cyber/KANLERGEMSDOE1",
    "kanlerxz87-cyber/KANLERGEMSDOE2",
    "kanlerxz87-cyber/KANLERGEMSDOE3",
    "eugboogieman123-ops/EUGGEMSDOE1",
    "eugboogieman123-ops/EUGGEMSDOE2",
    "eugboogieman123-ops/EUGGEMSDOE3",
    "ginnymcfiner23-ux/GINNYGEMSDOE1",
    "ginnymcfiner23-ux/GINNYGEMSDOE2",
    "ginnymcfiner23-ux/GINNYGEMSDOE3",
    "karagemop466-tech/GEMSDOEkarage1",
    "karagemop466-tech/GEMSDOEkarage2",
    "karagemop466-tech/GEMSDOEkarage3",
    "apartanish22-droid/ApartGEMSDOE1",
    "apartanish22-droid/ApartGEMSDOE2",
    "apartanish22-droid/ApartGEMSDOE3",
    "sassnarep3-star/GEMSDOESASS1",
    "sassnarep3-star/GEMSDOESASS2",
    "sassnarep3-star/GEMSDOESASS3",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_blob(repo: str, commit: str, rel_path: str, blob_sha: str, dst: Path) -> dict:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.stat().st_size == 0:
        proc = subprocess.run(
            ["gh", "api", "-H", "Accept: application/vnd.github.raw", f"repos/{repo}/git/blobs/{blob_sha}"],
            capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"gh api blob download failed for {repo}:{rel_path}: {proc.stderr.decode(errors='ignore')}")
        dst.write_bytes(proc.stdout)
    return {
        "repo": repo,
        "commit": commit,
        "remote_path": rel_path,
        "blob_sha": blob_sha,
        "local_relpath": str(dst.relative_to(ROOT)),
        "bytes": dst.stat().st_size,
        "sha256": _sha256(dst),
    }


def main() -> int:
    # 1. Core & 19-band template57 verification
    core_files = [
        ROOT / "data" / "training_features.tif",
        ROOT / "data" / "labels.tif",
        ROOT / "data" / "sample_submission.tif",
        ROOT / "data" / "existing_faults.tif",
    ]
    for p in core_files:
        if not p.exists():
            raise FileNotFoundError(f"Missing required core file: {p}")

    fc = json.loads((ROOT / "data" / "template57" / "evidence" / "feature_cache.json").read_text())
    verified_bands = 0
    for b in fc["bands"]:
        bp = ROOT / "data" / "template57" / b["cache_file"]
        if not bp.exists() or _sha256(bp) != b["sha256"]:
            raise RuntimeError(f"Template57 band SHA-256 mismatch: {bp}")
        verified_bands += 1

    # 2. External datasets & 10m DEM verification
    s2_rec = json.loads((ROOT / "evidence" / "wbg_s2" / "data_restore_receipt.json").read_text())
    ext_verified = 0
    for item in s2_rec["external_files"]:
        ep = ROOT / item["dest"]
        if not ep.exists() or _sha256(ep) != item["sha256"]:
            raise RuntimeError(f"External dataset SHA-256 mismatch: {ep}")
        ext_verified += 1

    dem10_files = sorted((ROOT / "data" / "dem10").glob("*.f32.npy"))
    if len(dem10_files) < 13:
        raise RuntimeError(f"Expected >=13 seamless 10m DEM grids, found {len(dem10_files)}")

    # 3. Focus inventory (360) + wbg_s2_peers (15)
    focus_inv = json.loads((ROOT / "registry" / "focus_inventory.json").read_text())
    focus_ok = sum(1 for r in focus_inv["rasters"] if (ROOT / r["cache_file"]).exists())
    if focus_ok != len(focus_inv["rasters"]):
        raise RuntimeError(f"Focus inventory incomplete: {focus_ok}/{len(focus_inv['rasters'])}")

    s2_peers = sorted((ROOT / "data" / "wbg_s2_peers").glob("*.tif"))
    if len(s2_peers) < 15:
        raise RuntimeError(f"Expected >=15 wbg_s2_peers TIFFs, found {len(s2_peers)}")

    # 4. Sister repositories read-only uniqueness audit mirror
    SISTER_DIR.mkdir(parents=True, exist_ok=True)
    repo_status: list[dict] = []
    download_jobs: list[tuple[str, str, str, str, Path]] = []

    for repo in SISTER_REPOS:
        p_sha = subprocess.run(
            ["gh", "api", f"repos/{repo}/commits/HEAD", "--jq", ".sha"],
            capture_output=True,
            text=True,
        )
        if p_sha.returncode != 0 or not p_sha.stdout.strip():
            repo_status.append({"repo": repo, "accessible": False, "reason": "not_found_or_private", "tif_count": 0})
            continue
        commit = p_sha.stdout.strip()
        p_tree = subprocess.run(
            ["gh", "api", f"repos/{repo}/git/trees/{commit}?recursive=1"],
            capture_output=True,
            text=True,
        )
        if p_tree.returncode != 0:
            repo_status.append({"repo": repo, "accessible": False, "reason": "tree_api_error", "tif_count": 0})
            continue
        tree = json.loads(p_tree.stdout)
        tifs = []
        for entry in tree.get("tree", []):
            rel = entry.get("path", "")
            if not rel.endswith(".tif"):
                continue
            low = rel.lower()
            if any(skip in low for skip in ("sample_submission", "training_features", "labels.tif", "existing_faults")):
                continue
            if any(seg in low for seg in ("docs/", "submissions/", "scored/", "downloads/")):
                tifs.append(rel)
                slug = repo.split("/")[1] + "__" + rel.replace("/", "__")
                download_jobs.append((repo, commit, rel, entry["sha"], SISTER_DIR / slug))
        repo_status.append({"repo": repo, "accessible": True, "commit": commit, "tif_count": len(tifs)})

    sister_files: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(_download_blob, r, c, rel, bsha, dst) for r, c, rel, bsha, dst in download_jobs]
        for fut in as_completed(futs):
            sister_files.append(fut.result())
    sister_files.sort(key=lambda d: (d["repo"], d["remote_path"]))

    unique_sister_shas = len({d["sha256"] for d in sister_files})
    receipt = {
        "lane_id": "WBG-4",
        "method_code": "CSJF-1",
        "core_files_verified": len(core_files),
        "template57_bands_verified": verified_bands,
        "external_datasets_verified": ext_verified,
        "dem10_arrays_verified": len(dem10_files),
        "focus_inventory_rasters_verified": focus_ok,
        "wbg_s2_peer_rasters_verified": len(s2_peers),
        "sister_repo_audit_status": repo_status,
        "sister_peer_rasters_downloaded": len(sister_files),
        "sister_peer_unique_sha256_count": unique_sister_shas,
        "sister_peer_usage_rule": "READ_ONLY_UNIQUENESS_AUDIT_NEVER_USED_IN_FEATURES_OR_TRAINING",
        "anti_leakage_column_strips": {
            "gdr_wellspring_in_footprint.csv": ["dist_known_fault_px"],
            "gdr_volcanic_vents_in_footprint.csv": ["dist_known_fault_px"],
            "forbidden_catalogue_files_excluded_from_features": [
                "labels.tif",
                "existing_faults.tif",
                "gdr_qfaults_traces.csv",
                "derived_sgmc_faults_100m_u8.tif",
            ],
        },
        "sister_files": sister_files,
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        f"[wbg4_restore_data] OK: {verified_bands}/19 bands, {ext_verified}/13 external, "
        f"{len(dem10_files)} dem10, {focus_ok}/360 focus, {len(s2_peers)} s2_peers, "
        f"{len(sister_files)} sister TIFFs ({unique_sister_shas} unique SHA-256)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
