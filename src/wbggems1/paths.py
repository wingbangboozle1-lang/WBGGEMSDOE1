"""Workspace and external scratch path resolution for WBGGEMSDOE1 (WBG-H1 / DPGF-1 lane).

Raw multi-hundred-MB rasters and memmap feature caches default to ``/tmp/gems_raw``
and ``/tmp/gems_work`` when present or requested via ``WBG_DATA_DIR`` / ``WBG_WORK_DIR``,
with automatic fallback to ``data/bridge`` for lightweight GeoTIFF format & collar
validation on CI runners.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return REPO_ROOT


def wbg_evidence_dir() -> Path:
    return REPO_ROOT / "evidence" / "wbg_h1"


def wbg_registry_dir() -> Path:
    return REPO_ROOT / "registry" / "wbg_h1"


def raw_data_dir() -> Path:
    env = os.environ.get("WBG_DATA_DIR")
    if env:
        return Path(env)
    tmp_default = Path("/tmp/gems_raw")
    local_default = REPO_ROOT / "data" / "raw"
    bridge_default = REPO_ROOT / "data" / "bridge"
    if (local_default / "training_features.tif").exists():
        return local_default
    if (tmp_default / "sample_submission.tif").exists():
        return tmp_default
    if (bridge_default / "sample_submission.tif").exists():
        return bridge_default
    return tmp_default


def work_dir() -> Path:
    env = os.environ.get("WBG_WORK_DIR")
    if env:
        return Path(env)
    tmp_work = Path("/tmp/gems_work")
    local_work = REPO_ROOT / "data" / "prepared"
    if (local_work / "base_features.npy").exists():
        return local_work
    return tmp_work


def registry_cache_dir() -> Path:
    env = os.environ.get("WBG_REGISTRY_DIR")
    if env:
        return Path(env)
    return raw_data_dir() / "registry_cache"
