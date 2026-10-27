#!/usr/bin/env python3
"""Publish WBG-2's corrected negative decision; never certify a stopped lane."""
import json
from html import escape
from pathlib import Path
from verify_wbg2_download import review

ROOT = Path(__file__).resolve().parents[1]


def build():
    card = json.loads((ROOT / 'evidence/wbg2/run_card.json').read_text())
    report = review()
    if not report['format_ok']:
        raise RuntimeError('Exact-file format validation failed; publication stopped')
    tif = Path(card['artifacts']['tif']).name
    body = f'''<h1>WBG-2: DO NOT SUBMIT</h1>
<p><strong>Download: YES, research only. Submit: NO. No qualifying high-scoring candidate exists.</strong></p>
<p><a href="downloads/{tif}" download>Download research TIFF</a> ·
<a href="downloads/{tif.replace('.tif','.zip')}" download>One-TIFF ZIP</a> ·
<a href="executive-summary.html">Nine-site executive summary and historical files</a></p>
<table><caption>Automatic gate decisions</caption><thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>
<tr><td>Exact-file format</td><td>PASS: one float32 band, no NaN/inf, [0,1], reference CRS/shape/transform; identical ZIP</td></tr>
<tr><td>Literal registry uniqueness</td><td>FAIL: recorded forward overlap 100% exceeds 70%; enrichment is not an exemption</td></tr>
<tr><td>Pre-placement surface gate</td><td>Not measured; provenance cannot substitute</td></tr>
<tr><td>HOLDOUT-DTI / CI / evaluator / positives</td><td>Unavailable: hide-and-recover not performed</td></tr>
<tr><td>Leaderboard estimate</td><td>Unavailable; previous regression forecast withdrawn</td></tr>
<tr><td>Organizer-confirmed result</td><td>None</td></tr>
<tr><td>Slot authorization</td><td>None; zero slots used</td></tr></tbody></table>
<p>SHA-256: <code>{card['raster_sha256']}</code></p>
<h2>Why the previous approval was revoked</h2>
<p>The old code required overlap above 70% <em>and</em> enrichment above threefold to stop.
Your protocol says overlap above 70% alone stops the lane. A dense witness may not mean
shared geology, but the literal rule is binding. No private exemption is allowed.</p>
<p>A small regression on related historical submissions cannot validate a new spatial strategy.
Its residual-only interval was not a prediction interval. No improvement over the supplied
GEMSDOE32 result is established.</p>
<h2>Why GEMSDOE32's B2 might have helped</h2>
<p>Audited B2 retains 37,654 of its parent's 44,090 dots and removes 6,436 within 200 m of
mapped faults, adding none. Deleting dots with low hidden-truth credit could reduce the
weighted false-positive penalty. Without hidden labels or artifact-linked submission receipts,
this is a plausible mechanism, not proof of causality or a verified score.</p>
<p><a href="protocol-review-20261027.md">Three-pass protocol review, limitations and next steps</a> ·
<a href="session-review-20261027.md">Nine-site session review</a> ·
<a href="research.html">Ranked geological research hypotheses</a> ·
<a href="how-to-submit.html">Submission requirements</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem and format</a></p>
<p><strong>Research name:</strong> {escape(card['submission_name'])}<br>
<strong>Note:</strong> {escape(card['submission_note'])}</p>'''
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>WBG-2 negative research result</title>
<link rel="stylesheet" href="assets/style.css"></head><body><main class="wrap">{body}</main></body></html>'''
    (ROOT / 'docs/wbg2.html').write_text(html)
    (ROOT / 'docs/wbg2-executive-summary.md').write_text(
        '# WBG-2 — DO NOT SUBMIT\n\nResearch download only. Literal overlap STOP; no qualifying holdout or leaderboard estimate.\n\n'
        '[Download TIFF](downloads/' + tif + ') · [Full executive summary](wbg2.html) · [Nine-site table](executive-summary.md)\n')
    (ROOT / 'docs/data/wbg2-corrected-preflight.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    build()
