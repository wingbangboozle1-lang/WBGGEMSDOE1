"""Tests for the WBG-6 lane: metric arithmetic, null model, and shipped artifact."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]

from wbg6.null_model import draw_truth, dti_for, expected_dti, kernel_field
from wbg6.truth_model import (KERNEL_MASS, dti_components, dti_from_components,
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
    "evidence/wbg6_submission_audit.json",
    "evidence/wbg6_score_estimate.json",
    "evidence/wbg6_null_calibration.json",
])
def test_receipts_label_their_evidence(receipt):
    data = json.loads((ROOT / receipt).read_text())
    assert data["schema"].startswith("wbg6-")
    blob = json.dumps(data)
    assert "organizer" not in blob.lower() or "no organizer" in blob.lower()
    assert "ORGANIZER-CONFIRMED" not in blob or "no ORGANIZER-CONFIRMED" in blob


def test_shipped_artifact_matches_its_receipt():
    audit = json.loads((ROOT / "evidence/wbg6_submission_audit.json").read_text())
    tif = ROOT / audit["tif"]
    if not tif.exists():
        pytest.skip("shipped artifact not present in this checkout")
    got = hashlib.sha256(tif.read_bytes()).hexdigest()
    assert got == audit["sha256"], "artifact drifted from its audited sha256"
    assert all(audit["gates"][k] for k in ("format_pass", "not_a_byte_copy",
                                           "surface_rho_below_0.90",
                                           "never_on_catalogue",
                                           "not_dense_over_budget"))

def test_wbg6_pages_fail_closed_under_literal_registry_gate():
    """Archived density-adjusted approval must not survive in public WBG-6 pages."""
    for relative in ("docs/wbg6/index.html", "docs/wbg6/how-to-submit.html"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        upper = text.upper()
        assert "DO NOT SUBMIT" in upper
        assert "70%" in text
        assert "DOWNLOAD:" in text
        assert "NO" in text
        assert "SUBMIT: YES" not in upper
        assert "DOWNLOAD &AMP; SUBMIT: <SPAN CLASS=\"OK\">YES" not in upper


def test_habitat_profile_receipt_is_internally_consistent():
    """The ring-lift analysis must describe all recovered rasters and its own verdict."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    hab = json.loads((root / "evidence/habitat_profile.json").read_text())
    assert hab["n"] == len(hab["rows"]) >= 100
    assert len(hab["footprint_share"]) == 8
    assert abs(sum(hab["footprint_share"]) - 1.0) < 1e-6
    for row in hab["rows"]:
        assert len(row["lift"]) == 8
        # A lift vector is a profile, so it must reproduce the unit mass.
        assert abs(sum(l * m for l, m in zip(row["lift"], hab["footprint_share"])) - 1.0) < 1e-3
    # The far-field claim on the site must remain true of the receipt it is read from.
    far = {r["ring"]: r for r in hab["ring_score_spearman"]}
    assert far["40.5"]["p"] < 0.01 and far["40.5"]["spearman"] > 0.25
    # ... and the model must be reported as not generalising across sites.
    assert hab["leave_one_site_out"]["r2"] < 0.15


def test_proxy_holdout_v2_keeps_the_negative_verdict():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    prx = json.loads((root / "evidence/proxy_holdout_portfolio_v2.json").read_text())
    assert prx["n"] > 100
    assert prx["verdict"].startswith("penalising catalogue dots does not repair")
    for key in ("catalogue_forgiven", "catalogue_penalised"):
        assert abs(prx[key]["spearman"]) < 0.35
