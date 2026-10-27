#!/usr/bin/env python3
"""Publish the corrected WBG-2 audit and nine-site comparison; never select a slot."""
from __future__ import annotations
import hashlib
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def load(rel):
    return json.loads((ROOT / rel).read_text())


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build():
    card = load("evidence/wbg2/run_card.json")
    artifact = ROOT / card["artifact"]
    if (card["verdict"] != "negative" or card["ok_to_submit"] is not False
            or card["leaderboard_estimate"] is not None or file_hash(artifact) != card["raster_sha256"]):
        raise ValueError("WBG-2 decision or artifact identity drift; do not publish")
    audit = load("evidence/nine_site_audit.json")
    explanations = {
        "GEMSDOE24": "D1.5 ridge-thinning family; its registry includes the lattice that stops WBG-2.",
        "GEMSDOE25": "D2.8 parent; its positive-pixel set matches the GEMSDOE30 file.",
        "GEMSDOE27": "Topographic gap-closure variant; no causal advantage is established.",
        "GEMSDOE28": "Rung30 is the highest supplied historical value among its listed variants.",
        "GEMSDOE30": "Re-encodes the same D2.8 positive-pixel set as GEMSDOE25.",
        "GEMSDOE31": "SOLO D2.8 family; related to the GEMSDOE28 variant.",
        "GEMSDOE32": "B2 removes catalogue-adjacent dots from the D2.8 parent; it adds none.",
        "GEMSDOE33": "A tip/stepover variant in the same inherited field family.",
        "GEMSDOE36": "Contains B2 plus additional support; not an independent clean benchmark.",
    }
    rows, mdrows = [], []
    for row in audit["rows"]:
        site = row["site"]
        value = row["reported_historical_value"]
        relation = explanations[site]
        rows.append(f'''<tr><td><strong>{escape(site)}</strong><br><a href="{escape(row['snapshot_url'], quote=True)}">Pinned source ↗</a></td>
<td class="file-cell"><a href="{escape(row['immutable_file_url'], quote=True)}">{escape(row['file'])}</a><br><small>Historical reference only; do not resubmit as new.</small></td>
<td><strong>{value:.4f}</strong><br><small>USER-REPORTED; no receipt</small></td><td>{escape(relation)}<br><strong>Not a unique new submission</strong></td></tr>''')
        mdrows.append(f"| {site} | [{row['file']}]({row['immutable_file_url']}) | USER-REPORTED {value:.4f}; no receipt | Historical; do not resubmit. {relation} |")
    lattice, c1 = card["registry"]["rows"]
    tif = artifact.name
    number = 100 * lattice["forward_overlap_within_3px"]
    note = escape(card["submission_note"])
    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WBG-2 audit and nine-site comparison · WBG GEMS</title><meta name="description" content="Corrected research-only WBG-2 decision and nine-site historical evidence.">
<link rel="stylesheet" href="assets/style.css"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"></head>
<body><a class="skip" href="#main">Skip to content</a><header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation"><a class="brand" href="index.html"><span>WBG / GEMS<small>FAULT MAPPING · RESEARCH DESK</small></span></a><div class="navlinks"><a href="index.html">Overview</a><a class="active" href="wbg2.html">WBG-2 audit</a><a href="executive-summary.html">Site comparison</a><a href="research.html">Research</a><a href="evidence.html">Evidence</a><a href="how-to-submit.html">How to submit</a></div></nav></div></header>
<main class="wrap" id="main"><div class="breadcrumb">GEMS prize challenge <span>/</span> Corrected audit <span>/</span> 27 OCT 2026</div>
<section class="subhero"><div><p class="eyebrow">Executive decision · no slot selected</p><h1>Research download.<br><em>Not a submission.</em></h1><p class="lead">WBG-2 is a previous genuinely generated TIFF. Its exact bytes pass local format checks, but it fails the literal registry-overlap gate. No current file is approved to submit.</p><div class="actions"><a class="button secondary" href="downloads/{escape(tif)}" download>Download TIFF for research ↓</a><a class="text-link" href="downloads/{escape(tif.replace('.tif','.zip'))}">Identical one-TIFF ZIP ↓</a></div></div><span class="pill no"><span class="dot"></span>SUBMIT: NO</span></section>
<div class="alert" role="note"><p><strong>DOWNLOAD: YES, for research only. SUBMIT: NO.</strong> The previous green approval and regression forecast are withdrawn. The automated shared-template audit measured <strong>{number:.4f}%</strong> of WBG-2 dots within three pixels of a registered GEMSDOE24 lattice, above the 70% STOP limit. This literal protocol can flag unrelated dense or space-filling fields; it is an obstruction, not proof of copied geology. <a href="data/wbg2-review.json">Full run card →</a></p></div>
<section class="stats" aria-label="Decision metrics"><div class="stat"><label>Current file</label><div class="value word bad">Do not submit</div><p>Format pass ≠ approval<br>Selection is separate.</p></div><div class="stat"><label>HOLDOUT-DTI</label><div class="value word">Unavailable</div><p>No qualifying visible-only test<br>CI and withheld count unavailable.</p></div><div class="stat"><label>Registry overlap</label><div class="value bad">{number:.2f}%</div><p>3 px forward · {escape(lattice['repo'])} lattice<br>Literal limit 70% · FAIL</p></div><div class="stat"><label>Leaderboard estimate</label><div class="value word">Unavailable</div><p>No artifact-linked receipt<br>No validated forecast.</p></div></section>
<section class="section"><div class="section-heading"><div><span class="section-num">01 / DECISION TABLE</span><h2>Files and evidence, at a glance.</h2><p>Historical file links support education and verification, not copying into a new entry. Scores are user-reported, not organizer-confirmed.</p></div></div><div class="table-wrap"><table><thead><tr><th>Site</th><th>File</th><th>Reported historical score</th><th>Uniqueness and decision</th></tr></thead><tbody>
<tr class="featured"><td><strong>WBG-2</strong><br>This project</td><td class="file-cell"><a href="downloads/{escape(tif)}" download>{escape(tif)}</a><br><small>Research download only</small></td><td><strong>Unavailable</strong><br><small>No HOLDOUT-DTI or organizer result</small></td><td><strong>FAIL · {number:.4f}% overlap</strong><br>GEMSDOE24 registered lattice; SUBMIT: NO</td></tr>{''.join(rows)}</tbody></table></div><p class="note">The old nine-champion audit was incomplete: one artifact per site cannot certify all site rasters. It also used a different neighborhood and a sampled correlation. The lattice is a second GEMSDOE24 registry file and is a decisive counterexample.</p></section>
<section class="section"><div class="section-heading"><div><span class="section-num">02 / WHY THE HISTORICAL LEADER?</span><h2>Evidence is narrower than the story.</h2></div></div><div class="two-col"><article class="mini-card"><span class="index">EXACT PIXEL ANCESTRY</span><h3>GEMSDOE32 B2</h3><p>Measured comparison: B2 is a subset of D2.8. It removes 6,436 parent dots within two pixels of the public catalogue and adds none. The user-reported B2 value is <strong>0.2778</strong>; no artifact-linked organizer receipt is available.</p><p>Removing low-value false positives could improve the weighted denominator. Hidden fault locations and actual per-dot credit are unknown, so that explanation is plausible—not established causation.</p><a href="research/wbg2-why-02778.md">Read the corrected forensic note →</a></article><article class="mini-card"><span class="index">CAN WE BEAT IT?</span><h3>Possible, not demonstrated.</h3><p>No current file has a valid same-instrument holdout improvement, final uniqueness clearance and separate selector decision. The former regression was fitted to unverified, correlated and partly duplicated historical observations; its in-sample residual interval is not a reliable forecast.</p><p>The official public leaderboard was observed at <strong>0.4544</strong> on 27 October 2026. That public observation is not a score for any file here. <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Review leaderboard ↗</a></p></article></div></section>
<section class="section"><div class="section-heading"><div><span class="section-num">03 / AUTOMATED CHECKS</span><h2>What passed—and what did not.</h2></div></div><div class="two-col"><article class="panel"><div class="panel-head">Exact-file preflight<span>Local, not organizer acceptance</span></div><div class="panel-pad"><ul class="gate-list"><li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>GeoTIFF and ZIP</b><small>One float32 band, CRS/shape/affine match the pinned mirror, whole array finite and in [0,1], ZIP bytes identical.</small></div></li><li><span class="gate-icon fail">×</span><div class="gate-copy"><b>Literal final-dot uniqueness</b><small>{number:.4f}% against GEMSDOE24 lattice and {100*c1['forward_overlap_within_3px']:.0f}% against the registered continuous WBG-C1 surface.</small></div></li><li><span class="gate-icon fail">×</span><div class="gate-copy"><b>Pre-placement gate and valid holdout</b><small>Not established; no current-best paired improvement or feature-by-feature canary clearance.</small></div></li><li><span class="gate-icon wait">—</span><div class="gate-copy"><b>Separate selector / weekly allowance</b><small>No authenticated account allowance or promotion; no slot used.</small></div></li></ul></div></article><article class="mini-card"><span class="index">EXACT IDENTITY</span><h3>Reproducible audit</h3><p class="mono">SHA-256 {card['raster_sha256']}</p><p>Name: <code>{escape(card['submission_name'])}</code><br>Research note: <code>{note}</code></p><p>Run <code>python scripts/review_wbg2.py --check</code>. The audit restores one SHA-pinned public witness if absent; it does not place dots, train or upload.</p><a href="how-to-submit.html">Guide for a future approved file →</a></article></div></section>
<section class="section"><div class="section-heading"><div><span class="section-num">04 / SOURCES & NEXT STEPS</span><h2>Build on the evidence.</h2></div></div><div class="prose"><p>The actual competition target is geological faults, not confirmed geothermal vents. The official problem uses a 300 m triangular kernel, alpha 0.2 and beta 0.8. The organizer requires all-fault predictions and explains an expert-reviewed final round.</p><p>Reproduced 19 cached-band hashes from a public owner mirror, not an authenticated DrivenData download. Resolve the missing assigned method, the literal registry-saturation obstruction, original band semantics and a clean paired benchmark before any future hypothesis is executed.</p><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem and format ↗</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules ↗</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN ↗</a> · <a href="https://gdr.openei.org/submissions/1391">DOE INGENIOUS data ↗</a> · <a href="data/wbg2-review.json">Reproduced audit JSON ↗</a> · <a href="research/source-and-wbg2-review.md">Line-by-line source review ↗</a> · <a href="data/wbg2-review-passes.json">Three review passes ↗</a></p></div></section></main><footer class="footer"><div class="wrap footer-inner"><p>Evidence before a weekly slot. Fault predictions are not verified geothermal vents.</p><a href="standing-prompt.md">Standing request</a></div></footer></body></html>'''
    (DOCS / "wbg2.html").write_text(body, encoding="utf-8")
    markdown = ["# WBG-2 executive audit — 27 October 2026", "", "**DOWNLOAD: YES for research only. SUBMIT: NO.** No new experiment or competition slot was used.", "", f"[Research TIFF](downloads/{tif}) · [identical ZIP](downloads/{tif.replace('.tif','.zip')}) · [corrected run card](data/wbg2-review.json)", "", f"Local format pass. Literal GEMSDOE24 lattice overlap **{number:.4f}%** (>70%); no qualifying visible-only HOLDOUT-DTI or credible leaderboard estimate. This protocol failure is not proof of copied geology.", "", "| Site | Historical file | Score evidence | Uniqueness and decision |", "|---|---|---|---|", *mdrows, "", "B2 is a strict subset of D2.8: 6,436 parent dots were removed within 200 m of the public catalogue; none added. Removing low-marginal-credit false positives might improve DTI, but hidden labels and submission receipts are unavailable. The old regression forecast and interval are withdrawn.", "", "[Official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [Official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [DOE INGENIOUS](https://gdr.openei.org/submissions/1391)", ""]
    (DOCS / "wbg2-executive-summary.md").write_text("\n".join(markdown), encoding="utf-8")
    (DOCS / "data/wbg2.json").write_text(json.dumps({"schema":"wbg2-page-bundle-v2", "run_card":card}, indent=2, allow_nan=False) + "\n")
    print("Built corrected WBG-2 audit page and nine-site table; no submission authorized.")


if __name__ == "__main__":
    build()
