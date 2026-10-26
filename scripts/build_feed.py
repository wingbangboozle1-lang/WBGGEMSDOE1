#!/usr/bin/env python3
"""Build the deterministic Pages evidence feed from frozen receipts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "evidence/tip1_run_card_20261026.json"
NINE = ROOT / "evidence/nine_site_executive_summary_20261026.json"
OUTPUT = ROOT / "docs/data/feed.json"


def main() -> int:
    card = json.loads(CARD.read_text())
    nine = json.loads(NINE.read_text())
    feed = {
        "schema": "gemsdoe1-pages-feed-v1",
        "generated_utc": card["generated_utc"],
        "status": {
            "verdict": card["verdict"],
            "ok_to_download": card["ok_to_download"],
            "ok_to_submit": card["ok_to_submit"],
            "submission_slots_used": card["submission_slots_used"],
        },
        "artifact": {
            "name": card["submission_name"],
            "url": f"../downloads/{card['submission_name']}",
            "sha256": card["raster_sha256"],
            "note": card["submission_note"],
        },
        "latest_measurement": {
            "label": "HOLDOUT-DTI",
            "arm": "B",
            "value": card["arms"]["B"]["holdout"]["dti"],
            "ci95": card["arms"]["B"]["holdout"]["ci95"]["interval"],
            "evaluator_version": card["arms"]["B"]["holdout"]["evaluator_version"],
            "withheld_positive_pixels": card["arms"]["B"]["holdout"][
                "n_withheld_positive_pixels"
            ],
        },
        "events": [
            {
                "date": "2026-10-26",
                "kind": "preregistration",
                "summary": "Ranked five hypotheses and froze TIP1 Arms A/B/C before implementation.",
                "ref": card["preregistration_commit"],
            },
            {
                "date": "2026-10-26",
                "kind": "registry",
                "summary": "Restored 231 pinned sources into 179 unique comparators with zero rejected rows.",
            },
            {
                "date": "2026-10-26",
                "kind": "experiment",
                "summary": "Executed three fixed arms in 132.4 seconds; Arm B HOLDOUT-DTI 0.082434; negative.",
            },
            {
                "date": "2026-10-26",
                "kind": "artifact",
                "summary": "Wrote and validated one strict all-finite [0,1] GeoTIFF; DO NOT SUBMIT.",
            },
        ],
        "reviewed_sites": [
            {"site": row["site"], "readme_ref": row["current_readme_ref"]}
            for row in nine["sites"]
        ],
        "evidence": [
            "tip1_run_card.json",
            "nine_site_executive_summary.json",
            "release_validation.json",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(feed, indent=2, allow_nan=False) + "\n")
    print(json.dumps(feed, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
