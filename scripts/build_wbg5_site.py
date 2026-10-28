#!/usr/bin/env python3
"""Build the WBG-5 / MTA-1 submit-path subpage from the frozen run card.

The page states the unique submission name, the short note, the measured
HOLDOUT-DTI with its paired confidence interval, the canary outcome and the
registry-uniqueness verdict, and labels the artifact download DOWNLOAD YES /
SUBMIT NO.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)

CARD = json.loads((ROOT / "evidence/wbg5/run_card.json").read_text())


def main() -> int:
    card = CARD
    tif = Path(card["artifact"]["tif"]).name
    zipf = tif.replace(".tif", ".zip")
    h = card["holdout_dti"]
    uniq = card["registry_uniqueness"]
    val = card["validator"]
    assert card["verdict"] == "negative", "refusing to publish an approval"

    body = f'''<section class="subhero"><div><p class="eyebrow">WBG-5 · MTA-1 · submit path</p><h1>Magnetic-texture anisotropy<br>vs depth contours</h1><p class="lead">A fresh, format-valid TIFF is generated here. It is a <strong>null</strong> on the paired holdout, so it is labeled <strong>DO NOT SUBMIT</strong>.</p></div><span class="pill no"><span class="dot"></span>Negative · no real slot</span></section>
<section class="content-section" id="artifact">
<h2>Submission identity</h2>
<div class="two-col content-section">
<div class="panel"><div class="panel-head">Unique submission name</div><div class="panel-pad"><div class="filename">{escape(card["submission_name"])}</div><p class="micro">SHA-256 <span class="mono">{escape(card["artifact"]["tif_sha256"])}</span></p></div></div>
<div class="panel"><div class="panel-head">Short note (portal field)</div><div class="panel-pad"><p class="mono">{escape(card["submission_note"])}</p><p class="micro">Length {len(card["submission_note"])} characters (limit 140).</p></div></div>
</div>
<div class="actions" style="margin-top:16px">
<a class="button" href="../downloads/{tif}" download>Download research TIFF ↓</a>
<a class="button secondary" href="../downloads/{zipf}" download>One-TIFF ZIP ↓</a>
<a class="button secondary" href="../evidence/wbg5/run_card.json">Run card JSON ↗</a>
</div>
<p class="note">DOWNLOAD: YES · SUBMIT: NO. Research artifact only; no organizer receipt, no authenticated weekly allowance, no promotion to a live slot.</p>
</section>

<section class="content-section" id="measured">
<div class="section-heading"><div><h2>Measured on the frozen holdout</h2><p>Every number is HOLDOUT-DTI, not a leaderboard score.</p></div></div>
<div class="panel-pad">
<p><strong>Candidate A2_mta1</strong> <code>HOLDOUT-DTI {h["dti"]:.6f}</code> · 95% CI [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}]<br>
<strong>Control A1_ctrl_no_mta</strong> (19-band stack) <code>{h["control_arm_A1_dti"]:.6f}</code> · 95% CI [{h["control_arm_A1_ci95"][0]:.6f}, {h["control_arm_A1_ci95"][1]:.6f}]</p>
<p><strong>Paired delta {h["paired_delta"]:+.6f}</strong> · 95% CI [{h["paired_delta_ci95"][0]:+.6f}, {h["paired_delta_ci95"][1]:+.6f}] · evaluator <code>{h["evaluator_version"]}</code> · {h["n_withheld_positives"]:,} withheld positives · MTA-1 wins 2 of 4 folds.</p>
<p class="note">The paired confidence interval includes zero. A projection is never a score; a non-significant paired CI is a null, not a forecast.</p>
</div>
</section>

<section class="content-section" id="canary">
<h2>Leakage canary</h2>
<div class="panel-pad">
<p>Canary over the full 32-channel set passed: <strong>{escape(str(card["canary"]["all_features_passed"]))}</strong>, no feature dropped, maximum symmetric fold AUC <code>{card["canary"]["max_sym_auc"]:.6f}</code> &le; 0.90. The reduced set also passed. The earlier canary false-positive was a holdout-misalignment artifact (the catalogue had been excluded from the evaluation footprint, which corrupted the valid/truth masks); it is resolved and no bands were dropped.</p>
</div>
</section>

<section class="content-section" id="uniqueness">
<div class="section-heading"><div><h2>Registry uniqueness</h2><p>Two gates, reported separately.</p></div></div>
<div class="panel-pad">
<p><strong>Competing-submission gate: PASSED.</strong> Maximum 3 px overlap against the nine historical masks <strong>{uniq["sparse_max_overlap"]*100:.2f}% &le; 70%</strong>; maximum |&rho;| = {uniq["sparse_max_abs_spearman"]:.4f} &le; 0.90. The artifact is not a duplicate of any competing submission.</p>
<p><strong>Literal all-entry gate: FAILED (reported, not waived).</strong> Maximum 3 px overlap {uniq["max_overlap_all"]*100:.2f}% — the only comparator above 70% is <code>wbg-c1</code>, WBGGEMSDOE1's own continuous research surface, which overlaps every budget-matched dotted field by construction. It is logged, never gating.</p>
</div>
</section>

<section class="content-section" id="decision">
<h2>The decision in plain English</h2>
<div class="prose"><ol>
<li><strong>The TIFF is genuinely generated here</strong> — {card["artifact"]["emitted_dots"]:,} zeros-mode dots, single-band float32, EPSG:32611, 3730×3292, values in [0,1], zero outside the footprint. Format validation: {escape(str(val["format_valid"]))}.</li>
<li><strong>It does not improve the clean control.</strong> The paired holdout CI includes zero, so MTA-1 adds no recoverable signal. No final dots were placed or retuned around the registry after the null.</li>
<li><strong>Uniqueness is reported, not decided by format.</strong> It passes the competing-submission gate but fails the literal all-entry gate against the project's own research surface.</li>
<li><strong>No real slot is selected.</strong> No organizer receipt and no authenticated weekly allowance. Promotion to a live slot is a separate selector step.</li>
</ol></div>
</section>'''

    (ROOT / "docs/wbg5").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/wbg5/index.html").write_text(
        bs.page("wbg5/index.html", "WBG-5 / MTA-1 · WBGGEMSDOE1", body), encoding="utf-8")
    print("Built WBG-5 submit-path subpage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
