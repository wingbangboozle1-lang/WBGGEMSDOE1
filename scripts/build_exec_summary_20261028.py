#!/usr/bin/env python3
"""Build the 2026-10-28 executive summary (JSON + Markdown + HTML).

Inputs are the pinned nine-site audit, the frozen DIFF1 run card and the verified
public leaderboard observation. Nothing here recomputes a score or relabels evidence.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NINE = ROOT / "evidence/nine_site_executive_summary_20261026.json"
DIFF1 = ROOT / "evidence/wbg5/diff1_run_card.json"
DECISION = ROOT / "docs/downloads/wbggemsdoe1-wbg5-diff1-scarp-lobe-20261028-2f3684a3f718-zeros.decision.json"
OUT_JSON = ROOT / "docs/data/executive_summary_20261028.json"
OUT_MD = ROOT / "docs/executive-summary-20261028.md"
OUT_HTML = ROOT / "docs/executive-summary-20261028.html"

LEADERBOARD_OBSERVED = {
    "date": "2026-10-28",
    "source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
    "rank1_team": "xiaofanhu",
    "rank1_score": 0.4544,
    "evidence_class": "PUBLIC-PAGE-OBSERVATION (not a project-file score)",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def build() -> dict:
    nine = load(NINE)
    diff1 = load(DIFF1)
    load(DECISION)
    # Deterministic: derive the summary timestamp from the frozen evidence card so
    # regenerating the summary is byte-for-byte reproducible (CI re-runs the builders
    # and then requires `git diff --exit-code` to be clean).
    now = diff1.get("generated_utc") or "2026-10-28T00:00:00+00:00"
    bench = diff1["benchmark"]
    arm_b = diff1["arms"]["B"]["holdout"]
    arm_c = diff1["arms"]["C"]["holdout"]
    competing = diff1["correlation_overlap_vs_registry"]["final_dots_competing_method"]
    literal = diff1["correlation_overlap_vs_registry"]["final_dots_literal"]

    rows = []
    for site in nine["sites"]:
        rows.append(
            {
                "site": site["site"],
                "file": site["historical_best_file"],
                "download_url": site["artifact_url"],
                "reported_value": site["reported_value"],
                "evidence_class": site["score_evidence_label"],
                "organizer_receipt": site["organizer_receipt_present"],
                "max_3px_overlap_vs_other_eight": site[
                    "maximum_3px_overlap_vs_other_eight_historical_masks"
                ],
                "unique_under_70_percent_rule": site["unique_under_70_percent_rule"],
                "decision": site["recommendation"],
            }
        )

    best_historical = max(rows, key=lambda r: r["reported_value"])

    diff1_row = {
        "site": "WBGGEMSDOE1 (this repository)",
        "file": diff1["submission_name"],
        "download_url": f"https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/downloads/{diff1['submission_name']}",
        "reported_value": None,
        "evidence_class": "HOLDOUT-DTI (evaluator gems-segment-pooled-v1, 60,988 withheld positives)",
        "organizer_receipt": False,
        "holdout_dti_arm_B": arm_b["dti"],
        "holdout_dti_arm_C": arm_c["dti"],
        "benchmark_dti": bench["dti"],
        "max_3px_overlap_vs_other_eight": None,
        "unique_under_70_percent_rule": False,
        "competing_method_passed": competing["competing_method_passed"],
        "max_competing_dot_overlap": competing["max_competing_dot_overlap"],
        "literal_all_entries_passed": literal["passed"],
        "decision": "DO NOT SUBMIT",
    }

    doc = {
        "schema": "gemsdoe1-executive-summary-20261028-v1",
        "generated_utc": now,
        "headline": {
            "verdict": "NO FILE APPROVED FOR SUBMISSION",
            "ok_to_download": "research only",
            "ok_to_submit": "NO",
            "best_historical_site": best_historical["site"],
            "best_historical_file": best_historical["file"],
            "best_historical_reported_value": best_historical["reported_value"],
            "best_historical_evidence_class": best_historical["evidence_class"],
            "leaderboard_rank1": LEADERBOARD_OBSERVED,
        },
        "score_governance": nine["score_governance"],
        "rows": rows,
        "new_artifact": diff1_row,
        "diff1_detail": {
            "hypothesis": diff1["hypothesis"],
            "mechanism": diff1["mechanism"],
            "named_non_fault_mimic": diff1["named_non_fault_mimic"],
            "canary_passed": diff1["leakage_canary"]["passed"],
            "max_abs_auc": max(
                max(f["pooled_auc"], 1 - f["pooled_auc"])
                for f in diff1["leakage_canary"]["features"].values()
            ),
            "surface_novelty_passed": all(
                v["passed"]
                for v in diff1["correlation_overlap_vs_registry"][
                    "surface_before_placement"
                ].values()
            ),
            "raster_sha256": diff1["raster_sha256"],
            "submission_note": diff1["submission_note"],
            "stopped_reason": diff1["stopped_reason"],
        },
        "h33_b2_explanation": nine["h33_b2_explanation"],
        "inputs": {
            "nine_site_audit": "evidence/nine_site_executive_summary_20261026.json",
            "diff1_run_card": "evidence/wbg5/diff1_run_card.json",
            "diff1_decision": "docs/downloads/wbggemsdoe1-wbg5-diff1-scarp-lobe-20261028-2f3684a3f718-zeros.decision.json",
        },
    }
    return doc


def to_markdown(doc: dict) -> str:
    h = doc["headline"]
    lines = [
        "# Executive summary — 28 October 2026",
        "",
        f"**{h['verdict']}** · DOWNLOAD: research only · SUBMIT: **NO**",
        "",
        f"Public leaderboard #1 on {LEADERBOARD_OBSERVED['date']}: **{LEADERBOARD_OBSERVED['rank1_score']}** "
        f"({LEADERBOARD_OBSERVED['rank1_team']}) — [leaderboard]({LEADERBOARD_OBSERVED['source']}). "
        "This is a public-page observation, **not** a score for any file in this repository.",
        "",
        "## Decision table — focus sites + the new DIFF1 artifact",
        "",
        "Every historical number is **OWNER-REPORTED / UNVERIFIED** (no artifact-linked DrivenData "
        "submission receipt exists). The new DIFF1 number is **HOLDOUT-DTI** (local hide-and-recover "
        "evaluator), never a leaderboard estimate. 'Unique ≤70%?' is the shared 3-pixel overlap gate "
        "against the other historical masks / the restored registry.",
        "",
        "| Site | File to download | Reported / estimate value | Evidence class | Unique ≤70%? | Decision |",
        "|---|---|---:|---|:---:|---|",
    ]
    for r in doc["rows"]:
        lines.append(
            f"| {r['site']} | [{r['file']}]({r['download_url']}) | {r['reported_value']} | "
            f"{r['evidence_class']} | {'YES' if r['unique_under_70_percent_rule'] else 'NO'} | {r['decision']} |"
        )
    d = doc["new_artifact"]
    lines.append(
        f"| {d['site']} | [{d['file']}]({d['download_url']}) | HOLDOUT-DTI {d['holdout_dti_arm_B']:.4f} "
        f"(arm C {d['holdout_dti_arm_C']:.4f}) | {d['evidence_class']} | NO | {d['decision']} |"
    )
    lines += [
        "",
        "## Which submission is the best to try?",
        "",
        f"Among the nine focus sites the largest **OWNER-REPORTED** value is "
        f"**{h['best_historical_site']} — {h['best_historical_file']} = {h['best_historical_reported_value']}**, "
        f"but it is **not organizer-confirmed** and it is **not unique** (it fails the 70% cross-site overlap "
        "gate against the other historical masks). No historical file should be copied into a new submission.",
        "",
        "The scientifically distinct candidate produced this session (WBG-5 / DIFF1) reaches only "
        f"**HOLDOUT-DTI {doc['new_artifact']['holdout_dti_arm_B']:.4f}** against the pinned promotion benchmark "
        f"**{doc['new_artifact']['benchmark_dti']:.4f}**, and it fails both novelty gates. It is a negative "
        "result, not a promotion.",
        "",
        "**No file in this repository is approved for a weekly slot.** A real upload requires, at minimum: "
        "(1) a HOLDOUT-DTI strictly above the current best with a positive paired 95% CI, (2) surface and "
        "final-dot uniqueness against the full restored registry, and (3) a separate selector authorization "
        "against the current account allowance. None of these is satisfied.",
        "",
        "## Why the GEMSDOE32 H33-B2 0.2778 is the historical leader",
        "",
        doc["h33_b2_explanation"]["mechanism_interpretation"]["evidence_supported_statement"],
        "",
        "## Limitations",
        "",
        "- No artifact-linked DrivenData receipt exists for any historical value; the 0.2778 is owner-reported.",
        "- The 19-band `training_features.tif` is not obtainable in this sandbox (DrivenData login wall), so no "
        "supervised replay of the 0.1661 benchmark is possible; promotion fails closed.",
        "- DIFF1 uses LiDAR-only inputs; it is genuinely distinct from the catalogue-based lanes but overlaps a "
        "published LiDAR-scarp submission (0.783 > 0.70), so it is not lane-unique.",
        "- The public leaderboard observation (0.4544) is a page snapshot, not a result for a project file.",
        "",
        "## Records",
        "",
        "- DIFF1 run card: [evidence/wbg5/diff1_run_card.json](../evidence/wbg5/diff1_run_card.json)",
        "- DIFF1 decision: [decision JSON](downloads/wbggemsdoe1-wbg5-diff1-scarp-lobe-20261028-2f3684a3f718-zeros.decision.json)",
        "- Three review passes (implement, bugs/edge cases, re-check vs request): "
        "[review-passes-20261028.json](data/review-passes-20261028.json)",
        "- How to submit (when a file is approved): [how-to-submit.html](how-to-submit.html)",
    ]
    return "\n".join(lines) + "\n"


def to_html(doc: dict, md: str) -> str:
    body = html.escape(md)
    body = body.replace("\n", "<br>\n")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Executive summary — WBGGEMSDOE1</title>
<link rel="stylesheet" href="styles.css"></head>
<body><main class="wrap">
<h1>Executive summary — 28 October 2026</h1>
{body}
<p><a href="index.html">Back to the research desk</a></p>
</main></body></html>
"""


def main() -> int:
    doc = build()
    md = to_markdown(doc)
    OUT_JSON.write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n")
    OUT_MD.write_text(md)
    OUT_HTML.write_text(to_html(doc, md))
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")
    print(f"wrote {OUT_HTML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
