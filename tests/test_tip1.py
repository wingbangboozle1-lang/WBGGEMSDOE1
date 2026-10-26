import numpy as np
import pytest

from gems import tip1


def test_decode_inverts_fixed_encodings_and_missing_zero():
    q = np.array([0, 1, 128, 255], dtype=np.uint8)
    linear = tip1.decode(q, 1.0, "linear")
    square = tip1.decode(q, 2.0, "sqrt")
    assert linear[0] == linear[1] == 0
    assert linear[-1] == pytest.approx(1)
    assert square[-1] == pytest.approx(2)
    assert square[2] == pytest.approx(2 * linear[2] ** 2)


def test_axial_delta_follows_north_and_east_strikes_without_edge_artifact():
    coherence = np.tile(np.arange(9, dtype=np.float32)[:, None], (1, 9))
    support = np.ones_like(coherence, dtype=bool)
    north = np.zeros_like(coherence)
    delta_north = tip1.axial_delta(coherence, north, support, 2, chunk_rows=3)
    assert delta_north[4, 4] == pytest.approx(4)
    assert delta_north[0, 4] == 0

    east_gradient = coherence.T.copy()
    east = np.full_like(coherence, 90)
    delta_east = tip1.axial_delta(east_gradient, east, support, 2, chunk_rows=4)
    assert delta_east[4, 4] == pytest.approx(4)
    assert delta_east[4, 0] == 0

    support[4, 6] = False
    blocked = tip1.axial_delta(east_gradient, east, support, 2)
    assert blocked[4, 4] == 0


def test_balance_veto_and_locked_arms():
    neg = np.array([[1.0, 1.0, 0.0]], dtype=np.float32)
    pos = np.array([[1.0, 0.0, 1.0]], dtype=np.float32)
    balance = tip1.curvature_balance(neg, pos)
    np.testing.assert_allclose(balance, [[1.0, 0.0, 0.0]], atol=1e-6)

    veto = tip1.channel_bank_veto(
        np.array([[0.0, 1.0]], np.float32),
        np.array([[1.0, 1.0]], np.float32),
        np.array([[0.5, 0.5]], np.float32),
    )
    np.testing.assert_allclose(veto, [[1.0, 0.5]])

    shape = (1, 2)
    arms = tip1.arm_surfaces(
        coherence=np.full(shape, 0.8, np.float32),
        delta2=np.full(shape, 0.2, np.float32),
        delta4=np.full(shape, 0.4, np.float32),
        balance=np.ones(shape, np.float32),
        root_step=np.full(shape, 0.5, np.float32),
        veto=np.ones(shape, np.float32),
        support=np.array([[True, False]]),
    )
    assert arms["A"][0, 0] == pytest.approx(0.4)
    assert arms["B"][0, 0] == pytest.approx(0.2)
    assert arms["C"][0, 0] == pytest.approx(np.sqrt(0.08) * 0.5)
    assert all(surface[0, 1] == 0 for surface in arms.values())


def test_fixed_support_requires_all_channels_and_majority_validity():
    shape = (2, 2)
    encoded = {name: np.full(shape, 255, np.uint8) for name in tip1.BANDS}
    footprint = np.ones(shape, bool)
    encoded["step_max"][0, 0] = 0
    # Linear valid code 128 decodes to exactly 0.5 and must not pass >0.5.
    encoded["valid"][0, 1] = 128
    support = tip1.fixed_support(encoded, footprint)
    np.testing.assert_array_equal(support, [[False, False], [True, True]])
