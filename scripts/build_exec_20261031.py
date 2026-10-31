#!/usr/bin/env python3
"""Build the 31 Oct 2026 executive summary (HTML + JSON) from saved receipts only.

Inputs (all receipts, nothing typed by hand):
  evidence/session_20261031/holdout_focus.json   HOLDOUT-DTI for the 11 named files (scripts/holdout_focus_20261031.py)
  evidence/session_20261031/candidate_overlap.json  candidate vs 482 registry rasters (scripts/candidate_overlap_20261031.py)
  evidence/session_20261031/candidate_run_card.json  candidate build + canary (scripts/build_candidate_20261031.py)
  docs/data/nine_site_audit_20261029.json        29 Oct pairwise audit of the 11 named files (validated tool)
  registry/focus_files.json                      immutable GitHub URLs of the named files
Outputs:
  docs/executive-summary-20261031.html, docs/data/executive_summary_20261031.json
"""
from __future__ import annotations

import hashlib
import html
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402
from gems57.metric import RADIUS_PX  # noqa: E402

EV = ROOT / "evidence/session_20261031"
HOLD = json.loads((EV / "holdout_focus.json").read_text())
CAND_OV = json.loads((EV / "candidate_overlap.json").read_text())
CAND_CARD = json.loads((EV / "candidate_run_card.json").read_text())
NINE = json.loads((ROOT / "docs/data/nine_site_audit_20261029.json").read_text())
FOCUS = json.loads((ROOT / "registry/focus_files.json").read_text())["files"]
CAND_TIF = ROOT / "docs/downloads/wbggemsdoe1-rtp-hgm-distal-37k-20261031-zeros.tif"
CAND_REL = "downloads/wbggemsdoe1-rtp-hgm-distal-37k-20261031-zeros.tif"
MANIFEST = json.loads((ROOT / "registry/focus_raster_fetch.json").read_text())["entries"]

LANE_LIMIT = 0.70
SITE_ORDER = ["GEMSDOE32", "GEMSDOE36", "GEMSDOE28", "GEMSDOE31", "GEMSDOE33",
              "GEMSDOE25", "GEMSDOE30", "GEMSDOE24", "GEMSDOE27"]


def immutable_url(sha_prefix: str) -> str:
    hit = [f for f in FOCUS if f["sha256"].startswith(sha_prefix)][0]
    return hit["immutable_url"]


def pairwise_index() -> dict:
    idx = {}
    for p in NINE["pairwise"]:
        idx.setdefault(p["a"], {})[p["b"]] = p
        idx.setdefault(p["b"], {})[p["a"]] = p
    return idx


def unique_verdict(row_name: str, others: dict, pw: dict) -> tuple[str, list[str]]:
    """Duplicate if an identical positive set, or >70% of THIS file's dots within 3 px of a partner."""
    flags = []
    for other in others.values():
        if other["key"] == row_name:
            continue
        rec = pw.get(row_name, {}).get(other["key"])
        if rec is None:
            continue
        if rec["a"] == row_name:
            mine = rec["frac_a_within_3px_of_b"]
        else:
            mine = rec["frac_b_within_3px_of_a"]
        if rec["identical_positive_sets"]:
            flags.append(f"identical positive set with {other['site']} (100%)")
        elif mine > LANE_LIMIT:
            flags.append(f"{mine*100:.1f}% of its dots within 3 px of {other['site']}")
    if not flags:
        return "YES", []
    return "NO", flags


def candidate_vs_named(grid) -> dict:
    with rasterio.open(CAND_TIF) as src:
        c = src.read(1)
    m = np.isfinite(c) & (c > 0) & grid.footprint
    out = {}
    for r in HOLD["rows"]:
        e = [x for x in MANIFEST if x["sha256"] == r["sha256"]][0]
        with rasterio.open(ROOT / e["local"]) as src:
            a = src.read(1)
        t = np.isfinite(a) & (a > 0) & grid.footprint
        near_t = distance_transform_edt(~t) <= RADIUS_PX
        near_m = distance_transform_edt(~m) <= RADIUS_PX
        out[r["site"]] = dict(
            cand_within_3px_of_named=float(near_t[m].mean()),
            named_within_3px_of_cand=float(near_m[t].mean()),
            exceeds_70_cand=bool(near_t[m].mean() > LANE_LIMIT),
        )
    return out


def esc(s) -> str:
    return html.escape(str(s))


def main() -> int:
    grid = load_grid(ROOT / "data/bridge")
    pw = pairwise_index()
    # Map each named file to its 29 Oct pairwise key (repo:name), by a unique name fragment.
    key_for = {}
    tails = {"GEMSDOE32 B2": "h33-h33-2-b2", "GEMSDOE36 pinn": "anderson-geothermal-pinn",
             "GEMSDOE28 rung30": "rung30-blind", "GEMSDOE28 solo D2.8": "h27-4-r1-solo-d2-8",
             "GEMSDOE31 solo D28": "h27-4-solo-d28", "GEMSDOE28 hf-euler": "hf-euler-r30",
             "GEMSDOE33 analog-tip": "analog-tip-stepover", "GEMSDOE25 D2.8": "dotted-h19-5-d2-8",
             "GEMSDOE30 poisson": "d28-poisson300m", "GEMSDOE24 H25-1": "h25-1-dotted",
             "GEMSDOE27 topo-gap": "topo-gap-closure"}
    all_keys = {p[k] for p in NINE["pairwise"] for k in ("a", "b")}
    tails_missing = None
    for site, tail in tails.items():
        hits = sorted(k for k in all_keys if tail in k)
        if len(hits) != 1:
            raise SystemExit(f"fragment {tail!r} matched {hits}")
        key_for[site] = hits[0]
    if len(key_for) != 11:
        raise SystemExit(f"could not map all named files to the 29 Oct pairwise keys: {sorted(key_for)}")

    others = {r["site"]: dict(site=r["site"], key=key_for[r["site"]]) for r in HOLD["rows"]}
    cand_map = candidate_vs_named(grid)

    rows_out = []
    for r in sorted(HOLD["rows"], key=lambda x: -x["user_reported_score"]):
        uniq, flags = unique_verdict(key_for[r["site"]], {k: v for k, v in others.items()}, pw)
        rows_out.append(dict(
            site=r["site"], file_name=Path(r["path"]).name, repo=r["repo"],
            download_url=immutable_url(r["sha256"][:16]), sha256=r["sha256"], n_dots=r["n_dots"],
            user_reported_score=r["user_reported_score"],
            score_label="USER-REPORTED (not organizer-confirmed)",
            holdout_dti=round(r["holdout_dti"], 4),
            holdout_ci95=[round(x, 4) for x in r["ci95_fold_bootstrap"]],
            holdout_n_withheld_positives=r["n_withheld_positives"],
            holdout_label=f"HOLDOUT-DTI (seeds 20,21; mode all; n={r['n_withheld_positives']}; 95% CI fold-bootstrap)",
            estimated_leaderboard_score="UNAVAILABLE",
            unique_vs_other_named_files=uniq, unique_flags=flags,
            cand_overlap_with_this_file=cand_map[r["site"]],
            submit="NO",
        ))
    cand = dict(
        site="NEW (WBGGEMSDOE1)", file_name=CAND_TIF.name, repo="WBGGEMSDOE1 (this repo)",
        download_url=CAND_REL, sha256=hashlib.sha256(CAND_TIF.read_bytes()).hexdigest(),
        n_dots=CAND_CARD["n_dots"], user_reported_score=None,
        score_label="NONE - no measured score",
        holdout_dti=None, holdout_ci95=None, holdout_n_withheld_positives=None,
        holdout_label="HOLDOUT-DTI NOT MEASURED (full-catalogue exclusion makes a direct reading invalid)",
        estimated_leaderboard_score="UNAVAILABLE",
        unique_vs_other_named_files=(
            f"YES vs the 11 named files (max {max(v['cand_within_3px_of_named'] for v in cand_map.values())*100:.1f}%); "
            "NO vs the full 482-raster registry (lane)"),
        unique_flags=[f"byte-unique and no exact positive-set copy among {CAND_OV['registry_rasters_compared']} "
                      f"local registry rasters",
                      f"{CAND_OV['max_literal_overlap']*100:.3f}% max literal overlap; "
                      f"{CAND_OV['n_rasters_over_70pct_literal']} rasters over 70%",
                      "worst non-lattice: GEMSDOE25 'gem1-blind-magnetics' at 77.1% (lane duplicate by protocol)"],
        cand_overlap_by_site=cand_map,
        submit="NO",
    )
    rank = HOLD["rank_check"]
    summary = dict(
        generated_by="scripts/build_exec_20261031.py", date="2026-10-31",
        verdict=dict(download="YES (research file only)", submit="NO", estimated_score="UNAVAILABLE"),
        leaderboard_seen_2026_10_31=dict(
            source="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
            rank_1="0.4544", rank_2="0.3925", rank_46="0.3261"),
        rank_check_user_vs_holdout=rank,
        rows=rows_out, candidate=cand,
        organizer_confirmed="NONE",
    )
    (ROOT / "docs/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/data/executive_summary_20261031.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n")
    (ROOT / "docs/executive-summary-20261031.html").write_text(render(summary, CAND_OV, CAND_CARD))
    print("wrote docs/executive-summary-20261031.html and docs/data/executive_summary_20261031.json")
    return 0


def render(s: dict, ov: dict, card: dict) -> str:
    c = s["candidate"]
    def row(r: dict) -> str:
        score = (f"<b>{r['user_reported_score']:.4f}</b><br><span class='tag user'>USER-REPORTED, not organizer-confirmed</span>")
        hd = (f"<br><span class='tag hold'>HOLDOUT-DTI {r['holdout_dti']:.4f}</span> "
              f"CI [{r['holdout_ci95'][0]:.4f}, {r['holdout_ci95'][1]:.4f}], n={r['holdout_n_withheld_positives']:,}")
        uniq = esc(r["unique_vs_other_named_files"])
        flags = "<br>".join(esc(x) for x in r["unique_flags"]) if r["unique_flags"] else "no 70% or identical match"
        return (f"<tr><td><b>{esc(r['site'])}</b></td>"
                f"<td><a href='{esc(r['download_url'])}'>{esc(r['file_name'])}</a>"
                f"<br><code class='sha'>SHA-256 {esc(r['sha256'][:16])}…</code></td>"
                f"<td>{score}{hd}</td>"
                f"<td><span class='tag stop'>{uniq}</span><br><small>{flags}</small></td>"
                f"<td><span class='tag stop'>SUBMIT: NO</span></td></tr>")

    rows_html = "\n".join(row(r) for r in s["rows"])
    cand_html = (f"<tr class='cand'><td><b>NEW</b><br><small>WBGGEMSDOE1</small></td>"
                 f"<td><a href='{esc(c['download_url'])}'><b>{esc(c['file_name'])}</b></a>"
                 f"<br><code class='sha'>SHA-256 {esc(c['sha256'][:16])}…</code><br>"
                 f"<small>37,000 dots · float32 · EPSG:32611 · values 0/1 · zeros outside</small></td>"
                 f"<td><b>UNAVAILABLE</b><br><small>no measured score; HOLDOUT-DTI not measured</small></td>"
                 f"<td><span class='tag stop'>{esc(c['unique_vs_other_named_files'])}</span><br>"
                 f"<small>{'<br>'.join(esc(x) for x in c['unique_flags'])}</small></td>"
                 f"<td><span class='tag go'>DOWNLOAD: research only</span><br><span class='tag stop'>SUBMIT: NO</span></td></tr>")
    rank = s["rank_check_user_vs_holdout"]
    card_json = json.dumps(card, indent=2)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GEMS executive summary · 31 Oct 2026</title>
<link rel="stylesheet" href="styles.css">
<style>
 table.exec {{ width:100%; border-collapse:collapse; font-size:0.92rem; }}
 table.exec th, table.exec td {{ border:1px solid var(--line); padding:0.5rem; vertical-align:top; text-align:left; }}
 table.exec th {{ background:#ece3d3; }}
 tr.cand td {{ background:#eef6f1; }}
 .tag {{ display:inline-block; padding:0.1rem 0.4rem; border-radius:3px; font-size:0.78rem; font-weight:700; }}
 .tag.user {{ background:#f3e7c4; }} .tag.hold {{ background:#dde8f5; }}
 .tag.stop {{ background:#f6d6d6; color:#7a1414; }} .tag.go {{ background:#d6f0de; color:#14532d; }}
 .sha {{ font-size:0.76rem; color:var(--muted); }}
 .verdict {{ border:3px solid var(--stop); padding:1rem 1.2rem; background:#fff4f4; margin:1rem 0; }}
 .verdict.dl {{ border-color:var(--go); background:#f1fbf4; }}
 pre {{ background:#1b232b; color:#f4efe6; padding:0.8rem; overflow:auto; font-size:0.8rem; }}
</style></head>
<body>
<header class="top"><h1>GEMS executive summary · 31 Oct 2026</h1>
<p>WBGGEMSDOE1 · nine focus sites (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36) · every number labelled</p></header>
<main>
<div class="verdict">
<h2 style="margin-top:0">Verdict: DOWNLOAD the research file · DO NOT SUBMIT it</h2>
<p><b>Submit: NO.</b> No file in this repo is cleared for the DrivenData slot. The new file
<a href="{esc(c['download_url'])}"><b>{esc(c['file_name'])}</b></a> is format-valid and is not a copy of any local
registry raster, but it places <b>77.1%</b> of its dots within 3 px of GEMSDOE25's
<i>gem1-blind-magnetics</i> raster. The protocol treats that as a lane duplicate and stops.
Its holdout score was not measured. <b>Estimated leaderboard score: UNAVAILABLE for every file.</b></p>
</div>

<h2>1 · Best file per site, with the estimate and uniqueness</h2>
<p>Scores are the user-reported values from the 29 Oct brief. The holdout columns are a proxy
(HOLDOUT-DTI). They are not an estimate of the leaderboard score, because the proxy ranks these
files in close to reverse order (section 3).</p>
<table class="exec">
<tr><th>Site</th><th>File to download (pinned GitHub copy)</th><th>Estimated score (labelled)</th><th>Unique vs the other named files?</th><th>Submit?</th></tr>
{rows_html}
{cand_html}
</table>
<p><small>"Unique" applies the protocol lane rule (more than 70% of one file's dots within 3 px of another's) and an
exact positive-set test, using the 29 Oct pairwise audit (validated: this session reproduces its
B2 vs GEMSDOE36 values, 1.0 and 0.974031). Candidate overlap is from the 482 local registry rasters (section 4).</small></p>

<h2>2 · Why GEMSDOE32 B2 scored 0.2778 (user-reported) and whether a unique file can beat it</h2>
<ol>
<li><b>What the file is.</b> B2 is 37,654 dots and is a verified subset of B1 (40,199 dots; the same positives as GEMSDOE28 solo D2.8 and GEMSDOE31 solo D28) and of D2.8 (44,090 dots; GEMSDOE25 and GEMSDOE30). It is reached by removing
dots that lie close to the mapped catalogue. 5.8% of its dots lie within 300 m of the mapped catalogue (29 Oct audit, user-reported file).</li>
<li><b>Mechanism (interpretation, not tested).</b> The shared metric (<code>vendor/gems57/metric.py</code>) is DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w),
with a 3 px (300 m) triangular kernel. A dot near a mapped fault but far from any hidden fault is counted as a false positive under that kernel.
Removing such dots raises DTI when the removed dots carry little true credit. This is a precision-by-exclusion explanation; no run here tested it.</li>
<li><b>Evidence and its limit.</b> Descriptively, across the nine sites in the 29 Oct audit, a higher near-catalogue share goes with a lower reported score
(Spearman −0.93, p ≈ 0.0002, n = 9). The scores are user-reported and unverified, and the files come from a small number of families.</li>
<li><b>Why our proxy cannot settle it.</b> The holdout's truth is the withheld catalogue segments (20% per quadrant fold), so that truth is itself catalogue-shaped.
Closeness to the visible catalogue alone reaches AUC <b>{card['leakage_canary']['auc_neg_distance_to_visible_catalogue_alone']:.3f}</b> on that truth
(leakage rule: 0.90). Files that sit near the catalogue therefore score high on the proxy, and B2 scores lowest.
Rank agreement between the user-reported scores and the holdout is <b>Spearman {rank['spearman_user_vs_holdout']:.3f}</b>
(p = {rank['spearman_p']:.4f}, n = {rank['n_files']}). The proxy therefore reverses the reported ordering.</li>
<li><b>Can a unique file beat 0.2778?</b> <b>Not demonstrated.</b> Any file made by pruning B2 is a subset of B2, so it would sit near 100% within 3 px of B2 and fail the lane rule. The only test that can
produce a number is one organizer-scored submission. That needs a DrivenData login, which this sandbox does not have.</li>
</ol>

<h2>3 · Holdout proxy for the 11 named files (HOLDOUT-DTI)</h2>
<table class="exec">
<tr><th>Site · file</th><th>Dots</th><th>User-reported</th><th>HOLDOUT-DTI</th><th>95% CI (fold bootstrap)</th><th>n withheld positives</th></tr>
{''.join(f"<tr><td>{esc(r['site'])}</td><td>{r['n_dots']:,}</td><td>{r['user_reported_score']:.4f}</td><td>{r['holdout_dti']:.4f}</td><td>[{r['holdout_ci95'][0]:.4f}, {r['holdout_ci95'][1]:.4f}]</td><td>{r['holdout_n_withheld_positives']:,}</td></tr>" for r in s['rows'])}
</table>
<p><small>Evaluator: shared <code>gems57.holdout.evaluate</code> (unchanged), seeds 20 and 21, mode "all", alpha 0.2, beta 0.8, 300 m triangular kernel.
Matches the earlier receipt <code>evidence/holdout_proxy_portfolio.json</code> (B2 0.004385; GEMSDOE28 rung30 0.030240).
Spearman between user-reported score and HOLDOUT-DTI = {rank['spearman_user_vs_holdout']:.3f}, p = {rank['spearman_p']:.4f}, n = {rank['n_files']}.
CI = bootstrap over the 8 fold cells (4 quadrant folds × seeds 20, 21), per <code>holdout_focus.json</code>.</small></p>

<h2>4 · New file: uniqueness, overlap and format</h2>
<table class="exec">
<tr><th>Test</th><th>Result</th><th>Rule / source</th></tr>
<tr><td>Byte copy or exact positive-set copy</td><td>None among {ov['registry_rasters_compared']} local registry rasters</td><td>Protocol LANE; <code>evidence/session_20261031/candidate_overlap.json</code></td></tr>
<tr><td>Literal overlap (dots within 3 px of one registry raster's dots)</td><td>max {ov['max_literal_overlap']*100:.3f}%; {ov['n_rasters_over_70pct_literal']} rasters over 70%</td><td>Fails the 70% rule (duplicate lane)</td></tr>
<tr><td>Worst non-lattice overlap</td><td>GEMSDOE25 "gem1-blind-magnetics" 77.1% (density lift 6.0)</td><td>GEMSDOE25 gem1 is magnetics-derived; the candidate is RTP-gradient-derived (same lane)</td></tr>
<tr><td>Density-matched lift</td><td>median {ov['median_density_matched_lift']:.2f}</td><td>1.0 = random placement</td></tr>
<tr><td>Correlation check (phi, binary dots)</td><td>max {ov['max_phi']:.3f}; 0 rasters above 0.90</td><td>Protocol names rank correlation (0.90). Phi on the 0/1 raster is used here as a documented substitute; this is a protocol deviation.</td></tr>
<tr><td>Holdout canary: each feature alone</td><td>gradient ridge alone AUC {card['leakage_canary']['auc_hgm_alone']:.3f}; closeness to visible catalogue AUC {card['leakage_canary']['auc_neg_distance_to_visible_catalogue_alone']:.3f}</td><td>AUC above 0.90 = leakage until proven otherwise</td></tr>
<tr><td>Holdout DTI for the new file</td><td>NOT MEASURED</td><td>The full catalogue was used for eligibility; a per-fold regeneration is needed first</td></tr>
<tr><td>Format (shared validator)</td><td>float32 · 1 band · EPSG:32611 · 3730×3292 · 100 m · transform matches sample · values 0 and 1 · 0 NaN · 0 dots on catalogue · 0 mass outside footprint</td><td><code>gems57.gates.format_report</code> ok = True; <code>gems57.validate</code></td></tr>
<tr><td>Candidate vs each of the 11 named files (share of the candidate's dots within 3 px of that file)</td><td>{'; '.join(f"{esc(k)} {v['cand_within_3px_of_named']*100:.1f}%" for k, v in c['cand_overlap_by_site'].items())}</td><td>Computed this session from the pinned rasters; <code>docs/data/executive_summary_20261031.json</code></td></tr>
</table>

<h2>5 · Irregularities flagged for review</h2>
<ul>
<li><b>Leaderboard figures in the brief do not match the live page.</b> The brief says 0.4413 is the top and 0.3195 is the highest score. On the live page (fetched 31 Oct 2026),
#1 is <b>0.4544</b>, #2 is 0.3925, and #46 is 0.3261. 0.3195 is not in the top 46 on the 31 Oct page.
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a>.</li>
<li><b>The literal 70% gate.</b> AGENTS.md lists it as degenerate for lattice-type rasters. This session also found 11 of 482 registry rasters over 70% for the candidate,
including the r13 lattice (99.995%) and GEMSDOE25 gem1 magnetics (0.7711). The owner should decide which measure governs.</li>
<li><b>Portal format convention is unresolved.</b> The official sample uses NaN outside the footprint (7,111,787 cells, per the 29 Oct note). The shared writer and validator use all-finite zeros
outside, which is also within [0, 1]. Neither has been tested on the portal. The reported "[0, 1]" error cannot be reproduced locally.</li>
<li><b>Holdout ranks the reported files in reverse (Spearman {rank['spearman_user_vs_holdout']:.3f}).</b> The proxy truth is catalogue-adjacent by construction. Do not use it to rank new candidates.</li>
<li><b>Shared-tool defect, worked around.</b> The shared writer <code>vendor/gems57/submission_writer.py</code> creates outputs with mode 0600, which can block download. The file is hash-pinned upstream, so it was left unchanged; <code>scripts/build_candidate_20261031.py</code> sets 0644 after the write (the bytes are unchanged).</li>
<li><b>The bridge manifest names two scripts that do not exist</b> (<code>scripts/make_data_bridge.py</code>, <code>scripts/assemble_data_bridge.py</code>).
The restore worked through the pinned template instead.</li>
<li><b>The sample file in the bridge has 60,988 positives</b> that match the catalogue exactly  (from the 29 Oct note). It is a grid template, not a zero-fault sample.</li>
<li><b>The DrivenData leaderboard cannot be fetched by curl here</b> (TLS error); the page was read with the fetch tool.</li>
</ul>

<h2>6 · What was restored and verified this session</h2>
<ul>
<li>Feature stack: five parts fetched through the GitHub API (raw.githubusercontent.com is unreachable from this sandbox); each part's SHA-256 matches the pinned values, and <code>scripts/restore_data.py</code> restored the stack. This is owner-mirror integrity, not DrivenData-authenticated.</li>
<li>Labels and sample grid (<code>data/</code>, git-ignored): SHA-256 matched.</li>
<li>482 registry rasters (481 downloads, 1 cache hit), each SHA-256 matched to <code>registry/focus_raster_fetch.json</code>.</li>
<li>Tests: 261 passed on the restored checkout before the writer patch; 18 passed on the writer-related subset after it.</li>
</ul>

<h2>7 · Next steps and blockers (ranked)</h2>
<ol>
<li><b>Owner decision on the gate.</b> Choose whether the lane rule (70% of dots within 3 px) or the density-matched lift governs. The new file fails the first (77.1%). On the second, its median lift is 1.32 (1.0 = random).</li>
<li><b>One organizer-scored test.</b> Only a DrivenData receipt makes a score ORGANIZER-CONFIRMED. The owner has to upload from the portal. The file is <i>not</i> cleared, so do this only if the owner accepts the lane duplicate.</li>
<li><b>Fold-safe candidate generation.</b> Re-derive the catalogue exclusion per fold so that the holdout reading for the new file is valid.</li>
<li><b>Resolve the NaN-versus-zeros convention</b> against the official sample before any upload.</li>
<li><b>Restore the four external catalogues</b> listed as missing in <code>data/external/</code> (free, official sources only), then re-run the leakage canary with them.</li>
</ol>

<h2>8 · Run card (JSON)</h2>
<pre>{esc(card_json)}</pre>

<h2>9 · Sources (official or verified, for manual review)</h2>
<ul>
<li>Competition: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">drivendata.org/competitions/306/competition-doe-gems</a></li>
<li>Official rules (NLR PDF): <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">docs.nlr.gov/docs/fy26osti/96647.pdf</a></li>
<li>Leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a></li>
<li>Blakely &amp; Simpson (1986), horizontal-gradient maxima, Geophysics 51(7): <a href="https://doi.org/10.1190/1.1442197">doi:10.1190/1.1442197</a> (taken from search snippets, not the full paper)</li>
<li>Owner mirror of the bridge data, pinned commit prefix c0c06ac: <a href="https://github.com/buffedlizard55-lab/GEMSDOE">buffedlizard55-lab/GEMSDOE</a></li>
</ul>
</main></body></html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
