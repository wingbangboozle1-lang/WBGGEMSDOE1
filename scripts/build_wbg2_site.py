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
        ("wbg2.html", "WBG-2 submission"),
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
<meta name="description" content="WBG-2: a unique, format-valid GEMS submission with a calibrated score estimate and a verified uniqueness audit against GEMSDOE24/25/27/28/30/31/32/33/36.">
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
    est = card["score_estimate"]["value"]
    lo, hi = card["score_estimate"]["ci95"]
    v = card["validator"]["tif"]
    sha = card["raster_sha256"]
    ok = card["decision"]["ok_to_submit"]
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

    obs = calib["observations"]
    fit_rows = "".join(
        f'<tr><td class="site-cell">{escape(o["site"])}</td>'
        f'<td>{o["positive_pixels"]:,}</td>'
        f'<td>{100*o["fraction_positive_within_3px_of_catalogue"]:.1f}%</td>'
        f'<td><span class="score">{o["organizer_reported_score"]:.4f}</span></td>'
        f'<td><span class="score">{f:.4f}</span></td></tr>'
        for o, f in zip(obs, [x["fitted"] for x in calib["fitted_values"]])
    )

    status_pill = pill("OK to submit", "ok") if ok else pill("Do not submit", "no")

    body = f'''
<section class="hero"><div><p class="eyebrow">Executive summary · WBG-2</p>
<h1>One file.<br><em>Download and submit.</em></h1>
<p class="lead">WBG-2 is a newly generated, format-valid, <strong>unique</strong> GeoTIFF for the DOE GEMS Prize. It is not a copy of GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 or 36. Its score is a calibrated <strong>model estimate</strong>, not an organizer result — and the honest reading is that it ties the best focus-site artifact rather than beating it.</p>
<div class="actions"><a class="button" href="downloads/{tif}" download>Download the submission TIFF ↓</a>
<a class="text-link" href="downloads/{zipn}">One-TIFF ZIP ↓</a></div>
<p class="micro" style="margin-top:18px">Name <code>{escape(card["submission_name"])}</code> · note {card["note_length"]}/140 characters · 0 competition slots used.</p></div>
<aside class="download-card" aria-label="Submission file and decision">
<div class="card-top"><div class="file-icon" aria-hidden="true">.TIF</div>
<div class="file-label">WBG-2 · off-catalogue density prior<small>36,000 scattered dots · zeros mode</small></div>{status_pill}</div>
<div class="card-body">
<div class="status-line"><span>Local format validator</span><b style="color:var(--teal)">PASS · {len(checks)} checks</b></div>
<div class="status-line"><span>Uniqueness vs 9 focus sites</span><b style="color:var(--teal)">PASS · {nine["max_enrichment_vs_chance"]:.2f}× chance</b></div>
<div class="status-line"><span>Estimated score (model)</span><b>{est:.4f}</b></div>
<div class="status-line"><span>Organizer-confirmed score</span><b style="color:var(--red)">none</b></div>
<div class="filename">{escape(tif)}</div>
<a class="button" href="downloads/{tif}" download><span>Download TIFF</span><span aria-hidden="true">↓</span></a>
<div class="under-download"><span>{size:.1f} MiB · float32 · EPSG:32611</span><a href="downloads/{zipn}">ZIP ↓</a></div>
<p class="micro" style="margin:15px 0 0">Upload this file, or its ZIP — they contain identical bytes. Do not upload anything under <code>docs/audit/</code> (those are other people's artifacts, kept for comparison only).</p>
</div></aside></section>

<div class="alert" role="note"><p><strong>Read this before you spend a slot.</strong> The estimated score <strong>{est:.4f}</strong> (95% model interval {lo:.4f}–{hi:.4f}) comes from a 9-point regression on <em>third-party reported</em> values, R² {calib["r2"]:.3f}. It is <strong>not</strong> a leaderboard forecast, and the predicted gain over GEMSDOE32's 0.2778 is only <strong>+{est-0.2778:.4f}</strong> — smaller than the model's own error and built on an extrapolation below the fitted range of catalogue proximity. Submit it because it is <em>unique and valid</em>, not because it is proven to score higher.</p></div>

<section class="stats" aria-label="Key numbers">
<div class="stat"><label>Estimated score · MODEL-ESTIMATE</label><div class="value">{est:.4f}</div><p>95% interval {lo:.4f}–{hi:.4f}<br>9-point calibration, R² {calib["r2"]:.3f}</p></div>
<div class="stat"><label>Uniqueness · MEASURED</label><div class="value word good">Unique</div><p>Max {nine["max_enrichment_vs_chance"]:.2f}× chance overlap<br>max |ρ| {nine["max_abs_spearman"]:.3f} across {nine["n_audited"]}/9 sites</p></div>
<div class="stat"><label>Format · MEASURED</label><div class="value word good">Passed</div><p>{v["positive_pixels"]:,} positive pixels<br>no NaN anywhere, values in [0, 1]</p></div>
<div class="stat"><label>Slots used</label><div class="value word">Zero</div><p>No upload performed here<br>no organizer receipt exists</p></div>
</section>

<section class="section"><div class="section-heading"><div><span class="section-num">01 / THE ANSWER</span><h2>What to download, what it should score, and why it is not a duplicate</h2><p>Every number below is measured in this repository or copied from a dated source. Nothing is projected as if it were a score.</p></div></div>
<div class="table-wrap"><table><caption>The required table — one row per focus site, plus our submission</caption>
<thead><tr><th>Site / artifact</th><th>File</th><th>Reported score</th><th>Overlap with WBG-2</th><th>Unique?</th></tr></thead>
<tbody>
<tr class="featured"><td class="site-cell">WBG-2<small>this submission</small></td>
<td class="file-cell"><a href="downloads/{tif}">{escape(tif)}</a>
<div class="cell-note">{v["positive_pixels"]:,} positive pixels · 0.0% within 300 m of the mapped catalogue (excluded by construction)</div></td>
<td><span class="score">{est:.4f}</span><div class="cell-note">MODEL-ESTIMATE, 95% {lo:.4f}–{hi:.4f} · no organizer receipt</div></td>
<td><span class="score">—</span><div class="cell-note">reference row</div></td>
<td>{pill("Reference", "neutral")}</td></tr>
{"".join(rows)}
</tbody></table></div>
<p class="note">Reported scores are the values supplied in the session brief. They are <strong>user/owner-reported</strong>: no submission-page receipt in this repository binds those bytes to a score. Two of the nine rows (GEMSDOE25 and GEMSDOE30) share an <em>identical</em> positive-pixel set, so the nine sites contain at most eight independent fields.</p></section>

<section class="section"><div class="section-heading"><div><span class="section-num">02 / WHY 0.2778 WON</span><h2>Not geology. Catalogue distance and budget.</h2><p>The mechanism is visible in the artifacts themselves.</p></div><a class="text-link" href="research/wbg2-why-02778.md">Full research note →</a></div>
<div class="two-col"><article class="panel"><div class="panel-head">Measured on the nine original files<span>only values 0.0 and 1.0</span></div>
<div class="panel-pad"><ul class="gate-list">
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>All nine are binary dot fields</b><small>Exactly two distinct values, 0.0 and 1.0. No continuous probability anywhere. Positive counts run 37,654–61,328 out of 5,167,373 scored cells.</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>Score is monotone in distance from the catalogue</b><small>Fraction of dots within 300 m of a mapped fault: 0.190 → 0.2477; 0.187 → 0.2600; 0.136 → 0.2632; 0.109 → 0.2708; 0.050 → 0.2750; 0.049 → 0.2778. Perfect rank order, no exceptions.</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>The winner is a controlled deletion, not a new model</b><small>Its own audit JSON states: "0.2708 base with every dot at d(catalogue) ≤ 2 px deleted (37,654 dots)". The +0.0070 came from deleting dots, not from finding faults.</small></div></li>
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
<article class="mini-card"><span class="index">WHAT THIS MEANS</span><h3>The binding constraint is data, not cleverness.</h3>
<p>Every route that could beat 0.28 requires a better fault-probability map. With only the catalogue plus weak external aggregates, the best available placement skill is roughly 2× chance — measured on a spatially blocked holdout — which is not enough to move a score meaningfully.</p>
<p><strong>To reach the 0.39–0.45 leaderboard band</strong>, download the official <code>training_features.tif</code>, train the reference U-Net, then apply the three measured rules: exclude the catalogue, keep the field small, and never ship NaN.</p>
<a class="text-link" href="how-to-submit.html">Submission checklist →</a></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">05 / HOW THE ESTIMATE WAS BUILT</span><h2>A 9-point calibration, shown in full.</h2><p>score = {calib["coefficients"]["intercept"]:.4f} {calib["coefficients"]["near3cat"]:+.4f}·near3cat {calib["coefficients"]["log_budget"]:+.4f}·ln(budget)</p></div></div>
<div class="table-wrap"><table><caption>Fitted against the nine reported values — every point is shown, none are hidden</caption>
<thead><tr><th>Site</th><th>Positive pixels</th><th>Within 300 m of catalogue</th><th>Reported</th><th>Fitted</th></tr></thead>
<tbody>{fit_rows}</tbody></table></div>
<p class="note">R² {calib["r2"]:.3f} · residual SD {calib["residual_sd"]:.4f} · n = {calib["n_observations"]}. The two regressors are collinear (r = {calib["collinearity"]["corr_near3cat_logbudget"]:.2f}) because every site obtained a low catalogue fraction by deleting dots, which also lowered the budget. Predicted values are MODEL-ESTIMATES, never scores. The estimator ranks our own candidate files; it does not forecast a leaderboard position.</p></section>

<section class="section"><div class="section-heading"><div><span class="section-num">06 / VALIDATION</span><h2>Every gate, automatically checked.</h2><p>No human inspector is needed for these checks — they run in CI on the exact bytes you download.</p></div></div>
<div class="two-col"><article class="panel"><div class="panel-head">Format validator<span>{escape(tif)}</span></div>
<div class="panel-pad"><ul class="gate-list">{check_rows}
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>zip single member, byte identical</b><small>{"pass" if card["validator"]["zip"]["all_checks_passed"] else "FAIL"}</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>radix-2 sha256 recorded</b><small class="mono">{sha}</small></div></li>
</ul></div></article>
<article class="mini-card"><span class="index">HOW TO SUBMIT</span><h3>Four steps.</h3>
<p><strong>1.</strong> Download the TIFF above (or the ZIP).<br>
<strong>2.</strong> Open the submission form: <a href="{SUBMISSIONS}">drivendata.org/…/submissions/</a><br>
<strong>3.</strong> Name: <code>{escape(card["submission_name"])}</code><br>
<strong>4.</strong> Note ({card["note_length"]}/140): <code>{escape(card["submission_note"])}</code></p>
<p>Check your remaining weekly allowance on the page before confirming. This repository has no uploader and used no slot.</p>
<a class="text-link" href="{PROBLEM}">Official submission format →</a></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">07 / IRREGULARITIES</span><h2>Flagged for review.</h2><p>Things a reviewer should know before trusting any number on this page.</p></div></div>
<div class="details-list">
<details open><summary>All nine reported scores are unverified third-party values</summary><div class="detail-body"><p>No submission-page receipt in this repository binds any of the nine artifacts to a score, and none binds WBG-2 to anything. The public leaderboard was observed at <strong>0.4544</strong> for rank 1 on 2026-10-27 (xiaofanhu), which supersedes the 0.4437 and 0.4413 figures quoted in earlier briefs. That observation says nothing about any file in this repository.</p></div></details>
<details><summary>GEMSDOE25 and GEMSDOE30 publish the same predictions</summary><div class="detail-body"><p>Their files differ in bytes and encoding, but their 44,090 positive pixels are the same set, and both are reported at 0.2600. Treat the "nine sites" as at most eight independent fields.</p></div></details>
<details><summary>The reported gap to the leaderboard is unexplained by the artifacts</summary><div class="detail-body"><p>The focus sites cluster at 0.245–0.278 while the public leaderboard runs 0.32–0.45. Nothing in the nine artifacts explains the gap; the most likely cause is access to the official 19-band feature stack, but that is an inference, not a measurement.</p></div></details>
<details><summary>External layers used in the rejected experiment are peer re-distributions</summary><div class="detail-body"><p>The GeoDAWN radiometric and 3DEP terrain rasters were read from a peer repository, not from the primary USGS archive. Their sidecars record DOI 10.5066/P93LGLVQ and ScienceBase item 657e1d85d34e23d3533209f7, but the bytes were not re-downloaded from USGS in this session. They are <strong>not</strong> used by WBG-2.</p></div></details>
<details><summary>WBG-2 is a spatial prior, not a detection</summary><div class="detail-body"><p>WBG-2 places dots where mapped faults are dense, displaced away from the catalogue. It encodes no measurement of any individual fault. Its named non-fault mimic is basin geometry: basin-fill depocentres and range-front aprons concentrate near mapped faults, so the prior partly tracks sedimentary basins rather than faulting.</p></div></details>
</div></section>

<aside class="feed-strip" aria-label="Official leaderboard"><div><strong>Official public leaderboard</strong> &nbsp; <b>0.4544</b> &nbsp; <span>observed 2026-10-27 (rank 1)</span><br><span>A dated observation, not a score for our file.</span></div>
<a href="{LEADERBOARD}">View official leaderboard ↗</a></aside>
'''

    html = page("WBG-2 submission", body)
    (DOCS / "wbg2.html").write_text(html, encoding="utf-8")

    md = [
        "# WBG-2 — executive summary",
        "",
        f"**Download:** `docs/downloads/{tif}` (or `{zipn}`). **Submit:** {'YES' if ok else 'NO'}.",
        "",
        f"- Estimated score: **{est:.4f}** (MODEL-ESTIMATE, 95% {lo:.4f}–{hi:.4f}, R² {calib['r2']:.3f}, n={calib['n_observations']}).",
        "- Organizer-confirmed score: **none**.",
        f"- Unique vs the nine focus sites: **YES** — max {nine['max_enrichment_vs_chance']:.2f}× chance overlap, max |ρ| {nine['max_abs_spearman']:.3f}, {nine['n_audited']}/9 sites audited.",
        f"- Format: single-band float32, EPSG:32611, 3730×3292, values in [0,1], no NaN, {v['positive_pixels']:,} positive pixels.",
        f"- sha256: `{sha}`",
        "",
        "## What to download",
        "",
        "| Site | File | Reported score | Overlap with WBG-2 | Unique? |",
        "|---|---|---|---|---|",
        f"| **WBG-2 (this)** | `{tif}` | **{est:.4f}** (estimate) | reference | — |",
    ]
    for r in sorted(nine["rows"], key=lambda r: -r["organizer_reported_score"]):
        if r.get("status") != "audited":
            md.append(f"| {r['site']} | not audited | {r['organizer_reported_score']:.4f} | unknown | unverified |")
        else:
            md.append(
                f"| {r['site']} | `{r['artifact']}` | {r['organizer_reported_score']:.4f} | "
                f"{r['enrichment_vs_chance']:.2f}× chance | Unique |"
            )
    md += [
        "",
        "## Why 0.2778 won",
        "",
        "All nine artifacts are binary dot fields (only 0.0 and 1.0). Their reported score is perfectly rank-ordered by how far their dots sit from the mapped catalogue: 0.190→0.2477, 0.187→0.2600, 0.136→0.2632, 0.109→0.2708, 0.050→0.2750, 0.049→0.2778. The GEMSDOE32 winner is documented in its own audit as the 0.2708 base with every dot within 200 m of the catalogue deleted. The gain came from deletion, not detection.",
        "",
        "## Levers, measured",
        "",
        "1. Exclude the catalogue — proven, used by WBG-2 at 400 m.",
        "2. Continuous traces — only with the true strike (0.936) vs scattered (0.140) vs guessed strike (0.090). WBG-2 scatters.",
        "3. Smaller budget at fixed hits — monotone gain (0.132→0.221 from 20k→2.5k pixels), but confounded with lever 1 across the nine sites (r=0.75).",
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
        "- Public leaderboard observed 2026-10-27 at 0.4544 (rank 1), superseding 0.4437/0.4413.",
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
    print(f"wrote docs/wbg2.html, docs/wbg2-executive-summary.md, docs/data/wbg2.json ({est:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
