"""Actual-file CLI checks, including negative approval and malformed inputs."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "registry/run_card.json").read_text())


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def cli(file, *flags):
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
    return subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"), *flags, str(file)],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)


@pytest.mark.parametrize("suffix,flags,code", [(".tif", (), 0), (".zip", (), 0),
    (".tif", ("--require-submit-ready",), 2), (".zip", ("--require-submit-ready",), 2)])
def test_actual_tiff_and_zip_cli_format_pass_is_never_submission_approval(suffix, flags, code):
    result = cli((ROOT / CARD["artifact"]).with_suffix(suffix), *flags)
    assert result.returncode == code, result.stderr
    report = json.loads(result.stdout)
    assert report["all_checks_passed"]
    assert report["sha256"] == CARD["raster_sha256"]
    assert report["run_card_matches_exact_tiff"]
    assert report["promotion_verdict"] == "negative"
    assert not report["ok_to_submit"]
    assert not report["independent_organizer_origin_authenticated"]


@pytest.mark.parametrize("kind", ["garbage_tiff", "bad_zip", "two_tiffs", "non_tiff", "wrong_extension"])
def test_cli_malformed_inputs_fail_closed_with_machine_readable_error(tmp_path, kind):
    path = tmp_path / ("bad.zip" if kind in ("bad_zip", "two_tiffs", "non_tiff") else "bad.txt" if kind == "wrong_extension" else "bad.tif")
    if kind in ("two_tiffs", "non_tiff"):
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("a.tif" if kind == "two_tiffs" else "notes.txt", b"not a raster")
            if kind == "two_tiffs":
                z.writestr("b.tif", b"not a raster")
    else:
        path.write_text("not an image")
    result = cli(path)
    assert result.returncode == 1
    report = json.loads(result.stderr)
    assert not report["all_checks_passed"] and not report["ok_to_submit"]
    assert report["error"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.01, 1.01])
def test_shared_validator_rejects_bad_pixel_values_without_repair(tmp_path, value):
    from gems57.validate import validate
    with rasterio.open(ROOT / CARD["artifact"]) as src:
        profile = src.profile
    a = np.zeros((profile["height"], profile["width"]), dtype=np.float32)
    a[50, 50] = value
    path = tmp_path / "malformed-range.tif"
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(a, 1)
    report = validate(path)
    assert not report["all_checks_passed"]
    with rasterio.open(path) as src:
        actual = src.read(1)[50, 50]
    assert np.isnan(actual) if np.isnan(value) else actual == np.float32(value)


def test_accidentally_flipping_one_flag_cannot_approve_negative_artifact():
    validator = module("validate_submission")
    card = copy.deepcopy(CARD)
    card["decision"]["ok_to_submit"] = True
    assert not validator.approval_matches(card, {"all_checks_passed": True}, True)
    assert not validator.approval_matches(None, {"all_checks_passed": True}, True)
    assert not validator.approval_matches(card, {"all_checks_passed": False}, True)
    assert not validator.approval_matches(card, {"all_checks_passed": True}, False)


def test_stopped_experiment_refuses_to_prepare_data_or_train(monkeypatch):
    experiment = module("run_experiment")
    monkeypatch.setattr(experiment, "prepare", lambda: pytest.fail("stopped experiment attempted a new preparation"))
    with pytest.raises(SystemExit, match="already started"):
        experiment.main()


def test_legacy_supplied_reference_cli_is_preserved_but_never_approves(tmp_path):
    from rasterio.transform import from_origin
    reference, candidate = tmp_path / "reference.tif", tmp_path / "candidate.tif"
    profile = dict(driver="GTiff", height=4, width=5, count=1, dtype="float32",
        crs="EPSG:32611", transform=from_origin(400000, 4500000, 100, 100), nodata=np.nan)
    for path, value in ((reference, 0.), (candidate, .25)):
        a = np.full((4, 5), value, dtype=np.float32)
        a[0, 0] = np.nan
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(a, 1)
    result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"),
        str(candidate), str(reference), "--require-submit-ready"], cwd=ROOT,
        text=True, capture_output=True, timeout=30)
    assert result.returncode == 2, result.stderr
    report = json.loads(result.stdout)
    assert report["reference_report"]["ok"] and report["all_checks_passed"]
    assert report["ok_to_submit"] is False
    assert "compatibility" in report["compatibility_mode"] or "inherited" in report["compatibility_mode"]
