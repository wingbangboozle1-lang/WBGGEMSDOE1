#!/usr/bin/env python3
"""Publish the frozen DPGF-1 result with the literal protocol and evidence labels.

Do not republish the inherited private-label inversion or LLI projection as
verified science. Frozen cards and figures remain available for provenance;
this entry point never alters a model, measurement, artifact or slot decision.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "docs/wbg-h1-dpgf1"
    (out / "data").mkdir(parents=True, exist_ok=True)
    # Keep exactly the original downloadable evidence set. Raw cards are historical,
    # not normalized approval or score forecasts.
    for name in ("run_card.json", "experiment_ledger.json"):
        source = ROOT / "evidence/wbg_h1" / name
        if source.exists():
            shutil.copyfile(source, out / "data" / name)
    card = json.loads((ROOT / "evidence/wbg_h1/run_card.json").read_text())
    h = card["holdout_dti"]
    registry = card["registry_correlation_and_overlap"]
    tif = Path(card["raster_sha256"]["tif_file"]).name
    zipname = Path(card["raster_sha256"]["zip_file"]).name
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>DPGF-1 frozen negative result · WBG GEMS</title>
<link rel="stylesheet" href="../assets/style.css"></head><body><header class="wrap"><nav>
<a href="../index.html">Research desk</a> · <a href="../portfolio-review.html">All-release review</a> · <a href="../executive-summary.html">Nine-site summary</a></nav></header>
<main class="wrap" id="main"><h1>WBG-H1 / DPGF-1 — frozen negative result</h1>
<div class="alert"><p><strong>DOWNLOAD: YES, research only. SUBMIT: NO. DO NOT SUBMIT.</strong>
Format-valid does not mean scientifically promoted, lane-unique or organizer-accepted.</p></div>
<h2>Exact research artifact</h2><p><a class="button" href="../downloads/{escape(tif)}" download>Download research TIFF</a> ·
<a href="../downloads/{escape(zipname)}" download>One-TIFF ZIP</a></p>
<p class="filename">{escape(tif)}<br>SHA-256: {card['raster_sha256']['tif_sha256']}</p>
<p>Name: <code>{escape(card['submission_name'])}</code><br>Original note (historical, not approval): {escape(card['submission_note'])}</p>
<h2>Recorded holdout, not a leaderboard forecast</h2><p><strong>HOLDOUT-DTI {h['dti']:.6f}</strong>,
95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}], evaluator <code>{escape(h['evaluator_version'])}</code>,
{h['n_withheld_positives']:,} withheld positives. This is a frozen measurement, not a new experiment.</p>
<p>Matched B0: HOLDOUT-DTI {h['baseline_b0_dti']:.6f}, 95% CI [{h['baseline_b0_ci95'][0]:.6f}, {h['baseline_b0_ci95'][1]:.6f}],
same evaluator/positives. Paired difference: HOLDOUT-DTI +{h['paired_delta_vs_b0']:.6f},
95% CI [{h['paired_delta_vs_b0_ci95'][0]:.6f}, {h['paired_delta_vs_b0_ci95'][1]:.6f}].
A positive matched-baseline difference is not a verified win over the current same-instrument portfolio best.</p>
<h2>Literal uniqueness: FAIL</h2><p>Recorded one-way 3 px overlap with the registered lattice:
<strong>{registry['literal_oneway_vs_r13_space_filling_lattice_ir_wbg1_01']*100:.4f}%</strong>.
Recorded one-way overlap with a dense slab: {registry['literal_oneway_vs_516k_continuous_slabs_ir_wbg1_03']*100:.2f}%.
Both exceed 70%. Sparse-only and symmetric overlap do not replace the user's all-registry forward-overlap gate.
No lattice or density exemption was authorized. These are frozen registry measurements; no fresh full-registry clearance is claimed.</p>
<h2>Corrections to inherited interpretation</h2><ul>
<li>GEMSDOE32's historical 0.2778 and other supplied artifact values are USER-REPORTED / NOT ORGANIZER-CONFIRMED. No receipt identifies these exact bytes and a result.</li>
<li>No verified leaderboard estimate exists for this TIFF. The inherited LLI regression used unverified historical claims; its projection is not a validated forecast.</li>
<li>One rounded lattice result plus an assumed average kernel response does not identify the private fault count, private recall, or locations of hidden faults. The inherited private-count inversion is not verified evidence.</li>
<li>Catalogue-distance pruning offers a plausible efficiency explanation; private-label causality cannot be proved from these files.</li>
<li>All local format checks passing is not a guarantee about the live portal. The cause of the original range rejection cannot be reconstructed without its exact bytes.</li></ul>
<h2>How a future approved submission would work</h2><p>There is no eligible file now. Do not upload this negative result for optional testing.
Follow the <a href="../how-to-submit.html">future submission guide</a> only after same-instrument efficacy,
canaries, literal surface and final-dot uniqueness, provenance, and saved-file checks pass, and a separate selector approves a slot.</p>
<p><a href="../portfolio-review.html">All four reopened files and current blockers</a> ·
<a href="data/run_card.json">Frozen original card (contains superseded interpretation; read corrections above)</a> ·
<a href="../data/portfolio-review.json">Current review JSON</a></p>
</main></body></html>'''
    for name in ("index.html", "executive-summary.html"):
        (out / name).write_text(html)
    print("Built corrected, fail-closed DPGF-1 result pages; preserved frozen evidence and artifacts.")


if __name__ == "__main__":
    main()
