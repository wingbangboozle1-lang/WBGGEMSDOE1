import numpy as np
import pytest

from wbggems.commutator import normalized_commutator, features, robust_field


def test_commuting_diagonal_and_isotropic_tensors_are_zero():
    assert normalized_commutator((2, 0, -1), (4, 0, 7)) == 0
    assert normalized_commutator((1, 0, 1), (3, 5, 9)) == 0
    assert normalized_commutator((0, 0, 0), (3, 5, 9)) == 0


def test_orthogonal_deviatoric_tensors_hit_analytic_bound():
    assert normalized_commutator((1, 0, -1), (0, 1, 0)) == pytest.approx(1)


def test_symmetric_exchange_scale_and_rotation_invariance():
    a = np.array([[3., 1.], [1., -2.]])
    b = np.array([[4., -3.], [-3., 2.]])
    tup = lambda m: (m[0, 0], m[0, 1], m[1, 1])
    expected = normalized_commutator(tup(a), tup(b))
    assert normalized_commutator(tup(b), tup(a)) == pytest.approx(expected)
    assert normalized_commutator(tup(a * 11), tup(b * -4)) == pytest.approx(expected)
    theta = .71
    q = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    assert normalized_commutator(tup(q @ a @ q.T), tup(q @ b @ q.T)) == pytest.approx(expected, abs=1e-6)


def test_nonfinite_tensors_rejected():
    with pytest.raises(ValueError, match="finite"):
        normalized_commutator((np.nan, 0, 1), (1, 2, 3))


def test_feature_bounds_missing_data_and_no_catalogue_argument():
    y, x = np.mgrid[-1:1:101j, -1:1:101j]
    c = (x*x - y*y).astype(np.float32)
    z = (x*y).astype(np.float32)
    fp = np.ones(c.shape, bool)
    fp[:3] = False
    c[50, 50] = np.nan
    planes, receipt = features(c, z, np.ones_like(c), fp)
    assert len(planes) == 4
    for p in planes:
        assert np.isfinite(p).all() and p.min() >= 0 and p.max() <= 1
        assert (p[~fp] == 0).all()
    assert receipt["catalogue_features_used"] is False
    assert receipt["prior_prediction_pixels_used"] is False


def test_empty_and_mismatched_measurements_fail():
    a = np.zeros((9, 10), np.float32)
    with pytest.raises(ValueError):
        robust_field(a, np.zeros_like(a, bool))
    with pytest.raises(ValueError, match="mismatch"):
        features(a, a[:, :3], a, np.ones_like(a, bool))
