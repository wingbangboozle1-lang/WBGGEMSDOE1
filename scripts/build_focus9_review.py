#!/usr/bin/env python3
"""Build the Focus-9 page from frozen source cards and the current STOP review."""
from html import escape
import json
from pathlib import Path

from build_site import page, pill

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def main():
    focus = load("evidence/focus9_exec/safety_review_20261028.json")
    if focus["verdict"] != "negative" or focus["ok_to_submit"] is not False:
        raise ValueError("Focus-9 must remain a negative research null")
    tif = Path(focus["artifact"]).name
    bound = load("evidence/lattice_coverage_certificate.json")["fixed_budget_overlap_bound"]["minimum_overlap_fraction"]
    rows = load("evidence/nine_site_audit.json")["rows"]
    ordered = {row["site"]: row for row in rows}
    sites = [f"GEMSDOE{i}" for i in (24, 25, 27, 28, 30, 31, 32, 33, 36)]
    if len(rows) != 9 or set(ordered) != set(sites):
        raise ValueError("nine-site inventory changed")
    table = "".join(
        f'<tr><td><strong>{escape(site)}</strong></td>'
        f'<td><a href="{escape(ordered[site]["immutable_file_url"], quote=True)}">{escape(ordered[site]["file"])}</a></td>'
        f'<td><strong>{ordered[site]["reported_historical_value"]:.4f}</strong><br><span class="micro">USER-REPORTED, unverified</span></td>'
        '<td>Unavailable</td><td>Historical research only; do not copy or submit.</td></tr>'
        for site in sites
    )
    overlap = focus["witness"]["my_dots_within_3px_of_theirs"] * 100
    body = f'''<section class="subhero"><div><p class="eyebrow">Nine-site audit · 27–28 October 2026</p><h1>Evidence before<br><em>the next slot.</em></h1><p class="lead">The highest supplied historical claim is GEMSDOE32 B2 at 0.2778. It is USER-REPORTED, not an organizer-confirmed receipt. No defensible leaderboard estimate exists for a new file.</p></div>
<aside class="download-card" aria-label="Focus-9 research-only TIFF"><div class="card-top"><div class="file-icon" aria-hidden="true">.TIF</div><div class="file-label">Focus-9 random null<small>Research only, not a geological model</small></div>{pill('DO NOT SUBMIT', 'no')}</div><div class="card-body"><div class="status-line"><span>HOLDOUT-DTI</span><b>Not measured</b></div><div class="status-line"><span>Literal C1 overlap</span><b>{overlap:.0f}% · STOP</b></div><div class="status-line"><span>Slot / selector eligibility</span><b>NO</b></div><div class="filename">{escape(tif)}</div><a class="button" href="downloads/{escape(tif)}" download><span>Download research TIFF</span><span aria-hidden="true">↓</span></a><div class="under-download"><span>float32 · EPSG:32611</span><a href="downloads/{escape(tif[:-4])}.zip" download>ZIP ↓</a></div><p class="micro">SHA-256 <code>{focus['raster_sha256']}</code></p></div></aside></section>
<div class="alert"><p><strong>DOWNLOAD: YES (research only) — SUBMIT: NO.</strong> No file in this repository is approved. The random null has no geological mechanism, no measured holdout and no leaderboard estimate. No model or dots were generated in this integration, and no competition slot was used.</p></div>
<section class="content-section"><h2>Why this file is negative</h2><div class="three-col"><article class="mini-card"><span class="index">LOCAL FORMAT</span><h3>Checks pass, not portal acceptance</h3><p>One float32 band; EPSG:32611; 3,730 × 3,292; 100 m transform; all finite in [0,1]; no masked interior pixels. The one-member ZIP matches exact TIFF bytes. The organizer describes null/NaN exterior; this file uses zeros. The old range error's cause is unknown.</p></article><article class="mini-card"><span class="index">ONE DECISIVE WITNESS</span><h3>{overlap:.0f}% overlaps C1</h3><p>Existing dots measured within 3 px of the registered C1 surface; the protocol stops above 70%. The r13 fixed-budget lower bound is {bound*100:.3f}%. Neither a sparse-only exemption nor the lower-bound argument proves a universal block for every budget.</p></article><article class="mini-card"><span class="index">SCOPED HASH CHECK</span><h3>Different bytes ≠ novelty</h3><p>No byte match in 377 recorded source paths and no decoded hash match among 360 recorded comparison rows. This is a historical hash-table lookup, not a full registry remeasurement; competing-sparse overlap is unmeasured and no pre-placement clearance is established.</p></article></div><p><a href="data/focus9-safety-20261028.json">Current forensic receipt ↗</a> · <a href="data/focus9-run-card.json">Original card (historical; corrections supersede its decoded hash and unmeasured expectations) ↗</a></p></section>
<section class="content-section" id="master-table"><h2>Nine sites, nine reported values</h2><p>Artifact links are immutable owner-repository snapshots for research; none supplies a verified organizer receipt. Values are not new-file scores or projections.</p><div class="table-wrap"><table><thead><tr><th>Site</th><th>Historical file</th><th>Highest supplied value</th><th>New-file estimate</th><th>Decision</th></tr></thead><tbody>{table}</tbody></table></div><p>GEMSDOE25 and GEMSDOE30 contain identical decoded predictions. GEMSDOE32 B2 is a strict subset of its D2.8 parent: 6,436 pixels removed, none added. Reduced catalogue-near false positives is a plausible explanation for 0.2778, not proof of hidden-label causation or a novel geothermal discovery. <a href="wbg3/forensics-and-hypotheses.html">Read full forensics ↗</a></p></section>
<section class="content-section"><h2>What the measured results actually say</h2><p>The parallel EXP3DET recorded <strong>HOLDOUT-DTI 0.138233</strong>, 95% CI [0.125701, 0.151956], <code>gems-segment-pooled-v1</code>, 60,988 withheld positives; it is below the historical 0.166060 benchmark and overlaps C1 by 100%. SPI-PMR recorded <strong>HOLDOUT-DTI 0.118180</strong>, CI [0.103658, 0.132432], same evaluator and positive count; it also fails the literal overlap rule. These are local results, not organizer scores. The Focus-9 random null has <strong>no measured HOLDOUT-DTI</strong>. <a href="wbg3.html">EXP3DET evidence ↗</a> · <a href="wbg3/index.html">SPI-PMR evidence ↗</a></p></section>
<section class="content-section prose"><h2>Next steps, not an upload instruction</h2><ol><li>Have a shared-template maintainer repair the reproduced interior-mask bug upstream; this repository's common integration guard is a local mitigation only.</li><li>Resolve the registry protocol and obtain a designated lane without carving out convenient exceptions. Confirm organizer-origin data and the feature metadata.</li><li>Consider the <a href="research/future-hypotheses-20261027.md">four ranked, untested hypotheses</a> only after authorization. Pre-register, run a leakage canary and both required uniqueness checks, then compare blocked holdout with a reproducible current best.</li><li>Only a separate selector with verified account allowance can authorize a slot after every gate passes. <a href="how-to-submit.html">Read the future submission guide ↗</a></li></ol><p>Fault prediction is not a verified geothermal vent or economic resource. Official sources: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">competition task and metric</a>, <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">DOE rules</a>, <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a>, and <a href="https://gdr.openei.org/submissions/1391">DOE INGENIOUS catalog</a>.</p></section>'''
    (ROOT / "docs/focus9-executive-summary.html").write_text(page("focus9-executive-summary.html", "Focus-9 Executive Summary", body))


if __name__ == "__main__":
    main()
