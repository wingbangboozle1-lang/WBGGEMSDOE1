#!/usr/bin/env python3
"""Render the frozen-download decision table from the exact-file review receipt."""
from __future__ import annotations

import hashlib
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build():
    source = ROOT / "evidence/release_review_20261027.json"
    data = json.loads(source.read_text())
    rows = []
    for r in data["rows"]:
        # A changed file/card must never keep an old green format badge.
        if (sha(ROOT / r["artifact"]) != r["expected_raster_sha256"]
                or sha(ROOT / r["source_card"]) != r["source_card_sha256"]):
            raise ValueError("release-review identity is stale; rerun exact-file review")
        if r["ok_to_submit"] or r["leaderboard_estimate"] is not None:
            raise ValueError("this frozen negative-result desk cannot authorize a submission or forecast")
        h = r["holdout"]
        name = Path(r["artifact"]).name
        rows.append(f'''<tr><td class="file-cell"><strong>{escape(r['lane'])}</strong><br>
<a href="downloads/{escape(name)}" download>{escape(name)}</a><br><small>Research download only</small></td>
<td>HOLDOUT-DTI <strong>{h['dti']:.6f}</strong><br>95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]<br>
<code>{escape(h['evaluator_version'])}</code><br>{h['withheld_positive_pixels']:,} withheld positives<br>Recorded prior measurement, not rerun.</td>
<td>Unavailable; no artifact-linked organizer receipt.</td>
<td>{'PASS' if r['ok_to_download'] else 'FAIL'} local format and identity<br><strong>SUBMIT: NO</strong><br>
Recorded forward overlap: {r['recorded_forward_3px_overlap']*100:.4f}%<br>{escape(r['registry_scope'])}<br>
{escape(r['reason'])}</td></tr>''')
    corrections = ''.join(f'<li>{escape(s)}</li>' for s in data["reporting_corrections"])
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>All research downloads — submission decisions</title>
<link rel="stylesheet" href="assets/style.css"></head><body>
<a class="skip" href="#main">Skip to content</a><main id="main" class="wrap review-page">
<nav><a href="index.html">Research desk</a> · <a href="executive-summary.html">Nine-site executive summary</a> ·
<a href="how-to-submit.html">Submission guide</a></nav>
<h1>Which file should I submit?</h1><section class="notice"><h2>None currently. DOWNLOAD: YES (research only). SUBMIT: NO.</h2>
<p>All four frozen local TIFFs passed revalidation on 2026-10-27, but none clears the scientific and literal uniqueness requirements.
No new TIFF was generated, no stopped lane was rerun, no final dots were placed for WBG-C1, and no competition slot was used.</p>
<p><a href="data/release-review.json">Download the machine-readable exact-file review</a> ·
<a href="review-20261027.md">Review findings and next steps</a> ·
<a href="data/review-run-card.json">Follow-up JSON run card</a></p></section>
<div class="table-wrap"><table><thead><tr><th>File to download</th><th>Recorded local evidence</th>
<th>Estimated leaderboard result</th><th>Unique and OK to submit?</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>These evaluator/split/representation combinations differ. Do not sort this table as a common leaderboard or select a slot from these values.
Format PASS is a local result, not organizer acceptance. Registry observations are dated and scope-limited, not a fresh global novelty check.</p>
<h2>Reporting corrections</h2><ul>{corrections}</ul>
<h2>How to reproduce the automatic check</h2>
<pre>.venv/bin/python scripts/review_releases.py --check</pre>
<p>This reopens all exact TIFFs with the unchanged shared validator, compares source-card and raster hashes, and checks the committed report.
It does not train, emit dots, relax novelty thresholds, select a weekly slot or upload anything.</p>
<h2>Official references and access limits</h2>
<p><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">Official reference repository (verified GitHub commit)</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem and format</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official public leaderboard</a></p>
<p>The current sandbox permits GitHub and package registries, not DrivenData, USGS, GDR, Dropbox or the rules PDF host.
Prior dated official-page observations remain historical; they are not fresh verification of today's leaderboard, license or account allowance.</p>
</main></body></html>'''
    (ROOT / "docs/release-review.html").write_text(page, encoding="utf-8")
    (ROOT / "docs/data/release-review.json").write_bytes(source.read_bytes())


if __name__ == "__main__":
    build()
