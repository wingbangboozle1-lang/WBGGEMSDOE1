import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_review_is_fail_closed_and_records_no_new_score():
    card = json.loads((ROOT / "evidence/repo_review_20261031.json").read_text())
    report = (ROOT / "docs/repo-review-20261031.md").read_text()

    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["submission_slots_used"] == 0
    assert card["submission_name"] is None
    assert card["raster_sha256"] is None
    assert card["holdout_dti"] == {
        "evidence_class": "NOT RUN",
        "evaluator_version": None,
        "withheld_positives": None,
        "dti": None,
        "ci95": None,
    }

    overlap = card["correlation_overlap_vs_registry"]["inherited_candidate_literal_overlap"]
    assert overlap["limit"] == 0.7
    assert all(overlap[arm] > overlap["limit"] for arm in ("E1", "E2", "E3"))
    assert "repo-review-20261031.md" in (ROOT / "README.md").read_text()
    assert "repo-review-20261031.md" in (ROOT / "docs/index.html").read_text()
    inherited = card["separate_inherited_research_artifact"]
    assert inherited["registry_rasters_checked"] == 0
    assert inherited["uniqueness"] == "NOT ESTABLISHED"
    assert inherited["ok_to_submit"] is False
    assert "offcatalogue-stratified-40000dots-20261031T005856Z.tif" in report
    homepage = (ROOT / "docs/index.html").read_text()
    assert "DOWNLOAD: YES (research) · SUBMIT: NO" in homepage
    assert "zero registry rasters were checked" in homepage
    assert "outside-footprint cells instead of null/NaN" in homepage


def test_new_review_does_not_present_historical_scores_as_organizer_receipts():
    report = (ROOT / "docs/repo-review-20261031.md").read_text()
    assert "OWNER-REPORTED" in report
    assert "ORGANIZER-CONFIRMED" in report
    assert "leaderboard estimate" in report.lower()
    assert "UNAVAILABLE" in report
    assert "SUBMIT: NO" in report
    assert report.count("**NONE — no candidate cleared**") == 9
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert f"| {site} |" in report
