"""Unit tests for the WBG-D1 radiometric alteration lane."""
from __future__ import annotations

import numpy as np
import pytest

from wbggemsd1.features import (
    CHANNEL_NAMES,
    DOT_BUDGET,
    deterministic_composite,
    nms_dots,
    robust_z,
    rtp_edge,
)


def test_robust_z_median_zero_and_mad_scale():
    a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], np.float32)
    mask = np.ones_like(a, bool)
    z = robust_z(a, mask)
    assert abs(float(np.median(z))) < 1e-6
    assert z.shape == a.shape and z.dtype == np.float32
    assert np.isfinite(z).all()


def test_nms_separation_budget_and_mask():
    rng = np.random.default_rng(0)
    score = rng.random((120, 120))
    allowed = np.ones_like(score, bool)
    allowed[:5, :] = False
    dots = nms_dots(score, allowed, budget=500, min_distance=3)
    assert dots.dtype == bool
    assert dots.sum() <= 500
    assert not dots[:5, :].any()
    yy, xx = np.nonzero(dots)
    # Chebyshev separation >= 3 px between every accepted pair (sampled check)
    for i in range(0, len(yy), max(1, len(yy) // 40)):
        d = np.maximum(np.abs(yy - yy[i]), np.abs(xx - xx[i]))
        assert d[d > 0].min() >= 3


def test_nms_rejects_nonfinite():
    score = np.full((40, 40), 0.5)
    score[0, 0] = np.nan
    allowed = np.ones_like(score, bool)
    with pytest.raises(ValueError):
        nms_dots(score, allowed, budget=10)


def test_composite_formula_and_support():
    H = W = 64
    fp = np.ones((H, W), bool)
    channels = {name: np.random.default_rng(i).normal(size=(H, W)).astype(np.float32)
                for i, name in enumerate(CHANNEL_NAMES)}
    rtp3 = np.abs(np.random.default_rng(9).normal(size=(H, W)).astype(np.float32))
    score = deterministic_composite(channels, rtp3, fp)
    assert score.shape == (H, W)
    fp2 = fp.copy()
    fp2[:8, :8] = False
    score2 = deterministic_composite(channels, rtp3, fp2)
    assert np.all(score2[:8, :8] == -1e9)
    # frozen coefficient check on a hand-built case
    ch = {name: np.zeros((H, W), np.float32) for name in CHANNEL_NAMES}
    ch["Potassic_hp5"][10, 10] = 2.0
    ch["K_hp10"][10, 10] = 1.0
    ch["ThK_edge5"][10, 10] = 0.5
    r0 = np.zeros((H, W), np.float32)
    s = deterministic_composite(ch, r0, fp)
    expected = 0.5 * 2.0 + 0.3 * 1.0 + 0.3 * np.tanh(0.5 / 2.0)
    assert abs(float(s[10, 10]) - expected) < 1e-6


def test_rtp_edge_zero_outside_footprint(tmp_path):
    fp = np.ones((48, 48), bool)
    fp[:6, :] = False
    p = tmp_path / "rtp.npy"
    np.save(p, np.random.default_rng(1).normal(size=(48, 48)).astype(np.float32))
    e = rtp_edge(p, fp)
    assert np.all(e[:6, :] == 0.0)
    assert np.isfinite(e).all() and (e >= 0).all()


def test_dot_budget_matches_historical_scale():
    # frozen in registry/preregistration_wbg_d1.json
    assert DOT_BUDGET == 37_654
    assert len(CHANNEL_NAMES) == 7
