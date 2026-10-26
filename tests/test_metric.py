"""Unit tests for the DTI metric (exact hand-checkable cases)."""
import numpy as np

from wbg1 import metric


def test_perfect_prediction_scores_one():
    truth = np.zeros((40, 40), dtype=bool)
    truth[10:30, 10:30] = True
    t = metric.dti_terms(truth.copy(), truth)
    assert t["DTI"] == 1.0, t
    assert t["A"] == t["N"] == t["T"]


def test_empty_prediction_scores_zero():
    truth = np.zeros((40, 40), dtype=bool)
    truth[10:30, 10:30] = True
    pred = np.zeros((40, 40), dtype=bool)
    t = metric.dti_terms(pred, truth)
    assert t["DTI"] == 0.0, t


def test_far_prediction_near_zero():
    truth = np.zeros((60, 60), dtype=bool)
    truth[5:10, 5:10] = True
    pred = np.zeros((60, 60), dtype=bool)
    pred[50:55, 50:55] = True
    t = metric.dti_terms(pred, truth)
    assert t["A"] == 0.0 and t["DTI"] == 0.0, t


def test_single_pixel_credit_geometry():
    # one truth px, one pred px at distance d (px): A = max(1-d/3,0)
    for d, expect in [(0, 1.0), (1, 2 / 3), (2, 1 / 3), (3, 0.0)]:
        truth = np.zeros((30, 30), dtype=bool)
        pred = np.zeros((30, 30), dtype=bool)
        truth[15, 15] = True
        pred[15, 15 + d] = True
        t = metric.dti_terms(pred, truth)
        assert abs(t["A"] - expect) < 1e-6, (d, t)
    # symmetric single-pixel case: DTI = A/(A+0.2(1-A)+0.8(1-A)) = A (A=B here)
    truth = np.zeros((30, 30), dtype=bool)
    pred = np.zeros((30, 30), dtype=bool)
    truth[15, 15] = True
    pred[15, 16] = True
    t = metric.dti_terms(pred, truth)
    assert abs(t["DTI"] - (2 / 3)) < 1e-6, t


def test_naive_closure_matches_exact_when_ab_equal():
    a, n_over_t = 0.4, 3.0
    assert abs(metric.naive_closure(a, n_over_t) - a / (0.8 + 0.2 * n_over_t)) < 1e-12
    # inversion round-trip
    target = 0.26
    aa = metric.solve_credit_fraction(target, n_over_t)
    assert abs(metric.naive_closure(aa, n_over_t) - target) < 1e-9


def test_break_even_values():
    assert abs(metric.break_even(0.26) - 0.052) < 1e-12
    assert abs(metric.break_even(0.2778) - 0.05556) < 1e-12


def test_bootstrap_ci_deterministic():
    rng = np.random.default_rng(0)
    a = rng.random(256) * 10
    fp = rng.random(256) * 5
    fn = rng.random(256) * 20
    c1 = metric.bootstrap_ci(a, fp, fn, n_rep=200, seed=7)
    c2 = metric.bootstrap_ci(a, fp, fn, n_rep=200, seed=7)
    assert c1 == c2
    assert c1["ci95"][0] <= c1["point"] <= c1["ci95"][1]
