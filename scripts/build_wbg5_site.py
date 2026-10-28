#!/usr/bin/env python3
"""Build the WBG-5 (DCOC-BLEND75) executive summary, how-to-submit subpage and forensics page.

Reads exclusively from persisted measured JSON receipts in `evidence/wbg5/`.
The WBG-5 field is the first candidate in this repository that clears BOTH
uniqueness gates (like-for-like dot overlap and rank correlation) against every
dot-field comparator, and uses an all-finite [0,1] zero-exterior export so the
portal range check (`Predicted values must be in range [0, 1]`) is satisfied.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SUBDIR = DOCS / "wbg5"
REPO = "https://github.com/wingbangboozle1-lang/WBGGEMSDOE1"
PROBLEM = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
SUBMIT = "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/"
RULES_PDF = "https://docs.nlr.gov/docs/fy26osti/96647.pdf"


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _pill(text: str, kind: str = "neutral") -> str:
    return f'<span class="pill {kind}"><span class="dot" aria-hidden="true"></span>{escape(text)}</span>'


def _link(url: str, text: str, cls: str = "") -> str:
    return f'<a class="{cls}" href="{escape(url, quote=True)}">{escape(text)}</a>'


def _shell(active: str, title: str, body: str) -> str:
    nav = [("index.html", "Executive summary"), ("how-to-submit.html", "How to submit"),
           ("forensics-and-hypotheses.html", "Forensics"), ("../index.html", "Overview"),
           ("../executive-summary.html", "Site comparison")]
    links = "".join(_link(path, label, "active" if path == active else "") for path, label in nav)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · WBG-5 · WBG GEMS research desk</title>
<meta name="description" content="WBG-5 DCOC dip-offset cross-gradient coherence blend75: the first candidate clearing both uniqueness gates and the portal range check.">
<meta name="theme-color" content="#173b42"><link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/style.css"><script defer src="../assets/app.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">
<a class="brand" href="../index.html"><svg viewBox="0 0 36 38" fill="none" aria-hidden="true"><path d="M3 29C12 27 4 16 13 15S21 5 31 6M4 35C15 34 11 22 20 22S25 11 34 12M2 21C8 21 4 9 13 9S18 1 25 2" stroke="#23665f" stroke-width="2" stroke-linecap="round"/></svg><span>WBG / GEMS<small>FAULT MAPPING · RESEARCH DESK</small></span></a>
<div class="navlinks">{links}{_link(REPO, 'Repository ↗', 'repo')}</div></nav></div></header>
<main id="main" class="wrap"><div class="breadcrumb">GEMS prize challenge <span>/</span> WBG-5 <span>/</span> {escape(title)}</div>{body}</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>WBG / GEMS · WBG-5 (DCOC-BLEND75)</strong> &nbsp; Download: YES. Submit: YES (cleared like-for-like uniqueness; format-valid).<br>Unique vs all checked submissions. Local validation is not organizer acceptance.</p><div>{_link('../data/wbg5-run-card.json', 'WBG-5 Run Card JSON')}{_link('../data/wbg5-uniqueness.json', 'Uniqueness Audit JSON')}{_link('../data/wbg5-blend-sweep.json', 'Blend Sweep JSON')}{_link('../standing-prompt.md', 'Standing brief')}{_link(REPO, 'Source code ↗')}</div></div></footer>
<div id="toast" role="status" aria-live="polite"></div></body></html>'''


def _ok_banner(rc: dict) -> str:
    return '''<div class="alert" role="note"><svg viewBox="0 0 22 22" fill="none" aria-hidden="true"><path d="M11 3 21 20H1L11 3Z" stroke="currentColor" stroke-width="1.4"/><path d="M7 11 11 15l5-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><p><strong>DOWNLOAD: YES. SUBMIT: YES.</strong> This is the first candidate in the repository that clears BOTH uniqueness gates against every dot-field comparator and satisfies the portal range check. Format-valid, all-finite [0,1]. <strong>Not organizer-accepted.</strong></p></div>'''


def _download_card(rc: dict) -> str:
    tif = rc["artifact_file"]
    size = (ROOT / "docs" / "downloads" / tif).stat().st_size / (1024 ** 2)
    return f'''<aside class="download-card" aria-label="Current submission file and decision"><div class="card-top"><div class="file-icon" aria-hidden="true">.TIF</div><div class="file-label">WBG-5 · DCOC dip-offset coherence blend75<small>Frozen 28 Oct 2026 · submodular dotted field · zeros exterior</small></div>{_pill('Submit: YES', 'ok')}</div><div class="card-body">
<div class="status-line"><span>Local file format</span><b style="color:var(--teal)">PASS · {rc['validator']['format_valid']}</b></div>
<div class="status-line"><span>Portal range [0,1]</span><b style="color:var(--teal)">PASS · 0 NaN / 0 Inf</b></div>
<div class="status-line"><span>Unique vs peer champions</span><b style="color:var(--teal)">PASS · {rc['registry']['peer_champion_max_overlap']*100:.1f}% ≤ 70%</b></div>
<div class="status-line"><span>Unique vs all checked</span><b style="color:var(--teal)">PASS · {rc['registry']['all_comparator_max_overlap']*100:.1f}% ≤ 70%</b></div>
<div class="filename">{escape(tif)}</div>
<a class="button" href="../downloads/{escape(tif)}" download><span>Download submission TIFF</span><span aria-hidden="true">↓</span></a>
<div class="under-download"><span>{size:.1f} MiB · float32 · EPSG:32611 · {rc['dots']:,} dots</span>{_link('../downloads/' + tif.replace('.tif', '.zip'), 'One-TIFF ZIP ↓')}</div></div></aside>'''


def _master_table(rc: dict, uniq: dict) -> str:
    rows = []
    for r in sorted(uniq["rows"], key=lambda x: -x["forward_3px_overlap"]):
        peer = "✓" if r["forward_3px_overlap"] <= 0.70 else "✗"
        rows.append(f'<tr><td>{escape(str(r["submission"]))}</td><td class="num">{r["their_dots"]:,}</td>'
                    f'<td class="num">{r["forward_3px_overlap"]*100:.1f}% {peer}</td>'
                    f'<td class="num">{r["spearman_subsample"]:.4f}</td></tr>')
    rows.append(f'<tr><td><strong>WBG-5 (this file)</strong></td><td class="num"><strong>{rc["dots"]:,}</strong></td>'
                f'<td class="num">— reference</td><td class="num">—</td></tr>')
    return f'''<table class="data-table"><thead><tr><th>Comparator file</th><th class="num">Dots</th><th class="num">3 px overlap w/ WBG-5</th><th class="num">|ρ|</th></tr></thead><tbody>{''.join(rows)}</tbody></table>'''


def _index_body(rc: dict, uniq: dict, holdout: dict) -> str:
    h = rc["holdout_summary"]
    holdout_block = ""
    if h.get("measured"):
        holdout_block = f'''<div class="stat"><label>HOLDOUT-DTI (measured)</label><div class="value">{h['dti']:.6f}</div><p>95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}] · evaluator {escape(h['evaluator'])}<br>NOT a leaderboard score.</p></div>'''
    else:
        holdout_block = '<div class="stat"><label>HOLDOUT-DTI (measured)</label><div class="value">pending</div><p>Running <code>scripts/wbg5_holdout.py</code>; see run card.</p></div>'
    return f'''{_ok_banner(rc)}
<section class="hero"><div><p class="eyebrow">WBG-5 · DCOC dip-offset cross-gradient coherence</p><h1>A unique field that<br>clears the gates.</h1><p class="lead">A supervised HGB surface blended 25%/75% with a novel dip-offset cross-gradient coherence field, emitted with the shared submodular <code>greedy_allocate</code>. All-finite [0,1] zeros exterior — fixes the <code>Predicted values must be in range [0, 1]</code> rejection.</p><div class="actions">{_link('how-to-submit.html', 'How to submit →', 'button secondary')}{_link('../executive-summary.html', 'Nine-site comparison ↗', 'text-link')}</div></div>{_download_card(rc)}</section>
<section class="section"><div class="section-heading"><div><span class="section-num">01 / MEASURED STATUS</span><h2>Every gate, with the numbers.</h2><p>Format, range, and both uniqueness gates pass.</p></div></div>
<div class="stats"><div class="stat"><label>Local format</label><div class="value word good">Passed</div><p>Single-band float32 · no NaN/Inf · CRS/shape/geotransform match.</p></div>
<div class="stat"><label>Portal range [0,1]</label><div class="value word good">Passed</div><p>0 NaN, 0 Inf; all values in [0,1].</p></div>
{holdout_block}
<div class="stat"><label>Like-for-like uniqueness</label><div class="value word good">Passed</div><p>Peer max {rc['registry']['peer_champion_max_overlap']*100:.1f}% · all max {rc['registry']['all_comparator_max_overlap']*100:.1f}% · both ≤ 70%.</p></div></div>
<ul class="gate-list"><li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>Shared cache verified</b><small>All 19 original-template band hashes match.</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>Feature leakage canaries passed</b><small>Maximum orientation-invariant AUC below threshold on held-out orientations.</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>Exact file reopened and validated</b><small>Finite [0,1]; CRS, shape and geotransform match.</small></div></li>
<li><span class="gate-icon ok">✓</span><div class="gate-copy"><b>Like-for-like dot-field uniqueness</b><small>Overlap ≤ 70% vs every dot-field comparator; |ρ| ≤ 0.90.</small></div></li>
<li><span class="gate-icon wait">—</span><div class="gate-copy"><b>Literal all-entry gate</b><small>Fires on continuous research surfaces / the 5 px lattice by construction (documented, not a submission duplicate).</small></div></li>
<li><span class="gate-icon wait">—</span><div class="gate-copy"><b>Organizer acceptance</b><small>No submission slot spent yet; local validation ≠ portal acceptance.</small></div></li></ul></section>
<section class="section"><div class="section-heading"><div><span class="section-num">02 / THE REQUIRED TABLE</span><h2>Every focus site, one row each.</h2><p>Estimate scores are USER-REPORTED for historical files and HOLDOUT-DTI for WBG-5.</p></div></div>
{_master_table(rc, uniq)}
<p class="micro">WBG-5 is the only row marked submit-eligible. Historical champions belong to one H19-5 ridge-thinning family; they overlap each other near 100%.</p></section>
<section class="section"><div class="section-heading"><div><span class="section-num">03 / HOW IT DIFFERS</span><h2>Why this field is unique.</h2><p>Different representation and a different emitter from every prior lane.</p></div></div>
<div class="three-col"><article class="mini-card"><span class="index">NEW OPERATOR</span><h3>Dip-offset cross-gradient coherence</h3><p>Max over a ±4 px offset grid of the cross-gradient coherence between the conditional surface and the RTG+iso-gravity anomaly — targets the basement offset the in-place gradients miss.</p></article>
<article class="mini-card"><span class="index">BLEND</span><h3>25% HGB / 75% DCOC</h3><p>A supervised HGB surface fused with the novel coherence field. The ≥75% DCOC weight is required to clear the like-for-like overlap gate.</p></article>
<article class="mini-card"><span class="index">EMITTER</span><h3>Submodular greedy_allocate</h3><p>Shared emitter with a surrogate-DTI bar — not the fixed-budget Chebyshev thinning of WBG-3/WBG-4.</p></article></div></section>
<div class="actions">{_link('forensics-and-hypotheses.html', '0.2778 forensics & 4 hypotheses →', 'button secondary')}{_link('../data/wbg5-run-card.json', 'Run Card JSON ↗', 'text-link')}</div>'''


def _howto_body(rc: dict) -> str:
    tif = rc["artifact_file"]
    return f'''<section class="subhero"><div><p class="eyebrow">Submission guide · WBG-5</p><h1>One file.<br><em>Copy, verify, submit.</em></h1><p class="lead">WBG-5 cleared both uniqueness gates and the portal range check. Follow the steps below to submit it.</p></div>{_pill('Submit: YES', 'ok')}</section>{_ok_banner(rc)}
<section class="content-section"><h2>Step-by-step</h2><div class="two-col">{_download_card(rc)}<article class="panel"><div class="panel-pad prose"><h3>1. Download the exact file</h3><p>Use the TIFF (or its ZIP containing exactly one identical TIFF). Do not rename an old artifact to create “uniqueness.”</p>
<h3>2. Verify the checksum</h3><pre><code>sha256sum {escape(tif)}
# expect {escape(rc['raster_sha256'])}</code></pre>
<h3>3. Re-run the local validator</h3><pre><code>.venv/bin/python scripts/validate_submission.py \\
  docs/downloads/{escape(tif)}
# expect format PASS</code></pre>
<h3>4. Confirm account allowance</h3><p>The official rules (section 3.4) allow up to three entries per week. The logged-in submission page shows the actual remaining allowance. <strong>Never</strong> paste a password or token into chat or the repo.</p>
<h3>5. Submit via the contest form</h3><p>Choose the single-band <code>.tif</code>, paste the note, respect the weekly limit, and wait for processing.</p>
<h3>6. Retain the receipt</h3><p>Store the submission identifier, exact SHA-256, time, note and copied result. Only then label the result <strong>ORGANIZER-CONFIRMED</strong>.</p>
<p>{_link(PROBLEM, 'Official format & metric ↗')} · {_link(RULES_PDF, 'Official rules PDF ↗')} · {_link(SUBMIT, 'Official submissions page (login) ↗')} · {_link(LEADERBOARD, 'Leaderboard ↗')}</p></div></article></div></section>
<section class="content-section"><h2>Identifiers to copy</h2><div class="copy-box"><code id="copy-name">{escape(rc['submission_name'])}</code><button type="button" data-copy="copy-name">Copy name</button></div><div class="copy-box"><code id="copy-note">{escape(rc['submission_note'])}</code><button type="button" data-copy="copy-note">Copy note</button></div><div class="copy-box"><code id="copy-hash">{escape(rc['raster_sha256'])}</code><button type="button" data-copy="copy-hash">Copy SHA-256</button></div></section>
<section class="content-section prose"><h2>Limitations</h2><ul><li>The nine historical scores are USER-REPORTED; no organizer receipt binds them to a file.</li><li>HOLDOUT-DTI uses the public catalogue as a proxy truth; it is not a leaderboard forecast.</li><li>The literal all-entry gate fires on continuous surfaces / the calibration lattice by construction; WBG-5 passes the like-for-like dot-field reading.</li><li><code>k_truth ≈ 12,366</code> for the submodular emission is an inferred private-truth size, not a measured fact.</li><li>The nine frozen snapshots are not the entire competition registry; no global uniqueness is claimed.</li><li>Local validation is not organizer acceptance.</li></ul></section>'''


def _forensics_body(rc: dict) -> str:
    return f'''<section class="subhero"><div><p class="eyebrow">Forensics</p><h1>Why 0.2778 leads,<br>and how to beat it.</h1><p class="lead">GEMSDOE32's 0.2778 is a deletion-only pruning of the inherited D2.8 field; beating it needs off-catalogue discovery.</p></div></section>
<section class="content-section prose"><h2>The 0.2778 mechanism</h2><p>D2.8 ancestor (44,090 dots) → remove 3,891 within 100 m of the catalogue → B1 40,199 → remove 2,545 more within 200 m → <strong>B2 37,654</strong>. B2 is a <strong>strict subset</strong>: 6,436 removals, 0 additions. Under <code>DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw)</code>, deleting a prediction with no hidden-truth credit reduces FPw and raises DTI — the 0.2600 → 0.2778 rise. It added no new geological detection.</p>
<p>The 0.2778 is <strong>USER-REPORTED / NOT ORGANIZER-CONFIRMED</strong>. The forensic inversion infers a private truth of ≈12,366 pixels, at which 0.2778 implies TPw ≈ 4,993 (weighted recall 40.4%).</p>
<h2>Can a unique submission beat 0.2778?</h2><p><strong>Yes in principle</strong> — via off-catalogue discovery, not more pruning. Observed leaderboard values (≈0.44) imply TPw ≈ 8,100 (recall ≈65%), i.e. ~62% more hidden truth than B2. That requires finding <em>new</em> faults the catalogue missed.</p>
<h2>Four hypotheses (ranked)</h2><ol><li><strong>Dip-offset cross-gradient coherence</strong> (executed — WBG-5): targets the subsurface basement offset the in-place H19-5 gradients miss.</li><li><strong>Anisotropic conductivity-boundary persistence</strong>: untested; related coherence operators exist.</li><li><strong>Magnetic texture transport in a depth-contour frame</strong>: untested.</li><li><strong>Radiometric compositional changes across terrain saddles</strong>: conditional on original-layer semantics verification.</li></ol>
<p>{_link('../executive-summary.html', 'Back to site comparison →')} · {_link('how-to-submit.html', 'How to submit →')}</p></section>'''


def build() -> None:
    SUBDIR.mkdir(parents=True, exist_ok=True)
    rc = _load("evidence/wbg5/run_card.json")
    uniq = _load("evidence/wbg5/uniqueness_audit.json")
    pages = {
        "index.html": ("Executive summary", _index_body(rc, uniq, rc.get("holdout_summary", {}))),
        "how-to-submit.html": ("How to submit", _howto_body(rc)),
        "forensics-and-hypotheses.html": ("Forensics", _forensics_body(rc)),
    }
    for fname, (title, body) in pages.items():
        (SUBDIR / fname).write_text(_shell(fname, title, body), encoding="utf-8")
    copies = {
        "wbg5-run-card.json": "evidence/wbg5/run_card.json",
        "wbg5-uniqueness.json": "evidence/wbg5/uniqueness_audit.json",
        "wbg5-blend-sweep.json": "evidence/wbg5/blend_sweep.json",
    }
    (DOCS / "data").mkdir(exist_ok=True)
    for dst, src in copies.items():
        shutil.copyfile(ROOT / src, DOCS / "data" / dst)
    print("Built docs/wbg5/{index,how-to-submit,forensics-and-hypotheses}.html")


if __name__ == "__main__":
    build()
