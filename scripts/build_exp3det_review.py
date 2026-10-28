#!/usr/bin/env python3
"""Build the parallel EXP3DET negative review from its forensic receipt."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

from build_site import page

ROOT = Path(__file__).resolve().parents[1]


def build() -> None:
    result = json.loads((ROOT / "evidence/wbg3/exp3det_safety_review_20261027.json").read_text())
    old = json.loads((ROOT / "evidence/wbg3/run_card.json").read_text())
    if (result["verdict"] != "negative" or result["ok_to_submit"] is not False
            or result["witness"]["my_dots_within_3px_of_theirs"] <= 0.70
            or result["leaderboard_estimate"] is not None
            or old["raster_sha256"] != result["raster_sha256"]):
        raise ValueError("EXP3DET forensic STOP receipt is missing or inconsistent")
    h, w, v = result["holdout"], result["witness"], result["validator"]
    file = Path(result["artifact"]).name
    overlap = 100 * w["my_dots_within_3px_of_theirs"]
    body = f'''<section class="hero"><div><p class="eyebrow">Parallel WBG-3 · EXP3DET · forensic review</p><h1>A measured result.<br><em>Not a submission.</em></h1><p class="lead"><strong>DOWNLOAD: YES for research. SUBMIT: NO.</strong> The already-placed dots meet a decisive literal registry STOP. The prior numerical leaderboard projection is withdrawn; no reliable leaderboard estimate or artifact-linked organizer score is available.</p><div class="actions"><a class="button secondary" href="wbg3/index.html">Compare SPI-PMR result →</a><a class="text-link" href="how-to-submit.html">Submission requirements →</a></div></div>
<aside class="download-card" aria-label="Research file and decision"><div class="card-top"><div class="file-icon">.TIF</div><div class="file-label">WBG-3 · EXP3DET<small>Existing frozen dots · research only</small></div><span class="pill no">DO NOT SUBMIT</span></div><div class="card-body"><div class="status-line"><span>Local format recheck</span><b>PASS · not portal acceptance</b></div><div class="status-line"><span>Literal C1 3 px overlap</span><b>{overlap:.1f}% · STOP</b></div><div class="status-line"><span>Live slot authorization</span><b>NO</b></div><div class="filename">{escape(file)}</div><a class="button" href="downloads/{escape(file)}" download>Download research TIFF ↓</a><p class="micro"><a href="downloads/{escape(file[:-4])}.zip" download>One-TIFF research ZIP ↓</a> · SHA-256 <code>{result['raster_sha256']}</code></p></div></aside></section>
<section class="content-section"><div class="alert"><p><strong>Negative result; no selector eligibility.</strong> The original nine-focus-artifact comparison was a partial diagnostic, not an all-registry pass. One valid counterexample is decisive. The literal rule does not exempt dense surfaces. This forensic remeasurement used existing files only; no new model, placement or competition slot.</p></div></section>
<section class="stats"><div class="stat"><label>Recorded HOLDOUT-DTI</label><div class="value">{h['dti']:.6f}</div><p>{escape(h['evaluator_version'])} · {h['withheld_positive_pixels']:,} positives<br>95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]</p></div><div class="stat"><label>Benchmark</label><div class="value">0.166060</div><p>Same-evaluator S3DEP1 comparison recorded in the historical card. EXP3DET trails it.</p></div><div class="stat"><label>Literal registry witness</label><div class="value bad">{overlap:.1f}%</div><p>Forward Euclidean overlap with C1; &gt;70% is STOP. Full-footprint dot Spearman {w['spearman_full_footprint']:.4f}.</p></div><div class="stat"><label>Leaderboard estimate</label><div class="value word">Unknown</div><p>Two-anchor projection withdrawn; hidden labels and receipts unavailable.</p></div></section>
<section class="content-section prose"><h2>What was checked</h2><ul><li>The exact TIFF has SHA-256 <code>{result['raster_sha256']}</code>, one float32 band, EPSG:32611, shape 3730 × 3292, transform <code>(100, 0, 243350, 0, -100, 4508550)</code>, range [{v['whole_array_min']:.1f}, {v['whole_array_max']:.1f}], and no NaN, infinity or masked interior pixel. The ZIP contains the same TIFF bytes. These are local checks against an owner mirror, not an organizer acceptance guarantee.</li><li><code>{w['their_dots']:,}</code> positive C1 cells are the registered witness under the literal finite-positive support rule. The overlap check uses the shared Euclidean 3-pixel gate, against <strong>one</strong> witness; it is not a complete inventory. It does not imply the methods copied each other.</li><li>The earlier nine-focus-file scan reported maximum forward overlap 45.06% and sampled Spearman |ρ| 0.03595 within that limited scope. It cannot override C1. A qualifying pre-placement overlap check is not established.</li><li>Our local all-finite exterior policy conflicts with the public specification's null/NaN exterior wording. The cause of the reported portal range error is unknown; no actual portal test was performed.</li><li>Fault likelihood is not evidence of a geothermal vent or a confirmed resource.</li></ul>
<p>Audit metadata (not upload instructions): name <code>{escape(result['submission_name'])}</code>; note <code>{escape(result['submission_note'])}</code> ({len(result['submission_note'])}/140 characters).</p><p><a href="data/exp3det-safety-20261027.json">Current forensic receipt ↗</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/main/evidence/wbg3/run_card.json">Historical run card (projection superseded) ↗</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official task and format ↗</a></p></section>'''
    (ROOT / "docs/wbg3.html").write_text(page("wbg3.html", "EXP3DET forensic review", body), encoding="utf-8")
    md = f'''# WBG-3 EXP3DET — forensic review (27 October 2026)

**DOWNLOAD: YES, research only. SUBMIT: NO.** The original model projection is withdrawn: a calibrated leaderboard estimate and artifact-linked organizer score are unavailable.

- Existing file: [`{file}`](downloads/{file}); SHA-256 `{result['raster_sha256']}`. No new training or dot placement was performed.
- Recorded **HOLDOUT-DTI {h['dti']:.6f}**, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}], `{h['evaluator_version']}`, {h['withheld_positive_pixels']:,} withheld positives; below the recorded same-evaluator S3DEP1 benchmark 0.166060. Historical result was not rerun here.
- **Literal duplicate STOP:** {overlap:.1f}% forward 3-pixel Euclidean overlap with registered WBG-C1 (SHA-256 `{w['sha256']}`); full-footprint dot Spearman {w['spearman_full_footprint']:.6f}. One witness proves the gate failure, not a complete registry audit or copying. A qualifying pre-placement overlap check is not established.
- Prior nine-focus-artifact diagnostic: maximum forward overlap 45.06%, sampled max |ρ| 0.03595; this restricted result cannot establish global uniqueness.
- Local exact-file preflight: one float32 band; EPSG:32611; 3730 × 3292; transform `(100, 0, 243350, 0, -100, 4508550)`; range [0,1]; zero NaN, infinity or masked interior pixels; ZIP contains the exact TIFF. Reference is an integrity-pinned owner mirror, not independently authenticated organizer data. Local format pass does not prove portal acceptance.
- Name `{result['submission_name']}`; note `{result['submission_note']}` ({len(result['submission_note'])}/140 characters). These identify research evidence, not an approved upload.
- No real submission was selected, no weekly slot was used, and remaining account allowance is unknown. Fault likelihood does not establish a geothermal resource or vent.

[Current machine-readable forensic receipt](data/exp3det-safety-20261027.json) · [Historical card (its old projection and partial uniqueness are superseded)](https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/main/evidence/wbg3/run_card.json) · [Official problem and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
'''
    (ROOT / "docs/wbg3-executive-summary.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    build()
