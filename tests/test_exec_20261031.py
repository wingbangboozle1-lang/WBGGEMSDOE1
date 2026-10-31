"""Tests for the 31 Oct 2026 decision artifacts (band-null candidate, audit, executive summary).

These check receipts against files on disk. They do not assert any leaderboard score.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DL = ROOT / "docs/downloads"
DATA = ROOT / "docs/data"
REF = ROOT / "data/bridge/sample_submission.tif"
CAT = ROOT / "data/bridge/labels.tif"
CARD = DATA / "band_null_run_card_20261031.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def card() -> dict:
    return json.loads(CARD.read_text())


def test_candidate_bytes_match_run_card(card):
    tif = ROOT / card["file"]
    assert tif.exists()
    assert _sha(tif) == card["sha256"]
    assert _sha(tif.with_suffix(".zip")) == card["zip_sha256"]


def test_candidate_is_single_band_float32_on_reference_grid(card):
    with rasterio.open(REF) as r:
        ref_shape, ref_tf, ref_crs = (r.height, r.width), tuple(r.transform), r.crs
        foot = np.isfinite(r.read(1))
    with rasterio.open(ROOT / card["file"]) as d:
        assert d.count == 1 and d.dtypes[0] == "float32"
        assert (d.height, d.width) == ref_shape
        assert tuple(d.transform) == ref_tf
        assert d.crs.to_epsg() == 32611 and d.crs == ref_crs
        a = d.read(1)
    assert np.isfinite(a[foot]).all(), "NaN/inf inside the footprint"
    assert ((a[foot] >= 0) & (a[foot] <= 1)).all(), "values outside [0,1] inside the footprint"
    assert (a[~foot] == 0).all(), "non-zero outside the footprint"


def test_candidate_dots_clear_the_catalogue(card):
    with rasterio.open(REF) as r:
        foot = np.isfinite(r.read(1))
    with rasterio.open(CAT) as c:
        cat = (c.read(1) > 0) & foot
    with rasterio.open(ROOT / card["file"]) as d:
        dots = d.read(1) > 0
    assert dots.sum() == card["construction"]["n_dots"] == 37654
    assert not (dots & cat).any()


def test_candidate_name_and_note_within_limit(card):
    assert 1 <= len(card["submission_name"]) <= 140
    assert 1 <= len(card["submission_note"]) <= 140
    assert len(card["submission_note"]) <= 140


def test_run_card_verdict_is_not_submit(card):
    assert card["submit"] == "NO"
    assert card["writer_receipt"]["submission_slots_used"] == 0
    assert card["writer_receipt"]["approved_for_weekly_slot"] is False


def test_summary_labels_and_no_scores(card):
    s = json.loads((DATA / "executive_summary_20261031.json").read_text())
    rows = s["nine_site_rows"]
    assert [r["site"] for r in rows].count("GEMSDOE32") == 1
    assert len(rows) == 10  # nine sites, GEMSDOE24 contributes two headline rows
    for r in rows:
        assert r["reported_score_label"].startswith("OWNER-REPORTED")
        assert r["estimated_score"].startswith("UNAVAILABLE")
        assert r["proxy_dti_label"].startswith("PROXY-DTI")
        assert r["verdict_submit"].startswith("SUBMIT: NO")
    assert s["headline"]["submit"] == "SUBMIT: NO"
    assert s["headline"]["download"].startswith("DOWNLOAD: YES")


def test_exec_page_shows_both_verdicts():
    page = (ROOT / "docs/executive-summary-20261031.html").read_text()
    assert "Download: YES - research file only" in page
    assert "Submit: NO - not cleared" in page
    assert "Estimated leaderboard score: UNAVAILABLE" in page


def test_b2_is_exact_subset_of_parent_per_audit():
    audit = json.loads((DATA / "focus_proxy_audit_20261031.json").read_text())
    m = audit["mechanism_test_b2_vs_parent"]
    assert m["b2_is_subset_of_parent"] is True
    assert m["parent_dots"] == 44090 and m["b2_dots"] == 37654 and m["removed_dots"] == 6436
    assert m["removed_dist_to_catalogue_px_max"] <= 2.0


def test_reported_match_count_matches_registry():
    audit = json.loads((DATA / "focus_proxy_audit_20261031.json").read_text())
    reg = json.loads((ROOT / "registry/focus_user_reported_scores.json").read_text())["entries"]
    assert len(audit["matched_reported_files"]) == len(reg) == 21
    assert all(r.get("status") == "OK" for r in audit["matched_reported_files"])


def test_headline_hashes_match_archives():
    man = json.loads((DATA / "focus_codeload_manifest_20261031.json").read_text())
    assert all(h["registry_sha256_matches_archive"] for h in man["headline_checks"])
