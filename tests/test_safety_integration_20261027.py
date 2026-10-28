"""Fail-closed regressions for the 27 October forensic integration review."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
import refresh_feed  # noqa: E402
import submission_writer  # noqa: E402
import validate_submission  # noqa: E402
from gems import submission  # noqa: E402


def make_raster(path: Path, data: np.ndarray, *, nodata=None, mask=None, internal=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=internal):
        with rasterio.open(path, "w", driver="GTiff", width=data.shape[1], height=data.shape[0],
                           count=1, dtype="float32", crs="EPSG:32611",
                           transform=from_origin(243350, 4508550, 100, 100), nodata=nodata) as ds:
            ds.write(data.astype("float32"), 1)
            if mask is not None:
                ds.write_mask(mask.astype("uint8"))
    return path


@pytest.fixture
def rasters(tmp_path):
    footprint = np.ones((8, 8), dtype=bool)
    footprint[0, :] = False
    ref = np.where(footprint, 0.0, np.nan).astype("float32")
    prediction = np.zeros((8, 8), dtype="float32")
    prediction[3, 3] = 1.0
    sample = make_raster(tmp_path / "data/bridge/sample_submission.tif", ref)
    return footprint, sample, prediction


def test_nodata_zero_masks_zero_predictions_and_must_fail(rasters, tmp_path):
    fp, sample, prediction = rasters
    bad = make_raster(tmp_path / "nodata-zero.tif", prediction, nodata=0)
    with rasterio.open(bad) as ds:
        assert submission.raster_mask_report(ds, fp) == {
            "masked_inside_footprint": int(fp.sum()) - 1,
            "inside_all_valid": False, "self_contained": True, "external_dependency_names": []}
    with pytest.raises(ValueError, match="masked values"):
        submission_writer.read_prediction(bad, sample)


def test_valid_zeros_and_exterior_mask_are_allowed(rasters, tmp_path):
    fp, sample, prediction = rasters
    mask = np.where(fp, 255, 0)
    valid = make_raster(tmp_path / "internal-valid.tif", prediction, mask=mask, internal=True)
    with rasterio.open(valid) as ds:
        info = submission.raster_mask_report(ds, fp)
    assert info["inside_all_valid"] and info["self_contained"]
    np.testing.assert_array_equal(submission_writer.read_prediction(valid, sample), prediction)
    with pytest.raises(ValueError, match="nonempty, grid-aligned"):
        with rasterio.open(valid) as ds:
            submission.raster_mask_report(ds, np.zeros_like(fp))


def test_internal_mask_and_external_sidecar_fail_closed(rasters, tmp_path):
    fp, sample, prediction = rasters
    mask = np.full(fp.shape, 255, dtype="uint8")
    mask[2, 2] = 0
    internal = make_raster(tmp_path / "internal-invalid.tif", prediction, mask=mask, internal=True)
    with rasterio.open(internal) as ds:
        info = submission.raster_mask_report(ds, fp)
    assert info["masked_inside_footprint"] == 1 and info["self_contained"]
    with pytest.raises(ValueError, match="masked values"):
        submission_writer.read_prediction(internal, sample)
    sidecar = make_raster(tmp_path / "external-mask.tif", prediction, mask=np.full(fp.shape, 255), internal=False)
    with rasterio.open(sidecar) as ds:
        info = submission.raster_mask_report(ds, fp)
    assert info["inside_all_valid"] and not info["self_contained"]
    assert info["external_dependency_names"] == ["external-mask.tif.msk"]
    with pytest.raises(ValueError, match="sidecar"):
        submission_writer.read_prediction(sidecar, sample)


def test_masked_numpy_input_cannot_be_silently_converted(rasters, tmp_path):
    fp, sample, prediction = rasters
    masked = np.ma.array(prediction, mask=np.zeros(fp.shape, dtype=bool))
    masked.mask[2, 2] = True
    with pytest.raises(ValueError, match="masked pixels"):
        submission.write_submission(masked, sample, tmp_path / "out.tif")


def test_common_cli_rejects_shared_false_pass_and_absent_reference(monkeypatch, rasters, tmp_path):
    fp, sample, prediction = rasters
    bad = make_raster(tmp_path / "nodata-zero.tif", prediction, nodata=0)
    monkeypatch.setattr(validate_submission, "ROOT", tmp_path)
    sha = hashlib.sha256(sample.read_bytes()).hexdigest()
    manifest = tmp_path / "registry/data_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"files": [{"dest": "sample_submission.tif", "sha256": sha}]}))
    monkeypatch.setattr(validate_submission, "SHAPE", fp.shape)
    # Isolate the known upstream false positive: the integration must reject it
    # even if both unchanged shared validators return success.
    monkeypatch.setattr(validate_submission, "validate_shared", lambda *a, **k: {
        "all_checks_passed": True, "checks": {}, "min": 0, "max": 1,
        "n_nan": 0, "n_infinite": 0, "meta": {}})
    monkeypatch.setattr(validate_submission.gates, "format_report", lambda *a, **k: {"ok": True})
    result = validate_submission.check_tiff(bad)
    assert not result["all_checks_passed"]
    assert result["mask_report"]["masked_inside_footprint"] == int(fp.sum()) - 1
    sample.unlink()
    missing = validate_submission.check_tiff(bad)
    assert not missing["all_checks_passed"] and missing["mask_report"] is None
    assert not missing["mirrored_reference_available"]


def test_card_booleans_cannot_forge_selector_approval():
    card = {"verdict": "promote", "decision": {"verdict": "promote", "ok_to_submit": True,
            "eligible_for_separate_selector": True, "approved_for_weekly_slot": True},
            "registry": {"passes_literal_uniqueness": True}}
    assert validate_submission.approval_matches(card, {"all_checks_passed": True}, True) is False


def test_feed_keeps_changed_head_when_refresh_fails_and_marks_unknown(monkeypatch):
    pins = [{"repo": "owner/one", "ref": "a" * 40}, {"repo": "owner/two", "ref": "c" * 40}]
    old = [{"repo": "owner/one", "observed_head": "b" * 40, "checked_utc": "2026-10-27T01:02:03Z"}]
    def fail(*args, **kwargs):
        raise OSError("network unavailable")
    monkeypatch.setattr(refresh_feed, "fetch", fail)
    rows, errors = refresh_feed.refresh_repository_heads(pins, old, attempt=True)
    assert len(rows) == len(errors) == 2
    assert rows[0]["changed_since_audit"] is True
    assert rows[0]["checked_utc"] == old[0]["checked_utc"]
    assert rows[0]["refresh_status"] == "unavailable_last_observation_retained"
    assert rows[1]["observed_head"] is None and rows[1]["changed_since_audit"] is None
    assert rows[1]["refresh_status"] == "unavailable_no_prior"
    offline, errors = refresh_feed.refresh_repository_heads(pins, old, attempt=False)
    assert not errors and offline[0]["refresh_status"] == "not_attempted_last_observation_retained"
    assert offline[1]["refresh_status"] == "not_attempted_no_prior"


def test_feed_fresh_observation_replaces_stale_without_inventing_success(monkeypatch):
    pins = [{"repo": "owner/one", "ref": "a" * 40}]
    monkeypatch.setattr(refresh_feed, "fetch", lambda *a, **k: json.dumps({"sha": "b" * 40}))
    monkeypatch.setattr(refresh_feed, "utc_now", lambda: "2026-10-27T01:02:03Z")
    rows, errors = refresh_feed.refresh_repository_heads(pins, [], attempt=True)
    assert errors == [] and rows[0]["refresh_status"] == "network_verified"
    assert rows[0]["changed_since_audit"] is True and rows[0]["checked_utc"] == "2026-10-27T01:02:03Z"


@pytest.mark.parametrize("script", ["run_experiments.py", "run_wbg3_experiments.py", "run_wbg3_exp3.py",
                                   "build_wbg3_submission.py", "run_wbg3_lane.py", "wbg_h1_run_experiment.py"])
def test_historical_runner_entrypoints_refuse_to_restart(script):
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT,
                          capture_output=True, text=True, timeout=20)
    assert proc.returncode != 0 and "stopped" in proc.stderr.lower()


def test_h1_sparse_only_gate_cannot_exit_success():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/wbg_h1_validate_submission.py"),
                           "missing.tif", "--check-uniqueness"], cwd=ROOT,
                          capture_output=True, text=True, timeout=20)
    assert proc.returncode != 0
    result = json.loads(proc.stdout)
    assert result["uniqueness_cleared"] is False and result["ok_to_submit"] is False


def test_published_parallel_result_uses_measured_stop_not_projection():
    result = json.loads((ROOT / "evidence/wbg3/exp3det_safety_review_20261027.json").read_text())
    assert result["witness"]["my_dots_within_3px_of_theirs"] == 1.0
    assert result["leaderboard_estimate"] is None and result["ok_to_submit"] is False
    assert len(result["submission_note"]) <= 140
    page = (ROOT / "docs/wbg3.html").read_text()
    assert "0.21 [0.17" not in page and "100.0%" in page and "DO NOT SUBMIT" in page
    howto = (ROOT / "docs/wbg3/how-to-submit.html").read_text()
    assert "Eliminates DrivenData" not in howto and "portal_safe_local_policy" not in howto
    assert "No separate selector has been implemented" in howto


def test_writer_rejects_existing_output_sidecar(rasters, tmp_path):
    fp, sample, prediction = rasters
    target = make_raster(tmp_path / "out.tif", prediction, mask=np.full(fp.shape, 255), internal=False)
    with pytest.raises(ValueError, match="existing raster sidecars"):
        submission.write_submission(prediction, sample, target)


def test_supplied_reference_compatibility_cli_rejects_sidecar(rasters, tmp_path):
    fp, sample, prediction = rasters
    compatible = np.where(fp, prediction, np.nan)
    target = make_raster(tmp_path / "legacy.tif", compatible, nodata=np.nan,
                         mask=np.full(fp.shape, 255), internal=False)
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"),
                           str(target), str(sample)], cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert not result["all_checks_passed"] and not result["ok_to_submit"]
    assert not result["reference_report"]["mask_report"]["self_contained"]


@pytest.mark.parametrize("suffix", [".tif", ".zip"])
def test_exp3det_exact_file_cli_identifies_negative_c1_witness(suffix):
    tif = ROOT / "docs/downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif"
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"),
                           str(tif.with_suffix(suffix)), "--require-submit-ready"], cwd=ROOT,
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 2, proc.stderr
    result = json.loads(proc.stdout)
    assert result["all_checks_passed"] and result["run_card_matches_exact_tiff"]
    assert result["promotion_verdict"] == "negative" and not result["ok_to_submit"]
    assert result["known_negative_registry_overlap"] == 1.0


def test_writer_cli_rejects_unpinned_reference_before_writing(rasters, tmp_path):
    _, sample, prediction = rasters
    source = tmp_path / "source.npy"
    np.save(source, prediction)
    output = tmp_path / "out.tif"
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/submission_writer.py"), str(source),
                           str(output), "--template", str(sample)], cwd=ROOT,
                          capture_output=True, text=True, timeout=20)
    assert proc.returncode != 0 and "pinned owner mirror" in proc.stderr
    assert not output.exists()


def test_tip1_and_h1_spent_modes_remain_closed():
    for args in (["run_tip1_lane.py"], ["wbg_h1_evaluate_holdout.py", "--canary"],
                 ["wbg_h1_evaluate_holdout.py", "--run-wbg-h1"], ["generate_focus9_unique_tif.py"]):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / args[0]), *args[1:]],
                              cwd=ROOT, capture_output=True, text=True, timeout=20)
        assert proc.returncode != 0 and "stopped" in proc.stderr.lower()


def test_focus9_current_receipt_corrects_frozen_decoded_identity_and_stops():
    card = json.loads((ROOT / "evidence/focus9_exec/run_card.json").read_text())
    audit = json.loads((ROOT / "evidence/focus9_exec/safety_review_20261028.json").read_text())
    assert audit["raster_sha256"] == card["raster_sha256"]
    assert audit["candidate_decoded_sha256"] != card["raster_decoded_sha256"]
    assert audit["witness"]["my_dots_within_3px_of_theirs"] == 1.0
    assert audit["witness"]["duplicate_by_overlap"] is True
    assert audit["holdout"]["dti"] is None and audit["leaderboard_estimate"] is None
    assert audit["historical_hash_table_check"]["not_a_surface_or_dot_novelty_audit"]
    assert audit["verdict"] == "negative" and not audit["ok_to_submit"]


def test_focus9_published_page_uses_current_safety_not_unmeasured_projection():
    html = (ROOT / "docs/focus9-executive-summary.html").read_text()
    assert "100%" in html and "Not measured" in html and "SUBMIT: NO" in html
    assert "expected PASS" not in html and "HOLDOUT-DTI ≈0.0003" not in html
    assert "focus9-safety-20261028.json" in html
    assert "scripts/audit_registry.py --candidate" not in html
