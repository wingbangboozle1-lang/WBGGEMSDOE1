#!/usr/bin/env python3
"""Restore and SHA-256-verify all external datasets, 10 m 3DEP channels, and peer rasters for WBG-S2.

Writes only to git-ignored `data/`, `.cache/research/`, and `evidence/wbg_s2/data_restore_receipt.json`.
Never modifies frozen receipts in `evidence/` or `evidence/wbg_h1/`.
"""
from __future__ import annotations

import concurrent.futures
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wbggems.audit import dump_json, sha256, utc_now

DEM10_REPO = "buffedlizard55-lab/GEMSDOE10"
DEM10_REF = "91d6566ecc86141eca9e81c259057678930e596f"
DEM10_CHANNELS: dict[str, str] = {
    "dem10_slope_max": "fd46738e9a58a6f40c130c3c70f645525dbfc12d27b6ed149e596e6a379cbfaa",
    "dem10_slope_mean": "338b443c441db61120faf36437ec61dfcccaa569c41aa3099ed3accef5a35f95",
    "dem10_slope_std": "9c15e0e760d8255eb0473821a07cc09e4fe4b40746e6e37278e69c7f615c0f642",
    "dem10_hgm20_max": "f58df86b0be3b3dc54affc60dc7d77a95db3dafb9c1267eac4912c5d8e57526b",
    "dem10_hgm50_max": "1cca42538ec0c91951b578136893eb5d90cd1414c45257d2a72ebe80b29f0f40",
    "dem10_hgm200_mean": "9328f889f4d607f8530840da138741b7431da49d2432b0ab2da110a82984102b",
    "dem10_steep_ratio_max": "eaf3d5e24c6769ffb98665e75c9665dbaa16bdb79708900217dca955031e6828",
    "dem10_resid_std": "50db8caa815cb09cc695ec230f15f41e8e04cd9bef5fc09b07b06aeadd44a86e",
    "dem10_resid_range": "bbcf8a462ace31a80964ba8a7ab76fcbcb347deb4f4d2919166b3eda5c721b0c",
    "dem10_curv_absmax": "58e82f1301032b46b10344b9299b83e6ce5bed1ca83e320f078fa57321bff632",
    "dem10_onesided": "02d1d241de9534d307f314d0b2f8a857ceb1ce0d099fd7dee8872a83bd0271f8",
    "dem10_onesided3": "bca9faf8e0c572ecb1e77b6c94b0cb96c41e824873cb7747e0ece28b531598d2",
    "dem10_valid_frac": "35d7ef0719bfed93f9aed927afd8c51882283fc7316cab0f8c219c9302b92122",
}

EXTRA_EXTERNAL: list[dict[str, Any]] = [
    {
        "id": "ext_tiger_road_distance_m",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "ref": "9da8a18381e179530c3b878d073314feaa26a20c",
        "path": "data/external/audit_sources/tiger_road_distance_m.tif",
        "dest": "external/tiger_road_distance_m.tif",
        "sha256": "e5350423508968fa2d32b0a6ae0d3fb4ae3ea645e3b8736f0c8e7ad9ff2f2988",
        "bytes": 10492276,
    },
    {
        "id": "ext_lidar_scarp_meta",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "ref": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "path": "data/external/lidar_scarp_features.json",
        "dest": "external/lidar_scarp_features.json",
        "sha256": None,
        "bytes": 3531,
    },
    {
        "id": "ext_geodawn_rad_meta",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "ref": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "path": "data/external/geodawn_rad.json",
        "dest": "external/geodawn_rad.json",
        "sha256": None,
        "bytes": 7985,
    },
    {
        "id": "ext_geodawn_ext_meta",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "ref": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "path": "data/external/geodawn_extensions.json",
        "dest": "external/geodawn_extensions.json",
        "sha256": None,
        "bytes": 8927,
    },
]

LATEST_PEER_SUBMISSIONS: list[dict[str, str]] = [
    {
        "site": "GEMSDOE24",
        "label": "GEMSDOE24_S3DEP1",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "ref": "2521cb676e17",
        "path": "docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif",
    },
    {
        "site": "GEMSDOE24",
        "label": "GEMSDOE24_DPRF1",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "ref": "2521cb676e17",
        "path": "docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
    },
    {
        "site": "GEMSDOE25",
        "label": "GEMSDOE25_H74_SUBSURF",
        "repo": "buffedlizard55-lab/GEMSDOE25",
        "ref": "5a60fb475b71",
        "path": "docs/downloads/gems25-h74-rmps-subsurf-catfree-b2-37654-20261026-3751606e1ce5-zeros.tif",
    },
    {
        "site": "GEMSDOE25",
        "label": "GEMSDOE25_H73_PM",
        "repo": "buffedlizard55-lab/GEMSDOE25",
        "ref": "5a60fb475b71",
        "path": "docs/downloads/gems25-h73-pm-deapron-sapd2-8-k3p0-20261026-1b7533ebb62b-zeros.tif",
    },
    {
        "site": "GEMSDOE27",
        "label": "GEMSDOE27_H31_1_DRCG_WL",
        "repo": "buffedlizard55-lab/GEMSDOE27",
        "ref": "69d6f0337581",
        "path": "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
    },
    {
        "site": "GEMSDOE28",
        "label": "GEMSDOE28_S21_PUHGB",
        "repo": "buffedlizard55-lab/GEMSDOE28",
        "ref": "67dbdf4da84f",
        "path": "docs/downloads/gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite.tif",
    },
    {
        "site": "GEMSDOE30",
        "label": "GEMSDOE30_CSR1",
        "repo": "buffedlizard55-lab/GEMSDOE30",
        "ref": "3c3d7255fdbb",
        "path": "docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif",
    },
    {
        "site": "GEMSDOE31",
        "label": "GEMSDOE31_H31X_JUNCTION",
        "repo": "buffedlizard55-lab/GEMSDOE31",
        "ref": "fbebc01703a3",
        "path": "docs/downloads/gemsdoe31-h31x-piedmont-junction-37654-20261026-5a956da9-zeros.tif",
    },
    {
        "site": "GEMSDOE31",
        "label": "GEMSDOE31_H31YM_MOSAIC",
        "repo": "buffedlizard55-lab/GEMSDOE31",
        "ref": "fbebc01703a3",
        "path": "docs/downloads/gemsdoe31-h31y-regime-mosaic-37654-20261026-66162f1f-zeros.tif",
    },
    {
        "site": "GEMSDOE32",
        "label": "GEMSDOE32_H47_LDGI",
        "repo": "buffedlizard55-lab/GEMSDOE32",
        "ref": "1398109a23f0",
        "path": "docs/downloads/gemsdoe32-h47-ldgi-dualhorizon-corridor-37654-20261026T230609Z-0eb8a25c-zeros.tif",
    },
    {
        "site": "GEMSDOE32",
        "label": "GEMSDOE32_H33_B2_HIST",
        "repo": "buffedlizard55-lab/GEMSDOE32",
        "ref": "1398109a23f0",
        "path": "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
    },
    {
        "site": "GEMSDOE33",
        "label": "GEMSDOE33_S33_SEISDIL",
        "repo": "buffedlizard55-lab/GEMSDOE33",
        "ref": "122e2240a835",
        "path": "docs/downloads/gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros.tif",
    },
    {
        "site": "GEMSDOE33",
        "label": "GEMSDOE33_G33_COHERENCE",
        "repo": "buffedlizard55-lab/GEMSDOE33",
        "ref": "122e2240a835",
        "path": "docs/downloads/gemsdoe33-g33-tilt-gravity-lidar-coherence-20261026-171b8b87dbf7-zeros.tif",
    },
    {
        "site": "GEMSDOE36",
        "label": "GEMSDOE36_KPL36_EXP3",
        "repo": "buffedlizard55-lab/GEMSDOE36",
        "ref": "757694235238",
        "path": "docs/downloads/gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif",
    },
    {
        "site": "KANLERGEMSDOE2",
        "label": "KANLERGEMSDOE2_KG2_MGHV",
        "repo": "kanlerxz87-cyber/KANLERGEMSDOE2",
        "ref": "4edc3346c394c54638f8635e3265870f010668cc",
        "path": "docs/downloads/kanlergemsdoe2-kg2-mghv-exp-1-37654-20261026-f5a469e94b14-zeros.tif",
    },
]


def _download_github_raw(repo: str, ref: str, rel_path: str, dest: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        actual = sha256(dest)
        if expected_sha256 is None or actual == expected_sha256:
            return {"dest": str(dest.relative_to(ROOT)), "status": "cached", "sha256": actual, "bytes": dest.stat().st_size}
    tmp = dest.with_suffix(dest.suffix + ".partial")
    endpoint = f"repos/{repo}/contents/{rel_path}?ref={ref}"
    try:
        if shutil.which("gh"):
            with tmp.open("wb") as out:
                subprocess.run(
                    ["gh", "api", endpoint, "-H", "Accept: application/vnd.github.raw"],
                    stdout=out,
                    check=True,
                )
        else:
            url = f"https://raw.githubusercontent.com/{repo}/{ref}/{rel_path}"
            req = urllib.request.Request(url, headers={"User-Agent": "wbggemsdoe1-s2-restore/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp, tmp.open("wb") as out:
                shutil.copyfileobj(resp, out)
        actual = sha256(tmp)
        if expected_sha256 is not None and actual != expected_sha256:
            raise ValueError(f"SHA-256 mismatch for {endpoint}: expected {expected_sha256}, got {actual}")
        tmp.replace(dest)
        return {"dest": str(dest.relative_to(ROOT)), "status": "downloaded", "sha256": actual, "bytes": dest.stat().st_size}
    finally:
        tmp.unlink(missing_ok=True)


def _restore_snapshot_tarball(row: dict[str, str]) -> dict[str, Any]:
    repo = row["repo"]
    ref = row["ref"]
    cache = ROOT / ".cache" / "research"
    destination = cache / repo.split("/")[1]
    marker = destination / ".snapshot-pin"
    if marker.exists() and marker.read_text().strip() == ref:
        return {"repo": repo, "ref": ref, "status": "reused"}
    archive = cache / (repo.split("/")[1] + ".tar.gz")
    temporary = archive.with_suffix(".partial")
    cache.mkdir(parents=True, exist_ok=True)
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
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


def main() -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verify core competition files already restored in data/
    core_manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    core_results = []
    for entry in core_manifest["files"]:
        if entry.get("group", "core") != "core":
            continue
        p = data_dir / entry["dest"]
        if not p.exists():
            raise FileNotFoundError(f"Missing {p}; run scripts/download_competition_data.sh first.")
        actual = sha256(p)
        if actual != entry["sha256"]:
            raise ValueError(f"Core hash mismatch on {p}: {actual} != {entry['sha256']}")
        core_results.append({"id": entry["id"], "dest": entry["dest"], "sha256": actual, "bytes": p.stat().st_size})
    print(f"[1/4] Verified {len(core_results)} core competition rasters in data/.")

    # 2. Download external datasets (3DEP 1m LiDAR, GeoDAWN, SGMC, GDR 1391, TIGER 2024)
    h1_manifest = json.loads((ROOT / "registry" / "wbg_h1" / "data_manifest.json").read_text())
    ext_jobs = [e for e in h1_manifest["files"] if e["group"] == "external"] + EXTRA_EXTERNAL
    ext_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futs = [
            ex.submit(
                _download_github_raw,
                e["repo"],
                e["ref"],
                e["path"],
                data_dir / e["dest"],
                e.get("sha256"),
            )
            for e in ext_jobs
        ]
        for fut in concurrent.futures.as_completed(futs):
            res = fut.result()
            ext_results.append(res)
            print(f"  [{res['status']:>10}] {res['dest']:48s} ({res['bytes']:,} B)")
    print(f"[2/4] Verified {len(ext_results)} external official-source rasters/tables.")

    # 3. Download seamless 10 m USGS 3DEP channels from GEMSDOE10 (verified against pinned manifest.json)
    dem10_dir = data_dir / "dem10"
    manifest_res = _download_github_raw(
        DEM10_REPO,
        DEM10_REF,
        "manifest.json",
        dem10_dir / "manifest.json",
        None,
    )
    dem10_manifest = json.loads((dem10_dir / "manifest.json").read_text())
    dem10_results = [manifest_res]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futs = [
            ex.submit(
                _download_github_raw,
                DEM10_REPO,
                DEM10_REF,
                f"{ch}.f32.npy",
                dem10_dir / f"{ch}.f32.npy",
                dem10_manifest["channel_stats"][ch]["sha256"],
            )
            for ch in dem10_manifest["channels"]
        ]
        for fut in concurrent.futures.as_completed(futs):
            res = fut.result()
            dem10_results.append(res)
            print(f"  [{res['status']:>10}] {res['dest']:48s} ({res['bytes']:,} B)")
    print(f"[3/4] Verified {len(dem10_results)} seamless 10 m USGS 3DEP files.")

    # 4. Restore 9-snapshot frozen registry cache (.cache/research) + latest 2026-10-27 focus-9 & peer candidates
    pins = json.loads((ROOT / "registry" / "repository_snapshots.json").read_text())["repositories"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        snap_results = list(ex.map(_restore_snapshot_tarball, pins))

    peer_dir = data_dir / "wbg_s2_peers"
    peer_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futs = [
            ex.submit(
                _download_github_raw,
                p["repo"],
                p["ref"],
                p["path"],
                peer_dir / f"{p['label']}__{Path(p['path']).name}",
                None,
            )
            for p in LATEST_PEER_SUBMISSIONS
        ]
        for fut in concurrent.futures.as_completed(futs):
            peer_results.append(fut.result())
    print(f"[4/4] Restored {len(snap_results)} frozen 9-site snapshots and {len(peer_results)} latest 2026-10-27 peer TIFFs.")

    receipt = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "core_files": sorted(core_results, key=lambda x: x["dest"]),
        "external_files": sorted(ext_results, key=lambda x: x["dest"]),
        "dem10_files": sorted(dem10_results, key=lambda x: x["dest"]),
        "frozen_snapshot_repos": snap_results,
        "latest_peer_files": sorted(peer_results, key=lambda x: x["dest"]),
    }
    dump_json(ROOT / "evidence" / "wbg_s2" / "data_restore_receipt.json", receipt)
    print("Wrote evidence/wbg_s2/data_restore_receipt.json")


if __name__ == "__main__":
    main()
