"""Tests for WBG-2: metric fidelity, validator, prior determinism, uniqueness gate."""

from __future__ import annotations

import json
import zipfile
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
def test_catalogue_buffer_excludes_a_disc():
    m = np.zeros((21, 21), dtype=bool)
    m[10, 10] = True
    b = P.catalogue_buffer(m, 4)
    assert b[10, 14] and b[10, 6] and b[14, 10]
    assert not b[10, 16]
    assert P.catalogue_buffer(m, 0).sum() == 0


def test_historic_buffer_is_four_connected_not_a_euclidean_400m_disc():
    m = np.zeros((21, 21), dtype=bool)
    m[10, 10] = True
    b = P.catalogue_buffer(m, 4)
    assert b[12, 12]  # four Manhattan steps, inside 3 Euclidean pixels
    assert not b[13, 12]  # sqrt(13) < 4 but five Manhattan steps


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
def test_validator_rejects_wrong_grid(tmp_path):
    import rasterio

    p = tmp_path / "bad.tif"
    with rasterio.open(
        p, "w", driver="GTiff", height=10, width=10, count=1, dtype="float32",
        crs="EPSG:32611", transform=rasterio.transform.from_origin(0, 0, 100, 100),
    ) as dst:
        dst.write(np.zeros((10, 10), np.float32), 1)
    rep = V.validate_tif(str(p))
    assert rep.all_checks_passed is False
    assert "shape_matches" in rep.errors


def test_validator_detects_nan_mode(tmp_path):
    import rasterio

    p = tmp_path / "nan.tif"
    tr = rasterio.transform.from_origin(243350, 4508550, 100, 100)
    a = np.zeros((3730, 3292), np.float32)
    a[0, 0] = np.nan
    with rasterio.open(
        p, "w", driver="GTiff", height=3730, width=3292, count=1, dtype="float32",
        crs="EPSG:32611", transform=tr,
    ) as dst:
        dst.write(a, 1)
    rep = V.validate_tif(str(p))
    assert rep.mode == "nan"
    assert rep.all_checks_passed is False


def test_zip_validator_requires_single_identical_member(tmp_path):
    import rasterio

    tr = rasterio.transform.from_origin(243350, 4508550, 100, 100)
    tif = tmp_path / "x.tif"
    with rasterio.open(
        tif, "w", driver="GTiff", height=8, width=8, count=1, dtype="float32",
        crs="EPSG:32611", transform=tr,
    ) as dst:
        dst.write(np.ones((8, 8), np.float32), 1)
    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as z:
        z.write(tif, arcname="x.tif")
    assert V.validate_zip(str(good), str(tif))["all_checks_passed"] is True

    two = tmp_path / "two.zip"
    with zipfile.ZipFile(two, "w") as z:
        z.write(tif, arcname="x.tif")
        z.write(tif, arcname="y.tif")
    assert V.validate_zip(str(two), str(tif))["all_checks_passed"] is False


# -------------------------------------------------------- literal uniqueness

def test_retired_private_gate_can_never_approve():
    with pytest.raises(RuntimeError, match="Retired unsafe WBG-2 gate"):
        U.compare(np.ones((5, 5)), np.ones((5, 5)))
    with pytest.raises(RuntimeError, match="Retired unsafe WBG-2 gate"):
        U.scan_registry([])


def test_shared_gate_uses_literal_euclidean_support_even_for_dense_references():
    from gems57.uniqueness import dot_overlap

    candidate = np.zeros((15, 15), np.float32)
    candidate[7, 10] = 1  # exactly three Euclidean pixels from the prior
    candidate[9, 10] = 1  # sqrt(13) > 3 pixels
    reference = np.zeros_like(candidate)
    reference[7, 7] = .5
    assert dot_overlap(candidate, reference) == pytest.approx(.5)
    assert dot_overlap(candidate, np.full_like(candidate, .5)) == 1.0


def test_stopped_generator_cli_creates_nothing(tmp_path):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_wbg2_submission.py")],
                            cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "STOP" in result.stderr and "DO NOT SUBMIT" in result.stderr
    assert not list(tmp_path.iterdir())


# ------------------------------------------------------------- shipped artifacts

def test_run_card_is_consistent_with_stopped_shipped_file():
    card = json.loads((ROOT / "evidence/wbg2/run_card.json").read_text())
    for key in ("hypothesis", "mechanism", "named_non_fault_mimic", "holdout",
                "raster_sha256", "score_estimate", "registry", "validator", "decision"):
        assert key in card
    assert card["verdict"] == "negative"
    assert card["decision"]["ok_to_download"] is True
    assert card["decision"]["ok_to_submit"] is False
    assert card["decision"]["approved_for_weekly_slot"] is False
    assert card["decision"]["submission_slots_used"] == 0
    assert card["validator"]["tif"]["all_checks_passed"] is True
    assert card["validator"]["zip"]["all_checks_passed"] is True
    assert card["validator"]["tif"]["report"]["template_report"]["ok"] is True
    assert card["validator"]["zip"]["report"]["run_card_matches_exact_tiff"] is True
    assert card["catalogue_buffer_diagnostic"]["dots_less_than_400m_euclidean"] == 813
    assert card["catalogue_buffer_diagnostic"]["dots_at_or_within_300m_euclidean"] == 0
    assert card["score_estimate"]["value"] is None
    assert card["holdout"]["pooled_dti"] is None
    assert card["registry"]["passes_literal_uniqueness"] is False
    assert card["registry"]["existing_final_dots"]["my_dots_within_3px_of_theirs"] > .70
    assert card["registry"]["surface_retrospective"]["my_dots_within_3px_of_theirs"] > .70
    assert 0 < len(card["submission_note"]) <= 140


def test_nine_site_diagnostics_do_not_override_lattice_witness():
    nine = json.loads((ROOT / "evidence/wbg2/nine_site_uniqueness.json").read_text())
    audit = json.loads((ROOT / "evidence/wbg2/safety_audit_20261027.json").read_text())
    assert nine["n_audited"] == len(nine["rows"]) == 9
    assert "negative" in nine["overall_verdict"]
    assert audit["passed_literal_gate"] is False and audit["ok_to_submit"] is False
    assert audit["surface_phase"].startswith("Retrospective")
    assert len(audit["nine_champion_diagnostics"]) == 9
    for row, measured in zip(nine["rows"], audit["nine_champion_diagnostics"]):
        assert row["site"] == measured["site"]
        assert row["sha256"] == measured["sha256"]
        assert row["forward_3px_overlap"] == measured["my_dots_within_3px_of_theirs"]
        assert "USER-REPORTED" in row["value_evidence_class"]


def test_calibration_is_quarantined_not_a_ranking_or_forecast():
    cal = json.loads((ROOT / "registry/wbg2_calibration.json").read_text())
    assert "INVALID" in cal["superseded_warning"]
    assert cal["historical_fit"]["n_observations"] == 9
    assert "history" in cal["superseded_warning"].lower() or "historical" in cal["superseded_warning"].lower()


def test_verifier_fails_closed_by_default_and_checks_the_negative_decision():
    import subprocess
    import sys
    script = str(ROOT / "scripts/verify_wbg2_download.py")
    for args, expected in [((), 2), (("--expect-negative",), 0)]:
        result = subprocess.run([sys.executable, script, *args], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == expected, result.stderr
        data = json.loads(result.stdout)
        assert data["negative_decision_integrity_passed"]
        assert data["local_format_passed"]
        assert data["ok_to_submit"] is False
        assert data["sha256"] == "f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3"


def test_verifier_rejects_accidental_approval_flag(tmp_path, monkeypatch):
    import importlib.util
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("verify_wbg2_download", ROOT / "scripts/verify_wbg2_download.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    card = json.loads((ROOT / "evidence/wbg2/run_card.json").read_text())
    card["decision"]["ok_to_submit"] = True
    path = tmp_path / "evidence/wbg2/run_card.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(card))
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    result = verifier.verify()
    assert result["checks"]["card_negative_and_not_submit"] is False
    assert result["negative_decision_integrity_passed"] is False
    assert result["ok_to_submit"] is False


@pytest.mark.parametrize("field", ["historical_score", "overlap", "approval"])
def test_site_builder_rejects_inconsistent_evidence_before_writing(tmp_path, monkeypatch, field):
    import copy
    import importlib.util
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("build_wbg2_site", ROOT / "scripts/build_wbg2_site.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    original = builder.load

    def altered(path):
        data = copy.deepcopy(original(path))
        if path == "evidence/wbg2/nine_site_uniqueness.json":
            if field == "historical_score":
                data["rows"][0]["user_reported_historical_value"] = .9999
            if field == "overlap":
                data["rows"][0]["forward_3px_overlap"] = 0.0
        if path == "evidence/wbg2/run_card.json" and field == "approval":
            data["decision"]["ok_to_submit"] = True
        return data

    monkeypatch.setattr(builder, "load", altered)
    monkeypatch.setattr(builder, "DOCS", tmp_path)
    with pytest.raises(ValueError):
        builder.build()
    assert not list(tmp_path.iterdir())
