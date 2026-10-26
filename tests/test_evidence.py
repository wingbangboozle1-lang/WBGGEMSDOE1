import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest
import rasterio

from gems57 import evaluate_holdout
from wbggems.audit import sha256

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def test_all_shared_template_sources_unchanged_and_verified_directly_upstream():
    pins = load("registry/shared_template.json")
    for row in pins["files"]:
        assert sha256(ROOT / row["path"]) == row["sha256"]
    upstream = load("evidence/upstream_template_verification.json")
    assert upstream["all_verified"]
    assert len(upstream["files"]) == len(pins["files"])
    assert all(row["verified"] for row in upstream["files"])


def test_cached_band_receipt_matches_all_19_template_pins():
    expected = load("registry/template_pins.json")["cached_feature_stack_reference"]["expected_band_sha256"]
    actual = load("evidence/shared_feature_cache.json")
    assert actual["count"] == 19
    assert [b["sha256"] for b in actual["bands"]] == expected
    assert actual["all_19_template_band_hashes_match"]
    assert actual["organizer_origin_authenticated"] is False


def test_preregistration_still_matches_frozen_experiment():
    exp = load("evidence/experiment.json")
    ledger = load("registry/experiment_ledger.json")
    assert exp["preregistration_sha256"] == sha256(ROOT / "registry/preregistration.json")
    assert ledger["preregistration_sha256"] == exp["preregistration_sha256"]
    assert ledger["experiments_completed"] == 1
    assert ledger["status"] == "negative_stopped"
    assert not exp["final_dots_generated"]
    assert exp["submission_slots_used"] == 0


def test_recorded_dti_and_ci_recompute_from_shared_block_terms_without_retraining():
    terms = load("evidence/block_terms.json")
    measured = load("evidence/experiment.json")["summary"]
    replay = evaluate_holdout.pooled_summary(terms, draws=1000, seed=71614,
        candidate="candidate_19band_plus_commutator_hgb")
    assert replay["evaluator_version"] == measured["evaluator_version"]
    assert replay["bootstrap"] == measured["bootstrap"]
    for name in measured["scores"]:
        expected, actual = measured["scores"][name], replay["scores"][name]
        assert actual["withheld_positive_pixels"] == expected["withheld_positive_pixels"] == 11330
        for key in ("dti", "tpw", "fpw", "fnw"):
            assert actual[key] == pytest.approx(expected[key], abs=1e-11)
        np.testing.assert_allclose(actual["ci95"], expected["ci95"], rtol=0, atol=1e-13)
    assert replay["paired_differences"] == measured["paired_differences"]


def test_canaries_cover_every_feature_alone_on_every_fold():
    receipt = load("evidence/feature_canaries.json")
    rows = receipt["rows"]
    assert len(rows) == 23 * 4
    assert len({r["feature"] for r in rows}) == 23
    assert {r["fold"] for r in rows} == {"NW", "NE", "SW", "SE"}
    assert not receipt["leakage_suspected"]
    assert receipt["maximum_orientation_invariant_auc"] == max(r["orientation_invariant_auc"] for r in rows)
    assert all(r["positive_pixels"] > 0 and r["negative_pixels"] > 0 for r in rows)


def test_current_tiff_exact_bytes_format_range_and_zip_identity():
    card = load("registry/run_card.json")
    path = ROOT / card["artifact"]
    assert sha256(path) == card["raster_sha256"]
    receipt = json.loads(path.with_suffix(".json").read_text())
    with rasterio.open(path) as ds:
        assert ds.count == 1
        assert ds.dtypes == ("float32",)
        assert ds.shape == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert list(ds.transform)[:6] == [100., 0., 243350., 0., -100., 4508550.]
        a = ds.read(1)
    assert np.isfinite(a).all()
    assert float(a.min()) == card["validator"]["range_min"]
    assert float(a.max()) == card["validator"]["range_max"]
    assert 0 <= a.min() <= a.max() <= 1
    assert hashlib.sha256(a.tobytes()).hexdigest() == card["raster_decoded_sha256"]
    with zipfile.ZipFile(path.with_suffix(".zip")) as z:
        assert z.namelist() == [path.name]
        assert z.read(path.name) == path.read_bytes()
    assert sha256(path.with_suffix(".zip")) == receipt["zip_sha256"]
    assert receipt["approved_for_weekly_slot"] is False
    assert receipt["promoted"] is False
    assert all(receipt["validator"]["checks"].values())


def test_negative_artifact_and_manifest_cannot_be_mistaken_for_promoted_dots():
    card, manifest = load("registry/run_card.json"), load("docs/downloads/manifest.json")
    assert card["verdict"] == manifest["verdict"] == "negative"
    assert card["decision"]["ok_to_download"]
    assert not card["decision"]["ok_to_submit"] and not manifest["ok_to_submit"]
    assert card["leaderboard_estimate"] is None and manifest["leaderboard_estimate"] is None
    assert card["organizer_confirmed_submission_score"] is None
    assert "NOT GENERATED" in card["registry"]["final_dots"]
    assert len(card["submission_name"]) <= 140 and len(card["submission_note"]) <= 140
    assert load("docs/data/run-card.json") == card


def test_registry_scope_forward_stop_and_exact_pixel_distinctness_are_separate():
    audit = load("evidence/registry_surface_audit.json")
    assert audit["registry_rasters_checked"] == 360
    assert audit["complete_accessible_scan"] and audit["missing_or_invalid"] == 0
    assert not audit["complete_all_user_listed_sites"]
    assert audit["byte_unique_among_checked"] and audit["pixel_unique_among_checked"]
    assert not audit["unique"] and audit["stop_required"]
    assert audit["duplicate_count"] == 1
    assert audit["worst_dot_overlap"] > .7
    assert all("their_dots_within_3px_of_mine" in r for r in audit["rows"])
    assert any(r["their_dots_within_3px_of_mine"] > 0 for r in audit["rows"])
    assert "their_dots_within_3px_of_mine" not in audit["first_stop"]["row"]
    certificate = load("evidence/lattice_coverage_certificate.json")
    assert not certificate["universal_overlap_blocker"]
    assert certificate["uncovered_allowed_pixels"] > 0


def test_historical_numbers_never_relabelled_as_verified_scores():
    audit = load("evidence/nine_site_audit.json")
    assert len(audit["rows"]) == 9
    for row in audit["rows"]:
        assert row["organizer_submission_receipt"] is None
        assert row["leaderboard_estimate"] is None
        assert row["historical_value_evidence_class"] == "USER-REPORTED; NOT ORGANIZER-CONFIRMED"
        assert not row["recommended_new_submission"]
    assert audit["rows"][0]["site"] == "GEMSDOE32"
    assert audit["rows"][1]["site"] == "GEMSDOE36"
    assert audit["lineage"]["d28_equals_gems30"]
    assert audit["lineage"]["b2_equals_d28_pruned_at_distance_le_2px"]
    assert audit["lineage"]["anderson_added_dots_to_b2"] == 1200


def test_complete_standing_request_is_embedded_in_readme():
    assert (ROOT / "docs/standing-prompt.md").read_text() in (ROOT / "README.md").read_text()
    assert "MUST GENERATE A UNIQUE TIF SUBMISSION" in (ROOT / "README.md").read_text()


def test_all_nine_commit_pins_and_inventoried_git_blobs_are_verified():
    pins = load("registry/repository_snapshots.json")["repositories"]
    verification = load("evidence/snapshot_commit_verification.json")
    assert len(pins) == len(verification) == 9
    assert {row["repo"]: row["ref"] for row in pins} == {row["repo"]: row["commit"] for row in verification}
    assert all(row["verified_commit"] and row["tree"] != row["commit"] for row in verification)
    inventory = load("registry/focus_inventory.json")
    assert inventory["complete_accessible_scan"] and not inventory["errors"]
    assert all(not Path(row["cache_file"]).is_absolute() for row in inventory["rasters"])
    files = load("registry/focus_files.json")["files"]
    assert len(files) == 377
    assert all(row["git_blob_identity_verified"] for row in files)


def test_concurrent_main_archive_and_frozen_science_are_byte_preserved():
    receipt = load("evidence/parallel_main_integration.json")
    assert receipt["all_archived_site_bytes_identical"]
    assert receipt["all_inherited_shared_source_hashes_unchanged"]
    assert not receipt["inherited_experiments_rerun"]
    assert receipt["no_score_pooling_or_cross_instrument_ranking"]
    for row in receipt["archived_site_files"]:
        assert sha256(ROOT / row["archived"]) == row["sha256"]
    for row in receipt["inherited_shared_sources"] + receipt["frozen_artifacts_and_cards"]:
        assert sha256(ROOT / row["path"]) == row["sha256"]
    legacy = receipt["legacy_reference_validator"]
    assert legacy["byte_identical"]
    assert sha256(ROOT / legacy["preserved_path"]) == legacy["original_sha256"]


def test_inherited_small_bridge_references_match_current_lane_pins():
    manifest = load("registry/data_manifest.json")
    pins = {row["dest"]: row["sha256"] for row in manifest["files"]}
    for name in ("labels.tif", "sample_submission.tif"):
        assert sha256(ROOT / "data/bridge" / name) == pins[name]


def test_first_stop_time_never_moves_when_diagnostics_are_rechecked():
    import importlib.util
    spec = importlib.util.spec_from_file_location("registry_caller", ROOT / "scripts/audit_registry.py")
    caller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(caller)
    first = load("evidence/first_registry_stop.json")
    ledger = load("registry/experiment_ledger.json")
    assert ledger["stop_utc"] == first["recorded_utc"]
    later = "2099-01-01T00:00:00+00:00"  # Synthetic future verification, not an observation.
    updated = caller.stopped_ledger(ledger, first, later)
    assert updated["stop_utc"] == first["recorded_utc"]
    assert updated["last_registry_verification_utc"] == later
    assert updated["experiments_completed"] == 1 and updated["submission_slots_used"] == 0
    assert caller.stopped_ledger(updated, None, later)["stop_utc"] == first["recorded_utc"]
