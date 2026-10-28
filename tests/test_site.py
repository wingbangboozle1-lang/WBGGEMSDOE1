from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()
        self.text = []
        self.alts = []

    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k):
                self.urls.append(a[k])
        if tag == "img":
            self.alts.append(a.get("alt", ""))

    def handle_data(self, data):
        self.text.append(data)


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize("name", ["index.html", "executive-summary.html", "focus9-executive-summary.html", "hypotheses.html", "research.html", "evidence.html", "how-to-submit.html", "release-review.html", "wbg-h1-dpgf1/index.html", "wbg-h1-dpgf1/executive-summary.html", "wbg2.html"])
def test_all_site_local_links_resolve_and_decision_is_unmistakable(name):
    file = DOCS / name
    html = file.read_text()
    parser = Elements()
    parser.feed(html)
    text = " ".join(parser.text).lower()
    assert "download: yes" in text and "submit: no" in text
    if name == "wbg2.html":
        assert "no weekly slot was used" in text and "retrospective" in text
    elif name in {"release-review.html", "wbg-h1-dpgf1/index.html", "wbg-h1-dpgf1/executive-summary.html"}:
        assert "no competition slot" in text
    elif name == "focus9-executive-summary.html":
        assert "do not submit" in text and "0 slots used" in text
    elif name == "hypotheses.html":
        assert "no experiment or slot was spent" in text and "untested proposals" in text
    else:
        assert "no final dots" in text and "no competition slot" in text
    assert '<html lang="en">' in html
    assert 'name="viewport"' in html
    assert 'href="#main"' in html
    assert all(len(alt) > 20 for alt in parser.alts)
    for url in parser.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            assert "localhost" not in url and "127.0.0.1" not in url
            continue
        target = (file.parent / unquote(parts.path)).resolve() if parts.path else file
        assert target.is_relative_to(ROOT)
        assert target.exists(), (name, url)
        if parts.fragment and target.suffix == ".html":
            p = Elements()
            p.feed(target.read_text())
            assert parts.fragment in p.ids, (name, url)


def test_focus9_executive_page_has_resolvable_published_links_and_research_only_status():
    file = DOCS / "focus9-executive-summary.html"
    html = file.read_text()
    parser = Elements()
    parser.feed(html)
    text = " ".join(parser.text)
    assert "DOWNLOAD: YES (research only)" in text
    assert "SUBMIT: NO" in text
    assert "USER-REPORTED" in text and "Unavailable" in text
    assert "81.932%" in text
    for url in parser.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            assert "localhost" not in url and "127.0.0.1" not in url
            continue
        target = (file.parent / unquote(parts.path)).resolve() if parts.path else file
        assert target.is_relative_to(ROOT) and target.exists(), url


def test_focus9_null_download_is_visible_and_fail_closed_in_generated_homepage_and_guide():
    site = module("build_site")
    banner = site.focus9_banner()
    assert "DOWNLOAD YES · SUBMIT NO" in banner
    assert "uniform-random null, not a geological model" in banner
    assert "no HOLDOUT-DTI was measured" in banner
    assert "81.932%" in banner and "&gt;70%" in banner
    assert "competing-sparse overlap is unmeasured" in banner
    assert "Download research TIFF" in banner
    for name in ("index.html", "how-to-submit.html"):
        html = (DOCS / name).read_text()
        assert "Focus-9 research file: DOWNLOAD YES · SUBMIT NO." in html
        assert "81.932%" in html


def test_wbg2_negative_decision_and_download_are_prominent():
    card = json.loads((ROOT / "evidence/wbg2/run_card.json").read_text())
    name = Path(card["artifacts"]["tif"]).name
    for file in ("index.html", "executive-summary.html", "wbg2.html"):
        html = (DOCS / file).read_text()
        assert f'href="downloads/{name}" download' in html
        assert "DO NOT SUBMIT" in html
        assert "0.2824" not in html
    assert "future-hypotheses-20261027.md" in (DOCS / "wbg2.html").read_text()


def test_nine_site_table_reports_estimate_and_measured_uniqueness_scope():
    site = module("build_site")
    audit = json.loads((DOCS / "data/nine-site-audit.json").read_text())
    html = site.comparison_table(audit)
    expected_sites = {
        "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
    }
    assert {row["site"] for row in audit["rows"]} == expected_sites
    assert "Estimated leaderboard score" in html
    assert "Not inferred from a proxy" in html
    assert "other eight listed site files only" in html
    for row in audit["rows"]:
        pct = f"{row['maximum_forward_3px_overlap_vs_other_focus_champions']:.2%}"
        assert pct in html
        assert 'NO · fails 70% gate' in html
    published = (DOCS / "executive-summary.html").read_text()
    assert "Unique new submission?" in published
    assert "Maximum forward 3 px overlap with another focus-site champion" in published
    assert "0.2778" in published and "USER-REPORTED" in published
    markdown = (DOCS / "executive-summary.md").read_text()
    assert "maximum forward 3 px overlap" in markdown
    assert "Unavailable for a new file" in markdown
    focus_page = (DOCS / "focus9-executive-summary.html").read_text()
    assert "no holdout evaluation" in focus_page.lower()
    assert "synthetic HOLDOUT-DTI ≈0.0003" not in focus_page
    assert "81.932%" in focus_page
    assert "do not silently clip" in (DOCS / "how-to-submit.html").read_text().lower()
    hypothesis_page = (DOCS / "hypotheses.html").read_text()
    assert "Highest benefit-to-cost judgment" in hypothesis_page
    assert "Not viable for validation yet" in hypothesis_page
    assert "No holdout DTI, leaderboard estimate" in hypothesis_page


@pytest.mark.parametrize("file", ["wbg2-executive-summary.md", "research/future-hypotheses-20261027.md"])
def test_current_research_markdown_local_links_resolve(file):
    path = DOCS / file
    for raw in re.findall(r"\[[^]]+\]\(([^)]+)\)", path.read_text()):
        parts = urlsplit(raw)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        target = (path.parent / unquote(parts.path)).resolve()
        assert target.is_relative_to(ROOT) and target.exists(), (file, raw)


def test_exact_primary_download_has_no_generate_or_upload_simulation():
    card = json.loads((ROOT / "registry/run_card.json").read_text())
    name = Path(card["artifact"]).name
    for file in ("index.html", "executive-summary.html", "how-to-submit.html"):
        html = (DOCS / file).read_text()
        assert f'href="downloads/{name}" download' in html
    script = (DOCS / "assets/app.js").read_text()
    assert "localhost" not in re.sub(r"//[^\n]*", "", script)
    assert 'fetch("data/feed.json"' in script
    assert "innerHTML" not in script


def test_feed_parser_accepts_only_unambiguous_official_style_public_score_cell():
    feed = module("refresh_feed")
    html = '''<table><tr><th>Rank</th><th>Team members</th><th>Participant</th><th>Best public DW-Tversky</th><th>Other</th></tr>
    <tr><td>#1</td><td>image</td><td>Example</td><td>0.4437</td><td>0.9999</td></tr></table>'''
    result = feed.parse_leaderboard(html)
    assert result["rank"] == 1 and result["public_dw_tversky"] == .4437
    assert result["not_a_project_submission_receipt"]
    assert result["participant_display"] == "Example"


@pytest.mark.parametrize("html", [
    "<h1>Login</h1><p>0.4437</p>",
    "<table><tr><th>Rank</th><th>Public accuracy</th></tr><tr><td>#1</td><td>0.4437</td></tr></table>",
    "<table><tr><th>Rank</th><th>public Tversky</th></tr><tr><td>#1</td><td>1.25</td></tr></table>",
    "<table><tr><th>Rank</th><th>public Tversky</th></tr><tr><td>#1</td><td>0.25 estimated</td></tr></table>",
])
def test_feed_parser_fails_closed_on_login_unrelated_metric_or_ambiguous_score(html):
    with pytest.raises(ValueError):
        module("refresh_feed").parse_leaderboard(html)


def test_nonfresh_feed_is_not_statically_rendered_as_a_current_check():
    site = module("build_site")
    feed = {"leaderboard_status": "retained_observation_not_refreshed", "leaderboard": {
        "public_dw_tversky": .4437, "source": "https://example.org/", "observed_date_utc": "2026-10-20"}}
    html = site.feed_strip(feed)
    assert "2026-10-20" in html and "not a fresh page check" in html
    assert "observed 2026-10-26" not in html


def test_github_only_feed_never_requests_the_official_leaderboard(tmp_path, monkeypatch):
    feed = module("refresh_feed")
    (tmp_path / "registry").mkdir()
    (tmp_path / "docs/data").mkdir(parents=True)
    for file in ("sources.json", "repository_snapshots.json"):
        (tmp_path / "registry" / file).write_bytes((ROOT / "registry" / file).read_bytes())
    pin = json.loads((ROOT / "registry/repository_snapshots.json").read_text())["repositories"][0]
    calls = []

    def fake_fetch(url, *, github=False):
        assert github and url.startswith("https://api.github.com/repos/")
        calls.append(url)
        return json.dumps({"sha": pin["ref"]})

    monkeypatch.setattr(feed, "ROOT", tmp_path)
    monkeypatch.setattr(feed, "fetch", fake_fetch)
    monkeypatch.setattr("sys.argv", ["refresh_feed.py", "--github-only"])
    feed.main()
    result = json.loads((tmp_path / "docs/data/feed.json").read_text())
    assert len(calls) == 9
    assert result["network_refresh_attempted"]
    assert not result["official_page_refresh_attempted"]
    assert result["leaderboard_status"] == "retained_observation_not_refreshed"
    source = json.loads((tmp_path / "registry/sources.json").read_text())
    seed = next(s for s in source["sources"] if s["id"] == "OFFICIAL-LEADERBOARD")
    assert result["leaderboard"]["public_dw_tversky"] == seed["observation"]["public_dw_tversky"]
    assert result["leaderboard"]["observed_date_utc"] == seed["observation"]["date_utc"]
    assert result["models_retrained"] is False and result["submission_slots_used"] == 0


def test_failed_leaderboard_refresh_preserves_exact_observation_date(tmp_path, monkeypatch):
    feed = module("refresh_feed")
    (tmp_path / "registry").mkdir()
    (tmp_path / "docs/data").mkdir(parents=True)
    for file in ("sources.json", "repository_snapshots.json"):
        (tmp_path / "registry" / file).write_bytes((ROOT / "registry" / file).read_bytes())
    prior = json.loads((DOCS / "data/feed.json").read_text())
    prior["leaderboard"]["observed_date_utc"] = "2001-01-01"  # Synthetic stale fixture.
    (tmp_path / "docs/data/feed.json").write_text(json.dumps(prior))
    monkeypatch.setattr(feed, "ROOT", tmp_path)

    def fail(url, **kwargs):
        raise ValueError("synthetic unavailable network")

    monkeypatch.setattr(feed, "fetch", fail)
    monkeypatch.setattr("sys.argv", ["refresh_feed.py"])
    feed.main()
    result = json.loads((tmp_path / "docs/data/feed.json").read_text())
    assert result["leaderboard"] == prior["leaderboard"]
    assert result["leaderboard_status"] == "refresh_unavailable_last_observation_retained"
    assert len(result["errors"]) == 10
    assert result["weekly_allowance"]["remaining"] is None


def test_staged_pages_match_legacy_url_layout_and_preserve_artifact_bytes(tmp_path, monkeypatch):
    import hashlib
    stage = module("stage_pages")
    (tmp_path / "docs/downloads").mkdir(parents=True)
    (tmp_path / "registry").mkdir()
    raw = b"synthetic staging test bytes, not a competition TIFF"
    (tmp_path / "docs/downloads/fixture.tif").write_bytes(raw)
    card = {"artifact": "docs/downloads/fixture.tif", "raster_sha256": hashlib.sha256(raw).hexdigest()}
    (tmp_path / "registry/run_card.json").write_text(json.dumps(card))
    (tmp_path / "evidence/wbg2").mkdir(parents=True)
    w2 = {"verdict": "negative", "decision": {"ok_to_submit": False},
          "artifacts": {"tif": "docs/downloads/fixture.tif"}, "raster_sha256": card["raster_sha256"]}
    safety = {"passed_literal_gate": False, "existing_tiff_sha256": card["raster_sha256"]}
    (tmp_path / "evidence/wbg2/run_card.json").write_text(json.dumps(w2))
    (tmp_path / "evidence/wbg2/safety_audit_20261027.json").write_text(json.dumps(safety))
    (tmp_path / "evidence/wbg_s2").mkdir()
    s2 = {"verdict": "negative", "artifact": {"tif_path": "docs/downloads/fixture.tif", "tif_sha256": card["raster_sha256"]},
          "strict_governance_decision": {"ok_to_submit": False, "eligible_for_separate_selector": False}}
    s2_safety = {"existing_tiff_sha256": card["raster_sha256"], "ok_to_submit": False, "eligible_for_separate_selector": False,
                 "witnesses": [{"duplicate_by_overlap": True, "my_dots_within_3px_of_theirs": .8},
                               {"duplicate_by_overlap": True, "my_dots_within_3px_of_theirs": 1.0}]}
    (tmp_path / "evidence/wbg_s2/run_card.json").write_text(json.dumps(s2))
    (tmp_path / "evidence/wbg_s2/safety_review_20261027.json").write_text(json.dumps(s2_safety))
    (tmp_path / "evidence/focus9_exec").mkdir(parents=True)
    focus9 = {"artifact": "docs/downloads/fixture.tif", "raster_sha256": card["raster_sha256"],
        "verdict": "negative", "decision": {"ok_to_submit": False},
        "correlation_overlap_vs_registry": {"lattice_coverage": {"pigeonhole_min_overlap_for_36800_dots": .819320652173913}},
        "holdout_dti": {"dti": None}}
    (tmp_path / "evidence/focus9_exec/run_card.json").write_text(json.dumps(focus9))
    (tmp_path / "index.html").write_text('<meta http-equiv="refresh" content="0; url=docs/">')
    monkeypatch.setattr(stage, "ROOT", tmp_path)
    monkeypatch.setattr(stage, "S2_SHA", card["raster_sha256"])
    target = stage.stage()
    assert (target / "docs/downloads/fixture.tif").read_bytes() == raw
    assert (target / "index.html").read_bytes() == (tmp_path / "index.html").read_bytes()
    assert (target / ".nojekyll").is_file()
    assert stage.stage() == target  # Marked generated bundles may be rebuilt.
    w2["decision"]["ok_to_submit"] = True
    (tmp_path / "evidence/wbg2/run_card.json").write_text(json.dumps(w2))
    with pytest.raises(ValueError, match="negative decision"):
        stage.stage()
    w2["decision"]["ok_to_submit"] = False
    (tmp_path / "evidence/wbg2/run_card.json").write_text(json.dumps(w2))
    assert stage.stage() == target
    s2["strict_governance_decision"]["ok_to_submit"] = True
    (tmp_path / "evidence/wbg_s2/run_card.json").write_text(json.dumps(s2))
    with pytest.raises(ValueError, match="negative decision"):
        stage.stage()
    s2["strict_governance_decision"]["ok_to_submit"] = False
    (tmp_path / "evidence/wbg_s2/run_card.json").write_text(json.dumps(s2))
    assert stage.stage() == target
    focus9["decision"]["ok_to_submit"] = True
    (tmp_path / "evidence/focus9_exec/run_card.json").write_text(json.dumps(focus9))
    with pytest.raises(ValueError, match="Focus-9 research bytes or negative null decision"):
        stage.stage()
    focus9["decision"]["ok_to_submit"] = False
    (tmp_path / "evidence/focus9_exec/run_card.json").write_text(json.dumps(focus9))
    assert stage.stage() == target
    (target / ".wbg-pages-stage").unlink()
    with pytest.raises(ValueError, match="unmarked"):
        stage.stage()
    assert (target / "docs/downloads/fixture.tif").exists()


def test_source_evidence_page_uses_the_dated_registry_seed():
    sources = json.loads((ROOT / "registry/sources.json").read_text())
    obs = next(s for s in sources["sources"] if s["id"] == "OFFICIAL-LEADERBOARD")["observation"]
    html = (DOCS / "evidence.html").read_text()
    assert f'Directly observed public rank-one value: {obs["public_dw_tversky"]} on {obs["date_utc"]}.' in html
    assert "Not a project TIFF receipt" in html


def test_format_guide_distinguishes_official_and_local_exterior():
    for name in ("how-to-submit.html", "wbg2.html"):
        html = (DOCS / name).read_text()
        assert "null/NaN" in html and "outside" in html
        assert "organizer acceptance" in html or "portal acceptance" in html


def test_feed_parser_handles_split_public_header_and_probe_reports_only_structure():
    html = '''<html><head><title>Public leaderboard</title></head><body><table>
    <tr><th>Rank</th><th>Participant</th><th>Best<br>public<br>DW-Tversky</th></tr>
    <tr><td>#1</td><td>Example</td><td>0.4544</td></tr></table><p>Do not include body text</p></body></html>'''
    feed = module("refresh_feed")
    probe = module("probe_leaderboard")
    assert feed.parse_leaderboard(html)["public_dw_tversky"] == .4544
    shape = probe.public_shape(html)
    assert shape["title"] == "Public leaderboard" and shape["table_count"] == 1
    assert shape["first_headers"] == [["Rank", "Participant", "Best public DW-Tversky"]]
    assert "Do not include body text" not in json.dumps(shape)


def test_feed_fetches_the_official_htmx_partial_and_labels_the_observation(tmp_path, monkeypatch):
    feed = module("refresh_feed")
    (tmp_path / "registry").mkdir()
    (tmp_path / "docs/data").mkdir(parents=True)
    for file in ("sources.json", "repository_snapshots.json"):
        (tmp_path / "registry" / file).write_bytes((ROOT / "registry" / file).read_bytes())
    calls = []
    fragment = '''<table><tr><th>Rank</th><th>Participant</th><th>Best public DW-Tversky</th></tr>
    <tr><td>#1</td><td>Example</td><td>0.4544</td></tr></table>'''

    def fake_fetch(url, *, github=False):
        calls.append(url)
        if url == feed.LEADERBOARD:
            return '<div id="leaderboard_table" hx-get="/competitions/306/competition-doe-gems/leaderboard_partial/"></div>'
        if url == feed.LEADERBOARD_PARTIAL:
            return fragment
        if github:
            return json.dumps({"sha": "a" * 40})
        raise AssertionError(url)

    monkeypatch.setattr(feed, "ROOT", tmp_path)
    monkeypatch.setattr(feed, "fetch", fake_fetch)
    monkeypatch.setattr("sys.argv", ["refresh_feed.py"])
    feed.main()
    result = json.loads((tmp_path / "docs/data/feed.json").read_text())
    assert calls[:2] == [feed.LEADERBOARD, feed.LEADERBOARD_PARTIAL]
    assert result["leaderboard_status"] == "network_verified"
    assert result["leaderboard"]["public_dw_tversky"] == .4544
    assert result["leaderboard"]["source"] == feed.LEADERBOARD
    assert result["leaderboard"]["source_fetch_url"] == feed.LEADERBOARD_PARTIAL
    assert result["leaderboard"]["not_a_project_submission_receipt"] is True


def test_feed_refuses_cross_origin_or_insecure_redirects():
    feed = module("refresh_feed")
    request = feed.urllib.request.Request("https://api.github.com/repos/example/project")
    handler = feed.SameOriginRedirect()
    for target in ("https://elsewhere.example/path", "http://api.github.com/path"):
        with pytest.raises(ValueError, match="refusing cross-host"):
            handler.redirect_request(request, None, 302, "Found", {}, target)


def test_feed_parser_repairs_the_official_unwrapped_thead_cells():
    feed = module("refresh_feed")
    html = '''<table><thead>
      <th>Rank</th><th>Team members</th><th>Participant</th>
      <th>Best<br>public<br>DW-Tversky (in descending order)</th><th>Shared work</th>
      </thead><tbody><tr><td>#1</td><td></td><td>Example</td><td>0.4544</td><td></td></tr></tbody></table>'''
    result = feed.parse_leaderboard(html)
    assert result["rank"] == 1 and result["public_dw_tversky"] == .4544
    assert result["source"] == feed.LEADERBOARD and result["not_a_project_submission_receipt"]
