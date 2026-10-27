#!/usr/bin/env python3
"""Diagnose the public feed's page shape in CI without changing evidence.

Emits a compact Actions annotation containing only the public page title,
count and first parsed table header, or the verified public rank-one value.
Network failures are informational: the production feed retains dated evidence.
No login, credentials, account data, model, file or competition slot is used.
"""
from html.parser import HTMLParser
import json
import re
from pathlib import Path
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_feed import LEADERBOARD, LEADERBOARD_PARTIAL, Tables, fetch, parse_leaderboard  # noqa: E402


class Title(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []
        self.scripts = []
        self.markers = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self.inside = True
        if tag == "script" and a.get("src"):
            # Public script names only; strip query strings and fragments.
            src = urlsplit(a["src"])
            self.scripts.append((src.netloc + src.path)[:120])
        for key in ("id", "data-url", "data-endpoint", "hx-get"):
            value = a.get(key, "")
            if "leaderboard" in value.lower() or "ranking" in value.lower():
                self.markers.append(f"{tag}:{key}={value.split('?')[0][:120]}")

    def handle_endtag(self, tag):
        if tag == "title":
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.parts.append(data)


def public_shape(html):
    tables = Tables()
    tables.feed(html)
    title = Title()
    title.feed(html)
    # Only public structural fields; no page body or login information.
    paths = sorted(set(re.findall(r"[\"'](/[^\"'\s?#]*(?:leaderboard|ranking)[^\"'\s?#]*)", html, re.I)))
    return {"title": " ".join(" ".join(title.parts).split())[:120],
            "table_count": len(tables.tables),
            "first_headers": [row[0][:6] for row in tables.tables[:2] if row],
            "script_sources": title.scripts[:8], "markers": title.markers[:8], "public_paths": paths[:8]}


def main():
    try:
        html = fetch(LEADERBOARD)
        try:
            row = parse_leaderboard(html)
            source = "main page"
        except ValueError:
            partial = fetch(LEADERBOARD_PARTIAL)
            try:
                row = parse_leaderboard(partial)
                source = "official HTMX partial"
            except ValueError as error:
                message = f"strict parse unavailable: {error}; main=" + json.dumps(public_shape(html), ensure_ascii=True)
                message += "; partial=" + json.dumps(public_shape(partial), ensure_ascii=True)
                row = None
        if row is not None:
            message = f"strict parse OK from {source}; public rank 1 = {row['public_dw_tversky']} (not a file receipt)"
    except Exception as error:
        message = f"public source unavailable: {type(error).__name__}: {str(error)[:160]}"
    # Escape workflow-command metacharacters and keep the annotation bounded.
    message = re.sub(r"\s+", " ", message)[:2200].replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::notice file=scripts/refresh_feed.py,line=1,title=Public leaderboard feed probe::{message}")


if __name__ == "__main__":
    main()
