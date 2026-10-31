"""WBG-8 deliverable consistency tests (31 Oct 2026).

These tests pin the automated-validation contract the owner asked for: the
delivered TIFF is format-valid, values in [0,1] with no NaN, unique against the
recorded registry audit, honestly labelled, and the executive pages resolve.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence" / "wbg8"
DOCS = ROOT / "docs"


def load(path):
    return json.loads(Path(path).read_text())


@pytest.fixture(scope="module")
def card():
    return load(EVID / "run_card.json")


@pytest.fixture(scope="module")
def candidate(card):
    name = card["submission_name"]
    return DOCS / "downloads" / f"{name}.tif"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_candidate_tif_matches_run_card_and_is_submittable_format(card, candidate):
    assert candidate.is_file()
    assert sha256_file(candidate) == card["raster_sha256"]
    with rasterio.open(candidate) as ds:
        a = ds.read(1)
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert list(tuple(ds.transform)[:6]) == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
    assert np.isfinite(a).all(), "NaN anywhere trips the portal's [0,1] check"
    assert a.min() >= 0.0 and a.max() <= 1.0
    assert card["validator"]["all_checks_passed"] is True
    assert card["validator"]["checks"]["outside_footprint_zero"] is True
    assert card["validator"]["checks"]["zero_dots_on_mapped_catalogue"] is True


def test_zip_bundle_exists_and_note_within_limit(card):
    zip_path = DOCS / "downloads" / f"{card['submission_name']}.zip"
    assert zip_path.is_file()
    assert len(card["submission_note"]) <= 140
    assert card["submission_name"] and card["submission_note"].strip()


def test_run_card_labels_and_verdict_are_honest(card):
    assert card["verdict"] in {"promote", "promote_with_reported_literal_degeneracy"}
    assert card["decision"]["download"] == "YES"
    assert card["decision"]["submit"].startswith("OK")
    est = card["estimated_leaderboard_score"]
    assert "MODEL-ESTIMATE" in est["strict_label"]
    assert "ORGANIZER-CONFIRMED" in est["strict_label"]  # explicitly says it is not one
    hold = card["holdout"]
    assert hold["evidence_class"] == "HOLDOUT-DTI"
    assert hold["evaluator_version"] == "gems57-pooled-hide-v2"
    cand = hold["candidate"]
    assert cand["ci95"][0] <= cand["dti"] <= cand["ci95"][1]
    paired = hold["paired_difference"]["control_poisson_same_mask"]
    assert paired["ci95"][0] > 0, "efficacy vs random control must exclude zero"
    assert card["proxy_dti"]["evidence_class"].startswith("PROXY-DTI")


def test_uniqueness_receipt_is_complete_and_failures_are_reported(card):
    uniq = load(EVID / "uniqueness_audit.json")
    assert uniq["byte_unique"] and uniq["pixel_unique"]
    assert uniq["registry_rasters_compared"] >= 400
    assert uniq["max_spearman_sample"]["value"] < 0.90
    assert card["gates"]["G2_exact_copy"] and card["gates"]["G3_rank_correlation"]
    # Every literal-gate failure must be listed with its degeneracy assessment.
    failures = [r for r in uniq["rows"] if r["literal_overlap_fail"]]
    diag = card["correlation_overlap_vs_registry"]["literal_failures_with_diagnostics"]
    assert len(diag) == len(failures) >= 1
    assert all(r["dense_registry_dots_gt_3x_mine"] for r in failures)
    assert all(r["lift"] <= 1.5 for r in diag)
    assert card["gates"]["G4_literal_overlap"] is False  # never silently relabelled
    assert card["gates"]["G4prime_density_matched_drift"] is True


def test_focus_champion_overlaps_show_no_lane_drift(card):
    overlaps = card["correlation_overlap_vs_registry"]["focus_champion_overlaps"]
    assert len(overlaps) >= 11
    assert max(overlaps.values()) < 0.70


def test_leakage_canary_and_channels_recorded():
    exp1 = load(EVID / "exp1_channel_screens.json")
    for name, cfg in exp1["configs"].items():
        assert cfg["canary_auc"] <= 0.90, name
        assert cfg["canary_pass"], name
    assert exp1["selection"]["dropped_canary_failures"] == []


def test_estimate_methods_are_labelled_projections():
    est = load(EVID / "score_estimate.json")
    assert est["label"].startswith("MODEL-ESTIMATE")
    for key in ("method_a_family_band", "method_b_pruning_delta",
                "method_c_proxy_calibrated", "method_d_frac3_mechanism"):
        assert key in est
    assert est["recommended_table_entry"]["strict_label"].startswith("MODEL-ESTIMATE")
    cal = load(EVID / "proxy_calibration.json")
    assert cal["n"] >= 10
    for row in cal["rows"]:
        assert row["score_owner_reported"] <= 1.0


def test_exec_summary_and_howto_pages_resolve_and_state_the_verdict():
    for name in ("executive-summary-20261031.html", "how-to-submit-20261031.html"):
        text = (DOCS / name).read_text()
        assert "<html lang=\"en\">" in text
        assert "DOWNLOAD: YES" in text and "SUBMIT: OK" in text
        assert "MODEL-ESTIMATE" in text
        assert "assets/style.css" in text
        for href in re.findall(r'href="([^"#]+)"', text):
            if href.startswith("http") or href.startswith("mailto"):
                continue
            target = (DOCS / name).parent / href
            assert target.resolve().exists(), (name, href)


def test_index_banner_points_at_the_new_candidate():
    card = load(EVID / "run_card.json")
    text = (DOCS / "index.html").read_text()
    assert "31 OCT 2026 · WBG-8 SUBMISSION CANDIDATE" in text
    assert f"downloads/{card['submission_name']}.tif" in text
    assert "executive-summary-20261031.html" in text
    assert "how-to-submit-20261031.html" in text


def test_preregistration_exists_and_fixes_the_budget():
    text = (ROOT / "research" / "07_wbg8_preregistration_20261031.md").read_text()
    assert "EXP1" in text and "EXP2" in text and "EXP3" in text
    assert "K_GRID" in text or "K = 37,654" in text
    assert "PROXY-DTI" in text and "HOLDOUT-DTI" in text
