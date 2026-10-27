"""WBG-3: literal uniqueness gate (vendor/gems57) + shipped run-card consistency."""
import hashlib
import json
from pathlib import Path

import numpy as np

from gems57.uniqueness import dot_overlap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NAME = "wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros"


def test_literal_gate_stops_a_copy():
    a = np.zeros((200, 200), np.float32)
    a[40:160, 100] = 1.0
    assert dot_overlap(a, a.copy()) > 0.70


def test_literal_gate_passes_an_independent_field():
    rng = np.random.default_rng(3)
    ours = np.zeros((200, 200), np.float32)
    ours.ravel()[rng.choice(200 * 200, 400, replace=False)] = 1.0
    other = np.zeros((200, 200), np.float32)
    other.ravel()[rng.choice(200 * 200, 400, replace=False)] = 1.0
    assert dot_overlap(ours, other) <= 0.70


def test_wbg3_run_card_consistent_with_shipped_file():
    card = json.loads((ROOT / "evidence/wbg3/run_card.json").read_text())
    tif = ROOT / f"docs/downloads/{NAME}.tif"
    assert tif.exists()
    digest = hashlib.sha256(tif.read_bytes()).hexdigest()
    assert card["raster_sha256"] == digest
    assert card["validator"]["tif"]["all_checks_passed"] is True
    assert card["validator"]["zip"]["all_checks_passed"] is True
    assert card["registry"]["unique_vs_nine_focus_sites"] is True
    assert card["registry"]["max_forward_3px_overlap_euclidean"] <= 0.70
    assert card["registry"]["max_abs_spearman"] <= 0.90
    assert len(card["submission_note"]) <= 140
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["score_estimate"]["evidence_class"] == "MODEL-ESTIMATE"
    assert card["organizer_confirmed_score"] is None
    # honest verdict: estimate below champion, gate not cleared
    assert card["decision"]["ok_to_submit"] is False
    assert card["score_estimate"]["value"] < 0.2778


def test_wbg3_holdout_beats_prior_reproducible_detectors():
    card = json.loads((ROOT / "evidence/wbg3/run_card.json").read_text())
    assert card["holdout"]["dti"] > 0.13196  # Exp2, same evaluator
    assert card["holdout"]["dti"] < card["holdout"]["benchmark_s3dep1_dti"]  # gate not cleared


def test_forensic_page_separates_pixel_lineage_from_score_causality():
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_wbg3_site", ROOT / "scripts/build_wbg3_site.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    card = json.loads((ROOT / "evidence/wbg3_spipmr/run_card.json").read_text())
    page = builder._forensics_body(card, prefix="../")
    assert "pixel-level lineage" in page.lower()
    assert "cannot establish which deleted pixels were false positives" in page
    assert "USER-REPORTED / NOT ORGANIZER-CONFIRMED" in page
    assert "no defensible conversion" in page.lower()
    assert "accounting analytically" not in page
    assert "82% of the denominator" not in page
    assert "+22%" not in page and "+110%" not in page
    assert "not identified here by organizer receipts tied to exact files" in page


def test_upload_guide_does_not_claim_cause_of_reported_range_error():
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_wbg3_site", ROOT / "scripts/build_wbg3_site.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    load = lambda name: json.loads((ROOT / name).read_text())
    page = builder._howto_body(
        load("evidence/wbg3_spipmr/run_card.json"),
        load("evidence/wbg_s2/run_card.json"),
        load("evidence/wbg_h1/run_card.json"),
        load("evidence/wbg2/run_card.json"),
        load("registry/run_card.json"),
        load("evidence/nine_site_audit.json"),
        prefix="../",
    )
    assert "Cause Unverified" in page
    assert "we do not claim they caused the reported error" in page
    assert "NaN &gt;= 0" not in page
    assert "all_checks_passed=true" in page
    assert "run_card_matches_exact_tiff=true" in page
    assert "submission_authorized" not in page
