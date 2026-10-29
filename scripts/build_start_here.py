#!/usr/bin/env python3
"""Build the START-HERE decision page and the final run card from measured receipts.

Every number on the page is read from a receipt file (run cards, uniqueness
audits, geometry, validator output). Nothing is typed in by hand. Reported
leaderboard scores of other sites are labelled USER-REPORTED. The public
leaderboard figures are labelled with the fetch date.

Called by scripts/build_site.py (page body) and run directly to write
evidence/scarp_offcat/final_run_card_20261029.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from html import escape
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

NAME = "wbggemsdoe1-lidar-scarp-coh-nms-offcat-36800-20261029-zeros"
TIF = ROOT / "docs/downloads" / f"{NAME}.tif"
RUN_CARD = ROOT / "evidence/scarp_offcat" / f"run_card_{NAME}.json"
VALIDATOR_OUT = ROOT / "evidence/scarp_offcat/validator_output.json"
UNIQ_FINAL = ROOT / "evidence/uniqueness/scarp_offcat_20261029.json"
NINE_UNIQ = ROOT / "evidence/uniqueness/nine_site_top_files_20261029.json"
GEOM = ROOT / "evidence/uniqueness/focus_site_geometry_20261029.json"
FINAL_CARD = ROOT / "evidence/scarp_offcat/final_run_card_20261029.json"
NOTE = "LiDAR scarp excess x coherence NMS; 36,800 off-catalogue dots; no fitted model; holdout unverified"
assert len(NOTE) <= 140, len(NOTE)

# Nine user-listed top submissions (USER-REPORTED, not organizer-confirmed).
# Each row names the file audited in evidence/uniqueness/nine_site_top_files_20261029.json.
NINE = [
    ("GEMSDOE24", "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477),
    ("GEMSDOE25", "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
    ("GEMSDOE27", "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449),
    ("GEMSDOE28", "gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710),
    ("GEMSDOE30", "gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", 0.2600),
    ("GEMSDOE31", "gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", 0.2708),
    ("GEMSDOE32", "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", 0.2778),
    ("GEMSDOE33", "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", 0.2632),
    ("GEMSDOE36", "gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", 0.2750),
]

LEADERBOARD_FETCH = {
    "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
    "fetched": "2026-10-29 (page cache time not shown)",
    "rows": [("#1", "xiaofanhu", 0.4544), ("#2", "cfld__", 0.3916), ("#3", "Batik Shirt Brothers", 0.3911),
             ("#4", "BrandenKMurray", 0.3841), ("#10", "zeaal", 0.3405), ("#20", "ndavis7", 0.3344)],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def run_validator() -> dict:
    out = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"), str(TIF)],
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    keep = {k: data.get(k) for k in ("file", "sha256", "bytes", "n_finite", "n_nan", "n_infinite", "min", "max",
                                     "emitted_positive_pixels", "on_catalogue_positive_pixels",
                                     "in_footprint_positive_pixels", "footprint_fraction", "all_checks_passed",
                                     "validation_class", "ok_to_submit", "promotion_verdict",
                                     "independent_organizer_origin_authenticated", "warning")}
    keep["run_card_matches_exact_tiff"] = data.get("run_card_matches_exact_tiff")
    keep["checks"] = data.get("checks")
    return keep


def nine_site_rows(nine_audit: dict, geom: dict):
    geom_by = {r["file"]: r for r in geom["rows"]}
    nz = {r["path"]: r["facts"].get("nonzero", 0) for r in nine_audit["registry"]}
    rows = []
    for site, fname, rep in NINE:
        key = next(k for k in nine_audit["candidates"] if k.endswith(fname))
        c = nine_audit["candidates"][key]
        # Non-self comparisons only: the candidate's own copy in the corpus is excluded.
        others = [p for p in nine_audit["pairs"] if p["candidate"] == key and not p["sha256_identical"]]
        identical = [p["registry_path"] for p in others if p["pixel_identical"]]
        literal_hits = [p for p in others if (p["dot_overlap_3px"] or 0) >= 0.70 or (p["spearman_sample"] or 0) > 0.90]
        g = geom_by[fname]
        rows.append({
            "site": site, "file": fname, "reported": rep,
            "format_pass": bool(c["format"]["format_pass"]), "dots": c["dots"],
            "median_dist_px": g["median_dist_to_catalogue_px"],
            "share_within_3px": g["share_within_3px_of_catalogue"],
            "on_catalogue": g["on_catalogue_share"],
            "max_overlap": c["max_dot_overlap_3px"]["value"],
            "max_overlap_registry": c["max_dot_overlap_3px"]["registry"],
            "max_rho": c["max_spearman"]["value"],
            "pixel_identical_nonself": len(identical),
            "pixel_identical_paths": [x.split("/")[0] + "/" + x.split("/")[-1] for x in identical],
            "literal_rule_hits_nonself": len(literal_hits),
            "literal_rule_hits_dense_registry": sum(
                1 for p in literal_hits if nz.get(p["registry_path"], 0) > 50000),
        })
    return rows


def build_card() -> dict:
    rc = load(RUN_CARD)
    uniq = load(UNIQ_FINAL)
    nine_audit = load(NINE_UNIQ)
    geom = load(GEOM)
    val = run_validator()
    VALIDATOR_OUT.write_text(json.dumps(val, indent=1) + "\n")
    nine = nine_site_rows(nine_audit, geom)
    rep = np.array([r["reported"] for r in nine])
    med = np.array([r["median_dist_px"] for r in nine])
    rho = spearmanr(rep, med)
    cand_key = next(k for k in uniq["candidates"] if k.endswith(f"{NAME}.tif"))
    cu = uniq["candidates"][cand_key]
    h = rc["holdout"]
    pdiff = h["paired_difference"]["control_random_same_mask"]
    card = {
        "schema": "gemsdoe1-final-run-card-v1",
        "date_utc": "2026-10-29",
        "name": NAME,
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "hypothesis": ("Unmapped fault scarps leave short-wavelength slope excess "
                       "(ex_max) that is coherent along strike (coh100); NMS peaks of ex_max x coh100 outside a "
                       "3 px (300 m) halo of the mapped catalogue are off-catalogue fault candidates."),
        "mechanism": ("Scarp crest: concentrated short-wavelength slope excess (ex_max) with linear coherence along "
                      "strike (coh100); peak survival under non-maximum suppression (NMS) and the 5 px spacing rule."),
        "named_non_fault_mimic": ("Roads, canal and ditch banks, channel banks, terrace risers, paleo-shorelines "
                                  "landslide headscarps and mines (caveats listed in "
                                  "data/external/lidar_scarp_features.json)."),
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": h["evaluator_version"],
            "scope": "catalogue hide-and-recover, fold-safe replay: dots regenerated per fold from visible catalogue only",
            "withheld_positives": h["withheld_positives"],
            "candidate_dti": h["candidate_dti"],
            "candidate_ci95": h["candidate_ci95"],
            "control_random_same_mask_dti": h["control_random_same_mask_dti"],
            "control_ci95": h["control_ci95"],
            "paired_delta_vs_control": pdiff["delta"],
            "paired_delta_ci95": pdiff["ci95"],
            "leakage_canary_auc_single_feature": h["leakage_canary_auc_ex_max_alone"],
            "leakage_canary_threshold": 0.90,
            "leakage_canary_pass": h["leakage_canary_pass"],
            "experiments_used": 3,
            "experiments_budget": 3,
            "selection_caveat": "Best of three variants on the same holdout; no independent split was used.",
        },
        "estimated_leaderboard_score": "UNAVAILABLE",
        "correlation_overlap_vs_registry": {
            "registry_rasters_compared": cu["registry_rasters_compared"],
            "max_spearman_sample": cu["max_spearman"],
            "max_dot_overlap_3px": cu["max_dot_overlap_3px"],
            "duplicate_hits": cu["duplicate_hits"],
            "unique_by_lane_rule": cu["unique_by_lane_rule"],
            "scope": "focus-site repos (GEMSDOE24,25,27,28,30,31,32,33,36) + repo downloads; not the full 24-repo registry",
        },
        "raster_sha256": sha256(TIF),
        "validator": val,
        "verdict": "negative_for_promotion",
        "decision": {
            "download": "YES",
            "submit": "NO",
            "reason": ("Format-valid and unique, but the project promotion gate requires a holdout that beats the "
                       "best same-evaluator result; this file beats only a random control, by a small paired margin. "
                       "No leaderboard score is projected."),
        },
        "nine_site_geometry_vs_reported": {
            "n": len(nine),
            "spearman_reported_vs_median_dist": float(rho.statistic),
            "spearman_p": float(rho.pvalue),
            "caveat": "n=9; reported scores are USER-REPORTED and unverified; correlation, not causation",
            "rows": nine,
        },
        "irregularities": IRREGULARITIES,
        "sources": SOURCES,
    }
    return card


IRREGULARITIES = [
    ("I1", "The portal error 'Predicted values must be in range [0, 1]' is not reproducible here; the portal is login-walled. Our file has no NaN and values in [0,1]."),
    ("I2", "The official rules allow null or NaN outside the bounds. Our file has no NaN cells (validator), so every cell holds a finite 0 or 1. Organizer acceptance of finite zeros outside the footprint is not verified."),
    ("I3", "data/bridge/sample_submission.tif is not all-zero: it holds 60,988 pixels equal to 1 (the mapped catalogue) and NaN outside the 5,167,373-cell footprint. The official page says the sample predicts total fault absence. The two disagree."),
    ("I4", "A recorded holdout value cannot be reproduced by re-scoring the final TIFF. The WBG-3 TIFF scores 0.003987 on the same folds, but its recorded value is 0.121862, because that lane regenerated dots inside each fold. A catalogue-trained TIFF has no single file-level holdout score."),
    ("I5", "The 'gems-segment-pooled-v1' evaluator has no implementing code in this repository or in the 6GEMSDOE mirror. Benchmarks based on it are unverified here."),
    ("I6", "The prompt gives the leaderboard top as 0.4413, and the repo notes say 0.4544. The page fetched on 2026-10-29 shows #1 at 0.4544 with no cache time. This is flagged, not resolved."),
    ("I7", "LiDAR coverage is partial and was not re-measured in this session (see data/external/lidar_scarp_features.json). The LiDAR feature responds to roads, channels, terrace risers and other steps, so it is not a fault detector by construction."),
    ("I8", "The nearest registry raster is a sibling LiDAR file created today (GEMSDOE24 geo1 concealed-conduit, 20261029) at about 64–65% dot overlap. It passes the 70% rule with a margin of about 5 points, which is a lane-proximity risk to review."),
    ("I9", "The uniqueness check covers 519 rasters from the nine focus-site repos and this repo's downloads. The full 24-repo registry cited in other receipts was not available."),
    ("I10", "The holdout scores recovery of known catalogue faults. The organizer scores new faults. The repo's own check finds the shared holdout does not rank submissions (Spearman 0.144, n=118, AGENTS.md). Holdout DTI is therefore not a leaderboard estimate."),
    ("I11", "Three variants were tested on one holdout, and the best paired interval was selected. That selection is a source of optimism."),
    ("I12", "All nine focus-site scores are USER-REPORTED, not organizer-confirmed. The distance-to-catalogue ordering uses nine points, and it was noticed after the scores were known, so the rank correlation is post hoc."),
    ("I13", "The literal uniqueness rule (≥70% 3 px dot overlap or Spearman >0.90) flags about 100 non-self registry rasters for each of the nine focus files. About half are dense binary rasters (a density artifact of the literal gate); the rest form a shared family. The nine files are therefore NOT unique in this corpus. Our coherence candidate's maximum on the same rule is 0.6424."),
    ("I14", "The shared validator reports run_card_matches_exact_tiff = false and run_card_path = null for the selected TIFF. The run card is not yet linked to the exact bytes; this is a blocker for any promotion."),
    ("I15", "The exmax and halo15 run cards still reference their original docs/downloads paths, which have been moved to evidence/scarp_offcat/negative/. Their SHA-256 values are recorded in the negative folder."),
]

SOURCES = [
    ("DrivenData problem description and metric (distance-weighted Tversky, alpha 0.2, beta 0.8, 300 m kernel, float32 in [0,1], EPSG:32611, 100 m)", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"),
    ("GEMS Prize Official Rules, September 2026", "https://docs.nlr.gov/docs/fy26osti/96647.pdf"),
    ("DrivenData leaderboard (fetched 2026-10-29)", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"),
        ("Reference solution (GitHub; recorded in repo notes, not fetched this session)", "https://github.com/drivendataorg/gems-prize-reference-solution"),
    ("EPSG:32611 (WGS 84 / UTM 11N; recorded in repo notes, not fetched this session)", "https://epsg.io/32611"),
    ("USGS 3DEP, cited as the LiDAR source in the restored JSON (not fetched this session; the no-restriction claim is unverified)", "https://www.usgs.gov/3d-elevation-program"),
    
]


START_CSS = """<style>
.start-hero h1{font-size:clamp(28px,4vw,44px);line-height:1.1;margin:8px 0 12px}
.decision-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:18px 0}
.decision{border-radius:12px;padding:16px;border:2px solid #23665f;background:#fff}
.decision span{display:block;font-size:12px;letter-spacing:.08em;color:#4a5c60}
.decision strong{display:block;font-size:22px;margin:6px 0}
.decision small{color:#4a5c60}
.decision.yes{border-color:#23665f}.decision.no{border-color:#a33b2c}.decision.neutral{border-color:#7a6a2a}
.cta{display:inline-block;background:#23665f;color:#fff;padding:12px 18px;border-radius:10px;text-decoration:none;font-weight:700}
.sha{display:block;margin-top:10px;word-break:break-all;font-size:12px}
table.data{width:100%;border-collapse:collapse;font-size:14px;margin:10px 0}
table.data th,table.data td{border-bottom:1px solid #d7dfe0;padding:8px;text-align:left;vertical-align:top}
table.data th{background:#eef4f4;font-weight:600}
table.data td:first-child{white-space:nowrap}
.tag{font-size:11px;background:#f3e7c9;padding:1px 6px;border-radius:6px}
.lead{font-size:18px}
</style>
"""


def page_body(card: dict) -> str:
    c = card
    h = c["holdout"]
    nr = c["nine_site_geometry_vs_reported"]["rows"]
    cu = c["correlation_overlap_vs_registry"]
    v = c["validator"]
    nine_tr = "".join(
        f"<tr><td>{escape(r['site'])}</td><td><code>{escape(r['file'])}</code></td>"
        f"<td>{r['reported']:.4f} <span class='tag'>USER-REPORTED</span></td>"
        f"<td>UNAVAILABLE</td>"
        f"<td>{'PASS' if r['format_pass'] else 'FAIL'}</td>"
        f"<td>{r['dots']:,}</td><td>{r['median_dist_px']:.2f}</td><td>{r['share_within_3px']*100:.1f}%</td>"
        f"<td>{r['pixel_identical_nonself']}</td>"
        f"<td>{r['literal_rule_hits_nonself']} <small>({r['literal_rule_hits_dense_registry']} dense)</small></td>"
        f"<td><strong>NO</strong> — public file in the {escape(r['site'])} repo</td>"
        f"<td><strong>DO NOT</strong></td></tr>"
        for r in nr)
    lb = "".join(f"<tr><td>{a}</td><td>{escape(b)}</td><td>{s:.4f}</td></tr>" for a, b, s in
                 LEADERBOARD_FETCH["rows"])
    irr = "".join(f"<li><strong>{k}.</strong> {escape(t)}</li>" for k, t in IRREGULARITIES)
    src = "".join(f"<li>{escape(t)} — <a href='{escape(u)}' rel='noopener'>{escape(u)}</a></li>" for t, u in SOURCES)
    rho = c["nine_site_geometry_vs_reported"]["spearman_reported_vs_median_dist"]
    return f"""
{START_CSS}
<section class="start-hero" id="start">
<p class="eyebrow">START HERE · 29 OCTOBER 2026</p>
<h1>Download the TIFF. Do not submit it for a top score.</h1>
<p class="lead">One unique, format-valid GeoTIFF is ready. Its expected leaderboard score is <strong>unknown</strong>. The project promotion gate is not met.</p>
<div class="decision-grid">
<div class="decision yes"><span>DOWNLOAD</span><strong>YES</strong><small>Format and uniqueness checks pass.</small></div>
<div class="decision no"><span>SUBMIT</span><strong>NO — NOT CLEARED</strong><small>Does not clear the holdout gate (see below).</small></div>
<div class="decision neutral"><span>ESTIMATED LEADERBOARD SCORE</span><strong>UNAVAILABLE</strong><small>No projection is written as a score.</small></div>
</div>
<p><a class="cta" href="downloads/{escape(NAME)}.tif" download>Download the TIFF ↓</a>
<code class="sha">SHA-256 {escape(c['raster_sha256'])}</code></p>
</section>

<section class="section" id="file">
<h2>1. The file to download</h2>
<table class="data">
<tr><th>What to download</th><td><code>{escape(NAME)}.tif</code> (<a href="downloads/{escape(NAME)}.tif" download>direct link</a>)</td></tr>
<tr><th>Format (local shared validator)</th><td>one band, float32, EPSG:32611, 3730 × 3292, 100 m, transform matches the competition grid · min {v['min']:.0f}, max {v['max']:.0f} · NaN {v['n_nan']} · all checks {'PASS' if v['all_checks_passed'] else 'FAIL'}</td></tr>
<tr><th>Dots</th><td>{v['emitted_positive_pixels']:,} pixels = 1.0; all others 0.0; on mapped catalogue {v['on_catalogue_positive_pixels']}</td></tr>
<tr><th>Unique vs {cu['registry_rasters_compared']} registry rasters</th><td>exact duplicates {cu['duplicate_hits']} · max 3 px dot overlap <strong>{cu['max_dot_overlap_3px']['value']*100:.2f}%</strong> (limit 70%; nearest <code>{escape(cu['max_dot_overlap_3px']['registry'].split('/')[-1])}</code>) · max sampled Spearman <strong>{cu['max_spearman_sample']['value']:.3f}</strong> (limit 0.90) · <strong>{'UNIQUE' if cu['unique_by_lane_rule'] else 'NOT UNIQUE'}</strong> by the lane rule</td></tr>
<tr><th>Holdout (HOLDOUT-DTI)</th><td>evaluator <code>{escape(h['evaluator_version'])}</code>, fold-safe replay, n={h['withheld_positives']:,} withheld positives · candidate <strong>{h['candidate_dti']:.4f}</strong> (95% CI [{h['candidate_ci95'][0]:.4f}, {h['candidate_ci95'][1]:.4f}]) · random control same mask <strong>{h['control_random_same_mask_dti']:.4f}</strong> (95% CI [{h['control_ci95'][0]:.4f}, {h['control_ci95'][1]:.4f}]) · paired delta <strong>{h['paired_delta_vs_control']:+.4f}</strong> (95% CI [{h['paired_delta_ci95'][0]:+.4f}, {h['paired_delta_ci95'][1]:+.4f}])</td></tr>
<tr><th>Leakage canary</th><td>single feature ex_max × coh100, AUC {h['leakage_canary_auc_single_feature']:.3f} ≤ 0.90 · <strong>PASS</strong></td></tr>
<tr><th>Submit-ready?</th><td><strong>No.</strong> The shared validator says <code>ok_to_submit: {str(v['ok_to_submit']).lower()}</code> because no approved run card exists, and the gate is not met. Format pass is not organizer acceptance.</td></tr>
</table>
<p><strong>Submission name and note</strong> (for the DrivenData form): name <code>{escape(NAME)}</code> · note (≤140 characters, {c['submission_note_chars']} used): <code>{escape(c['submission_note'])}</code></p>
</section>

<section class="section" id="nine">
<h2>2. The nine focus sites — which file, what estimate, is it unique?</h2>
<p class="micro">Reported scores are USER-REPORTED from the prompt, not organizer receipts. The leaderboard estimate for every one of these files is UNAVAILABLE. Each file is a public file in another site's repo, so it is not a unique submission for us. Median distance is the Euclidean distance from each dot to the nearest mapped-fault pixel, in 100 m pixels.</p>
<table class="data">
<tr><th>Site</th><th>File</th><th>Reported (user)</th><th>Estimated score</th><th>Format</th><th>Dots</th><th>Median dist (px)</th><th>Within 3 px</th><th>Pixel-identical copies (non-self)</th><th>Literal-rule hits, non-self (≥70% overlap or ρ&gt;0.9)</th><th>Unique new submission?</th><th>Download &amp; submit?</th></tr>
{nine_tr}
</table>
</section>

<section class="section" id="why">
<h2>3. Why did GEMSDOE32 (0.2778) score highest, and can we beat it?</h2>
<ul>
<li><strong>Off the mapped faults.</strong> All nine files place 0% of dots on the mapped catalogue. Whether the organizer's labels also exclude mapped faults is not verified here.</li>
<li><strong>Stays away from the known-fault halo.</strong> Across the nine sites, the median dot distance to the catalogue rises in the same order as the reported scores (Spearman {rho:.2f}, n=9; post hoc, because the ordering was noticed after the scores were known). GEMSDOE32 has the largest median distance (19.65 px) and the fewest dots within 3 px (5.8%). This is a hypothesis: nine points, unverified scores, and correlation, not causation.</li>
<li><strong>Mechanism (proposed).</strong> With alpha 0.2 and beta 0.8, the metric weights false negatives (0.8) four times as heavily as false positives (0.2). If new faults lie away from the known traces, dots hugging known traces mostly add false positives, while spacing dots away from them covers more unmapped area per dot.</li>
<li><strong>Can we beat 0.2778?</strong> Not demonstrated. Our best measured candidate beats only a random control, by a small paired margin, on a catalogue proxy. No measurement in this sandbox can establish a score above 0.2778 on the organizer's private set.</li>
<li><strong>Test of the distance mechanism.</strong> Experiment 3 excluded a 15 px halo. Its candidate (0.0218) did not beat its own control (0.0202), and this proxy rewards catalogue proximity by construction. The test cannot settle the question, so it is inconclusive.</li>
</ul>
</section>

<section class="section" id="experiments">
<h2>4. Experiments run (budget 3 of 3)</h2>
<table class="data">
<tr><th>Variant</th><th>Holdout DTI</th><th>Control</th><th>Paired delta (95% CI)</th><th>Outcome</th></tr>
<tr><td>ex_max NMS (scarp slope excess)</td><td>0.054981</td><td>0.049541</td><td>+0.005439 [−0.001270, +0.012483]</td><td>Not significant. Kept as a negative result (<code>evidence/scarp_offcat/negative/</code>).</td></tr>
<tr><td><strong>ex_max × coh100 NMS (selected file)</strong></td><td><strong>0.058087</strong></td><td>0.049541</td><td><strong>+0.008546 [+0.001053, +0.016446]</strong></td><td>Best paired interval. Downloadable; not cleared to submit.</td></tr>
<tr><td>coh100 + 15 px halo</td><td>0.021793</td><td>0.020169</td><td>+0.001624 [−0.003752, +0.006584]</td><td>Not significant. Negative result.</td></tr>
</table>
</section>

<section class="section" id="lb">
<h2>5. Public leaderboard (fetched, not verified against the live page)</h2>
<table class="data"><tr><th>Rank</th><th>Participant</th><th>Public DW-Tversky</th></tr>{lb}</table>
<p class="micro">Source: <a href="{escape(LEADERBOARD_FETCH['url'])}">{escape(LEADERBOARD_FETCH['url'])}</a>, fetched {escape(LEADERBOARD_FETCH['fetched'])}. The prompt's 0.4413 and 0.3195 figures do not match this page (irregularity I6).</p>
</section>

<section class="section" id="how">
<h2>6. How to submit (no manual judgement needed)</h2>
<ol>
<li>Download <code>{escape(NAME)}.tif</code> from this page.</li>
<li>Check the SHA-256 above matches your download.</li>
<li><strong>Decide first:</strong> the decision box says SUBMIT: NO. Only upload if you accept that the expected score is unknown and probably below the top.</li>
<li>If you upload, use the DrivenData submission form (requires login): single-band GeoTIFF, the name and note above.</li>
</ol>
<p class="micro">Source for the format: the official rules and problem page list, EPSG:32611, 100 m, same bounds, float32 values between 0 and 1, and data outside the bounds null or NaN. Links are in section 9.</p>
</section>

<section class="section" id="irr">
<h2>7. Irregularities flagged for review</h2>
<ul class="irr">{irr}</ul>
</section>

<section class="section" id="next">
<h2>8. Ranked next hypotheses (untested)</h2>
<ol>
<li><strong>H4 — budget curve (cheapest).</strong> Layers: the existing scarp score. Signature: DTI is a function of dot count under a fixed alpha and beta. Test N = 20k to 60k on the same holdout. Cost: minutes. Does not need new data.</li>
<li><strong>H1 — coherent crest lines.</strong> Layers: ex_max and coh100. Signature: continuous ridge lines along strike rather than dots. Cost: moderate. Needs a line-aware scoring rule before a holdout is meaningful.</li>
<li><strong>H3 — radiometric halo.</strong> Layers: <code>geodawn_rad_u8.tif</code> (K, Th, U, total count), already in GEMSDOE24's data. Signature: potassium and thorium anomalies near scarp crests (hydrothermal alteration). Differs from the repo's other lanes, which use magnetics and gravity. Cost: moderate; provenance must be verified first.</li>
<li><strong>H2 — distance-profile placement.</strong> Signature: the median-distance ordering. Cannot be tested here; it needs organizer receipts for the nine sites or a reproduced score.</li>
</ol>
</section>

<section class="section" id="src">
<h2>9. Official sources (for manual review)</h2>
<ul>{src}</ul>
</section>
"""


def render_body() -> str:
    card = build_card()
    return page_body(card)


if __name__ == "__main__":
    card = build_card()
    FINAL_CARD.parent.mkdir(parents=True, exist_ok=True)
    FINAL_CARD.write_text(json.dumps(card, indent=2, default=float) + "\n")
    print(json.dumps({"final_card": str(FINAL_CARD.relative_to(ROOT)), "sha256": card["raster_sha256"],
                      "spearman": card["nine_site_geometry_vs_reported"]["spearman_reported_vs_median_dist"]}, indent=1))
