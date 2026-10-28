"""Unit tests for the WBG-5 lane: trace geometry, gates arithmetic, ladder identity."""
import numpy as np
import pytest

from wbg5 import emission, fleet, gates, structure, trace


def _two_segments():
    m = np.zeros((60, 60), bool)
    m[10:26, 30] = True          # a 16-px N-S segment
    m[40, 5:15] = True           # a 10-px E-W segment
    return m


def test_tip_traces_extend_along_strike_and_stop():
    geom = structure.segments_from_mask(_two_segments(), min_px=8)
    tf = trace.tip_traces(geom, (60, 60), extend=15)
    assert tf.n_tips == 2 * len(geom.segments)
    # the vertical segment's tips are (10,30) and (25,30); its extension runs to row 40
    assert tf.mask[40, 30]
    assert tf.mask[0, 30]
    # it must not wander sideways
    assert not tf.mask[25, 33]
    # the catalogue itself is never emitted
    assert not (tf.mask & _two_segments()).any()


def test_tip_traces_is_deterministic():
    geom = structure.segments_from_mask(_two_segments(), min_px=8)
    a = trace.tip_traces(geom, (60, 60), 15).mask
    b = trace.tip_traces(geom, (60, 60), 15).mask
    assert np.array_equal(a, b)


def test_tip_traces_clip_at_the_grid_edge():
    m = np.zeros((30, 30), bool)
    m[0:10, 15] = True
    geom = structure.segments_from_mask(m, min_px=8)
    tf = trace.tip_traces(geom, (30, 30), extend=40)
    assert tf.mask.shape == (30, 30)
    assert tf.mask[0, 15] or tf.mask.sum() > 0


def test_score_identity_matches_the_published_form():
    """DTI must equal TP / (TP + 0.2 FP + 0.8 FN) for the ladder's own numbers."""
    tp, fp, fn = 10_249.0, 19_010.0, 28_551.0
    dti = tp / (tp + 0.2 * fp + 0.8 * fn)
    assert dti == pytest.approx(0.2778, abs=5e-4)
    recovered_tp = 0.2 * 22_415 / ((1 / 0.2477 - 1) - (1 / 0.2778 - 1))
    assert recovered_tp == pytest.approx(10_249, rel=0.01)


def test_forward_overlap_is_asymmetric_and_bounded():
    a = np.zeros((40, 40), bool)
    a[10, 10:20] = True
    b = np.zeros((40, 40), bool)
    b[10, 12] = True
    # only the six of a's ten pixels within 3 px of (10, 12) are explained
    assert gates.forward_overlap(a, b) == pytest.approx(0.6)
    assert gates.forward_overlap(b, a) == pytest.approx(1.0)
    assert 0.0 <= gates.forward_overlap(a, b) <= 1.0


def test_operative_rule_drops_carpets_and_keeps_emissions():
    rows = [
        {"registry_file": "carpet", "n_dots": 60_000, "reference_own_halo_coverage": 0.8,
         "forward_overlap_3px": 0.99, "surface_spearman": 0.1},
        {"registry_file": "emission", "n_dots": 30_000, "reference_own_halo_coverage": 0.2,
         "forward_overlap_3px": 0.1, "surface_spearman": 0.1},
    ]
    out = gates.operative(rows)
    assert out["pass"] is True
    assert out["n_excluded_as_carpet"] == 1
    assert out["excluded"] == ["carpet"]


def test_alignment_null_does_not_flag_a_distance_matched_field():
    shape = (80, 80)
    d_cat = np.full(shape, 9.0, np.float32)
    fp = np.ones(shape, bool)
    rng = np.random.default_rng(0)
    ref = np.zeros(shape, bool)
    ref[rng.integers(0, 80, 200), rng.integers(0, 80, 200)] = True
    cand = np.zeros(shape, bool)
    cand[rng.integers(0, 80, 200), rng.integers(0, 80, 200)] = True
    registry = {"rasters": {"r": {"n_dots": 200, "mask": gates.encode_mask(ref)}}}
    out = gates.alignment_test(cand, registry, d_cat, fp, n_null=6)
    assert out["rows"][0]["excess_over_null"] < 0.30


def test_mask_codec_round_trips():
    m = np.zeros((30, 40), bool)
    m[3:9, 4:20] = True
    m[22, 33] = True
    assert np.array_equal(gates.decode_mask(gates.encode_mask(m), m.shape), m)


def test_fleet_geometry_is_a_pure_function_of_the_mask():
    cat = np.zeros((50, 50), bool)
    cat[20, :] = True
    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    m = np.zeros((50, 50), bool)
    m[10, 5:15] = True
    a = fleet.geometry(m, d_cat, cat, int(cat.sum()))
    b = fleet.geometry(m.copy(), d_cat, cat, int(cat.sum()))
    assert a == b
    assert set(a) == set(fleet.FEATURES)


def test_dash_emit_respects_the_separation_floor():
    rng = np.random.default_rng(1)
    rank = rng.random((50, 50)).astype(np.float32)
    theta = np.zeros((50, 50), np.float32)
    m = emission.dash_emit(rank, theta, np.ones((50, 50), bool), 200, step=6.0, min_sep=6.0)
    ys, xs = np.nonzero(m)
    assert m.sum() > 20
    # no two emitted pixels on the same row within 5 px of each other
    for y in np.unique(ys):
        row = np.sort(xs[ys == y])
        assert np.all(np.diff(row) >= 5)
