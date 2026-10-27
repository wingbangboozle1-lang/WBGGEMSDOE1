"""Verification receipts for the 2026-10-27 TASC lane and decision pages."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def load(rel):
    return json.loads((ROOT / rel).read_text())


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def test_tasc_preregistration_and_feature_canary():
    prereg = load("registry/preregistration_tasc_20261027.json")
    features = load("evidence/tasc_features_20261027.json")
    canary = load("evidence/tasc_canary_20261027.json")
    assert prereg["hypothesis_id"] == "TASC"
    assert prereg["budget"]["maximum_experiments"] == 3
    assert prereg["gates"]["weekly_slots_authorized"] == 0
    assert features["preregistration_sha256"] == sha256(ROOT / "registry/preregistration_tasc_20261027.json")
    assert canary["passed"] is True
    assert len(canary["features"]) == 13
    assert max(max(r["auc"], 1 - r["auc"]) for v in canary["features"].values()
               for r in v["folds"]) <= 0.90
    for fold in features["fold_receipts"]:
        assert fold["catalogue_derived_from_visible_only"] is True
        assert fold["skeleton_intersects_hidden_components"] is False


def test_tasc_run_cards_are_negative_and_tiffs_match():
    cards = [
        load("evidence/tasc_run_card_20261027.json"),
        load("evidence/tasc_best_arm_run_card_20261027.json"),
    ]
    assert cards[0]["experiments_completed"] == 3
    assert cards[0]["submission_slots_used"] == 0
    for card in cards:
        assert card["verdict"] == "negative"
        assert card["decision"]["ok_to_download"] is True
        assert card["decision"]["ok_to_submit"] is False
        assert card["decision"]["submission_slots_used"] == 0
        assert len(card["submission_note"]) <= 140
        assert card["raster_sha256"] == sha256(ROOT / card["artifact"])
        assert card["validator_output"]["format_valid"] is True
        assert card["validator_output"]["checks"][
            "variant_strict_whole_array_no_nan_allowed"]["pass"] is True
        with rasterio.open(ROOT / card["artifact"]) as ds:
            arr = ds.read(1)
            assert ds.count == 1 and ds.dtypes == ("float32",)
            assert ds.crs.to_epsg() == 32611
            assert (ds.height, ds.width) == (3730, 3292)
            assert tuple(ds.transform)[:6] == (100, 0, 243350, 0, -100, 4508550)
        assert np.isfinite(arr).all()
        assert arr.min() >= 0.0 and arr.max() <= 1.0
        assert set(np.unique(arr).tolist()).issubset({0.0, 1.0})
    assert cards[0]["holdout"]["B"]["dti"] < cards[1]["holdout"]["dti"]
    assert cards[0]["correlation_overlap_vs_registry"]["final_dots_literal_unseparated_passed"] is False
    assert cards[1]["correlation_overlap_vs_registry"]["final_dots_literal_unseparated_passed"] is False
    assert cards[1]["correlation_overlap_vs_registry"]["final_dots_competing_method_passed"] is True


def test_current_decision_payload_and_estimate_governance():
    d = load("docs/data/current_decision_20261027.json")
    assert len(d["sites"]) == 9
    assert len(d["new_files"]) == 3
    assert d["decision"]["status"] == "NEGATIVE"
    assert d["decision"]["submit"].startswith("NO")
    assert d["decision"]["slots_used"] == 0
    assert "LLI-PROJECTION" in d["decision"]["best_estimate_label"]
    assert d["target_context"]["observed_official_leaderboard"] == 0.4544
    for s in d["sites"]:
        assert s["historical_value_label"] == "USER-REPORTED / NOT ORGANIZER-CONFIRMED"
        assert s["estimate_label"] == "LLI-PROJECTION (NOT a score)"
        assert s["ok_to_submit"] is False
    for f in d["new_files"]:
        assert f["ok_to_submit"] is False
        assert f["literal_gate_passed"] is False
        assert (ROOT / "docs/downloads" / f["file"]).is_file()


def test_inherited_mislabeling_corrected():
    for rel in [
        "evidence/wbg_h1/focus9_executive_audit.json",
        "evidence/wbg_h1/run_card.json",
        "docs/wbg-h1-dpgf1/data/site_payload.json",
        "docs/wbg-h1-dpgf1/index.html",
    ]:
        text = (ROOT / rel).read_text()
        assert "n=118 ORGANIZER-CONFIRMED rasters" not in text
        assert '"label": "ORGANIZER-CONFIRMED (owner-reported receipt)"' not in text
    assert "USER-REPORTED / NOT ORGANIZER-CONFIRMED" in (ROOT / "src/wbggems1/forensics.py").read_text()


def test_feed_observation_and_irregularities():
    feed = load("docs/data/feed.json")
    issues = load("registry/irregularities.json")
    assert feed["leaderboard"]["public_dw_tversky"] == 0.4544
    assert feed["leaderboard"]["observed_date_utc"] == "2026-10-27"
    ids = {i["id"] for i in issues["items"]}
    assert {"IR-020", "IR-021", "IR-022", "IR-023", "IR-024"}.issubset(ids)


def test_submission_decision_page_links_and_status():
    page = (ROOT / "docs/submission-decision.html").read_text().lower()
    assert "download: yes" in page
    assert "submit: no" in page
    assert "do not submit" in page
    assert "no final dots" in page
    assert "no competition slot" in page
    assert "0.4544" in page
    assert "data/ranked-hypotheses-20261027.md" in page
    assert "data/next-steps-20261027.md" in page
    assert (ROOT / "docs/data/ranked-hypotheses-20261027.md").is_file()
    assert (ROOT / "docs/data/next-steps-20261027.md").is_file()
