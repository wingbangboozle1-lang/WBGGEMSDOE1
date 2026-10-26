"""Directory resolution. Env overrides: WBG1_ROOT, WBG1_DATA, WBG1_WORK."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("WBG1_ROOT", Path(__file__).resolve().parents[2]))


def root() -> Path:
    return ROOT


def data_dir() -> Path:
    return Path(os.environ.get("WBG1_DATA", str(ROOT / "data" / "raw")))


def registry_raster_dir() -> Path:
    d = ROOT / "data" / "registry"
    if not d.exists():
        alt = Path(os.environ.get("WBG1_DATA", str(ROOT / "data" / "raw")))
        if (alt / ".." / "registry").exists():
            return alt / ".." / "registry"
    return d


def work_dir() -> Path:
    d = Path(os.environ.get("WBG1_WORK", str(ROOT / "work")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def docs_dir() -> Path:
    return ROOT / "docs"


def downloads_dir() -> Path:
    d = ROOT / "docs" / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def registry_dir() -> Path:
    return ROOT / "registry"


def evidence_dir() -> Path:
    d = ROOT / "evidence"
    d.mkdir(parents=True, exist_ok=True)
    return d
