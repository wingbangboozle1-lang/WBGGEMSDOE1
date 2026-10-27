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


# ------------------------------------------------------------------- uniqueness
def test_enrichment_is_one_for_independent_dense_field():
    """A dense surface must not be reported as a duplicate."""
    ours = np.zeros((200, 200), np.float32)
    rng = np.random.default_rng(1)
    idx = rng.choice(200 * 200, 500, replace=False)
    ours.ravel()[idx] = 1.0
    dense = np.ones((200, 200), np.float32) * 0.5
    c = U.compare(ours, dense)
    assert c["forward_overlap"] == 1.0
    assert c["enrichment"] == pytest.approx(1.0, abs=1e-6)


def test_enrichment_flags_a_copy():
    a = np.zeros((200, 200), np.float32)
    a[50:150, 100] = 1.0
    c = U.compare(a, a.copy())
    assert c["forward_overlap"] == pytest.approx(1.0)
    assert c["enrichment"] > U.STOP_ENRICHMENT
    assert c["rho"] > U.STOP_RHO


# ------------------------------------------------------------- shipped artifacts
def test_run_card_is_consistent_with_shipped_file():
    card = json.loads((ROOT / "evidence/wbg2/run_card.json").read_text())
    for key in ("raster_sha256", "score_estimate", "registry", "validator", "decision"):
        assert key in card
    assert card["decision"]["ok_to_submit"] is True
    assert card["validator"]["tif"]["all_checks_passed"] is True
    assert card["validator"]["zip"]["all_checks_passed"] is True
    assert card["registry"]["passes_final_dot_gate"] is True
    assert len(card["submission_note"]) <= 140


def test_nine_site_audit_is_recorded():
    nine = json.loads((ROOT / "evidence/wbg2/nine_site_uniqueness.json").read_text())
    assert nine["n_audited"] == 9
    assert nine["max_enrichment_vs_chance"] < U.STOP_ENRICHMENT
    assert nine["max_abs_spearman"] < U.STOP_RHO
    assert nine["verdict"].startswith("UNIQUE")


def test_calibration_is_documented_and_honest():
    cal = json.loads((ROOT / "registry/wbg2_calibration.json").read_text())
    assert cal["n_observations"] == 9
    assert 0.9 < cal["r2"] <= 1.0
    assert any("receipt" in c for c in cal["caveats"])
    assert cal["collinearity"]["corr_near3cat_logbudget"] > 0.5
