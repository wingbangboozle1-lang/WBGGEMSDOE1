from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = [
    DOCS / "index.html",
    DOCS / "research.html",
    DOCS / "methodology.html",
    DOCS / "submission-instructions.html",
    DOCS / "repo-review-20261027.html",
    DOCS / "executive-summary-focus-sites.html",
    DOCS / "executive-summary-unique.html",
]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        for key in ("href", "src"):
            if key in data:
                self.paths.append(data[key])


def test_all_internal_site_links_resolve_to_published_files():
    missing = []
    for page in PAGES:
        parser = Links()
        parser.feed(page.read_text())
        for raw in parser.paths:
            parsed = urlparse(raw)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.is_file():
                missing.append((page.name, raw))
    assert not missing


def test_wbg7_focus_page_does_not_claim_complete_uniqueness_or_submission_clearance():
    text = (DOCS / "executive-summary-focus-sites.html").read_text(encoding="utf-8").upper()
    assert "UNIQUENESS IS THEREFORE <STRONG>NOT FULLY ESTABLISHED" in text
    assert "DO NOT UPLOAD IT" in text
    assert "CURRENT STATUS: <STRONG>NO FILE IS CLEARED" in text
    assert "GENUINE, UNIQUE, FORMAT-VALID ENTRY" not in text


def test_main_executive_summary_does_not_overclaim_registry_uniqueness():
    text = (DOCS / "executive-summary-unique.html").read_text(encoding="utf-8").upper()
    assert "REGISTRY UNIQUENESS:</B> <STRONG>NOT CLEARED" in text
    assert "FULL 179-ENTRY REGISTRY IS NOT CHECKED" in text
    assert "GENERATED: UNIQUE GEOTIFF" not in text


def test_repository_review_card_is_published_from_canonical_evidence():
    source = ROOT / "evidence" / "repo_review_20261029.json"
    staged = DOCS / "data" / "repo-review-20261029.json"
    assert source.is_file()
    assert staged.is_file()
    assert staged.read_bytes() == source.read_bytes()


def test_wbg4_app_feed_is_staged_from_current_site_feed():
    source = DOCS / "data" / "feed.json"
    staged = DOCS / "wbg4" / "data" / "feed.json"
    assert source.is_file()
    assert staged.is_file()
    assert staged.read_bytes() == source.read_bytes()


def test_every_page_has_clear_negative_status():
    for page in PAGES:
        text = page.read_text()
        assert "Do not submit" in text or "DO NOT SUBMIT" in text
        assert "assets/style.css" in text
