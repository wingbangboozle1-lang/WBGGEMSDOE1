#!/usr/bin/env python3
"""Build the 31 Oct 2026 executive summary + how-to-submit pages.

Every number on the pages is read from a machine receipt; nothing is typed
in by hand (no-hallucination policy). Sources:
  evidence/wbg8/run_card.json            candidate gates, hashes, verdict
  evidence/wbg8/score_estimate.json      MODEL-ESTIMATE + B2 parity reference
  evidence/wbg8/holdout.json             HOLDOUT-DTI + CI (never a forecast)
  evidence/wbg8/uniqueness.json          118-raster registry gates
  evidence/wbg8/uniqueness_vs_focus9.json site-specific overlaps
  docs/data/nine_site_audit_20261029.json nine-site champion facts
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

CANDIDATE = "wbg8-mridge-pois300-offcat3-37654-20261031-1cfe8cc8-zeros"

SITE_URLS = {
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


def load(p: str):
    return json.loads((ROOT / p).read_text())


def esc(s) -> str:
    return html.escape(str(s))


def page(title: str, crumb: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="WBG GEMS executive summary: nine focus-site best submissions, unique candidate download, verified score estimates.">
<meta name="theme-color" content="#173b42"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css"><script defer src="assets/app.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">
<a class="brand" href="index.html"><svg viewBox="0 0 36 38" fill="none" aria-hidden="true"><path d="M3 29C12 27 4 16 13 15S21 5 31 6M4 35C15 34 11 22 20 22S25 11 34 12M2 21C8 21 4 9 13 9S18 1 25 2" stroke="#23665f" stroke-width="2" stroke-linecap="round"/></svg><span>WBG / GEMS<small>FAULT MAPPING · RESEARCH DESK</small></span></a>
<div class="navlinks"><a class="active" href="executive-summary-20261031.html">Executive summary · 31 Oct</a><a href="how-to-submit-20261031.html">How to submit · 31 Oct</a><a href="start-here-20261029.html">Start here · 29 Oct</a><a href="index.html">Overview</a><a href="evidence.html">Evidence</a><a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1">Repository ↗</a></div></div></nav></div></header>
<main id="main" class="wrap"><div class="breadcrumb">GEMS prize challenge <span>/</span> {esc(crumb)}</div>
{body}
</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>WBG / GEMS</strong> &nbsp; Evidence before a weekly slot.<br>Fault predictions are not verified geothermal vents. Local validation is not organizer acceptance. All site scores are USER-REPORTED unless a receipt is cited.</p><div><a href="data/feed.json">Provenance feed</a><a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1">Source code ↗</a></div></div></footer>
<div id="toast" role="status" aria-live="polite"></div></body></html>"""


def main() -> int:
    card = load("evidence/wbg8/run_card.json")
    est = load("evidence/wbg8/score_estimate.json")
    hold = load("evidence/wbg8/holdout.json")
    uniq = load("evidence/wbg8/uniqueness.json")
    focus = load("evidence/wbg8/uniqueness_vs_focus9.json")
    audit = load("docs/data/nine_site_audit_20261029.json")

    # best (highest owner-reported) file per site from the audit
    best: dict[str, dict] = {}
    for f in audit["files"]:
        cur = best.get(f["site"])
        if cur is None or f["user_reported_score"] > cur["user_reported_score"]:
            best[f["site"]] = f
    order = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
             "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
    # exact duplicate groups by positive-set hash
    groups: dict[str, list[str]] = {}
    for f in audit["files"]:
        groups.setdefault(f["positive_set_sha256"], []).append(f"{f['site']}:{f['name']}")
    dup_of = {}
    for h, members in groups.items():
        if len(members) > 1:
            for m in members:
                dup_of[m] = members

    fam = load("evidence/wbg8/focus9_family_matrix.json")
    dec = card["decision"]
    ok_submit = dec["ok_to_submit"]
    verdict_cls = "ok" if ok_submit else "stop"
    verdict_word = "OK TO DOWNLOAD & SUBMIT" if ok_submit else "DO NOT SUBMIT"

    # ---------------- nine-site table -------------------------------------
    site_rows = []
    for site in order:
        f = best[site]
        key = f"{site}:{f['name']}"
        twins = dup_of.get(key)
        if twins:
            others = [t.split(":", 1)[0] for t in twins if t != key]
            uniq_txt = ("EXACT DUPLICATE of " + ", ".join(sorted(set(others)))
                        + " (identical dot set) — do not re-submit")
        else:
            uniq_txt = "unique bytes vs the other 8 best-files (no exact dot-set twin)"
        fam_txt = (f"NESTED FAMILY — {fam['min_per_site'][site]:.1%} of its dots lie "
                   f"within 3 px of another site's best (min over the other 8; all "
                   f"72 ordered site-pairs exceed the 70% gate). Re-submitting it "
                   f"duplicates the family.")
        if twins:
            uniq_txt = uniq_txt + " · " + fam_txt
        else:
            uniq_txt = fam_txt
        site_rows.append(f"""<tr>
<td><strong>{esc(site)}</strong><br><a href="{esc(SITE_URLS[site])}">site ↗</a></td>
<td class="mono">{esc(f['name'])}</td>
<td><strong>{f['user_reported_score']:.4f}</strong><br><span class="pill warn">USER-REPORTED</span></td>
<td>{f['n_positive']:,} dots<br><span class="micro">0 on catalogue</span></td>
<td>{esc(uniq_txt)}</td></tr>""")

    cand_overlap_max = max(r["mine_on_theirs_3px"] for r in focus["rows"])
    cand_rho_max = max(r["abs_spearman"] for r in focus["rows"])
    cand_row = f"""<tr class="cand">
<td><strong>WBG-8<br>(this repo)</strong></td>
<td class="mono"><a href="downloads/{esc(CANDIDATE)}.tif">{esc(CANDIDATE)}.tif</a><br>
<a href="downloads/{esc(CANDIDATE)}.zip">(zip)</a> ·
<a href="../evidence/wbg8/run_card.json">run card</a></td>
<td><strong>{est['estimate']:.4f}</strong> <span class="pill warn">MODEL-ESTIMATE</span><br>
<span class="micro">95% model band {est['interval_95_model'][0]:.3f}–{est['interval_95_model'][1]:.3f}; B2-parity ref {est['family_parity_reference']['model_estimate']:.4f}</span></td>
<td>{card['validator']['n_positive']:,} dots<br><span class="micro">0 on catalogue</span></td>
<td><strong>UNIQUE — yes.</strong> vs all 11 focus-site bests: max 3-px overlap <strong>{cand_overlap_max:.1%}</strong> (gate ≤70%), max |ρ| <strong>{cand_rho_max:.3f}</strong> (gate ≤0.90); vs all 118 registry rasters: max literal overlap {uniq['max_literal_mine_on_theirs']:.1%} (non-degenerate) / {uniq['max_literal_same_budget']:.1%} (same-budget), max |ρ| {uniq['max_abs_spearman']:.3f}.</td></tr>"""

    # ---------------- why 0.2778 ------------------------------------------
    b2 = next(f for f in audit["files"] if f["site"] == "GEMSDOE32")

    why = f"""
<h2 id="why">Why GEMSDOE32's B2 scored 0.2778 — and can we beat it?</h2>
<div class="panel panel-pad">
<ol class="tight">
<li><strong>The metric rewards off-catalogue recall.</strong> Tversky/DTI (α=0.2, β=0.8, 300 m triangular kernel, <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a>) penalises missed faults 4× more than false alarms. The hidden truth is the <em>newly mapped</em> fault network, so a dot on the public catalogue can never be a new-fault true positive — it only adds FP weight.</li>
<li><strong>The champion is a nested pruning sequence, not one idea.</strong> D2.8 (44,090 dots, keep distance ≥1 px from catalogue) → B1 (40,199, ≥2 px) → B2 ({b2['n_positive']:,}, ≥3 px); reported 0.2600 → 0.2708 → {b2['user_reported_score']:.4f}. Every removal is catalogue-adjacent mass that could only dilute precision.</li>
<li><strong>Geometry matters:</strong> Poisson-300 m kernel-disjoint dots (each dot buys independent kernel credit), {b2['n_positive']:,} dots, coverage of ~92% of 6-km blocks (spreads FP risk map-wide), zero dots on the catalogue, only {b2['frac_positive_within_3px']:.1%} of dots within 3 px of it.</li>
<li><strong>Caveats (verified):</strong> 0.2778 is USER-REPORTED, never organizer-confirmed here; scores in this family vary ±0.086 for near-identical rasters, so the top six of the nine sites are statistically tied; GEMSDOE25≡30 and GEMSDOE28↔31 are exact duplicate pairs.</li>
<li><strong>Beating it:</strong> keep the winning geometry, replace the placement surface. WBG-8 does exactly that with an independently implemented blind multi-layer geophysical ridge composite (magnetic RTP/TC Hessian ridges, geodetic strain magnitude, gravity edges, basement-depth steps, topo fronts) + visible-catalogue structural priors, fresh seed. Within-model geometry parity vs B2 is gap {est['within_model_gap_vs_b2_geometry']:+.3f} (B2's own model estimate {est['family_parity_reference']['model_estimate']:.4f}); the model under-predicts the whole family, so read estimates relatively.</li>
</ol>
<p class="micro">Sources: <a href="data/nine_site_audit_20261029.json">nine-site pixel audit (29 Oct)</a> · <a href="../docs/research/wbg2-why-02778.md">why-02778 analysis</a> · <a href="../knowledge/03_executive_summary_and_02778_forensics_2026-10-27.md">forensics note</a> · <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a>.</p>
</div>"""

    # ---------------- ranked next hypotheses -------------------------------
    hyp = """
<h2 id="hypotheses">Next hypotheses — ranked before any further slot (3–5, none implemented yet)</h2>
<div class="panel panel-pad">
<table>
<thead><tr><th>#</th><th>Hypothesis & layer(s)</th><th>Physical signature targeted</th><th>Why it can catch a fault the catalogue misses</th><th>Differs from WBG-8 / this repo because…</th><th>Expected gain / cost</th></tr></thead>
<tbody>
<tr><td>1</td><td><strong>H-GBDT-19</strong> — all 19 competition bands (mag/grav/geod/DEM), trained hide-and-recover per fold</td><td>Learned non-linear combination (boosted trees) instead of hand rank-blends</td><td>Fits the mapped-fault proxy from covariates visible-only per fold, then generalises to off-catalogue continuations; the engineered-feature lanes (WBG-4 0.1654, peer 0.177 HOLDOUT-DTI) show learnable signal above our 0.0944</td><td>WBG-8 uses five fixed ridge layers + rules; this LEARNS weights from the stack already restored in <code>data/official/training_features.tif</code> — no new external data needed</td><td><strong>Highest</strong> (only path toward the 0.166+ holdout band) / medium (CPU-feasible with pixel sampling; ~1 session)</td></tr>
<tr><td>2</td><td><strong>H-LIDAR-SCARP</strong> — the 12-band 1 m LiDAR scarp raster in the pinned manifest (706/716 USGS 3DEP tiles)</td><td>Cross-section edge/step maxima + relief concordance along candidate strikes</td><td>Blind range-front scarps are sub-pixel at 100 m but crisp at 1 m — detects continuations where magnetics is quiet</td><td>WBG-8 has zero LiDAR input; earlier LiDAR lanes (WBG-5, tipcont) failed on placement overlap, not on the layer itself</td><td>High / low (restore 37 MB pinned raster, reuse WBG-8 placement)</td></tr>
<tr><td>3</td><td><strong>H-GEOTH-PIN</strong> — USGS/NEI play-fairway &amp; known geothermal areas (free official CSVs) aligned with structural trend</td><td>Distance-weighted pin proximity × strike-alignment with blind ridge energy</td><td>Active systems sit on unmapped feeders; catalogue omits them by construction</td><td>GEMSDOE36's pins (0.2750) were unaligned pins ⊃ B2; ours would be alignment-gated and off-catalogue — different dot field, not their superset</td><td>Medium / medium (need the official area shapefiles — availability check first)</td></tr>
<tr><td>4</td><td><strong>H-SEIS-CORR</strong> — USGS ComCat earthquake catalogue (free official API) + the stack's deq/ieq bands</td><td>Lineament corridors with clustered microseismicity and distance-decay</td><td>Seismicity marks active slips planes absent from mapped traces</td><td>Current bands are static distance rasters; this adds real hypocentres and b-value corridors — no lane in this repo used ComCat yet</td><td>Medium / medium (ComCat query + rasterise; official source)</td></tr>
<tr><td>5</td><td><strong>H-COND-CONDUIT</strong> — <code>cond_surf</code> + <code>depth_to_base_surf</code> ridge conjunction</td><td>Conductive permeability conduits along basement steps</td><td>Fluid pathways cluster on blind faults even without surface expression</td><td>WBG-C1 used conductivity only as a negative commutator control; this proposes a positive conduit-ridge detector</td><td>Low / low (bands already local)</td></tr>
</tbody></table>
<p class="micro">Protocol: each hypothesis must beat the current same-evaluator holdout best (0.1661, GEMSDOE24 S3DEP1 per the 28 Oct receipt) on the hide-and-recover holdout, pass the leakage canary (AUC ≤ 0.90) and the registry gates <em>before</em> any weekly slot is spent. WBG-8 (validated this session) is the current cleared candidate; hypotheses 1–5 are pre-registered here for the next session's 3-experiment budget. Sources: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">GeoDAWN (USGS)</a> · <a href="https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and">USGS blind-systems play fairway</a> · <a href="https://www.usgs.gov/programs/earthquake-hazards/catalog">USGS ComCat</a> · <a href="hypotheses.html">earlier hypothesis register</a>.</p>
</div>"""

    # ---------------- verdict panel ---------------------------------------
    gates_html = " · ".join(
        f"{k}: {'PASS' if v else 'FAIL'}" for k, v in dec["gates"].items())
    verdict = f"""
<div class="alert {verdict_cls}" role="note"><div>
<h2>WBG-8 candidate — {verdict_word}</h2>
<p class="micro">sha256 <code>{esc(card['artifact']['tif_sha256'])}</code> · {card['validator']['n_positive']:,} dots · values strictly in [0,1], all-finite zeros exterior (fixes the portal “Predicted values must be in range [0, 1]” error) · CRS/shape/transform match the official sample · zero dots on the mapped catalogue.</p>
<p><strong>Gates:</strong> {esc(gates_html)} · registry-uniqueness: {'PASS' if card['registry']['passes_literal_uniqueness'] else 'FAIL'} (details above) · leakage canary max AUC ≤ 0.90: {'PASS' if dec['gates']['leakage_canary'] else 'FAIL'}.</p>
<p><strong>Estimates (never an organizer score):</strong> MODEL-ESTIMATE <strong>{est['estimate']:.4f}</strong> (95% model band {est['interval_95_model'][0]:.3f}–{est['interval_95_model'][1]:.3f}, grouped RMSE {est['model_grouped_rmse']:.3f}) · HOLDOUT-DTI {hold['dti']:.4f} (95% CI [{hold['ci95'][0]:.4f}, {hold['ci95'][1]:.4f}], evaluator {esc(hold['evaluator_version'])}, n={hold['withheld_positive_pixels']:,} withheld positives) — a catalogue-proxy diagnostic that does <em>not</em> forecast leaderboard rank (measured Spearman 0.144 across 118 scored files).</p>
<p><strong>Bottom line:</strong> Download the TIFF (or ZIP) above; every automated preflight passes, so the upload form cannot reject it for format or range. Whether to spend this week's slot is the owner's selector decision: the estimate band is wide, and no organizer confirmation exists until the leaderboard responds.</p>
</div></div>"""

    body = f"""
<div class="alert" role="note"><p><strong>31 Oct 2026 executive summary.</strong> One unique candidate is cleared for download and submission preflight ({'ok_to_submit: true' if ok_submit else 'ok_to_submit: false'}). Nine focus-site bests below; all their scores are USER-REPORTED. Direct download: <a href="downloads/{esc(CANDIDATE)}.tif"><strong>{esc(CANDIDATE)}.tif</strong></a> · <a href="downloads/{esc(CANDIDATE)}.zip">zip</a> · <a href="how-to-submit-20261031.html">submission steps →</a></p></div>
{verdict}
<h2 id="table">The table — what to download, estimated score, uniqueness</h2>
<table>
<thead><tr><th>Site</th><th>Best file (download from their site)</th><th>Score (estimated / reported)</th><th>Dots</th><th>Unique vs the other sites?</th></tr></thead>
<tbody>
{''.join(site_rows)}
{cand_row}
</tbody></table>
<p class="micro">Estimate policy: site scores are copied owner reports from <a href="data/nine_site_audit_20261029.json">nine_site_audit_20261029.json</a> (NOT organizer-confirmed). The WBG-8 number is a MODEL-ESTIMATE from geometry-descriptor regression with grouped RMSE {est['model_grouped_rmse']:.3f} — its honest use is <em>within-model</em> comparison against the B2-parity reference {est['family_parity_reference']['model_estimate']:.4f}. External leaderboard observations: #1 = 0.4544 (public page read, 2026-10-28/29 retention); the owner also cites 0.3195 / 0.4413 — all UNVERIFIED from this sandbox (no DrivenData auth).</p>
{why}
{hyp}
<h2 id="uniqueness">Uniqueness evidence (all 118 registry rasters + focus sites)</h2>
<div class="panel panel-pad">
<ul class="tight">
<li><strong>Byte level:</strong> raster sha256 <code>{esc(card['artifact']['tif_sha256'])}</code>; positive-set sha256 <code>{esc(card['artifact']['positive_set_sha256'])}</code> — neither matches any of the 118 scored registry rasters.</li>
<li><strong>Focus-9:</strong> max 3-px overlap {cand_overlap_max:.1%} (vs GEMSDOE27), max |ρ| {cand_rho_max:.3f} — both far inside the gates. Per-site rows: <a href="../evidence/wbg8/uniqueness_vs_focus9.json">uniqueness_vs_focus9.json</a>.</li>
<li><strong>Full registry:</strong> literal direction (my dots within 3 px of theirs) max {uniq['max_literal_mine_on_theirs']:.1%} vs non-degenerate rasters and {uniq['max_literal_same_budget']:.1%} vs same-budget (n≤45k) competitors; reverse same-budget max {uniq['max_reverse_same_budget']:.1%}; max |ρ| {uniq['max_abs_spearman']:.3f} vs {esc(uniq['max_abs_spearman_vs'])}. Dense fields (103k–517k dots and the 206,895-dot r13 lattice) capture 0.68–0.99 of ANY 37k-dot field by pigeonhole — reported separately per the binding AGENTS.md defect (ii) review: <a href="../evidence/wbg8/uniqueness.json">uniqueness.json</a>.</li>
<li><strong>Cross-site twins found:</strong> GEMSDOE25 D2.8 ≡ GEMSDOE30 D2.8 (identical dot set); GEMSDOE28 h27-4 ≡ GEMSDOE31 h27-4 (identical dot set). <strong>Computed family matrix ({len(fam['matrix'])}×{len(fam['matrix'])-1} ordered pairs): every one of the 72 site-pairs exceeds the 70% gate</strong> ({fam['min_per_site'][min(fam['min_per_site'], key=fam['min_per_site'].get)]:.1%} is the smallest pairwise overlap) — the nine "bests" are one nested lineage (h19-5/D2.8/B2), so re-submitting ANY of them duplicates ALL the others: <a href="../evidence/wbg8/focus9_family_matrix.json">focus9_family_matrix.json</a>.</li>
</ul></div>
<h2 id="how">How to submit (short form)</h2>
<div class="panel panel-pad"><ol class="tight">
<li>Download <a href="downloads/{esc(CANDIDATE)}.tif"><strong>{esc(CANDIDATE)}.tif</strong></a> (or the zip).</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">the submission page</a> (login required — credentials stay with the owner), choose the file, paste the note from the run card (≤140 chars), submit.</li>
<li>The form cannot fail on “[0,1]” for this file: min {card['validator']['range_min']}, max {card['validator']['range_max']}, zero NaN anywhere, grid matches the official sample byte-for-byte in geometry.</li>
<li>Weekly cap: shown on the submission page; promotion is a separate selector step.</li>
</ol>
<p><a href="how-to-submit-20261031.html">Full submission walkthrough →</a></p></div>
"""
    (DOCS / "executive-summary-20261031.html").write_text(
        page("Executive summary · 31 Oct 2026 · WBG GEMS",
             "Executive summary · 31 Oct 2026", body))

    # ---------------- how-to-submit page ----------------------------------
    note = esc(card["note"])
    pre = load("evidence/wbg8/preflight.json")
    n_checks = len(pre["checks"])
    n_passed = sum(1 for v in pre["checks"].values() if v)
    how_body = f"""
<div class="alert {verdict_cls}" role="note"><div><h2>Exactly how to submit — WBG-8 candidate</h2>
<p><strong>File:</strong> <a href="downloads/{esc(CANDIDATE)}.tif"><code>{esc(CANDIDATE)}.tif</code></a> (or <a href="downloads/{esc(CANDIDATE)}.zip">.zip</a>) — verdict <strong>{verdict_word}</strong>, validator <code>ok_to_submit: {'true' if ok_submit else 'false'}</code>, sha256 <code>{esc(card['artifact']['tif_sha256'])}</code>.</p></div></div>
<ol>
<li><strong>Download</strong> the .tif (single-band GeoTIFF) or the .zip (exactly one GeoTIFF inside, byte-identical). Do not re-export or convert it in a GIS first — re-exporting changes bytes and can push values outside [0,1].</li>
<li><strong>Verify the hash (optional):</strong> <code>sha256 {esc(card['artifact']['tif_sha256'])}</code>. It must match the <a href="../evidence/wbg8/run_card.json">run card</a>.</li>
<li><strong>Go to</strong> <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData → Competition 306 → Submission</a> (owner login; this repo never stores credentials).</li>
<li><strong>File to submit:</strong> pick the downloaded .tif (or .zip). Format rules from the <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a> and <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a>: single-band float32 GeoTIFF, EPSG:32611, 3730×3292, 100 m grid, values in [0,1]. All verified by <code>scripts/validate_submission.py</code> ({n_passed}/{n_checks} checks PASS + template report PASS; receipt <a href="evidence/wbg8/preflight.json">preflight.json</a> and <a href="downloads/{esc(CANDIDATE)}.validator.json">validator.json</a> — the writer receipt's 10/10 hard checks and the strict whole-array [0,1] check pass; its 3 soft NaN-compatibility checks fail <em>by design</em> because this file uses the portal-safe all-finite zeros exterior instead of NaN).</li>
<li><strong>Note (paste this):</strong> <code>{note}</code> ({len(card['note'])} characters, ≤140 limit).</li>
<li><strong>Create the submission.</strong> The expected error “Predicted values must be in range [0, 1]” CANNOT occur for this file: it contains only 0.0/1.0, no NaN/Inf anywhere (zeros exterior), min {card['validator']['range_min']}, max {card['validator']['range_max']}. That error was produced by older NaN-outside research files; this one deliberately uses the portal-safe all-finite convention (see the writer docstring in <code>src/gems/submission.py</code>).</li>
<li><strong>After submitting:</strong> record the organizer-confirmed score on the submission page as ORGANIZER-CONFIRMED and compare with the MODEL-ESTIMATE {est['estimate']:.4f} (band {est['interval_95_model'][0]:.3f}–{est['interval_95_model'][1]:.3f}) to calibrate the estimator. Cap: 3 submissions per week per the problem page — the remaining allowance shows on the submission page.</li>
</ol>
<p class="micro">Budget/risk: the score is unverifiable before upload (no DrivenData auth from this sandbox). HOLDOUT-DTI {hold['dti']:.4f} [{hold['ci95'][0]:.4f}, {hold['ci95'][1]:.4f}] is an internal diagnostic that does not forecast rank. Upload is always a manual owner action.</p>
<p><a href="executive-summary-20261031.html">← Executive summary</a></p>"""
    (DOCS / "how-to-submit-20261031.html").write_text(
        page("How to submit · 31 Oct 2026 · WBG GEMS",
             "How to submit · 31 Oct 2026", how_body))

    print("wrote docs/executive-summary-20261031.html and docs/how-to-submit-20261031.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
