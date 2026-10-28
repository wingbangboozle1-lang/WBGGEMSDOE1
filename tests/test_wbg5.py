"""WBG-5 lane tests: metric algebra, placement, and the vacuous-gate certificate.

These tests need only numpy/scipy/rasterio and the small bridge rasters, so they
run in CI without the 1.6 GB feature stack or any network access.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from gems.metric import dti_score_fast  # noqa: E402
from wbg5 import place  # noqa: E402


def test_marginal_threshold_matches_bruteforce_dti():
    """Brute force: adding one isolated dot raises DTI exactly when k > alpha*DTI.

    Uses the shared evaluator, not a re-implementation, so the test fails if the
    metric and the placement rule ever drift apart.
    """
    truth = np.zeros((40, 40), bool)
    truth[10, 10] = truth[30, 30] = True
    base_pred = np.zeros((40, 40), bool)
    base_pred[30, 30] = True          # one truth pixel covered, one not
    base = dti_score_fast(base_pred.astype(np.float32), truth)
    thr = place.marginal_threshold(base["dti"])
    assert thr == pytest.approx(0.2 * base["dti"])      # alpha * DTI
    for distance in (0.0, 1.0, 2.0, 2.9):
        candidate = base_pred.copy()
        candidate[10 + int(round(distance)), 10] = True
        k = max(1.0 - round(distance) / 3.0, 0.0)
        after = dti_score_fast(candidate.astype(np.float32), truth)["dti"]
        assert (after > base["dti"]) == (k > thr), (distance, k, thr, after, base["dti"])


def test_threshold_formula_is_shift_invariant_in_k():
    """dD = alpha for every k, so the rule cannot depend on the kernel weight."""
    for dti in (0.05, 0.2, 0.4, 0.6):
        assert place.marginal_threshold(dti) == pytest.approx(0.2 * dti)


def test_threshold_stays_below_the_kernel_weight_at_2_5px():
    """For every realistic DTI, a dot 2.5 px from truth (k=0.167) is worth adding."""
    for dti in np.linspace(0.0, 0.6, 61):
        assert place.marginal_threshold(float(dti)) < 1.0 - 2.5 / 3.0


def test_suppression_order_respects_spacing_and_budget():
    rng = np.random.default_rng(0)
    score = rng.random((60, 60)).astype(np.float32)
    eligible = np.ones((60, 60), bool)
    for d_min in (2.0, 3.0, 4.0):
        order = place.suppression_order(score, eligible, d_min=d_min, max_n=100,
                                        keep_frac=1.0)
        assert len(order) == 100
        rr, cc = np.divmod(order, 60)
        pts = np.column_stack([rr, cc])
        d = np.hypot(*(pts[:, None, :] - pts[None, :, :]).transpose(2, 0, 1))
        np.fill_diagonal(d, np.inf)
        assert d.min() >= d_min - 1e-9, (d_min, d.min())


def test_suppression_order_is_score_greedy():
    """The first accepted index must be the global argmax of the eligible score."""
    score = np.zeros((20, 20), np.float32)
    score[3, 7] = 0.9
    score[10, 10] = 0.8
    order = place.suppression_order(score, np.ones((20, 20), bool), d_min=2.0, max_n=3)
    assert order[0] == 3 * 20 + 7


def test_dots_from_order_and_coverage_report():
    dots = np.zeros((30, 30), bool)
    truth = np.zeros((30, 30), bool)
    truth[10, 10] = truth[10, 11] = True
    dots[10, 10] = True
    rep = place.coverage_report(dots, truth)
    assert rep["n_truth"] == 2
    assert rep["coverage"] == pytest.approx((1.0 + 2.0 / 3.0) / 2.0, abs=1e-6)


def test_vacuous_lattice_gate_certificate():
    """The spacing-5 lattice must 'overlap' a random dot set at >99%.

    This is the measured basis for excluding synthetic calibration lattices from
    the competing-submission novelty gate. It is a property of the comparator,
    not of any submission.
    """
    from scipy.ndimage import distance_transform_edt

    lattice_path = ROOT / ".cache" / "anchors" / "lattice_r13_s5.tif"
    template = ROOT / "data" / "bridge" / "sample_submission.tif"
    if not lattice_path.exists():
        pytest.skip("lattice control not fetched (run scripts/fetch_anchor_rasters.py)")
    import rasterio

    with rasterio.open(lattice_path) as ds:
        lattice = np.nan_to_num(ds.read(1)) > 0
    with rasterio.open(template) as ds:
        foot = np.isfinite(ds.read(1))
    dist = distance_transform_edt(~lattice)
    population = float((dist[foot] <= 3.0).mean())
    rng = np.random.default_rng(7)
    idx = rng.choice(np.flatnonzero(foot), size=40000, replace=False)
    random_overlap = float((dist.ravel()[idx] <= 3.0).mean())
    assert population > 0.99
    assert random_overlap > 0.99


def test_validator_receipt_shape():
    receipt = ROOT / "evidence" / "wbg5" / "validator.json"
    if not receipt.exists():
        pytest.skip("validator receipt not built yet")
    data = json.loads(receipt.read_text())
    assert data["checks"]["single_band"] and data["checks"]["float32"]
    assert data["checks"]["values_in_0_1"]
    assert data["checks"]["no_nan_inside_footprint"]
    assert data["checks"]["nan_outside_footprint_only"]
    assert data["positive_pixels"] > 0
