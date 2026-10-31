#!/usr/bin/env python3
"""Build the static GEMS evidence desk from persisted measured JSON, not hand scores."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wbggems.audit import dump_json

DOCS = ROOT / "docs"
REPO = "https://github.com/wingbangboozle1-lang/WBGGEMSDOE1"
PROBLEM = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
SUBMIT = "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/"


def load(path):
    return json.loads((ROOT / path).read_text())


def pill(text, kind="neutral"):
    return f'<span class="pill {kind}"><span class="dot" aria-hidden="true"></span>{escape(text)}</span>'


def link(url, text, cls=""):
    return f'<a class="{cls}" href="{escape(url, quote=True)}">{escape(text)}</a>'


def page(name, title, body):
    nav = [("start-here.html", "START HERE"), ("unique-lane-summary-20261029.html", "Unique lane · 29 Oct"), ("how-to-submit-20261029.html", "How to submit · 29 Oct"), ("focus-unique-attempt-20261029.html", "Focus lane · 29 Oct"), ("index.html", "Overview"), ("wbg6/index.html", "WBG-6 submit"), ("wbg5/index.html", "WBG-5"), ("wbg4/index.html", "WBG-4"), ("wbg3/index.html", "WBG-3"), ("wbg2.html", "WBG-2 audit"),
           ("executive-summary-20261028.html", "Exec summary 10-28"),
           ("executive-summary.html", "Site comparison"),
           ("executive-summary-focus-sites.html", "Nine-site exec summary"),
           ("research.html", "Research"), ("evidence.html", "Evidence"),
           ("repo-review-20261031.md", "Latest review · 31 Oct"), ("how-to-submit.html", "How to submit")]
    links = "".join(link(path, label, "active" if path == name else "") for path, label in nav)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · WBG GEMS research desk</title>
<meta name="description" content="An auditable GEMS fault-mapping research desk: nine-site comparison, measured holdout results, unique-byte research TIFF and explicit no-go submission status.">
<meta name="theme-color" content="#173b42"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css"><script defer src="assets/app.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">
<a class="brand" href="index.html"><svg viewBox="0 0 36 38" fill="none" aria-hidden="true"><path d="M3 29C12 27 4 16 13 15S21 5 31 6M4 35C15 34 11 22 20 22S25 11 34 12M2 21C8 21 4 9 13 9S18 1 25 2" stroke="#23665f" stroke-width="2" stroke-linecap="round"/></svg><span>WBG / GEMS<small>FAULT MAPPING · RESEARCH DESK</small></span></a>
<div class="navlinks">{links}{link(REPO, 'Repository ↗', 'repo')}</div></nav></div></header>
<main id="main" class="wrap"><div class="breadcrumb">GEMS prize challenge <span>/</span> {escape(title)} <span>/</span> 26 OCT 2026 frozen experiment</div><p class="micro"><strong>31 Oct 2026 review:</strong> no TIFF is cleared to submit; current score estimates unavailable. <a href="repo-review-20261031.md">Read decision and verification →</a></p><p class="micro"><a href="review-20261028.md">28 October review: no submission approved; frozen generator disabled →</a></p><p class="micro"><a href="portfolio-review.html">27 October follow-up: four earlier releases and trust corrections →</a></p><p class="micro"><a href="repo-review-20261027.html">27 October 2026 review: all 9 monitored heads changed; no file cleared →</a></p>{body}</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>WBG / GEMS</strong> &nbsp; Evidence before a weekly slot.<br>Fault predictions are not verified geothermal vents. Local validation is not organizer acceptance.</p><div>{link('data/run-card.json', 'Run card JSON')}{link('repo-review-20261031.md', 'Latest review · 31 Oct')}{link('standing-prompt.md', 'Standing brief')}{link('parallel/main-b9a2d53/index.html', 'Parallel negative archives')}{link(REPO, 'Source code ↗')}</div></div></footer>
<div id="toast" role="status" aria-live="polite"></div></body></html>'''


def alert():
    return '''<div class="alert" role="note"><svg viewBox="0 0 22 22" fill="none" aria-hidden="true"><path d="M11 3 21 20H1L11 3Z" stroke="currentColor" stroke-width="1.4"/><path d="M11 8v5m0 3h.01" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg><p><strong>Download: YES, for research. Submit: NO.</strong> <strong>DO NOT SUBMIT this research surface.</strong> The new file passes local GeoTIFF checks but fails the efficacy and literal uniqueness gates. The lane is stopped. No final dots were placed for C1; the WBG-2 dots were already placed before this audit. No competition slot was used. <a href="release-review.html">Four earlier downloads remain SUBMIT: NO</a>.</p></div>'''


def download_card(card, receipt):
    tif = Path(card["artifact"]).name
    size = (ROOT / card["artifact"]).stat().st_size / (1024 ** 2)
    return f'''<aside class="download-card" aria-label="Current research file and submission decision"><div class="card-top"><div class="file-icon" aria-hidden="true">.TIF</div><div class="file-label">WBG-C1 · Curvature commutator<small>Frozen 26 Oct result · continuous research surface</small></div>{pill('No-go', 'no')}</div><div class="card-body">
<div class="status-line"><span>Local file format</span><b style="color:var(--teal)">PASS · {len(receipt['validator']['checks'])} checks</b></div>
<div class="status-line"><span>Exact-copy check</span><b>Distinct in checked inventory</b></div>
<div class="status-line"><span>Eligible to submit</span><b style="color:var(--red)">NO · stopped</b></div>
<div class="filename">{escape(tif)}</div>
<a class="button" href="downloads/{escape(tif)}" download><span>Download research TIFF</span><span aria-hidden="true">↓</span></a>
<div class="under-download"><span>{size:.1f} MiB · float32 · EPSG:32611</span>{link('downloads/' + tif.replace('.tif', '.zip'), 'One-TIFF ZIP ↓')}</div>
<p class="micro" style="margin:15px 0 0">Not a final dotted submission. A different filename, checksum or pixel field does not override the overlap STOP.</p></div></aside>'''


def stats(card):
    h = card["holdout"]
    return f'''<section class="stats" aria-label="Current research status">
<div class="stat"><label>Measured · HOLDOUT-DTI</label><div class="value">{h['dti']:.6f}</div><p>95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]<br>{h['withheld_positive_pixels']:,} withheld positive pixels</p></div>
<div class="stat"><label>Local format · not portal acceptance</label><div class="value word good">Passed</div><p>Single-band float32 · no NaN / inf<br>All values in [0, 1]; exact grid match</p></div>
<div class="stat"><label>Literal novelty · REGISTRY-MEASUREMENT</label><div class="value bad">{card['registry']['max_forward_3px_overlap'] * 100:.2f}%</div><p>Forward 3 px overlap · limit 70%<br>New bytes, but overlap gate FAILED</p></div>
<div class="stat"><label>Competition slots used</label><div class="value word">Zero</div><p>Negative screen · no selector approval<br>Authenticated remaining allowance unknown</p></div></section>'''


def gates(card):
    rows = [
        ("ok", "✓", "Shared cache verified", "All 19 original-template band hashes match."),
        ("ok", "✓", "Feature leakage canaries passed", f"23 inputs × 4 folds; maximum AUC {card['leakage_canary']['maximum_orientation_invariant_auc']:.4f} < 0.90. Not proof of all possible leakage."),
        ("ok", "✓", "Exact file reopened and validated", "Finite [0,1] values; CRS, shape and geotransform match."),
        ("fail", "×", "Paired improvement not established", "Candidate trails its same-instrument control; the delta CI includes zero."),
        ("fail", "×", "Surface registry STOP", f"{card['registry']['max_forward_3px_overlap'] * 100:.2f}% forward overlap with the registered lattice. No exemption."),
        ("wait", "—", "Promotion and weekly allowance", "No assigned lane, current-best victory, untouched confirmation or authenticated slot receipt."),
    ]
    return '<ul class="gate-list">' + ''.join(f'<li><span class="gate-icon {kind}">{icon}</span><div class="gate-copy"><b>{title}</b><small>{text}</small></div></li>' for kind, icon, title, text in rows) + '</ul>'


def chart(card):
    minimum, maximum = .009, .019
    x = lambda v: 150 + (v - minimum) / (maximum - minimum) * 340
    bits = ['<svg class="ci-chart" viewBox="0 0 550 205" role="img" aria-label="Paired screen: candidate and control confidence intervals overlap; no improvement established.">']
    for tick in (.010, .012, .014, .016, .018):
        xx = x(tick)
        bits.append(f'<path d="M{xx} 40V158" stroke="#e5eae2"/><text x="{xx}" y="181" text-anchor="middle" fill="#718184" font-size="10" font-family="monospace">{tick:.3f}</text>')
    for y, label, key, color in ((72, "19-band control", "control_holdout", "#81978c"), (128, "WBG-C1 candidate", "holdout", "#23665f")):
        h = card[key]
        low, high = map(x, h["ci95"])
        xx = x(h["dti"])
        bits.append(f'<text x="14" y="{y + 4}" fill="#36545a" font-size="11">{label}</text><path d="M{low} {y}H{high}M{low} {y-6}V{y+6}M{high} {y-6}V{y+6}" stroke="{color}" stroke-width="2"/><circle cx="{xx}" cy="{y}" r="5" fill="{color}"/>')
    bits.append('<text x="320" y="201" text-anchor="middle" fill="#718184" font-size="10">HOLDOUT-DTI · 95% spatial-cluster intervals</text></svg>')
    return ''.join(bits)


HISTORY = {
    "GEMSDOE24": ("Sparse ridge thinning", "The historical D1.5 file contains 60,069 positive pixels. It is part of the inherited H19-5 ridge-thinning family, not an independent new geological detector. Later user-reported negative results are not improvements over this supplied historical value."),
    "GEMSDOE25": ("D2.8 parent field", "The 44,090-pixel D2.8 field has exactly the same decoded predictions as GEMSDOE30's historical champion despite different file encodings. Its name alone is not a verified physical separation parameter."),
    "GEMSDOE27": ("Topographic gap closure", "The supplied historical leader contains 61,328 positive pixels, 1,259 more than D1.5. Its lower user-reported value suggests that adding topographic bridges was not automatically beneficial; hidden labels are unavailable to establish a cause. The later H29 value in the prompt is also below this site's supplied historical leader."),
    "GEMSDOE28": ("Rung30 / B1-family variant", "Rung30 has 37,660 positive pixels and the largest supplied historical value among the four listed GEMSDOE28 variants. It is not a new independent field relative to the ridge-thinning family. The earlier SOLO variant is pixel-identical to GEMSDOE31's base."),
    "GEMSDOE30": ("Repackaged D2.8 dots", "Its 44,090 positive pixels match GEMSDOE25 D2.8 exactly. Different TIFF bytes or outside-footprint encoding do not constitute different predictions. It must not be copied as a unique new submission."),
    "GEMSDOE31": ("Catalogue-distance B1 pruning", "The 40,199-pixel field is exactly D2.8 with dots at distance ≤1 pixel from the public catalogue removed: 3,891 removals. It reproduces GEMSDOE28's SOLO variant. Pixel-exact masking is an evaluation rule; this additional distance buffer is a model choice."),
    "GEMSDOE32": ("B2 nested-pruning benchmark", "The 37,654-pixel supplied historical leader is exactly D2.8 restricted to catalogue distance >2 pixels. It removes a further 2,545 pixels from B1. This identity is verified from the actual files, not inferred from their names. It is the highest USER-REPORTED historical value among these nine supplied records, not an independently confirmed score."),
    "GEMSDOE33": ("Analog-tip / stepover extension", "The historical analog-tip file contains 41,865 positive pixels and remains heavily overlapping with the inherited family. The supplied value is below the unextended GEMSDOE31 base's reported value, so extra structural plausibility did not by itself establish better scoring. The actual source must be consulted before attributing any algorithmic causality."),
    "GEMSDOE36": ("Anderson-labelled augmentation", "Every GEMSDOE32 B2 dot is retained, with 1,200 additions, for 38,854 positives. The filename includes PINN, but the measured set relation does not establish that a new physics-informed neural network generated this particular artifact. The supplied value is below the B2 parent's reported value."),
}


def comparison_table(audit, *, compact=False):
    body = []
    for n, row in enumerate(audit["rows"]):
        site = row["site"]
        description = HISTORY[site][0]
        duplicate = row["exact_dot_duplicates_at_other_focus_champions"]
        exact_note = "Same pixels as " + ", ".join(duplicate) if duplicate else "Pixel-distinct from other eight listed champions"
        file_cell = f'{link(row["immutable_file_url"] + "?raw=1", row["file"])}<div class="cell-note">Original, historical file · audit / education only</div>'
        body.append(f'''<tr class="{'featured' if n == 0 else ''}" data-site="{site}"><td class="site-cell">{site}<small>{escape(description)}</small>{'<small>HIGHEST SUPPLIED HISTORICAL CLAIM</small>' if n == 0 else ''}</td><td><span class="score">{row['reported_historical_value']:.4f}</span><div class="cell-note">USER-REPORTED<br>Not organizer-confirmed</div></td><td class="file-cell">{file_cell}</td><td><span class="cell-note">Unavailable<br>Not inferred from a proxy</span></td><td>{pill('No new-slot clearance', 'warn')}<div class="cell-note">{escape(exact_note)}. Family overlap exceeds the literal gate.</div></td></tr>''')
    return f'''<div class="table-wrap"><table id="site-table"><caption>Nine focus sites — best values in the supplied historical records, NOT measured new-submission forecasts</caption><thead><tr><th scope="col">Site / lineage</th><th scope="col">Historical claim</th><th scope="col">Original file to inspect</th><th scope="col">Estimated leaderboard score</th><th scope="col">Unique new submission?</th></tr></thead><tbody>{''.join(body)}</tbody></table></div>'''


def parallel_section():
    return '''<section class="section"><div class="section-heading"><div><span class="section-num">04 / PARALLEL WORK PRESERVED</span><h2>Separate lanes. Frozen negative results.</h2><p>WBG-4 (CSJF-1), WBG-3 (SPI-PMR-WCS-1), WBG-S2 (MKSF-1), WBG-H1 (DPGF-1), TIP1 and MVGZ ran as independent lanes alongside WBG-C1. Each retains its own frozen Run Card, validator receipt and zero-slot-expenditure decision.</p></div></div><div class="two-col" style="margin-bottom:18px"><article class="mini-card"><span class="index">NEW LANE / WBG-4 (CSJF-1 · UNTOUCHED SEED=77 CONFIRMATION)</span><h3>Listric back-projection + conjugate &lambda;<sub>2</sub> + 2-stage OOF context</h3><p>78-channel label-free stack + 2-stage hidden-component OOF context pyramid + Horvitz-Thompson self-credit 300 m CELF (35,135 binary dots in zeros mode). Beats 19-band control across all 3 spatial evaluators: <strong>HOLDOUT-DTI 0.165424</strong> (95% CI [0.152338, 0.178931], <code>gems-segment-pooled-v1</code>, n=60,988; +78.0%), <strong>0.094601</strong> (<code>seed=20</code>, n=11,321; +72.1%), and untouched confirmation <strong>HOLDOUT-DTI 0.103660</strong> (<code>seed=77</code>, n=11,326 vs 0.051234 ctrl; +102.3%). Clears all 460 competing sparse rasters across 24 repos (max 3 px overlap <strong>57.25% &le; 70%</strong>; max |&rho;| = 0.4952 &le; 0.90), but literal registry STOP binds at <strong>99.6983%</strong> vs <code>r13-lattice-s5</code> and <strong>100%</strong> vs <code>WBG-C1</code>. Verdict negative; DO NOT SUBMIT.</p><a class="text-link" href="wbg4/index.html">Open WBG-4 executive summary ↗</a> · <a class="text-link" href="wbg4/how-to-submit.html">How to submit subpage ↗</a> · <a class="text-link" href="wbg4/forensics-and-hypotheses.html">0.2778 PhD forensics &amp; 4 hypotheses ↗</a> · <a class="text-link" href="downloads/wbggemsdoe1-wbg4-csjf1-edti-35135-20261027-b3dacd59-zeros.tif">Download WBG-4 .tif ↓</a></article><article class="mini-card"><span class="index">PRIOR LANE / WBG-3 (SPI-PMR-WCS-1 · 1m-LiDAR-FREE)</span><h3>Crustal SPI + FFT Poisson + monogenic phase + wing-crack</h3><p>40-channel 100 m geophysical stack (zero 1 m LiDAR, zero 10 m DEM derivatives) + 36,800 off-catalogue binary dots in zeros mode. Beats 19-band control across 4/4 spatial folds: <strong>HOLDOUT-DTI 0.118180</strong> (95% CI [0.103658, 0.132432], <code>gems-segment-pooled-v1</code>, n=60,988) vs <strong>0.090781</strong> control (+30.2%), and <strong>HOLDOUT-DTI 0.121862</strong> (<code>gems57-pooled-hide-v2</code>, n=11,330) vs <strong>0.076470</strong> control (+59.4%). Competing sparse overlap across 206 rasters passes (max 59.38% ≤ 70%; 27.55% vs GEMSDOE32 B2; 43.40% vs WBG-S2), but <strong>literal registry STOP</strong> binds at <strong>99.9946%</strong> vs <code>r13-lattice-s5</code> and <strong>100%</strong> vs <code>WBG-C1</code>. Verdict negative; DO NOT SUBMIT.</p><a class="text-link" href="wbg3/index.html">Open WBG-3 executive summary ↗</a> · <a class="text-link" href="wbg3/how-to-submit.html">How to submit subpage ↗</a> · <a class="text-link" href="wbg3/forensics-and-hypotheses.html">0.2778 PhD forensics &amp; 4 hypotheses ↗</a> · <a class="text-link" href="downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.tif">Download WBG-3 .tif ↓</a></article></div><div class="two-col" style="margin-bottom:18px"><article class="mini-card"><span class="index">PARALLEL LANE / WBG-H1 (DPGF-1 · EXP-3)</span><h3>Dip-projected basement coupling + 300 m CELF</h3><p>66-channel label-free geophysical stack + LiDAR-dual ensemble + two-regime 300 m CELF emitter. Recorded candidate <strong>HOLDOUT-DTI 0.123310</strong>, 95% CI [0.108921, 0.137557], versus matched B0 <strong>HOLDOUT-DTI 0.103855</strong>, 95% CI [0.090213, 0.117398]; both <code>gems-segment-pooled-v1</code>, 60,988 withheld positives. The paired difference is +0.019455, 95% CI [+0.007288, +0.031848]; not a leaderboard forecast. <strong>Literal registry STOP:</strong> 99.8035% forward overlap with the registered lattice exceeds 70%; a 64.49% sparse-peer-only diagnostic cannot override it. Verdict negative; format checks are not portal acceptance. The original linked card includes superseded interpretations.</p><a class="text-link" href="wbg-h1-dpgf1/index.html">Open WBG-H1 dashboard &amp; 9-site audit ↗</a> · <a class="text-link" href="wbg-h1-dpgf1/executive-summary.html">Upload guide ↗</a> · <a class="text-link" href="downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif">Download WBG-H1 .tif ↓</a> · <a class="text-link" href="wbg-h1-dpgf1/data/run_card.json">WBG-H1 Run Card JSON ↗</a></article><article class="mini-card"><span class="index">PARALLEL LANE / WBG-S2 (MKSF-1)</span><h3>10m DEM + 1m LiDAR Vierbein-Coulomb</h3><p>Parallel-reported <strong>HOLDOUT-DTI 0.183594</strong> (<code>gems-segment-pooled-v1</code>), stopped on literal <strong>99.5538%</strong> r13 overlap and <strong>100%</strong> WBG-C1 overlap. Verdict negative; DO NOT SUBMIT.</p><a class="text-link" href="wbg-s2-mksf1/index.html">Open WBG-S2 subsite ↗</a> · <a class="text-link" href="data/wbg-s2-safety-20261027.json">WBG-S2 safety receipt ↗</a> · <a class="text-link" href="data/tip1_run_card.json">Frozen TIP1 card ↗</a> · <a class="text-link" href="evidence/run_card.json">Frozen MVGZ card ↗</a></article></div></section>'''


def feed_strip(feed):
    observation = feed["leaderboard"]
    score = observation["public_dw_tversky"]
    observed = observation.get("observed_utc") or observation.get("observed_date_utc") or observation.get("date_utc") or "unknown date"
    status = ("Official public-page refresh succeeded; not a score for our file."
              if feed["leaderboard_status"] == "network_verified" else
              "Retained dated observation, not a fresh page check or a score for our file.")
    return f'''<aside class="feed-strip" aria-label="Dated public leaderboard observation"><div><strong>Official public leaderboard observation</strong> &nbsp; <b data-feed-score>{score:.4f}</b> &nbsp; <span data-feed-date>observed {escape(observed)}</span><br><span data-feed-status>{status}</span></div>{link(observation['source'], 'View official leaderboard ↗')}</aside>'''



def wbg2_banner():
    """Prominent fail-closed pointer to the WBG-2 retrospective audit."""
    card = load("evidence/wbg2/run_card.json")
    audit = load("evidence/wbg2/safety_audit_20261027.json")
    if card["verdict"] != "negative" or card["decision"]["ok_to_submit"]:
        raise ValueError("WBG-2 is stopped; refusing to publish an upload recommendation")
    overlap = audit["already_placed_final_dots_witness"]["my_dots_within_3px_of_theirs"] * 100
    tif = Path(card["artifacts"]["tif"]).name
    return f'''<div class="alert" role="note"><p><strong>WBG-2: DO NOT SUBMIT.</strong> The exact TIFF passes local format checks, but its literal registry overlap is <strong>{overlap:.4f}%</strong> (limit 70%). No valid leaderboard estimate or holdout result is available. <a href="wbg2.html">Executive audit and nine-site table →</a> · <a href="downloads/{tif}" download>Download TIFF for research only ↓</a></p></div>'''


def wbg_s2_banner():
    """Show the binding negative result from the independently measured parallel lane."""
    card = load("evidence/wbg_s2/run_card.json")
    safety = load("evidence/wbg_s2/safety_review_20261027.json")
    decision = card["strict_governance_decision"]
    if (card["verdict"] != "negative" or decision["ok_to_submit"] is not False
            or decision["eligible_for_separate_selector"] is not False
            or safety["ok_to_submit"] is not False):
        raise ValueError("WBG-S2 is stopped; refusing to publish an approval")
    r13, c1 = safety["witnesses"]
    tif = Path(card["artifact"]["tif_path"]).name
    return f'''<div class="alert" role="note"><p><strong>WBG-S2: DO NOT SUBMIT; no selector eligibility.</strong> Final-dot overlap is <strong>{r13['my_dots_within_3px_of_theirs']*100:.4f}%</strong> against r13 and <strong>{c1['my_dots_within_3px_of_theirs']*100:.0f}%</strong> against WBG-C1 (limit 70%). The pre-placement sampled Spearman screen did not establish full literal clearance. Holdouts are parallel-reported and selected on the same splits. <a href="wbg-s2-mksf1/index.html">WBG-S2 result and evidence →</a> · <a href="downloads/{tif}" download>Research-only TIFF ↓</a></p></div>'''


def wbg3_banner():
    """Show the binding negative result and competing-sparse uniqueness audit from WBG-3 SPI-PMR-WCS-1 and parallel EXP3DET."""
    card = load("evidence/wbg3_spipmr/run_card.json")
    if card["verdict"] != "negative" or card["decision"]["ok_to_submit"] is not False:
        raise ValueError("WBG-3 is stopped; refusing to publish an approval")
    tif = Path(card["artifact"]).name
    seg = card["holdout_dti"]["primary_segment_holdout"]["dti"]
    intra = card["holdout_dti"]["secondary_intrabasin_holdout"]["dti"]
    comp_ov = card["correlation_overlap_vs_registry"]["final_dots_competing_sparse"]["max_forward_3px_overlap"] * 100
    return f'''<div class="alert" role="note"><p><strong>WBG-3 (1m-LiDAR-free SPI-PMR-WCS-1): DO NOT SUBMIT; no selector eligibility.</strong> 36,800 zeros-mode dots beat 19-band control across 4/4 spatial folds (<code>HOLDOUT-DTI {seg:.6f}</code> on <code>gems-segment-pooled-v1</code>; <code>{intra:.6f}</code> on <code>gems57-pooled-hide-v2</code>) and pass all 207 competing sparse rasters (max 3 px overlap <strong>{comp_ov:.2f}% ≤ 70%</strong>; 27.55% vs GEMSDOE32 B2), but literal overlap hits <strong>99.9946%</strong> vs <code>r13-lattice-s5</code> and <strong>100%</strong> vs <code>WBG-C1</code>. <a href="wbg3/index.html">WBG-3 SPI-PMR executive summary →</a> · <a href="wbg3/how-to-submit.html">How to submit →</a> · <a href="wbg3/forensics-and-hypotheses.html">0.2778 PhD forensics →</a> · <a href="wbg3.html">Parallel EXP3DET summary →</a> · <a href="downloads/{tif}" download>Research-only WBG-3 TIFF ↓</a></p></div>'''


def wbg4_banner():
    """Show the binding negative result, untouched seed=77 confirmation, and 464-raster uniqueness audit from WBG-4 CSJF-1."""
    card = load("evidence/wbg4/run_card.json")
    uniq = load("evidence/wbg4/uniqueness_audit.json")
    if card["verdict"] != "negative":
        raise ValueError("WBG-4 is stopped; refusing to publish an approval")
    tif = Path(card["artifact"]["tif_relpath"]).name
    seg = card["holdout_dti"]["primary_segment_holdout"]["dti"]
    c77 = card["holdout_dti"]["untouched_confirmation_holdout"]["dti"]
    comp_ov = card["registry_uniqueness"]["competing_sparse_max_forward_3px_overlap"] * 100
    r13_ov = uniq["two_phase_summary"]["like_for_like_reading"]["worst_forward_overlap_dot_fields"] * 100
    return f'''<div class="alert" role="note"><p><strong>WBG-4 (CSJF-1 · Untouched seed=77 Confirmation): DO NOT SUBMIT; no selector eligibility.</strong> 35,135 zeros-mode dots beat 19-band control across all 3 spatial evaluators (<code>HOLDOUT-DTI {seg:.6f}</code> on <code>gems-segment-pooled-v1</code>; untouched <code>seed=77 = {c77:.6f}</code>, +102.3%) and clear all 460 competing sparse rasters across 24 repos (max 3 px overlap <strong>{comp_ov:.2f}% &le; 70%</strong>; max |&rho;| = 0.4952 &le; 0.90), but literal overlap hits <strong>{r13_ov:.4f}%</strong> vs <code>r13-lattice-s5</code> and <strong>100%</strong> vs <code>WBG-C1</code>. <a href="wbg4/index.html">WBG-4 executive summary &amp; master table →</a> · <a href="wbg4/how-to-submit.html">How to submit →</a> · <a href="wbg4/forensics-and-hypotheses.html">0.2778 PhD forensics →</a> · <a href="downloads/{tif}" download>Research-only WBG-4 TIFF ↓</a></p></div>'''


def wbg5_banner():
    """Expose the WBG-5 / MTA-1 null result with its competing-submission uniqueness verdict."""
    card = load("evidence/wbg5/run_card.json")
    if card["verdict"] != "negative":
        raise ValueError("WBG-5 is stopped; refusing to publish an approval")
    tif = Path(card["artifact"]["tif"]).name
    h = card["holdout_dti"]
    uniq = card["registry_uniqueness"]
    seg_ci, ctrl_ci = h["ci95"], h["control_arm_A1_ci95"]
    return f'''<div class="alert" role="note"><p><strong>WBG-5 (MTA-1): DO NOT SUBMIT; no selector eligibility.</strong> {card['artifact']['emitted_dots']:,} zeros-mode dots. The paired holdout screen is a <strong>null</strong>: MTA-1 <code>HOLDOUT-DTI {h['dti']:.6f}</code> (95% CI [{seg_ci[0]:.6f}, {seg_ci[1]:.6f}], <code>{h['evaluator_version']}</code>, n={h['n_withheld_positives']:,}) vs the 19-band control <code>{h['control_arm_A1_dti']:.6f}</code> (95% CI [{ctrl_ci[0]:.6f}, {ctrl_ci[1]:.6f}]); paired delta <strong>{h['paired_delta']:+.6f}</strong>, 95% CI [{h['paired_delta_ci95'][0]:+.6f}, {h['paired_delta_ci95'][1]:+.6f}] — <strong>the CI includes zero</strong> (MTA-1 wins 2 of 4 folds), so the magnetic-texture-anisotropy hypothesis adds no recoverable signal. It does pass the competing-submission uniqueness gate (max 3 px overlap <strong>{uniq['sparse_max_overlap']*100:.2f}% &le; 70%</strong> vs the nine historical masks; max |&rho;| = {uniq['sparse_max_abs_spearman']:.4f}); the literal all-entry gate fails only against WBGGEMSDOE1's own continuous wbg-c1 research surface, which is reported and never gating. <a href="wbg5/index.html">WBG-5 executive summary &amp; submit path →</a> · <a href="downloads/{tif}" download>Download research TIFF ↓</a> · <a href="data/wbg5_run_card.json">Run card JSON ↗</a></p></div>'''


def wbg5_diff1_banner():
    """Expose the WBG-5 / DIFF1 negative research download with its gates unmistakable.

    The MTA-1 lane owns evidence/wbg5/run_card.json; DIFF1 keeps its own frozen card
    so both 2026-10-28 WBG-5 sub-lanes stay independently inspectable.
    """
    card = load("evidence/wbg5/diff1_run_card.json")
    tif = card["submission_name"]
    arm_b = card["arms"]["B"]["holdout"]
    arm_c = card["arms"]["C"]["holdout"]
    comp = card["correlation_overlap_vs_registry"]["final_dots_competing_method"]
    lit = card["correlation_overlap_vs_registry"]["final_dots_literal"]
    if card["verdict"] != "negative" or card["ok_to_submit"] is not False:
        raise ValueError("DIFF1 is a negative lane; refusing to publish a promotion")
    return f'''<div class="alert" role="note"><p><strong>NEW · WBG-5 / DIFF1 (LiDAR scarp-lobe morphology): DOWNLOAD YES (research) · SUBMIT NO.</strong> A uniquely named, format-valid {card['final_dot_count']:,}-dot zeros-mode TIFF from a catalogue-free diffusion-shape detector. <strong>HOLDOUT-DTI {arm_b['dti']:.4f}</strong> (arm C {arm_c['dti']:.4f}) against benchmark <strong>{card['benchmark']['dti']:.4f}</strong>; leakage canary PASS; surface novelty PASS. Final dots FAIL: competing-method 3 px overlap <strong>{comp['max_competing_dot_overlap']*100:.2f}% &gt; 70%</strong> and literal all-entry overlap <strong>{lit['max_dot_overlap']*100:.2f}% &gt; 70%</strong>. <a href="executive-summary-20261028.html">Open 28 Oct executive summary →</a> · <a href="downloads/{tif}" download>Download research TIFF ↓</a> · <a href="downloads/{Path(tif).with_suffix('.zip').name}" download>ZIP ↓</a> · <a href="data/wbg5_diff1_run_card.json">Run card JSON</a></p></div>'''


def wbg6_banner():
    # Fail closed: the literal proximity rule supersedes the historic adjusted gate.
    audit = load("evidence/wbg6_submission_audit.json")
    tif = audit["name"] + ".tif"
    overlap = audit["duplicate_screen"]["max_forward_overlap_3px"]
    return (f'''<div class="alert" role="alert" style="border-left:6px solid #a32626">'''
            f'''<p><strong>NO CURRENT TIFF IS CLEARED TO SUBMIT.</strong> The prior WBG-6 approval is withdrawn under the explicit 70% proximity gate: the archived maximum 3 px registry overlap is {overlap:.4%}. Its 0.247 figure is a MODEL-ESTIMATE, not HOLDOUT-DTI or organizer-confirmed. This TIFF is <strong>research download only — DO NOT UPLOAD</strong>. '''
            f'''<a href="repo-review-current-20261028.md">Read the current review →</a> · '''
            f'''<a href="downloads/{tif}" download>Download research artifact →</a> · '''
            f'''<a href="wbg6/how-to-submit.html">Submission instructions / gates →</a></p></div>''')


def wbg7_banner():
    """WBG-7 unique submission: fail-checked, never oversold.

    Publishes the format/canary/uniqueness receipts and an unambiguous
    download slot.  Refuses to claim a leaderboard score or a cleared slot.
    """
    card = load("evidence/wbg7/run_card.json")
    v = card["validator"]
    h = card["holdout"]
    tif = card["submission_name"] + ".tif"
    return f'''<div class="alert" role="note" style="border-left:6px solid var(--amber)"><p><strong>NEW · WBG-7 unique submission:</strong> <strong>DOWNLOAD: research only</strong> — <a href="downloads/{tif}" download>{tif}</a> · <a href="downloads/{card['submission_name']}.zip" download>ZIP ↓</a>. Single-band float32, EPSG:32611, 3730×3292, <strong>values in [0,1] (no "[0,1]" portal error)</strong>, {v['in_footprint_positive_pixels']:,} off-catalogue dots, SHA-256 {card['raster_sha256'][:12]}…. <strong>OK to submit: NOT CLEARED</strong> — holdout-DTI {h['dti']:.4f} does not beat the 0.1661 same-evaluator best and no organizer score receipt exists; do not claim it beats 0.2778. <a href="executive-summary-focus-sites.html">Nine-site executive summary →</a> · <a href="evidence/wbg7/run_card.json">Run card →</a></p></div>'''


def focus9_banner():
    """Expose the synthetic Focus-9 download while keeping its negative gate unmistakable."""
    card = load("evidence/focus9_exec/run_card.json")
    tif = Path(card["artifact"]).name
    bound = card["correlation_overlap_vs_registry"]["lattice_coverage"]["pigeonhole_min_overlap_for_36800_dots"]
    if (card["verdict"] != "negative" or card["decision"]["ok_to_submit"] is not False
            or bound <= .70 or card["holdout_dti"]["dti"] is not None):
        raise ValueError("Focus-9 synthetic is a negative null; refusing to publish a promotion")
    return f'''<div class="alert" role="note"><p><strong>Focus-9 research file: DOWNLOAD YES · SUBMIT NO.</strong> <code>{tif}</code> is a reproducible uniform-random null, not a geological model; no HOLDOUT-DTI was measured. Local format checks pass, but the fixed 36,800-dot r13 lattice-overlap lower bound is <strong>{bound*100:.3f}% (&gt;70%)</strong>; competing-sparse overlap is unmeasured. <a href="focus9-executive-summary.html">Open Focus-9 table and forensics →</a> · <a href="downloads/{tif}" download>Download research TIFF ↓</a> · <a href="downloads/{tif.replace('.tif', '.zip')}" download>ZIP ↓</a></p></div>'''


def start_banner():
    return '''<section class="alert-panel" style="border-left:6px solid #23665f"><p class="eyebrow">START HERE · 29 OCTOBER 2026</p><p><strong>DOWNLOAD: YES · SUBMIT: NO · estimated leaderboard score: UNAVAILABLE.</strong> One unique, format-valid TIFF (wbggemsdoe1-lidar-scarp-coh-nms-offcat-36800-20261029-zeros). Its holdout beats only a random control by a small paired margin, so the promotion gate is not met. Nine-site table, irregularities, and the official sources are on <a href="start-here.html">start-here.html</a>.</p></section>'''


def tipcont_experiment_banner():
    """Tip-continuation experiment (WBGGEMSDOE1, 29 Oct 2026). Numbers come from the measured summary JSON."""
    summ = json.loads((ROOT / "docs/data/tipcont_experiment_20261029.json").read_text())
    nf = summ["new_file"]
    h = nf["holdout_dti_catalogue_proxy"]
    u = nf["uniqueness"]
    tif = Path(nf["zeros_tif"]).name
    return (f'<div class="alert" role="note"><p>'
            f'<strong>WBGGEMSDOE1 tip-continuation experiment (29 Oct 2026): DOWNLOAD RESEARCH ONLY · SUBMIT NO.</strong> '
            f'{nf["dots"]:,} binary dots, format-valid, byte-unique. Catalogue-proxy HOLDOUT-DTI {h["pooled_dti"]:.6f} '
            f'(95% CI [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}]) against a matched random null of '
            f'{h["matched_random_null_dti_2_5_97_5"][0]:.4f}–{h["matched_random_null_dti_2_5_97_5"][1]:.4f}; '
            f'{u["of_which_GEMSDOE25_family"]} GEMSDOE25-family rasters exceed the 70% gate. Estimated leaderboard score: <strong>UNAVAILABLE</strong>. '
            f'<a href="tipcont-experiment-20261029.html"><strong>Experiment page, nine-site overlap table and how-to-submit →</strong></a> · '
            f'<a href="downloads/{escape(tif).replace(".tif", ".zip")}" download>Research ZIP ↓</a></p></div>')


def decision_banner():
    """First thing on the homepage: the single, unambiguous submit decision (29 Oct 2026)."""
    audit = load("docs/data/nine_site_audit_20261029.json")
    best = next(f for f in audit["files"] if f["site"] == "GEMSDOE32")
    return ('<div class="alert" role="alert" style="border:4px solid #a32626;background:#fff"><div style="min-width:0">'
            '<p style="font-size:20px;margin:0 0 6px"><strong style="color:#a32626">SUBMIT: NO. No file is cleared.</strong></p>'
            '<p><strong>DOWNLOAD:</strong> research only. <strong>Estimated leaderboard score:</strong> UNAVAILABLE for every file here '
            '(no holdout or organizer score can be computed in this sandbox). Live public leaderboard #1 is 0.4544; the 50th row read this session is 0.3169 (the board moves: another read recorded 0.3167).</p>'
            '<p>Best user-reported nine-site file: GEMSDOE32 B2, 0.2778 (USER-REPORTED, not organizer-confirmed). '
            'It is already in the competition, so it is a duplicate and must not be uploaded again. '
            f'Its SHA-256 is <code>{best["sha256"][:16]}…</code>.</p>'
            '<p><a href="executive-summary-20261029.html"><strong>Open the 29 Oct executive summary: nine-site decision table, '
            'why 0.2778 scored, blockers, and ranked hypotheses →</strong></a></p></div></div>')


def home(card, receipt, audit, feed):
    score = card["holdout"]
    return start_banner() + decision_banner() + tipcont_experiment_banner() + wbg7_banner() + wbg6_banner() + focus9_banner() + wbg2_banner() + wbg5_diff1_banner() + wbg4_banner() + wbg5_banner() + wbg_s2_banner() + wbg3_banner() + f'''<section class="hero"><div><p class="eyebrow">Evidence first. Every submission.</p><h1>A fresh TIFF.<br>An <em>honest decision.</em></h1><p class="lead">An auditable research desk for the GEMS fault-mapping challenge. Nine sites compared, separate research lanes recorded, and no weekly slot spent by this integration.</p><div class="actions">{link('executive-summary.html', 'Read executive summary  →', 'button secondary')}{link('evidence.html', 'Inspect the evidence ↗', 'text-link')}</div><p class="micro" style="margin-top:20px">C1 frozen screen: 26 October 2026 · Verdict <strong>NEGATIVE</strong><br>The experiment did not beat its control. “Format valid” never means “ready to submit.”</p></div>{download_card(card, receipt)}</section>
{alert()}{stats(card)}
<section class="section"><div class="section-heading"><div><span class="section-num">01 / THE CURRENT EXPERIMENT</span><h2>Research surface, not a promoted prediction</h2><p>WBG-C1: non-coaxial curvature of conductivity/depth proxy fields.</p></div>{link('research.html', 'Method & limitations →', 'text-link')}</div><div class="two-col"><article class="panel"><div class="panel-head">Actual exported research field<span>Not ground truth</span></div><div class="map-frame"><span class="map-label">UTM 11N · 100 m source grid</span><img src="assets/research-field.png" alt="The actual continuous WBG-C1 confidence surface across the irregular GeoDAWN footprint; not a map of verified faults or vents." width="610" height="690"></div><div class="map-caption"><span>Nearest-neighbour preview of the exported TIFF.<br>Outside-footprint and known-catalogue support are zero.<br>OOF seams are not geological evidence.</span><div><div class="gradient-legend"></div><div class="legend-labels"><span>0</span><span>0.9</span></div><span>Confidence, not calibrated probability</span></div></div></article><article class="panel"><div class="panel-head">Automated validation gates{pill('Stopped', 'no')}</div><div class="panel-pad">{gates(card)}<div class="gates-foot"><span>No human inspector required for these local checks.</span>{link('evidence.html', 'View receipts →')}</div></div></article></div></section>
<section class="section"><div class="section-heading"><div><span class="section-num">02 / MEASURED, NOT PROJECTED</span><h2>Did the new hypothesis help?</h2><p>No statistically established improvement on this frozen screen.</p></div>{link('data/experiment.json', 'Full evaluator output ↗', 'text-link')}</div><div class="two-col"><article class="panel"><div class="panel-head">Same-instrument comparison<span>Continuous confidence surfaces</span></div><div class="panel-pad">{chart(card)}<p class="micro">HOLDOUT-DTI · <code>{card['holdout_instrument']['evaluator_version']}</code> · {score['withheld_positive_pixels']:,} withheld positives · 95% paired spatial-cluster intervals. Not a leaderboard estimate; not a comparison against sparse historical TIFFs.</p></div></article><article class="mini-card"><span class="index">WHY THE LANE STOPS HERE</span><h3>Different bytes are not enough.</h3><p>The fresh TIFF is not an exact copy of any checked registry raster. But its positive support overlaps the registered lattice by {card['registry']['max_forward_3px_overlap'] * 100:.2f}%, exceeding the unexempted 70% rule.</p><p>The C1 scientific screen is negative as well. No C1 final dots were placed; we have not retuned around registry gaps, claimed a new high score, or spent a submission slot.</p>{link('executive-summary.html#decision', 'Read the decision →', 'text-link')}</article></div></section>
<section class="section"><div class="section-heading"><div><span class="section-num">03 / LEARN FROM THE BEST, DO NOT COPY IT</span><h2>Nine sites. One closely related family.</h2><p>GEMSDOE32 has the highest supplied historical claim; no new upload is recommended.</p></div>{link('executive-summary.html#comparison', 'All nine files & findings →', 'text-link')}</div><div class="three-col"><article class="mini-card"><span class="index">HIGHEST SUPPLIED HISTORICAL CLAIM</span><h3>GEMSDOE32 · B2</h3><p><strong>USER-REPORTED 0.2778</strong>, not organizer-confirmed. A 37,654-dot pruning of the inherited D2.8 field, not a new independent discovery model.</p></article><article class="mini-card"><span class="index">EXACT PREDICTION DUPLICATE</span><h3>GEMSDOE25 = GEMSDOE30</h3><p>Their 44,090 positive-pixel sets are identical. Different file hashes and encodings do not make them different submissions.</p></article><article class="mini-card"><span class="index">THE REAL NEXT STEP</span><h3>Better evidence, not more slots</h3><p>Resolve the lane/metadata/registry scope, freeze a comparable current-best benchmark, then run an untouched confirmation in a separately authorized lane.</p></article></div></section>{parallel_section()}{feed_strip(feed)}'''


def executive(card, receipt, audit, feed):
    h, c, d = card["holdout"], card["control_holdout"], card["paired_delta_holdout"]
    tif = Path(card["artifact"]).name
    details = []
    for row in audit["rows"]:
        name, text = HISTORY[row["site"]]
        details.append(f'''<details><summary>{row['site']} — {escape(name)} <span class="mono">{row['dots']:,} positive pixels</span></summary><div class="detail-body"><p>{escape(text)}</p><p><strong>Submission decision:</strong> historical learning reference only; not a unique new-slot recommendation. Supplied historical value <strong>{row['reported_historical_value']:.4f}</strong> is USER-REPORTED / NOT ORGANIZER-CONFIRMED. A leaderboard estimate for a new file is unavailable.</p><p>{link(row['snapshot_url'], 'Pinned source snapshot ↗')} · {link(row['immutable_file_url'], 'Original TIFF ↗')}</p><div class="mono">SHA-256 of inspected bytes: {row['sha256']}</div></div></details>''')
    return wbg6_banner() + wbg2_banner() + wbg5_diff1_banner() + wbg4_banner() + wbg5_banner() + wbg_s2_banner() + wbg3_banner() + f'''<section class="subhero"><div><p class="eyebrow">Executive summary · decision memo</p><h1>What should you submit?<br><em>No current file is cleared.</em></h1><p class="lead">All available TIFFs are research-only under the active validation protocol. WBG-6 fails the literal registry overlap gate; the best supplied historical value belongs to GEMSDOE32 at 0.2778 and must not be copied.</p></div>{pill('Negative · no real slot', 'no')}</section>{alert()}
<div class="two-col content-section"><div class="panel"><div class="panel-head">C1 research surface (not the submission){pill('Research only', 'warn')}</div><div class="panel-pad"><div class="filename">{escape(tif)}</div><div class="actions"><a class="button" href="downloads/{tif}" download>Download research TIFF ↓</a>{link('downloads/' + tif.replace('.tif', '.zip'), 'One-TIFF ZIP ↓', 'button secondary')}</div><p class="micro" style="margin-top:15px">DOWNLOAD: YES · SUBMIT: NO. This is a continuous unplaced surface, not a final dotted submission. Organizer-confirmed score and leaderboard estimate are both <strong>unavailable</strong>.</p></div></div><div class="panel"><div class="panel-head">Measured screen<span>HOLDOUT-DTI, not forecast</span></div><div class="panel-pad"><p><strong>Candidate {h['dti']:.6f}</strong> · 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]<br><strong>Control {c['dti']:.6f}</strong> · 95% CI [{c['ci95'][0]:.6f}, {c['ci95'][1]:.6f}]</p><p class="micro">Paired delta {d['delta']:+.6f}; 95% CI [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]. Evaluator <code>{card['holdout_instrument']['evaluator_version']}</code>; {h['withheld_positive_pixels']:,} withheld positives; {card['holdout_instrument']['physical_bootstrap_clusters']} physical bootstrap clusters.</p></div></div></div>
<section class="content-section" id="decision"><h2>The decision in plain English</h2><div class="prose"><ol><li><strong>The TIFF is genuinely generated here.</strong> Its bytes and normalized decoded pixels differ from all {card['registry']['checked_unique_file_hashes']} checked prior file hashes. Previous predictions were used only for audit and historical learning, never as model features, labels or output pixels.</li><li><strong>It is locally format-valid, not cleared to submit.</strong> The reopened float32 single band matches CRS/shape/transform and has no NaN/inf, no out-of-range values, zero outside the footprint and zero support on known catalogue faults.</li><li><strong>It does not improve the clean control.</strong> The paired screen is negative and no identically rerun cross-repository current-best benchmark or untouched confirmation was established. We do not compare a dense confidence-surface DTI to a sparse historical leaderboard claim.</li><li><strong>The surface fails the required literal registry overlap gate.</strong> Maximum forward overlap is {card['registry']['max_forward_3px_overlap'] * 100:.2f}% versus a 70% ceiling; maximum signed Spearman ρ is {card['registry']['max_spearman_rho']:.6f}. The lattice is retained, not exempted. No final dots were placed or tested after STOP.</li><li><strong>No real slot is selected.</strong> The lane paragraph is missing and the submissions page requires login. The rules PDF states up to three entries weekly, but the actual remaining account allowance is unknown. No credential was requested and no upload occurred.</li></ol></div></section>
<section class="content-section" id="comparison"><div class="section-heading"><div><h2>Which original file performed best at each site?</h2><p>Ranked by the user-supplied historical claims, not by invented estimates.</p></div></div><div class="row-buttons"><span class="micro">File links point to immutable owner snapshots, for learning / audit only.</span><label><span class="micro">Filter sites &nbsp;</span><input class="search" id="site-filter" type="search" placeholder="e.g. GEMSDOE32" aria-label="Filter site comparison"></label></div>{comparison_table(audit)}<p class="note">“Historical claim” is deliberately not labelled ORGANIZER-CONFIRMED: there is no submission-page receipt binding those exact bytes to the supplied values. No defensible leaderboard projection is available. A different pixel set is not equivalent to passing the literal lane gate.</p></section>
<section class="content-section" id="lineage"><h2>Why did the GEMSDOE32 file lead the supplied group?</h2><div class="prose"><p><strong>What the bytes establish:</strong> D2.8 has 44,090 dots. The GEMSDOE31 B1 field removes 3,891 dots at catalogue distance ≤100 m, leaving 40,199. GEMSDOE32 B2 removes another 2,545 at distance ≤200 m, leaving 37,654. These are exact set identities on the recovered grid. GEMSDOE36 preserves all of B2 and adds 1,200 dots.</p><p><strong>The metric mechanism is plausible, not proven from hidden labels:</strong> distance-weighted true-positive credit saturates at the maximum contributing confidence for each truth cell. Redundant predictions can add false-positive mass with little new coverage. Sparse placement and pruning low-marginal-credit dots can therefore improve DTI. The supplied historical values are consistent with that explanation, but they do not prove where hidden faults were or establish a universal 200 m exclusion rule.</p><p><strong>Can it be beaten?</strong> In principle yes: the directly observed official public leaderboard is higher. But no experiment here establishes a higher project leaderboard result, and this negative screen is not a contender. A defensible replacement must beat a clean, identically evaluated current best, pass final-dot novelty after surface clearance, and survive untouched confirmation.</p><p>{link(PROBLEM, 'Official metric and submission requirements ↗')} · {link('data/nine-site-audit.json', 'Exact lineage measurements ↗')}</p></div></section>
<section class="content-section"><h2>Site-by-site executive notes</h2><div class="details-list">{''.join(details)}</div></section>
<section class="content-section"><h2>Next actions, in priority order</h2><div class="three-col"><article class="mini-card"><span class="index">01 / TRUST THE INPUTS</span><h3>Resolve metadata and provenance</h3><p>Obtain a legitimate organizer-origin data manifest/download, establish what each literal band means, and verify the current remaining allowance without storing credentials in chat or Git.</p></article><article class="mini-card"><span class="index">02 / RESPECT THE LANE</span><h3>Resolve protocol scope</h3><p>A separate selector must establish an actual assigned method and registry policy. Do not waive dense/lattice priors privately, use lattice holes as a target, or reset the stopped run.</p></article><article class="mini-card"><span class="index">03 / EARN THE SLOT</span><h3>Freeze a stronger benchmark</h3><p>Use an identically refitted current-best model, a fixed physically meaningful emission policy, untouched component-level confirmation and a fresh registry audit before any future promotion.</p></article></div></section>{feed_strip(feed)}<div class="actions">{link('how-to-submit.html', 'Submission instructions & preflight →', 'button secondary')}{link('data/run-card.json', 'Full JSON run card ↗', 'text-link')}{link('executive-summary.md', 'Download summary as Markdown ↓', 'text-link')}</div>'''


def research(card):
    h = card["holdout"]
    return f'''<section class="subhero"><div><p class="eyebrow">Science · falsifiable hypotheses</p><h1>Target hidden structures.<br><em>Test the mechanism.</em></h1><p class="lead">Structural complexity is a reasonable scientific starting point. It is not a guarantee of fault displacement, geothermal permeability or a high competition result.</p></div>{pill('1 experiment · stopped', 'warn')}</section>{alert()}
<section class="content-section"><h2>What was actually tested?</h2><div class="two-col"><article class="panel"><div class="panel-pad prose"><h3>WBG-C1 · Hessian non-coaxiality</h3><p>From literal bands <code>cond_surf</code>, <code>depth_to_base_surf</code> and <code>geod_dilaterate</code>, take scale-normalized Gaussian Hessians at 300 m and 800 m. The normalized matrix commutator detects disagreement in principal curvature directions. Require curvature strength and cross-scale persistence; supply positive-dilatation support as a separate feature.</p><pre><code>C(A, B) = |[A B − B A]₀₁| / (‖A‖F ‖B‖F)
C = 0 for commuting / shared-axis tensors
C ∈ [0, 1] for the real symmetric 2 × 2 tensors used here</code></pre><p><strong>Named mimic:</strong> oblique saline-clay basin fill, lithologic contacts or shared inversion artifacts can produce the same signature. The operator itself is an unproven research hypothesis.</p></div></article><article class="panel"><div class="panel-pad prose"><h3>Leakage-safe screen</h3><ul><li>Reuse all 19 byte-matching template cache bands; add only four catalogue-blind channels.</li><li>Withhold whole original connected catalogue components globally; buffer feature context and use label-blind eroded quadrants.</li><li>Train outside the held quadrant and its 8 km collar. Never treat withheld components as training negatives.</li><li>Mask known faults pixel-exactly for scoring. Use the unchanged pooled max-cover DTI evaluator and 20 km physical bootstrap clusters.</li><li>Test each of 23 features alone in every held quadrant, including reverse AUC and missingness checks.</li></ul><p><strong>Measured:</strong> HOLDOUT-DTI {h['dti']:.6f}, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]; {h['withheld_positive_pixels']:,} withheld positives; <code>{card['holdout_instrument']['evaluator_version']}</code>. Negative paired efficacy; no final dot placement.</p></div></article></div></section>
<section class="content-section"><h2>Four candidates ranked before implementation</h2><div class="details-list"><details open><summary>1 · Conductivity/depth Hessian commutator — low cost, highest-priority conjecture</summary><div class="detail-body"><p>Layers: literal bands 17, 15, 8. Signature: multiscale non-coaxial curvature, not scalar gradient strength, Euler depth or inherited ridge thinning. Missing-catalogue rationale: concealed geometric complexity without catalogue proximity. Mimic: oblique basin-fill/lithologic boundaries. Existing shared cache is sufficient; no external data needed. Exact operator not found in inspected code, but global/unpublished novelty is not established.</p><p><strong>Executed once; negative.</strong> Expected improvement was qualitative and uncertain, never a numeric forecast.</p></div></details><details><summary>2 · Depth-conditioned magnetic texture transport — medium cost, untested</summary><div class="detail-body"><p>Layers: cached RTP, TMI and depth proxy. Signature: lagged texture changes along versus across depth-contour directions. It may flag covered offsets without an exposed scarp; volcanic/intrusive contacts or survey leveling can mimic it. More specific than a high-amplitude magnetic edge. Related peer texture/phase proposals already exist; exact added information and lane novelty are unknown. No new source needed for an initial screen.</p></div></details><details><summary>3 · Radiometric compositional changes across saddles — medium cost, conditional</summary><div class="detail-body"><p>Layers: USGS GeoDAWN K/Th/U and terrain saddles. Signature: tangent-coherent cross-saddle compositional changes, not raw counts. Fracture-controlled alteration might lie outside mapped traces; sorting, weathering and lithology can mimic it. Ratio features already exist in peer code, so a ratio alone is not novel. The official GeoDAWN catalogue/license was checked, and owner-derived layers exist; original bytes, quantization meanings and coverage must be independently established before calling this ready.</p><p>{link('https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and', 'Official free USGS source · DOI 10.5066/P93LGLVQ ↗')}</p></div></details><details><summary>4 · Anisotropic conductivity-boundary persistence — medium cost, untested</summary><div class="detail-body"><p>Layers: cached conductivity and depth proxies. Signature: boundary survival under smoothing along, but not across, a local orientation tensor. It might retain elongated concealed discontinuities; saline deposits or gridding seams are mimics. Different proposed statistic from a scalar edge, but related coherence/vesselness already exists. Needs a future assigned lane and frozen validation, not an automatic slot.</p></div></details></div><p class="note">The proposals are ranked research judgments, not measured DTI improvements. Only WBG-C1 was implemented, and the lane stopped. {link('hypotheses.md', 'Full hypothesis matrix and readiness caveats ↗')}</p></section>
<section class="content-section prose"><h2>Grounded in literature, not validated by analogy</h2><p>{link('https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa', 'Siler (2023), USGS · DOI 10.1144/geoenergy2023-009')} provides process-based explanations for localized stress and strain near interacting structures. It motivates studying complexity, but does not validate this operator.</p><p>{link('https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and', 'Faulds et al. (2019), USGS · DOI 10.2172/1724080')} describes convergent structural, geophysical, thermal and geochemical evidence for blind systems. A fault likelihood field alone is not evidence of a resource or a vent.</p><div class="callout warning"><strong>Metadata warning:</strong> the mirror's <code>tc</code> descriptor and the interpretation of <code>depth_to_base_surf</code> differ across materials. Inputs are integrity-pinned, not independently authenticated organizer metadata. No physical-unit conversion or geothermal discovery claim is justified here.</div></section><div class="actions">{link('data/preregistration.json', 'Frozen preregistration ↗', 'button secondary')}{link('data/feature-canaries.json', 'All individual-feature canaries ↗', 'text-link')}{link('evidence.html', 'Sources & limitations →', 'text-link')}</div>'''


def evidence(card, sources, irregularities, feed):
    sourcecards = []
    for s in sources["sources"]:
        claims = ''.join('<li>' + escape(c) + '</li>' for c in s.get("verified_claims", []))
        if s.get("observation"):
            obs = s["observation"]
            claims += '<li>Directly observed public rank-one value: ' + escape(str(obs["public_dw_tversky"])) + ' on ' + escape(obs["date_utc"]) + '. Not a project TIFF receipt.</li>'
        sourcecards.append(f'<article class="source-card"><span class="source-id">{s["id"]}</span><h3>{escape(s["title"])}</h3><p>{escape(s["access"])}</p><ul>{claims}</ul>{link(s["url"], "Review official source ↗")}</article>')
    issues = ''.join(f'<details><summary>{escape(i["id"])} · {escape(i["title"])} {pill(i["severity"], "ok" if i["severity"] == "fixed" else "warn")}</summary><div class="detail-body"><p>{escape(i["finding"])}</p><p><strong>Action:</strong> {escape(i["action"])}</p></div></details>' for i in irregularities["items"])
    return f'''<section class="subhero"><div><p class="eyebrow">Audit trail · independently inspectable</p><h1>Know what is measured.<br><em>Know what is missing.</em></h1><p class="lead">Every material claim links to a source or measured JSON. Unknowns remain unknown; no claim of exhaustive literature review, all-site coverage, hidden-label access or guaranteed leaderboard performance is made.</p></div>{pill('No organizer score receipt', 'warn')}</section>{alert()}
<section class="content-section"><h2>Keep these evidence classes separate</h2><div class="three-col"><article class="mini-card"><span class="index">HOLDOUT-DTI</span><h3>A local measured result</h3><p>Must carry evaluator version, withheld-positive count, representation and confidence interval. These recover withheld public-catalogue faults, not the organizer's unseen new-fault labels.</p></article><article class="mini-card"><span class="index">ORGANIZER-CONFIRMED</span><h3>Requires a real file receipt</h3><p>Reserved for a submission-page receipt linking the actual artifact to its result. No project file has such a verified receipt here. The public leaderboard is a separate dated observation.</p></article><article class="mini-card"><span class="index">USER-REPORTED / UNCONFIRMED</span><h3>Historical claims, quarantined</h3><p>The supplied site values stay in this class. A source repository repeating a claim does not independently verify it. Predictions and projections are never relabelled as measured scores.</p></article></div></section>
<section class="content-section"><h2>Current receipts and inventory</h2><div class="check-grid"><div class="check"><b>360 unique file hashes / 377 source paths</b><p>Aligned prediction-like TIFFs from nine frozen snapshots; 0 unreadable indexed candidates. Not the entire competition or all 92 sites.</p></div><div class="check"><b>Shared template reused unchanged</b><p>24 pinned source files match, including evaluate_holdout.py and submission_writer.py. All nineteen original-cache band hashes match.</p></div><div class="check"><b>Exact newly generated artifact</b><p class="mono">SHA-256 {card['raster_sha256']}</p></div><div class="check"><b>Unknowns block approval automatically</b><p>Lane authorization, independent organizer-origin data, same-instrument current-best victory, untouched confirmation and authenticated account allowance.</p></div></div><div class="actions" style="margin-top:20px">{link('data/registry-surface-audit.json', 'All 360 registry comparisons ↗', 'button secondary')}{link('data/template-integrity.json', 'Shared-template integrity ↗', 'text-link')}{link('data/shared-feature-cache.json', '19-band cache receipt ↗', 'text-link')}{link('data/experiment.json', 'Holdout folds & CI ↗', 'text-link')}{link('data/upstream-template-verification.json', '24 direct upstream matches ↗', 'text-link')}{link('data/snapshot-commit-verification.json', '9 verified commit pins ↗', 'text-link')}{link('data/review-passes.json', 'Three review passes ↗', 'text-link')}{link('data/browser-checks.json', 'Desktop / mobile / download checks ↗', 'text-link')}</div></section>
<section class="content-section"><h2>Official sources and checked claims</h2><p class="note">See individual source entries for retrieval dates. Relevant sections were read; the full rules PDF, every external dataset and all linked literature were not exhaustively verified. Original raster bytes have not been independently downloaded from the organizer.</p><div class="source-grid">{''.join(sourcecards)}</div><p class="note">{link('data/sources.json', 'Machine-readable sources, access status and normalized excerpts ↗')}</p></section>
<section class="content-section"><h2>Irregularities, not hidden exceptions</h2><div class="details-list">{issues}</div></section>
<section class="content-section"><h2>Public provenance feed</h2>{feed_strip(feed)}<p class="prose">Scheduled Pages builds attempt to refresh the official leaderboard and the nine GitHub heads. If a request fails, the last verified observation stays dated and the error is reported; it is never called a fresh measurement. Head changes flag that the frozen inventory may be stale. The feed never retrains a model, changes an approval, picks a submission or spends a slot.</p><div class="actions">{link('data/feed.json', 'Current feed JSON ↗', 'button secondary')}{link('data/repository-snapshots.json', 'Immutable audit pins ↗', 'text-link')}{link('data/irregularities.json', 'All irregularities JSON ↗', 'text-link')}</div></section>'''


def howto(card, receipt):
    tif = Path(card["artifact"]).name
    return focus9_banner() + f'''<section class="subhero"><div><p class="eyebrow">Submission guide · for a future promoted file</p><h1>Validate the exact file.<br><em>Then earn the slot.</em></h1><p class="lead">The current download is a negative research result. These instructions explain the future submission process; they do not authorize uploading this file.</p></div>{pill('Current file: do not submit', 'no')}</section>{alert()}
<section class="content-section"><h2>The current file is safe to inspect, not approved to upload</h2><div class="two-col">{download_card(card, receipt)}<article class="panel"><div class="panel-pad prose"><h3>What automated preflight checks</h3><ul><li>One float32 raster band, values in [0,1] and no NaN/inf anywhere under our conservative export policy.</li><li>CRS EPSG:32611, shape 3,730 rows × 3,292 columns, 100 m pixel grid and exact reference geotransform/bounds.</li><li>Zero support outside the mirrored footprint and on mapped catalogue pixels.</li><li>On-disk roundtrip plus a ZIP containing exactly one identical GeoTIFF.</li><li>Separate scientific, leakage and registry gates; no “human inspection only” escape hatch.</li></ul><p>The official format says data outside the bounds should be null/NaN. All-finite zeros outside the mirrored footprint are a conservative local project choice, not verified portal acceptance; the two descriptions may not refer to exactly the same area. We cannot prove the cause of the old rejected upload without its actual bytes and receipt.</p></div></article></div></section>
<section class="content-section prose"><h2>For a future candidate that passes every gate</h2><h3><span class="step-number">1</span> Read the decision, not just the filename</h3><p>Only a candidate that passes surface novelty, fixed-policy holdout efficacy, untouched confirmation and final-dot novelty may reach a separate selector. Local format validity alone never authorizes upload. This run is <strong>negative</strong>, with <strong>zero slots used</strong>.</p><h3><span class="step-number">2</span> Confirm current account allowance</h3><p>The official September rules PDF, section 3.4, states up to three entries per week as specified on the website. The logged-in submission page is the source for actual remaining allowance. This session redirects to login, so remaining allowance is <strong>unknown</strong>. No password or token should be put into chat or the repository.</p><h3><span class="step-number">3</span> Download and verify a promoted artifact</h3><p>Use the exact file linked in its approved manifest; do not rename an old artifact to create “uniqueness.” Run the project validator against the reference grid and verify its SHA-256. Do not open/resave the TIFF in software that changes pixel values, shape or metadata before upload.</p><pre><code>python -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python scripts/validate_submission.py \
  docs/downloads/{escape(tif)}
# This file currently returns format PASS and promotion NO.
# This command never uploads anything.</code></pre><h3><span class="step-number">4</span> Use the contest's “New submission” form</h3><p>For an actually approved future file, choose the single-band <code>.tif</code>, or its ZIP containing only that TIFF. Paste the short approved note, respect the remaining weekly limit, and wait for organizer processing. Do not upload a report, a training raster, a multi-band TIFF, or this research-only negative surface.</p><h3><span class="step-number">5</span> Retain the organizer receipt</h3><p>Store the submission identifier, exact artifact SHA-256, time, note and copied result from the submission page. Only then label that result <strong>ORGANIZER-CONFIRMED</strong>. The public leaderboard alone does not identify this particular file. The rules require one final selected submission across both prize rounds.</p><p>{link(PROBLEM, 'Official format and metric ↗')} · {link('https://docs.nlr.gov/docs/fy26osti/96647.pdf', 'Official rules PDF ↗')} · {link(SUBMIT, 'Official submissions page (login required) ↗')}</p></section>
<section class="content-section"><h2>Current research identifier — not an upload recommendation</h2><p class="micro">Both name and comment meet the ≤140-character project policy. Copy controls are for the audit trail, not permission to submit.</p><div class="copy-box"><code id="copy-name">{escape(card['submission_name'])}</code><button type="button" data-copy="copy-name">Copy name</button></div><div class="copy-box"><code id="copy-note">{escape(card['submission_note'])}</code><button type="button" data-copy="copy-note">Copy note</button></div><div class="copy-box"><code id="copy-hash">{escape(card['raster_sha256'])}</code><button type="button" data-copy="copy-hash">Copy SHA-256</button></div></section>
<section class="content-section prose"><h2>Autonomous pipeline, not a browser simulation</h2><p>This static site serves the pre-generated artifact and its exact automated receipts. It does not pretend a browser click can train on hundreds of megabytes of geophysical rasters. The Python pipeline restores hashes, reuses the shared cache, tests features, fits spatially held-out models, measures pooled DTI, writes the validated TIFF/ZIP and applies the literal registry STOP. Its ledger blocks rerunning or retuning this stopped experiment. New work belongs to a separately assigned, preregistered future session.</p><p>{link(REPO + '/blob/main/README.md', 'Reproducible commands and full standing request ↗')} · {link('data/run-card.json', 'Exact current decision JSON ↗')}</p></section>'''


def markdown_summary(card, audit):
    h, d = card["holdout"], card["paired_delta_holdout"]
    tif = Path(card["artifact"]).name
    lines = ["# Executive summary — 27 October 2026", "", "## DOWNLOAD: YES (research only). SUBMIT: NO.", "", "[WBG-2 decision, nine-site audit and research download](wbg2.html): literal overlap STOP; no verified holdout or leaderboard estimate. [Earlier four-release review](portfolio-review.html). No new experiment or slot was used.", "",
        f"[Download the frozen research TIFF](downloads/{tif}) · [one-TIFF ZIP](downloads/{tif.replace('.tif', '.zip')}) · [machine-readable run card](data/run-card.json)", "",
        "No final dotted or high-scoring promoted competition submission was produced. The literal surface overlap STOP and negative efficacy screen prohibit promotion. No weekly slot was used.", "",
        f"**HOLDOUT-DTI {h['dti']:.6f}**, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}], evaluator `{card['holdout_instrument']['evaluator_version']}`, {h['withheld_positive_pixels']:,} withheld positives. Continuous confidence surface, not a matched-budget dotted submission or leaderboard estimate.", "",
        f"Paired delta versus refitted 19-band control: **{d['delta']:+.6f}** (HOLDOUT-DTI), 95% CI [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]; same evaluator and positives. No improvement established.", "",
        "| File / site | Observed local result or historical claim | Estimated leaderboard result | Uniqueness / submit decision |", "|---|---|---|---|",
        f"| [{tif}](downloads/{tif}) | HOLDOUT-DTI {h['dti']:.6f}; see CI/version/n above | **Unavailable**; not inferred from proxy | New bytes/pixels among 360 checked hashes, but literal overlap {card['registry']['max_forward_3px_overlap']*100:.2f}% >70%. **DO NOT SUBMIT**. |"]
    for row in audit["rows"]:
        lines.append(f"| {row['site']}: [{row['file']}]({row['immutable_file_url']}?raw=1) | USER-REPORTED historical {row['reported_historical_value']:.4f}; **NOT ORGANIZER-CONFIRMED** | Unavailable for a new file | Historical learning reference; family overlap fails. Do not copy as a unique submission. |")
    lines += ["", "## Earlier four-release follow-up", "", "[All four local download decisions](release-review.html): exact files revalidated, all research-only. WBG-H1 literal lattice overlap exceeds 70%; filtered diagnostics do not clear uniqueness. No new experiment or slot use. [Review and access limits](review-20261027.md).", "", "## Why GEMSDOE32 leads the supplied historical records", "",
        "Exact raster identities: D2.8 44,090 dots → remove 3,891 within 100 m of the catalogue → B1 40,199 → remove 2,545 more within 200 m → B2 37,654. GEMSDOE25 and GEMSDOE30 have identical decoded predictions. GEMSDOE36 contains all B2 pixels plus 1,200 additions. Sparse support and low-marginal-credit pruning can reduce redundant false-positive cost under the official max-cover metric. Hidden labels are unavailable, so that mechanism is plausible, not a proved causal account of each historical result. A 200 m exclusion is not an organizer rule.", "",
        "GEMSDOE32's supplied 0.2778 is USER-REPORTED, not a verified file receipt. The direct official public leaderboard observation on 2026-10-27 was 0.4544; it is not a result for any project TIFF. No leaderboard projection is justified for the new surface.", "", "## Site-by-site findings", ""]
    for row in audit["rows"]:
        lines += [f"### {row['site']} — {HISTORY[row['site']][0]}", HISTORY[row['site']][1], f"Inspected SHA-256: `{row['sha256']}`. [Pinned source]({row['snapshot_url']}).", ""]
    lines += ["## Earlier pre-implementation hypotheses", "", "1. Conductivity/depth Hessian non-coaxiality: lowest cost, highest-priority uncertain benefit; executed once, negative.", "2. Magnetic texture transport in a depth-contour frame: medium cost, untested, related peer ideas exist.", "3. Radiometric compositional changes across terrain saddles: medium cost, conditional on original-layer semantics/coverage verification.", "4. Anisotropic conductivity-boundary persistence: medium cost, untested; related coherence operators already exist.", "", "[Earlier proposals](hypotheses.md) · [Four ranked future hypotheses, source and data-readiness audit](research/future-hypotheses-20261027.md). No numerical improvement was forecast.", "", "## Limitations and next actions", "", "- No assigned lane paragraph was supplied. The screen is provisional research, not an authorized promotion lane.", "- Core data and all 19 band-cache hashes match public owner mirrors, not an independently authenticated organizer-origin manifest.", "- Literal band metadata are ambiguous across documents. Do not claim physical units, heat, permeability or geothermal vent discovery from these numbers.", "- The historical file scores lack organizer submission-page receipts. No hidden test labels or private-score access exists.", "- The nine frozen snapshots are not the entire 92-site/competition registry. No global uniqueness is claimed. The measured duplicate is enough for STOP.", "- The current account allowance is unknown because the submissions page redirects to login. The rules PDF's three-per-week limit is not proof of remaining allowance.", "- An independent future authorized lane needs a clean same-instrument current-best comparator, untouched confirmation, surface and final-dot uniqueness and exact-artifact format validation before a separate selector considers a real slot.", "", "[How to submit a future promoted file](how-to-submit.html) · [official sources and irregularities](evidence.html) · [full prompt](standing-prompt.md)", "", "## Run card", "", "[Download the complete JSON run card](data/run-card.json). Verdict: **negative**.", ""]
    return "\n".join(lines)


def main():
    card = load("registry/run_card.json")
    receipt = json.loads((ROOT / card["artifact"]).with_suffix(".json").read_text())
    audit, sources, issues = load("evidence/nine_site_audit.json"), load("registry/sources.json"), load("registry/irregularities.json")
    feed = load("docs/data/feed.json")
    # Evidence is downloadable from GitHub Pages, not only reachable in a checkout.
    copies = {"experiment.json": "evidence/experiment.json", "registry-surface-audit.json": "evidence/registry_surface_audit.json",
        "nine-site-audit.json": "evidence/nine_site_audit.json", "feature-canaries.json": "evidence/feature_canaries.json",
        "template-integrity.json": "evidence/template_integrity.json", "shared-feature-cache.json": "evidence/shared_feature_cache.json",
        "sources.json": "registry/sources.json", "irregularities.json": "registry/irregularities.json",
        "preregistration.json": "registry/preregistration.json", "repository-snapshots.json": "registry/repository_snapshots.json",
        "focus-files.json": "registry/focus_files.json", "lattice-coverage-certificate.json": "evidence/lattice_coverage_certificate.json",
        "upstream-template-verification.json": "evidence/upstream_template_verification.json",
        "snapshot-commit-verification.json": "evidence/snapshot_commit_verification.json",
        "review-passes.json": "evidence/review_passes.json", "browser-checks.json": "evidence/browser_checks.json",
        "parallel-main-integration.json": "evidence/parallel_main_integration.json",
        "followup-run-card.json": "evidence/followup_run_card_20261027.json",
        "source-review-20261027.json": "evidence/source_review_20261027.json",
        "official-source-audit-20261027.json": "evidence/official_source_audit_20261027.json",
        "session-review-20261027.json": "evidence/repo_review_session_20261027.json",
        "wbg2-review-passes-20261027.json": "evidence/wbg2/review_passes_20261027.json",
        "wbg-s2-safety-20261027.json": "evidence/wbg_s2/safety_review_20261027.json",
        "wbg3-run-card.json": "evidence/wbg3_spipmr/run_card.json",
        "wbg3-uniqueness.json": "evidence/wbg3_spipmr/uniqueness_audit.json",
        "wbg3-canaries.json": "evidence/wbg3_spipmr/leakage_canary.json",
        "wbg3-preregistration.json": "registry/wbg3_preregistration.json",
        "wbg2-followup-audit.json": "evidence/wbg2_followup_audit_20261027.json",
        "focus9-run-card.json": "evidence/focus9_exec/run_card.json",
        "data-manifest.json": "registry/data_manifest.json"}
    for dest, source in copies.items():
        shutil.copyfile(ROOT / source, DOCS / "data" / dest)
    dump_json(DOCS / "data/run-card.json", card)
    from build_start_here import render_body as start_body
    # docs/executive-summary.html is a hand-maintained Focus-9 submission/status
    # page (with its own candidate-specific validation receipts). Do not replace
    # it with the older C1-only summary generated by executive() above.
    pages = {"start-here.html": ("START HERE", start_body()),
        "index.html": ("Overview", home(card, receipt, audit, feed)),
        "research.html": ("Research", research(card)),
        "evidence.html": ("Evidence & sources", evidence(card, sources, issues, feed)),
        "how-to-submit.html": ("How to submit", howto(card, receipt))}
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(page(name, title, body), encoding="utf-8")
    legacy = {"methodology.html": "research.html",
        "sources.html": "evidence.html", "irregularities.html": "evidence.html",
        "submission-guide.html": "how-to-submit.html", "submission-instructions.html": "how-to-submit.html"}
    for name, target in legacy.items():
        archived = "parallel/main-b9a2d53/" + name
        (DOCS / name).write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="0; url={target}"><title>Research page moved</title><link rel="stylesheet" href="assets/style.css"></head><body><main class="wrap"><h1>Research page moved</h1><p><strong>DO NOT SUBMIT the negative research artifacts.</strong></p><p><a href="{target}">Open the current evidence desk</a> · <a href="{archived}">Original frozen parallel page</a></p></main></body></html>''', encoding="utf-8")
    (DOCS / "executive-summary.md").write_text(markdown_summary(card, audit), encoding="utf-8")
    (DOCS / ".nojekyll").touch()
    manifest = {"schema_version": 1, "artifact": Path(card["artifact"]).name, "sha256": card["raster_sha256"],
                "submission_name": card["submission_name"], "note": card["submission_note"],
                "verdict": card["verdict"], "ok_to_download": True, "ok_to_submit": False,
                "artifact_role": card["artifact_role"], "holdout": card["holdout"], "leaderboard_estimate": None,
                "zip_file": receipt["zip_file"], "zip_sha256": receipt["zip_sha256"],
                "warning": "Research surface only. No final dots or promoted competition submission. No organizer score receipt."}
    dump_json(DOCS / "downloads/manifest.json", manifest)
    import importlib.util

    review_spec = importlib.util.spec_from_file_location("build_portfolio_review", ROOT / "scripts/build_portfolio_review.py")
    review_module = importlib.util.module_from_spec(review_spec)
    review_spec.loader.exec_module(review_module)
    if review_module.main() != 0:
        raise RuntimeError("Portfolio artifact validation failed closed")
    spec = importlib.util.spec_from_file_location("wbg_h1_build_pages", ROOT / "scripts" / "wbg_h1_build_pages.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()
    spec = importlib.util.spec_from_file_location("build_release_review", ROOT / "scripts/build_release_review.py")
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    release.build()
    from build_wbg2_site import build as build_wbg2
    build_wbg2()
    from wbg_s2_build_audit_and_docs import main as build_wbg_s2
    build_wbg_s2()
    from build_wbg3_site import build as build_wbg3
    build_wbg3()
    from build_wbg4_site import build as build_wbg4
    build_wbg4()
    from build_wbg5_site import main as build_wbg5
    build_wbg5()
    from build_exec_20261029 import build as build_exec_20261029
    build_exec_20261029()
    print("Built static reports, WBG-H1, WBG-S2, WBG-3, WBG-4, and WBG-5 subsites, the 29 Oct executive summary, and fail-closed research downloads.")


if __name__ == "__main__":
    main()
