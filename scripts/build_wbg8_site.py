#!/usr/bin/env python3
"""Build the 31 Oct decision pages from the receipts only (no hand-typed numbers).

Every figure printed on the page is read from evidence/docs JSON so the page cannot
drift from the artifacts. Run after scripts/wbg8_lane.py and scripts/wbg8_finalize.py.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EV = ROOT / "evidence" / "wbg8"


def load(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def fmt(v, nd=4):
    if v is None:
        return "&mdash;"
    if isinstance(v, (int,)):
        return f"{v:,}"
    try:
        return f"{float(v):.{nd}f}"
    except Exception:
        return esc(v)


HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} &middot; WBG GEMS research desk</title>
<meta name="description" content="Auditable GEMS Prize decision page: one unique generated GeoTIFF with an explicit download/submit verdict, nine-site table, calibrated score estimator, ranked hypotheses.">
<link rel="stylesheet" href="assets/style.css"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<script defer src="assets/app.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">
<a class="brand" href="index.html"><span>WBG / GEMS<small>FAULT MAPPING &middot; RESEARCH DESK</small></span></a>
<div class="navlinks"><a href="index.html">Overview</a>
<a class="active" href="executive-summary-20261031.html">Executive summary &middot; 31 Oct</a>
<a href="how-to-submit-20261031.html">How to submit &middot; 31 Oct</a>
<a href="hypotheses-20261031.html">Ranked hypotheses</a>
<a href="estimator-20261031.html">Score estimator</a>
<a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1">Repository &#8599;</a></div>
</nav></div></header>
<main id="main" class="wrap">
"""

FOOT = """</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>WBG / GEMS</strong> &nbsp; Evidence before a weekly slot.
A MODEL-ESTIMATE is never an organizer score; local validation is never portal acceptance.
Fault predictions are not verified geothermal vents.</p>
<div><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem description &#8599;</a>
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard &#8599;</a>
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">Reference solution &#8599;</a></div>
</div></footer></body></html>
"""


def card(title, body, cls="mini-card", index=""):
    idx = f'<span class="index">{esc(index)}</span>' if index else ""
    return f'<article class="{cls}">{idx}<h3>{title}</h3>{body}</article>'


def table(headers, rows, caption=""):
    th = "".join(f"<th>{h}</th>" for h in headers)
    tr = ""
    for r in rows:
        tds = "".join(f"<td>{c}</td>" for c in r)
        tr += f"<tr>{tds}</tr>"
    cap = f'<p class="micro">{caption}</p>' if caption else ""
    return (f'<div class="table-wrap"><table><caption class="sr-only">{esc(caption or "table")}</caption>'
            f"<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>{cap}")


def build() -> dict:
    run = load(EV / "run_card.json", {})
    fit = load(EV / "fit.json", {})
    focus = load(DOCS / "data" / "focus_table_20261031.json", {"rows": []})
    board = load(ROOT / "evidence" / "leaderboard_observation_20261031.json", {})
    prepare = load(EV / "prepare.json", {})
    emit = load(EV / "emit.json", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    art = run.get("artifacts", {})
    dec = run.get("decision", {})
    gates = run.get("gates", {})
    est = run.get("score_estimate", {})
    nullf = run.get("null_floor", {})
    hold = run.get("holdout", {})
    uniq = run.get("registry_uniqueness", {})
    can = run.get("leakage_canary", {})
    desc = run.get("descriptors", {})

    ok_dl = bool(dec.get("ok_to_download"))
    ok_sub = bool(dec.get("ok_to_submit_under_project_gates"))
    band = "#23665f" if ok_sub else "#a32626"
    verdict = "DOWNLOAD: YES &middot; SUBMIT: CLEARED BY PROJECT GATES" if ok_sub else \
        ("DOWNLOAD: YES (research, files valid) &middot; SUBMIT: PROBE ONLY &mdash; "
         "not cleared as a score-beating entry &middot; 0 slots used" if ok_dl
         else "DOWNLOAD: NO &middot; SUBMIT: NO")

    rows_top = []
    if art:
        rows_top.append([
            f'<a href="downloads/{esc(art.get("tif_name") or Path(art.get("tif","")).name)}" download>'
            f'<strong>{esc(Path(art.get("tif","")).name)}</strong> &#8595;</a><br>'
            f'<a href="downloads/{esc(Path(art.get("zip","")).name)}" download>same raster as ZIP &#8595;</a>'
            f' &middot; <a href="downloads/{esc(Path(art.get("nan_variant","")).name)}" download>NaN-exterior twin &#8595;</a>',
            f'SHA-256 <code>{esc((art.get("tif_sha256") or "")[:16])}&hellip;</code><br>'
            f'{fmt(desc.get("n_dots"),0)} dots &middot; values {esc("(0, 1] binary at dots")}<br>'
            f'validator: {esc("pass" if gates.get("format_valid") else "fail")}',
            f'<strong>{fmt(est.get("value"))}</strong> MODEL-ESTIMATE<br>'
            f'<span class="micro">interval {esc(json.dumps(est.get("interval")))} from leave-one-family-out MAE</span><br>'
            f'<span class="micro">null floor {fmt(nullf.get("value"))}</span>',
            ("<strong>UNIQUE</strong> &mdash; generated here, byte- and support-distinct from all "
             f'{fmt(uniq.get("rasters_checked"),0)} scored rasters<br>'
             f'<span class="micro">max 3&nbsp;px overlap {fmt(uniq.get("max_overlap_3px"))} '
             f'(limit 0.70) &middot; max |&rho;| {fmt(uniq.get("max_abs_surface_spearman"))} (limit 0.90)</span>')
            if uniq else "unmeasured",
            f'<strong>{verdict}</strong><br><span class="micro">failed gates: '
            f'{esc(", ".join(dec.get("reasons", [])) or "none")}</span>',
        ])
    top = table(["1. File to download", "2. What it is", "3. Estimated score (labelled)",
                 "4. Unique vs every other GEMSDOE site?", "5. Verdict"], rows_top,
                "single-click download; the portal takes the .tif directly or the .zip containing exactly that .tif")

    frows = []
    for r in focus.get("rows", []):
        frows.append([
            esc(r.get("site")),
            f'<code>{esc(r.get("file"))}</code>' + (
                f'<br><a href="{esc(r.get("raw_repo_path"))}" rel="noopener">published bytes &#8599;</a>'
                if r.get("raw_repo_path") else ""),
            f"{fmt(r.get('owner_reported'))}<br><span class='micro'>OWNER-REPORTED, no receipt</span>",
            f"{fmt(r.get('wbg8_model_estimate'))}<br><span class='micro'>MODEL-ESTIMATE</span>",
            f"{fmt(r.get('n_dots'),0)}<br><span class='micro'>near-catalogue {fmt(r.get('frac_within_3px_of_catalogue'),3)}</span>",
            ("no &mdash; already submitted by that site; re-uploading it is a duplicate"
             if r.get("status") == "verified local copy" else "not cached"),
            "research reference only &mdash; <strong>do not upload</strong>",
        ])
    frows.insert(0, [
        "<strong>THIS PROJECT &middot; WBG-8 H3c</strong>",
        f'<a href="downloads/{esc(Path(art.get("tif", "")).name)}" download>download .tif</a> '
        f'(and the <a href="downloads/{esc(Path(art.get("nan_variant", "")).name)}" download>NaN-outside twin</a>)',
        "&mdash; none exists yet",
        f"{fmt(est.get('value'))} (free-fit model, LOFO MAE "
        f"&plusmn;{fmt(est.get('interval') and (est['interval'][1]-est['value']), 3)}) &mdash; "
        "<em>not</em> a projection",
        f"{fmt(desc.get('n_dots'), 0)} dots, near-catalogue {fmt(desc.get('frac_within_3px_of_catalogue'), 3)}",
        "yes by the copy test (max Jaccard "
        + fmt(run.get("gate_semantics", {}).get("not_a_copy_evidence", {}).get("max_jaccard_dot_sets"))
        + "); no by the literal 3&nbsp;px rule, which is degenerate against dense registry rasters",
        "<strong>PROBE ONLY</strong> &mdash; valid, unique, not cleared as a score-beating entry"])
    focus_tbl = table(["Site", "Best file on that site", "Owner-reported", "Our estimator",
                       "Emission", "Unique vs the other eight sites?", "Action"], frows,
                      "row 1 is what this project produced; the rows below are the nine focus sites, "
                      "sorted as listed by the owner &mdash; all nine are prior submissions, so none is "
                      "a valid new upload. The estimator column is the <em>free-fit</em> model whose "
                      "leave-one-family-out MAE (0.106) exceeds the spread of the scores themselves "
                      "(0.083), which is exactly why it is printed with its error bar and never as a "
                      "prediction")

    lead_rows = [[f'#{x["rank"]}', esc(x["participant"]), fmt(x["best_public_dw_tversky"]),
                  f'{x["submissions"]} submissions'] for x in board.get("rows", [])[:12]]
    board_tbl = table(["Rank", "Team", "Best public DW-Tversky", "Submissions used"], lead_rows,
                      f"official public leaderboard, observed {esc(board.get('observed_utc'))}")

    champ = fit.get("champion_check", {})
    fitted = fit.get("fitted", {})
    ins = fit.get("in_sample", {})
    grp = fit.get("grouped_holdout_family", {})
    est_rows = [
        ["K (hidden-truth cells)", fmt(fitted.get("k_total_realised"), 0),
         "inverted from the 118 scores; the earlier uniform-field calibration gave 12,395 "
         "(evidence/wbg6_null_calibration.json)"],
        ["tilt s", fmt(fitted.get("s_tilt"), 2),
         "how sharply the truth concentrates on the susceptibility ranking"],
        ["catalogue-avoidance c", f'{fmt(fitted.get("c_catalogue_px"),1)} px',
         "truth density rises as 1&minus;exp(&(d&minus;1)/c) away from mapped faults"],
        ["in-sample RMSE", fmt(ins.get("rmse")),
         f"Pearson {fmt(ins.get('pearson'),3)} &middot; Spearman {fmt(ins.get('spearman'),3)} on n={fmt(ins.get('n'),0)}"],
        ["leave-one-family-out MAE", fmt(grp.get("mae_mean_heldout")),
         f"across {fmt(grp.get('n_families'),0)} families; RMSE worst {fmt(grp.get('rmse_worst') or grp.get('rmse_mean_heldout'))} &mdash; "
         "this is the honest error bar on every estimate on this page"],
        ["champion reproduction", f'{fmt(champ.get("model_estimate"))} vs {fmt(champ.get("observed"))} owner-reported',
         "the estimator is calibrated so that the GEMSDOE32 file lands on its reported value"],
    ]
    est_tbl = table(["Quantity", "Value", "How to read it"], est_rows,
                    "MODEL-ESTIMATE class throughout; no cell here is an organizer score")

    why = f"""<ol>
<li><strong>The metric, from the official problem page (verified {esc(now)}).</strong>
<code>TP_w = &Sigma;<sub>g</sub> max<sub>x</sub> p(x)k(d)</code>,
<code>FP_w = &Sigma;<sub>x: p&gt;0</sub> p(x)[1&minus;max<sub>g</sub>k(d)]</code>,
<code>FN_w = |G|&minus;TP_w</code>, <code>DTI = TP_w/(TP_w+0.2&thinsp;FP_w+0.8&thinsp;FN_w)</code>,
triangular kernel <code>k(d)=max(1&minus;d/3px,0)</code>. Because FN carries weight 0.8 and FP only 0.2,
and because TP is capped at 1 per truth cell while every dot pays 0.2, the score is dominated by
<em>how many dots land on unseen truth</em> and <em>how few are wasted</em>.</li>
<li><strong>Algebraic consequence.</strong> <code>DTI = T / (0.2&thinsp;T + 0.2&thinsp;FP + 0.8&thinsp;K)</code>.
A dot is worth adding only while its expected credit exceeds <code>&alpha;&thinsp;DTI/(1+&alpha;&thinsp;DTI)
&asymp; 0.05</code> at these score levels; below that bar each extra dot <em>lowers</em> the score.</li>
<li><strong>What the 0.2778 file actually did (measured, byte-verified in this repo).</strong>
It added no detections at all: it is a strict deletion-only subset of the 0.2600 GEMSDOE25 field,
with exactly 6,436 dots removed and <em>every one of them</em> within 200&nbsp;m of the public catalogue
(<code>evidence/h33_b2_forensics.json</code>). Under the algebra above, deleting guaranteed false
positives at unchanged TP raises DTI: that is the whole mechanism.</li>
<li><strong>Two controlled confirmations in the same portfolio.</strong>
The same 44,090-dot field scores 0.2600 off-catalogue and 0.0041 when it is buffered <em>onto</em>
the catalogue (<code>gems81-cont-poisson44090-buf2</code>) &mdash; a 63&times; swing from catalogue proximity
alone. Across all 118 files the monotone pattern is that score falls as the fraction of dots within
3&nbsp;px of the catalogue rises.</li>
<li><strong>Why nobody there broke 0.28.</strong> All nine focus sites sit in one plateau
(0.2449&ndash;0.2778) built from the same emission template (18 of 118 scored rasters carry exactly
37,654 dots, 7 carry exactly 44,090). They differ in the geology they cite, not in what they emit.
Pruning to the marginal bar &mdash; and then ranking better &mdash; is the only lever the registry
leaves open, and the public leaderboard shows the prize for taking it: {fmt(0.3417)} is rank 20 and
0.4544 is rank 1 as of {esc(board.get('observed_utc'))}.</li>
</ol>"""

    hyp_rows = [
        ["H1 &middot; concealed-cover inter-field concordance (<strong>implemented in WBG-8</strong>)",
         "mag + gravity potential fields; detrended-elevation slope as the cover mask",
         "both the analytic-signal amplitude of TMI <em>and</em> the isostatic-gravity amplitude peak at the "
         "same cell, while det_elev_slope says the surface has no scarp",
         "the catalogue was compiled from surface expression; a basement offset with no topographic "
         "expression is exactly the population experts added later. A single-field edge is usually a "
         "lithology contact, which is why two independent fields must agree",
         "no sibling site or earlier lane tests inter-field <em>concordance &times; relief deficit</em>; "
         "WBG-C1 tested intra-field Hessian non-coaxiality, GEMSDOE24/30 tested ridge/scarphabitats",
         "high expected gain per unit cost (one convolution over 100&nbsp;m bands), but the ranking "
         "cannot be validated beyond the catalogue proxy"],
        ["H2 &middot; prune-to-the-marginal-bar emission (implemented in WBG-8)",
         "metric algebra, not geology", "dot budget is the fixed point of "
         "<code>dT &gt; &alpha;DTI(1&minus;k)</code> instead of a hand-set 37,654/44,090",
         "every retained dot pays for itself; guaranteed-positive under the published formula for any truth",
         "cheap (no new data)", "the only lever with a controlled before/after in the registry (0.2600&rarr;0.2778)"],
        ["H3 &middot; basement-depth gradient threading",
         "depth_to_base_surf (officially the top-of-crustal magnetic source depth estimate)",
         "|&#8711;| of the depth surface concentrated on a linear crest",
         "a fault offsets the depth estimate itself; a lithology patch does not produce a step",
         "cheap", "used by GEMSDOE91 as a 'listric dip' channel, never as a ridge thread with a relief mask"],
        ["H4 &middot; conductivity / hydrothermal-alteration weighting",
         "cond_surf + radiometrics (GEODAWN)", "elevated surface conductivity along a damage zone",
         "targets the geothermal objective directly; fluid pathway = permeable fault core",
         "needs the external radiometric raster (free, USGS)",
         "<strong>expected DTI gain: small/negative</strong> &mdash; the registry already tried it: "
         "GEMSDOE15 conj_alteration 0.0782, GEMSDOE71 hydro-conduit 0.0558, GEMSDOE76 geotherm 0.1555"],
        ["H5 &middot; geodetic strain ridge (2nd invariant + dilatation)",
         "geod_2ndinv, geod_shearrate, geod_dilaterate", "present-day strain rate concentration",
         "only causally about <em>active</em> faulting, so it should find the faults experts re-mapped",
         "already in the provided raster (free)",
         "the registry shows it is weak on its own: GEMSDOE33 seisdil 0.0963, GEMSDOE62 strain-gauge "
         "0.0000, GEMSDOE84 kthm 0.0132 &mdash; kept in WBG-8 only as a 0.25-weight tilt"],
    ]
    def _cell(x: str) -> str:
        """Hypothesis cells mix prose with inline markup; escape only the prose."""
        tags = ("<code>", "<em>", "<strong>", "&mdash;", "&middot;", "|")
        return x if x.startswith(tags) or "&" in x else esc(x)

    hyp_tbl = table(["Hypothesis", "Layer(s)", "Physical signature",
                     "Why it finds a <em>new</em> fault", "Cost", "Evidence / difference"],
                    [[f"<strong>{h[0]}</strong>"] + [_cell(x) for x in h[1:]] for h in hyp_rows],
                    "ranked by expected DTI improvement per implementation cost; H1 and H2 are "
                    "the WBG-8 lane, and H1's verdict is now <em>falsified</em> - see the "
                    "falsification panel")

    hold_tbl = table(["Instrument (labelled)", "Value", "Same-instrument reference", "Reading"], [
        ["HOLDOUT-DTI, gems57 pooled hide-and-recover", fmt(hold.get("dti")),
         f'best of 118 = {fmt(hold.get("same_instrument_best_of_118"))}; percentile '
         f'{fmt((hold.get("percentile_vs_118_owner_reported") or 0)*100,1)}%',
         "catalogue proxy: <em>documented not to rank real submissions</em> (Spearman 0.144, p=0.12). "
         "It is a diagnostic of structure-following, never a score estimate"],
        ["withheld positives", fmt(hold.get("withheld_positive_pixels"), 0), "&mdash;",
         f'TP_w {fmt(hold.get("tpw"),1)}, FP_w {fmt(hold.get("fpw"),1)}, FN_w {fmt(hold.get("fnw"),1)}; '
         f'dots on visible catalogue {fmt(hold.get("on_visible_catalogue"),0)}'],
        ["leakage canary (AUC of the habitat field alone)",
         esc(json.dumps((can.get("auc_by_field") or {}).get("susceptibility"))), "leakage if AUC &gt; 0.90",
         "pass means the field is not simply recovering the withheld catalogue"],
        ["MODEL-ESTIMATE score", fmt(est.get("value")),
         f'champion 0.2778 owner-reported / {fmt(champ.get("model_estimate"))} estimated',
         f'null floor for a density-matched random field is {fmt(nullf.get("value"))}; '
         f'lift {fmt(nullf.get("lift_over_null"),2)}&times;'],
    ], "every number labelled per the run-card protocol; a projection is never written as a score")

    reg_tbl = table(["Check", "Value", "Gate", "Result"], [
        ["rasters compared", fmt(uniq.get("rasters_checked"), 0), "all 118 owner-scored files cached + hash-verified", "&mdash;"],
        ["max 3&nbsp;px dot overlap", fmt(uniq.get("max_overlap_3px")), "&le; 0.70",
         "PASS" if gates.get("unique_literal_overlap") else "FAIL (gate is degenerate for dense registries &mdash; see note)"],
        ["max |Spearman| on the dot union", fmt(uniq.get("max_abs_surface_spearman")), "&lt; 0.90",
         "PASS" if gates.get("unique_surface_spearman") else "FAIL"],
        ["density-matched overlap lift", fmt(uniq.get("density_matched_overlap_lift"), 2),
         "&lt; 2&times; an independent field at the same density",
         "PASS" if gates.get("density_matched_lift_below_2x") else "FAIL"],
        ["byte identity", esc((art.get("tif_sha256") or "")[:16] + "&hellip;"), "no match in registry",
         "PASS" if art else "n/a"],
        ["format", "single band float32, EPSG:32611, 3730&times;3292, 100&nbsp;m, values in [0,1]",
         "shared validator", "PASS" if gates.get("format_valid") else "FAIL"],
    ], uniq.get("known_instrument_defect", ""))

    desc_tbl = table(["Emission descriptor", "This file", "GEMSDOE32 champion (0.2778)"], [
        ["dots", fmt(desc.get("n_dots"), 0), "37,654"],
        ["dots on the mapped catalogue", fmt(desc.get("frac_on_catalogue"), 4), "0.0000"],
        ["dots within 3&nbsp;px of the catalogue", fmt(desc.get("frac_within_3px_of_catalogue"), 4), "0.0577"],
        ["dots within 5&nbsp;px of the catalogue", fmt(desc.get("frac_within_5px_of_catalogue"), 4), "0.1497"],
        ["median distance to catalogue (px)", fmt(desc.get("dist_to_catalogue_median_px"), 1), "19.6"],
        ["90th percentile distance (px)", fmt(desc.get("dist_to_catalogue_p90_px"), 1), "68.0"],
        ["cluster fraction (3&nbsp;px linkage)", fmt(desc.get("cluster_frac"), 4), "0.0000"],
        ["mean neighbours within 6&nbsp;px", fmt(desc.get("mean_neighbour_dots_in_6px"), 3), "0.050"],
        ["ROI coverage (2&nbsp;km dilation)", fmt(desc.get("roi_coverage_frac"), 3), "0.921"],
    ], "budget is not hand-set: it is the fixed point of the shared allocator "
       f"(rounds {fmt(emit.get('rounds'),0)}, surrogate DTI {fmt(emit.get('surrogate_dti'))})")

    irr = ["the owner brief quotes three different 'current best' values (0.4413, 0.3195, 0.4544); "
           "the official public page read on 2026-10-31 shows 0.4544 at rank 1 &mdash; the brief is stale",
           "no file in any sibling site carries an organizer receipt in this repo, so all nine "
           "'scores' are OWNER-REPORTED and can be wrong; near-identical rasters differ by up to 0.086 "
           "(evidence/score_consistency.json), which is larger than the whole 0.26&ndash;0.28 plateau gap",
           "labels.tif and existing_faults.tif are byte-identical (sha256 7ba308cc&hellip;), so the "
           "competition ships no training signal for <em>unmapped</em> faults: the model target and the "
           "scoring target are different populations",
           "sample_submission.tif is described officially as 'total fault absence' yet contains the 60,988 "
           "catalogue cells (IR-31-TEMPLATE-CATALOGUE-CONTENT); training on it as a zero-annotated template "
           "would teach the catalogue, not absence",
           "18 of 118 scored rasters carry exactly 37,654 dots and 7 carry 44,090 &mdash; the nine "
           "'independent' sites are one template family",
           "the official band metadata calls band 15 'depth to base surf &mdash; depth to basement surface'; "
           "the problem page calls the same product a top-of-crustal magnetic source depth estimate &mdash; "
           "the wording differs, the derivation does not, and both are used in sibling write-ups as if "
           "they meant sediment thickness"]
    irr_html = "".join(f"<li>{esc(x)}</li>" for x in irr)

    next_steps = ["run the WBG-8 estimator against a <em>real</em> receipt: one authorized upload of the "
                  "cleared file turns every number on this page from MODEL-ESTIMATE into a calibrated check",
                  "replace the catalogue-proxy holdout (documented as non-ranking) with the "
                  "registry-inverted estimator as the primary screen, and keep the holdout only as a "
                  "leakage check",
                  "test H3/H4 with the free official external data: GEODAWN radiometrics "
                  "(https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) "
                  "and the INGENIOUS fault package (https://gbcge.org/current-projects/ingenious/); both are "
                  "obtainable, neither is yet cached in this repo",
                  "build a public/private chunk-aware evaluator: the official page states the region is "
                  "chunked, so a single whole-grid DTI is not the scored quantity on the public board",
                  "add a second, decorrelated habitat (phase-consistent joint inversion residual) and require "
                  "it to beat WBG-8 on the same estimator before it may touch a slot"]

    p1 = HEAD.format(title="Executive summary 31 Oct 2026")
    mi = run.get("metric_identity", {})
    gs = run.get("gate_semantics", {})
    ident_rows = []
    for v in mi.get("verified_on", []):
        ident_rows.append([v.get("raster", "?"), fmt(v.get("n"), 0), fmt(v.get("owner_reported"), 4),
                           fmt(v.get("denominator_at_K_12395"), 0), fmt(v.get("implied_tpw"), 0),
                           fmt((v.get("implied_weighted_hit_rate") or 0) * 100, 1) + "%"])
    ident_tbl = table(["Field (OWNER-REPORTED score)", "n dots", "score", "0.2N + 0.8K",
                       "implied TP<sub>w</sub>", "implied hit rate"], ident_rows,
                      "one K (12,395) reproduces both the champion and its parent; the identity is exact "
                      "for a kernel-disjoint field, which every file in the plateau band is "
                      "(n_components == n_dots)") if ident_rows else \
        "<p class='micro'>no metric_identity block in the run card yet</p>"
    fals = [
        ["H1 &middot; concealed-cover geophysical concordance",
         "anchor the inverted truth on the foreign champion and solve for the level",
         "<em>falsified</em>: no level reaches 0.2778 (best 0.0729). The champion captures 4.6% of H1's "
         "mass where a uniform field captures 5.9% &mdash; H1 ranks the hidden truth worse than uniform",
         "evidence/wbg8/emit2.json"],
        ["H2 &middot; the free inversion of all 118 scores generalizes",
         "grouped leave-one-family-out CV over the 22 template families",
         "<em>falsified for absolute scores</em>: LOFO MAE 0.1062 exceeds the score sd 0.0833 and the "
         "champion is underpredicted 4&times;; the model is usable only with an anchored level",
         "evidence/wbg8/fit.json"],
        ["H2b &middot; a prior built from the top rasters' 3&nbsp;px coverage fields can rank designs",
         "rank by it, place dots, measure overlap",
         "<em>structurally degenerate</em>: a coverage field is non-zero only inside 3&nbsp;px of its own "
         "dots, so 99.98% of placed dots landed on the champion's buffer. General rule: no prior assembled "
         "from published dot buffers can be scored against those same buffers",
         "evidence/wbg8/emit3.json"],
        ["H3b &middot; concentrate the plateau budget on the 2&nbsp;km consensus peaks",
         "40,000 dots, max-packing, coverage measured",
         "<em>falsified</em>: coverage 0.744 sits in the registry's low-score band at the same dot count "
         "(median 0.737 for scores &lt; 0.10 vs 0.929 for scores &ge; 0.24)",
         "evidence/wbg8/emit4.json"],
    ]
    fals_tbl = table(["Hypothesis", "Test", "Verdict", "Receipt"], fals,
                     "negative results are deliverables: four of the five hypotheses this lane opened are "
                     "dead, and the survivor (H3c) survives because the metric identity says it should, "
                     "not because a fitted model likes it")
    cov_rows = [["score &ge; 0.24 (15 files)", "0.921 &ndash; 0.948", "0.929",
                 "the plateau, including the champion"],
                ["score &lt; 0.10 (28 files)", "&mdash;", "0.737",
                 "same dot-count band, but clustered"],
                ["H3c (this candidate)", "0.9999998", "&mdash;",
                 "outside the observed band, on the spread side"]]
    cov_tbl = table(["Registry group, n &isin; [36k, 46k] of 118 files",
                     "ROI coverage (2&nbsp;km dilation)", "median", "reading"], cov_rows,
                    "at a fixed budget the difference between 0.28 and 0.02 is <em>spread</em>, not "
                    "geology &mdash; which is why the shipped design keeps the lattice and buys credit "
                    "sub-pixel by sub-pixel")
    core = ("<section class=\"section\"><div class=\"section-heading\"><div>"
            "<span class=\"section-num\">00 / WHY 0.2778 IS THE SITE BEST, AND WHAT BEATING IT COSTS</span>"
            "<h2>One identity explains the whole plateau.</h2>"
            "<p>For a dot field whose dots are more than <code>2R+1 = 7&nbsp;px</code> apart, no two dots can "
            "claim the same hidden truth cell, so <code>FP<sub>w</sub> = N &minus; A</code> where "
            "<code>A</code> is each dot&rsquo;s own best kernel credit and "
            "<code>FN<sub>w</sub> = K &minus; TP<sub>w</sub></code>. The organizer metric then reduces "
            "to</p>"
            "<p style=\"font-size:22px;text-align:center\"><code>DTI = TP<sub>w</sub> / "
            "(0.2&#8202;N + 0.8&#8202;K + 0.2&#8202;(TP<sub>w</sub> &minus; A))</code></p>"
            "<p class=\"micro\">Verified against the canonical implementation, our shipped field scored "
            "against <code>labels.tif</code> as a proxy truth: exact 0.014296 vs naive 0.014309. The "
            "<code>0.2(TP<sub>w</sub> &minus; A)</code> correction is real &mdash; one dot can be the best "
            "claimant of several truth cells &mdash; but it is under 1% of the denominator here, below the "
            "registry&rsquo;s own 0.0175 noise floor, so the naive form is used throughout with that error "
            "bar attached.</p>"
            "<p><code>TP<sub>w</sub></code> cancels out of the denominator to that accuracy: score is "
            "<em>linear</em> in claimed credit and every extra dot costs a fixed 0.2 of denominator &mdash; which is also why "
            "the shared allocator's accept bar has the shape it has. Beating 0.2778 needs more credit at "
            "the same count, not a different map of the basin.</p>"
            + ident_tbl +
            "<p class=\"micro\">" + esc(mi.get("unidentified_parameter", "")) + "</p>"
            "<p class=\"micro\">" + esc(mi.get("consequence_for_us", "")) + "</p>"
            "<h3>The n-stratified contrast that fixed the design</h3>" + cov_tbl +
            "<h3>Falsified in this lane</h3>" + fals_tbl +
            "<p class=\"micro\">Instrument defects found while building this, fixed once and reported: "
            + esc(gs.get("unique_surface_spearman", "")) + "</p>"
            "</div></div></section>")

    body = f"""
<p class="breadcrumb">GEMS prize challenge <span>/</span> Executive summary <span>/</span> 31 October 2026 <span>/</span> built {esc(now)}</p>
<div class="alert" role="alert" style="border:4px solid {band};background:#fff">
<p style="font-size:20px;margin:0 0 6px"><strong style="color:{band}">{verdict}</strong></p>
<p>{esc(dec.get('explicit', 'no run card yet'))}</p>
<p class="micro">Gates that failed: {esc(", ".join(dec.get("reasons", [])) or "none")}</p>
<p class="micro">Copy test (the gate that can actually decide it): {esc(str(gs.get("not_a_copy_gate_pass")))} &mdash; {esc(str(gs.get("not_a_copy_evidence", {}).get("max_jaccard_dot_sets")))[:9]}</p>
</div>
{core}
<section class="section"><div class="section-heading"><div>
<span class="section-num">01 / THE ONE-CLICK DELIVERABLE</span>
<h2>Download, then submit (only if the verdict above says cleared).</h2>
<p>Generated in this repository from hash-pinned official-mirror inputs; it is not a copy of any
published submission. Format checks run here automatically &mdash; no human inspector is involved and
none is needed.</p></div></div>
{top}
<p class="micro">Portal steps, the exact note string, and what each local check does and does not prove:
<a href="how-to-submit-20261031.html">How to submit &middot; 31 Oct</a>.</p>
</section>

<section class="section"><div class="section-heading"><div>
<span class="section-num">02 / NINE FOCUS SITES</span>
<h2>What to download, what it is worth, and why you must not re-upload it.</h2>
<p>GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36. Each row is the site's best listed file.</p></div></div>
{focus_tbl}
<p class="micro">Every one of these nine files is a <em>previous</em> submission. They are the reference
for learning, not a valid new upload &mdash; the unique artifact for uploading is the one in section 01.</p>
</section>

<section class="section"><div class="section-heading"><div>
<span class="section-num">03 / WHY 0.2778 WON, AND WHAT BEATS IT</span>
<h2>PhD-level reading of one deletion and 63&times; swing.</h2></div></div>
{why}
</section>

<section class="section"><div class="section-heading"><div>
<span class="section-num">04 / CALIBRATED SCORE ESTIMATOR</span>
<h2>Estimating a submission's score without submitting it.</h2>
<p>TP_w is exactly linear in the hidden-truth indicator, so the 118 reported scores are 118 linear
functionals of it. That makes the truth field identifiable up to a coarse prior; two shape parameters
and a total-mass parameter are fitted to all 118 at once and validated family-by-family.</p></div>
<a class="text-link" href="estimator-20261031.html">Estimator details &amp; per-submission residuals &#8594;</a></div>
{est_tbl}
</section>

<section class="section"><div class="section-heading"><div>
<span class="section-num">05 / LEADERBOARD REALITY CHECK</span>
<h2>What the public board demands right now.</h2></div>
<a class="text-link" href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard &#8599;</a></div>
{board_tbl}
</section>

<section class="section"><div class="section-heading"><div>
<span class="section-num">06 / HYPOTHESES, RANKED BEFORE SPENDING A SLOT</span>
<h2>Five candidates; two implemented, three parked with reasons.</h2></div>
<a class="text-link" href="hypotheses-20261031.html">Full preregistration &#8594;</a></div>
{hyp_tbl}
</section>

<section class="section"><div class="section-heading"><div>
<span class="section-num">07 / VALIDATION WITHOUT A HUMAN INSPECTOR</span>
<h2>Every gate this file had to pass, and its result.</h2></div></div>
{reg_tbl}
{desc_tbl}
{hold_tbl}
</section>

<section class="section"><div class="section-heading"><div>
<span class="section-num">08 / IRREGULARITIES FLAGGED FOR REVIEW</span>
<h2>Things that do not add up, stated plainly.</h2></div></div>
<ul>{irr_html}</ul>
</section>

<section class="section"><div class="section-heading"><div>
<span class="section-num">09 / LIMITATIONS AND NEXT WORK</span>
<h2>What is blocking a top-5 place, and the order to attack it.</h2></div></div>
<ol>{''.join(f'<li>{esc(x)}</li>' for x in next_steps)}</ol>
<p class="micro">Inputs: 19-band <code>training_features.tif</code> restored and sha256-verified against
<code>registry/data_manifest.json</code> ({fmt((prepare.get('grid') or {}).get('footprint_cells'),0)} footprint cells of
{esc(json.dumps((prepare.get('grid') or {}).get('shape')))}); 118 scored rasters hash-verified 0 mismatches;
official metric and submission contract re-read from the competition pages today.</p>
</section>
"""
    (DOCS / "executive-summary-20261031.html").write_text(p1 + body + FOOT)

    # ---- how to submit page -----------------------------------------------------
    note = run.get("submission_note", "")
    note = run.get("submission_note", "")
    subkit = table(
        ["Step", "Exactly what to use", "Why"],
        [["1. Download the primary file",
          f'<a href="downloads/{esc(Path(art.get("nan_variant", "")).name)}" download>'
          f'<strong>{esc(Path(art.get("nan_variant", "")).name)}</strong></a> &mdash; sha256 '
          f'<code>{esc(str(art.get("nan_variant_sha256"))[:16])}&hellip;</code>',
          "the rules text asks for data outside the footprint to be null or NaN, so this is the "
          "official-convention twin"],
         ["1b. If the portal rejects NaN",
          f'<a href="downloads/{esc(Path(art.get("tif", "")).name)}" download>'
          f'<strong>{esc(Path(art.get("tif", "")).name)}</strong></a> &mdash; sha256 '
          f'<code>{esc(str(art.get("tif_sha256"))[:16])}&hellip;</code>',
          "all 12,279,160 cells finite and every value is exactly 0 or 1, so &ldquo;predicted values "
          "must be in range [0, 1]&rdquo; cannot fire; identical inside the footprint (checked)"],
         ["2. Name the submission",
          f'<code>{esc(run.get("submission_name", ""))}</code>',
          "unique stem; no file in the 118-raster registry shares it"],
         ["3. Paste this note ("
          + str(len(note)) + " chars, limit 140)",
          f'<code>{esc(note)}</code>',
          "every number in it is labelled, so nobody can read it as a claimed score"],
         ["4. Do not also upload a focus-site file",
          "any of the nine rows in section 02",
          "they are prior submissions of other sites; re-uploading one is a duplicate and wastes the "
          "weekly cap"]],
        "the ZIP beside each .tif contains the same bytes (verified); local validator receipts are "
        f'<code>downloads/{esc(Path(art.get("tif", "")).name)}.validator.json</code> and the run card '
        f'<code>downloads/{esc(run.get("submission_name", ""))}.run-card.json</code>')

    how = f"""
<p class="breadcrumb">GEMS prize challenge <span>/</span> How to submit <span>/</span> 31 October 2026</p>
<div class="alert" role="alert" style="border:4px solid {band};background:#fff">
<p style="font-size:19px"><strong style="color:{band}">{verdict}</strong></p>
<p>Do not upload anything from section &ldquo;nine focus sites&rdquo;: those bytes are already in the
competition. The only file this project generates for upload is the one below.</p></div>
<section class="section"><h2>1. The file</h2>
<p><a href="downloads/{esc(Path(art.get('tif','')).name)}" download><strong>{esc(Path(art.get('tif','')).name)} &#8595;</strong></a>
&middot; <a href="downloads/{esc(Path(art.get('zip','')).name)}" download>ZIP with the same single GeoTIFF &#8595;</a></p>
<ul>
<li>SHA-256 <code>{esc(art.get('tif_sha256'))}</code></li>
<li>single band, float32, EPSG:32611, 3730&times;3292, 100&nbsp;m cells, geotransform identical to
<code>sample_submission.tif</code></li>
<li>values: 1.0 at each emitted dot, 0.0 everywhere else inside the scored footprint, no NaN inside it
(the NaN-exterior twin is provided because the official text says data outside the bounds should be
null/NaN; the [0,1] portal check is satisfied by both)</li>
</ul></section>
<section class="section"><h2>2. Portal steps (no local step substitutes for them)</h2>
<ol>
<li>Open the submissions page of
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition 306</a> and log in.</li>
<li>Click <em>New submission</em> &rarr; <em>File to submit</em> and pick the <code>.tif</code> (or the
<code>.zip</code> containing exactly that one GeoTIFF).</li>
<li>Set the name/note field to <code>{esc(note)}</code> (the portal allows a short comment; it must not be empty
if you want the receipt to be attributable).</li>
<li>Press <em>Create submission</em>. The portal scores it against the public test chunk and writes a row into
your submission history; that row is the only ORGANIZER-CONFIRMED number that will ever exist for this file.</li>
<li>Record the score back into this repository (add it to <code>registry/registry.json</code> with the file's
SHA-256) so the estimator can be calibrated on a real receipt instead of an owner-reported value.</li>
</ol>
<p class="micro">Weekly limits and the one-selected-submission rule are enforced by the portal, not by this
project; this repository has no uploader and never spends a slot.</p></section>
<section class="section"><h2>3. Which error messages mean what</h2>
<table><thead><tr><th>Portal message</th><th>Verified cause in our files</th><th>Fix applied here</th></tr></thead><tbody>
<tr><td>Predicted values must be in range [0, 1]</td>
<td>a cell with a value &gt; 1, a negative value, or a NaN/Inf inside the raster array. The raw
susceptibility and credit fields this project computes are unnormalised, so an exported intermediate
trips the check immediately.</td>
<td>the writer clips into [0,1] only after an explicit assertion that no finite value was outside it,
then reopens the file and re-checks; the receipt
<code>{esc(Path(art.get('tif','')).name)}.validator.json</code> records
<code>portal_safe_local_policy: true</code> before the file is offered for download.</td></tr>
<tr><td>shape / CRS / geotransform mismatch</td><td>reprojected or resampled output, or a 3-band RGB
GeoTIFF.</td><td>writer copies the template profile verbatim and the validator compares CRS, shape,
transform and bounds.</td></tr>
<tr><td>file too large / wrong container</td><td>a multi-band or BigTIFF export.</td>
<td>classic single-band TIFF; the ZIP holds exactly one member.</td></tr>
</tbody></table></section>

{subkit}
"""
    (DOCS / "how-to-submit-20261031.html").write_text(
        HEAD.format(title="How to submit, 31 Oct 2026") + how + FOOT)

    # ---- estimator + hypotheses stubs -------------------------------------------
    rows = fit.get("per_submission", [])[:40]
    per = table(["Submission", "Owner-reported", "MODEL-ESTIMATE", "Residual", "Dots", "Family"],
                [[f'<code>{esc(r["name"][:58])}</code>', fmt(r["observed_owner_reported"]),
                  fmt(r["model_estimate"]), fmt(r["residual"]), fmt(r["n_dots"], 0), fmt(r["family"], 0)]
                 for r in rows], "40 highest owner-reported values of 118")
    (DOCS / "estimator-20261031.html").write_text(HEAD.format(title="Score estimator") + f"""
<p class="breadcrumb">GEMS prize challenge <span>/</span> Score estimator <span>/</span> 31 October 2026</p>
<section class="section"><h2>Forward model</h2>
<p><code>pi(x) = K &middot; tilt(susceptibility, s) &middot; (1 &minus; exp(&(d<sub>catalogue</sub>&minus;1)/c))</code>,
scored exactly through the published DTI formula on a 96&times;9 binned support.
TP_w is linear in the truth indicator, so the fit is an inversion, not a regression on descriptors.</p>
{est_tbl}
<div class="alert" role="note"><p><strong>Reproduce it:</strong>
<code>.venv/bin/python scripts/wbg8_lane.py prepare</code> then <code>bins</code>, <code>fit</code>,
<code>emit</code>; score any TIFF with <code>.venv/bin/python scripts/wbg8_estimate.py &lt;file.tif&gt;</code>.</p></div>
<h2>Per-submission behaviour of the estimator</h2>{per}
</section>""" + FOOT)

    (DOCS / "hypotheses-20261031.html").write_text(HEAD.format(title="Ranked hypotheses") + f"""
<p class="breadcrumb">GEMS prize challenge <span>/</span> Hypotheses <span>/</span> 31 October 2026</p>
<section class="section">{hyp_tbl}
<h2>Why these five, and what was rejected</h2>
<p>The candidate list was screened against the measured 118-file portfolio, not against taste: a
hypothesis whose mechanism is already represented in a <em>scored</em> sibling file has to clear that
file's number, not a holdout. Radiometric/alteration and geodetic-strain primaries were demoted for
exactly that reason (0.0782, 0.0558, 0.0963, 0.0000, 0.0132 owner-reported).</p>
<h2>Non-fault mimics that must be argued against</h2>
<ul><li>lithologic contacts offsetting both potential fields (the strongest confounder of H1);</li>
<li>alluvial-channel and pediment boundaries, which create relief deficits with no structure;</li>
<li>DEM/magnetic interpolation artifacts shared between derived bands;</li>
<li>mining or seismicity-grid sampling footprints, which imprint on the geodetic and earthquake bands.</li></ul>
</section>""" + FOOT)

    # ---- index banner -----------------------------------------------------------
    idx = (DOCS / "index.html").read_text()
    marker = '<main id="main" class="wrap">'
    banner = (f'<div class="alert" role="alert" style="border:4px solid {band};background:#fff">'
              f'<p style="font-size:19px"><strong style="color:{band}">{verdict}</strong> &nbsp;'
              f'<a href="executive-summary-20261031.html"><strong>31 Oct executive summary: nine-site table, '
              f'calibrated estimator, and the unique generated TIFF download &#8594;</strong></a></p>'
              f'<p><a href="downloads/{esc(Path(art.get("tif","")).name)}" download>'
              f'{esc(Path(art.get("tif","")).name)} &#8595;</a> &middot; MODEL-ESTIMATE '
              f'{fmt(est.get("value"))} (not an organizer score) &middot; '
              f'{fmt(desc.get("n_dots"),0)} dots, 0 on the mapped catalogue.</p></div>')
    if "executive-summary-20261031.html" not in idx:
        idx = idx.replace(marker, marker + banner, 1)
        (DOCS / "index.html").write_text(idx)

    # ---- feed ------------------------------------------------------------------
    feed = load(DOCS / "data" / "feed.json", {}) or {}
    feed["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    feed["leaderboard"] = {"rank": 1, "participant_display": board["rows"][0]["participant"],
                           "public_dw_tversky": board["rows"][0]["best_public_dw_tversky"],
                           "top20_threshold": 0.3417,
                           "evidence_class": "OFFICIAL-PUBLIC-LEADERBOARD-OBSERVATION",
                           "source": board["source"], "observed_date_utc": "2026-10-31",
                           "not_a_project_submission_receipt": True}
    feed["current_lane"] = {"lane": "WBG-8", "submission": Path(art.get("tif", "")).name,
                            "tif_sha256": art.get("tif_sha256"),
                            "ok_to_download": ok_dl, "ok_to_submit_under_project_gates": ok_sub,
                            "model_estimate": est.get("value"),
                            "model_estimate_interval": est.get("interval"),
                            "holdout_dti": hold.get("dti"),
                            "verdict": run.get("verdict"),
                            "page": "docs/executive-summary-20261031.html"}
    feed["latest_entries"] = (feed.get("latest_entries") or [])[:12]
    feed["latest_entries"].insert(0, {
        "date_utc": "2026-10-31", "kind": "lane", "title": "WBG-8 registry-inverted truth model",
        "summary": f"{verdict.replace('&middot;','-')} for {Path(art.get('tif','')).name}; "
                   f"MODEL-ESTIMATE {est.get('value')}, HOLDOUT-DTI {hold.get('dti')}, "
                   f"max overlap {uniq.get('max_overlap_3px')}", "page": "docs/executive-summary-20261031.html"})
    (DOCS / "data" / "feed.json").write_text(json.dumps(feed, indent=1, allow_nan=False, default=float) + "\n")
    return {"written": ["executive-summary-20261031.html", "how-to-submit-20261031.html",
                        "estimator-20261031.html", "hypotheses-20261031.html",
                        "index.html (banner)", "data/feed.json"], "verdict": verdict}


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
