#!/usr/bin/env python3
"""Render the inherited WBG-H1 result *without* its unsafe upload advice.

The frozen research card, TIFF, evidence JSON, and archived earlier site are not
edited. The older subsite falsely called owner-reported scores organizer-confirmed,
recommended negative candidates as backups, and linked a negative TIFF directly
to an upload walkthrough. These pages are a read-only safety correction, not a
new experiment, score, or change to an inherited scientific result.
"""
from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/wbg-h1-dpgf1"


def read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text())


def file_digest(relative: str) -> str:
    with (ROOT / relative).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def page(title: str, body: str) -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · WBG-H1 archived research</title><link rel="stylesheet" href="../assets/style.css"></head><body>
<a class="skip" href="#main">Skip to content</a><header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">
<a class="brand" href="../index.html">WBG / GEMS <small>RESEARCH DESK · INHERITED WBG-H1</small></a>
<div class="navlinks"><a href="../index.html">Current decision</a><a href="../executive-summary.html">Nine sites</a><a href="../how-to-submit.html">Submission rules</a></div></nav></div></header>
<main id="main" class="wrap"><div class="breadcrumb">Frozen 26 Oct 2026 lane / WBG-H1</div>
<section class="subhero"><div><p class="eyebrow">Archived negative result · not a selector recommendation</p><h1>DOWNLOAD: YES, for research.<br><em>SUBMIT: NO.</em></h1><p class="lead">This file passes local format checks but fails the literal all-registry uniqueness gate and does not beat the strongest cited holdout reference. No final live slot was approved or spent.</p></div><span class="pill no"><span class="dot" aria-hidden="true"></span>DO NOT SUBMIT</span></section>
<div class="alert" role="note"><p><strong>DO NOT SUBMIT this or any of the nine historical files.</strong> The earlier version of this subsite labelled owner claims “organizer-confirmed” and treated sparse-peer-only comparisons as permission to upload. Neither is justified. It also contained speculative hidden-label inversions and absolute claims about the old range error. These are <strong>not verified facts</strong>; the frozen research receipts remain available for audit. No final dots were placed in the *separate* WBG-C1 lane, and no competition slot was used there.</p></div>
{body}</main><footer class="footer"><div class="wrap footer-inner"><p>Fault predictions are not verified geothermal vents. Local format validation is not organizer acceptance.</p><div><a href="../index.html">Current verdict</a><a href="../data/run-card.json">Current run card</a></div></div></footer></body></html>'''


def render():
    rc = read("evidence/wbg_h1/run_card.json")
    nine = read("evidence/nine_site_audit.json")
    feed = read("docs/data/feed.json")
    if rc["verdict"] != "negative":
        raise ValueError("inherited WBG-H1 decision changed; do not publish without new reviewed evidence")
    paths = rc["raster_sha256"]
    for suffix in ("tif", "zip"):
        if file_digest(paths[f"{suffix}_file"]) != paths[f"{suffix}_sha256"]:
            raise ValueError(f"inherited WBG-H1 {suffix} bytes no longer match frozen run card")
    if len(nine["rows"]) != 9 or any(r.get("organizer_submission_receipt") is not None for r in nine["rows"]):
        raise ValueError("historical score evidence changed; review before publishing")
    h = rc["holdout_dti"]
    tif = Path(paths["tif_file"]).name
    zip_name = Path(paths["zip_file"]).name
    baseline = h["baseline_b0_dti"]
    overlap = rc["registry_correlation_and_overlap"]["literal_oneway_vs_r13_space_filling_lattice_ir_wbg1_01"]
    if overlap <= .7 or h["dti"] >= .163792:
        raise ValueError("the frozen negative conclusion needs new review")
    if not (0 < len(rc["submission_note"]) <= 140):
        raise ValueError("invalid frozen note")

    measured = f'''<section class="content-section"><h2>The exact inherited result</h2><div class="two-col">
<article class="panel"><div class="panel-head">Research-only artifact <span class="pill no">No live slot</span></div><div class="panel-pad">
<div class="filename">{escape(tif)}</div><div class="actions"><a class="button" download href="../downloads/{escape(tif)}">Download research TIFF ↓</a><a class="button secondary" download href="../downloads/{escape(zip_name)}">One-TIFF ZIP ↓</a></div>
<p class="micro">SHA-256: <code>{escape(paths['tif_sha256'])}</code><br>Research name: <code>{escape(rc['submission_name'])}</code><br>Research note (not upload advice): <code>{escape(rc['submission_note'])}</code></p>
</div></article><article class="panel"><div class="panel-head">Scientific &amp; format gates</div><div class="panel-pad prose">
<p><strong>HOLDOUT-DTI {h['dti']:.6f}</strong> · 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}] · evaluator <code>{escape(h['evaluator_version'])}</code> · {h['n_withheld_positives']:,} withheld positives. Matched control HOLDOUT-DTI {baseline:.6f}, 95% CI [{h['baseline_b0_ci95'][0]:.6f}, {h['baseline_b0_ci95'][1]:.6f}] on that evaluator/count. Different instruments and output representations are not automatically comparable.</p>
<p><strong>Strict literal novelty: FAIL.</strong> {overlap*100:.2f}% of these dots are within 3 px of a registered spacing-5 lattice (70% ceiling); the inherited sparse-only calculation is not a waiver. Local saved-byte format checks passed; that is not an organizer receipt. The historical 0.2778 value is <strong>OWNER-REPORTED / UNVERIFIED</strong>, not this TIFF's score.</p>
<p><a href="data/run_card.json">Frozen WBG-H1 card ↗</a> · <a href="../data/parallel-main-integration.json">Integration provenance ↗</a> · <a href="../executive-summary.html">Current nine-site decision ↗</a></p>
</div></article></div></section>'''
    rows = []
    for r in nine["rows"]:
        rows.append(f'''<tr><td>{escape(r['site'])}</td><td><a href="{escape(r['immutable_file_url'], quote=True)}">{escape(r['file'])}</a><br><small>Historical audit only</small></td>
<td>USER-REPORTED {r['reported_historical_value']:.4f}<br><small>NOT ORGANIZER-CONFIRMED</small></td><td>No calibrated estimate</td><td>DO NOT SUBMIT · peer-overlap gate fails</td></tr>''')
    summary = f'''<section class="content-section"><h2>Nine-site executive comparison</h2><p>Frozen historical claims and byte-inspected files from the 26 Oct audit; none is a new or submit-ready artifact. Current project score estimates are unavailable without artifact-linked receipts and an out-of-sample calibration. Some upstream repositories have changed since this audit. The public rank-one observation on {escape(feed['leaderboard']['observed_date_utc'])} was {feed['leaderboard']['public_dw_tversky']:.4f}, <strong>not a project TIFF score</strong>; <a href="{escape(feed['leaderboard']['source'],quote=True)}">check the official page ↗</a>.</p>
<div class="table-wrap"><table><caption>Nine historical sites — owner claims only, no submission clearance</caption><thead><tr><th>Site</th><th>Pinned learning-only file</th><th>Historical claim</th><th>New-file estimate</th><th>Current decision</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>'''
    science = '''<section class="content-section prose"><h2>What 0.2778 does and does not mean</h2><p>The GEMSDOE32 B2 dot field is an exact <em>subset</em> of the earlier D2.8 field: 44,090 dots minus 6,436 within 200 m of mapped public faults = 37,654 dots, with no additions. Removing predictions with little hidden-truth credit could reduce the 0.2-weighted false-positive denominator while preserving true-positive coverage. This is a plausible metric mechanism, <strong>not a proved causal account</strong> or a new fault discovery: the private labels and exact-artifact submission receipt are unavailable. See the <a href="../data/nine-site-audit.json">byte audit</a> and <a href="../executive-summary.html">current executive summary</a>.</p><p>USGS <a href="https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and">blind-system research</a> emphasizes convergent geological, geophysical, temperature and drilling evidence; a fault-prediction TIFF alone cannot validate a geothermal resource. Review the <a href="../research.html">prospective hypothesis queue and scientific limitations</a>.</p></section>'''
    instruction = '''<section class="content-section prose"><h2>How to submit a future promoted file</h2><ol><li>Pass the buffered whole-segment holdout, paired current-best and leakage checks.</li><li>Pass the literal surface <em>and</em> final-dot registry gates. This file fails.</li><li>Reopen the exact all-finite [0,1] GeoTIFF and one-file ZIP; check CRS/shape/transform against the pinned grid.</li><li>Seek a separate selector decision and independently check the logged-in account's remaining slots. Only then follow the <a href="../how-to-submit.html">current step-by-step guide</a>.</li></ol><p>Official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">format and metric</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules §3.4–3.5</a>. No current file has passed the selector.</p></section>'''
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page("WBG-H1 negative research", measured + summary + science), encoding="utf-8")
    (OUT / "executive-summary.html").write_text(page("WBG-H1 safe submission guide", measured + summary + instruction), encoding="utf-8")
    print("Published read-only WBG-H1 negative pages; archived science and bytes unchanged.")


def main():
    render()


if __name__ == "__main__":
    main()
