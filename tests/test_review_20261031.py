import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def test_current_review_is_linked_from_readme_and_site():
    readme = (ROOT / "README.md").read_text()
    site = (ROOT / "docs/index.html").read_text()
    assert "docs/repo-review-20261031.md" in readme
    assert "evidence/repo_review_20261031.json" in readme
    assert "repo-review-20261031.md" in site
    assert "SUBMIT: NO" in readme


def test_review_status_matches_frozen_run_card_and_artifact_bytes():
    review = load("evidence/repo_review_20261031.json")
    card = load("registry/run_card.json")
    artifact = ROOT / card["artifact"]
    actual = hashlib.file_digest(artifact.open("rb"), "sha256").hexdigest()

    assert review["verdict"] == "negative"
    assert review["new_rasters_this_review"] == 0
    assert review["submission_slots_used"] == 0
    assert review["current_research_artifact"]["sha256"] == actual == card["raster_sha256"]
    assert review["current_research_artifact"]["submit"] is False
    assert review["current_research_artifact"]["holdout_dti"]["value"] == card["holdout"]["dti"]
    assert review["current_research_artifact"]["holdout_dti"]["ci95"] == card["holdout"]["ci95"]


def test_focus9_historical_claims_are_all_unverified_and_no_go():
    summary = load("docs/data/nine_site_executive_summary.json")
    sites = summary["sites"]
    expected = {
        "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
    }
    focus_rows = [row for row in sites if row["site"] in expected]
    assert {row["site"] for row in focus_rows} == expected
    assert len(focus_rows) == 9
    assert all(row["score_evidence_label"] == "OWNER-REPORTED / UNVERIFIED" for row in focus_rows)
    assert all(row["organizer_receipt_present"] is False for row in focus_rows)
    assert all(row["unique_under_70_percent_rule"] is False for row in focus_rows)
    assert all(row["recommendation"] == "DO NOT SUBMIT" for row in focus_rows)
    assert summary["leaderboard_claim_irregularity"]["status"] == "UNVERIFIED-OWNER-REPORT"


def test_latest_binary_candidate_is_research_only_and_uniqueness_is_not_claimed():
    review = load("evidence/repo_review_20261031.json")
    candidate = review["latest_binary_candidate_from_upstream_pr_68"]
    path = ROOT / candidate["path"]
    digest = hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
    page = (ROOT / "docs/executive-summary.html").read_text()

    assert digest == candidate["sha256"]
    assert candidate["submit"] is False
    assert candidate["holdout_dti"] is None
    assert candidate["registry_unique"] is None
    assert candidate["registry_entries_checked"] == 0
    assert candidate["frozen_registry_entries_total"] == 179
    assert "UNVERIFIED" in page
    assert "0 of 179 registry entries compared" in page
    assert "unique-by-construction" not in page
    assert "repo-review-20261031.md" in page


def test_report_run_card_does_not_claim_new_holdout_or_current_leaderboard():
    review = load("evidence/repo_review_20261031.json")
    report = (ROOT / "docs/repo-review-20261031.md").read_text()
    assert review["current_research_artifact"]["holdout_dti"]["freshly_measured_this_review"] is False
    assert "unavailable" in report.lower()
    assert "2026-10-31 current leaderboard value" in report
    assert "did not create a new raster" in report.lower()
