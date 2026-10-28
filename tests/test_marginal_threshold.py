"""The marginal-inclusion rule must follow from the metric, not from memory.

With the organiser's alpha=0.2 / beta=0.8 the weights sum to 1, so one extra
non-redundant dot moves the metric denominator by exactly alpha and the
break-even kernel credit is ``alpha * DTI``. These tests rebuild that number
through the pixel evaluator, pin the distance form, and document -- without
rewriting -- the frozen fork that disagrees.
"""

import numpy as np
import pytest

from gems.metric import ALPHA, BETA, dti_score_fast
from gems.metric import marginal_inclusion_threshold as frozen_fork
from gems.marginal_rule import (
    break_even_kernel_credit,
    break_even_radius_px,
    denominator_shift,
    dot_is_worth_adding,
)


def test_break_even_is_alpha_times_dti():
    for dti in (0.05, 0.20, 0.28, 0.45):
        assert break_even_kernel_credit(dti) == pytest.approx(ALPHA * dti, abs=1e-15)
    assert break_even_kernel_credit(0.28) == pytest.approx(0.056, abs=1e-12)


def test_denominator_shifts_by_exactly_alpha_for_any_kernel_credit():
    # dD = k + alpha*(1-k) - beta*k == alpha because 1 - alpha - beta == 0.
    for k in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0):
        assert denominator_shift(k) == pytest.approx(ALPHA, abs=1e-15)
    assert ALPHA + BETA == pytest.approx(1.0)


def test_distance_form_matches_the_three_pixel_kernel():
    # DTI 0.28 -> break even at 2.832 px; DTI 0 -> any dot helps (3 px).
    assert break_even_radius_px(0.28) == pytest.approx(3.0 * (1 - 0.056), abs=1e-12)
    assert break_even_radius_px(0.0) == pytest.approx(3.0)
    assert break_even_radius_px(0.9) == pytest.approx(3.0 * (1 - 0.18))
    for dti in np.linspace(0, 1, 9):
        k = break_even_kernel_credit(dti)
        assert dot_is_worth_adding(k + 1e-9, dti)
        assert not dot_is_worth_adding(k - 1e-9, dti)


def test_one_dot_through_the_evaluator_behaves_as_derived():
    """Brute force: a dot inside the break-even radius raises DTI, one outside lowers it."""
    shape = (41, 41)
    truth = np.zeros(shape, bool)
    truth[20, 8:14] = True   # six truth pixels, fully covered by ``base``
    truth[5, 30] = True      # one truth pixel left uncovered -> a real FN to claim
    valid = np.ones(shape, bool)
    base = np.zeros(shape, bool)
    base[20, 8:14] = True
    base[2:6, 2:12] = True   # ten off-truth dots, all far from the uncovered pixel
    before = dti_score_fast(base, truth, valid_mask=valid)
    start = before["dti"]
    assert before["FN_w"] == pytest.approx(1.0)  # the marginal dot has something to claim

    k_star = break_even_kernel_credit(start)
    assert 0.0 < k_star < 1.0 / 3.0  # so the integer 2 px step straddles the threshold
    inside = base.copy()
    inside[5, 32] = True    # 2 px away -> k = 1/3 > k*
    outside = base.copy()
    outside[5, 33] = True   # 3 px away -> k = 0 < k*

    gained = dti_score_fast(inside, truth, valid_mask=valid)
    lost = dti_score_fast(outside, truth, valid_mask=valid)
    # The identity the rule rests on: the denominator moves by exactly alpha.
    assert gained["TP_w"] + 0.2 * gained["FP_w"] + 0.8 * gained["FN_w"] == pytest.approx(
        before["TP_w"] + 0.2 * before["FP_w"] + 0.8 * before["FN_w"] + 0.2, abs=1e-6
    )
    assert gained["TP_w"] > before["TP_w"]
    assert gained["dti"] > start
    assert lost["dti"] < start


@pytest.mark.parametrize("bad", [-0.01, 1.01, float("nan")])
def test_rejects_impossible_dti(bad):
    with pytest.raises(ValueError):
        break_even_kernel_credit(bad)


def test_frozen_fork_divergence_is_documented_not_silent():
    """src/gems/metric.py is hash-pinned by an audit receipt, so it is superseded, not edited."""
    for dti in np.linspace(0.0, 1.0, 11):
        drift = frozen_fork(dti) - break_even_kernel_credit(dti)
        assert drift >= 0.0  # the fork always asks for slightly more credit
        assert drift <= 0.06  # and never by enough to move a recorded result
    assert 1e-3 < frozen_fork(0.2778) - break_even_kernel_credit(0.2778) < 5e-3
