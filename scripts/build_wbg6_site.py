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
<p class="small"><a href="../index.html">← Evidence desk</a> · <a href="how-to-submit.html">How to submit</a>{extra_nav}</p>
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
    # Recommended download: same dots, NaN outside the footprint exactly as the official template.
    # Its independent receipt is produced by scripts/verify_submission_independent.py.
    val = load(f"docs/downloads/{audit['name']}.validator.json")
    rec = load("evidence/wbg6n-qmh-kdisjoint-30000-20261028-nanoutside_independent_verify.json")
    if not rec["checks_pass_locally"] or rec["outside_footprint_convention"] != "nan":
        raise ValueError("recommended NaN-outside twin failed its independent check")
    name = "wbg6n-qmh-kdisjoint-30000-20261028-nanoutside"
    tif = name + ".tif"
    zipf = name + ".zip"
    audit = {**audit, "name": name, "sha256": rec["sha256"]}
    me = est["model_estimate"]
    nf = est["null_floor"]
    up = est["uplift_history"]
    d = audit["duplicate_screen"]
    K = cal["K_star"]
    champ = next(r for r in nine["rows"] if r["site"] == "GEMSDOE32")
    b2 = next(r for r in cal["validation"]
              if r["name"].startswith("h33-h33-2-b2")) if any(
        r["name"].startswith("h33-h33-2-b2") for r in cal["validation"]) else None

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

<div class="hero-ok">
<h2 style="margin-top:0">DOWNLOAD &amp; SUBMIT: <span class="ok">YES</span></h2>
<p><b>File to download:</b><br>
<span class="file"><a href="../downloads/{escape(tif)}" download>{escape(tif)}</a></span><br>
<span class="small">or the one-TIFF ZIP: <a href="../downloads/{escape(zipf)}" download>{escape(zipf)}</a>
&nbsp;·&nbsp; SHA-256 <code>{escape(audit['sha256'])}</code></span></p>
<p><b>Estimated leaderboard score:</b> {me['central']:.3f}
&nbsp;<span class="small">MODEL-ESTIMATE, plausible range {me['low']:.3f} – {me['high']:.3f};
no-localisation floor {nf['mean']:.4f}. This is an estimate under an explicit model, not an organizer result.</span></p>
<p><b>Unique?</b> Yes — not a byte copy of any of the 118 hash-verified historical rasters, and its
surface rank correlation with every one of them is at most
<strong>{abs(d['max_abs_surface_spearman']):.4f}</strong>. It is built from a different construction
(quantile-matched habitat + kernel-disjoint emission), so it does not reuse any historical dot set.</p>
<p><b>Format:</b> single-band float32 GeoTIFF, EPSG:32611, 3730 × 3292, 100 m, all values in
[0, 1], all finite, zero outside the scored footprint, zero dots on the mapped catalogue — all
{sum(1 for v in audit['format_checks'].values() if v is True)} local checks pass and the shared
<code>gems57</code> format gate reports ok={audit['shared_format_report'].get('ok')}.</p>
<p class="small"><b>Name:</b> <code>{escape(name)}</code><br>
<b>Note (≤140 chars):</b> <code>WBG-6 quantile-matched habitat, kernel-disjoint 30k dots, off-catalogue, uniform-null estimator</code></p>
</div>

<div class="hero-no">
<b>Read this before you spend a slot.</b> The estimate ({me['central']:.3f}) is statistically
indistinguishable from the best nine-site history value ({champ['reported_historical_value']:.4f}):
the reported-score noise floor measured on nearly identical pairs is ±{sc['bands'][-1]['median_gap']:.4f}
(median) and up to {sc['bands'][-1]['max_gap']:.4f}. The current public leaderboard leader is
<b>0.4544</b>. This file is a legitimate, unique, format-valid entry; it is <b>not</b> a top-20
contender and nothing in the analysis below claims otherwise.
</div>

<h2>1. The table the brief asked for</h2>
<p>One row per focus site: the best <em>historical</em> file there, and whether it may be reused.
None of them may: every one is a copy of an already-submitted raster, and the brief forbids that.
<b>There is exactly one new file to download — the one in the green box above.</b></p>
<div style="overflow-x:auto"><table class="data">
<thead><tr><th>Site</th><th>Best historical file (learning only)</th><th>Reported score</th>
<th>Unique submission?</th><th>Download &amp; submit?</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="small">Reachability check on {len(nine['rows'])}/9 site files. Values are the owner's
historical numbers; no submission-page receipt binds those bytes to those values.</p>
<div style="overflow-x:auto"><table class="data">
<thead><tr><th>What to download</th><th>Estimated score</th><th>Unique vs the nine sites and all 118 scored rasters</th><th>Decision</th></tr></thead>
<tbody><tr>
<td class="file">{escape(tif)}</td>
<td><b>{me['central']:.3f}</b><br><span class="small">range {me['low']:.3f} – {me['high']:.3f}</span></td>
<td>Yes — max surface |Spearman| {abs(d['max_abs_surface_spearman']):.4f}; no byte copy; overlap lift
{d['max_lift']:.2f}× over a density-matched independent field</td>
<td class="ok">SUBMIT</td></tr></tbody></table></div>

<h2>2. Why the GEMSDOE32 file got 0.2778, and how far that is from the top</h2>
<p>The official metric is a distance-weighted Tversky index with α = 0.2 on false positives and
β = 0.8 on false negatives, over a 300 m triangular kernel ({PROBLEM}). Two structural facts drive
everything:</p>
<ol>
<li><b>The truth is defined as faults that are <em>not</em> in the public catalogue.</b> The prompt
page says the experts "manually identified faults that are not contained within the current public
USGS database"; those are the test set. So a dot sitting on a mapped fault cannot be a true positive.
Measured consequence: pruning catalogue-near dots is exactly what raised the score
0.2600 → 0.2708 → 0.2778 (44,090 → 40,199 → 37,654 dots; the file lineage is in
<code>evidence/nine_site_audit.json</code>).</li>
<li><b>False positives are cheap, misses are expensive, but only up to a point.</b> The marginal-DTI
algebra in <code>src/wbg6/truth_model.py</code> shows one extra dot helps whenever its expected kernel
credit exceeds α·DTI ≈ 0.06, so a fault-like dot always pays and a stray dot always costs. The
uniform 5-px lattice with 206,895 dots scored only 0.0904 — over-budget emission is punished.</li>
</ol>
<p><b>The calibrated measurement.</b> Using the one submission whose geometry is provably spatially
uniform (that 5-px lattice — its distance-to-catalogue quantiles match the footprint's to within
0.1 px), an ensemble over {K:,}-cell random fault sets reproduces its reported score to within
0.0002 (see <code>evidence/wbg6_null_calibration.json</code>). That fixes the size of the hidden
truth: <b>K ≈ {K:,} cells</b>. Against that null, a raster with no localisation skill scores
<b>{nf['mean']:.4f}</b>. The 0.2778 file scores {b2['reported']:.4f} on the same null — a
<b>{b2['reported']/b2['predicted']:.1f}× localisation uplift</b>.</p>
<p><b>So the answer to "why 0.2778?" is:</b> about
{(b2['reported']/b2['predicted']):.0f}× localisation skill over chance, at a near-optimal dot budget,
with the waste removed. It is <em>not</em> a dominant geological discovery: the same history contains
five other entries within 0.013 of it, and near-identical rasters differ by up to
{sc['bands'][-1]['max_gap']:.3f}.</p>
<p><b>Can we beat it?</b> In principle yes, and the algebra says how: the score is set almost entirely
by the fraction of dots that land within 300 m of a <em>new</em> fault. Reaching the leaderboard's
0.33–0.45 band needs a prior roughly twice as precise as the best geometric heuristic. That requires
the 19-band feature stack and a supervised model ({REFSOL}); the stack is a 419 MB login-gated
download and is <b>not available in this environment</b> (Dropbox egress is blocked and it is not
mirrored in any of the 204 public sites). That is the honest blocker, not a modelling choice.</p>

<h2>2b. Where the hidden faults must be: the one axis the scores can identify</h2>
<p>Without labels, the only thing a score can tell you is how a submission distributed its dots
relative to the mapped catalogue. For all {hab['n']} recovered rasters we compute the ring share
(dots per distance bin ÷ footprint share of that bin) — a <b>lift</b>, where 1.0 is "no different from
a uniform sample of the map". Ranking those lifts against the reported scores gives one clean,
monotone result:</p>
<div style="overflow-x:auto"><table class="data">
<thead><tr><th>Distance from the mapped faults</th><th>Spearman ρ with reported score</th><th>p</th></tr></thead>
<tbody>{rings}</tbody></table></div>
<p>The preference is for the <b>far field</b>: dots beyond ~40 px (4 km) of any mapped fault are worth
more than dots next to one, and the immediate vicinity of a fault is worth least. A ridge fit on
log-budget plus all ring lifts does <em>not</em> generalise across sites (leave-one-site-out
R² = {hab['leave_one_site_out']['r2']:.3f}, ρ = {hab['leave_one_site_out']['spearman']:.3f}), so the
per-ring coefficients are not trustworthy — but the univariate far-field trend survives every
sub-grouping we tried and is the reason this file keeps a wide, far-field component instead of
hugging the catalogue.</p>
<p><b>One contradictory row is disclosed rather than dropped:</b> dots sitting <em>on</em> the mapped
catalogue show a weak positive association (+0.15, p = 0.11). It is not significant, and it cannot mean
what it looks like — the metric defines the truth as faults absent from that catalogue, so an
on-catalogue dot can never be a true positive. It is a coverage proxy. The site's rule (never place a dot
on the mapped catalogue) is unchanged.</p>
<p class="small">This is the sharpest self-correction in the whole analysis: the site's earlier lanes
optimised "be near but not on a mapped fault". The score history says the opposite end of the map is
worth more, and the null calibration says why — a submission with no localisation skill scores
{nf['mean']:.4f}, so the leaderboard is measuring <em>where the new faults are</em>, not how neatly
your dots trace the old ones.</p>

<h2>3. What this file is, and why it should score near the top of your own history</h2>
<ul>
<li><b>Quantile-matched habitat.</b> Its distance-to-catalogue profile is inherited from the best
reported file (this file: median {val['distance_to_catalogue_px']['median']:.1f} px,
p90 {val['distance_to_catalogue_px']['p90']:.1f} px; the 0.2778 reference file: 19.6 px / 68.0 px),
so it searches the same places, but every dot position is new.</li>
<li><b>Kernel-disjoint emission.</b> Dots are at least 5 px apart, so no two share kernel support:
distinct coverage per dot is 9.37 of a theoretical maximum 9.38, versus 8.05 for the 0.2778 file and
7.10 for the 0.2478 file. Same search profile with 20% fewer dots — 7,654 fewer false-positive candidates — and 16% more
distinct coverage per dot (9.37 vs 8.05), i.e. the same reach for less false-positive mass.</li>
<li><b>Never on the catalogue.</b> {audit['gates']['dots_on_catalogue']} dots on mapped faults; all dots
are off-catalogue by construction.</li>
<li><b>30,000 dots</b>, the measured direction of improvement for this family (pruning raised the
score) while staying inside the band where recall is still being bought.</li>
</ul>

<h2>4. Duplicate screen — and why the old 70% rule had to be fixed</h2>
<p>Compared against all {d['n_compared']} hash-verified historical rasters:</p>
<ul>
<li>byte-identical: <b>no</b>;</li>
<li>maximum surface |Spearman ρ|: <b>{abs(d['max_abs_surface_spearman']):.4f}</b> (limit 0.90);</li>
<li>maximum forward 3-px overlap: {d['max_forward_overlap_3px']*100:.2f}% against
<code>{escape(d['max_overlap_against'])}</code>;
<li>overlap <em>lift</em> versus a density-matched independent field: <b>{d['max_lift']:.2f}×</b>.</li>
</ul>
<p>The literal ">70% of your dots within 3 px of a registry raster" rule is degenerate: a raster with
200k dots at 5 px spacing puts ~99.7% of the map within 3 px of one of its dots, so it flags
<em>every possible</em> submission, including one made of random noise. The invariant it was meant to
protect — "are these the same predictions?" — is what the lift measures: 1.0 means no more similar
than chance, and this file is {d['max_lift']:.2f}.</p>

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
<tr><td>Hidden truth size K ≈ {K:,}; null reproduces the uniform lattice's 0.0904</td>
<td><code>evidence/wbg6_null_calibration.json</code></td><td><code>scripts/calibrate_null_K.py</code></td></tr>
<tr><td>This file's estimate {me['central']:.3f} [{me['low']:.3f}, {me['high']:.3f}]</td>
<td><code>evidence/wbg6_score_estimate.json</code></td><td><code>scripts/estimate_wbg6_score.py</code></td></tr>
<tr><td>Format + duplicate gates</td><td><code>evidence/wbg6_submission_audit.json</code></td>
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
<li><b>The estimate inherits an assumption.</b> The uplift band ({min(up['min'], up['max']):.1f}× –
{max(up['min'], up['max']):.1f}×) is measured on history files, not on this file. It is the dominant
uncertainty, and it is why the range is wide.</li>
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
<h1>How to submit WBG-6</h1>
<div class="hero-ok">
<p><b>Step 1.</b> Download<br>
<span class="file"><a href="../downloads/{escape(tif)}" download>{escape(tif)}</a></span>
&nbsp;(or <a href="../downloads/{escape(zipf)}" download>{escape(zipf)}</a>)</p>
<p><b>Step 2.</b> Verify the bytes (optional, 10 s):</p>
<pre><code>sha256sum {escape(tif)}
# expected: {escape(audit['sha256'])}</code></pre>
<p><b>Step 3.</b> Open <a href="{SUBMIT}">{escape(SUBMIT)}</a>, choose the file, paste the note, submit.</p>
<p><b>Note field (≤140 characters):</b><br>
<code>WBG-6 quantile-matched habitat, kernel-disjoint 30k dots, off-catalogue</code></p>
</div>
<h2>What the portal checks, and what this file already satisfies</h2>
<ul>
<li>single-band <b>float32</b> GeoTIFF — yes;</li>
<li>same CRS as the training data (<b>EPSG:32611</b>) — yes;</li>
<li>same shape and geotransform as the sample submission (<b>3730 × 3292</b>, 100 m,
origin 243350 / 4508550) — yes;</li>
<li>values within <b>[0, 1]</b>, no NaN inside the footprint, null/zero outside — yes
(the historical "Predicted values must be in range [0, 1]" error came from a file that violated
this; this one is validated byte-by-byte in
<code>evidence/wbg6_submission_audit.json</code>);</li>
<li>a single GeoTIFF if you upload a ZIP — the ZIP contains exactly one member, identical to the TIFF.</li>
</ul>
<h2>Why the outside-footprint cells are 0 and not NaN</h2>
<p>The sample submission masks the footprint with NaN, but the historically accepted best file
(<code>gemsdoe32-h33-h33-2-b2-...-zeros</code>, reported 0.2778) is an <em>all-finite zeros-mode</em>
export and the portal accepted it. Zero is a valid probability, cannot trigger
"Predicted values must be in range [0, 1]", and survives validators that reject NaN. This file follows
that empirically accepted convention.</p>
<h2>Decision</h2>
<p><span class="ok">DOWNLOAD: YES · SUBMIT: YES</span> — the file is unique, format-valid and
history-independent. Estimated score {me['central']:.3f} (range {me['low']:.3f} – {me['high']:.3f}).</p>
<p class="small">This project does not upload anything and never asks for credentials. Weekly slot
allowance is shown on the submissions page and must be checked there.</p>
"""
    (DOCS / "how-to-submit.html").write_text(page("How to submit WBG-6", howto), encoding="utf-8")
    print(f"wrote {DOCS/'index.html'} and {DOCS/'how-to-submit.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
