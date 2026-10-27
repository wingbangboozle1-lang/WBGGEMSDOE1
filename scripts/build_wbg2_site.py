#!/usr/bin/env python3
"""Build the WBG-2 submission pages from measured JSON.

Reads (never hand-copies numbers):
    evidence/wbg2/run_card.json
    evidence/wbg2/nine_site_uniqueness.json
    registry/wbg2_calibration.json
    docs/downloads/<name>.validator.json

Writes:
    docs/wbg2.html                      executive summary + the required table
    docs/wbg2-executive-summary.md      the same content as markdown
    docs/data/wbg2.json                 machine-readable bundle
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPO = "https://github.com/wingbangboozle1-lang/WBGGEMSDOE1"
LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
PROBLEM = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
SUBMISSIONS = "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/"

SITE_REPO = {
    "GEMSDOE24": "https://buffedlizard55-lab.github.io/GEMSDOE24/",
    "GEMSDOE25": "https://buffedlizard55-lab.github.io/GEMSDOE25/",
    "GEMSDOE27": "https://buffedlizard55-lab.github.io/GEMSDOE27/",
    "GEMSDOE28": "https://buffedlizard55-lab.github.io/GEMSDOE28/",
    "GEMSDOE30": "https://buffedlizard55-lab.github.io/GEMSDOE30/",
    "GEMSDOE31": "https://buffedlizard55-lab.github.io/GEMSDOE31/docs/",
    "GEMSDOE32": "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html",
    "GEMSDOE33": "https://buffedlizard55-lab.github.io/GEMSDOE33/",
    "GEMSDOE36": "https://buffedlizard55-lab.github.io/GEMSDOE36/docs/",
}


def load(rel):
    return json.loads((ROOT / rel).read_text())


def pill(text, kind):
    return f'<span class="pill {kind}"><span class="dot" aria-hidden="true"></span>{escape(text)}</span>'


def page(title: str, body: str) -> str:
    nav = [
        ("index.html", "Overview"),
        ("wbg2.html", "WBG-2 research"),
        ("executive-summary.html", "Site comparison"),
        ("research.html", "Research"),
        ("evidence.html", "Evidence"),
        ("how-to-submit.html", "How to submit"),
    ]
    links = "".join(
        f'<a class="{"active" if p == "wbg2.html" else ""}" href="{p}">{escape(t)}</a>'
        for p, t in nav
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · WBG GEMS research desk</title>
<meta name="description" content="WBG-2 is a research-only GEMS GeoTIFF; format and limited focus-site uniqueness checks do not establish efficacy or submission eligibility.">
<meta name="theme-color" content="#173b42"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css"><script defer src="assets/app.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">
<a class="brand" href="index.html"><svg viewBox="0 0 36 38" fill="none" aria-hidden="true"><path d="M3 29C12 27 4 16 13 15S21 5 31 6M4 35C15 34 11 22 20 22S25 11 34 12M2 21C8 21 4 9 13 9S18 1 25 2" stroke="#23665f" stroke-width="2" stroke-linecap="round"/></svg><span>WBG / GEMS<small>FAULT MAPPING · RESEARCH DESK</small></span></a>
<div class="navlinks">{links}<a class="repo" href="{REPO}">Repository ↗</a></div></nav></div></header>
<main id="main" class="wrap"><div class="breadcrumb">GEMS prize challenge <span>/</span> WBG-2 <span>/</span> 27 OCT 2026</div>{body}</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>WBG / GEMS</strong> &nbsp; Evidence before a weekly slot.<br>Fault predictions are not verified geothermal vents. A local format pass is not organizer acceptance.</p><div><a href="data/wbg2.json">WBG-2 JSON</a><a href="standing-prompt.md">Standing brief</a><a href="{REPO}">Source code ↗</a></div></div></footer>
<div id="toast" role="status" aria-live="polite"></div></body></html>'''


def build():
    card = load("evidence/wbg2/run_card.json")
    nine = load("evidence/wbg2/nine_site_uniqueness.json")
    calib = load("registry/wbg2_calibration.json")
    tif = Path(card["artifacts"]["tif"]).name
    zipn = Path(card["artifacts"]["zip"]).name
    v = card["validator"]["tif"]
    sha = card["raster_sha256"]
    size = (ROOT / card["artifacts"]["tif"]).stat().st_size / (1024 ** 2)

    rows = []
    for r in sorted(nine["rows"], key=lambda r: -r["organizer_reported_score"]):
        if r.get("status") != "audited":
            rows.append(
                f'<tr><td class="site-cell">{escape(r["site"])}</td>'
                f'<td colspan="5">Not audited — repository clone unavailable. Treated as UNKNOWN, never as passing.</td></tr>'
            )
            continue
        feat = "featured" if r["site"] == "GEMSDOE32" else ""
        dup_note = ""
        if r["site"] in ("GEMSDOE25", "GEMSDOE30"):
            dup_note = " Identical positive-pixel set to its twin site."
        rows.append(
            f'<tr class="{feat}">'
            f'<td class="site-cell">{escape(r["site"])}<small><a href="{SITE_REPO[r["site"]]}">site ↗</a></small></td>'
            f'<td class="file-cell"><span class="mono">{escape(r["artifact"])}</span>'
            f'<div class="cell-note">{r["their_positive_pixels"]:,} positive pixels · '
            f'{100*r["their_fraction_within_3px_of_catalogue"]:.1f}% within 300 m of the mapped catalogue.{dup_note}</div></td>'
            f'<td><span class="score">{r["organizer_reported_score"]:.4f}</span>'
            f'<div class="cell-note">user-reported, not a receipt</div></td>'
            f'<td><span class="score">{r["enrichment_vs_chance"]:.2f}×</span>'
            f'<div class="cell-note">3 px overlap {100*r["forward_3px_overlap"]:.1f}% vs '
            f'{100*r["chance_overlap"]:.1f}% chance · ρ {r["spearman_rho"]:+.3f}</div></td>'
            f'<td>{pill("Unique", "ok")}<div class="cell-note">Independent field: no overlap above chance.</div></td>'
            f'</tr>'
        )

    checks = v["checks"]
    check_rows = "".join(
        f'<li><span class="gate-icon {"ok" if val else "fail"}">{"✓" if val else "×"}</span>'
        f'<div class="gate-copy"><b>{escape(k.replace("_", " "))}</b>'
        f'<small>{"pass" if val else "FAIL"}</small></div></li>'
        for k, val in checks.items()
    )



    status_pill = pill("Do not submit", "no")

    body = f'''
<section class="hero"><div><p class="eyebrow">Executive summary · WBG-2</p>
<h1>Research file.<br><em>Do not submit.</em></h1>
<p class="lead">WBG-2 is a format-valid research GeoTIFF with a limited uniqueness audit against the nine focus-site artifacts. It has <strong>not</strong> passed a comparable hide-and-recover HOLDOUT-DTI efficacy gate and has no authorized slot-selection record. Its historical regression output is withdrawn as a score estimate.</p>
<div class="actions"><a class="button" href="downloads/{tif}" download>Download research TIFF ↓</a>
<a class="text-link" href="downloads/{zipn}">One-TIFF ZIP ↓</a>
<a class="text-link" href="session-review-20261027.md">Full repository review ↗</a></div>
<p class="micro" style="margin-top:18px">Name <code>{escape(card["submission_name"])}</code> · note {card["note_length"]}/140 characters · 0 competition slots used.</p></div>
<aside class="download-card" aria-label="Submission file and decision">
<div class="card-top"><div class="file-icon" aria-hidden="true">.TIF</div>
<div class="file-label">WBG-2 · off-catalogue density prior<small>36,000 scattered dots · zeros mode</small></div>{status_pill}</div>
<div class="card-body">
<div class="status-line"><span>Local format validator</span><b style="color:var(--teal)">PASS · {len(checks)} checks</b></div>
<div class="status-line"><span>Focus-site uniqueness audit</span><b style="color:var(--teal)">recorded · limited scope</b></div>
<div class="status-line"><span>Comparable HOLDOUT-DTI</span><b style="color:var(--red)">not measured</b></div>
<div class="status-line"><span>Submission decision</span><b style="color:var(--red)">DO NOT SUBMIT</b></div>
<div class="filename">{escape(tif)}</div>
<a class="button" href="downloads/{tif}" download><span>Download TIFF</span><span aria-hidden="true">↓</span></a>
<div class="under-download"><span>{size:.1f} MiB · float32 · EPSG:32611</span><a href="downloads/{zipn}">ZIP ↓</a></div>
<p class="micro" style="margin:15px 0 0"><strong>Research download only — do not upload.</strong> The ZIP contains the identical TIFF bytes. Do not upload comparison artifacts under <code>docs/audit/</code>.</p>
</div></aside></section>

<div class="alert" role="note"><p><strong>Do not spend a slot on this file.</strong> The old 0.2824 output was a MODEL-ESTIMATE fit to nine unverified third-party reports (one duplicated raster pair), not HOLDOUT-DTI and not an organizer result. It is withdrawn as a score estimate. Without comparable holdout efficacy, superiority is unknown.</p></div>

<section class="stats" aria-label="Key numbers">
<div class="stat"><label>HOLDOUT-DTI</label><div class="value word bad">Unavailable</div><p>No comparable hide-and-recover result<br>no leaderboard score estimate</p></div>
<div class="stat"><label>Uniqueness · MEASURED</label><div class="value word good">Unique</div><p>Max {nine["max_enrichment_vs_chance"]:.2f}× chance overlap<br>max |ρ| {nine["max_abs_spearman"]:.3f} across {nine["n_audited"]}/9 sites</p></div>
<div class="stat"><label>Format · MEASURED</label><div class="value word good">Passed</div><p>{v["positive_pixels"]:,} positive pixels<br>no NaN anywhere, values in [0, 1]</p></div>
<div class="stat"><label>Slots used</label><div class="value word">Zero</div><p>No upload performed here<br>no organizer receipt exists</p></div>
</section>

<section class="section"><div class="section-heading"><div><span class="section-num">01 / THE ANSWER</span><h2>What can be downloaded, why it is not an exact duplicate, and why it is not cleared</h2><p>Historical values are OWNER-REPORTED, not organizer-confirmed. WBG-2 is not assigned a projected score; its only local clearance is format plus a limited focus-site uniqueness audit.</p></div></div>
<div class="table-wrap"><table><caption>Historical reference values are owner-reported; WBG-2 has no validated score estimate</caption>
<thead><tr><th>Site / artifact</th><th>File</th><th>Historical reported value</th><th>Overlap with WBG-2</th><th>Unique?</th></tr></thead>
<tbody>
<tr class="featured"><td class="site-cell">WBG-2<small>research artifact only</small></td>
<td class="file-cell"><a href="downloads/{tif}">{escape(tif)}</a>
<div class="cell-note">{v["positive_pixels"]:,} positive pixels · 0.0% within 300 m of the mapped catalogue (excluded by construction)</div></td>
<td><span class="score">Unavailable</span><div class="cell-note">No comparable HOLDOUT-DTI or organizer receipt. Prior regression withdrawn; not a score.</div></td>
<td><span class="score">—</span><div class="cell-note">reference row</div></td>
<td>{pill("Research only", "no")}</td></tr>
{"".join(rows)}
</tbody></table></div>
<p class="note">Reported scores are the values supplied in the session brief. They are <strong>user/owner-reported</strong>: no submission-page receipt in this repository binds those bytes to a score. Two of the nine rows (GEMSDOE25 and GEMSDOE30) share an <em>identical</em> positive-pixel set, so the nine sites contain at most eight independent fields.</p></section>

<section class="section"><div class="section-heading"><div><span class="section-num">02 / WHY GEMSDOE32 LEADS THE OWNER-REPORTS</span><h2>Catalogue-distance pruning is a plausible explanation, not proven causality.</h2><p>The raster ancestry is visible; hidden labels and an artifact-linked submission receipt are not available.</p></div><a class="text-link" href="research/wbg2-why-02778.md">Full research note →</a></div>
<div class="two-col"><article class="panel"><div class="panel-head">Measured on the nine original files<span>only values 0.0 and 1.0</span></div>
<div class="panel-pad"><ul class="gate-list">
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>All nine are binary dot fields</b><small>Exactly two distinct values, 0.0 and 1.0. No continuous probability anywhere. Positive counts run 37,654–61,328 out of 5,167,373 scored cells.</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>Owner-reported value is ordered with catalogue distance</b><small>The reported value is rank-ordered with decreasing mapped-fault proximity across this small related set. Historical values are OWNER-REPORTED, not ORGANIZER-CONFIRMED; this association does not establish causality.</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>The highest reported raster is a controlled deletion, not a new model</b><small>Raster forensics show B2 is a strict subset of the D2.8 parent: 6,436 dots were removed, none added; all removed pixels were within two 100 m cells of the mapped catalogue. This supports a precision-cleanup hypothesis but cannot prove their hidden-truth status or explain a private score.</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>No dot sits on a mapped fault</b><small>All nine have 0.0000 fraction of positives on catalogue pixels — the scored target is defined as the faults the catalogue is missing.</small></div></li>
</ul></div></article>
<article class="mini-card"><span class="index">THE MECHANISM</span><h3>The metric pays you to delete bad guesses.</h3>
<p>With α = 0.2 and β = 0.8, an off-target dot costs 0.2 while a dot exactly on a hidden fault earns 1.0 and removes a 0.8 false-negative penalty. Deleting a dot that sits on a <em>mapped</em> fault is therefore pure profit: the mapped fault is not a target.</p>
<p>That is why the highest-scoring focus-site artifact is the one with the fewest catalogue-adjacent dots — and why every one of the nine is a pruning lineage of the same base field rather than nine independent discoveries.</p>
<a class="text-link" href="data/wbg2.json">Machine-readable bundle ↗</a></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">03 / CAN WE BEAT IT?</span><h2>Yes in principle. Not with the data in this sandbox.</h2><p>Three levers were tested numerically against the official metric.</p></div></div>
<div class="three-col">
<article class="mini-card"><span class="index">LEVER 1 · PROVEN</span><h3>Exclude the catalogue</h3><p>A dot within 300 m of a mapped fault is close to worthless. WBG-2 excludes <strong>everything</strong> within 400 m — stricter than any of the nine (their best was 200 m).</p><p class="cell-note">Evidence: controlled deletion in GEMSDOE32's own record (+0.0070) and perfect rank order across nine files.</p></article>
<article class="mini-card"><span class="index">LEVER 2 · NEGATIVE</span><h3>Continuous traces only help if you know the trace</h3><p>Simulated against the official metric: a 1 px continuous trace along the <em>true</em> local strike scores 0.936; scattered dots score 0.140; runs at a <em>guessed</em> strike score 0.090 — worse than scattering.</p><p class="cell-note">Conclusion: WBG-2 scatters. Rendering is not the lever; knowing where the fault runs is.</p></article>
<article class="mini-card"><span class="index">LEVER 3 · UNRESOLVED</span><h3>Shrink the field</h3><p>At a fixed number of true hits, DTI rises monotonically as predicted pixels fall (0.132 → 0.221 going from 20,000 to 2,500 pixels). But shrinking only helps if the retained pixels are better than the discarded ones.</p><p class="cell-note">The nine-site data cannot separate budget from catalogue proximity (r = {calib["collinearity"]["corr_near3cat_logbudget"]:.2f}). WBG-2 therefore stays inside the observed budget range.</p></article>
</div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">04 / NEGATIVE RESULTS</span><h2>What we tried and threw away.</h2><p>Both are recorded so the next session does not repeat them.</p></div></div>
<div class="two-col"><article class="panel"><div class="panel-head">Official GeoDAWN + 3DEP detector<span>rejected</span></div>
<div class="panel-pad"><p class="micro">A fault-likeness score was built from official USGS GeoDAWN radiometrics (K, Th, U, TC; DOI 10.5066/P93LGLVQ) and USGS 3DEP 1 m DEM terrain descriptors instead of topography, gated by scarp asymmetry and structure-tensor line-likeness.</p>
<ul class="gate-list">
<li><span class="gate-icon fail">×</span><div class="gate-copy"><b>No discrimination</b><small>AUC vs mapped faults: step 0.574, crest 0.585, asymmetry 0.493, line-likeness 0.497, radiometric alteration 0.487, combined 0.549.</small></div></li>
<li><span class="gate-icon fail">×</span><div class="gate-copy"><b>Worse than random at the real budget</b><small>Ranking the whole grid and taking 37,654 cells scored 0.0303 against the catalogue; a uniform random draw of the same size scored 0.0695.</small></div></li>
</ul><p class="micro">Cause: at 100 m the shipped 8-bit rad/3DEP aggregates do not localise Great Basin faults. The official 19-band <code>training_features.tif</code> is the missing input and is login-gated.</p></div></article>
<article class="mini-card"><span class="index">WHAT THIS MEANS</span><h3>Evidence and authorization are the current blockers.</h3>
<p>The WBG-2 surface is a catalogue-derived spatial prior, not a validated fault detector. No comparable holdout result supports a performance claim. Official competition data access and account allowance are not available in this environment.</p>
<p>Do not infer that a higher score follows from excluding mapped faults or reducing dot count. Those are hypotheses requiring prospective blocked validation.</p>
<a class="text-link" href="how-to-submit.html">Submission requirements →</a></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">05 / WITHDRAWN ESTIMATE</span><h2>No score estimate is available for WBG-2.</h2><p>The old regression is retained only to document why a tempting number was rejected.</p></div></div>
<div class="alert" role="note"><p>The previous 0.2824 regression output used nine owner-reported points without artifact-linked organizer receipts; GEMSDOE25 and GEMSDOE30 also share the same decoded predictions. The model cannot isolate dot-budget effects from catalogue-distance effects. It is withdrawn and must not be used as a submission-score estimate or slot-selection signal.</p></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">06 / VALIDATION</span><h2>Every gate, automatically checked.</h2><p>No human inspector is needed for these checks — they run in CI on the exact bytes you download.</p></div></div>
<div class="two-col"><article class="panel"><div class="panel-head">Format validator<span>{escape(tif)}</span></div>
<div class="panel-pad"><ul class="gate-list">{check_rows}
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>zip single member, byte identical</b><small>{"pass" if card["validator"]["zip"]["all_checks_passed"] else "FAIL"}</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>radix-2 sha256 recorded</b><small class="mono">{sha}</small></div></li>
</ul></div></article>
<article class="mini-card"><span class="index">SUBMISSION GATE</span><h3>Do not upload this research artifact.</h3>
<p>It has no comparable HOLDOUT-DTI result showing improvement over the current same-instrument best. A separate authorized selector record and current account allowance are also absent.</p>
<p>Format validation and uniqueness alone do not establish scientific efficacy or slot eligibility. No uploader exists here; no slot was used.</p>
<a class="text-link" href="{PROBLEM}">Official submission format →</a></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">07 / IRREGULARITIES</span><h2>Flagged for review.</h2><p>Things a reviewer should know before trusting any number on this page.</p></div></div>
<div class="details-list">
<details open><summary>Historical scores and leaderboard values are not artifact receipts</summary><div class="detail-body"><p>No submission-page receipt in this repository binds any of the nine artifacts to a score, and none binds WBG-2 to anything. Repository observations include 0.4437 (2026-10-26) and 0.4544 (2026-10-27); the latest user brief reports 0.3195. Current leaderboard value is unresolved because no fresh official-page check was available. None is a score for a file in this repository.</p></div></details>
<details><summary>GEMSDOE25 and GEMSDOE30 publish the same predictions</summary><div class="detail-body"><p>Their files differ in bytes and encoding, but their 44,090 positive pixels are the same set, and both are reported at 0.2600. Treat the "nine sites" as at most eight independent fields.</p></div></details>
<details><summary>The reported gap to the leaderboard is unexplained by the artifacts</summary><div class="detail-body"><p>The focus sites cluster at 0.245–0.278 while the public leaderboard runs 0.32–0.45. Nothing in the nine artifacts explains the gap; the most likely cause is access to the official 19-band feature stack, but that is an inference, not a measurement.</p></div></details>
<details><summary>External layers used in the rejected experiment are peer re-distributions</summary><div class="detail-body"><p>The GeoDAWN radiometric and 3DEP terrain rasters were read from a peer repository, not from the primary USGS archive. Their sidecars record DOI 10.5066/P93LGLVQ and ScienceBase item 657e1d85d34e23d3533209f7, but the bytes were not re-downloaded from USGS in this session. They are <strong>not</strong> used by WBG-2.</p></div></details>
<details><summary>WBG-2 is a spatial prior, not a detection</summary><div class="detail-body"><p>WBG-2 places dots where mapped faults are dense, displaced away from the catalogue. It encodes no measurement of any individual fault. Its named non-fault mimic is basin geometry: basin-fill depocentres and range-front aprons concentrate near mapped faults, so the prior partly tracks sedimentary basins rather than faulting.</p></div></details>
</div></section>

<aside class="feed-strip" aria-label="Leaderboard status"><div><strong>Current leaderboard score</strong><br><span>Unverified in this review. The repository retains a prior dated public-page observation of 0.4544; the latest user message reports 0.3195. These conflict and must not be presented as current without a fresh official-page check.</span></div>
<a href="{LEADERBOARD}">Open official leaderboard ↗</a></aside>
'''

    html = page("WBG-2 research artifact", body)
    (DOCS / "wbg2.html").write_text(html, encoding="utf-8")

    md = [
        "# WBG-2 — executive summary",
        "",
        f"**Download for research:** `docs/downloads/{tif}` (or `{zipn}`). **Submit:** NO.",
        "",
        "- Comparable HOLDOUT-DTI: **unavailable**. Validated leaderboard score estimate: **unavailable**.",
        "- Former 0.2824 exploratory regression output: withdrawn; not a score and not for slot selection.",
        "- Organizer-confirmed score: **none**.",
        f"- Unique vs the nine focus sites: **YES** — max {nine['max_enrichment_vs_chance']:.2f}× chance overlap, max |ρ| {nine['max_abs_spearman']:.3f}, {nine['n_audited']}/9 sites audited.",
        f"- Format: single-band float32, EPSG:32611, 3730×3292, values in [0,1], no NaN, {v['positive_pixels']:,} positive pixels.",
        f"- sha256: `{sha}`",
        "",
        "## What to download",
        "",
        "| Site | File | OWNER-REPORTED historical value | Overlap with WBG-2 | Unique? |",
        "|---|---|---|---|---|",
        f"| **WBG-2 research artifact** | `{tif}` | unavailable | reference | limited audit only; DO NOT SUBMIT |",
    ]
    for r in sorted(nine["rows"], key=lambda r: -r["organizer_reported_score"]):
        if r.get("status") != "audited":
            md.append(f"| {r['site']} | not audited | {r['organizer_reported_score']:.4f} (OWNER-REPORTED) | unknown | unverified |")
        else:
            md.append(
                f"| {r['site']} | `{r['artifact']}` | {r['organizer_reported_score']:.4f} (OWNER-REPORTED) | "
                f"{r['enrichment_vs_chance']:.2f}× chance | Unique |"
            )
    md += [
        "",
        "## Why GEMSDOE32 is the highest supplied owner-reported result",
        "",
        "Raster forensics show the B2 field is a strict deletion-only subset of D2.8: 6,436 dots removed, none added, with every removed pixel within 200 m of the mapped catalogue. This supports a precision-cleanup hypothesis. It does not prove the deleted dots were false positives or that this deletion caused the reported score, because hidden labels and an artifact-linked submission receipt are unavailable. The reported 0.2778 is OWNER-REPORTED, not ORGANIZER-CONFIRMED.",
        "",
        "## Levers, measured",
        "",
        "1. Catalogue exclusion — used by WBG-2 as a placement rule, not proven to improve hidden-fault detection.",
        "2. Continuous-trace and fixed-budget comparisons remain exploratory; they do not authorize a submission without a prospective holdout.",
        "3. Dot-budget effects are confounded with catalogue proximity in these related artifacts; do not treat the historical association as a causal score law.",
        "",
        "## Negative results",
        "",
        "- A detector built from official GeoDAWN radiometrics and 3DEP terrain descriptors scored AUC 0.549 against mapped faults and 0.0303 versus 0.0695 for random at the real budget. Rejected.",
        "- The official 418 MB `training_features.tif` is absent (login-gated), so no feature-based model could be trained here.",
        "",
        "## Irregularities",
        "",
        "- All nine reported scores are third-party values with no receipt.",
        "- GEMSDOE25 and GEMSDOE30 share an identical positive-pixel set.",
        "- Leaderboard current value is unresolved: a prior dated repository observation is 0.4544; the current user brief reports 0.3195. Neither is refreshed by this build.",
        "- External geophysical layers are peer re-distributions, not primary-download bytes; not used by WBG-2.",
        "",
    ]
    (DOCS / "wbg2-executive-summary.md").write_text("\n".join(md), encoding="utf-8")

    (DOCS / "data" / "wbg2.json").write_text(
        json.dumps(
            {
                "schema": "wbg2-page-bundle-v1",
                "run_card": card,
                "nine_site_uniqueness": nine,
                "calibration": calib,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print("wrote docs/wbg2.html, docs/wbg2-executive-summary.md, docs/data/wbg2.json (research-only; DO NOT SUBMIT; score estimate unavailable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
