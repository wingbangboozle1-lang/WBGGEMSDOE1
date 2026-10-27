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
    DOCS / "wbg-d1.html",
    DOCS / "executive-summary.html",
    DOCS / "how-to-submit.html",
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


def test_every_page_has_clear_negative_status():
    for page in PAGES:
        text = page.read_text()
        assert "Do not submit" in text or "DO NOT SUBMIT" in text
        assert "assets/style.css" in text
