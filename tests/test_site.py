import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path
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


@pytest.mark.parametrize("name", ["index.html", "executive-summary.html", "research.html", "evidence.html", "how-to-submit.html"])
def test_all_site_local_links_resolve_and_decision_is_unmistakable(name):
    file = DOCS / name
    html = file.read_text()
    parser = Elements()
    parser.feed(html)
    text = " ".join(parser.text).lower()
    assert "download: yes" in text and "submit: no" in text
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
    assert result["leaderboard"]["public_dw_tversky"] == .4544
    assert result["leaderboard"]["observed_date_utc"] == "2026-10-27"
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
    (tmp_path / "index.html").write_text('<meta http-equiv="refresh" content="0; url=docs/">')
    monkeypatch.setattr(stage, "ROOT", tmp_path)
    target = stage.stage()
    assert (target / "docs/downloads/fixture.tif").read_bytes() == raw
    assert (target / "index.html").read_bytes() == (tmp_path / "index.html").read_bytes()
    assert (target / ".nojekyll").is_file()
    assert stage.stage() == target  # Marked generated bundles may be rebuilt.
    (target / ".wbg-pages-stage").unlink()
    with pytest.raises(ValueError, match="unmarked"):
        stage.stage()
    assert (target / "docs/downloads/fixture.tif").exists()
