#!/usr/bin/env python3
"""Build the WBG-2 research-only review from the preserved evidence bundle.

The page intentionally has no submit CTA or active leaderboard estimate. The
existing TIFF/ZIP are linked as research downloads only and are never rebuilt.
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
RULES_PDF = "https://docs.nlr.gov/docs/fy26osti/96647.pdf"
REFERENCE = "https://github.com/drivendataorg/gems-prize-reference-solution"
USGS = "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and"
GDR = "https://gdr.openei.org/submissions/1391"
EPSG = "https://epsg.io/32611"

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


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def esc(value) -> str:
    return escape(str(value), quote=True)


def pill(text: str, kind: str) -> str:
    return f'<span class="pill {kind}"><span class="dot" aria-hidden="true"></span>{esc(text)}</span>'


def page(title: str, body: str) -> str:
    nav = [
        ("index.html", "Overview"),
        ("wbg2.html", "WBG-2 review"),
        ("executive-summary.html", "Site comparison"),
        ("research.html", "Research"),
        ("evidence.html", "Evidence"),
        ("how-to-submit.html", "How to submit"),
    ]
    links = "".join(
        f'<a class="{"active" if path == "wbg2.html" else ""}" href="{path}">{esc(label)}</a>'
        for path, label in nav
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · WBG GEMS research desk</title>
<meta name="description" content="WBG-2 research artifact review. Download for research only; not cleared to submit. No valid holdout score or global uniqueness clearance is available.">
<meta name="theme-color" content="#173b42"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css"><script defer src="assets/app.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">
<a class="brand" href="index.html"><svg viewBox="0 0 36 38" fill="none" aria-hidden="true"><path d="M3 29C12 27 4 16 13 15S21 5 31 6M4 35C15 34 11 22 20 22S25 11 34 12M2 21C8 21 4 9 13 9S18 1 25 2" stroke="#23665f" stroke-width="2" stroke-linecap="round"/></svg><span>WBG / GEMS<small>FAULT MAPPING · RESEARCH DESK</small></span></a>
<div class="navlinks">{links}<a class="repo" href="{REPO}">Repository ↗</a></div></nav></div></header>
<main id="main" class="wrap"><div class="breadcrumb">GEMS prize challenge <span>/</span> WBG-2 research review <span>/</span> 27 OCT 2026</div>{body}</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>WBG / GEMS</strong> &nbsp; Evidence before a weekly slot.<br>A research download is not a submission recommendation; a local format pass is not organizer acceptance.</p><div><a href="data/wbg2.json">WBG-2 JSON</a><a href="standing-prompt.md">Standing brief</a><a href="{REPO}">Source code ↗</a></div></div></footer>
<div id="toast" role="status" aria-live="polite"></div></body></html>'''


def build() -> int:
    card = load("evidence/wbg2/run_card.json")
    nine = load("evidence/wbg2/nine_site_uniqueness.json")
    review = load("evidence/wbg2/review_20261027.json")
    calibration = load("registry/wbg2_calibration.json")
    tif = Path(card["artifacts"]["tif"]).name
    zip_name = Path(card["artifacts"]["zip"]).name
    tiff_path = ROOT / card["artifacts"]["tif"]
    size_mib = tiff_path.stat().st_size / (1024 ** 2)
    validator = card["validator"]["tif"]
    format_checks = validator.get("checks", {})
    format_pass = bool(validator.get("all_checks_passed"))
    reg = card["registry"]
    holdout = card["holdout_dti"]

    rows = []
    for row in sorted(nine["rows"], key=lambda item: -item["user_reported_score"]):
        site = row["site"]
        note = " Same decoded positive-pixel set is reported for GEMSDOE25/GEMSDOE30." if site in {"GEMSDOE25", "GEMSDOE30"} else ""
        rows.append(
            f'<tr class="{"featured" if site == "GEMSDOE32" else ""}">'
            f'<td class="site-cell"><a href="{SITE_REPO[site]}">{esc(site)} ↗</a></td>'
            f'<td class="file-cell"><span class="mono">{esc(row["artifact"])}</span>'
            f'<div class="cell-note">{int(row["their_positive_pixels"]):,} positive pixels.{note}</div></td>'
            f'<td><span class="score">USER-REPORTED {float(row["user_reported_score"]):.4f}</span>'
            f'<div class="cell-note">Not a receipt-backed organizer result.</div></td>'
            f'<td>{100*float(row["forward_3px_overlap"]):.2f}%</td>'
            f'<td>{float(row["sampled_spearman_rho_diagnostic_only"]):+.4f}</td>'
            f'<td>{pill("Pairwise distinct vs WBG-2", "ok")}'
            f'<div class="cell-note">Focus-nine comparison only; not global clearance.</div></td></tr>'
        )

    validator_rows = "".join(
        f'<li><span class="gate-icon {"ok" if passed else "fail"}">{"✓" if passed else "×"}</span>'
        f'<div class="gate-copy"><b>{esc(label.replace("_", " "))}</b>'
        f'<small>{"PASS · local format only" if passed else "FAIL"}</small></div></li>'
        for label, passed in format_checks.items()
    )
    scope_rows = "".join(
        f'<li><span class="gate-icon fail">×</span><div class="gate-copy"><b>{esc(label)}</b><small>{esc(detail)}</small></div></li>'
        for label, detail in [
            ("Assigned method lane", "No single-method paragraph was supplied; not authorized for promotion."),
            ("Surface check before placement", "No pre-placement uniqueness check is recorded."),
            ("Literal final-dot overlap", f"STOP: {float(reg['max_forward_3px_overlap']):.1%} forward overlap exceeds the 70% limit; the legacy chance-enrichment waiver is retired."),
            ("Full registry clearance", "Not established; the recorded local scan covered only eight rasters."),
            ("Scientific score", "No valid HOLDOUT-DTI, withheld-positive count, 95% CI, or organizer receipt exists."),
        ]
    )
    note = card["submission_note"]

    body = f'''
<section class="hero"><div><p class="eyebrow">Artifact review · WBG-2</p>
<h1>Download for research.<br><em>Do not submit.</em></h1>
<p class="lead">The preserved GeoTIFF is byte-intact and locally format-valid. That is not enough for a competition entry: WBG-2 has no authorized method lane, missed the required surface-before-placement check, triggers the literal overlap STOP, and has no valid holdout score.</p>
<div class="actions"><a class="button" href="downloads/{esc(tif)}" download>Download research TIFF ↓</a>
<a class="button secondary" href="downloads/{esc(zip_name)}">Research ZIP ↓</a></div>
<p class="micro" style="margin-top:18px">Artifact label <code>{esc(card["submission_name"])}</code> · research note {len(note)}/140 characters · no competition slot used.</p></div>
<aside class="download-card" aria-label="Research download and submission decision">
<div class="card-top"><div class="file-icon" aria-hidden="true">.TIF</div>
<div class="file-label">WBG-2 · off-catalogue density prior<small>36,000 scattered dots · zeros mode</small></div>{pill("DO NOT SUBMIT", "no")}</div>
<div class="card-body">
<div class="status-line"><span>Local format validator</span><b style="color:var(--teal)">{"PASS" if format_pass else "FAIL"} · {len(format_checks)} checks</b></div>
<div class="status-line"><span>Focus-nine pairwise audit</span><b>{nine["n_audited"]}/9 only</b></div>
<div class="status-line"><span>Full registry / lane clearance</span><b style="color:var(--red)">NO · STOP</b></div>
<div class="status-line"><span>HOLDOUT-DTI</span><b>NOT MEASURED</b></div>
<div class="filename">{esc(tif)}</div>
<a class="button" href="downloads/{esc(tif)}" download><span>Download research TIFF</span><span aria-hidden="true">↓</span></a>
<div class="under-download"><span>{size_mib:.1f} MiB · float32 · EPSG:32611</span><a href="downloads/{esc(zip_name)}">ZIP ↓</a></div>
<p class="micro" style="margin:15px 0 0">Research copy only. Do not upload this TIFF or its ZIP to the competition portal.</p>
</div></aside></section>

<div class="alert" role="alert"><p><strong>DOWNLOAD: YES (RESEARCH ONLY) &nbsp;·&nbsp; SUBMIT: NO.</strong> Format validity and pairwise difference from the nine focus-site files do not override the strict literal overlap STOP. Do not target registry holes or waive the threshold.</p></div>

<section class="stats" aria-label="Evidence status">
<div class="stat"><label>Leaderboard estimate</label><div class="value word">Unavailable</div><p>No defensible estimate.<br>Prior regression projection withdrawn.</p></div>
<div class="stat"><label>HOLDOUT-DTI</label><div class="value word">Not measured</div><p>No evaluator version, withheld positives, or 95% CI for WBG-2.</p></div>
<div class="stat"><label>Literal overlap · REGISTRY-MEASUREMENT</label><div class="value bad">{float(reg["max_forward_3px_overlap"]):.0%}</div><p>Against a recorded research surface<br>Strict limit: 70%; STOP.</p></div>
<div class="stat"><label>Focus-nine pairwise audit</label><div class="value word">Scoped</div><p>{float(nine["max_forward_overlap"]):.1%} maximum overlap · {float(nine["max_abs_sampled_spearman_diagnostic_only"]):.4f} max sampled |ρ| (diagnostic only) across the named nine.</p></div>
</section>

<section class="section"><div class="section-heading"><div><span class="section-num">01 / DECISION</span><h2>Why WBG-2 is not cleared</h2><p>All listed blockers are binding; a positive file-format check cannot cancel a scientific or lane STOP.</p></div></div>
<div class="two-col"><article class="panel"><div class="panel-head">Promotion gates<span>Fail-closed</span></div><div class="panel-pad"><ul class="gate-list">{scope_rows}</ul></div></article>
<article class="mini-card"><span class="index">RUN CARD DECISION</span><h3>Research download: yes.<br>Submission: no.</h3>
<p>Recorded HOLDOUT-DTI status: <strong>{esc(holdout["status"])}</strong>. The separate PROXY-DTI against mapped catalogue faults is 0.0 by construction, so it does not estimate performance on withheld faults.</p>
<p>Artifact SHA-256: <code class="mono">{esc(card["raster_sha256"])}</code></p>
<p>Research note ({len(note)}/140 characters; not portal guidance): <code>{esc(note)}</code></p>
<a class="text-link" href="data/wbg2.json">Open the complete machine-readable review ↗</a></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">02 / FOCUS-NINE COMPARISON</span><h2>Different from the named sites is not global clearance</h2><p>The exact nine-file audit is a scoped pairwise comparison, separate from the broader literal STOP documented above.</p></div></div>
<div class="table-wrap"><table><caption>Focus-site values are USER-REPORTED; 3 px overlap is a scoped REGISTRY-MEASUREMENT, while sampled ρ is diagnostic only.</caption>
<thead><tr><th>Site</th><th>Inspected artifact</th><th>Historical value</th><th>3 px overlap with WBG-2</th><th>Sampled Spearman ρ · diagnostic only</th><th>Scope result</th></tr></thead>
<tbody><tr class="featured"><td class="site-cell">WBG-2<small>preserved research artifact</small></td>
<td class="file-cell"><a href="downloads/{esc(tif)}">{esc(tif)}</a><div class="cell-note">36,000 positive cells; format-valid only</div></td>
<td><span class="score">Unavailable</span><div class="cell-note">No HOLDOUT-DTI or receipt</div></td>
<td>{100*float(nine["max_forward_overlap"]):.2f}% maximum across nine</td>
<td>{float(nine["max_abs_sampled_spearman_diagnostic_only"]):.4f} maximum absolute</td>
<td>{pill("Research only", "warn")}<div class="cell-note">Global clearance: NO.</div></td></tr>
{"".join(rows)}
</tbody></table></div>
<p class="note">The focus-nine measurements do not retroactively supply the missing surface-before-placement check, do not cover the complete registry, and do not override the 100% literal overlap measurement against the WBG-C1 continuous research surface. The former chance-enrichment exception was not authorized.</p></section>

<section class="section"><div class="section-heading"><div><span class="section-num">03 / WHY GEMSDOE32 B2 LED THE SUPPLIED RESULTS</span><h2>Observed set changes; causal explanation remains unproven</h2><p>The top supplied focus-site result is a historical report, not a verified submission receipt.</p></div><a class="text-link" href="research/wbg2-why-02778.md">Read the full audit note →</a></div>
<div class="two-col"><article class="panel"><div class="panel-head">Recorded lineage<span>Historical artifacts</span></div><div class="panel-pad"><ul class="gate-list">
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>D2.8 → B1 → B2 is a nested deletion sequence</b><small>D2.8: 44,090 dots; B1: 40,199; B2: 37,654. The B1 step removes 3,891 catalogue-near dots; B2 removes a further 2,545. These are exact set relations in the stored audit.</small></div></li>
<li><span class="gate-icon warn">!</span><div class="gate-copy"><b>Reported value: USER-REPORTED 0.2778</b><small>The evidence bundle contains no submission-page receipt binding the exact B2 bytes to that result.</small></div></li>
<li><span class="gate-icon warn">!</span><div class="gate-copy"><b>Why it may help: low-marginal-coverage pruning</b><small>Under a max-cover distance metric, redundant predictions can add false-positive mass with little new true-positive coverage. The observed ordering is consistent with this mechanism; hidden labels and receipts are absent, so causality is not established.</small></div></li>
</ul></div></article>
<article class="mini-card"><span class="index">WHAT WE CAN CONCLUDE</span><h3>Whether a unique file can beat 0.2778 is unknown.</h3>
<p>WBG-2 has no valid HOLDOUT-DTI, and its regression projection has been withdrawn. The existing nine-site audit proves only scoped pairwise difference, not eligibility or expected performance. Do not infer that the current file beats GEMSDOE32 B2.</p>
<p>The DTI of 0.0 versus mapped catalogue faults is a <strong>PROXY-DTI</strong> by construction, not a result against withheld faults.</p></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">04 / SCIENTIFIC LIMITS</span><h2>WBG-2 is a spatial prior, not a fault detector</h2><p>The output samples a smoothed density of already mapped structures.</p></div></div>
<div class="three-col"><article class="mini-card"><span class="index">MECHANISM</span><h3>Mapped-fault KDE</h3><p>A 1.5 km Gaussian kernel smooths the visible catalogue; candidate cells inside a 400 m exclusion are removed; a 36,000-cell point field is sampled from the remaining prior. No feature-level evidence for an individual hidden fault is added.</p></article>
<article class="mini-card"><span class="index">NAMED NON-FAULT MIMIC</span><h3>Basin geometry</h3><p>Basin-fill depocentres and range-front alluvial aprons can cluster near mapped faults. A density prior can reproduce sedimentary basin geometry rather than undiscovered fault traces.</p></article>
<article class="mini-card"><span class="index">WITHDRAWN PROJECTION</span><h3>Not a score</h3><p>The nine-row regression used user-reported values, duplicate prediction fields and collinear predictors, then extrapolated outside the fit range. It is retained in the JSON solely for audit and must not be quoted as an estimated score.</p></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">05 / LOCAL FORMAT CHECK</span><h2>Correct bytes, limited claim</h2><p>A local file-format check is not evidence of scientific efficacy or organizer acceptance.</p></div></div>
<div class="two-col"><article class="panel"><div class="panel-head">Pinned WBG-2 download<span>{"PASS" if format_pass else "FAIL"} · local checks</span></div><div class="panel-pad"><ul class="gate-list">{validator_rows}</ul>
<ul class="gate-list"><li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>Single-member ZIP is byte-identical</b><small>Local archive check recorded as passed.</small></div></li><li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>SHA-256</b><small class="mono">{esc(card["raster_sha256"])}</small></div></li></ul></div></article>
<article class="mini-card"><span class="index">RESEARCH ARTIFACT IDENTIFIER</span><h3>{esc(card["submission_name"])}</h3><p>This label and note are for distinguishing the preserved research download only. They are <strong>not</strong> an instruction to enter it into the competition portal.</p><p><strong>Download decision:</strong> YES, research only.<br><strong>Submit decision:</strong> NO.<br><strong>Slots used:</strong> zero.</p><a class="text-link" href="how-to-submit.html">Instructions for a future separately approved file →</a></article></div></section>

<section class="section"><div class="section-heading"><div><span class="section-num">06 / MANUAL REVIEW LINKS</span><h2>Official and trusted references</h2><p>Links are retained for manual review. These pages were not freshly retrieved in this repository review.</p></div></div>
<div class="details-list">
<details><summary>Competition description, data and scoring</summary><div class="detail-body"><p><a href="{PROBLEM}">DrivenData problem description and metric ↗</a> · <a href="{LEADERBOARD}">Public leaderboard ↗</a> · <a href="{SUBMISSIONS}">Submission page ↗</a> · <a href="{RULES_PDF}">DOE/NLR rules PDF ↗</a>. Portal access may require the competition account; no current allowance or upload receipt was checked.</p></div></details>
<details><summary>Reference solution, survey data and CRS</summary><div class="detail-body"><p><a href="{REFERENCE}">DrivenData reference solution ↗</a> · <a href="{USGS}">USGS GeoDAWN survey page ↗</a> · <a href="{GDR}">DOE Geothermal Data Repository submission 1391 ↗</a> · <a href="{EPSG}">EPSG:32611 definition ↗</a>.</p></div></details>
</div>
<div class="actions"><a class="button secondary" href="data/wbg2.json">Machine-readable bundle ↓</a><a class="text-link" href="downloads/{esc(tif).replace('.tif', '.validator.json')}">Exact shared-validator report ↗</a><a class="text-link" href="data/wbg2-review-20261027.json">Full review card ↗</a><a class="text-link" href="research/wbg2-why-02778.md">GEMSDOE32 B2 analysis ↗</a></div></section>
'''

    html = page("WBG-2 research review", body)
    (DOCS / "wbg2.html").write_text(html, encoding="utf-8")

    md = [
        "# WBG-2 — research artifact review",
        "",
        "**DOWNLOAD: YES, research only. SUBMIT: NO.** The local format pass does not override the missing lane, missing pre-placement check, strict overlap STOP, absent HOLDOUT-DTI, or absent organizer receipt.",
        "",
        f"- Research TIFF: [`docs/downloads/{tif}`](downloads/{tif}) (or [`{zip_name}`](downloads/{zip_name})).",
        f"- SHA-256: `{card['raster_sha256']}`.",
        f"- Local format validation: **{'PASS' if format_pass else 'FAIL'}**; one float32 band, EPSG:32611, shape 3730×3292, [0,1], no NaN, exact sample-template affine transform revalidated.",
        "- HOLDOUT-DTI: **NOT MEASURED**; no evaluator version, withheld-positive count, or 95% CI.",
        "- Organizer-confirmed score: **none**. Current leaderboard estimate: **unavailable**.",
        f"- Focus-nine pairwise audit: {nine['n_audited']}/9 exact artifacts; max forward overlap {nine['max_forward_overlap']:.4f}; max sampled |ρ| {nine['max_abs_sampled_spearman_diagnostic_only']:.4f} (diagnostic only). This is not full-registry clearance.",
        f"- Partial local registry scan: {reg['rasters_compared']} rasters; maximum literal forward 3 px overlap {reg['max_forward_3px_overlap']:.4f} against WBG-C1 research surface. **STOP** under the no-exemption rule.",
        "- Surface-before-placement check: **not recorded**. Method lane: **not authorized**.",
        "",
        "## Why GEMSDOE32 B2 led the supplied focus-site results",
        "",
        "GEMSDOE32 B2 is the highest supplied value, **USER-REPORTED 0.2778 / NOT ORGANIZER-CONFIRMED**. The stored raster lineage is D2.8 (44,090 dots) → B1 (40,199) → B2 (37,654), removing catalogue-near predictions at each step. Under a max-cover DTI, removing low-marginal-coverage predictions can reduce false-positive cost; this is consistent with the reported ordering but is not proven without hidden labels and a receipt. It does not establish a universal exclusion buffer.",
        "",
        "Whether a genuinely unique artifact can beat 0.2778 is **unknown**. WBG-2 has no valid HOLDOUT-DTI and no defensible score estimate.",
        "",
        "## Artifact mechanism and mimic",
        "",
        "A Gaussian KDE of mapped-fault density (1.5 km) supplies the placement prior, with a 400 m catalogue exclusion and 36,000 scattered cells. This is a spatial prior, not a fault detector. Basin-fill depocentres and range-front alluvial aprons are named non-fault mimics.",
        "",
        "The recorded PROXY-DTI against mapped catalogue faults is 0.0 by construction and is not a score. The former regression projection was withdrawn because it used unverified user reports, included duplicate prediction fields, had collinear predictors, and extrapolated beyond its fit domain.",
        "",
        "## Three-pass review",
        "",
        "1. **Audit:** found a false submit approval, an unauthorized chance-enrichment exception, a withdrawn projection, and no pre-placement surface gate.",
        "2. **Correct:** reclassified the unchanged TIFF/ZIP as research-only; made score and eligibility fields fail closed; kept the focus-nine result explicitly scoped.",
        "3. **Verify:** the exact TIFF and one-member ZIP passed the shared format validator; 146 repository tests, Ruff E9/F, Chromium 153 desktop/mobile checks for 10 pages, and all local CI validation commands passed. Download identities matched pinned hashes. GitHub Actions remains pending PR creation; none of these checks constitute organizer acceptance or global uniqueness clearance.",
        "",
        "## Manual-review sources",
        "",
        f"- [DrivenData problem / metric]({PROBLEM}) · [leaderboard]({LEADERBOARD}) · [submission page]({SUBMISSIONS}) · [DOE/NLR rules PDF]({RULES_PDF})",
        f"- [DrivenData reference solution]({REFERENCE}) · [USGS GeoDAWN]({USGS}) · [DOE GDR 1391]({GDR}) · [EPSG:32611]({EPSG})",
        "",
        "External sources and the competition portal were not freshly accessed in this review. No experiment, TIFF regeneration, upload, or slot use occurred.",
    ]
    (DOCS / "wbg2-executive-summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    bundle = {
        "schema": "wbg2-review-bundle-v2",
        "run_card": card,
        "nine_site_pairwise_audit": nine,
        "promotion_review": review,
        "retired_calibration_for_audit_only": calibration,
        "active_score_estimate": None,
        "download_decision": "research-only",
        "submit_decision": "NO",
    }
    (DOCS / "data/wbg2.json").write_text(json.dumps(bundle, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    (DOCS / "data/wbg2-review-20261027.json").write_text(
        json.dumps(review, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print("Built WBG-2 research-only review; no score estimate and no submit approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
