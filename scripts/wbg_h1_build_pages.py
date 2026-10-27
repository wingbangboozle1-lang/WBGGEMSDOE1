#!/usr/bin/env python3
"""Publish a corrected WBG-H1 summary; never rerun inherited science.

Frozen source receipts remain available for audit, including unsupported claims.
Only the publication layer is corrected. No private evaluator/writer or forecast.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "docs/wbg-h1-dpgf1"
    (out / "data").mkdir(parents=True, exist_ok=True)
    rc = json.loads((ROOT / "evidence/wbg_h1/run_card.json").read_text())
    overlap_witness = rc["registry_correlation_and_overlap"]["literal_oneway_vs_r13_space_filling_lattice_ir_wbg1_01"]
    if rc["verdict"] != "negative" or overlap_witness <= .70:
        raise ValueError("frozen WBG-H1 negative/literal-overlap decision changed; review before publishing")
    paths = rc["raster_sha256"]
    for kind in ("tif", "zip"):
        path = (ROOT / paths[f"{kind}_file"]).resolve()
        if not path.is_relative_to((ROOT / "docs/downloads").resolve()) or not path.is_file():
            raise ValueError(f"frozen WBG-H1 {kind} download missing or outside public downloads")
        with path.open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != paths[f"{kind}_sha256"]:
                raise ValueError(f"frozen WBG-H1 {kind} bytes differ from source run card")
    with zipfile.ZipFile(ROOT / paths["zip_file"]) as bundle:
        if bundle.namelist() != [Path(paths["tif_file"]).name]:
            raise ValueError("frozen WBG-H1 ZIP must contain exactly its TIFF")
        if hashlib.sha256(bundle.read(bundle.namelist()[0])).hexdigest() != paths["tif_sha256"]:
            raise ValueError("frozen WBG-H1 ZIP payload differs from exact TIFF")
    # Preserve raw receipts as historical evidence, not as approved conclusions.
    for name in ("run_card.json", "forensic_proof_02778.json"):
        source = ROOT / "evidence/wbg_h1" / name
        shutil.copyfile(source, out / "data" / name)
    h = rc["holdout_dti"]
    overlap = rc["registry_correlation_and_overlap"]
    tif = Path(rc["raster_sha256"]["tif_file"]).name
    esc = html.escape
    body = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WBG-H1 — corrected negative-result summary</title><link rel="stylesheet" href="../assets/style.css"></head>
<body><a class="skip" href="#main">Skip to content</a><main id="main" class="wrap review-page">
<nav><a href="../index.html">Research desk</a> · <a href="../executive-summary.html">Nine-site executive summary</a> ·
<a href="../release-review.html">All local download decisions</a></nav>
<h1>WBG-H1 / DPGF-1: negative result</h1>
<section class="notice"><h2>DOWNLOAD: YES (research only). SUBMIT: NO.</h2>
<p>The inherited TIFF is retained for reproducibility. Local format validation is not organizer acceptance,
scientific promotion or permission to spend a weekly slot. Do not upload it as an optional benchmark.</p>
<a class="button" href="../downloads/{esc(tif)}" download>Download frozen research TIFF ↓</a>
<p><a href="../data/release-review.json">Automatic exact-file validation and decision report</a></p></section>
<h2>Measured evidence, not a leaderboard estimate</h2>
<p><strong>HOLDOUT-DTI {h['dti']:.6f}</strong>; 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}];
evaluator <code>{esc(h['evaluator_version'])}</code>; {h['n_withheld_positives']:,} withheld positives.
This is an inherited measurement, not rerun on 2026-10-27.</p>
<p>Matched B0 control: <strong>HOLDOUT-DTI {h['baseline_b0_dti']:.6f}</strong>;
95% CI [{h['baseline_b0_ci95'][0]:.6f}, {h['baseline_b0_ci95'][1]:.6f}], same evaluator and positives.
Paired delta: <strong>HOLDOUT-DTI {h['paired_delta_vs_b0']:+.6f}</strong>;
95% CI [{h['paired_delta_vs_b0_ci95'][0]:+.6f}, {h['paired_delta_vs_b0_ci95'][1]:+.6f}].
A lift against B0 does not prove a win against the current best or hidden leaderboard.</p>
<p>Leaderboard estimate: <strong>unavailable</strong>. Artifact-linked organizer receipt: <strong>none supplied</strong>.</p>
<h2>Literal uniqueness: FAILED</h2>
<p>Recorded final-dot forward overlap with the registry lattice within 3 px is
<strong>{overlap['literal_oneway_vs_r13_space_filling_lattice_ir_wbg1_01']*100:.4f}%</strong>, exceeding 70%.
The recorded slab overlap is {overlap['literal_oneway_vs_516k_continuous_slabs_ir_wbg1_03']*100:.2f}%.
Sparse-only overlap ({overlap['focus9_sites_max_3px_dot_overlap']*100:.2f}%) and symmetric overlap
are diagnostics, not authorized replacements for the literal forward gate. No lattice exemption applies.</p>
<p>The recorded pre-placement |Spearman| is {overlap['pre_placement_surface_max_abs_spearman']:.6f},
but this does not certify a complete pre-placement forward-overlap pass.
Different TIFF bytes do not establish lane uniqueness.</p>
<h2>Correction of inherited claims</h2>
<ul><li>GEMSDOE32's historical 0.2778 is <strong>USER-REPORTED / NOT ORGANIZER-CONFIRMED</strong> here.
The exact nested raster identity is useful learning evidence; it cannot prove the hidden-label cause of the reported gain.</li>
<li>The claimed private fault count, private recall and recall targets from lattice inversion are not established.
For binary dots, DTI = T / [0.2(T + N − M) + 0.8K]. T and M sum coverage over different sets;
a global lattice mean does not determine its value on unknown test faults.</li>
<li>The inherited LLI forecast is not published as an estimated score: its claimed organizer-confirmed training values
lack receipts, and no untouched validation establishes its applicability to a new geological lane.</li>
<li>The exact organizer portal implementation and the cause of the originally rejected upload are unknown.
The conservative all-finite [0,1] export avoids NaN/range risks locally; it cannot guarantee acceptance.</li>
<li>Cross-evaluator numbers must not be ranked as a common holdout result. A fault-prediction raster is not proof of geothermal vents.</li></ul>
<h2>Identity and traceability</h2>
<p>SHA-256: <code>{esc(rc['raster_sha256']['tif_sha256'])}</code></p>
<p>Recorded name: <code>{esc(rc['submission_name'])}</code></p>
<p>Research note (not upload authorization): <code>WBG-H1 frozen dip-projection experiment; literal overlap FAILED; research download only; DO NOT SUBMIT.</code></p>
<h2>Evidence and next action</h2>
<p><a href="data/run_card.json">Original inherited run card</a> ·
<a href="data/forensic_proof_02778.json">Original forensic claims (not accepted conclusions)</a> ·
<a href="../review-20261027.md">Dated review and limitations</a> ·
<a href="../how-to-submit.html">Future submission procedure</a></p>
<p>Keep frozen scientific modules, source cards, TIFF bytes and negative results. Do not tune a stopped lane or
relocate dots into lattice holes. A distinct assigned lane and clean paired benchmark are prerequisites to new research.
No experiments were rerun and no competition slots were used in this review.</p>
</main></body></html>'''
    for name in ("index.html", "executive-summary.html"):
        (out / name).write_text(body, encoding="utf-8")
    print("Built corrected WBG-H1 negative-result pages; frozen numerical evidence unchanged.")


if __name__ == "__main__":
    main()
