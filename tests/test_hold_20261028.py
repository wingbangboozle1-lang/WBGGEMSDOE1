"""Regression tests for the 28 Oct 2026 WBG-6 HOLD decision.

These pin the measured facts so a rebuild cannot silently re-advertise a file as cleared.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
NAN_TIF = ROOT / "docs/downloads/wbg6-qmh-kdisjoint-30000-20261028-nan.tif"
NAN_ZIP = ROOT / "docs/downloads/wbg6-qmh-kdisjoint-30000-20261028-nan.zip"
NAN_RECEIPT = ROOT / "docs/downloads/wbg6-qmh-kdisjoint-30000-20261028-nan.validator.json"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"
GATE = ROOT / "evidence/literal_gate_degeneracy_20261028.json"
NINE = ROOT / "evidence/nine_sites_bytes_20261028.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_nan_variant_matches_official_footprint_and_receipt():
    receipt = json.loads(NAN_RECEIPT.read_text())
    assert receipt["all_checks_pass"] is True
    assert _sha(NAN_TIF) == receipt["tif_sha256"]
    assert _sha(NAN_ZIP) == receipt["zip_sha256"]
    with rasterio.open(SAMPLE) as s:
        footprint = np.isfinite(s.read(1))
    with rasterio.open(NAN_TIF) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert ds.crs.to_epsg() == 32611 and ds.shape == (3730, 3292)
    assert np.array_equal(np.isnan(a), ~footprint), "NaN mask must equal the sample footprint"
    inside = a[footprint]
    assert np.isfinite(inside).all()
    assert ((inside >= 0) & (inside <= 1)).all()
    assert int((inside > 0).sum()) == receipt["positives"] == 30000


def test_nan_variant_zip_has_exactly_one_identical_member():
    with zipfile.ZipFile(NAN_ZIP) as z:
        assert z.namelist() == [NAN_TIF.name]
        assert z.read(NAN_TIF.name) == NAN_TIF.read_bytes()


def test_literal_gate_is_degenerate_for_random_in_footprint_dots():
    gate = json.loads(GATE.read_text())
    assert gate["wbg6_forward3px_vs_r13"] > 0.70
    assert gate["random_in_footprint_dots_forward3px_vs_r13"]["min"] > 0.70, (
        "if random in-footprint dots ever fall below 0.70 the gate is no longer degenerate; re-audit WBG-6"
    )


def test_nine_site_receipt_labels_scores_as_user_reported():
    nine = json.loads(NINE.read_text())
    rows = [f for f in nine["files"] if "file" in f]
    assert len(rows) == 10
    assert all(f["label"].startswith("USER-REPORTED") for f in rows)
    assert all(f["footprint_matches_sample"] or f["outside_footprint_all_zero"] for f in rows)
    assert all(set(f["unique_values"]) <= {0.0, 1.0} for f in rows)
    assert "within3px_of_catalogue" in nine["wbg6"] and nine["wbg6"]["dots"] == 30000


def test_agents_md_has_no_merge_conflict_markers():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for marker in ("<<<<<<<", "\n=======\n", ">>>>>>>"):
        assert marker not in text


@pytest.mark.parametrize("path", ["README.md", "docs/index.html", "docs/wbg6/index.html",
                                  "docs/wbg6/how-to-submit.html", "PROMPT.md"])
def test_no_page_advertises_wbg6_as_cleared(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    for bad in ("DOWNLOAD & SUBMIT: YES", "DOWNLOAD: YES · SUBMIT: YES", "APPROVED TO SUBMIT",
                "the one file cleared to submit"):
        assert bad not in text, f"{path} still contains {bad!r}"


def test_hold_is_visible_on_homepage_and_readme():
    assert "HOLD" in (ROOT / "docs/index.html").read_text(encoding="utf-8")
    assert "HOLD" in (ROOT / "README.md").read_text(encoding="utf-8")[:1500]
