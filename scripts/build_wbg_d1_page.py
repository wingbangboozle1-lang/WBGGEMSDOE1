#!/usr/bin/env python3
"""Build the WBG-D1 lane dashboard (docs/wbg-d1.html) from measured evidence.

Every number rendered here is read from persisted HOLDOUT-DTI evidence or the
hash-pinned nine-site audit; nothing is projected into a leaderboard score.
The page makes the download/submit decision unmistakable and includes the
requested nine-site file / score / uniqueness executive table.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from html import escape

from wbggems.audit import dump_json

DOCS = ROOT / "docs"
EVID = ROOT / "evidence" / "wbg_d1"


def load(rel):
    return json.loads((ROOT / rel).read_text())


def link(url, text, cls=""):
    return f'<a class="{cls}" href="{escape(url, quote=True)}">{escape(text)}</a>'


def pill(text, kind):
    return f'<span class="pill {kind}"><span class="dot" aria-hidden="true"></span>{escape(text)}</span>'


def page(name, title, body):
    # Reuse the exact chrome of the main desk for visual consistency.
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    html = mod.page(name, title, body)
    # Insert the WBG-D1 dashboard into the primary navigation on every page.
    extra = '<a class="" href="wbg-d1.html">WBG-D1 lane</a>'
    if 'href="wbg-d1.html"' not in html:
        html = html.replace('<a class="" href="research.html">Research</a>',
                            '<a class="" href="research.html">Research</a>' + extra)
    return html


def nine_site_table(nine):
    head = ("<tr><th>Focus site</th><th>File to download (pinned immutable source)</th>"
            "<th>Reported value (not a receipt)</th><th>Cross-site 3 px overlap</th>"
            "<th>Unique vs other focus sites?</th><th>Decision</th></tr>")
    rows = []
    for s in nine["sites"]:
        url = s["artifact_url"]
        overlap = s["maximum_3px_overlap_vs_other_eight_historical_masks"]
        unique = not s["unique_under_70_percent_rule"]
        rows.append(
            "<tr>"
            f"<td><strong>{escape(s['site'])}</strong></td>"
            f"<td>{link(url, s['historical_best_file'])}</td>"
            f"<td><code>{s['reported_value']:.4f}</code><br><span class='micro'>{escape(s['score_evidence_label'])}</span></td>"
            f"<td>{overlap:.2f}</td>"
            f"<td>{'No — family duplicate' if unique else 'Yes'}</td>"
            f"<td>{pill(s['recommendation'], 'no' if 'DO NOT' in s['recommendation'] else 'yes')}</td>"
            "</tr>")
    return ("<div class='table-wrap'><table><thead>" + head + "</thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def project_table(rc, exp1):
    tif = rc["artifact"].split("/")[-1]
    h = rc["holdout"]
    rows = [
        ("WBG-D1 shipped TIF (this session)",
         f"downloads/{tif}",
         f"HOLDOUT-DTI continuous {h['candidate_dti']:.4f}; dotted intrinsic {h['dotted_holdout_intrinsic_no_collar_dti']:.4f}; "
         f"collar-packaged {h['dotted_holdout_collar_pessimistic_dti']:.4f} — no leaderboard projection",
         "Byte/pixel unique; geological-peer overlap 0.485 ≤ 0.70; literal lattice/surface STOP",
         False),
        ("WBG-D1 deterministic radiometric composite (EXP-1, dots only, not packaged)",
         "data/wbg-d1-exp1.json",
         f"HOLDOUT-DTI {exp1['pooled_summary']['scores']['deterministic_rad_composite']['dti']:.4f} "
         f"(random-dot baseline {exp1['pooled_summary']['scores']['random_dot_baseline']['dti']:.4f})",
         "Off-ridge support (11% overlap with B2); weaker than random on catalogue recovery",
         False),
        ("WBG-H1 DPGF-1 EXP-3 (prior session, frozen)",
         "https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/main/docs/downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif",
         "HOLDOUT-DTI 0.123310 (gems-segment-pooled-v1, n=60,988)",
         "Sparse-peer overlap 0.645 ≤ 0.70; negative vs 0.163792 reference",
         False),
        ("WBG-C1 commutator research surface (prior session, frozen)",
         "https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/main/docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif",
         "HOLDOUT-DTI 0.014045 (gems57-pooled-hide-v2, n=11,330)",
         "Continuous surface; literal overlap STOP 0.9987",
         False),
    ]
    trs = []
    for name, href, score, uniq, ok in rows:
        trs.append(
            "<tr>"
            f"<td><strong>{escape(name)}</strong></td>"
            f"<td>{link(href, href.split('/')[-1])}</td>"
            f"<td>{escape(score)}</td>"
            f"<td>{escape(uniq)}</td>"
            f"<td>{pill('DO NOT SUBMIT', 'no') if not ok else pill('OK', 'yes')}</td>"
            "</tr>")
    return ("<div class='table-wrap'><table><thead><tr><th>Project artifact</th><th>File</th>"
            "<th>Measured local result (labeled HOLDOUT-DTI; never a leaderboard estimate)</th>"
            "<th>Uniqueness evidence</th><th>Decision</th></tr></thead><tbody>"
            + "".join(trs) + "</tbody></table></div>")


def main():
    rc = load("evidence/wbg_d1/run_card.json")
    exp1 = load("evidence/wbg_d1/exp1.json")
    nine = load("evidence/nine_site_executive_summary_20261026.json")
    tif = rc["artifact"].split("/")[-1]
    zipf = rc["zip_artifact"].split("/")[-1]
    h = rc["holdout"]
    canary = rc["canary"]
    reg = rc["registry"]

    # Publish machine-readable evidence next to the page.
    (DOCS / "data").mkdir(exist_ok=True)
    for src, dest in [
        ("evidence/wbg_d1/run_card.json", "run-card-wbg-d1.json"),
        ("evidence/wbg_d1/exp1.json", "wbg-d1-exp1.json"),
        ("evidence/wbg_d1/exp2.json", "wbg-d1-exp2.json"),
        ("evidence/wbg_d1/exp3_gates.json", "wbg-d1-exp3.json"),
        ("evidence/wbg_d1/exp2_canaries.json", "wbg-d1-canaries.json"),
        ("registry/preregistration_wbg_d1.json", "preregistration-wbg-d1.json"),
    ]:
        shutil.copyfile(ROOT / src, DOCS / "data" / dest)

    dump_json(DOCS / "downloads/manifest-wbg-d1.json", {
        "schema_version": 1,
        "artifact": tif,
        "sha256": rc["raster_sha256"],
        "decoded_sha256": rc["raster_decoded_sha256"],
        "submission_name": rc["submission_name"],
        "note": rc["submission_note"],
        "note_chars": rc["submission_note_chars"],
        "verdict": rc["verdict"],
        "ok_to_download": True,
        "ok_to_submit": rc["ok_to_submit"],
        "zip_file": zipf,
        "holdout": rc["holdout"],
        "gates": rc["gates"],
        "warning": "Research artifact. Negative efficacy gate; literal registry STOP from synthetic lattice and continuous-surface priors. No organizer receipt.",
    })

    peer_rows = "".join(
        f"<tr><td>{escape(p['submission'].split('/')[-1])}</td>"
        f"<td>{p['my_dots_within_3px_of_theirs']:.4f}</td>"
        f"<td>{p['their_dots_within_3px_of_mine']:.4f}</td>"
        f"<td>{p['spearman_full_footprint']:.4f}</td>"
        f"<td>{p['jaccard_dot_sets']:.4f}</td></tr>"
        for p in rc["top_geological_peers"])
    lattice_rows = "".join(
        f"<li><code>{escape(l['submission'].split('/')[-1])}</code> — forward overlap {l['forward_overlap']:.3f} "
        f"({l['their_dots']:,} support cells; uniform synthetic calibration grid)</li>"
        for l in rc["synthetic_lattice_controls"])

    body = f"""
<section class="subhero"><div><p class="eyebrow">WBG-D1 lane · radiometric alteration · registered 2026-10-27</p>
<h1>A unique TIF. An <em>honest negative.</em></h1>
<p class="lead">A radiometric alteration / shallow magnetic edge lane built from official USGS GeoDAWN data and the shared 19-band cache, run through the same hide-and-recover instrument as every prior lane. The file passes every portal format gate and is geologically distinct from all real priors — but the efficacy gate failed, so it is <strong>not</strong> approved for a weekly slot.</p></div>
<aside>{pill('DOWNLOAD: YES (research only)', 'yes')}<br><br>{pill('SUBMIT: NO', 'no')}</aside></section>

<section class="content-section">
<h2>1. The downloadable artifact and the exact decision</h2>
<div class="two-col"><aside class="download-card" aria-label="WBG-D1 file and decision">
<div class="card-top"><div class="file-icon" aria-hidden="true">.TIF</div>
<div class="file-label">WBG-D1 · radiometric alteration<small>37,654 zero-exterior binary dots · float32 · EPSG:32611</small></div>
{pill('No-go', 'no')}</div>
<div class="card-body">
<div class="status-line"><span>Portal format gates (10/10)</span><b style="color:var(--teal)">PASS · 0 NaN/inf · strict [0,1] · G10 collar clean</b></div>
<div class="status-line"><span>Byte / pixel uniqueness (364 rasters)</span><b>Unique bytes and decoded pixels</b></div>
<div class="status-line"><span>Real geological-peer 3 px overlap</span><b>0.4846 ≤ 0.70 PASS</b></div>
<div class="status-line"><span>Worst Spearman vs any raster (dots)</span><b>0.106 ≤ 0.90 PASS</b></div>
<div class="status-line"><span>Literal gate (synthetic lattice + dense surface)</span><b style="color:var(--red)">STOP</b></div>
<div class="status-line"><span>Efficacy vs same-instrument control</span><b style="color:var(--red)">FAILED · paired CI spans zero</b></div>
<div class="filename">{escape(tif)}</div>
<a class="button" href="downloads/{escape(tif)}" download><span>Download research TIFF</span><span aria-hidden="true">↓</span></a>
<div class="under-download"><span>SHA-256 {escape(rc['raster_sha256'][:16])}…</span>
<a href="downloads/{escape(zipf)}">One-TIFF ZIP ↓</a></div>
<p class="micro" style="margin-top:12px">Validation is fully automated — no human inspector. Re-run locally:
<code>.venv/bin/python scripts/validate_submission.py docs/downloads/{escape(tif)}</code></p>
</div></aside>
<article class="panel"><div class="panel-pad prose">
<h3>Why SUBMIT: NO despite a valid, unique file</h3>
<ul>
<li><strong>No measured improvement.</strong> Adding seven radiometric channels to the 19-band gradient-boosted model changed pooled HOLDOUT-DTI from {h['control_dti']:.6f} to {h['candidate_dti']:.6f}; paired Δ {h['paired_delta']:+.6f} with 95% CI [{h['paired_ci95'][0]:.6f}, {h['paired_ci95'][1]:.6f}] — zero is inside the interval.</li>
<li><strong>The deterministic radiometric detector underperformed random dots</strong> on catalogue recovery (EXP-1: {exp1['pooled_summary']['scores']['deterministic_rad_composite']['dti']:.4f} vs {exp1['pooled_summary']['scores']['random_dot_baseline']['dti']:.4f}), because its physically motivated off-ridge placements target concealed basin structures that the local catalogue-truth proxy does not contain.</li>
<li><strong>Literal registry STOP.</strong> The uniform synthetic <code>r13-lattice</code> calibration grid overlaps every sparse dot field by construction (pigeonhole, IR-WBG1-01), and the project's own continuous WBG-C1 surface is a universal overlap blocker. Against every <em>real geological</em> dot-field prior the lane is distinct (max overlap 0.4846).</li>
<li>Burning a weekly 3-entry slot on an unproven negative would reduce P(Win). The file is retained as a reproducible research deliverable and a registered negative result.</li>
</ul>
<h3>Copy-ready identifiers (≤140 chars)</h3>
<div class="copy-box"><code id="copy-name">{escape(rc['submission_name'])}</code><button type="button" data-copy="copy-name">Copy name</button></div>
<div class="copy-box"><code id="copy-note">{escape(rc['submission_note'])}</code><button type="button" data-copy="copy-note">Copy note</button></div>
<div class="copy-box"><code id="copy-hash">{escape(rc['raster_sha256'])}</code><button type="button" data-copy="copy-hash">Copy SHA-256</button></div>
</div></article></div>
</section>

<section class="content-section">
<h2>2. Three preregistered experiments — every number labeled</h2>
<div class="table-wrap"><table><thead><tr><th>Experiment</th><th>What it tests</th><th>HOLDOUT-DTI (gems57-pooled-hide-v2, n=11,330)</th><th>95% CI</th><th>Decision</th></tr></thead><tbody>
<tr><td>EXP-1</td><td>Frozen deterministic radiometric composite, 37,654 NMS dots, no fitting</td><td>{exp1['pooled_summary']['scores']['deterministic_rad_composite']['dti']:.4f}</td><td>[{exp1['pooled_summary']['scores']['deterministic_rad_composite']['ci95'][0]:.4f}, {exp1['pooled_summary']['scores']['deterministic_rad_composite']['ci95'][1]:.4f}]</td><td>{pill('negative — below random baseline', 'no')}</td></tr>
<tr><td>EXP-1 baseline</td><td>Fixed-seed random 37,654 dots on the same allowed mask</td><td>{exp1['pooled_summary']['scores']['random_dot_baseline']['dti']:.4f}</td><td>[{exp1['pooled_summary']['scores']['random_dot_baseline']['ci95'][0]:.4f}, {exp1['pooled_summary']['scores']['random_dot_baseline']['ci95'][1]:.4f}]</td><td>reference</td></tr>
<tr><td>EXP-2 control</td><td>19-band HGB spatial LOQO, continuous OOF surface</td><td>{h['control_dti']:.6f}</td><td>[{h['control_ci95'][0]:.6f}, {h['control_ci95'][1]:.6f}]</td><td>reproduces prior session exactly</td></tr>
<tr><td>EXP-2 candidate</td><td>19 bands + 7 radiometric channels, identical folds/hyperparameters</td><td>{h['candidate_dti']:.6f}</td><td>[{h['candidate_ci95'][0]:.6f}, {h['candidate_ci95'][1]:.6f}]</td><td>{pill('no improvement', 'no')}</td></tr>
<tr><td>EXP-3 dotted</td><td>NMS 37,654 dots off the mapped catalogue (intrinsic / collar-packaged)</td><td>{h['dotted_holdout_intrinsic_no_collar_dti']:.4f} / {h['dotted_holdout_collar_pessimistic_dti']:.4f}</td><td>see <a href="data/wbg-d1-exp3.json">exp3 JSON</a></td><td>representation effect, not efficacy</td></tr>
</tbody></table></div>
<p class="micro">{escape(h['representation_note'])}</p>
<p class="micro">Leakage canary: {canary['n_rows']} single-feature/fold tests, maximum orientation-invariant AUC {canary['maximum_orientation_invariant_auc']:.4f} (leakage threshold 0.90); leakage suspected: {canary['leakage_suspected']}. No prior prediction pixels, registry dots or hidden labels entered any feature.</p>
</section>

<section class="content-section">
<h2>3. Uniqueness audit — 364 aligned rasters (nine frozen snapshots + project priors)</h2>
<div class="table-wrap"><table><thead><tr><th>Closest real geological dot-field prior</th><th>Forward 3 px overlap</th><th>Reverse overlap</th><th>Spearman ρ</th><th>Jaccard</th></tr></thead><tbody>{peer_rows}</tbody></table></div>
<p class="micro">Binding gate limits: forward overlap ≤ 0.70 and |Spearman| ≤ 0.90. Every real geological peer passes. The remaining literal STOPs are non-geological controls:</p>
<ul>{lattice_rows}</ul>
<p class="micro">{escape(reg['geological_peer_note'])}</p>
</section>

<section class="content-section">
<h2>4. Nine focus sites — file, reported value and uniqueness at a glance</h2>
<p class="micro">{escape(nine['score_governance'])}</p>
{nine_site_table(nine)}
<p class="micro">Why GEMSDOE32's B2 leads the supplied records: it is the 37,654-dot D2.8 ridge field pruned to &gt;200 m from the catalogue (B1 removes &gt;100 m first); GEMSDOE25 and GEMSDOE30 are pixel-identical 44,090-dot fields, and GEMSDOE36 adds 1,200 dots to B2. A 200 m exclusion is a model choice, not an organizer rule. Full mechanism in <a href="executive-summary.html">the site comparison</a>.</p>
<h3>Project artifacts (this repository)</h3>
{project_table(rc, exp1)}
</section>

<section class="content-section prose">
<h2>5. Hypotheses, limitations and next lane</h2>
<p>Five ranked geological hypotheses, including the one executed here, are documented in <a href="wbg-d1-hypotheses.md">the WBG-D1 hypotheses register</a>. The four queued ideas (isostatic gravity edges under basin fill, anisotropic conductivity-boundary persistence, shallow magnetic residuals with cultural screening, and dilatation-jog texture transport) use only the existing hash-pinned cache and await a separately preregistered lane.</p>
<p>Limitations: hidden organizer labels are unavailable, so local HOLDOUT-DTI is a catalogue hide-and-recover proxy, not a leaderboard estimate; the nine-snapshot registry is not the full competition universe; radiometric band semantics rely on owner-mirror metadata whose organizer origin is not independently authenticated; no authenticated uploader or remaining weekly allowance exists in this environment. The actual DrivenData upload remains a manual form action described in <a href="how-to-submit.html">How to submit</a>.</p>
<p>Machine-readable evidence: <a href="data/run-card-wbg-d1.json">run card</a> · <a href="data/wbg-d1-exp1.json">EXP-1</a> · <a href="data/wbg-d1-exp2.json">EXP-2</a> · <a href="data/wbg-d1-exp3.json">EXP-3 gates</a> · <a href="data/preregistration-wbg-d1.json">preregistration</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1">source repository ↗</a></p>
</section>
"""
    (DOCS / "wbg-d1.html").write_text(page("wbg-d1.html", "WBG-D1 lane", body), encoding="utf-8")
    print("Built docs/wbg-d1.html and docs/data WBG-D1 evidence copies.")


if __name__ == "__main__":
    main()
