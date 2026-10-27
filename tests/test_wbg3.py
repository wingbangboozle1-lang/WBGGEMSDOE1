"""WBG-3: per-raster uniqueness gate fix + shipped run-card consistency."""
import hashlib
import json
from pathlib import Path

import numpy as np

from wbg2 import uniqueness as U

ROOT = Path(__file__).resolve().parents[1]
NAME = "wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros"


def test_per_raster_gate_not_false_stopped_by_mixed_registry():
    """Worst enrichment and worst overlap must come from the SAME raster."""
    ours = np.zeros((200, 200), np.float32)
    rng = np.random.default_rng(3)
    idx = rng.choice(200 * 200, 400, replace=False)
    ours.ravel()[idx] = 1.0
    dense = np.full((200, 200), 0.5, np.float32)          # overlap 1.0, enrichment ~1
    sparse_other = np.zeros((200, 200), np.float32)       # unrelated sparse field
    idx2 = rng.choice(200 * 200, 400, replace=False)
    sparse_other.ravel()[idx2] = 1.0
    for theirs in (dense, sparse_other):
        c = U.compare(ours, theirs)
        assert not (c["enrichment"] >= U.STOP_ENRICHMENT and c["forward_overlap"] > U.STOP_OVERLAP)


def test_per_raster_gate_stops_a_copy():
    a = np.zeros((200, 200), np.float32)
    a[40:160, 100] = 1.0
    c = U.compare(a, a.copy())
    assert c["enrichment"] >= U.STOP_ENRICHMENT and c["forward_overlap"] > U.STOP_OVERLAP


def test_wbg3_run_card_consistent_with_shipped_file():
    card = json.loads((ROOT / "evidence/wbg3/run_card.json").read_text())
    tif = ROOT / f"docs/downloads/{NAME}.tif"
    assert tif.exists()
    digest = hashlib.sha256(tif.read_bytes()).hexdigest()
    assert card["raster_sha256"] == digest
    assert card["validator"]["tif"]["all_checks_passed"] is True
    assert card["validator"]["zip"]["all_checks_passed"] is True
    assert card["registry"]["passes_final_dot_gate"] is True
    assert card["registry"]["per_raster_gate_failures"] == []
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
