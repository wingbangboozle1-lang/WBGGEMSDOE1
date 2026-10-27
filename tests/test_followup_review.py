"""Follow-up integrity, evidence-label and export-wrapper regression checks."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_raster(path, transform, crs="EPSG:32611", count=1):
    with rasterio.open(path, "w", driver="GTiff", width=5, height=4, count=count,
                       dtype="float32", crs=crs, transform=transform) as ds:
        ds.write(np.zeros((count, 4, 5), np.float32))


@pytest.mark.parametrize("mismatch", ["transform", "crs", "count"])
def test_integration_writer_rejects_discarding_source_georeferencing(tmp_path, mismatch):
    writer = module("submission_writer")
    template = tmp_path / "template.tif"
    source = tmp_path / "source.tif"
    tr = from_origin(243350, 4508550, 100, 100)
    write_raster(template, tr)
    write_raster(source, from_origin(243450, 4508550, 100, 100) if mismatch == "transform" else tr,
                 crs="EPSG:4326" if mismatch == "crs" else "EPSG:32611",
                 count=2 if mismatch == "count" else 1)
    with pytest.raises(ValueError, match="match|one band"):
        writer.read_prediction(source, template)


def test_integration_writer_accepts_aligned_geotiff_and_requires_reference(tmp_path):
    writer = module("submission_writer")
    source = tmp_path / "source.tif"
    write_raster(source, from_origin(243350, 4508550, 100, 100))
    assert writer.read_prediction(source, source).shape == (4, 5)
    with pytest.raises(ValueError, match="reference template"):
        writer.read_prediction(source)


@pytest.mark.parametrize("clobber", ["input", "template", "receipt"])
def test_writer_refuses_to_clobber_input_template_or_output(tmp_path, monkeypatch, clobber):
    writer = module("submission_writer")
    source, template, output = [tmp_path / n for n in ("source.npy", "template.tif", "output.tif")]
    args = ["submission_writer.py", str(source), str(source if clobber == "input" else template if clobber == "template" else output), "--template", str(template)]
    if clobber == "receipt":
        args += ["--receipt", str(output)]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(ValueError, match="overwrite"):
        writer.main()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("outside,expected_code", [("zero", 0), ("nan", 2)])
def test_real_writer_nan_twin_never_reports_portal_safe_success(tmp_path, outside, expected_code):
    source = tmp_path / "pred.npy"
    np.save(source, np.zeros((3730, 3292), np.float32))
    output = tmp_path / "export.tif"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/submission_writer.py"),
                             str(source), str(output), "--outside", outside],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == expected_code, result.stderr
    report = json.loads(result.stdout)
    assert report["portal_safe_local_policy"] is (outside == "zero")
    assert report["submission_authorized"] is False


def test_all_four_current_releases_reopen_but_none_is_submission_ready():
    review = module("build_portfolio_review").build_review()
    assert review["format_integrity_passed"]
    assert len(review["rows"]) == 4
    assert review["experiments_started"] == review["submission_slots_used"] == 0
    assert not review["ok_to_submit"]
    for row in review["rows"]:
        assert row["validation"]["passed"]
        assert all(row["validation"]["checks"].values())
        assert row["decoded_distinct_among_four_releases"]
        assert row["leaderboard_estimate"] is row["organizer_confirmed_score"] is None
        assert row["verdict"] == "negative" and row["ok_to_submit"] is False
        assert row["holdout"]["evidence_class"] == "HOLDOUT-DTI"
        assert len(row["holdout"]["ci95"]) == 2
        assert row["holdout"]["withheld_positive_pixels"] > 0
    dpgf = next(r for r in review["rows"] if "DPGF" in r["id"])
    assert dpgf["registry"]["literal_oneway_vs_r13_space_filling_lattice_ir_wbg1_01"] > .7


def test_published_dpgf_page_never_approves_optional_upload_or_unverified_inversion():
    for name in ("index.html", "executive-summary.html"):
        text = (ROOT / "docs/wbg-h1-dpgf1" / name).read_text()
        assert "DO NOT SUBMIT" in text
        assert "99.8035%" in text and "Literal uniqueness: FAIL" in text
        assert "Do not upload this negative result for optional testing" in text
        assert "not a validated forecast" in text
        assert "USER-REPORTED / NOT ORGANIZER-CONFIRMED" in text
        assert "inversion is not verified evidence" in text
        assert "data/run_card.json" in text


def test_readiness_reports_actual_research_artifact_and_stopped_lane():
    report = module("check_readiness").build_report()
    assert report["submission_tif_generated"]
    assert report["lane_stopped"]
    assert not report["pipeline_ready"] and not report["ok_to_submit"]
    assert report["organizer_origin_authenticated"] is False


def test_readiness_missing_ignored_data_does_not_trust_historical_receipt(tmp_path, monkeypatch):
    readiness = module("check_readiness")
    real_load = readiness.load
    monkeypatch.setattr(readiness, "load", real_load)
    monkeypatch.setattr(readiness, "ROOT", tmp_path)
    # Keep config evidence available but no ignored data/cache or actual TIFF.
    for name in ("data_manifest.json", "shared_template.json", "template_pins.json", "run_card.json", "experiment_ledger.json"):
        path = tmp_path / "registry" / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes((ROOT / "registry" / name).read_bytes())
    report = readiness.build_report()
    assert report["status"] == "BLOCKED_INPUTS"
    assert not report["inputs_integrity_verified"]
    assert not report["submission_tif_generated"]
    assert report["lane_stopped"]
