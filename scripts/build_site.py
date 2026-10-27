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
    nav = [("index.html", "Overview"), ("wbg2.html", "WBG-2 audit"),
           ("executive-summary.html", "Site comparison"),
           ("research.html", "Research"), ("evidence.html", "Evidence"), ("how-to-submit.html", "How to submit")]
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
<main id="main" class="wrap"><div class="breadcrumb">GEMS prize challenge <span>/</span> {escape(title)} <span>/</span> 26 OCT 2026 frozen experiment</div><p class="micro"><a href="portfolio-review.html">27 October follow-up: four earlier releases and trust corrections →</a></p>{body}</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>WBG / GEMS</strong> &nbsp; Evidence before a weekly slot.<br>Fault predictions are not verified geothermal vents. Local validation is not organizer acceptance.</p><div>{link('data/run-card.json', 'Run card JSON')}{link('standing-prompt.md', 'Standing brief')}{link('parallel/main-b9a2d53/index.html', 'Parallel negative archives')}{link(REPO, 'Source code ↗')}</div></div></footer>
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
    return '''<section class="section"><div class="section-heading"><div><span class="section-num">04 / PARALLEL WORK PRESERVED</span><h2>Separate lanes. Frozen negative results.</h2><p>WBG-H1 (DPGF-1), TIP1 and MVGZ ran as independent parallel lanes alongside WBG-C1. Each retains its own frozen Run Card, validator receipt and zero-slot-expenditure decision.</p></div></div><div class="two-col" style="margin-bottom:18px"><article class="mini-card"><span class="index">PARALLEL LANE / WBG-H1 (DPGF-1 · EXP-3)</span><h3>Dip-projected basement coupling + 300 m CELF</h3><p>66-channel label-free geophysical stack + LiDAR-dual ensemble + two-regime 300 m CELF emitter. Recorded candidate <strong>HOLDOUT-DTI 0.123310</strong>, 95% CI [0.108921, 0.137557], versus matched B0 <strong>HOLDOUT-DTI 0.103855</strong>, 95% CI [0.090213, 0.117398]; both <code>gems-segment-pooled-v1</code>, 60,988 withheld positives. The paired difference is +0.019455, 95% CI [+0.007288, +0.031848]; not a leaderboard forecast. <strong>Literal registry STOP:</strong> 99.8035% forward overlap with the registered lattice exceeds 70%; a 64.49% sparse-peer-only diagnostic cannot override it. Verdict negative; format checks are not portal acceptance. The original linked card includes superseded interpretations.</p><a class="text-link" href="wbg-h1-dpgf1/index.html">Open WBG-H1 dashboard &amp; 9-site audit ↗</a> · <a class="text-link" href="wbg-h1-dpgf1/executive-summary.html">Upload guide ↗</a> · <a class="text-link" href="downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif">Download WBG-H1 .tif ↓</a> · <a class="text-link" href="wbg-h1-dpgf1/data/run_card.json">WBG-H1 Run Card JSON ↗</a></article><article class="mini-card"><span class="index">INHERITED / TIP1 &amp; MVGZ</span><h3>Directional tip &amp; magnetic valley lanes</h3><p>Retained TIP1 and MVGZ negative artifacts, tests and evidence remain byte-intact under their original evaluators and splits; neither authorizes a competition slot.</p><a class="text-link" href="data/tip1_run_card.json">Frozen TIP1 card ↗</a> · <a class="text-link" href="evidence/run_card.json">Frozen MVGZ card ↗</a> · <a class="text-link" href="parallel/main-b9a2d53/index.html">Original parallel site ↗</a> · <a class="text-link" href="data/parallel-main-integration.json">Integration receipt ↗</a></article></div></section>'''


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


def home(card, receipt, audit, feed):
    score = card["holdout"]
    return wbg2_banner() + f'''<section class="hero"><div><p class="eyebrow">Evidence first. Every submission.</p><h1>A fresh TIFF.<br>An <em>honest decision.</em></h1><p class="lead">An auditable research desk for the GEMS fault-mapping challenge. Nine sites compared, one distinct hypothesis tested, and no weekly slot wasted on an unproven idea.</p><div class="actions">{link('executive-summary.html', 'Read executive summary  →', 'button secondary')}{link('evidence.html', 'Inspect the evidence ↗', 'text-link')}</div><p class="micro" style="margin-top:20px">C1 frozen screen: 26 October 2026 · Verdict <strong>NEGATIVE</strong><br>The experiment did not beat its control. “Format valid” never means “ready to submit.”</p></div>{download_card(card, receipt)}</section>
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
    return wbg2_banner() + f'''<section class="subhero"><div><p class="eyebrow">Executive summary · decision memo</p><h1>What should you submit?<br><em>Nothing from this run.</em></h1><p class="lead">A new, format-valid TIFF is available, but it does not clear the scientific or literal uniqueness gates. The highest supplied historical value belongs to GEMSDOE32; copying it would violate the unique-submission requirement.</p></div>{pill('Negative · no real slot', 'no')}</section>{alert()}
<div class="two-col content-section"><div class="panel"><div class="panel-head">Current deliverable{pill('Research only', 'warn')}</div><div class="panel-pad"><div class="filename">{escape(tif)}</div><div class="actions"><a class="button" href="downloads/{tif}" download>Download research TIFF ↓</a>{link('downloads/' + tif.replace('.tif', '.zip'), 'One-TIFF ZIP ↓', 'button secondary')}</div><p class="micro" style="margin-top:15px">DOWNLOAD: YES · SUBMIT: NO. This is a continuous unplaced surface, not a final dotted submission. Organizer-confirmed score and leaderboard estimate are both <strong>unavailable</strong>.</p></div></div><div class="panel"><div class="panel-head">Measured screen<span>HOLDOUT-DTI, not forecast</span></div><div class="panel-pad"><p><strong>Candidate {h['dti']:.6f}</strong> · 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]<br><strong>Control {c['dti']:.6f}</strong> · 95% CI [{c['ci95'][0]:.6f}, {c['ci95'][1]:.6f}]</p><p class="micro">Paired delta {d['delta']:+.6f}; 95% CI [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]. Evaluator <code>{card['holdout_instrument']['evaluator_version']}</code>; {h['withheld_positive_pixels']:,} withheld positives; {card['holdout_instrument']['physical_bootstrap_clusters']} physical bootstrap clusters.</p></div></div></div>
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
    return f'''<section class="subhero"><div><p class="eyebrow">Submission guide · for a future promoted file</p><h1>Validate the exact file.<br><em>Then earn the slot.</em></h1><p class="lead">The current download is a negative research result. These instructions explain the future submission process; they do not authorize uploading this file.</p></div>{pill('Current file: do not submit', 'no')}</section>{alert()}
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
        "wbg2-review-passes-20261027.json": "evidence/wbg2/review_passes_20261027.json"}
    for dest, source in copies.items():
        shutil.copyfile(ROOT / source, DOCS / "data" / dest)
    dump_json(DOCS / "data/run-card.json", card)
    pages = {"index.html": ("Overview", home(card, receipt, audit, feed)),
        "executive-summary.html": ("Executive summary", executive(card, receipt, audit, feed)),
        "research.html": ("Research", research(card)),
        "evidence.html": ("Evidence & sources", evidence(card, sources, issues, feed)),
        "how-to-submit.html": ("How to submit", howto(card, receipt))}
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(page(name, title, body), encoding="utf-8")
    legacy = {"hypotheses.html": "research.html", "methodology.html": "research.html",
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
    print("Built five static pages, executive-summary Markdown, WBG-H1 subsite, evidence downloads and fail-closed manifest.")


if __name__ == "__main__":
    main()
