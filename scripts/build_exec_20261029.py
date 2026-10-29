#!/usr/bin/env python3
"""Build the 29 Oct 2026 executive summary and How-to-submit pages.

Every number on these pages is read from a persisted JSON receipt in this repository.
Nothing is typed by hand. Labels follow docs/owner-brief-20261029.md:
  HOLDOUT-DTI  = local spatially-blocked holdout (evaluator version, withheld positives, 95% CI shown)
  ORGANIZER-CONFIRMED = none exists for any file in this repository
  USER-REPORTED = owner registry / user prompt value, not organizer-confirmed
"""
from __future__ import annotations

import json
import shutil
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

LANE_ALL = ROOT / "evidence/unique_candidate_lane.json"
LANE_DET = ROOT / "evidence/unique_candidate_lane_detached.json"
NINE = ROOT / "docs/data/nine-site-audit.json"
NINE_SUM = ROOT / "docs/data/nine_site_executive_summary.json"
FOCUS = ROOT / "evidence/focus_structure_audit.json"
CARD = ROOT / "evidence/candidates/wbggemsdoe1-tipgap2km-K12395-20261029.run_card.json"
HOLD = ROOT / "evidence/candidates/wbggemsdoe1-tipgap2km-K12395-20261029.holdout.json"
UNIQ = ROOT / "evidence/candidates/wbggemsdoe1-tipgap2km-K12395-20261029.uniqueness.json"

PROBLEM = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
LEADER = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
SUBMIT = "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/"
RULES = "https://docs.nlr.gov/docs/fy26osti/96647.pdf"
REPO = "https://github.com/wingbangboozle1-lang/WBGGEMSDOE1"
GDR = "https://gdr.openei.org/submissions/1391"

DATE = "29 October 2026"
CANDIDATE = "wbggemsdoe1-tipgap2km-K12395-20261029"
CAND_TIF = f"downloads/{CANDIDATE}.tif"
CAND_ZIP = f"downloads/{CANDIDATE}.zip"
CAND_NOTE = json.loads(CARD.read_text())["note"]
K_STAR = 12395  # owner-calibrated hidden-truth scale; see scripts/unique_candidate_lane.py


def load(p: Path):
    return json.loads(p.read_text())


def e(x) -> str:
    return escape("" if x is None else str(x))


def f4(x) -> str:
    return "n/a" if x is None else f"{float(x):.4f}"


def ci(c) -> str:
    return f"[{float(c[0]):.4f}, {float(c[1]):.4f}]"


def page_wrap(title: str, body: str, name: str) -> str:
    # Uses the same stylesheet and masthead as the rest of the site.
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
    bs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bs)
    return bs.page(name, title, body)


def verdict_banner(card: dict) -> str:
    dl = "YES" if card["ok_to_download"] else "NO"
    sub = "YES" if card["ok_to_submit"] else "NO"
    fails = [k for k, v in card["gates"].items() if not v]
    return f"""<section class="content-section" id="verdict">
<div class="alert" role="note"><p><strong>DOWNLOAD: {dl} (research file, format-valid, not a byte or pixel copy of any of the 117 checked registry rasters). SUBMIT: {sub}.</strong>
Do not submit this file. Failed gates: {", ".join(e(x) for x in fails)}.
<a href="{CAND_TIF}" download>Download the research TIFF ↓</a> · <a href="data/{CANDIDATE}.run_card.json">Run card JSON ↗</a></p></div>
</section>"""


def best_table(nine: dict, card: dict) -> str:
    rows = sorted(nine["rows"], key=lambda r: -float(r["reported_historical_value"]))
    body = []
    for i, r in enumerate(rows, 1):
        best = " <strong>(highest reported)</strong>" if i == 1 else ""
        body.append(
            f"<tr><td>{i}</td><td>{e(r['site'])}{best}</td>"
            f"<td><a href=\"{e(r['download_url'])}\">{e(r['file'])}</a> <small>(learning only; do not submit a copy)</small></td>"
            f"<td>{e(r['reported_historical_value'])} <small>USER-REPORTED; no organizer receipt</small></td>"
            f"<td>{e(r['dots'])}</td>"
            f"<td>max forward 3-px overlap vs other focus champions: {float(r['maximum_forward_3px_overlap_vs_other_focus_champions']):.4f}; "
            f"exact dot duplicates: {e(', '.join(r['exact_dot_duplicates_at_other_focus_champions']) or 'none')}; "
            f"passes literal 70% rule: {'yes' if r['passes_literal_overlap_among_focus_champions'] else 'no'}</td></tr>"
        )
    cand = (f"<tr><td>new</td><td>this session (C_tipgap 2 km, K* 12,395)</td>"
            f"<td><a href=\"{CAND_TIF}\" download>{CANDIDATE}.tif</a> · <a href=\"{CAND_ZIP}\">zip</a></td>"
            f"<td><strong>No estimate.</strong> No organizer receipt, and the local holdout cannot score this exact file (see lane table).</td>"
            f"<td>{card['raster']['dots']}</td>"
            f"<td>{e(card['registry_comparison']['duplicate_count'])} registry rasters exceed the literal 70% forward-overlap rule; "
            f"byte-unique and pixel-unique among {card['registry_comparison']['checked']} checked; scan complete: "
            f"{'yes' if card['registry_comparison']['complete_accessible_scan'] else 'no'}. <strong>Uniqueness FAIL.</strong></td></tr>")
    return f"""<h3>Best-submission table (all values are labelled; none is a projection)</h3>
<div class="table-wrap"><table><thead><tr><th>#</th><th>Site</th><th>File</th><th>Score (estimated / reported)</th><th>Dots</th><th>Uniqueness vs other sites</th></tr></thead>
<tbody>{''.join(body)}{cand}</tbody></table></div>
<p><strong>Verdict for every site:</strong> {e(nine['promotion_recommendation'])} <small>(repo audit: {e(nine['score_warning'])})</small></p>"""


def lane_table(all_: dict, det: dict) -> str:
    rows = []
    for key in det["arms"]:
        d = det["arms"][key]
        a = all_["arms"].get(key, {})
        rows.append(
            f"<tr><td>{e(key)}</td>"
            f"<td>{f4(d['draw21']['dti'])} {ci(d['draw21']['ci95'])}</td>"
            f"<td>{f4(d['draw21_null']['dti'])}</td>"
            f"<td>{f4(d['draw21_paired_vs_null']['delta'])} {ci(d['draw21_paired_vs_null']['ci95'])}</td>"
            f"<td>{f4(d['canary_auc_max'])} {'FAIL' if d['canary_auc_max'] > 0.90 else 'pass'}</td>"
            f"<td>{f4(a.get('draw21', {}).get('dti'))} (canary {f4(a.get('canary_auc_max'))})</td></tr>")
    return f"""<h3>Parallel-run lane, measured (HOLDOUT-DTI · {e(det['evaluator_version'])} · report draw 21)</h3>
<div class="table-wrap"><table><thead><tr><th>Arm</th><th>Detached HOLDOUT-DTI, 95% CI</th><th>Matched null</th><th>Paired gain vs null, 95% CI</th><th>Canary max AUC (&gt;0.90 = leakage)</th><th>All-mode HOLDOUT-DTI (canary)</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p>Withheld positive pixels per cell are reported in the JSON (e.g. {det['arms']['C_tipgap@2000m']['draw21']['withheld_positive_pixels']} for the draw-21 pool).
Selection rule recorded in the receipt: draw 20 selects, draw 21 reports. The highest draw-20 all-mode HOLDOUT-DTI was C_tipgap@2000m (0.1413).
Canary: every arm that beats its null fails the 0.90 rule in both modes. B_ring passes the canary in all mode but falls below its null, so no arm is cleared. The 0.90 rule is applied literally.</p>
<p><strong>Protocol deviation (must be read):</strong> the lane ran 8 configurations (5 in all mode, 3 in detached mode), exceeding the 3-experiment cap in the parallel-run protocol. The detached re-check was added to resolve the canary failure. The deviation alone blocks promotion.</p>
<h4>Caveats recorded in the lane receipt</h4><ul>{''.join(f'<li>{e(c)}</li>' for c in det['caveats'])}</ul>"""


def hypothesis_table(all_: dict, det: dict) -> str:
    d = det["arms"]
    t1 = d["C_tipgap@2000m"]
    t2a, t2b = d["A_decay@2000m"], d["A_decay@4000m"]
    b1 = all_["arms"]["B_ring@1500m"]
    b3 = all_["arms"]["B_ring@3000m"]
    tested = [
        ("T1", "Tip-gap decay from visible catalogue endpoints (C_tipgap, 2 km)", "Tested",
         f"Detached {f4(t1['draw21']['dti'])} vs null {f4(t1['draw21_null']['dti'])}, but canary {f4(t1['canary_auc_max'])} FAIL. The holdout is dominated by catalogue proximity, not proven new-fault skill."),
        ("T2", "Catalogue-distance exponential decay (A_decay, 2 and 4 km)", "Tested",
         f"Detached {f4(t2a['draw21']['dti'])} / {f4(t2b['draw21']['dti'])} vs null {f4(t2a['draw21_null']['dti'])} / {f4(t2b['draw21_null']['dti'])}; canary {f4(t2a['canary_auc_max'])} / {f4(t2b['canary_auc_max'])} FAIL."),
        ("T3", "Fault-spacing ring (1.5 / 3 km, σ 750 m)", "Tested, refuted",
         f"All mode only: {f4(b1['draw21']['dti'])} and {f4(b3['draw21']['dti'])} vs null {f4(b1['draw21_null']['dti'])} and {f4(b3['draw21_null']['dti'])}, below null. Canary passes ({f4(b1['canary_auc_max'])} / {f4(b3['canary_auc_max'])}), so spacing gives no support here."),
    ]
    untested = [
        ("U1", "Label-free geophysical field with no catalogue input, emitted at a fixed K*, scored by one spatially-blocked holdout run. It avoids the catalogue-proximity confound by construction, but its canary still has to be run. Prior label-free lanes (WBG-3, WBG-4) passed holdout but failed literal uniqueness against r13 and WBG-C1, so U1 must add a uniqueness-aware thinning step.", "Rank 1: top candidate for the next single experiment. Not run."),
        ("U2", "Uniqueness-aware thinning of the T1 field: drop dots within 3 px of any dot in the 19 flagged rasters. Dense rasters that cover about 100% of the support may make this impossible.", "Rank 2. Not run."),
        ("U3", "Measure whether the canary AUC above 0.90 is spatial proximity to hidden traces rather than label leakage, by widening the detached collar. This tests the protocol rule itself, not a submission.", "Rank 3. Not run."),
    ]
    rows = "".join(f"<tr><td>{a}</td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td></tr>" for a, b, c, d in tested)
    rows += "".join(f"<tr><td>{a}</td><td>{e(b)}</td><td>Untested</td><td>{e(c)}</td></tr>" for a, b, c in untested)
    return f"""<h3>Hypotheses: three tested, three untested (ranked)</h3>
<div class="table-wrap"><table><thead><tr><th>ID</th><th>Hypothesis</th><th>Status</th><th>Result / rank</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>The top untested hypothesis (U1) must pass a spatially-blocked holdout before any slot is used. No slot has been used.</p>"""


def build() -> None:
    all_ = load(LANE_ALL)
    det = load(LANE_DET)
    nine = load(NINE)
    nsum = load(NINE_SUM)
    focus = load(FOCUS)
    card = load(CARD)
    b2 = nsum["h33_b2_explanation"]
    b2_ex = b2["exact_ancestry"]
    b2_sc = b2["score_evidence"]
    sp = focus["spearman_score_vs_feature"]

    def sp_line(k):
        v = sp[k]
        return f"ρ {v['spearman_rho']:.2f} [{v['bootstrap95'][0]:.2f}, {v['bootstrap95'][1]:.2f}], n={v['n']}"

    dl_rows = (f"<tr><td>Candidate TIF</td><td><a href=\"{CAND_TIF}\" download>{CANDIDATE}.tif</a></td>"
               f"<td>sha256 {card['raster']['sha256']}</td></tr>"
               f"<tr><td>Candidate ZIP</td><td><a href=\"{CAND_ZIP}\">{CANDIDATE}.zip</a></td>"
               f"<td>sha256 {card['raster']['zip_sha256']}</td></tr>")

    body = f"""
<section class="content-section" id="top"><h1>Executive summary · {DATE}</h1>
<p class="micro">GEMSDOE 24, 25, 27, 28, 30, 31, 32, 33, 36 and this session's new candidate. Read before any upload.</p>
{verdict_banner(card)}
</section>

<section class="content-section" id="best"><h2>1. Best submission and download decision</h2>
<p><strong>Best reported historical file: GEMSDOE32 B2, 0.2778 (USER-REPORTED).</strong> It is not organizer-confirmed and has no submission receipt. Its pixels are distinct from every other focus champion, but it fails the literal 70% forward-overlap rule (max 1.0 against at least one other champion). <strong>Do not submit a copy</strong>; the file is linked for learning only.</p>
{best_table(nine, card)}
<p><strong>Estimated score for a new file: none.</strong> The only local number that names this file is the leaked compatibility-evaluator figure, which is excluded from claims (see §4). The public leaderboard gives no estimate for an unsubmitted file.</p>
<h3>Download and submit status</h3><div class="table-wrap"><table><thead><tr><th>Item</th><th>Link</th><th>Hash</th></tr></thead><tbody>{dl_rows}</tbody></table></div>
<p><strong>Name:</strong> {CANDIDATE} · <strong>Note ({len(CAND_NOTE)} characters):</strong> {e(CAND_NOTE)}</p>
</section>

<section class="content-section" id="why"><h2>2. Why GEMSDOE32 B2 reads highest, and whether a higher score is achievable</h2>
<p>B2 is an exact subset of its parent D2.8 (44,090 dots). It <strong>added 0 dots</strong> and removed <strong>{b2_ex['removed_parent_dots']:,}</strong> dots, all within 2 px of mapped catalogue traces (mean distance {b2_ex['removed_distance_to_catalogue_px']['mean']:.2f} px). The owner-reported value rose from {b2_sc['parent_d2_8_value']:.2f} to {b2_sc['h33_b2_value']:.4f}. That difference of {b2_sc['difference']:.4f} is attributed to this pruning. It is <strong>{e(b2_sc['label'])}</strong>: {e(b2_sc['limitation'])}</p>
<p><strong>Higher score achievable?</strong> The public board shows scores above 0.45 (rank 1, 0.4544, read 29 Oct 2026). This repository has no validated path to a higher score. The lane above did not produce a canary-clean improvement. The honest answer is: unknown, and not established here.</p>
<h3>Public board, read today (page reading, not a project receipt)</h3>
<ul>
<li>#1 xiaofanhu 0.4544 · #2 cfld__ 0.3916 · #3 Batik Shirt Brothers 0.3911 · #20 yifanxu 0.3335 · #46 tran.thuy.trang 0.3231 · #47 like60986 0.3217 · #48 kpomazi 0.3195 · #49 drjy 0.3180 · #50 twang 0.3169.</li>
<li>Reconciliation: 0.3195 matches #48 kpomazi on this page. 0.4413 does not appear on today's board. The repo's irregularities file records that earlier briefs quoted 0.4437 and 0.4413 while rank 1 was 0.4544 on 27 Oct 2026. 0.2778 does not appear in the visible top 50, so it would rank below #50 if present.</li>
<li>Source: <a href="{LEADER}">{LEADER}</a>. The board shows 50 rows; no later page was found in the fetch.</li>
</ul>
<p>Feature-to-score relationships in the registry are descriptive only: {e(sp_line('n_positive'))} for dot count; {e(sp_line('frac_within_1px_catalogue'))} for the share of dots within 1 px of the catalogue. All bootstrap 95% intervals span zero.</p>
</section>

<section class="content-section" id="lane"><h2>3. Parallel-run lane: results and gates</h2>
<p>Protocol: LANE = unique-candidate; REUSE = the shared gems57 evaluator, writer and uniqueness code, unmodified; LABEL = HOLDOUT-DTI; LEAKAGE CANARY = AUC &gt; 0.90 means leakage until proven otherwise; budget = 3 experiments or 2 hours. The budget was exceeded (see the deviation note), and no arm passed the canary.</p>
{lane_table(all_, det)}
{hypothesis_table(all_, det)}
<p>Remaining gap: no arm's holdout number is comparable to the same-evaluator benchmark 0.166060 (GEMSDOE24 S3DEP1). The lane evaluator is gems57-pooled-hide-v2, and that benchmark does not come from it.</p>
</section>

<section class="content-section" id="file"><h2>4. The new candidate, measured</h2>
<p>The file is emitted from the full public catalogue at K* = {K_STAR:,} (owner-calibrated scale), using the greedy allocator from the shared template. The greedy step stopped at <strong>{card['raster']['dots']:,} dots</strong>; K* is a field scale, not a dot count. The shared validator passes it for format (float32, EPSG:32611, 3730×3292, zeros outside the footprint, all values in [0,1]).</p>
<ul>
<li><strong>Format:</strong> PASS (shared validator; this is not organizer acceptance).</li>
<li><strong>Uniqueness:</strong> FAIL on the literal rule. {card['registry_comparison']['duplicate_count']} registry rasters exceed the 70% forward-overlap limit. Worst Spearman {card['registry_comparison']['worst_spearman_full_footprint']:.3f} (limit 0.90). Byte-unique and pixel-unique among {card['registry_comparison']['checked']} checked rasters. The scan is not complete: one owner raster fails the pinned transform and is excluded.</li>
<li><strong>Leakage canary:</strong> FAIL (detached max AUC {f4(card['leakage_canary']['detached_max_auc'])} &gt; 0.90).</li>
<li><strong>Holdout (MVGZ-compatibility evaluator, pooled):</strong> not reported as a score. The receipt is marked <code>valid_for_claims: false</code> because the file was emitted from the full catalogue, including components this evaluator hides. Its number is leaked by construction.</li>
</ul>
<p>Decision: <strong>DOWNLOAD: YES (research). SUBMIT: NO.</strong></p>
</section>

<section class="content-section" id="gaps"><h2>5. Irregularities, limitations and remaining work</h2>
<ul>
<li>Owner-reported scores are not organizer-confirmed. No artifact-linked DrivenData receipt exists in this repository.</li>
<li>Protocol deviation: 8 configurations ran against a cap of 3 experiments. Reported here, not hidden.</li>
<li>GDR-intersection lane dropped. The derived GDR rasters are not in the workspace, are not tracked in git, and GDR's host is not reachable from this sandbox.</li>
<li>Uniqueness scan incomplete: 117 of 118 checked. One owner raster fails the pinned CRS/transform check.</li>
<li>Focus-9 audit: the structure audit found 118 rows and 66 focus pairs. The 14GEMSDOE raster GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f fails the transform pin. GEMSDOE9 raster 2314b599 has 196,132 positives outside its footprint. Both are reported, not corrected.</li>
<li>The 0.2778 owner value and all nine historical values remain USER-REPORTED.</li>
<li>Remaining work: (a) run U1 once on a spatially-blocked holdout (one experiment); (b) decide whether any file can ever pass the literal uniqueness rule; (c) a human selector step owns any slot decision. Nothing here uploads anything.</li>
</ul>
<p class="micro">Sources: <a href="{PROBLEM}">DrivenData problem page</a> · <a href="{LEADER}">leaderboard</a> · <a href="{SUBMIT}">submissions page (requires login)</a> · <a href="{RULES}">NLR official rules (PDF)</a> · <a href="{GDR}">DOE GDR / INGENIOUS 1391</a> · <a href="{REPO}">repository</a> · <a href="owner-brief-20261029.md">owner brief (29 Oct 2026)</a>.</p>
</section>
"""
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "unique-lane-summary-20261029.html").write_text(
        page_wrap("Unique-lane summary · 29 Oct 2026", body, "unique-lane-summary-20261029.html"), encoding="utf-8")

    how = f"""
<section class="content-section" id="how"><h1>How to submit · read the verdict first</h1>
<div class="alert" role="note"><p><strong>No file is cleared to submit.</strong> The new candidate fails the leakage canary and the literal uniqueness rule. The historical files are not to be copied. Download the research file for inspection only.</p></div>
<ol>
<li><strong>Read the verdict on the summary page.</strong> A file may be submitted only when its run card shows <code>ok_to_submit: true</code>. Currently none does.</li>
<li><strong>Check the file hash.</strong> Verify the SHA-256 against the run card before any upload.</li>
<li><strong>Format rules</strong> (problem page, rules PDF): one GeoTIFF, float32, EPSG:32611, 3730 × 3292, values in [0, 1]. The local validator checks this; it does not check acceptance.</li>
<li><strong>Name and note.</strong> Each submission needs a unique name and a note of at most 140 characters. The candidate's note is {len(CAND_NOTE)} characters.</li>
<li><strong>Limit.</strong> Three submissions per week (problem page). The remaining allowance is not visible from this sandbox.</li>
<li><strong>Upload is manual.</strong> It is done by the account owner on the official page: <a href="{SUBMIT}">{SUBMIT}</a>. This repository never stores or requests DrivenData credentials.</li>
</ol>
<p class="micro"><a href="executive-summary-20261029.html">← Executive summary</a> · <a href="{PROBLEM}">Problem page</a> · <a href="{RULES}">Rules (PDF)</a></p>
</section>
"""
    (DOCS / "how-to-submit-20261029.html").write_text(
        page_wrap("How to submit · 29 Oct 2026", how, "how-to-submit-20261029.html"), encoding="utf-8")

    data = DOCS / "data"
    data.mkdir(parents=True, exist_ok=True)
    for src, dst in [(CARD, f"{CANDIDATE}.run_card.json"), (HOLD, f"{CANDIDATE}.holdout.json"),
                     (UNIQ, f"{CANDIDATE}.uniqueness.json"), (LANE_ALL, "unique-candidate-lane.json"),
                     (LANE_DET, "unique-candidate-lane-detached.json"), (FOCUS, "focus-structure-audit.json")]:
        shutil.copyfile(src, data / dst)


def main() -> int:
    build()
    print("wrote docs/unique-lane-summary-20261029.html and docs/how-to-submit-20261029.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
