"""Follow-up audit: exact bytes, frozen science, literal gates and honest pages."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    # Script imports share the same CLI module as normal execution.
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def receipt():
    return json.loads((ROOT / "evidence/release_review_20261027.json").read_text())


def test_exact_all_four_downloads_revalidate_and_no_lane_is_promoted():
    mod = module("review_releases")
    measured = mod.review()
    # JSON serialization normalizes tuples in unchanged validator reports.
    assert json.loads(json.dumps(measured)) == receipt()
    assert measured["new_experiments"] == measured["submission_slots_used"] == 0
    assert measured["all_exact_artifacts_format_valid"]
    assert not measured["any_ok_to_submit"]
    assert {r["lane"] for r in measured["rows"]} == {"WBG-C1", "TIP1", "MVGZ", "WBG-H1"}
    for row in measured["rows"]:
        assert row["ok_to_download"]
        assert not row["ok_to_submit"] and not row["uniqueness_cleared"]
        assert row["leaderboard_estimate"] is row["organizer_confirmed_score"] is None
        assert row["validator"]["n_nan"] == row["validator"]["n_infinite"] == 0
        assert row["validator"]["mirrored_reference_available"]
        assert row["validator"]["catalogue_reference_available"]
        assert len(row["holdout"]["ci95"]) == 2
        assert row["holdout"]["withheld_positive_pixels"] > 0
    assert "/home/user" not in json.dumps(measured)


@pytest.mark.parametrize("missing", ["mirrored_reference_available", "catalogue_reference_available"])
def test_missing_pinned_reference_cannot_keep_download_pass(monkeypatch, missing):
    mod = module("review_releases")
    row = receipt()["rows"][0]
    fake = copy.deepcopy(row["validator"])
    fake[missing] = False
    monkeypatch.setattr(mod, "specifications", lambda: mod_specs(row))
    monkeypatch.setattr(mod, "check_tiff", lambda path: fake)
    result = mod.review()
    assert not result["all_exact_artifacts_format_valid"]
    assert not result["rows"][0]["ok_to_download"]
    assert not result["rows"][0]["ok_to_submit"]


def mod_specs(row):
    return [(row["lane"], row["source_card"], row["artifact"], row["expected_raster_sha256"],
             row["holdout"], row["recorded_forward_3px_overlap"], row["registry_scope"], row["reason"])]


@pytest.mark.parametrize("failure", ["wrong_hash", "malformed"])
def test_changed_or_corrupt_tiff_fails_closed(monkeypatch, failure):
    mod = module("review_releases")
    row = receipt()["rows"][0]
    monkeypatch.setattr(mod, "specifications", lambda: mod_specs(row))
    def check(path):
        if failure == "malformed":
            raise ValueError("malformed TIFF")
        fake = copy.deepcopy(row["validator"])
        fake["sha256"] = "0" * 64
        return fake
    monkeypatch.setattr(mod, "check_tiff", check)
    report = mod.review()
    assert not report["all_exact_artifacts_format_valid"]
    assert not report["rows"][0]["exact_identity_matches"]
    assert not report["rows"][0]["ok_to_download"]
    assert not report["rows"][0]["ok_to_submit"]


def test_release_builder_rejects_stale_identity(monkeypatch):
    mod = module("build_release_review")
    monkeypatch.setattr(mod, "sha", lambda path: "0" * 64)
    with pytest.raises(ValueError, match="stale"):
        mod.build()


def test_check_mode_rejects_report_drift(tmp_path, monkeypatch):
    mod = module("review_releases")
    monkeypatch.setattr(mod, "review", receipt)
    monkeypatch.setattr(mod, "OUTPUT", tmp_path / "wrong.json")
    monkeypatch.setattr(sys, "argv", ["review_releases.py", "--check"])
    (tmp_path / "wrong.json").write_text("{}")
    with pytest.raises(SystemExit, match="differs"):
        mod.main()


def test_literal_witness_overrides_filtered_diagnostics_in_publication():
    rows = {r["lane"]: r for r in receipt()["rows"]}
    assert rows["WBG-H1"]["literal_overlap_exceeds_limit"]
    assert rows["TIP1"]["literal_overlap_exceeds_limit"]
    assert rows["WBG-C1"]["literal_overlap_exceeds_limit"]
    for page in ("index.html", "executive-summary.html"):
        text = (ROOT / "docs/wbg-h1-dpgf1" / page).read_text()
        assert "SUBMIT: NO" in text
        assert "Literal uniqueness: FAILED" in text
        assert "99.8035%" in text
        assert "USER-REPORTED / NOT ORGANIZER-CONFIRMED" in text
        assert "inferred_private_fault_pixels" not in text
        assert "--check-uniqueness" not in text  # old nonexistent CLI option
        assert "optional benchmark" in text  # explicitly do not upload
        assert "guarantees" not in text.lower()


def test_truth_credit_and_dot_credit_cannot_be_collapsed_for_score_inversion():
    # Mathematical synthetic fixture, not a geological experiment or HOLDOUT-DTI.
    # One prediction covers two adjacent truth cells. T > M even though N is fixed.
    from gems57.metric import dti_binary
    truth = np.zeros((15, 15), dtype=bool)
    truth[7, 7] = truth[7, 8] = True
    prediction = np.zeros_like(truth)
    prediction[7, 7] = True
    out = dti_binary(prediction, truth)
    assert out["tp"] == pytest.approx(1 + 2 / 3)
    m = 1 - out["fp"]
    assert m == pytest.approx(1)
    assert out["tp"] != pytest.approx(m)
    assert out["dti"] == pytest.approx(out["tp"] / (0.2 * (out["tp"] + 1 - m) + 0.8 * 2))
    # Same N,K; different truth geometry changes kernel-conditioned quantities.
    truth[7, 8] = False
    truth[12, 12] = True
    other = dti_binary(prediction, truth)
    assert out["n_truth"] == other["n_truth"]
    assert out["n_emitted"] == other["n_emitted"]
    assert out["dti"] != pytest.approx(other["dti"])


def test_review_card_retains_stopped_science_and_has_short_research_note():
    card = json.loads((ROOT / "evidence/review_run_card_20261027.json").read_text())
    old = json.loads((ROOT / "registry/run_card.json").read_text())
    assert card["new_experiments"] == card["new_tiffs_generated"] == card["submission_slots_used"] == 0
    assert card["raster_sha256"] == old["raster_sha256"]
    assert card["holdout"]["dti"] == old["holdout"]["dti"]
    assert card["holdout"]["ci95"] == old["holdout"]["ci95"]
    assert card["verdict"] == "negative" and not card["ok_to_submit"]
    assert len(card["submission_note"]) <= 140
    assert (ROOT / "docs/data/review-run-card.json").read_bytes() == (ROOT / "evidence/review_run_card_20261027.json").read_bytes()
