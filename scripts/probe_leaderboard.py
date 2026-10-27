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

from refresh_feed import LEADERBOARD, Tables, fetch, parse_leaderboard


class Title(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.inside = True

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
    return {"title": " ".join(" ".join(title.parts).split())[:120],
            "table_count": len(tables.tables),
            "first_headers": [row[0][:6] for row in tables.tables[:2] if row]}


def main():
    try:
        html = fetch(LEADERBOARD)
        try:
            row = parse_leaderboard(html)
            message = f"strict parse OK; public rank 1 = {row['public_dw_tversky']} (not a file receipt)"
        except ValueError as error:
            message = f"strict parse unavailable: {error}; shape=" + json.dumps(public_shape(html), ensure_ascii=True)
    except Exception as error:
        message = f"public source unavailable: {type(error).__name__}: {str(error)[:160]}"
    # Escape workflow-command metacharacters and keep the annotation bounded.
    message = re.sub(r"\s+", " ", message)[:900].replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::notice file=scripts/refresh_feed.py,line=1,title=Public leaderboard feed probe::{message}")


if __name__ == "__main__":
    main()
