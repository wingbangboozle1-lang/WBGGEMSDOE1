import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

from gems import holdout, submission

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "evidence/tip1_run_card_20261026.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_tip1_frozen_receipt_and_pooled_holdouts():
    card = json.loads(CARD_PATH.read_text())
    assert card["schema"] == "gemsdoe1-tip1-run-card-v1"
    assert card["experiments_run"] == 3
    assert card["elapsed_seconds"] <= 7200
    assert card["submission_slots_used"] == 0
    assert card["verdict"] == "negative"
    assert card["promote"] is card["ok_to_submit"] is False
    assert card["leakage_canary"]["passed"] is True
    assert card["leakage_canary"]["n_features_checked"] == 29
    assert card["arms"]["B"]["fixed_role"].startswith("primary")
    for arm in ("A", "B", "C"):
        result = card["arms"][arm]["holdout"]
        assert result["label"] == "HOLDOUT-DTI"
        assert result["evaluator_version"] == "gems-segment-pooled-v1"
        assert result["n_withheld_positive_pixels"] == 60988
        pooled = holdout.pooled_components(result["folds"])
        np.testing.assert_allclose(result["dti"], pooled["dti"], rtol=1e-12, atol=1e-10)


def test_exact_download_reopens_and_matches_complete_validator():
    card = json.loads(CARD_PATH.read_text())
    artifact = ROOT / "docs/downloads" / card["submission_name"]
    assert sha256(artifact) == card["raster_sha256"]
    with rasterio.open(artifact) as dataset:
        values = dataset.read(1)
        assert dataset.count == 1
        assert dataset.dtypes == ("float32",)
        assert dataset.crs.to_epsg() == 32611
    assert np.isfinite(values).all()
    assert values.min() >= 0 and values.max() <= 1
    current = submission.check_variants(artifact, TEMPLATE)
    assert submission.matches_frozen_validation(current, card["validator_output"])
    assert current["checks"]["footprint_gdal_mask_valid"]["pass"]
    assert current["checks"]["single_file_self_contained"]["pass"]
    assert card["validator_output"]["format_valid"] is True
    assert card["validator_output"]["checks"][
        "variant_strict_whole_array_no_nan_allowed"
    ]["pass"] is True


def test_nine_site_claims_are_not_upgraded_without_receipts():
    summary = json.loads(
        (ROOT / "evidence/nine_site_executive_summary_20261026.json").read_text()
    )
    assert len(summary["sites"]) == 9
    assert all(
        row["score_evidence_label"] == "OWNER-REPORTED / UNVERIFIED"
        and row["organizer_receipt_present"] is False
        and row["recommendation"] == "DO NOT SUBMIT"
        for row in summary["sites"]
    )
    h33 = next(row for row in summary["sites"] if row["site"] == "GEMSDOE32")
    assert h33["reported_value"] == 0.2778
    assert summary["h33_b2_explanation"]["exact_ancestry"]["removed_parent_dots"] == 6436
    assert summary["h33_b2_explanation"]["exact_ancestry"]["added_dots"] == 0


def test_registry_manifest_retains_literal_lattice_and_has_no_rejections():
    registry = json.loads((ROOT / "registry/registry.json").read_text())
    assert registry["source_rows"] == 231
    assert registry["unique_rasters"] == 179
    assert registry["rejected_count"] == 0
    assert registry["retained_spacing_5_lattice_present"] is True
    controls = [
        row
        for row in registry["entries"]
        if row["comparator_role"] == "retained_spacing_5_calibration_control"
    ]
    assert len(controls) == 1
