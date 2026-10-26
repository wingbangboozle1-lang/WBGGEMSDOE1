#!/usr/bin/env python3
"""Restore and verify the immutable nine-site novelty registry.

The source inventory pins repository commits (and SHA-256 where already known).
This script fetches blobs with Git, checks object identity and bytes, validates the
competition grid, deduplicates exact float32 footprint content, and writes the
canonical manifest consumed by ``gems.novelty.compare_registry``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "registry/source_registry.json"
OUTPUT = ROOT / "registry/registry.json"
CACHE = ROOT / "registry/cache"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    prefix = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(prefix + payload, usedforsecurity=False).hexdigest()


def run(*args: str, capture: bool = False) -> bytes:
    return subprocess.run(
        list(args), check=True, stdout=subprocess.PIPE if capture else None
    ).stdout


def ensure_repo(repo: str) -> Path:
    path = CACHE / "_git" / (repo.replace("/", "--") + ".git")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        run(
            "git",
            "clone",
            "--quiet",
            "--bare",
            "--filter=blob:none",
            f"https://github.com/{repo}.git",
            str(path),
        )
    return path


def ensure_commit(repo_path: Path, commit: str) -> None:
    check = subprocess.run(
        ["git", "-C", str(repo_path), "cat-file", "-e", f"{commit}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if check.returncode:
        run(
            "git",
            "-C",
            str(repo_path),
            "fetch",
            "--quiet",
            "--filter=blob:none",
            "origin",
            commit,
        )


def restore(force: bool = False) -> dict:
    sources = json.loads(SOURCES.read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    source_sha = sha256_file(SOURCES)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in sources["rows"]:
        grouped[row["repo"]].append(row)

    with rasterio.open(TEMPLATE) as template:
        footprint = np.isfinite(template.read(1))
        expected = (template.shape, template.crs, template.transform)

    candidates: list[dict] = []
    rejected: list[dict] = []
    for repo in sorted(grouped):
        repo_path = ensure_repo(repo)
        for commit in sorted({row["commit"] for row in grouped[repo]}):
            ensure_commit(repo_path, commit)
        for source in grouped[repo]:
            identity = f"{source['commit']}:{source['path']}"
            try:
                payload = run(
                    "git", "-C", str(repo_path), "show", identity, capture=True
                )
                actual_blob = git_blob_sha1(payload)
                expected_blob = source.get("git_blob_sha1")
                if expected_blob and actual_blob != expected_blob:
                    raise ValueError(
                        f"Git blob mismatch: expected {expected_blob}, got {actual_blob}"
                    )
                actual_sha = sha256_bytes(payload)
                if source.get("sha256") and actual_sha != source["sha256"]:
                    raise ValueError(
                        f"SHA-256 mismatch: expected {source['sha256']}, got {actual_sha}"
                    )
                if source.get("bytes") is not None and len(payload) != source["bytes"]:
                    raise ValueError(
                        f"byte-size mismatch: expected {source['bytes']}, got {len(payload)}"
                    )
                destination = CACHE / f"{actual_sha}.tif"
                if force or not destination.exists() or sha256_file(destination) != actual_sha:
                    destination.write_bytes(payload)
                with rasterio.open(destination) as dataset:
                    if (dataset.shape, dataset.crs, dataset.transform) != expected:
                        raise ValueError("competition-grid mismatch")
                    array = dataset.read(1)
                if not np.isfinite(array[footprint]).all():
                    raise ValueError("nonfinite value inside footprint")
                values = np.asarray(array[footprint], dtype="<f4")
                content = hashlib.sha256(values.tobytes()).hexdigest()
                expected_content = source.get("footprint_sha256")
                if expected_content and content != expected_content:
                    raise ValueError(
                        f"footprint checksum mismatch: expected {expected_content}, got {content}"
                    )
                binary = bool(np.isin(values, [0.0, 1.0]).all())
                comparison_dir = CACHE / "comparison"
                comparison_dir.mkdir(parents=True, exist_ok=True)
                comparison = comparison_dir / f"{content}-{'positive-positions' if binary else 'values'}.npy"
                if force or not comparison.exists():
                    np.save(
                        comparison,
                        np.flatnonzero(values > 0).astype(np.uint32)
                        if binary
                        else values,
                        allow_pickle=False,
                    )
                comparison_sha = sha256_file(comparison)
                candidates.append(
                    {
                        **source,
                        "sha256": actual_sha,
                        "git_blob_sha1": actual_blob,
                        "bytes": len(payload),
                        "footprint_sha256": content,
                        "positive_pixels": int(np.count_nonzero(values > 0)),
                        "cache_path": str(destination.relative_to(ROOT)),
                        "comparison_cache_path": str(comparison.relative_to(ROOT)),
                        "comparison_cache_sha256": comparison_sha,
                        "comparison_encoding": (
                            "uint32_footprint_positive_positions" if binary else "float32_footprint_values"
                        ),
                    }
                )
            except Exception as error:  # retain every irregularity rather than silently omit it
                rejected.append(
                    {
                        "repo": source["repo"],
                        "commit": source["commit"],
                        "path": source["path"],
                        "reason": f"{type(error).__name__}: {error}",
                    }
                )

    # Exact footprint-content deduplication. Prefer explicit calibration-control rows,
    # then already SHA-pinned rows, then stable lexical source identity.
    candidates.sort(
        key=lambda row: (
            row["source_set"] != "retained-literal-calibration-control",
            source_sha is None,
            row["repo"],
            row["commit"],
            row["path"],
        )
    )
    unique: dict[str, dict] = {}
    variants: list[dict] = []
    for row in candidates:
        content = row["footprint_sha256"]
        if content in unique:
            variants.append(
                {
                    "sha256": row["sha256"],
                    "repo": row["repo"],
                    "commit": row["commit"],
                    "file": row["path"],
                    "same_footprint_as": unique[content]["sha256"],
                }
            )
        else:
            unique[content] = row

    entries = []
    lattice_hash = sources["retained_spacing_5_lattice"]["footprint_sha256"]
    for index, row in enumerate(unique.values(), 1):
        entries.append(
            {
                "id": f"registry-{index:03d}",
                "repo": row["repo"],
                "ref": row["commit"],
                "file": row["path"],
                "source_url": row["source_url"],
                "sha256": row["sha256"],
                "git_blob_sha1": row["git_blob_sha1"],
                "bytes": row["bytes"],
                "cache_path": row["cache_path"],
                "comparison_cache_path": row["comparison_cache_path"],
                "comparison_cache_sha256": row["comparison_cache_sha256"],
                "comparison_encoding": row["comparison_encoding"],
                "footprint_sha256": row["footprint_sha256"],
                "positive_pixels": row["positive_pixels"],
                "comparator_role": (
                    "retained_spacing_5_calibration_control"
                    if row["footprint_sha256"] == lattice_hash
                    else "competing_published_raster"
                ),
            }
        )

    output = {
        "schema": "gemsdoe1-immutable-novelty-registry-v1",
        "source_manifest": str(SOURCES.relative_to(ROOT)),
        "source_manifest_sha256": source_sha,
        "scope": sources["scope"],
        "source_rows": len(sources["rows"]),
        "restored_rows": len(candidates),
        "unique_rasters": len(entries),
        "duplicate_content_variants": len(variants),
        "rejected_count": len(rejected),
        "retained_spacing_5_lattice_present": any(
            row["comparator_role"] == "retained_spacing_5_calibration_control"
            for row in entries
        ),
        "entries": entries,
        "variants": variants,
        "rejected": rejected,
    }
    OUTPUT.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rewrite cached blobs")
    args = parser.parse_args()
    result = restore(args.force)
    print(
        json.dumps(
            {key: result[key] for key in (
                "source_rows",
                "restored_rows",
                "unique_rasters",
                "duplicate_content_variants",
                "rejected_count",
                "retained_spacing_5_lattice_present",
            )},
            indent=2,
        )
    )
    if result["rejected_count"] or not result["retained_spacing_5_lattice_present"]:
        raise SystemExit("Registry restoration is incomplete; scientific run must fail closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
