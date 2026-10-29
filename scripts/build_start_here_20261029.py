#!/usr/bin/env python3
"""Build the 29 Oct 2026 START-HERE executive summary from measured receipts only.

Inputs (all local, reproducible):
  * evidence/session_20261029/overlap_*.json  (scripts/measure_registry_overlap.py, shared gate)
  * .cache/scored/*.tif                       (owner-reported registry, hash-checked by fetch_scored_rasters.py)
  * data/bridge/existing_faults.tif, sample_submission.tif (pinned grid + catalogue)
Outputs:
  * evidence/session_20261029/summary.json
  * docs/start-here-20261029.html
Estimated scores are NOT computed here: no validated estimator exists (see IR-WBG5-01).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.uniqueness import _near, OVERLAP_LIMIT  # noqa: E402

EV = ROOT / "evidence/session_20261029"
NINE = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
CANDIDATES = [
    ("WBG-6 (wbg6-qmh-kdisjoint-30000-20261028)", "docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif", "overlap_wbg6.json"),
    ("WBG-7 (wbg7-blind-tip-splay-relay-30000-20261028-zeros)", "docs/downloads/wbg7-blind-tip-splay-relay-30000-20261028-zeros.tif", "overlap_wbg7-blind-tip-splay-relay-30000-20261028-zeros.json"),
    ("Main-lane adjacency (WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z)", "docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif", "overlap_WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.json"),
    ("Focus-9 synthetic null (wbggemsdoe1-focus9-exec-20261027-unique-36k-zeros)", "docs/downloads/wbggemsdoe1-focus9-exec-20261027-unique-36k-zeros.tif", "overlap_wbggemsdoe1-focus9-exec-20261027-unique-36k-zeros.json"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_bin(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        return ds.read(1) > 0


def validator(p: Path) -> dict:
    out = subprocess.run([str(ROOT / ".venv/bin/python"), "scripts/validate_submission.py", str(p)],
                         capture_output=True, text=True, cwd=ROOT, check=True).stdout
    d = json.loads(out)
    return {"format_checks_passed": bool(d["all_checks_passed"]),
            "validator_ok_to_submit_flag": bool(d.get("ok_to_submit")),
            "run_card_matches_exact_tiff": bool(d.get("run_card_matches_exact_tiff"))}


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    reg = json.loads((ROOT / "registry/wbg_h1/scored_registry.json").read_text())["entries"]
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    cat = read_bin(ROOT / "data/bridge/existing_faults.tif")
    d_cat = ndi.distance_transform_edt(~cat)

    # ---- candidate files (new TIFFs) -------------------------------------------------
    cand_rows = []
    for label, rel, ov_name in CANDIDATES:
        p = ROOT / rel
        ov = json.loads((EV / ov_name).read_text())
        v = validator(p)
        fails = [r["submission"] for r in ov["rows"] if r.get("duplicate_by_overlap")]
        cand_rows.append({
            "label": label, "file": rel, "sha256": sha(p), "dots": ov["my_dots"],
            "format_checks_passed": v["format_checks_passed"],
            "validator_ok_to_submit_flag": v["validator_ok_to_submit_flag"],
            "registry_rasters_checked": ov["registry_rasters_unique_checked"],
            "rasters_over_70pct_3px": ov["rasters_over_limit"],
            "worst_3px_overlap": ov["worst_overlap"], "worst_against": ov["worst_against"],
            "over_limit_examples": fails[:3],
            "passes_literal_70pct_gate": ov["passes_literal_overlap_gate"],
            "estimated_leaderboard_score": "UNAVAILABLE (no validated estimator)",
        })

    # ---- nine-site registry table ---------------------------------------------------
    nine, seen = [], {}
    for e in reg:
        if e["repo"] not in NINE:
            continue
        p = ROOT / ".cache/scored" / f"{e['repo']}__{os.path.basename(e['path'])}"
        a = read_bin(p)
        dd = d_cat[a]
        seen[e["name"]] = (a, e)
        nine.append({"site": e["repo"], "name": e["name"], "owner_reported_score": e["score"],
                     "dots": int(a.sum()), "sha256": e["sha256"], "repo_path": e["path"],
                     "dots_on_catalogue": int((dd == 0).sum()),
                     "share_within_3px_of_catalogue": round(float((dd <= 3).mean()), 4),
                     "median_distance_to_catalogue_px": round(float(np.median(dd)), 1)})
    names = list(seen)
    for row in nine:
        a = seen[row["name"]][0]
        best, identical_to, over = 0.0, [], []
        for other in names:
            if other == row["name"]:
                continue
            b = seen[other][0]
            if np.array_equal(a, b):
                identical_to.append(other)
            from gems57.uniqueness import dot_overlap
            ov = dot_overlap(a.astype(np.float32), b.astype(np.float32))
            best = max(best, ov)
            if ov > OVERLAP_LIMIT:
                over.append(other)
        row["max_3px_overlap_vs_other_nine_site_rasters"] = round(best, 6)
        row["identical_dot_sets_with"] = identical_to
        row["rasters_over_70pct_vs_others"] = len(over)
    nine.sort(key=lambda r: -r["owner_reported_score"])

    # ---- literal-gate ceiling: dots that can be placed outside r13's 3-px support ----
    r13 = [e for e in reg if "r13-lattice-s5" in e["name"]][0]
    r13a = read_bin(ROOT / ".cache/scored" / f"{r13['repo']}__{os.path.basename(r13['path'])}")
    near13 = _near(r13a)
    free = foot & ~near13
    rr = 5
    yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
    disk = yy * yy + xx * xx <= rr * rr
    blocked = np.zeros_like(free)
    greedy = 0
    for y, x in zip(*np.nonzero(free)):
        if blocked[y, x]:
            continue
        greedy += 1
        y0, y1, x0, x1 = max(0, y - rr), min(free.shape[0], y + rr + 1), max(0, x - rr), min(free.shape[1], x + rr + 1)
        blocked[y0:y1, x0:x1] |= disk[y0 - (y - rr):y1 - (y - rr), x0 - (x - rr):x1 - (x - rr)]
    ceiling = {
        "r13_raster": r13["name"], "r13_dots": int(r13a.sum()),
        "r13_support_share_of_footprint": round(float((near13 & foot).sum() / foot.sum()), 5),
        "footprint_pixels": int(foot.sum()), "r13_free_footprint_pixels": int(free.sum()),
        "greedy_5px_separated_dots_in_r13_free_area": int(greedy),
        "max_total_dots_if_30pct_must_be_outside_r13_ceiling_estimate": int(greedy / 0.30),
        "note": "greedy lower bound on placeable dots, not a proven maximum; competitive history files carry 37,654-44,090 dots",
    }

    summary = {
        "schema": "start-here-20261029-v1",
        "built_by": "scripts/build_start_here_20261029.py",
        "leaderboard_observation": {"source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
                                    "fetched_utc_date": "2026-10-29", "top_public_score": 0.4544,
                                    "top_user": "xiaofanhu", "label": "PUBLIC-PAGE OBSERVATION (not a project receipt)"},
        "official_rules": {"source": "https://www.nlr.gov/docs/fy26osti/96647.pdf",
                           "single_geotiff_100m": True, "three_submissions_per_week": True,
                           "single_final_submission": True,
                           "uniqueness_or_overlap_gate": False,
                           "originality_clause": "Appendix A.5: entire submission is an original work by the competitor"},
        "candidate_files": cand_rows,
        "nine_site_registry": nine,
        "literal_gate_ceiling": ceiling,
        "registry_entries": len(reg),
        "registry_unique_rasters_by_sha256": len({sha(ROOT / '.cache/scored' / f"{e['repo']}__{os.path.basename(e['path'])}") for e in reg if (ROOT / '.cache/scored' / f"{e['repo']}__{os.path.basename(e['path'])}").exists()}),
    }
    (EV / "summary.json").write_text(json.dumps(summary, indent=1))
    (ROOT / "docs/start-here-20261029.html").write_text(render(summary))
    print("wrote", EV / "summary.json", "and docs/start-here-20261029.html")
    return 0


def esc(x) -> str:
    return html.escape(str(x))


def render(s: dict) -> str:
    c = s["candidate_files"]
    w6 = c[0]
    rows_c = "".join(
        f"<tr><td>{esc(r['label'])}<br><a href=\"{esc(r['file'])}\">{esc(r['file'])}</a><br><small>SHA-256 <code>{esc(r['sha256'])}</code></small></td>"
        f"<td>{r['dots']:,}</td><td>{'PASS' if r['format_checks_passed'] else 'FAIL'}</td>"
        f"<td>{r['rasters_over_70pct_3px']} of {r['registry_rasters_checked']} (worst {r['worst_3px_overlap']:.4f} vs {esc(r['worst_against'])})</td>"
        f"<td>{'YES' if r['passes_literal_70pct_gate'] else 'NO'}</td>"
        f"<td>{esc(r['estimated_leaderboard_score'])}</td>"
        f"<td class=\"no\">NOT CLEARED under the 70% protocol</td></tr>"
        for r in c)
    rows_n = "".join(
        f"<tr><td>{esc(r['site'])}</td><td>{esc(r['name'])}</td><td>{r['owner_reported_score']:.4f}</td>"
        f"<td>{r['dots']:,}</td><td>{r['dots_on_catalogue']}</td><td>{r['share_within_3px_of_catalogue']:.3f}</td>"
        f"<td>{r['median_distance_to_catalogue_px']}</td>"
        f"<td>{'; '.join(esc(x) for x in r['identical_dot_sets_with']) or '—'}</td>"
        f"<td>{r['max_3px_overlap_vs_other_nine_site_rasters']:.3f}</td>"
        f"<td class=\"no\">DO NOT SUBMIT (another team's prior submission; A.5)</td></tr>"
        for r in s["nine_site_registry"])
    g = s["literal_gate_ceiling"]
    lb = s["leaderboard_observation"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>START HERE — GEMS submission status · 29 Oct 2026</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f5f7f6;color:#1b2a2a;line-height:1.5}}
main{{max-width:1100px;margin:0 auto;padding:24px}}
h1{{font-size:1.7rem;margin:.2rem 0}} h2{{margin-top:2rem;border-bottom:2px solid #c8d6d3;padding-bottom:.3rem}}
.banner{{background:#fff4d6;border:2px solid #b7791f;border-radius:10px;padding:16px 20px}}
.verdict{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}}
.box{{padding:12px;border-radius:8px;background:#fff;border:1px solid #d6e0dd}}
.box.red{{border-color:#c53030;background:#fff5f5}} .box.green{{border-color:#2f855a;background:#f0fff4}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:.88rem;margin:.6rem 0}}
th,td{{border:1px solid #d6e0dd;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#e8f0ee}} td.no{{color:#9b2c2c;font-weight:600}} code{{font-size:.8rem;word-break:break-all}}
small{{color:#4a5a5a}} .tag{{display:inline-block;font-size:.75rem;padding:1px 6px;border-radius:4px;background:#e2e8f0}}
ul li{{margin:.25rem 0}}
</style></head><body><main>
<p><span class="tag">Built from measured receipts · {esc(s['built_by'])}</span></p>
<h1>START HERE — which file to download and submit</h1>

<div class="banner"><strong>Bottom line (29 Oct 2026):</strong> <strong>No file is cleared for submission under your 70% uniqueness protocol.</strong>
The only format-valid, original-generated file we hold is WBG-6. It <em>fails</em> the 70% gate against {w6['rasters_over_70pct_3px']} registry rasters.
The highest owner-reported historical file (GEMSDOE32 B2, 0.2778) is another team's prior submission; submitting it would breach the official \"original work\" clause (A.5).
We have <strong>no validated score estimate</strong> for any new file.
<div class="verdict">
<div class="box green"><strong>DOWNLOAD — allowed for review only</strong><br>
<a href="{esc(w6['file'])}">{esc(w6['file'])}</a><br><small>Format checks pass · 30,000 dots · values 0/1 (in [0,1]) · EPSG:32611 · 3,730×3,292 · 100 m</small></div>
<div class="box red"><strong>SUBMIT — NO (not cleared)</strong><br>Your protocol says overlap &gt; 70% = duplicate. WBG-6 is {w6['worst_3px_overlap']*100:.2f}% overlapping with <code>{esc(w6['worst_against'])}</code>. The official rules contain <em>no</em> overlap gate (see below), so this is a decision for you, not for the code.</div>
</div></div>

<h2>1. Candidate files — what to download, estimated score, uniqueness</h2>
<p>Estimated leaderboard score: <strong>UNAVAILABLE for every file.</strong> The shared holdout does not rank real submissions (Spearman 0.144, p = 0.12, n = 118; <a href="../evidence/holdout_proxy_portfolio.json">evidence/holdout_proxy_portfolio.json</a>). The older 0.247 figure for WBG-6 is a model estimate that is not validated and is not used here.</p>
<table><thead><tr><th>File (download)</th><th>Dots</th><th>Format</th><th>Literal 3-px gate: rasters over 70%</th><th>Passes 70% gate?</th><th>Estimated score</th><th>Submit decision</th></tr></thead>
<tbody>{rows_c}</tbody></table>
<p><small>Measured by <code>scripts/measure_registry_overlap.py</code> (uses the shared <code>vendor/gems57/uniqueness.dot_overlap</code>) against {w6['registry_rasters_checked']} unique registry rasters (owner-reported). Receipts: <code>evidence/session_20261029/overlap_*.json</code>.</small></p>

<h2>2. Nine focus sites — highest owner-reported files (all are other teams' prior submissions)</h2>
<p>Owner-reported scores are <strong>not organizer-confirmed</strong>. Sorted by score. "Share within 3 px of catalogue" is the fraction of dots within 3 px of a mapped fault; no dot sits on a mapped fault in any of these files.</p>
<table><thead><tr><th>Site</th><th>Registry name</th><th>Owner score</th><th>Dots</th><th>On catalogue</th><th>Share ≤3 px of catalogue</th><th>Median px to catalogue</th><th>Identical dot sets with</th><th>Max 3-px overlap vs other nine-site rasters</th><th>Submit?</th></tr></thead>
<tbody>{rows_n}</tbody></table>
<ul>
<li><strong>Uniqueness among the nine sites fails the literal 70% test:</strong> most pairs overlap at 0.97–1.00. Two pairs have identical dot sets (GEMSDOE25 = GEMSDOE30; GEMSDOE28 h27-4-r1 = GEMSDOE31 h27-4-solo).</li>
<li><strong>Why GEMSDOE32 B2 (0.2778) ranks highest in the owner's data (measured, association only):</strong> it has zero dots on the catalogue, the lowest share of dots near a mapped fault among the top files (5.8%), and a median distance of 19.6 px. The 0.2600 files, with 19.5% of dots near a fault, sit lower. Six files is too few to prove causation.</li>
<li><strong>Can we beat 0.2778?</strong> Not demonstrated. We have no validated estimator and no organizer receipt. Only a real public-leaderboard submission can answer this, and that spends one of the three weekly submissions.</li>
</ul>

<h2>3. Why no new file is generated in this session</h2>
<ul>
<li>The literal 70% rule cannot be met at competitive dot counts. The r13 lattice (206,895 dots) covers <strong>{g['r13_support_share_of_footprint']*100:.2f}%</strong> of the footprint. Only {g['r13_free_footprint_pixels']:,} footprint pixels are outside its 3-px reach.</li>
<li>A greedy estimate places about {g['greedy_5px_separated_dots_in_r13_free_area']:,} dots (5 px apart) in that area. Keeping 30% of dots outside r13 caps the total at roughly <strong>{g['max_total_dots_if_30pct_must_be_outside_r13_ceiling_estimate']:,}</strong> dots. Competitive files carry 37,654–44,090.</li>
<li>Writing another file of the same family would only add a near-duplicate of WBG-6 with no validated gain.</li>
</ul>

<h2>3b. Other sessions merged to main on 29 Oct (read with this page)</h2>
<ul>
<li><strong>Main-lane adjacency file is a leakage case (NEGATIVE):</strong> archived HOLDOUT-DTI 0.4657 (CI95 [0.4563, 0.4748], n=60,161) falls to <strong>0.0069</strong> when placement uses only visible faults per fold. Leakage canary: distance-to-visible-catalogue AUC 0.829, below the 0.90 threshold. Source: <a href="../evidence/per_fold_recheck_blind_adjacency.json">evidence/per_fold_recheck_blind_adjacency.json</a>. Its 129,184 dots and 19 registry rasters over 70% make it DO NOT SUBMIT.</li>
<li>Parallel focus-9 summary: <a href="../docs/executive-summary-focus9-20261029.md">docs/executive-summary-focus9-20261029.md</a>. Its conclusion (no file cleared) matches this page.</li>
</ul>

<h2>4. Official sources checked (fetched 29 Oct 2026)</h2>
<ul>
<li>Problem description (metric, labels, one submission): <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">drivendata.org …/page/967/</a></li>
<li>About the data and task: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">drivendata.org …/page/968/</a></li>
<li>Official rules (single GeoTIFF, 100 m, three submissions per week, one final submission, A.5 original work; no overlap gate): <a href="https://www.nlr.gov/docs/fy26osti/96647.pdf">nlr.gov/docs/fy26osti/96647.pdf</a></li>
<li>Public leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">drivendata.org …/leaderboard/</a> — top public score <strong>{lb['top_public_score']:.4f}</strong> ({esc(lb['top_user'])}); this is a public-page observation, not a project receipt. The prompt's figures 0.4413 and 0.3195 do not match this page.</li>
</ul>

<h2>5. Irregularities flagged for human review</h2>
<ul>
<li><strong>IR-29-01 (high):</strong> WBG-6's run card and its validator report <code>ok_to_submit: true</code>, while the registry overlap test fails. The card's claim that the literal gate is "degenerate" is an override of your protocol. The validator's flag is <em>not</em> a uniqueness clearance.</li>
<li><strong>IR-29-02 (high):</strong> <code>AGENTS.md</code> said WBG-6 was "APPROVED FOR SUBMISSION"; the README said nothing is cleared. Corrected in this session.</li>
<li><strong>IR-29-03 (high):</strong> the literal 70% gate cannot be satisfied at competitive dot counts (see section 3). Your protocol and the official rules disagree.</li>
<li><strong>IR-29-04 (medium):</strong> the leaderboard values differ: prompt 0.4413 and 0.3195; repo 0.4544; live page 0.4544.</li>
<li><strong>IR-29-05 (medium):</strong> the nine-site registry has 12 entries for 9 sites; identical dot sets appear across sites (section 2).</li>
<li><strong>IR-29-06 (medium):</strong> the "Predicted values must be in range [0, 1]" error from the portal is not reproduced by WBG-6 (binary 0/1). The user's rejected file was not supplied, so its cause is unknown.</li>
<li><strong>IR-29-07 (medium):</strong> the official rules require the competitor's entire submission to be an original work (A.5). Submitting any file from the registry would breach that clause.</li>
</ul>

<h2>6. Decisions needed from you (next steps)</h2>
<ol>
<li><strong>Decide the uniqueness gate.</strong> Option A: use the official rules (no overlap gate; original work plus format pass). Under A, WBG-6 is downloadable and submittable, but it still needs a slot decision by you. Option B: keep the 70% gate. Under B, no competitive file can pass, so the decision is to stop.</li>
<li><strong>Spend one weekly slot on a public-leaderboard probe.</strong> The only real score feedback is an organizer score. Doing this would turn WBG-6's estimate into an ORGANIZER-CONFIRMED number. This is your call; we have not submitted anything.</li>
<li><strong>Provide the rejected file</strong> from the portal error, so IR-29-06 can be reproduced.</li>
</ol>

<p><small>Machine-readable: <a href="../evidence/session_20261029/summary.json">evidence/session_20261029/summary.json</a>. Builder: <a href="../scripts/build_start_here_20261029.py">scripts/build_start_here_20261029.py</a>. Nothing in this page was uploaded or submitted.</small></p>
</main></body></html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
