"""Tests for WBG-2: metric fidelity, validator, prior determinism, uniqueness gate."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from wbg2 import prior as P
from wbg2 import uniqueness as U
from wbg2 import validate as V
from wbg2.metric import ALPHA, BETA, EPS, R_PIXELS, dti, triangular_kernel
from wbg2 import verification

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------- metric fidelity
def test_organizer_worked_example_arithmetic():
    """The organizer publishes TP_w=3.00, FP_w=1.89, FN_w=2.00 -> DTI 0.60."""
    res = verification.organizer_arithmetic()
    assert res["value"] == pytest.approx(0.60, abs=5e-3)


def test_brute_force_agrees_with_fast_path():
    res = verification.random_cross_check(trials=12)
    assert res["max_abs_difference"] < 1e-12


def test_known_kernel_values():
    kv = verification.known_values()
    assert kv["exact_hit"] == pytest.approx(1.0, abs=1e-8)
    assert kv["one_pixel_off"] == pytest.approx(2.0 / 3.0, abs=1e-8)
    assert kv["three_pixels_off"] == 0.0
    assert triangular_kernel(np.array([1.0]))[0] == pytest.approx(2.0 / 3.0)
    assert triangular_kernel(np.array([3.0]))[0] == 0.0


def test_full_verification_suite_passes():
    assert verification.run_all()["all_pass"] is True


def test_metric_constants_match_organizer():
    assert ALPHA == 0.2 and BETA == 0.8
    assert R_PIXELS == 3.0
    assert EPS > 0


def test_metric_shape_mismatch_raises():
    with pytest.raises(ValueError):
        dti(np.zeros((4, 4)), np.zeros((4, 5), dtype=bool))


def test_perfect_prediction_scores_one():
    g = np.zeros((20, 20), dtype=bool)
    g[5:15, 10] = True
    p = g.astype(np.float32)
    assert dti(p, g) == pytest.approx(1.0, abs=1e-6)


def test_empty_prediction_scores_zero():
    g = np.zeros((10, 10), dtype=bool)
    g[3, 3] = True
    assert dti(np.zeros((10, 10), np.float32), g) == 0.0


# ------------------------------------------------------------------- placement
def test_catalogue_buffer_is_a_manhattan_diamond_not_a_disc():
    m = np.zeros((21, 21), dtype=bool)
    m[10, 10] = True
    b = P.catalogue_buffer(m, 4)
    assert b[10, 14] and b[10, 6] and b[14, 10]
    assert not b[10, 16]
    assert not b[13, 12]  # sqrt(13) pixels < 4, but Manhattan distance 5
    assert P.catalogue_buffer(m, 0).sum() == 0


def test_placement_is_deterministic_and_on_admissible_cells():
    rng = np.random.default_rng(0)
    allowed = np.zeros((40, 40), dtype=bool)
    allowed[5:35, 5:35] = True
    inten = rng.random((40, 40)).astype(np.float32)
    a = P.place(inten, allowed, 100, seed=7)
    b = P.place(inten, allowed, 100, seed=7)
    assert np.array_equal(a, b)
    assert allowed[a[:, 0], a[:, 1]].all()
    assert len({tuple(r) for r in a.tolist()}) == len(a)


def test_placement_rejects_empty_admissible_set():
    with pytest.raises(ValueError):
        P.place(np.ones((5, 5), np.float32), np.zeros((5, 5), bool), 3, seed=1)


def test_density_prior_is_bounded():
    m = np.zeros((30, 30), dtype=bool)
    m[15, 10:20] = True
    d = P.density_prior(m, 3.0)
    assert d.max() == pytest.approx(1.0)
    assert d.min() >= 0.0
    assert d[15, 10:20].min() > 0.0


# -------------------------------------------------------------------- validator
@pytest.mark.parametrize("legacy", [V.validate_tif, V.validate_zip])
def test_legacy_private_validator_is_disabled(legacy):
    with pytest.raises(RuntimeError, match="disabled"):
        legacy("anything")


def test_shared_validator_rejects_shift_and_nonfinite_exterior(tmp_path, monkeypatch):
    import rasterio
    from rasterio.transform import from_origin
    from gems57 import validate as shared

    transform = from_origin(243350, 4508550, 100, 100)
    monkeypatch.setattr(shared, "HEIGHT", 20)
    monkeypatch.setattr(shared, "WIDTH", 20)
    monkeypatch.setattr(shared, "TRANSFORM", transform)
    path = tmp_path / "test.tif"
    footprint = np.ones((20, 20), dtype=bool)
    footprint[0, 0] = False
    arr = np.zeros((20, 20), np.float32)

    def write(t):
        with rasterio.open(path, "w", driver="GTiff", height=20, width=20, count=1,
                           dtype="float32", crs="EPSG:32611", transform=t) as dst:
            dst.write(arr, 1)

    write(transform)
    assert shared.validate(path, footprint)["all_checks_passed"]
    write(from_origin(243450, 4508550, 100, 100))
    assert not shared.validate(path, footprint)["checks"]["transform_matches_sample_submission"]
    arr[0, 0] = np.nan
    write(transform)
    assert not shared.validate(path, footprint)["checks"]["no_nan_anywhere"]
    arr[0, 0] = 0
    arr[5, 5] = 1.01
    write(transform)
    assert not shared.validate(path, footprint)["checks"]["range_0_1_guaranteed"]


# ------------------------------------------------------------------- uniqueness
def test_legacy_enrichment_exemption_is_disabled():
    with pytest.raises(RuntimeError, match="disabled"):
        U.compare(np.zeros((5, 5)), np.ones((5, 5)))


def test_shared_literal_gate_stops_dense_field_and_shifted_grid(tmp_path):
    import rasterio
    from rasterio.transform import from_origin
    from gems57 import uniqueness as shared

    tr = from_origin(243350, 4508550, 100, 100)
    ours = np.zeros((20, 20), np.float32)
    ours[4, 4] = ours[15, 15] = 1
    dense = np.full((20, 20), .5, np.float32)
    paths = [tmp_path / "ours.tif", tmp_path / "dense.tif", tmp_path / "shifted.tif"]
    for path, values, transform in zip(paths, [ours, dense, dense],
                                       [tr, tr, from_origin(243450, 4508550, 100, 100)]):
        with rasterio.open(path, "w", driver="GTiff", height=20, width=20, count=1,
                           dtype="float32", crs="EPSG:32611", transform=transform) as dst:
            dst.write(values, 1)
    mask = np.ones((20, 20), bool)
    with rasterio.open(paths[0]) as src:
        grid = (src.shape, src.crs, src.transform)
    good = shared.compare_to_registry(paths[0], [{"file": str(paths[1])}], mask, expected_grid=grid)
    assert good["stop_required"] and not good["unique"]
    assert good["rows"][0]["my_dots_within_3px_of_theirs"] == 1.0
    assert good["rows"][0]["duplicate_by_overlap"]
    bad = shared.compare_to_registry(paths[0], [{"file": str(paths[2])}], mask, expected_grid=grid)
    assert bad["stop_required"] and not bad["unique"]
    assert "error" in bad["rows"][0]


# ------------------------------------------------------------- shipped artifacts
def test_run_card_is_a_negative_decision_with_pinned_reproducible_witness():
    card = json.loads((ROOT / "evidence/wbg2/run_card.json").read_text())
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["validator_output"]["all_checks_passed"]
    assert card["validator_output"]["zip_exact_single_identical_tiff"]
    assert not card["registry"]["passes_literal_uniqueness"]
    assert card["registry"]["rows"][0]["forward_overlap_within_3px"] == pytest.approx(0.9989722222)
    assert card["registry"]["rows"][0]["duplicate_by_overlap"]
    assert card["registry"]["rows"][1]["forward_overlap_within_3px"] == 1.0
    assert card["holdout"]["value"] is None and card["leaderboard_estimate"] is None
    assert card["new_experiments"] == card["new_rasters_generated"] == card["submission_slots_used"] == 0
    assert len(card["submission_note"]) <= 140


def test_nine_site_legacy_audit_is_not_a_uniqueness_approval():
    nine = json.loads((ROOT / "evidence/wbg2/nine_site_uniqueness.json").read_text())
    assert nine["n_audited"] == 9
    assert "PARTIAL" in nine["verdict"]
    assert all("USER-REPORTED" in r["score_evidence_class"] for r in nine["rows"])
    assert any("not all site rasters" in issue for issue in nine["limitations"])


def test_calibration_is_explicitly_withdrawn():
    cal = json.loads((ROOT / "registry/wbg2_calibration.json").read_text())
    assert cal["n_observations"] == 9
    assert "SUPERSEDED" in cal["status"]
    assert "not a defensible prediction interval" in cal["additional_caveat"]


def test_stopped_entry_points_fail_without_modifying_candidate():
    import hashlib
    import subprocess
    import sys
    tif = ROOT / "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif"
    before = hashlib.sha256(tif.read_bytes()).hexdigest()
    for script in ("build_wbg2_submission.py", "wbg2_nine_site_audit.py"):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], capture_output=True, text=True)
        assert result.returncode == 2 and "STOP" in result.stderr
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == before


def test_full_audit_card_comparison_rejects_semantic_drift():
    from scripts.review_wbg2 import compare_documents
    baseline = {"verdict": "negative", "registry": {"overlap": 0.998972222222, "pass": False}}
    compare_documents(baseline, {"verdict": "negative", "registry": {"overlap": 0.998972222223, "pass": False}})
    with pytest.raises(ValueError, match="drift"):
        compare_documents(baseline, {"verdict": "negative", "registry": {"overlap": 0.998972222222, "pass": True}})
    with pytest.raises(ValueError, match="drift"):
        compare_documents(baseline, {"verdict": "negative", "registry": {"overlap": 0.998972222222}})
