"""Tests for the WBG-5 lane: metric arithmetic, null model, and shipped artifact."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]

from wbg5.null_model import draw_truth, dti_for, expected_dti, kernel_field
from wbg5.truth_model import (KERNEL_MASS, dti_components, dti_from_components,
                              ring_ids)


def test_official_worked_example():
    """Competition page 967 worked example: TP=3.00, FP=1.89, FN=2.00 -> 0.60."""
    dti = dti_from_components(3.00, 1.89, 2.00)
    assert abs(dti - 0.6027) < 1e-3


def test_dti_bounds():
    assert dti_from_components(0.0, 10.0, 10.0) == 0.0
    assert dti_from_components(5.0, 0.0, 0.0) == pytest.approx(1.0)


def test_kernel_mass_matches_discrete_sum():
    assert 9.0 < KERNEL_MASS < 10.0


def test_ring_ids():
    assert list(ring_ids(np.array([0.0, 1.0, 2.0, 3.0, 100.0]))) == [0, 1, 1, 2, 7]


def test_kernel_field_triangular():
    assert kernel_field(np.array([0.0, 1.5, 3.0, 4.0])) == pytest.approx([1.0, 0.5, 0.0, 0.0])


def test_brute_force_dti_matches_components():
    """A single dot at the centre of a 15x15 truth: check the two routes agree."""
    truth = np.zeros((15, 15), bool)
    truth[7, 5:10] = True
    values = np.zeros((15, 15), np.float32)
    values[7, 7] = 1.0
    got = dti_components(values, truth, None)
    # TP: every truth cell within 3 px of the dot, weighted by the kernel
    d = np.hypot(*np.mgrid[0:15, 0:15])
    expected_tp = float(np.maximum(1.0 - np.abs(np.arange(5) - 2) / 3.0, 0).sum())
    assert got["tp"] == pytest.approx(expected_tp)
    assert got["K"] == 5
    assert 0.0 < got["dti"] < 1.0
    assert d.shape == (15, 15)


def test_draw_truth_never_on_catalogue_and_hits_budget():
    rng = np.random.default_rng(3)
    cat = np.zeros((120, 120), bool)
    cat[60, :] = True
    foot = np.ones((120, 120), bool)
    t = draw_truth(cat, foot, 400, rng)
    assert not (t & cat).any()
    assert 200 <= int(t.sum()) <= 600


def test_expected_dti_is_reproducible_and_bounded():
    cat = np.zeros((90, 90), bool)
    cat[45, 20:70] = True
    foot = np.ones((90, 90), bool)
    values = np.zeros((90, 90), np.float32)
    values[30, 30:60] = 1.0
    a = expected_dti(values, cat, foot, K=400, draws=6, seed=5)
    b = expected_dti(values, cat, foot, K=400, draws=6, seed=5)
    assert a["mean"] == b["mean"]
    assert 0.0 <= a["mean"] <= 1.0
    assert a["draws"] == 6


def test_dti_for_zero_prediction_is_zero():
    truth = np.zeros((20, 20), bool)
    truth[5, 5] = True
    assert dti_for(np.zeros((20, 20), np.float32), truth) == 0.0


@pytest.mark.parametrize("receipt", [
    "evidence/wbg5_submission_audit.json",
    "evidence/wbg5_score_estimate.json",
    "evidence/wbg5_null_calibration.json",
])
def test_receipts_label_their_evidence(receipt):
    data = json.loads((ROOT / receipt).read_text())
    assert data["schema"].startswith("wbg5-")
    blob = json.dumps(data)
    assert "organizer" not in blob.lower() or "no organizer" in blob.lower()
    assert "ORGANIZER-CONFIRMED" not in blob or "no ORGANIZER-CONFIRMED" in blob


def test_shipped_artifact_matches_its_receipt():
    audit = json.loads((ROOT / "evidence/wbg5_submission_audit.json").read_text())
    tif = ROOT / audit["tif"]
    if not tif.exists():
        pytest.skip("shipped artifact not present in this checkout")
    got = hashlib.sha256(tif.read_bytes()).hexdigest()
    assert got == audit["sha256"], "artifact drifted from its audited sha256"
    assert all(audit["gates"][k] for k in ("format_pass", "not_a_byte_copy",
                                           "surface_rho_below_0.90",
                                           "never_on_catalogue",
                                           "not_dense_over_budget"))
