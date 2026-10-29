"""Invariants for the catalogue tip-continuation candidate and the per-fold holdout path (2026-10-29)."""

import numpy as np
from scipy.ndimage import distance_transform_edt

from gems1 import holdout as H
from gems1.tip_continuation import GATE_PX, generate_dots, random_null


def _synthetic():
    foot = np.ones((120, 120), bool)
    fault = np.zeros_like(foot)
    # one elongated trace per quadrant so every holdout fold has a hidden component
    fault[30, 30:60] = True
    fault[30, 80:110] = True
    fault[90, 30:60] = True
    fault[90, 80:110] = True
    return foot, fault


def test_dots_respect_gate_footprint_and_catalogue():
    foot, fault = _synthetic()
    dots = generate_dots(fault, foot)
    assert dots.sum() > 0
    d = distance_transform_edt(~fault)
    assert (d[dots] > GATE_PX).all()
    assert not (dots & fault).any()
    assert not (dots & ~foot).any()


def test_dots_are_thinned_to_non_adjacent():
    foot, fault = _synthetic()
    dots = generate_dots(fault, foot)
    rr, cc = np.nonzero(dots)
    for r, c in zip(rr, cc):
        nb = dots[max(r - 1, 0) : r + 2, max(c - 1, 0) : c + 2].sum()
        assert nb == 1  # only itself within the 3x3 box


def test_dots_use_only_the_visible_set():
    """Removing a trace must change the candidate only through that trace's own tips."""
    foot, fault = _synthetic()
    full = generate_dots(fault, foot)
    reduced = fault.copy()
    reduced[90, 80:110] = False  # withhold one trace
    part = generate_dots(reduced, foot)
    # nothing emitted may be closer than the gate to the reduced visible set
    d = distance_transform_edt(~reduced)
    assert (d[part] > GATE_PX).all()
    assert full.sum() != part.sum() or not np.array_equal(full, part)


def test_per_fold_oracle_scores_one_and_empty_scores_zero():
    foot, fault = _synthetic()
    ctx = H.build_context(foot, fault)
    oracle = {f.index: (f.hidden & f.active & (f.d_visible > GATE_PX)) for f in ctx.folds}
    res = H.evaluate_mask(None, ctx, b_visible_px=GATE_PX, n_boot=5, pred_by_fold=oracle)
    assert res["n_withheld_positives"] > 0
    assert abs(res["pooled_dti"] - 1.0) < 1e-9
    empty = H.evaluate_mask(np.zeros(foot.shape, bool), ctx, b_visible_px=GATE_PX, n_boot=5)
    assert empty["pooled_dti"] == 0.0


def test_random_null_has_requested_size_and_stays_in_region():
    foot, _ = _synthetic()
    region = foot.copy()
    region[:10] = False
    rng = np.random.default_rng(3)
    out = random_null(region, 50, rng)
    assert out.sum() == 50
    assert not (out & ~region).any()
