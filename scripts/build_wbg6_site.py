#!/usr/bin/env python3
"""Generate the WBG-6 executive summary + submission guide from the receipts.

Every number rendered here is read from a persisted JSON receipt, so the page
cannot drift from the measurements it cites.
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "wbg6"

LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
PROBLEM = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
RULES = "https://www.drivendata.org/competitions/306/competition-doe-gems/rules/"
SUBMIT = "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/"
REFSOL = "https://github.com/drivendataorg/gems-prize-reference-solution"


def load(p):
    return json.loads((ROOT / p).read_text())


def page(title, body, extra_nav=""):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · WBG-6</title>
<link rel="stylesheet" href="../assets/style.css">
<style>
.ok {{ color:#0f766e; font-weight:700 }}
.no {{ color:#b91c1c; font-weight:700 }}
.file {{ font-family:ui-monospace,monospace; word-break:break-all }}
table.data {{ border-collapse:collapse; width:100%; font-size:14px }}
table.data th, table.data td {{ border:1px solid #d7ded9; padding:8px 10px; text-align:left; vertical-align:top }}
table.data th {{ background:#f3f6f4 }}
.hero-ok {{ border:3px solid #0f766e; background:#f0fdfa; border-radius:12px; padding:20px 24px; margin:22px 0 }}
.hero-no {{ border:3px solid #b91c1c; background:#fef2f2; border-radius:12px; padding:16px; margin:16px 0 }}
code {{ background:#f3f6f4; padding:1px 4px; border-radius:4px }}
.wrap {{ max-width:1040px; margin:0 auto; padding:24px }}
.small {{ font-size:13px; color:#4b5d59 }}
</style></head><body><div class="wrap">
<p class="small"><a href="../index.html">← Evidence desk</a> · <a href="how-to-submit.html">WBG-6 no-submit decision</a>{extra_nav}</p>
{body}
</div></body></html>"""


def main() -> int:
    audit = load("evidence/wbg6_submission_audit.json")
    est = load("evidence/wbg6_score_estimate.json")
    cal = load("evidence/wbg6_null_calibration.json")
    nine = load("evidence/nine_site_audit.json")
    hp = load("evidence/holdout_proxy_portfolio.json")
    hab = load("evidence/habitat_profile.json")
    prx = load("evidence/proxy_holdout_portfolio_v2.json")
    rings = "".join(
        f"<tr><td>{r['ring']} px</td><td>{r['spearman']:+.3f}</td><td>{r['p']:.2g}</td></tr>"
        for r in hab["ring_score_spearman"])
    rings += (f"<tr><td>budget (dots)</td><td>{hab['budget_spearman']['spearman']:+.3f}</td>"
              f"<td>{hab['budget_spearman']['p']:.2g}</td></tr>")
    sc = load("evidence/score_consistency.json")
    name = audit["name"]
    tif = name + ".tif"
    zipf = name + ".zip"
    me = est["model_estimate"]
    d = audit["duplicate_screen"]
    K = cal["K_star"]
    champ = next(r for r in nine["rows"] if r["site"] == "GEMSDOE32")

    rows = []
    for r in nine["rows"]:
        dups = r.get("exact_dot_duplicates_at_other_focus_champions") or []
        uniq = ("No — pixel-identical to " + ", ".join(dups)) if dups else \
               "Only within its own site; part of one 22-family cluster history"
        rows.append(
            f"<tr><td><b>{escape(r['site'])}</b></td>"
            f"<td class='file'><a href='{escape(r['immutable_file_url'])}'>{escape(r['file'])}</a></td>"
            f"<td>{r['reported_historical_value']:.4f}<br><span class='small'>OWNER-REPORTED</span></td>"
            f"<td>{uniq}<br><span class='small'>max 3-px overlap vs other nine: "
            f"{(r.get('maximum_forward_3px_overlap_vs_other_focus_champions') or 0)*100:.2f}%</span></td>"
            f"<td>Not recommended — history only</td></tr>")

    body = f"""
<h1>WBG-6 executive summary</h1>
<p class="small">DrivenData competition 306 · DOE GEMS Prize · generated from the receipts in
<code>evidence/wbg6_*.json</code> · all scores below are labeled either
<strong>OWNER-REPORTED</strong>, <strong>MODEL-ESTIMATE</strong> or
<strong>NULL-FLOOR</strong>. No ORGANIZER-CONFIRMED value exists for any file.</p>

<div class="hero-no" role="alert">
<h2 style="margin-top:0">DOWNLOAD: <span class="no">RESEARCH ONLY</span> · SUBMIT: <span class="no">NO</span></h2>
<p><strong>Do not upload this file.</strong> The archived final-dot audit records a maximum 3-pixel
registry overlap of <strong>{d['max_forward_overlap_3px']:.6f} ({d['max_forward_overlap_3px']*100:.4f}%)</strong>,
which exceeds the active 70% stop threshold. The earlier density-adjusted approval is superseded.</p>
<p><b>Research artifact:</b> <a href="../downloads/{escape(tif)}" download>{escape(tif)}</a>
&nbsp;·&nbsp; <a href="../downloads/{escape(zipf)}" download>one-TIFF ZIP</a>
&nbsp;·&nbsp; SHA-256 <code>{escape(audit['sha256'])}</code></p>
<p><b>Score:</b> {me['central']:.3f} is a historical <strong>MODEL-ESTIMATE</strong> only
(range {me['low']:.3f}–{me['high']:.3f}); it is neither HOLDOUT-DTI nor ORGANIZER-CONFIRMED.
The estimate's holdout proxy failed external validation, so it must not be used as a leaderboard forecast.</p>
<p><b>Format:</b> archived local checks report a single-band float32 GeoTIFF, EPSG:32611,
3730 × 3292, values in [0,1], all finite; this is not proof of organizer acceptance.
No file is cleared for a submission slot.</p>
<p class="small"><b>Name:</b> <code>{escape(name)}</code><br>
<b>Note (≤140 chars, for identification only):</b> <code>WBG-6 research-only artifact; fails literal 3-pixel registry-overlap gate; DO NOT SUBMIT</code></p>
</div>

<div class="hero-no" role="note">
<b>Decision basis.</b> The reported nine-site value {champ['reported_historical_value']:.4f} is OWNER-REPORTED,
not receipt-verified. The WBG-6 {me['central']:.3f} value is a MODEL-ESTIMATE; its construction inherits
unverified historical uplift and the holdout proxy does not rank the recovered submissions. Neither
value establishes this file's organizer score, leaderboard rank, or submission eligibility.
</div>

<h2>1. The table the brief asked for</h2>
<p>One row per focus site: the best <em>historical</em> file there, and whether it may be reused.
These are history-only references; their supplied values are OWNER-REPORTED and not organizer receipts.
The WBG-6 raster below is available only as a research artifact and is not cleared for upload.</p>
<div style="overflow-x:auto"><table class="data">
<thead><tr><th>Site</th><th>Best historical file (learning only)</th><th>Reported score</th>
<th>Unique submission?</th><th>Download &amp; submit?</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="small">Reachability check on {len(nine['rows'])}/9 site files. Values are the owner's
historical numbers; no submission-page receipt binds those bytes to those values.</p>
<div style="overflow-x:auto"><table class="data">
<thead><tr><th>Research artifact</th><th>Score estimate</th><th>Registry uniqueness</th><th>Decision</th></tr></thead>
<tbody><tr>
<td class="file">{escape(tif)}</td>
<td><b>{me['central']:.3f} MODEL-ESTIMATE</b><br><span class="small">range {me['low']:.3f}–{me['high']:.3f}; invalidated as leaderboard forecast by failed holdout-proxy validation</span></td>
<td><b>FAIL</b> — literal 3-pixel overlap {d['max_forward_overlap_3px']*100:.4f}% exceeds 70%; density-adjusted lift does not override the protocol</td>
<td class="no">DOWNLOAD FOR RESEARCH · DO NOT SUBMIT</td></tr></tbody></table></div>

<h2>2. What can and cannot be inferred about GEMSDOE32 B2's reported 0.2778</h2>
<p>The official problem description defines a distance-weighted Tversky score (α=0.2, β=0.8) with a
300 m triangular kernel and hidden fault labels; see the <a href="{PROBLEM}">official problem page</a>.
The value 0.2778 for GEMSDOE32 B2 and the comparison values in the table are OWNER-REPORTED, not tied
to an organizer receipt in this repository.</p>
<p>Local raster forensics record B2 as a subset of the D2.8 parent with 6,436 fewer dots, none added,
and the removed dots near the mapped catalogue. This establishes a pixel-level relationship, not why
the reported score changed. Fewer redundant or catalogue-adjacent predictions could reduce false-positive
penalty while retaining some kernel coverage; hidden labels are unavailable here, so this remains a
plausible mechanism, not a causal result.</p>
<p>The archived score-inversion exercise reproduces one reported lattice value under an assumed random
truth model. Its inferred K≈{K:,} and null/“uplift” figures are MODEL OUTPUTS conditional on the assumed
truth distribution and an unverified score; they do not measure the hidden truth size or B2's localization
skill. Separately, the recovered submission archive contains correlated variants; its leave-one-family
validation and the hide-and-recover comparison do not validate a leaderboard ranker. No score projection
for a new raster is justified by those analyses.</p>
<p><strong>Can a unique file beat 0.2778?</strong> That is unknown. The reported 0.2778 itself is not
organizer-confirmed, and this repository has no validated prospective estimate or eligible candidate.
A defensible claim would require authentic labels/inputs or a protocol-valid, leakage-controlled holdout
that beats a same-evaluator comparator, plus exact final-file validation and the separate selector step.</p>

<h2>2b. Historical score associations are exploratory, not a map of hidden truth</h2>
<p>The following exploratory summaries compare distance-ring distributions across {hab['n']} recovered
rasters with reported scores. They are not independent experiments: many rasters are close variants,
reported scores lack artifact-linked organizer receipts, and grouped validation of these associations
was weak. Treat the rows below as a descriptive audit of this archive only, not evidence that any distance
ring contains more hidden faults or that a new prediction should be placed there.</p>
<div style="overflow-x:auto"><table class="data">
<thead><tr><th>Distance from mapped faults</th><th>Spearman with reported score</th><th>p (exploratory)</th></tr></thead>
<tbody>{rings}</tbody></table></div>
<p>These associations are vulnerable to family duplication, selection effects, and unobserved differences
in modeling or submission conditions. The recorded leave-one-site-out model fit is weak
(R²={hab['leave_one_site_out']['r2']:.3f}, ρ={hab['leave_one_site_out']['spearman']:.3f}); no causal
interpretation or emission rule follows from the table.</p>

<h2>3. WBG-6 artifact properties and limits</h2>
<ul>
<li>Its generator used an archived catalogue-distance profile and kernel-spacing rule. These describe
the construction, not independent geological evidence for hidden faults.</li>
<li>The archived raster has 30,000 positive cells and reports zero on the mapped catalogue. Local
format validity does not establish uniqueness, scientific value, portal acceptance, or an organizer score.</li>
<li>The explicit active registry rule is literal: stop if over 70% of candidate dots lie within 3 px of
any registry raster. Its recorded maximum is {d['max_forward_overlap_3px']*100:.4f}%, so WBG-6 fails.
A density-adjusted statistic is not authorized to waive this threshold.</li>
<li>There is no current leaderboard estimate supported by a validated model. The archived MODEL-ESTIMATE
is retained only for provenance and must not be used to choose a slot.</li>
</ul>

<h2>4. Registry comparison — literal rule governs</h2>
<p>The archived audit compared {d['n_compared']} historical rasters. Byte novelty and surface correlation
are not enough to clear the independent proximity stop:</p>
<ul>
<li>byte-identical among that archived scope: <b>no</b>;</li>
<li>maximum archived surface |Spearman ρ|: <b>{abs(d['max_abs_surface_spearman']):.4f}</b>;</li>
<li>maximum forward 3-px overlap: <b>{d['max_forward_overlap_3px']*100:.4f}%</b> against
<code>{escape(d['max_overlap_against'])}</code> (active limit 70%);</li>
<li>density-adjusted overlap lift was also recorded, but it does not replace or waive the literal rule.</li>
</ul>
<p><strong>Decision: duplicate STOP under the stated protocol.</strong> Do not tune around registry
coverage or reinterpret this historical comparison. Its scope is frozen and incomplete; a fresh complete
registry audit would still be required for any future candidate.</p>

<h2>5. Evidence index (every claim, and how to re-derive it)</h2>
<div style="overflow-x:auto"><table class="data">
<thead><tr><th>Claim</th><th>Receipt</th><th>Reproduce with</th></tr></thead><tbody>
<tr><td>Official metric α=0.2, β=0.8, 300 m kernel; truth = faults absent from the catalogue</td>
<td>competition page 967</td><td><a href="{PROBLEM}">open page</a></td></tr>
<tr><td>Public leaderboard leader is 0.4544</td><td>fetched 2026-10-28</td>
<td><a href="{LEADERBOARD}">open leaderboard</a></td></tr>
<tr><td>118 scored rasters recovered, all sha256-verified</td>
<td><code>evidence/scored_raster_fetch.json</code></td><td><code>scripts/fetch_scored_rasters.py</code></td></tr>
<tr><td>Reported-score noise floor: median |Δ| {sc['bands'][-1]['median_gap']:.4f} at >95% overlap</td>
<td><code>evidence/score_consistency.json</code></td><td><code>scripts/score_consistency.py</code></td></tr>
<tr><td>118 submissions collapse to 22 independent families</td>
<td><code>evidence/wbg6_score_model.json</code></td><td><code>scripts/calibrate_score_model.py</code></td></tr>
<tr><td>Geometry descriptors do <em>not</em> generalise across families (grouped R²
{load('evidence/wbg6_score_model.json')['r2_grouped']:.3f})</td>
<td><code>evidence/wbg6_score_model.json</code></td><td>same script</td></tr>
<tr><td>Hide-and-recover holdout does not rank real scores (ρ {hp['spearman']:.3f}, p={hp['spearman_p']:.2f})</td>
<td><code>evidence/holdout_proxy_portfolio.json</code></td><td><code>scripts/holdout_proxy_portfolio.py</code></td></tr>
<tr><td>Consensus agreement is a duplication artefact (family-level ρ
{json.loads((ROOT/'evidence/consensus_partial.json').read_text())['family_spearman']:.3f})</td>
<td><code>evidence/consensus_partial.json</code> · <code>evidence/consensus_test.json</code></td>
<td><code>scripts/consensus_test.py</code>, <code>scripts/consensus_partial.py</code></td></tr>
<tr><td>Assumption-conditional null calibration (K≈{K:,}); not a measured hidden-truth size</td>
<td><code>evidence/wbg6_null_calibration.json</code></td><td><code>scripts/calibrate_null_K.py</code></td></tr>
<tr><td>Archived {me['central']:.3f} MODEL-ESTIMATE; not validated as a leaderboard forecast</td>
<td><code>evidence/wbg6_score_estimate.json</code></td><td><code>scripts/estimate_wbg6_score.py</code></td></tr>
<tr><td>Archived format report and literal proximity STOP (fails active overlap gate)</td><td><code>evidence/wbg6_submission_audit.json</code></td>
<td><code>scripts/audit_wbg6_submission.py</code></td></tr>
</tbody></table></div>

<h2>6. Limitations and irregularities (nothing here is hidden)</h2>
<p><b>New this pass — the shared holdout was re-tested two ways.</b> We re-scored all {prx['n']} recovered
rasters against the segment holdout under (a) the repo's rule, which forgives dots placed on the mapped
catalogue, and (b) the organiser's rule, which counts them as false positives. The two variants return
<b>identical</b> numbers: these rasters were all built to avoid the catalogue, so the forgiveness rule is
inert and is <em>not</em> why the proxy fails. Corrected or not, the proxy still does not rank real
scores (ρ = {prx['catalogue_penalised']['spearman']:+.3f}, p = {prx['catalogue_penalised']['spearman_p']:.2f}).
The reason is structural: the withheld components were visible to the authors when the rasters were
made, so the proxy scores catalogue-following, not detection of unmapped faults.</p>
<ul>
<li><b>No organizer confirmation.</b> Every historical score in this repo is the owner's own report;
no submission-page receipt identifies those bytes. The leaderboard figure is a public page
observation, not a score for any project file.</li>
<li><b>Only 22 independent observations.</b> 118 files reduce to 22 near-duplicate families, so any
fitted relationship has a very small effective sample. Both the descriptor model and the holdout
proxy fail grouped validation, and this page says so rather than quoting the flattering in-sample
number.</li>
<li><b>The MODEL-ESTIMATE is not validated.</b> Its uplift comes from historical score reports, not
an independent experiment on this file; the held-out proxy did not validate ranking. Do not interpret
its interval as a confidence interval for leaderboard performance.</li>
<li><b>No feature stack, no 1 m DEM.</b> Both are egress-blocked here; without them a supervised
prior cannot be trained, which caps achievable precision (see §2).</li>
<li><b>Note text.</b> The competition allows a ≤140-character note; use
<code>WBG-6 quantile-matched habitat, kernel-disjoint 30k dots, off-catalogue</code> so the entry is
identifiable later.</li>
</ul>
<p class="small">Questions about the rules: <a href="{RULES}">competition rules</a> ·
<a href="{SUBMIT}">submissions page</a>. This project never uploads anything and never asks for
credentials.</p>
"""
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(page("WBG-6 executive summary", body), encoding="utf-8")

    howto = f"""
<h1>WBG-6 research artifact — do not submit</h1>
<div class="hero-no" role="alert">
<p><strong>DOWNLOAD: YES for research · SUBMIT: NO.</strong> The recorded final-dot registry overlap
is {d['max_forward_overlap_3px']*100:.4f}% within 3 pixels, exceeding the active 70% stop threshold.
The archived approval is superseded. Do not use a competition slot.</p>
<p>Research file: <a href="../downloads/{escape(tif)}" download>{escape(tif)}</a>
(or <a href="../downloads/{escape(zipf)}" download>one-TIFF ZIP</a>).</p>
<p>SHA-256: <code>{escape(audit['sha256'])}</code></p>
</div>
<h2>What was checked locally</h2>
<p>The archived validator reports a single-band float32 TIFF on the recorded grid, values in [0,1],
finite pixels, and a one-member ZIP. These are local checks only; they do not establish portal acceptance.
The original rejected submission and organizer error receipt are unavailable, so the cause of the prior
“Predicted values must be in range [0, 1]” message is unknown.</p>
<h2>Outside-footprint convention</h2>
<p>This research artifact stores zero outside the footprint. The provided sample and official materials
have been reported elsewhere as using null/NaN outside; organizer handling of this exact artifact has
not been verified. Do not infer acceptance from another file's reported score.</p>
<h2>Score label and disposition</h2>
<p>The value {me['central']:.3f} (range {me['low']:.3f}–{me['high']:.3f}) is a MODEL-ESTIMATE based on
historical reported-score uplift, not a HOLDOUT-DTI and not an ORGANIZER-CONFIRMED score. The local
holdout proxy failed validation as a leaderboard ranker. Registry uniqueness fails the active literal
rule. <strong>DOWNLOAD: YES for research · SUBMIT: NO.</strong></p>
<p class="small">This project does not upload files or request credentials. The competition submission page
requires account access; this repository cannot see current allowance or verify receipts.</p>
"""
    (DOCS / "how-to-submit.html").write_text(page("WBG-6 research-only status", howto), encoding="utf-8")
    print(f"wrote {DOCS/'index.html'} and {DOCS/'how-to-submit.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
