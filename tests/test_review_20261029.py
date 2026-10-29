from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_current_review_and_card_have_same_fail_closed_decision():
    card = json.loads((ROOT / "docs/data/repo-review-20261029.json").read_text())
    report = (ROOT / "docs/repo-review-current-20261029.md").read_text()
    assert card["verdict"] == "negative"
    assert card["experiments_started"] == card["submission_slots_used"] == 0
    assert card["holdout_dti"]["evidence_class"] == "NOT RUN"
    assert card["holdout_dti"]["evaluator_version"] is None
    assert card["holdout_dti"]["withheld_positive_pixels"] is None
    assert card["holdout_dti"]["ci95"] is None
    assert card["raster_sha256"] is None
    assert card["submission_name"] is None
    assert card["submission_note_length"] == len(card["submission_note"]) <= 140
    assert card["leaderboard_estimate"] is None
    assert "No new TIFF was generated" in report
    assert "DO NOT SUBMIT" in report
    assert "OWNER-REPORTED / NOT ORGANIZER-CONFIRMED" in report


def test_four_prospective_hypotheses_cover_required_science_and_readiness_fields():
    card = json.loads((ROOT / "docs/data/repo-review-20261029.json").read_text())
    candidates = card["candidate_ranking"]
    assert len(candidates) == 4
    required = {
        "expected_incremental_benefit",
        "implementation_cost",
        "layers",
        "physical_signature",
        "why_missing_faults",
        "named_non_fault_mimic",
        "difference_from_repo",
        "data_source",
        "data_checked",
        "viable_now",
        "blocking_reason",
    }
    for candidate in candidates:
        assert required <= candidate.keys()
        assert candidate["viable_now"] is False
        assert "not a score estimate" in candidate["expected_incremental_benefit"]
    assert candidates[0]["id"] == "P1"
    assert "missing authorized single-method lane" in candidates[0]["blocking_reason"]


def test_readme_and_agent_instructions_link_current_review_and_avoid_stale_approval():
    readme = (ROOT / "README.md").read_text()
    agents = (ROOT / "AGENTS.md").read_text()
    builder = (ROOT / "scripts/build_readme.py").read_text()
    assert "docs/repo-review-current-20261029.md" in readme
    assert "docs/repo-review-current-20261029.md" in builder
    assert "NO CURRENT TIFF CLEARED" in readme
    assert "NO CURRENT TIFF CLEARED" in agents
    assert "APPROVED FOR SUBMISSION" not in agents
    assert "WBG-7 (this branch)" not in agents


def test_homepage_does_not_label_wbg7_as_unique_submission_clearance():
    source = (ROOT / "scripts/build_site.py").read_text()
    page = (ROOT / "docs/index.html").read_text()
    assert "WBG-7 RESEARCH TIFF: DOWNLOAD YES (research only) · SUBMIT NO." in source
    assert "two focus-site champions, not the complete registry" in source
    assert "WBG-7 RESEARCH TIFF: DOWNLOAD YES (research only) · SUBMIT NO." in page
    assert "repo-review-current-20261029.md" in page
    assert "Depth-conditioned magnetic texture transport — TESTED NULL" in source
    assert re.search(r"HOLDOUT-DTI\s+0\.0149", page)
