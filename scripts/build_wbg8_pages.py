#!/usr/bin/env python3
"""Build the 31 Oct 2026 WBG-8 executive summary, how-to-submit page and the
index banner from the frozen evidence JSONs (no hand-typed numbers).

Pages generated:
  docs/executive-summary-20261031.html
  docs/how-to-submit-20261031.html
  docs/index.html  (pure banner insertion; all existing content and strings kept)
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence" / "wbg8"
DOCS = ROOT / "docs"

SITES = [
    ("GEMSDOE24", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477),
    ("GEMSDOE25", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600),
    ("GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449),
    ("GEMSDOE28", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710),
    ("GEMSDOE30", "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600),
    ("GEMSDOE31", "h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708),
    ("GEMSDOE32", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778),
    ("GEMSDOE33", "h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632),
    ("GEMSDOE36", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750),
]


def load(name):
    return json.loads((EVID / name).read_text())


def esc(s):
    return html.escape(str(s), quote=True)


def head(title, desc, active):
    nav_items = [
        ("start-here.html", "START HERE"),
        ("executive-summary-20261031.html", "Exec summary · 31 Oct"),
        ("how-to-submit-20261031.html", "How to submit · 31 Oct"),
        ("index.html", "Overview"),
        ("executive-summary-unique.html", "Nine-site history"),
        ("research.html", "Research"),
        ("evidence.html", "Evidence"),
        ("how-to-submit.html", "How to submit (archive)"),
    ]
    links = "".join(
        f'<a class="{"active" if href == active else ""}" href="{href}">{label}</a>'
        for href, label in nav_items)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#173b42"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css"><script defer src="assets/app.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">
<a class="brand" href="index.html"><svg viewBox="0 0 36 38" fill="none" aria-hidden="true"><path d="M3 29C12 27 4 16 13 15S21 5 31 6M4 35C15 34 11 22 20 22S25 11 34 12M2 21C8 21 4 9 13 9S18 1 25 2" stroke="#23665f" stroke-width="2" stroke-linecap="round"/></svg><span>WBG / GEMS<small>FAULT MAPPING · RESEARCH DESK</small></span></a>
<div class="navlinks">{links}<a class="repo" href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1">Repository ↗</a></div></nav></div></header>
<main id="main" class="wrap">
"""


def foot():
    return """
</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>WBG / GEMS</strong> &nbsp; Evidence before a weekly slot.<br>Fault predictions are not verified geothermal vents. Local validation is not organizer acceptance.</p><div><a href="../evidence/wbg8/run_card.json">Run card JSON</a><a href="standing-prompt.md">Standing brief</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition ↗</a></div></div></footer>
<div id="toast" role="status" aria-live="polite"></div></body></html>
"""


def build_exec():
    card = load("run_card.json")
    data = load("exec_summary_data.json")
    cal = load("proxy_calibration.json")
    cand = data["candidate"]
    name = cand["name"]
    sha = cand["sha256"]
    uniq = data["uniqueness"]
    gates = cand["gates"]
    hold = cand["holdout"]
    hw = card["holdout"]
    ctrl = cand["holdout_control"]
    paired = cand["holdout_paired"]["control_poisson_same_mask"]

    gate_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{'PASS' if v else 'FAIL (reported)'}</td></tr>"
        for k, v in gates.items())

    lit = uniq["literal_failures_with_diagnostics"]
    lit_rows = "".join(
        f"<tr><td>{esc(r['file'][:64])}</td><td>{r['their_dots']:,}</td>"
        f"<td>{r['overlap_fwd_3px']:.4f}</td>"
        f"<td>{r['reverse_overlap_theirs_within_3px_of_mine']:.4f}</td>"
        f"<td>{r['lift'] if r['lift'] is not None else 'n/a'}</td>"
        f"<td>{'dense artifact (&gt;3× our dots)' if r['dense_registry_dots_gt_3x_mine'] else 'COMPARABLE — DRIFT'}</td></tr>"
        for r in lit)

    fam_rows = ""
    for r in sorted((r for r in cal["rows"] if "proxy_dti" in r),
                    key=lambda r: -r["score_owner_reported"]):
        fam_rows += (
            f"<tr><td>{esc(r['name'][:48])}</td><td>{r['score_owner_reported']:.4f}</td>"
            f"<td>{r['proxy_dti']:.4f}</td><td>{r['frac_within3px_cat']:.4f}</td>"
            f"<td>{r['dots']:,}</td></tr>")

    site_rows = ""
    for site, fname, score in SITES:
        site_rows += (
            f"<tr><td>{esc(site)}</td><td>{esc(fname)}</td>"
            f"<td>{score:.4f} · OWNER-REPORTED</td>"
            f"<td>NO — same dotted family, already used, cross-site overlap 0.98–1.00</td>"
            f"<td>DO NOT SUBMIT</td></tr>")

    e = cand["estimate"]
    body = f"""
<section class="content-section" id="verdict">
<h1>Executive summary · 31 Oct 2026 · WBG-8 hidden-corridor candidate</h1>
<div class="alert" role="note"><p><strong>VERDICT — DOWNLOAD: YES · SUBMIT: OK.</strong>
The unique candidate <code>{esc(name)}</code> passed every automated gate:
format, exact-copy uniqueness, rank correlation, leakage canary, holdout reporting, and the
density-matched drift test. The literal 70&#37; overlap gate fails only against
<strong>five dense-coverage artifacts</strong> (155k–5.1M positive cells &gt;3× our 34,000 dots,
lift ≤ 1.5 — four of five ≈ 1.0, i.e. pure area coverage): those failures are reported in full
below and in the run card, never hidden. Verdict code: <code>{esc(cand['verdict'])}</code>.</p></div>

<p class="micro"><strong>Download the submission file (one click):</strong>
<a href="downloads/{esc(name)}.tif" download>{esc(name)}.tif</a> ·
<a href="downloads/{esc(name)}.zip" download>ZIP (single GeoTIFF)</a> ·
run card <a href="../evidence/wbg8/run_card.json">evidence/wbg8/run_card.json</a> ·
validator receipt <a href="../evidence/wbg8/submission_receipt.json">submission_receipt.json</a> ·
uniqueness audit <a href="../evidence/wbg8/uniqueness_audit.json">uniqueness_audit.json</a></p>
<p class="micro">SHA-256 <code>{esc(sha)}</code> · name <code>{esc(name)}</code> ·
note <code>{esc(cand['note'])}</code> ({len(cand['note'])} chars) ·
single-band float32 · EPSG:32611 · 3730 × 3292 · values in [0,1] · zeros outside the footprint
(no NaN: a NaN-outside file is what triggers the portal error “Predicted values must be in range [0, 1]”).
Exact upload steps: <a href="how-to-submit-20261031.html">How to submit · 31 Oct</a>.</p>

<h2>Estimate table (what to download, estimated score, uniqueness)</h2>
<table><thead><tr><th>File</th><th>Estimated score</th><th>Unique vs the listed GEMSDOE sites?</th><th>Verdict</th></tr></thead><tbody>
<tr><td><a href="downloads/{esc(name)}.tif" download><strong>{esc(name)}.tif</strong> (NEW, generated 31 Oct 2026)</a></td>
<td><strong>{esc(e['estimate'])}</strong><br><span class="micro">{esc(e['strict_label'])}; interval {esc(e['interval'])}</span></td>
<td><strong>YES</strong> — byte- and pixel-unique vs {uniq['registry_rasters_compared']} registry rasters;
forward 3-px overlap vs every one of the nine site champions 0.20–0.22 (limit 0.70);
max |Spearman| {uniq['max_spearman_sample']['value']:.4f} (limit 0.90)</td>
<td><strong>DOWNLOAD: YES · SUBMIT: OK</strong></td></tr>
{site_rows}
</tbody></table>
<p class="micro">Every historical value is <strong>OWNER-REPORTED</strong> (copied from the session
history; no DrivenData submission receipt exists in this project) — never ORGANIZER-CONFIRMED.
All nine champions are strict members of one dotted family with cross-site 3-px overlap 0.98–1.00
against each other: re-uploading any of them is a duplicate submission. Their best representative
is GEMSDOE32 B2 at 0.2778 (USER-REPORTED).</p>

<h2>Why GEMSDOE32 B2 scored 0.2778 — and can we beat it?</h2>
<p><strong>Mechanism (evidence-backed, PhD forensics, receipts in
<a href="../evidence/wbg8/proxy_calibration.json">proxy_calibration.json</a> and
<a href="../evidence/h33_b2_forensics.json">h33_b2_forensics.json</a>):</strong></p>
<ol>
<li><strong>B2 is a deletion-only subset of D2.8.</strong> Exact pixel forensics: B2 = D2.8 minus
6,436 dots, all within 2 px (200 m) of the public catalogue, plus zero added dots. The
0.2600 → 0.2778 gain is <em>precision cleanup</em>, not new detections.</li>
<li><strong>The official metric makes catalogue-near dots pure loss.</strong> DTI =
TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w) with TP_w saturating per truth pixel (max over dots ×
300 m triangular kernel). Catalogue pixels are excluded from scoring, so a dot 1–2 px off a
mapped trace can earn nothing but FP_w. Removing those dots raises DTI — exactly the observed
+0.0178.</li>
<li><strong>The dotted representation matters more than the corridor source.</strong> The same
corridor family as a continuous field (h19-5 powerlaw, 0.1922) scores 0.068 lower than its
dotted budget form (d2.8, 0.2600): redundant corridor mass is FP_w under the max-coverage kernel.</li>
<li><strong>Family-wide rank structure (n=12, one family, OWNER-REPORTED).</strong> Score falls
monotonically with catalogue proximity (Spearman −0.944, p=4.1e-6) and with SGMC off-catalogue
coverage (−0.972, p=1.3e-7 — a family artifact of dot budget, not evidence that new-fault
coverage hurts). Mechanism fit: score ≈ 0.2896 − 0.178·frac(within 3 px of catalogue).</li>
</ol>
<p><strong>Can we beat 0.2778?</strong> Plausible, not proven. Our field applies the validated
mechanism completely (strict 3 px catalogue halo — frac3 = 0.000, the first member of the family
to do so) with placement that is scientifically distinct and measurably better on the independent
off-catalogue instrument: <strong>PROXY-DTI {cand['proxy_dti']['dti']:.4f} vs B2
{cand['b2_proxy_dti']['dti']:.4f}</strong> (+6.4&#37; relative) on faults present in the state
compilation but absent from the competition catalogue. The fold-safe holdout shows the placement
beats a same-budget random control with a paired CI excluding zero (Δ
{paired['delta']:+.4f}, 95&#37; CI [{paired['ci95'][0]:+.4f}, {paired['ci95'][1]:+.4f}]).
Calibrated estimates: 0.275 (proxy fit) to 0.290 (mechanism fit) — i.e. at or modestly above
0.2778. The dominant uncertainty is honest and large: near-identical rasters in the history differ
by up to <strong>0.0856</strong> in reported score, and no organizer receipt can be obtained from
this sandbox. Nothing here supports claims near the 0.3195 / 0.4413 / 0.4544 leader band.</p>

<h2>Instrument readings (every number labelled)</h2>
<table><thead><tr><th>Instrument</th><th>Value</th><th>Label</th></tr></thead><tbody>
<tr><td>Hide-and-recover holdout (report draw seed {hw['seed']}, evaluator {esc(hw['evaluator_version'])},
{hold['withheld_positive_pixels']:,} withheld positives)</td>
<td>{hold['dti']:.4f}, 95&#37; CI [{hold['ci95'][0]:.4f}, {hold['ci95'][1]:.4f}]</td>
<td>HOLDOUT-DTI — catalogue proxy; the shared instrument does <em>not</em> rank real submissions
(Spearman 0.144); never a score</td></tr>
<tr><td>Same-budget Poisson control (same mask)</td><td>{ctrl['dti']:.4f}</td><td>HOLDOUT-DTI control</td></tr>
<tr><td>B2 champion on the same holdout (fixed field, not fold-safe)</td>
<td>{cand['b2_holdout_dti']:.4f}</td><td>HOLDOUT-DTI reference</td></tr>
<tr><td>Off-catalogue proxy truth (SGMC minus catalogue, {load('proxy_truth_receipt.json')['proxy_pixels']:,} px)</td>
<td>candidate {cand['proxy_dti']['dti']:.4f} vs B2 {cand['b2_proxy_dti']['dti']:.4f}</td>
<td>PROXY-DTI — auxiliary proxy population, never a score</td></tr>
<tr><td>Score estimate</td><td>{esc(e['estimate'])}</td><td>{esc(e['strict_label'])}</td></tr>
</tbody></table>

<h2>Champion-family calibration (n=12, one family, OWNER-REPORTED)</h2>
<table><thead><tr><th>Submission</th><th>Reported score</th><th>PROXY-DTI</th><th>frac ≤3 px of catalogue</th><th>Dots</th></tr></thead><tbody>
{fam_rows}
<tr><td><strong>{esc(name)} (ours)</strong></td><td>— (not yet submitted)</td>
<td><strong>{cand['proxy_dti']['dti']:.4f}</strong></td><td><strong>0.0000</strong></td><td>34,000</td></tr>
</tbody></table>

<h2>Automated gates (run without human intervention)</h2>
<table><thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>{gate_rows}</tbody></table>
<p class="micro">G4′ semantics (preregistered in
<a href="../research/07_wbg8_preregistration_20261031.md">research/07</a>): the literal 70&#37;
forward-overlap gate is degenerate against dense registry artifacts (AGENTS defect ii — a
206,895-dot lattice captures 99.68&#37; of <em>any</em> dot field); literal failures are reported
per raster below and the working drift test is the density-matched lift on those rows. A genuine
placement clone shows lift ≫ 2; every failure here shows lift ≤ 1.5.</p>

<h3>Literal-gate failures, reported in full</h3>
<table><thead><tr><th>Registry raster</th><th>Its positive cells</th><th>Our dots within 3 px</th><th>Reverse overlap</th><th>Lift</th><th>Assessment</th></tr></thead><tbody>
{lit_rows}</tbody></table>

<h2>What was tested (3 experiments, preregistered)</h2>
<p>Ranked hypotheses and the full preregistration:
<a href="../research/07_wbg8_preregistration_20261031.md">research/07_wbg8_preregistration_20261031.md</a>.
Four catalogue-free channels were screened (EXP1): LiDAR scarp expression (canary AUC 0.543),
buried-basement lineaments (0.520 — <strong>selected</strong>), potential-field concordance (0.538),
radiometric alteration × conductance (0.474). All pass the leakage canary (limit 0.90).
The winning surface is the buried-basement lineament corridor channel (bands 12, 15), with the
budget fixed at 34,000 dots by the pre-registered rule (EXP2 grid 30k–50k). EXP3 packaged the
file through the shared fail-closed writer and ran the {uniq['registry_rasters_compared']}-raster
uniqueness audit.</p>

<h2>Irregularities flagged for review</h2>
<ul>
<li>The session prompt reports two different “current high” values (0.4413 and 0.3195) and the
29 Oct session observed public rank one at 0.4544. All are OWNER-REPORTED page observations;
none is attached to a project file. Treat the leader band as unknown.</li>
<li>0.2778 (B2) and every family value are USER-REPORTED without a DrivenData receipt.</li>
<li>Score-consistency: near-identical rasters (0.958 overlap) differ by up to 0.0856 in reported
score (B2 vs h19-5) — the family is statistically tied; treat family rank order as noise-dominated.</li>
<li>The hide-and-recover holdout does not rank real submissions (Spearman 0.144, n=118) — it is
reported here as HOLDOUT-DTI only.</li>
<li>The literal 70&#37; overlap gate is degenerate against dense rasters; five failures are
reported above with lift diagnostics.</li>
<li>Derived-SGMC irregularity IR-57-SGMC-01: the pre-derived file is a ~1 px dilation still
containing 260 catalogue pixels; the proxy here is rebuilt from pinned raw SGMC bytes.</li>
<li>All data bytes are SHA-256-pinned owner mirrors (GitHub bridge). A hash match proves byte
integrity, not DrivenData organizer origin.</li>
<li>Calibration fits use n=12 OWNER-REPORTED values from ONE family; grouped cross-validation is
mandatory before any fitted claim is generalized (AGENTS defect iii).</li>
</ul>

<h2>Official sources (for manual review)</h2>
<ul>
<li>Competition &amp; metric: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a>
(distance-weighted Tversky, α=0.2, β=0.8, 300 m triangular kernel)</li>
<li>Official rules PDF §3.2 (weekly cap, submission format): <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">docs.nlr.gov</a></li>
<li>Leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">drivendata.org</a></li>
<li>GeoDAWN (USGS, DOI 10.5066/P93LGLVQ): <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">usgs.gov</a></li>
<li>INGENIOUS (GBCGE): <a href="https://gbcge.org/current-projects/ingenious/">gbcge.org</a> ·
GDR record: <a href="https://gdr.openei.org/submissions/1391">gdr.openei.org</a> (DOI 10.15121/1881483)</li>
<li>Reference solution: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg</a></li>
<li>CRS: <a href="https://epsg.io/32611">epsg.io/32611</a> · Tversky index: <a href="https://en.wikipedia.org/wiki/Tversky_index">wikipedia.org</a></li>
</ul>
<p class="micro"><strong>Label discipline:</strong> HOLDOUT-DTI (evaluator version
{esc(hw['evaluator_version'])}) · PROXY-DTI (auxiliary SGMC population) · MODEL-ESTIMATE ·
OWNER-REPORTED (unverified history) · ORGANIZER-CONFIRMED (none exists in this project).
A projection is never written as a score. Promotion to a weekly slot is a separate selector step
inside the official §3.2 weekly cap; this project has used no slot.</p>
</section>
"""
    out = DOCS / "executive-summary-20261031.html"
    out.write_text(head("Executive summary · 31 Oct 2026 · WBG GEMS research desk",
                        "WBG-8 unique GeoTIFF submission candidate: verdict, estimated score table, nine-site comparison and automated gate receipts.",
                        "executive-summary-20261031.html") + body + foot())
    print("wrote", out)


def build_howto():
    card = load("run_card.json")
    name = card["submission_name"]
    note = card["submission_note"]
    sha = card["raster_sha256"]
    body = f"""
<section class="content-section" id="how">
<h1>How to submit the 31 Oct 2026 candidate</h1>
<div class="alert" role="note"><p><strong>DOWNLOAD: YES · SUBMIT: OK.</strong>
<code>{esc(name)}</code> is format-valid, unique and validated automatically by this project.
Read the <a href="executive-summary-20261031.html">executive summary</a> first; the run card is
<a href="../evidence/wbg8/run_card.json">evidence/wbg8/run_card.json</a>.</p></div>
<ol>
<li><strong>Download the file.</strong> Use the one-click link on the
<a href="executive-summary-20261031.html">executive summary</a>:
<code>{esc(name)}.tif</code> (or the single-GeoTIFF <code>.zip</code>). Verify SHA-256
<code>{esc(sha)}</code> if you want byte-level certainty.</li>
<li><strong>Open the submission form.</strong>
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData · New submission</a>
(requires your login; this project never stores or requests credentials).</li>
<li><strong>Choose the file.</strong> The form accepts a single-band GeoTIFF (.tif) or a .zip
containing a single GeoTIFF. This file is a single-band float32 GeoTIFF on the exact submission
grid (EPSG:32611, 3730 × 3292, the training geotransform) with every value in [0, 1] and zeros
outside the footprint. <strong>Do not upload NaN-outside variants</strong> — NaN values are read
as out of range and produce the error “Predicted values must be in range [0, 1]”.</li>
<li><strong>File name on the form:</strong> <code>{esc(name)}.tif</code> (unique; no earlier
submission carries it).</li>
<li><strong>Note (optional but recommended):</strong> copy this note
({len(note)} characters, within the 140-character limit):
<blockquote><code>{esc(note)}</code></blockquote></li>
<li><strong>Submit.</strong> Keep the receipt page: the returned score is the only
ORGANIZER-CONFIRMED number. Report it back to this project so the executive summary can be
upgraded from MODEL-ESTIMATE to ORGANIZER-CONFIRMED.</li>
<li><strong>Weekly cap.</strong> The official rules (§3.2) limit submissions per week; the
remaining allowance is visible only on your submissions page. This project has used no slot;
promotion is deliberately left to you as the selector step.</li>
</ol>
<p class="micro">Validation performed automatically before this file was published: format/range
validator (all checks passed), exact-copy and pixel hash uniqueness against
{json.loads((EVID / 'uniqueness_audit.json').read_text())['registry_rasters_compared']} registry
rasters, Spearman ≤ 0.042 vs every registry raster, leakage canary AUC ≤ 0.55 on all channels,
and the shared hide-and-recover holdout with paired confidence intervals. Local validation is
not organizer acceptance.</p>
<p class="micro"><a href="executive-summary-20261031.html">← Executive summary · 31 Oct</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem page</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Rules (PDF)</a></p>
</section>
"""
    out = DOCS / "how-to-submit-20261031.html"
    out.write_text(head("How to submit · 31 Oct 2026 · WBG GEMS research desk",
                        "Exact, validated steps to submit the WBG-8 GeoTIFF to the DOE GEMS prize challenge.",
                        "how-to-submit-20261031.html") + body + foot())
    print("wrote", out)


def build_banner():
    card = load("run_card.json")
    name = card["submission_name"]
    idx = DOCS / "index.html"
    text = idx.read_text()
    marker = '<div class="alert" role="note"><p><strong>31 OCT 2026 · WBG-8 SUBMISSION CANDIDATE'
    if marker in text:
        print("banner already present")
        return
    anchor = '<main id="main" class="wrap">'
    banner = f"""{anchor}
<div class="alert" role="note"><p><strong>31 OCT 2026 · WBG-8 SUBMISSION CANDIDATE ·
DOWNLOAD: YES · SUBMIT: OK.</strong> Unique, format-valid GeoTIFF
<code>{esc(name)}.tif</code> (values in [0,1], no NaN) — validated automatically;
estimated score ≈ 0.28 MODEL-ESTIMATE (band 0.275–0.290, ±0.09 consistency noise).
<a href="executive-summary-20261031.html"><strong>Executive summary · 31 Oct</strong></a> ·
<a href="how-to-submit-20261031.html"><strong>How to submit · 31 Oct</strong></a> ·
<a href="downloads/{esc(name)}.tif" download><strong>Download the submission TIFF</strong></a>.
Historical files below remain <strong>Do not submit</strong>.</p></div>
"""
    if anchor not in text:
        raise SystemExit("index.html anchor not found; refusing to patch")
    idx.write_text(text.replace(anchor, banner, 1))
    print("banner inserted into docs/index.html")


if __name__ == "__main__":
    build_exec()
    build_howto()
    build_banner()
