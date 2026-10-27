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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wbggems.audit import dump_json, utc_now

LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
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
                participant = row[participant_column] if participant_column is not None else None
                return {"evidence_class": "OFFICIAL-PUBLIC-LEADERBOARD-OBSERVATION", "rank": 1,
                        "public_dw_tversky": float(row[column]),
                        "participant": participant,
                        "participant_display": participant,
                        "source": LEADERBOARD,
                        "not_a_project_submission_receipt": True}
    raise ValueError("no recognizable public Tversky leaderboard table with rank one")


def fetch(url, *, github=False):
    headers = {"User-Agent": "WBGGEMSDOE1-provenance-feed/1.0"}
    if github and os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN")):
        headers["Authorization"] = "Bearer " + os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN"))
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        final = response.geturl()
        if "login" in final:
            raise ValueError("redirected to login; no authenticated evidence available")
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
    seed_observation = {
        **seed["observation"],
        "evidence_class": seed["evidence_class"],
        "source": seed["url"],
        "observed_date_utc": seed["observation"].get("date_utc"),
        "observation_method": seed["observation"].get("observation_method", seed.get("access", "recorded official-page observation")),
        "prior_observations": seed.get("prior_observations", []),
        "not_a_project_submission_receipt": True,
    }
    last = previous.get("leaderboard", seed_observation)
    errors, heads = [], []
    leaderboard_status = "retained_observation_not_refreshed"
    if not args.offline:
        if not args.github_only:
            try:
                fetched_at = utc_now()
                fresh = {
                    **parse_leaderboard(fetch(LEADERBOARD)),
                    "observed_utc": fetched_at,
                    "observed_date_utc": fetched_at[:10],
                    "observation_method": "strict official HTML leaderboard table parse",
                }
                history = list(last.get("prior_observations", []))
                old_record = {
                    key: last[key]
                    for key in ("date_utc", "observed_date_utc", "rank", "participant", "public_dw_tversky", "evidence_class")
                    if key in last
                }
                fresh_key = (fresh["observed_date_utc"], fresh["rank"], fresh.get("participant"), fresh["public_dw_tversky"])
                old_key = (
                    old_record.get("observed_date_utc") or old_record.get("date_utc"),
                    old_record.get("rank"), old_record.get("participant"), old_record.get("public_dw_tversky"),
                )
                if old_record and old_key != fresh_key and old_key not in {
                    (row.get("observed_date_utc") or row.get("date_utc"), row.get("rank"), row.get("participant"), row.get("public_dw_tversky"))
                    for row in history
                }:
                    history.append(old_record)
                fresh["prior_observations"] = history[-20:]
                last = fresh
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
