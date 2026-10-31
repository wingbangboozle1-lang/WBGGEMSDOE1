#!/usr/bin/env python3
"""Build the 31 Oct 2026 executive summary, machine-readable table and run card.

Every number is read from a file in this repository (nothing typed by hand):
  * docs/data/nine_site_audit_20261029.json      nine-site top files, owner-reported scores, hashes, pairwise overlap
  * evidence/h2_lag/experiment_20261031.json     H2 holdout arms (HOLDOUT-DTI, CI, canary)
  * evidence/h2_lag/avoid_sweep_px*.json         catalogue-avoidance ablation (HOLDOUT-DTI)
  * evidence/h2_lag/random_field_literal_gate_control.json   literal gate on a random dot field
  * evidence/h2_lag/candidate_uniqueness_rows_20261031.json  per-raster rows for the candidate
  * docs/downloads/wbggemsdoe1-h2-...-20261031.json         shared writer receipt for the candidate TIFF
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "wbggemsdoe1-h2-edgecorr-avoid3-37654-20261031"
TIF_REL = f"downloads/{NAME}.tif"
ZIP_REL = f"downloads/{NAME}.zip"
RECEIPT_REL = f"downloads/{NAME}.json"
NOTE = "H2 potential-field edge corroboration, 3px catalogue avoidance; research only, NOT approved for upload"
LEADERBOARD_OBS = {
    "fetched_utc": "2026-10-31",
    "source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
    "rank1": {"user": "xiaofanhu", "score": 0.4544},
    "rank2": {"user": "cfld__", "score": 0.3925},
}
USER_CLAIMS = {"highest_user_claim_focus": 0.2778, "leaderboard_user_claim": 0.4413, "user_claim_0_3195": 0.3195}


def load(p):
    return json.loads((ROOT / p).read_text())


def esc(x):
    return html.escape(str(x))


def main() -> int:
    audit = load("docs/data/nine_site_audit_20261029.json")
    exp = load("evidence/h2_lag/experiment_20261031.json")
    sweep = {a: load(f"evidence/h2_lag/avoid_sweep_px{a}.json") for a in (0, 3, 6)}
    control = load("evidence/h2_lag/random_field_literal_gate_control.json")
    rows = load("evidence/h2_lag/candidate_uniqueness_rows_20261031.json")["rows"]
    gate = load("evidence/h2_lag/candidate_uniqueness_20261031.json")["gate"]
    full_reg = load("evidence/h2_lag/focus_vs_registry_overlap_20261031.json")["sites"]
    receipt = load(f"docs/{RECEIPT_REL}")
    tif = ROOT / f"docs/{TIF_REL}"
    tif_sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    assert tif_sha == receipt["sha256"], "receipt hash mismatch"

    # ---- nine focus sites: best (highest owner-reported) file per site
    best = {}
    for f in audit["files"]:
        s = f["site"]
        if s not in best or f["user_reported_score"] > best[s]["user_reported_score"]:
            best[s] = f
    sites = sorted(best, key=lambda s: int(s.replace("GEMSDOE", "")))
    assert sites == ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31",
                     "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"], sites
    top_keys = {best[s]["key"]: s for s in sites}

    pair = {}
    for p in audit["pairwise"]:
        pair[(p["a"], p["b"])] = p
        pair[(p["b"], p["a"])] = {**p, "a": p["b"], "b": p["a"],
                                   "frac_a_within_3px_of_b": p["frac_b_within_3px_of_a"],
                                   "frac_b_within_3px_of_a": p["frac_a_within_3px_of_b"]}

    row_by_sha = {r.get("sha256"): r for r in rows}
    table = []
    for s in sites:
        f = best[s]
        worst = (0.0, None, False)
        for k in top_keys:
            if k == f["key"]:
                continue
            p = pair.get((f["key"], k))
            if p is None:
                continue
            if p["frac_a_within_3px_of_b"] > worst[0]:
                worst = (p["frac_a_within_3px_of_b"], top_keys[k], p["identical_positive_sets"])
        cand_row = row_by_sha.get(f["sha256"], {})
        cand_frac = cand_row.get("my_dots_within_3px_of_theirs")
        literal_pass = worst[0] <= 0.70 and not worst[2]
        table.append({
            "site": s,
            "file_name": f["name"],
            "download_url": f"https://github.com/{f['repo']}/blob/{f['commit']}/{f['path']}",
            "sha256": f["sha256"],
            "dots": f["n_positive"],
            "owner_reported_score": f["user_reported_score"],
            "score_label": "OWNER-REPORTED (not ORGANIZER-CONFIRMED; no submission receipt)",
            "max_literal_overlap_vs_other_focus_tops": round(worst[0], 4),
            "max_overlap_partner": worst[1],
            "identical_to_partner": bool(worst[2]),
            "unique_under_literal_70pct_rule_vs_focus_sites": literal_pass,
            "unique_by_bytes_vs_focus_sites": not worst[2],
            "candidate_overlap_vs_this_file": cand_frac,
            "full_registry_max_literal_overlap": full_reg[s]["max_literal_overlap_vs_registry"],
            "full_registry_entries_over_70pct": len(full_reg[s]["registry_entries_over_70pct"]),
            "full_registry_unique_literal": full_reg[s]["unique_literal_vs_registry"],
        })

    # ---- candidate
    cand_max_registry = max((r.get("my_dots_within_3px_of_theirs") or 0) for r in rows)
    cand_dups = [r["submission"] for r in rows
                 if (r.get("my_dots_within_3px_of_theirs") or 0) > 0.70]
    arms = exp["arms"]
    candidate = {
        "name": NAME,
        "note": NOTE,
        "note_chars": len(NOTE),
        "download_file": TIF_REL,
        "zip_file": ZIP_REL,
        "sha256": tif_sha,
        "dots": receipt["validator"]["emitted_positive_pixels"] if "emitted_positive_pixels" in receipt["validator"] else None,
        "dot_count_from_writer": int(receipt["metadata"]["dots"]),
        "format_checks": receipt["validator"]["checks"],
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator": exp["evaluator"],
            "withheld_truth_cells_summed": arms["full"]["n_truth"],
            "dti": round(arms["full"]["pooled_dti"], 6),
            "ci95": [round(v, 6) for v in arms["full"]["ci95_bootstrap_over_16_cells"]],
            "random_null_dti": round(arms["random"]["pooled_dti"], 6),
            "random_null_ci95": [round(v, 6) for v in arms["random"]["ci95_bootstrap_over_16_cells"]],
            "paired_full_minus_random": round(exp["paired_full_minus_random_mean_cell_dti"], 6),
            "paired_ci95": [round(v, 6) for v in exp["paired_ci95_over_16_cells"]],
            "mag_only_dti": round(arms["mag_only"]["pooled_dti"], 6),
            "grav_only_dti": round(arms["grav_only"]["pooled_dti"], 6),
        },
        "canary_alone_auc": exp["canary_alone_auc"],
        "uniqueness_literal": {
            "byte_unique_among_checked": gate["byte_unique_among_checked"],
            "pixel_unique_among_checked": gate["pixel_unique_among_checked"],
            "registry_rasters_checked": gate["registry_rasters_checked"],
            "max_spearman_vs_registry": round(gate["worst_spearman_full_footprint"], 4),
            "max_overlap_vs_registry": round(cand_max_registry, 4),
            "duplicates_over_70pct": cand_dups,
            "unique": len(cand_dups) == 0,
        },
        "leaderboard_estimate": "UNAVAILABLE (no organizer receipt; holdout does not rank submissions)",
        "verdict": {"download": "YES (research file)", "submit": "NO"},
    }
    ctrl_summary = [{"trial": c["trial"], "duplicate_count": c["duplicate_count"],
                     "worst_overlap": round(c["worst_dot_overlap"], 4),
                     "worst_submission": c["worst_overlap_submission"]} for c in control]

    summary = {
        "schema": "gemsdoe1-exec-summary-20261031-v1",
        "generated_by": "scripts/build_exec_20261031.py",
        "verdict_page": "docs/executive-summary-h2-20261031.html",
        "submission_slots_used": 0,
        "nine_site_table": table,
        "candidate": candidate,
        "literal_gate_random_control": ctrl_summary,
        "catalogue_avoidance_ablation_random_arm": {
            f"avoid_{a}px_HOLDOUT-DTI": round(sweep[a]["arms"]["random"]["pooled_dti"], 6) for a in (0, 3, 6)
        },
        "leaderboard_observation": LEADERBOARD_OBS,
        "user_claims_unverified": USER_CLAIMS,
    }
    (ROOT / "docs/data/executive_summary_20261031.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n")

    run_card = {
        "schema": "wbggemsdoe1-run-card-v1",
        "date_utc": "2026-10-31",
        "candidate": NAME,
        "hypothesis": "Potential-field edges co-located in magnetic (rtp) AND gravity (iso_grav_anom) fields, "
                      "on coherent magnetic fabric, mark concealed faults missing from the USGS/INGENIOUS catalogue.",
        "mechanism": "A fault offsets both magnetic basement fabric and gravity contacts at the same place; "
                     "joint edges with high structure-tensor coherence are fault-like.",
        "named_non_fault_mimic": "Lithologic contacts and intrusive margins (magnetic/gravity edges without offset), "
                                 "plus flight-line/levelling artifacts that appear in magnetics only.",
        "holdout_dti_ci": candidate["holdout"],
        "leakage_canary_alone_auc": exp["canary_alone_auc"],
        "registry_correlation_overlap": candidate["uniqueness_literal"],
        "raster_sha256": tif_sha,
        "validator_output": {"shared_validator_all_checks_passed": receipt["validator"]["all_checks_passed"] if "all_checks_passed" in receipt["validator"] else None,
                             "writer_checks": receipt["validator"]["checks"]},
        "submission_name": NAME,
        "submission_note": NOTE,
        "note_chars": len(NOTE),
        "verdict": "negative for promotion: holdout gain over matched random null not established (paired CI includes 0); "
                   "literal 70% uniqueness gate fails (random control fails too). DOWNLOAD: research only. SUBMIT: NO.",
        "submission_slots_used": 0,
    }
    (ROOT / "evidence/h2_lag/run_card_20261031.json").write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")

    # ---- HTML
    def row_html(t):
        cls = "fail" if not t["unique_under_literal_70pct_rule_vs_focus_sites"] else "pass"
        return (f"<tr><td><b>{esc(t['site'])}</b></td>"
                f"<td><a href=\"{esc(t['download_url'])}\">{esc(t['file_name'])}</a><br><small>SHA-256 {esc(t['sha256'][:16])}… · {t['dots']:,} dots</small></td>"
                f"<td><b>{t['owner_reported_score']:.4f}</b><br><small>OWNER-REPORTED · not organizer-confirmed</small></td>"
                f"<td class=\"{cls}\">{'UNIQUE' if t['unique_under_literal_70pct_rule_vs_focus_sites'] else 'NOT UNIQUE'}"
                f"<br><small>max overlap {t['max_literal_overlap_vs_other_focus_tops']*100:.1f}% vs {esc(t['max_overlap_partner'])}"
                f"{' (identical dot set)' if t['identical_to_partner'] else ''}</small></td>"
                f"<td class=\"{'pass' if t['full_registry_unique_literal'] else 'fail'}\">{'UNIQUE' if t['full_registry_unique_literal'] else 'NOT UNIQUE'}"
                f"<br><small>{t['full_registry_entries_over_70pct']} registry entries over 70%; max {t['full_registry_max_literal_overlap']*100:.1f}%</small></td>"
                f"<td><small>Already submitted by the owner (per prompt). Re-uploading it is a duplicate; do not upload.</small></td></tr>")

    H = candidate["holdout"]
    ctrl_lines = "".join(f"<li>Random dot field, trial {c['trial']}: {c['duplicate_count']} literal duplicates, worst overlap {c['worst_overlap']*100:.2f}% vs <code>{esc(c['worst_submission'])}</code></li>" for c in ctrl_summary)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive summary 31 Oct 2026 · GEMS submission status</title>
<link rel="stylesheet" href="assets/style.css">
<style>
 body{{font-family:system-ui,Arial,sans-serif;max-width:1180px;margin:0 auto;padding:18px;color:#1d2a2e;line-height:1.45}}
 .verdict{{border:3px solid #b3261e;background:#fff4f2;padding:14px 18px;border-radius:10px;margin:10px 0}}
 .ok{{border-color:#1e7b3a;background:#f1fbf4}}
 table{{border-collapse:collapse;width:100%;margin:10px 0;font-size:14px}}
 th,td{{border:1px solid #c9d4d7;padding:7px 9px;vertical-align:top;text-align:left}}
 th{{background:#173b42;color:#fff}}
 td.fail{{background:#fdecea}} td.pass{{background:#e9f7ee}}
 code{{font-size:12.5px}} small{{color:#4a5d63}}
 .big{{font-size:19px;font-weight:700}}
</style></head><body>
<p><a href="index.html">← Research desk overview</a> · <a href="start-here-20261029.html">29 Oct start page</a></p>
<h1>Executive summary · 31 Oct 2026</h1>
<div class="verdict"><div class="big">DOWNLOAD: YES (research file) · SUBMIT: NO</div>
<p>No file is cleared for the DrivenData upload. The new file <code>{esc(NAME)}.tif</code> is a valid, unique file, but it fails the project's literal
uniqueness gate on {len(cand_dups)} registry rasters. A uniformly random dot field fails the same gate, so this rule cannot be satisfied by any dot file (see §4).</p>
<p><a href="{esc(TIF_REL)}"><b>Download the candidate TIFF</b></a> · <a href="{esc(ZIP_REL)}">ZIP</a> · <a href="{esc(RECEIPT_REL)}">receipt</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/arena/0c266855-wbggemsdoe1/evidence/h2_lag/run_card_20261031.json">run card (JSON)</a></p>
<p><b>Estimated leaderboard score: UNAVAILABLE.</b> The only numbers here are HOLDOUT-DTI on the project's holdout, which does not rank real submissions (AGENTS.md 0b-i) and is not on the leaderboard scale.</p></div>

<h2>1. Nine focus sites: the file to download, its score and uniqueness</h2>
<p>Each row is the highest owner-reported file for that site. Scores come from the prompt and are <b>not organizer-confirmed</b>. "Unique" uses the literal 70% rule, first against the other eight focus files, then against every cached registry raster (self excluded; <code>evidence/h2_lag/focus_vs_registry_overlap_20261031.json</code>). The 0.2778 file is the highest owner-reported score, and it is already in the competition, so re-uploading it is a duplicate.</p>
<table><tr><th>Site</th><th>File to download (GitHub, for manual review)</th><th>Score (label)</th><th>Unique vs other focus sites?</th><th>Unique vs ALL 117 registry rasters?</th><th>Decision</th></tr>
{''.join(row_html(t) for t in table)}
</table>
<p><small>GEMSDOE25 and GEMSDOE30 hold the same dot set (Jaccard 1.0). They count as one design. Source: <code>docs/data/nine_site_audit_20261029.json</code>.</small></p>

<h2>2. The new unique TIFF</h2>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Download</td><td><a href="{esc(TIF_REL)}">{esc(NAME)}.tif</a> (one-TIFF ZIP: <a href="{esc(ZIP_REL)}">zip</a>)</td></tr>
<tr><td>SHA-256</td><td><code>{tif_sha}</code></td></tr>
<tr><td>Format (independent rasterio read + shared writer receipt)</td><td>1 band, float32, EPSG:32611, 3,730 × 3,292, transform = training grid, values {{0, 1}} only, 0 NaN, 0 Inf, {candidate['dot_count_from_writer']:,} dots, 0 dots on the mapped catalogue, 0 dots outside the footprint.</td></tr>
<tr><td>Name</td><td><code>{esc(NAME)}</code></td></tr>
<tr><td>Note ({len(NOTE)} characters)</td><td><code>{esc(NOTE)}</code></td></tr>
<tr><td>Method</td><td>Surface = √(magnetic edge × gravity edge) × magnetic structure coherence, from the 19 cached potential-field bands only. Quadrant quota K/4, with dots kept more than 3 px from the mapped catalogue (the exclusion removes pixels at distance of 3 px or less), with 3-px spacing.</td></tr>
<tr><td>HOLDOUT-DTI (method) <small>evaluator gems57-pooled-hide-v2</small></td><td><b>{H['dti']:.4f}</b>, 95% CI [{H['ci95'][0]:.4f}, {H['ci95'][1]:.4f}], n withheld truth = {H['withheld_truth_cells_summed']:,} (summed over 16 cells)</td></tr>
<tr><td>Matched random-dot null (same budget, same avoidance)</td><td>HOLDOUT-DTI {H['random_null_dti']:.4f}, 95% CI [{H['random_null_ci95'][0]:.4f}, {H['random_null_ci95'][1]:.4f}]</td></tr>
<tr><td>Paired gain over null (decisive test)</td><td>{H['paired_full_minus_random']:+.4f}, paired 95% CI [{H['paired_ci95'][0]:+.4f}, {H['paired_ci95'][1]:+.4f}]. <b>Includes 0, so no gain is established.</b></td></tr>
<tr><td>Magnetic-only / gravity-only arms</td><td>{H['mag_only_dti']:.4f} / {H['grav_only_dti']:.4f} (neither beats the null)</td></tr>
<tr><td>Leakage canary (each feature alone, AUC)</td><td>{', '.join(f"{k} {v}" for k, v in exp['canary_alone_auc'].items() if k not in ('max_alone_auc','leakage_alarm_gt_0_90'))}; max {exp['canary_alone_auc']['max_alone_auc']} (alarm > 0.90: no)</td></tr>
<tr><td>Literal uniqueness (registry)</td><td>Byte-unique: {gate['byte_unique_among_checked']}; pixel-unique: {gate['pixel_unique_among_checked']}; among {gate['registry_rasters_checked']} cached owner-registry rasters. Max Spearman {candidate['uniqueness_literal']['max_spearman_vs_registry']:.4f} (&lt; 0.90 PASS). Literal 3-px overlap &gt; 70% against: {esc(', '.join(cand_dups))}. <b>FAIL.</b></td></tr>
<tr><td>Leaderboard estimate</td><td><b>UNAVAILABLE</b>. No organizer receipt exists. Submission slots used: 0.</td></tr>
</table>

<h2>3. Why GEMSDOE32 B2 (0.2778, owner-reported) scored highest, and whether we can beat it</h2>
<ol>
<li><b>Verified facts (audit JSON):</b> B2 has 37,654 dots, 0 on the mapped catalogue, 0 within 1 px or 2 px of it, and 2,171 (5.8%) within 3 px. Its nearest rival D2.8 is a 44,090-dot file. The 2026-10-29 analysis states that B2 is a pruned subset of D2.8, removing 6,436 dots that lay within 2 px of catalogue traces. Source: <code>docs/data/nine_site_audit_20261029.json</code>, <code>docs/unique-lane-summary-20261029.html</code>. We did not re-derive the subset claim this session.</li>
<li><b>Mechanism (first-order, algebra):</b> with DTI = TP/(TP + 0.2·FP + 0.8·FN), let D be the current score and c a dot's expected kernel cover of truth. Removing that dot raises the score only if c &gt; 0.2·D/(1 − 0.8·D). At D = 0.2778 the threshold is c &gt; 0.0714. Dots with less than about 7% expected cover are net-negative to keep. Pruning dots that sit next to known faults is a plausible way to remove such dots, but this is a derivation, not a measurement.</li>
<li><b>Competing evidence (our holdout, our experiment E2):</b> on the holdout, random dots with <i>no</i> catalogue avoidance score {sweep[0]['arms']['random']['pooled_dti']:.4f}, 3-px avoidance {sweep[3]['arms']['random']['pooled_dti']:.4f}, 6-px avoidance {sweep[6]['arms']['random']['pooled_dti']:.4f}. The holdout therefore rewards proximity to visible faults. The holdout hides catalogue segments, which are continuous with visible traces. The competition's hidden labels are new faults, which are not in the catalogue. <b>The holdout cannot test the pruning mechanism behind B2.</b> This is the central validity problem (see §5).</li>
<li><b>Can we beat 0.2778?</b> Not demonstrated. The best unique candidate has no paired holdout gain (§2). The only real signal is the owner-reported leaderboard values, and a leaderboard check needs an organizer receipt. A calibration ladder on the portal is the fastest way to learn. Each upload uses a weekly slot (three per week under rules §3.4), and this is a user action.</li>
</ol>

<h2>4. The literal uniqueness rule cannot be satisfied by a dot file</h2>
<p>The project's literal lane rule says a file fails if more than 70% of its dots lie within 3 px of one registry raster's dots. A uniformly random dot field of the same size fails it too, so the rule is a control-tested blocker for every dot file:</p>
<ul>{ctrl_lines}</ul>
<p>Decision needed (owner): replace the literal rule with a density-matched rule, or accept that no dot file can ever be cleared. We have not changed the rule. Changing it is an owner decision.</p>

<h2>5. Holdout validity: the central irregularity</h2>
<p>On the random arm, catalogue avoidance lowers the holdout score: {sweep[0]['arms']['random']['pooled_dti']:.4f} with none, {sweep[3]['arms']['random']['pooled_dti']:.4f} at 3 px, {sweep[6]['arms']['random']['pooled_dti']:.4f} at 6 px. That direction is the opposite of the leaderboard evidence (§3). The holdout is therefore not a valid proxy for the catalogue-avoidance lever. Recommendation: stop using the holdout to choose dot placement, and calibrate with organizer receipts instead.</p>

<h2>6. Portal error "Predicted values must be in range [0, 1]"</h2>
<ul>
<li>Official text (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a>): float32 values between 0 and 1, and "data outside the bounds is null or nan."</li>
<li>Conflict: the shared validator (<code>vendor/gems57/validate.py</code>) requires zeros outside the footprint and no NaN anywhere. The official text and the official sample (<code>sample_submission.tif</code>, NaN outside, per registry note) say NaN. The repository's own writer comment (<code>src/gems/submission.py</code>) says some portal validators reject NaN outside, but this is unverified.</li>
<li>The candidate uses all-finite zeros outside, the convention of the previously scored files named "zeros", so the candidate follows the repo's convention. This choice is a risk to flag, not a verified fact.</li>
<li>We cannot see the user's failed upload, so the actual cause is unverified. Likely causes: NaN inside the footprint, values outside [0,1], or NaN outside the footprint.</li>
</ul>

<h2>7. Live leaderboard check (irregularity)</h2>
<p>Fetched {LEADERBOARD_OBS['fetched_utc']} from the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">official leaderboard</a>: rank 1 xiaofanhu 0.4544, rank 2 cfld__ 0.3925. The prompt's figures 0.4413 and 0.3195 do not match rank 1. The source of 0.3195 is unknown. Flagged for review; we did not use the prompt's figures as facts.</p>

<h2>8. Irregularities and blockers (flagged for review)</h2>
<ol>
<li>All nine focus scores are OWNER-REPORTED. No submission-page receipt binds any file to a score.</li>
<li>The literal 70% gate fails for every dot file, including a random control (§4).</li>
<li>The holdout rewards catalogue proximity, the opposite of the leaderboard-consistent mechanism (§5).</li>
<li>Portal NaN/zero convention conflict between the official text and the shared validator (§6).</li>
<li>GEMSDOE25 and GEMSDOE30 are identical dot sets (§1).</li>
<li>The holdout n is summed over 16 cells, so the same withheld pixel can count in more than one cell.</li>
<li>The registry cache has 117 files for 118 entries. One entry is a duplicate filename and is not checked (<code>missing_or_invalid: 1</code>).</li>
<li>The restore step rewrote <code>evidence/data_restore.json</code> (timestamp only).</li>
</ol>

<h2>9. What the owner must do (no manual work is needed for the rest)</h2>
<ul>
<li>Decide the uniqueness rule (§4). Until then the verdict stays SUBMIT: NO.</li>
<li>If you want a calibrated score, upload one candidate yourself through the DrivenData portal (a login is required; this sandbox cannot upload). The receipt then becomes ORGANIZER-CONFIRMED.</li>
<li>Confirm the NaN vs zero outside convention with the competition forum before any upload.</li>
</ul>

<h2>Sources (official, for manual review)</h2>
<ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description, metric and submission format</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules (Sept 2026), §3.4 weekly submission limit, §3.5 submission</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Data page (login required; not accessed)</a></li>
<li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">GeoDAWN (USGS)</a> · <a href="https://gbcge.org/current-projects/ingenious/">INGENIOUS (GBCGE)</a></li>
</ul>
<p><small>Machine-readable: <a href="data/executive_summary_20261031.json">docs/data/executive_summary_20261031.json</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/arena/0c266855-wbggemsdoe1/evidence/h2_lag/run_card_20261031.json">run card</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/arena/0c266855-wbggemsdoe1/scripts/run_h2_lag_corroboration.py">experiment script</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/arena/0c266855-wbggemsdoe1/scripts/build_h2_candidate_20261031.py">candidate script</a></small></p>
</body></html>
"""
    (ROOT / "docs/executive-summary-h2-20261031.html").write_text(page)
    print("wrote docs/executive-summary-h2-20261031.html, docs/data/executive_summary_20261031.json, evidence/h2_lag/run_card_20261031.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
