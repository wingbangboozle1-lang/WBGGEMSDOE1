#!/usr/bin/env python3
"""Publish a fail-closed WBG-2 research and nine-site audit page.

The exact TIFF hash and recorded literal witness are checked before rendering.
No model is trained and no score or approval is inferred. Raw earlier approvals
and projections remain archived as explicitly superseded evidence.
"""
from __future__ import annotations

import hashlib
from html import escape
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


def load(name):
    return json.loads((ROOT / name).read_text())


def build():
    card = load('evidence/wbg2/run_card.json')
    safety = load('evidence/wbg2/safety_audit_20261027.json')
    nine = load('evidence/wbg2/nine_site_uniqueness.json')
    historic = load('evidence/nine_site_audit.json')['rows']
    feed = load('docs/data/feed.json')
    observation = feed['leaderboard']
    public_score = observation['public_dw_tversky']
    if not isinstance(public_score, (int, float)) or not math.isfinite(public_score) or not 0 <= public_score <= 1:
        raise ValueError('invalid dated public leaderboard observation')
    observed = observation.get('observed_utc') or observation.get('observed_date_utc') or 'date unavailable'
    score_context = ('This exceeds the supplied historical value, but' if public_score > .2778 else 'This public observation')
    sys.path.insert(0, str(ROOT / 'scripts'))
    from verify_wbg2_download import verify
    verified = verify()  # Reopen TIFF and ZIP; a local pass never authorizes upload.
    tif = Path(card['artifacts']['tif'])
    with (ROOT / tif).open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    stop = safety['already_placed_final_dots_witness']
    if not (sha == card['raster_sha256'] == safety['existing_tiff_sha256']
            and card['verdict'] == 'negative' and not card['decision']['ok_to_submit']
            and not safety['passed_literal_gate'] and stop['duplicate_by_overlap']
            and stop['my_dots_within_3px_of_theirs'] > .70
            and card['score_estimate']['value'] is None and card['holdout']['pooled_dti'] is None
            and not card['decision']['approved_for_weekly_slot']
            and verified['negative_decision_integrity_passed'] and len(nine['rows']) == 9
            and card['registry']['existing_final_dots'] == stop
            and card['registry']['surface_retrospective'] == safety['surface_witness']):
        raise ValueError('WBG-2 safety evidence or bytes changed; refusing to publish a decision')
    measured = safety['nine_champion_diagnostics']
    if len(measured) != 9 or len(historic) != 9:
        raise ValueError('nine-site evidence is incomplete')
    for row, check, source in zip(nine['rows'], measured, historic):
        if not (row['site'] == check['site'] == source['site']
                and row['sha256'] == check['sha256'] == source['sha256']
                and row['artifact'] == source['file']
                and row['immutable_file_url'] == source['immutable_file_url'] == check['source']
                and row['user_reported_historical_value'] == source['reported_historical_value']
                and row['forward_3px_overlap'] == check['my_dots_within_3px_of_theirs']
                and row['same_decoded_predictions'] == check['identical_decoded_predictions']):
            raise ValueError('nine-site evidence contradicts pinned safety audit')
    name = tif.name
    surface = safety['surface_witness']['my_dots_within_3px_of_theirs'] * 100
    final = stop['my_dots_within_3px_of_theirs'] * 100
    rows = []
    mdrows = []
    for r in nine['rows']:
        overlap = 100 * r['forward_3px_overlap']
        # This is a single champion comparison, not a claim about an entire site.
        state = 'Different from this champion' if not r['same_decoded_predictions'] else 'Same decoded pixels'
        rows.append(f'''<tr><td><strong>{escape(r['site'])}</strong></td><td class="file-cell"><a href="{escape(r['immutable_file_url'], quote=True)}">{escape(r['artifact'])}</a><div class="cell-note">Historical bytes · learning only</div></td><td><strong>{r['user_reported_historical_value']:.4f}</strong><div class="cell-note">USER-REPORTED; no receipt</div></td><td>{overlap:.2f}%<div class="cell-note">{escape(state)} · one file only</div></td><td>Unavailable</td></tr>''')
        mdrows.append(f"| {r['site']} | [{r['artifact']}]({r['immutable_file_url']}) | USER-REPORTED {r['user_reported_historical_value']:.4f}; no receipt | {overlap:.2f}% vs this champion; {state.lower()} | Unavailable |")
    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WBG-2 decision · WBG GEMS</title><meta name="description" content="Audit of the stopped WBG-2 raster, nine historical site comparisons and submission rules.">
<link rel="stylesheet" href="assets/style.css"></head><body><a class="skip" href="#main">Skip to content</a>
<header class="wrap"><nav class="nav" aria-label="Main navigation"><a class="brand" href="index.html">WBG / GEMS <small>RESEARCH DESK</small></a><div class="navlinks"><a href="index.html">Overview</a><a href="executive-summary.html">Site comparison</a><a href="research.html">Research</a><a href="how-to-submit.html">How to submit</a></div></nav></header>
<main class="wrap" id="main"><section class="subhero"><div><p class="eyebrow">Executive summary · 27 Oct 2026</p><h1>Download for research.<br><em>Do not submit.</em></h1><p class="lead">The existing WBG-2 GeoTIFF passes local file checks but fails the required literal registry gate. It has no reliable leaderboard estimate or verified holdout result. There is currently <strong>no approved upload</strong>.</p></div><span class="pill no">SUBMIT: NO</span></section>
<div class="alert"><p><strong>DOWNLOAD: YES, research only. SUBMIT: NO. Decision: NEGATIVE · DO NOT SUBMIT.</strong> The original “safe to upload” message and projection were withdrawn. A different checksum or comparison to only nine champions does not clear the all-registry rule. No weekly slot was used.</p></div>
<section class="two-col content-section"><article class="panel"><div class="panel-head">Existing research TIFF<span>NOT FOR UPLOAD</span></div><div class="panel-pad"><p class="filename">{escape(name)}</p><div class="actions"><a class="button" href="downloads/{escape(name)}" download>Download research TIFF ↓</a><a class="text-link" href="downloads/{escape(name.replace('.tif', '.zip'))}">One-TIFF ZIP ↓</a></div><p class="micro">SHA-256 <code>{sha}</code><br>Single band, float32, finite [0,1], mirrored reference grid. Local validation is not organizer acceptance.</p><p class="micro">Name: <code>{escape(card['submission_name'])}</code><br>Note: <code>{escape(card['submission_note'])}</code></p></div></article>
<article class="panel"><div class="panel-head">Automated gate review<span>Fail closed</span></div><div class="panel-pad"><p><strong>Literal overlap: {final:.4f}%</strong> of already placed dots lie within 3 px of a pinned registered lattice; limit 70%.</p><p>The retrospectively reconstructed surface overlaps the same witness by {surface:.4f}%. This is not evidence the gate was checked before placement.</p><p><strong>Catalogue buffer correction:</strong> the historic 4-step mask was Manhattan, not a 400 m Euclidean disc. {safety["catalogue_buffer_diagnostic"]["dots_less_than_400m_euclidean"]:,} existing dots are under 400 m Euclidean from the catalogue.</p><p><strong>Holdout:</strong> not available for this exact candidate; no per-feature canary or paired current-best win was found. <strong>Score estimate:</strong> unavailable.</p><a href="data/wbg2-safety.json">View exact checks and comparisons →</a></div></article></section>
<section class="content-section"><h2>Nine sites · historical records, not new upload recommendations</h2><p class="note">The table checks WBG-2 against only one hash-pinned historical champion per site. Percentages use the shared Euclidean 3-pixel test. The actual registry is broader; the lattice already makes the overall decision negative. Reported values come from the user's historical list, not an organizer submission-page receipt. On narrow screens, scroll the table horizontally to see every column.</p><div class="table-wrap"><table id="wbg2-site-table"><thead><tr><th scope="col">Site</th><th scope="col">Historical file to inspect</th><th scope="col">Historical claim</th><th scope="col">WBG-2 overlap / limited comparison</th><th scope="col">Estimated leaderboard score</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section class="content-section prose"><h2>Why GEMSDOE32's B2 might have performed well</h2><p>In the prior pixel audit, D2.8 had 44,090 dots, B1 40,199, and B2 37,654 after removing dots close to the mapped catalogue. GEMSDOE25 and GEMSDOE30 have the same decoded dot field; GEMSDOE36 contains B2 and 1,200 additions. These related fields are not nine independent discoveries.</p><p>The organizer's 300 m triangular kernel gives diminishing distance credit, and α=0.2 reduces the penalty for false positives while β=0.8 penalizes missed positives. Removing redundant predictions could improve the metric if they contributed little hidden-fault coverage. The hidden labels and a file-specific receipt are unavailable, so neither the exact reason for the reported 0.2778 nor an improvement beyond it is established. A 200 m or 400 m exclusion is not an organizer rule; the WBG-2 buffer was a four-step Manhattan mask, not a true 400 m Euclidean disc.</p><p><strong>Could a genuinely unique file beat 0.2778?</strong> In principle, yes. The <a href="{escape(observation['source'], quote=True)}">official public leaderboard</a> recorded {public_score:.4f} ({escape(observed)}). {score_context} does not demonstrate that any candidate in this repository is both unique under the stated registry rule and better; WBG-2 is not such a candidate. A credible answer requires a properly gated and measured prospective test.</p><p>Fault likelihood is not proof of geothermal vents, permeability or economically recoverable resources. See <a href="https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and">USGS blind-system research</a> and the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem and metric</a>.</p></section>
<section class="content-section prose"><h2>What must happen before a future upload</h2><ol><li>Assign one prospective method lane and address the literal saturated-registry obstruction centrally; do not optimize around its uncovered holes.</li><li>Run feature canaries and visible-only, buffered whole-segment holdout. Beat a reproducible same-evaluator current-best baseline with appropriate paired uncertainty.</li><li>Pass both pre-placement and final-dot registry checks, exact TIFF/ZIP checks, and a separate selector with current account allowance. Only then use the official submission form and retain its receipt.</li></ol><p><a href="how-to-submit.html">Step-by-step submission guide</a> · <a href="research/future-hypotheses-20261027.md">Four untested hypotheses and official sources</a> · <a href="data/wbg2-run-card.json">Run card JSON</a> · <a href="data/wbg2-safety.json">Safety audit JSON</a> · <a href="data/wbg2-review-passes-20261027.json">Three safety-review passes</a></p></section>
</main><footer class="wrap footer"><p>WBG / GEMS · Evidence before a weekly slot. No model training or upload was performed by this page.</p></footer></body></html>'''
    (DOCS / 'wbg2.html').write_text(body, encoding='utf-8')
    md = f'''# WBG-2 executive summary — 27 October 2026

**DOWNLOAD: YES, research only. SUBMIT: NO.** No approved competition TIFF or reliable leaderboard estimate exists.

[Research TIFF](downloads/{name}) · [ZIP](downloads/{name.replace('.tif','.zip')}) · SHA-256 `{sha}` · [safety audit](data/wbg2-safety.json) · [run card](data/wbg2-run-card.json)

Local all-finite, [0,1], grid and one-TIFF-ZIP checks passed. They do not prove organizer acceptance. The exact file's **REGISTRY-MEASUREMENT** is {final:.4f}% overlap against the pinned lattice (limit 70%); the retrospectively reconstructed prior is {surface:.4f}%. This is a STOP, not scientific similarity or global uniqueness. WBG-2 has no reproducible HOLDOUT-DTI / CI and no reliable score estimate. Zero slots used. The historical four-step Manhattan buffer is not a 400 m Euclidean disc: {safety["catalogue_buffer_diagnostic"]["dots_less_than_400m_euclidean"]:,} dots are within 400 m Euclidean.

## Nine historical champions

Only one champion per site was checked. Values are user-reported, with no file-specific organizer receipts. No historical file is recommended for a new submission.

| Site | Historical file to inspect | Historical value | WBG-2 vs this one champion | New-file score estimate |
|---|---|---|---|---|
{chr(10).join(mdrows)}

**Why B2?** The recorded lineage is D2.8 (44,090 dots) → B1 (40,199) → B2 (37,654) through catalogue-near pruning. Removing redundant low-credit pixels may help the official distance-weighted Tversky metric, but the hidden labels and receipt are unavailable. The claim 0.2778 and its cause remain unverified. Removing mapped-fault-adjacent pixels can also remove genuinely new nearby faults.

The official public leaderboard recorded {public_score:.4f} ({observed}); this is not a score for any project file. [Dated provenance feed](data/feed.json) · [three safety-review passes](data/wbg2-review-passes-20261027.json).

See [official metric and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [research hypotheses](research/future-hypotheses-20261027.md), and [future submission guide](how-to-submit.html).
'''
    (DOCS / 'wbg2-executive-summary.md').write_text(md, encoding='utf-8')
    (DOCS / 'data').mkdir(exist_ok=True)
    bundle = {'run_card': card, 'safety_audit': safety, 'nine_champion_diagnostics': nine,
              'warning': 'Current decision supersedes raw historical approvals; no forecast or upload authorization.'}
    for fname, data in [('wbg2.json', bundle), ('wbg2-safety.json', safety), ('wbg2-run-card.json', card)]:
        (DOCS / 'data' / fname).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    print('Built WBG-2 negative research page; no upload is approved.')


if __name__ == '__main__':
    build()
