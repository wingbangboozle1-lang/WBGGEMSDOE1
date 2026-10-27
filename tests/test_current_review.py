"""2026-10-27 source freshness, archived-site safety and real-file readiness regressions."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def read(path):
    return json.loads((ROOT / path).read_text())


def test_dated_official_observation_is_not_an_organizer_receipt():
    obs = read("evidence/official_leaderboard_observation_20261027.json")
    feed = read("docs/data/feed.json")
    source = next(s for s in read("registry/sources.json")["sources"] if s["id"] == "OFFICIAL-LEADERBOARD")
    assert obs["rank_one"]["public_dw_tversky"] == feed["leaderboard"]["public_dw_tversky"] == .4544
    assert source["observation"]["public_dw_tversky"] == .4544
    assert obs["observed_date_utc"] == feed["leaderboard"]["observed_date_utc"] == "2026-10-27"
    assert obs["not_a_project_submission_receipt"] and feed["leaderboard"]["not_a_project_submission_receipt"]
    assert feed["leaderboard_status"] == "retained_observation_not_refreshed"
    assert not feed["official_page_refresh_attempted"]  # GitHub-only CLI, separate direct fetch_page observation.
    assert read("registry/run_card.json")["organizer_confirmed_submission_score"] is None
    assert all(h["changed_since_audit"] for h in feed["repository_heads"])
    for site in ("docs/index.html", "docs/executive-summary.html", "docs/executive-summary.md", "docs/evidence.html", "README.md"):
        text = (ROOT / site).read_text()
        assert "0.4544" in text, site
        if site != "docs/evidence.html":
            assert "0.2778" in text, site
    assert "Directly observed public rank-one value: 0.4544 on 2026-10-27" in (ROOT / "docs/evidence.html").read_text()


def test_inherited_subsite_cannot_recommend_negative_file_or_owner_claims_as_receipts():
    for page in ("index.html", "executive-summary.html"):
        text = (ROOT / "docs/wbg-h1-dpgf1" / page).read_text()
        assert "DOWNLOAD: YES, for research" in text
        assert "SUBMIT: NO" in text and "DO NOT SUBMIT" in text
        assert "OWNER-REPORTED / UNVERIFIED" in text
        assert "99.80%" in text
        assert "CONDITIONAL BACKUP" not in text
        assert "ORGANIZER-CONFIRMED</code>" not in text
        assert "Open DrivenData GEMS Submission Portal" not in text
        assert "--check-uniqueness" not in text  # This option doesn't exist in the current validator.
    assert "NEW HEAD since frozen audit" in (ROOT / "docs/executive-summary.html").read_text()
    assert "Frozen inventory alert" in (ROOT / "docs/index.html").read_text()


def test_review_decision_card_is_not_a_second_scientific_run():
    card = read("evidence/review_run_card_20261027_followup.json")
    frozen = read("registry/run_card.json")
    new = card["prospective_hypothesis"]
    old = card["frozen_existing_negative_reference"]
    assert new["id"] == "MFO1" and "UNTESTED" in new["status"]
    assert new["holdout_dti"] is new["holdout_ci95"] is new["withheld_positives"] is None
    assert new["generated_new_raster_sha256"] is None
    assert old["holdout"] == frozen["holdout"]
    assert old["registry_surface_before_dots"] == frozen["registry"]
    assert old["tiff_sha256"] == frozen["raster_sha256"]
    assert old["exact_validator"]["all_checks_passed"]
    assert old["exact_validator"]["require_submit_ready_exit_code"] == 2
    assert not old["exact_validator"]["require_submit_ready_ok_to_submit"]
    assert not card["decision"]["ok_to_submit_any_current_raster"]
    assert card["experiment_budget"]["new_experiments_this_review"] == 0
    assert card["experiment_budget"]["weekly_slots_used_this_review"] == 0
    assert len(old["proposed_name_never_uploaded"]) <= 140
    assert len(old["proposed_note_never_uploaded"]) <= 140


def test_inherited_subsite_internal_links_really_exist():
    from html.parser import HTMLParser
    from urllib.parse import unquote, urlsplit

    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = []

        def handle_starttag(self, _tag, attrs):
            self.urls.extend(value for key, value in attrs if key in ("href", "src") and value)

    for name in ("index.html", "executive-summary.html"):
        page = ROOT / "docs/wbg-h1-dpgf1" / name
        parser = Links()
        parser.feed(page.read_text())
        for url in parser.urls:
            parts = urlsplit(url)
            if not parts.scheme and not parts.netloc:
                target = (page.parent / unquote(parts.path)).resolve() if parts.path else page
                assert target.is_relative_to(ROOT) and target.exists(), (page, url)


def test_archive_warning_and_radiometric_erratum_are_visible_in_current_guidance():
    for path in ("README.md", "docs/index.html", "docs/wbg-h1-dpgf1/index.html"):
        text = (ROOT / path).read_text()
        assert "DO NOT SUBMIT" in text, path
    assert "outdated upload advice. Do not follow it" in (ROOT / "README.md").read_text()
    assert "not upload advice" in (ROOT / "docs/index.html").read_text()
    assert "19-band core cache" in (ROOT / "docs/hypotheses.md").read_text()
    assert "not" in (ROOT / "docs/hypotheses.md").read_text().split("19-band core cache")[0][-40:].lower()
    assert read("registry/irregularities.json")["items"][-2]["id"] == "IR-023"
    assert read("docs/data/review-run-card-20261027.json") == read("evidence/review_run_card_20261027_followup.json")


def test_readiness_reports_actual_saved_tiff_and_separates_data_from_science():
    checker = module("check_readiness")
    report = checker.inspect(ROOT)
    assert report["submission_tif_generated"] and report["submission_tif_locally_format_validated"]
    assert report["research_artifact"]["zip_contains_same_tiff"]
    assert report["shared_template_pins"]["verified"] and report["shared_template_pins"]["files_checked"] == 24
    assert report["optional_1m_dem_links_csv"]["required_for_cached_19_band_method"] is False
    assert report["scientific_screen_recorded"] and report["current_lane_stopped"]
    assert report["scientific_gates_passed"] is False and report["ok_to_submit"] is False
    assert report["cached_19_band_pipeline_inputs_ready"] == (
        all(r["verified_to_owner_mirror_pin"] for r in report["core_inputs"].values())
        and report["feature_cache"]["verified"] and report["shared_template_pins"]["verified"]
    )  # Pytest CI clones lack ignored raw data.


def test_readiness_never_accepts_stale_band_receipt_and_csv_is_optional(tmp_path, monkeypatch):
    checker = module("check_readiness")
    (tmp_path / "registry").mkdir()
    (tmp_path / "data/template57/.cache/features").mkdir(parents=True)
    (tmp_path / "data/template57/evidence").mkdir()
    (tmp_path / "docs/downloads").mkdir(parents=True)
    digests = {}
    for name in checker.CORE:
        p = tmp_path / "data" / name
        p.write_bytes(name.encode())
        digests[name] = checker.sha256(p)
    (tmp_path / "registry/data_manifest.json").write_text(json.dumps({"files": [
        {"dest": name, "sha256": digests[name]} for name in checker.CORE]}))
    blob = tmp_path / "data/template57/.cache/features/band-01.npy"
    blob.write_bytes(b"synthetic cache; not a scientific raster")
    band_hash = checker.sha256(blob)
    (tmp_path / "registry/template_pins.json").write_text(json.dumps({
        "cached_feature_stack_reference": {"expected_band_sha256": [band_hash]}}))
    (tmp_path / "data/template57/evidence/feature_cache.json").write_text(json.dumps({
        "source_sha256": digests["training_features.tif"],
        "bands": [{"band": 1, "cache_file": ".cache/features/band-01.npy", "sha256": band_hash}]}))
    (tmp_path / "registry/run_card.json").write_text(json.dumps(read("registry/run_card.json")))
    for tool in checker.TOOLS:
        path = tmp_path / tool
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic")
    tool_pin = tmp_path / checker.TOOLS[0]
    (tmp_path / "registry/shared_template.json").write_text(json.dumps({"files": [
        {"path": checker.TOOLS[0], "sha256": checker.sha256(tool_pin)}]}))
    monkeypatch.setattr(checker, "inspect_artifact", lambda *args: {
        "present": True, "sha256_matches_frozen_card": True, "local_format_passed": True,
        "zip_contains_same_tiff": True, "submission_approved": False})
    valid = checker.inspect(tmp_path)
    assert valid["cached_19_band_pipeline_inputs_ready"]
    assert valid["status"] == "INPUTS_READY_LANE_STOPPED"
    assert not valid["optional_1m_dem_links_csv"]["present"]
    receipt_path = tmp_path / "data/template57/evidence/feature_cache.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["bands"][0]["band"] = 99
    receipt_path.write_text(json.dumps(receipt))
    reordered = checker.inspect(tmp_path)
    assert reordered["feature_cache"]["status"] == "CACHE_INTEGRITY_FAILURE"
    assert not reordered["ok_to_submit"]
    receipt["bands"][0]["band"] = 1
    receipt_path.write_text(json.dumps(receipt))
    blob.write_bytes(b"tampered; same old receipt")
    invalid = checker.inspect(tmp_path)
    assert invalid["feature_cache"]["status"] == "CACHE_INTEGRITY_FAILURE"
    assert not invalid["cached_19_band_pipeline_inputs_ready"] and not invalid["ok_to_submit"]
    blob.write_bytes(b"synthetic cache; not a scientific raster")
    tool_pin.write_text("# altered shared evaluator")
    modified = checker.inspect(tmp_path)
    assert not modified["shared_template_pins"]["verified"]
    assert not modified["cached_19_band_pipeline_inputs_ready"] and not modified["ok_to_submit"]


def test_pages_publication_gate_checks_exact_bytes_zip_and_negative_status(tmp_path):
    site = module("build_site")
    d = tmp_path / "docs/downloads"
    d.mkdir(parents=True)
    tif = d / "negative.tif"
    tif.write_bytes(b"synthetic format fixture, never submitted")
    digest = hashlib.sha256(tif.read_bytes()).hexdigest()
    archive = tif.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(tif.name, tif.read_bytes())
    card = {"artifact": "docs/downloads/negative.tif", "raster_sha256": digest,
            "verdict": "negative", "decision": {"ok_to_submit": False},
            "registry": {"passes_literal_uniqueness": False, "final_dots": "NOT GENERATED"}}
    receipt = {"sha256": digest, "validator": {"all_checks_passed": True, "checks": {"synthetic": True}},
               "zip_file": archive.name, "zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
    assert site.verify_publication(card, receipt, tmp_path)
    changed = copy.deepcopy(card)
    changed["registry"]["passes_literal_uniqueness"] = True
    with pytest.raises(ValueError, match="unexpected promotion"):
        site.verify_publication(changed, receipt, tmp_path)
    changed = copy.deepcopy(receipt)
    changed["validator"]["checks"]["synthetic"] = False
    with pytest.raises(ValueError, match="format checks"):
        site.verify_publication(card, changed, tmp_path)
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("other.tif", tif.read_bytes())
    with pytest.raises(ValueError, match="ZIP checksum"):
        site.verify_publication(card, receipt, tmp_path)
    tif.write_bytes(b"different bytes")
    with pytest.raises(ValueError, match="published TIFF bytes"):
        site.verify_publication(card, receipt, tmp_path)
