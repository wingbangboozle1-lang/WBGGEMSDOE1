#!/usr/bin/env python3
"""Refresh public provenance, not model scores, lanes, approvals or submission slots.

A failed network request never replaces a last verified leaderboard observation
with zero, a projected score, a login page or an invented timestamp. This script
runs on scheduled GitHub Pages builds; no git commit/push or upload is performed.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wbggems.audit import dump_json, utc_now

LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
LEADERBOARD_PARTIAL = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard_partial/"


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.orphan_headers = []
        self.orphan_cell = False

    def flush_orphan_headers(self):
        if self.orphan_headers and self.table is not None:
            self.table.append(self.orphan_headers)
            self.orphan_headers = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
            self.orphan_headers = []
        elif tag == "tr" and self.table is not None:
            self.flush_orphan_headers()
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
            self.orphan_cell = False
        elif tag == "th" and self.table is not None:
            # The official HTMX fragment currently puts <th> directly under
            # <thead>, without a <tr>; browsers repair this automatically.
            self.cell = []
            self.orphan_cell = True

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            text = " ".join(" ".join(self.cell).split())
            if self.orphan_cell:
                self.orphan_headers.append(text)
            else:
                self.row.append(text)
            self.cell = None
            self.orphan_cell = False
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "thead":
            self.flush_orphan_headers()
        elif tag == "table" and self.table is not None:
            self.flush_orphan_headers()
            self.tables.append(self.table)
            self.table = None


def parse_leaderboard(html):
    parser = Tables()
    parser.feed(html)
    for table in parser.tables:
        if not table:
            continue
        for header_index, header in enumerate(table):
            score_columns = [i for i, text in enumerate(header) if "Tversky" in text and "public" in text.lower()]
            if not score_columns:
                continue
            for row in table[header_index + 1:]:
                if not row or not re.fullmatch(r"#?\s*1", row[0]):
                    continue
                column = score_columns[0]
                if column >= len(row) or not re.fullmatch(r"(?:0\.\d{4,8}|1(?:\.0{4,8})?)", row[column]):
                    raise ValueError("rank-one metric cell did not contain one unambiguous [0,1] score")
                participant_column = next((i for i, text in enumerate(header) if "Participant" in text), None)
                return {"evidence_class": "OFFICIAL-PUBLIC-LEADERBOARD-OBSERVATION", "rank": 1,
                        "public_dw_tversky": float(row[column]),
                        "participant_display": row[participant_column] if participant_column is not None else None,
                        "source": LEADERBOARD,
                        "not_a_project_submission_receipt": True}
    raise ValueError("no recognizable public Tversky leaderboard table with rank one")


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward GitHub authorization across hosts or HTTPS downgrades."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        original, target = urlsplit(req.full_url), urlsplit(newurl)
        if target.scheme != "https" or target.hostname != original.hostname:
            raise ValueError("refusing cross-host or non-HTTPS redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, *, github=False):
    headers = {"User-Agent": "WBGGEMSDOE1-provenance-feed/1.0"}
    if github and os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN")):
        headers["Authorization"] = "Bearer " + os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN"))
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.build_opener(SameOriginRedirect()).open(request, timeout=25) as response:
        final = response.geturl()
        if "login" in final:
            raise ValueError("redirected to login; no authenticated evidence available")
        if not github and urlsplit(final).hostname != "www.drivendata.org":
            raise ValueError("public leaderboard redirected away from the official host")
        return response.read().decode("utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="publish retained verified observation, clearly not a fresh network check")
    mode.add_argument("--github-only", action="store_true", help="refresh permitted GitHub heads only; retain the dated official-page observation")
    args = ap.parse_args()
    path = ROOT / "docs/data/feed.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    sources = json.loads((ROOT / "registry/sources.json").read_text())
    seed = next(s for s in sources["sources"] if s["id"] == "OFFICIAL-LEADERBOARD")
    last = previous.get("leaderboard", {**seed["observation"], "evidence_class": seed["evidence_class"],
        "source": seed["url"], "observed_date_utc": seed["observation"]["date_utc"], "observation_method": "fetch_page direct official page retrieval in research session",
        "not_a_project_submission_receipt": True})
    errors, heads = [], []
    leaderboard_status = "retained_observation_not_refreshed"
    if not args.offline:
        if not args.github_only:
            try:
                # The official page loads its public table via HTMX. First
                # accept a server-rendered table if present, otherwise fetch
                # only the pinned same-origin public partial, then apply the
                # same strict rank-one and metric-cell parser.
                page_html = fetch(LEADERBOARD)
                try:
                    row = parse_leaderboard(page_html)
                    source_fetch_url = LEADERBOARD
                except ValueError:
                    row = parse_leaderboard(fetch(LEADERBOARD_PARTIAL))
                    source_fetch_url = LEADERBOARD_PARTIAL
                last = {**row, "observed_utc": utc_now(), "source_fetch_url": source_fetch_url,
                        "observation_method": "strict official public leaderboard table parse"}
                leaderboard_status = "network_verified"
            except Exception as e:
                errors.append({"source": LEADERBOARD, "error": str(e)[:220]})
                leaderboard_status = "refresh_unavailable_last_observation_retained"
        pins = json.loads((ROOT / "registry/repository_snapshots.json").read_text())["repositories"]
        for pin in pins:
            try:
                data = json.loads(fetch(f"https://api.github.com/repos/{pin['repo']}/commits/main", github=True))
                heads.append({"repo": pin["repo"], "audited_commit": pin["ref"], "observed_head": data["sha"],
                              "changed_since_audit": data["sha"] != pin["ref"], "checked_utc": utc_now()})
            except Exception as e:
                errors.append({"source": pin["repo"], "error": str(e)[:220]})
    else:
        heads = previous.get("repository_heads", [])
    feed = {"generated_utc": utc_now(), "network_refresh_attempted": not args.offline,
            "official_page_refresh_attempted": not args.offline and not args.github_only,
            "leaderboard_status": leaderboard_status, "leaderboard": last,
            "repository_heads": heads, "errors": errors,
            "models_retrained": False, "submission_slots_used": 0,
            "weekly_allowance": {"authenticated": False, "remaining": None,
                                 "rule_pdf_limit": 3, "rule_pdf_is_not_current_account_allowance": True},
            "promotion_status": "negative — frozen research result; feed updates never authorize a submission",
            "scope": "Public provenance only; a changed upstream head is not a newly validated prediction or a file-specific organizer score."}
    dump_json(path, feed)
    print(json.dumps({"leaderboard_status": leaderboard_status, "repository_heads_checked": len(heads), "errors": len(errors)}))


if __name__ == "__main__":
    main()
