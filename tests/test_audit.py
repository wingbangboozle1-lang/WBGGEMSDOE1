import numpy as np
import pytest

from wbggems.audit import single_feature_canary, promotion_decision
from gems57 import submission_writer, evaluate_holdout


def test_canary_finds_leakage_in_both_orientations():
    truth = np.array([0, 0, 0, 1, 1, 1], bool)
    for values in (truth.astype(float), ~truth):
        result = single_feature_canary(values, truth, name="deliberate_leak", fold="test")
        assert result["leakage_suspected"]
        assert result["orientation_invariant_auc"] == 1


def test_canary_checks_missingness():
    truth = np.array([0, 0, 0, 1, 1, 1], bool)
    values = np.array([0., 0., 0., np.nan, np.nan, np.nan])
    assert single_feature_canary(values, truth, name="missing", fold="test")["leakage_suspected"]


def test_selector_cannot_approve_a_weekly_slot_even_when_scientific_gates_pass():
    result = promotion_decision(format_ok=True, novelty_ok=True, canary_ok=True,
        paired_ci95=[.001, .01], same_instrument_best_beaten=True, authorized_lane=True,
        organizer_slot_receipt={"source": "synthetic-test-only"}, confirmation_passed=True)
    assert result["eligible_for_separate_selector"]
    assert result["verdict"] == "promote"
    assert not result["ok_to_submit"] and result["submission_slots_used"] == 0


def test_unknown_allowance_and_lane_fail_closed():
    result = promotion_decision(format_ok=True, novelty_ok=True, canary_ok=True,
        paired_ci95=[.001, .01], same_instrument_best_beaten=True, authorized_lane=False,
        organizer_slot_receipt=None, confirmation_passed=False)
    assert result["verdict"] == "negative"
    assert result["ok_to_download"] and not result["ok_to_submit"]
    assert len(result["reasons"]) == 3


@pytest.mark.parametrize("bad", [np.nan, np.inf, -0.001, 1.001, -9999])
def test_shared_writer_refuses_range_error_without_silent_repairs(tmp_path, bad):
    p = np.zeros((4, 5), np.float32)
    p[1, 2] = bad
    with pytest.raises(ValueError, match="finite"):
        submission_writer.write_submission(tmp_path / "invalid.tif", p, tmp_path / "sample.tif",
            np.ones_like(p, bool), note="test", name="test")
    assert not list(tmp_path.iterdir())


def test_shared_pooled_summary_rejects_mismatched_truth_counts():
    a = np.array([[1., 4., 2., 3.], [2., 5., 2., 4.]])
    b = a.copy()
    b[0, 3] += 1
    with pytest.raises(ValueError, match="truth count"):
        evaluate_holdout.pooled_summary({"control": a, "candidate": b}, candidate="candidate")
