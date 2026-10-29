"""Regression checks for the 29 Oct 2026 candidate, its run card and its public pages.

Uses only committed artifacts (docs/ and evidence/), so it runs in CI without restored inputs.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
NAME = "wbggemsdoe1-tipgap2km-K12395-20261029"
CARD = ROOT / f"evidence/candidates/{NAME}.run_card.json"
HOLD = ROOT / f"evidence/candidates/{NAME}.holdout.json"
TIF = ROOT / f"docs/downloads/{NAME}.tif"
PAGE = ROOT / "docs/unique-lane-summary-20261029.html"


def test_run_card_verdict_is_download_yes_submit_no():
    card = json.loads(CARD.read_text())
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["gates"]["G1_format"] is True
    assert card["gates"]["G3_leakage_canary_detached"] is False
    assert card["leakage_canary"]["detached_max_auc"] > 0.90
    assert card["organizer_confirmed_score"] is None


def test_note_and_name_meet_portal_limits():
    card = json.loads(CARD.read_text())
    assert len(card["note"]) <= 140
    assert card["name"] == NAME


def test_holdout_receipt_is_not_claimable():
    hold = json.loads(HOLD.read_text())
    assert hold["valid_for_claims"] is False
    assert "leaked by construction" in hold["invalid_reason"]


def test_tif_is_float32_in_unit_interval_with_expected_dot_count():
    card = json.loads(CARD.read_text())
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        assert ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
    assert np.isfinite(a).all()
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0
    assert int((a > 0).sum()) == card["raster"]["dots"]


def test_run_card_hash_matches_tif():
    import hashlib

    card = json.loads(CARD.read_text())
    assert hashlib.sha256(TIF.read_bytes()).hexdigest() == card["raster"]["sha256"]


@pytest.mark.parametrize("needle", ["DOWNLOAD: YES", "SUBMIT: NO", "USER-REPORTED", "0.2778"])
def test_summary_page_states_verdicts_and_labels(needle):
    assert needle in PAGE.read_text()


def test_summary_page_never_labels_candidate_with_a_score():
    text = PAGE.read_text()
    assert "No estimate." in text
    assert "leaked by construction" in text
