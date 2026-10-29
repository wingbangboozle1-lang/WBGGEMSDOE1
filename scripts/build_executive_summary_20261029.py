#!/usr/bin/env python3
"""Build the 2026-10-29 executive summary (HTML + JSON) from measured receipts only.

Inputs (all produced by scripts in this session):
  docs/data/focus9_top_table_20261029.json          nine top files, measured
  evidence/tip_continuation_20261029/uniqueness.json  registry scan of the new file
  evidence/tip_continuation_20261029/run_card.json    run card (holdout, validator, name)
  evidence/tip_continuation_20261029/holdout.json     fold-wise holdout
  evidence/tip_continuation_20261029/superseded_E1_gate_bug/  first run, kept for audit

Adds one computed table: pairwise 3 px dot overlap among the nine focus top files.
Leaderboard figures are fetched and pinned below with their source URL and fetch date.

Usage: /tmp/venv/bin/python scripts/build_executive_summary_20261029.py --focus /tmp/focus
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence/tip_continuation_20261029"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"

LEADERBOARD = {
    "source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
    "fetched": "2026-10-29",
    "rows": [("#1", "xiaofanhu", 0.4544), ("#2", "cfld__", 0.3916), ("#3", "Batik Shirt Brothers", 0.3911)],
}
OFFICIAL = {
    "rules_pdf": "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
    "problem_page": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
}
PROMPT_LEADER_VALUES = [0.4413, 0.3195]


def pairwise_overlap(paths: dict[str, Path]) -> dict:
    with rasterio.open(TEMPLATE) as s:
        foot = np.isfinite(s.read(1))
    pos = {}
    for k, p in paths.items():
        with rasterio.open(p) as s:
            a = s.read(1)
        pos[k] = np.argwhere(np.isfinite(a) & (a > 0) & foot)
    trees = {k: cKDTree(v) for k, v in pos.items()}
    names = list(paths)
    mat = {}
    for i in names:
        for j in names:
            if i == j:
                mat[(i, j)] = 1.0
                continue
            d, _ = trees[j].query(pos[i], k=1)
            mat[(i, j)] = float((d <= 3.0).mean())
    return {"names": names, "matrix": {f"{i}|{j}": v for (i, j), v in mat.items()}}


def fmt(x, nd=4):
    return "—" if x is None else f"{x:.{nd}f}"


def pct(x):
    return "—" if x is None else f"{100 * x:.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", type=Path, default=Path("/tmp/focus"))
    args = ap.parse_args()

    top = json.loads((ROOT / "docs/data/focus9_top_table_20261029.json").read_text())
    uniq = json.loads((EVID / "uniqueness.json").read_text())
    card = json.loads((EVID / "run_card.json").read_text())
    hold = json.loads((EVID / "holdout.json").read_text())
    old = json.loads((EVID / "superseded_E1_gate_bug/holdout.json").read_text())
    old_card = json.loads((EVID / "superseded_E1_gate_bug/run_card.json").read_text())

    rows = {r["site"]: r for r in top["rows"]}
    paths = {s: args.focus / s / r["repo_path"].split("!")[0] for s, r in rows.items() if r.get("repo_path")}
    pair = pairwise_overlap(paths)
    M = pair["matrix"]

    def max_other(site):
        vals = [M[f"{site}|{o}"] for o in pair["names"] if o != site]
        return max(vals)

    site_rows = []
    for s in ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]:
        r = rows[s]
        mo = max_other(s)
        site_rows.append({
            "site": s,
            "file_to_download": r["github_raw_url"],
            "repo_path": r["repo_path"],
            "raster_sha256": r["raster_sha256"],
            "user_reported_score": r["user_reported_score"],
            "estimated_score": "UNAVAILABLE (no measurable estimate in this repo; not inferred)",
            "positive_dots": r["positive_px"],
            "outside_convention": r["outside_convention"],
            "share_within_200m_of_catalogue": r["share_within_200m_of_catalogue"],
            "min_dist_to_catalogue_m": r.get("min_dist_to_catalogue_m"),
            "max_overlap_vs_other_9_sites_3px": mo,
            "unique_vs_other_9_sites": bool(mo <= 0.70),
            "overlap_with_new_file_3px": r["overlap_with_candidate_3px"],
        })
    dup_pairs = [(i, j, M[f"{i}|{j}"]) for i in pair["names"] for j in pair["names"] if i < j and M[f"{i}|{j}"] > 0.70]

    # Measured: is GEMSDOE32 B2 exactly the GEMSDOE31 h27-4 base minus its catalogue-near dots?
    from scipy.ndimage import distance_transform_edt
    with rasterio.open(TEMPLATE) as s_:
        foot_ = np.isfinite(s_.read(1))
    with rasterio.open(ROOT / "data/bridge/labels.tif") as s_:
        fault_ = s_.read(1) == 1
    d_cat = distance_transform_edt(~fault_)
    def _pos(site):
        with rasterio.open(paths[site]) as s_:
            a_ = s_.read(1)
        return np.isfinite(a_) & (a_ > 0) & foot_
    base_m, b2_m = _pos("GEMSDOE31"), _pos("GEMSDOE32")
    removed = base_m & ~b2_m
    b2_vs_base = {
        "base_site_file": rows["GEMSDOE31"]["repo_path"],
        "b2_site_file": rows["GEMSDOE32"]["repo_path"],
        "base_dots": int(base_m.sum()),
        "b2_dots": int(b2_m.sum()),
        "b2_subset_of_base": bool(not (b2_m & ~base_m).any()),
        "removed_dots": int(removed.sum()),
        "removed_dist_min_m": float(d_cat[removed].min() * 100.0),
        "removed_dist_max_m": float(d_cat[removed].max() * 100.0),
        "removed_all_within_200m": bool((d_cat[removed] <= 2.0).all()),
    }

    s_sum = uniq["summary"]
    lane_stops = [r for r in uniq["rows"] if (r.get("dot_overlap_3px") or 0) > 0.70]
    gd25 = [r for r in lane_stops if r["site"] == "GEMSDOE25"]
    lift_gd25 = [r["dot_overlap_3px"] / r["expected_random_overlap_3px"] for r in gd25]

    decision = {
        "download": "RESEARCH ONLY",
        "submit": "NO",
        "headline": "No file in this repository is cleared for upload. The new TIFF is format-valid and not a byte-duplicate, but it fails the holdout test and the 70% lane gate.",
    }
    nz = card["raster_sha256"]
    summary = {
        "schema": "executive-summary-20261029-v1",
        "decision": decision,
        "new_file": {
            "name": card["submission_name"],
            "note": card["submission_note"],
            "note_chars": card["note_length"],
            "zeros_tif": f"docs/downloads/{card['submission_name']}-zeros.tif",
            "zeros_zip": f"docs/downloads/{card['submission_name']}-zeros.zip",
            "nan_tif": f"docs/downloads/{card['submission_name']}-nan.tif",
            "nan_zip": f"docs/downloads/{card['submission_name']}-nan.zip",
            "sha256_zeros_tif": nz["zeros_tif"],
            "sha256_nan_tif": nz["nan_tif"],
            "dots": card["dots"],
            "estimated_score": "UNAVAILABLE",
            "holdout_dti_catalogue_proxy": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator": hold["evaluator_version"],
                "pooled_dti": hold["pooled_dti"],
                "ci95": hold["ci95"],
                "withheld_positives": hold["withheld_positives"],
                "matched_random_null_dti_2_5_97_5": [card["matched_null"]["dti_p2_5"], card["matched_null"]["dti_p97_5"]],
            },
            "uniqueness": {
                "rasters_scanned": s_sum["rasters_scanned"],
                "exact_or_decoded_duplicates": len(s_sum["exact_or_decoded_duplicates"]),
                "max_abs_spearman": s_sum["max_abs_spearman"],
                "rasters_over_70pct_3px_overlap": len(lane_stops),
                "of_which_GEMSDOE25_family": len(gd25),
                "GEMSDOE25_family_lift_over_chance": [min(lift_gd25), max(lift_gd25)] if lift_gd25 else None,
                "bytes_unique": len(s_sum["exact_or_decoded_duplicates"]) == 0,
                "lane_unique_under_70pct_gate": len(lane_stops) == 0,
            },
            "validator": {
                "zeros_variant": "all finite, zero exterior; fails official 'outside is null or nan' text",
                "nan_variant": "NaN exterior; matches official sample profile; fails repo strict no-NaN check",
            },
            "verdict": card["verdict"],
        },
        "nine_sites": site_rows,
        "nine_site_pairs_over_70pct": [{"a": a, "b": b, "overlap_3px": v} for a, b, v in dup_pairs],
        "nine_site_pairwise_matrix": {"names": pair["names"], "matrix": M},
        "b2_vs_base_0_2708_file": b2_vs_base,
        "leaderboard_pinned": {**LEADERBOARD, "prompt_supplied_values_not_matching_live_page": PROMPT_LEADER_VALUES},
        "experiments": [
            {"id": "E1", "status": "SUPERSEDED - gate bug (axis-aligned traces emitted zero rays)", "dots": old_card["dots"],
             "pooled_dti": old["pooled_dti"], "ci95": old["ci95"]},
            {"id": "E1b", "status": "VALID - run card", "dots": card["dots"], "pooled_dti": hold["pooled_dti"], "ci95": hold["ci95"]},
        ],
        "budget": {"experiments_used": 2, "experiments_allowed": 3, "time_note": "under 2 hours of working time"},
        "irregularities": [
            "Leaderboard top value differs across sources: prompt lists 0.4413 and 0.3195; the live DrivenData page (fetched 2026-10-29) shows #1 0.4544 and #2 0.3916.",
            "AGENTS.md described WBG-6 as APPROVED; its own audit fails the literal 70% gate (3 px overlap 0.99677 vs r13-lattice-s5). Corrected in this session.",
            "GEMSDOE25 and GEMSDOE30 top files have identical positive pixel sets (44,090 dots, all shared) though listed as separate sites, both at 0.2600.",
            "Portal error 'Predicted values must be in range [0, 1]' is unexplained. The official text allows null or NaN outside the footprint; the shared writer defaults to zeros on an unverified claim that NaN is rejected.",
            "The 0.2778 value is USER-REPORTED. No organizer receipt for that file exists in the sources reviewed.",
            "The GEMSDOE32 audit calls B2 a prune of a '0.2708 base'. That base is measured as the GEMSDOE31 h27-4-solo-d28 file (40,199 dots), but the GEMSDOE33 repo's forensic note says the 0.2708 file association is unsupported: no organizer receipt, and the GEMSDOE28 owner page labels H27-4 unscored.",
            "training_features.tif (about 419 MB) is not in the repository and DrivenData requires login; no holdout uses the full feature stack.",
            "The shared holdout collar (15 px) withholds only truth at least 15 px from visible faults. Rays up to 15 px from a visible tip are structurally unable to earn credit. Flagged for review; the shared evaluator was not redesigned.",
            "The literal 70% gate is degenerate against dense lattice rasters: the 206,895-dot r13-lattice-s5 overlaps the new file at 99.9%, where chance expectation is 69.4%.",
        ],
        "limitations": [
            "No organizer score is available for any file in this repository. Every number here is a HOLDOUT-DTI, USER-REPORTED, or a measured local property.",
            "The sandbox cannot reach DrivenData, Dropbox, OpenEI, or the NLR PDF directly. The official rules were read through the page-fetch tool. GitHub and PyPI were reachable.",
            "Holdout uses catalogue segments as stand-in truth. The competition's hidden labels are NEW faults that are not in the catalogue, so a catalogue holdout does not measure the competition target.",
        ],
        "sources": [
            {"label": "Official rules PDF (NLR), sections 3 and submission format", "url": OFFICIAL["rules_pdf"], "checked": "2026-10-29"},
            {"label": "DrivenData problem description (metric, submission format)", "url": OFFICIAL["problem_page"], "checked": "2026-10-29"},
            {"label": "DrivenData leaderboard", "url": LEADERBOARD["source"], "checked": "2026-10-29"},
            {"label": "GEMSDOE32 audit receipt (0.2778 file)", "url": "https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json", "checked": "2026-10-29"},
            {"label": "Competition repo reference solution", "url": "https://github.com/drivendataorg/gems-prize-reference-solution", "checked": "2026-10-29"},
        ],
    }
    (ROOT / "docs/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/data/executive_summary_20261029.json").write_text(json.dumps(summary, indent=1, allow_nan=False, default=str) + "\n")
    (ROOT / "docs/executive-summary-20261029.html").write_text(render(summary))
    print("wrote docs/executive-summary-20261029.html and docs/data/executive_summary_20261029.json")
    return 0


def render(s: dict) -> str:
    e = html.escape
    nf = s["new_file"]
    h = nf["holdout_dti_catalogue_proxy"]
    u = nf["uniqueness"]
    b2 = next(r for r in s["nine_sites"] if r["site"] == "GEMSDOE32")
    bvb = s["b2_vs_base_0_2708_file"]
    zero_sites = ", ".join(r["site"] for r in s["nine_sites"] if r["share_within_200m_of_catalogue"] == 0.0)
    others = [r["share_within_200m_of_catalogue"] for r in s["nine_sites"] if r["site"] != "GEMSDOE32" and r["share_within_200m_of_catalogue"] != 0.0]
    b2_n = b2["positive_dots"]
    b2_zero = f"0 within 200 m (its nearest dot is {b2['min_dist_to_catalogue_m']:.0f} m away)"
    other_n = len(others)
    other_lo, other_hi = pct(min(others)), pct(max(others))
    pv = [p["overlap_3px"] for p in s["nine_site_pairs_over_70pct"]]
    n_pairs = len(s["nine_site_pairwise_matrix"]["names"]) * (len(s["nine_site_pairwise_matrix"]["names"]) - 1) // 2
    pairs_html = (f"{len(pv)} of {n_pairs} site pairs exceed 70% (range {pct(min(pv))} to {pct(max(pv))}); "
                  "the nine top files are one lane, not nine independent submissions") if pv else "none"
    nine_rows = []
    for r in s["nine_sites"]:
        ok = "YES" if r["unique_vs_other_9_sites"] else "NO"
        nine_rows.append(
            "<tr>"
            f"<td><b>{e(r['site'])}</b></td>"
            f"<td><a href=\"{e(r['file_to_download'])}\">{e(r['repo_path'].split('/')[-1])}</a><br><small>sha256 {e(r['raster_sha256'][:16])}…</small></td>"
            f"<td>{e(str(r['user_reported_score']))}<br><small>USER-REPORTED</small></td>"
            "<td>UNAVAILABLE</td>"
            f"<td>{r['positive_dots']:,}</td>"
            f"<td>{pct(r['share_within_200m_of_catalogue'])}</td>"
            f"<td>{pct(r['max_overlap_vs_other_9_sites_3px'])}</td>"
            f"<td><b>{ok}</b></td>"
            f"<td>{pct(r['overlap_with_new_file_3px'])}</td>"
            "</tr>"
        )
    exp_rows = "".join(
        f"<tr><td>{e(x['id'])}</td><td>{e(x['status'])}</td><td>{x['dots'] if x['dots'] is not None else '—'}</td>"
        f"<td>{fmt(x['pooled_dti'], 6)}</td><td>[{fmt(x['ci95'][0], 6)}, {fmt(x['ci95'][1], 6)}]</td></tr>"
        for x in s["experiments"]
    )
    lb = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{c:.4f}</td></tr>" for a, b, c in s["leaderboard_pinned"]["rows"])
    irr = "".join(f"<li>{e(x)}</li>" for x in s["irregularities"])
    lim = "".join(f"<li>{e(x)}</li>" for x in s["limitations"])
    src = "".join(f"<li><a href=\"{e(x['url'])}\">{e(x['label'])}</a> <small>(checked {e(x['checked'])})</small></li>" for x in s["sources"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMS executive summary · 29 Oct 2026</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f7f8fa;color:#1d2330;line-height:1.5}}
main{{max-width:1180px;margin:0 auto;padding:24px}}
.verdict{{background:#fff4f2;border:3px solid #a32626;border-radius:10px;padding:18px 22px;margin-bottom:22px}}
.verdict h1{{margin:0 0 6px;font-size:1.5rem;color:#a32626}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:0.92rem}}
th,td{{border:1px solid #d7dce5;padding:7px 9px;vertical-align:top;text-align:left}}
th{{background:#eef2f7}}
section{{background:#fff;border:1px solid #d7dce5;border-radius:8px;padding:16px 20px;margin:18px 0}}
code{{background:#eef2f7;padding:1px 4px;border-radius:4px}}
small{{color:#5b6472}}
</style></head><body><main>
<div class="verdict">
<h1>DOWNLOAD: RESEARCH ONLY &nbsp;·&nbsp; SUBMIT: NO</h1>
<p><b>{e(s['decision']['headline'])}</b></p>
<p>Checked against the official rules: float32, one band, EPSG:32611, 3,292 × 3,730 at 100 m, values in [0, 1], outside the footprint null or NaN. The rules are at <a href="{e(OFFICIAL['rules_pdf'])}">the NLR PDF</a> and the <a href="{e(OFFICIAL['problem_page'])}">problem page</a>. Scoring is a distance-weighted Tversky index (α = 0.2, β = 0.8, 300 m triangular kernel). Maximum three submissions per week.</p>
</div>

<section><h2>1 · The new file: what to download and what to expect</h2>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Download (recommended, zeros exterior)</td><td><a href="{e(nf['zeros_zip'])}">{e(nf['zeros_zip'])}</a> · raw <a href="{e(nf['zeros_tif'])}">.tif</a></td></tr>
<tr><td>Download (NaN exterior, matches official sample)</td><td><a href="{e(nf['nan_zip'])}">{e(nf['nan_zip'])}</a> · raw <a href="{e(nf['nan_tif'])}">.tif</a></td></tr>
<tr><td>Name / note (≤140 chars, {nf['note_chars']} used)</td><td><code>{e(nf['name'])}</code> — {e(nf['note'])}</td></tr>
<tr><td>Positive dots</td><td>{nf['dots']:,} (binary 0/1), none on the catalogue, none within 200 m of it</td></tr>
<tr><td>sha256 (zeros tif)</td><td><code>{e(nf['sha256_zeros_tif'])}</code></td></tr>
<tr><td>sha256 (nan tif)</td><td><code>{e(nf['sha256_nan_tif'])}</code></td></tr>
<tr><td><b>Estimated leaderboard score</b></td><td><b>UNAVAILABLE.</b> Not measurable here. The only number is a catalogue-proxy HOLDOUT-DTI of {h['pooled_dti']:.6f}, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}] ({h['evaluator']}, {h['withheld_positives']:,} withheld positives). The matched random null is {h['matched_random_null_dti_2_5_97_5'][0]:.4f} to {h['matched_random_null_dti_2_5_97_5'][1]:.4f}. It is a negative result and is not an estimate of the leaderboard score.</td></tr>
<tr><td><b>Unique versus the GEMSDOE sites?</b></td><td><b>Bytes: YES</b> ({u['rasters_scanned']} rasters scanned, {u['exact_or_decoded_duplicates']} duplicates, max |ρ| {u['max_abs_spearman']:.3f}). <b>Lane: NO</b>: {u['rasters_over_70pct_3px_overlap']} rasters exceed the 70% three-pixel gate, {u['of_which_GEMSDOE25_family']} of them in the GEMSDOE25 family at {u['GEMSDOE25_family_lift_over_chance'][0]:.1f}–{u['GEMSDOE25_family_lift_over_chance'][1]:.1f}× chance. Protocol: duplicate, stop.</td></tr>
<tr><td><b>Verdict</b></td><td><b>{e(nf['verdict'].upper())}.</b> Download for research. Do not upload this file.</td></tr>
</table></section>

<section><h2>How to submit, only after a CLEARED verdict</h2>
<ol>
<li>Confirm that the run card for the file reads <code>promote</code>, that the holdout CI is strictly positive, and that the lane gate passes. Today none of those is true for any file here.</li>
<li>Download the ZIP. Verify the sha256 of the TIF inside it against the run card.</li>
<li>Upload the single TIF inside the ZIP. The portal's automatic validation runs on upload; no human inspection is involved.</li>
<li>Use the name and note from the run card (note at most 140 characters). Keep to the 3-per-week cap; a weekly slot is a separate selector step.</li>
</ol>
<p><small>Official: <a href="{e(OFFICIAL['rules_pdf'])}">rules PDF</a> · <a href="{e(OFFICIAL['problem_page'])}">problem page</a>. Portal format error: see irregularities.</small></p></section>

<section><h2>2 · Nine focus sites: file to download, estimated score, uniqueness</h2>
<p>Each row is the top file that each site lists in the supplied history. Each file was matched by name inside its own cloned GitHub repository, and the match had to be unique. Scores are <b>USER-REPORTED</b>, not organizer-confirmed. The uniqueness column compares each site's file with the other eight files in the table (not with the registry). Yes means every pairwise 3 px overlap is 70% or less.</p>
<table>
<tr><th>Site</th><th>File to download</th><th>Reported score</th><th>Estimated score</th><th>Positive dots</th><th>Share within 200 m of catalogue</th><th>Max overlap with other 8 sites</th><th>Unique vs other GEMSDOE sites?</th><th>Overlap with the new file</th></tr>
{''.join(nine_rows)}
</table>
<p><b>Among the nine:</b> {pairs_html}. GEMSDOE25 and GEMSDOE30 are pixel-identical in dots.</p>
</section>

<section><h2>3 · Why the 0.2778 file scored highest, and what we can measure</h2>
<ul>
<li><b>Measured (this repo):</b> GEMSDOE32 B2 is exactly the GEMSDOE31 <code>h27-4-solo-d28</code> file minus {bvb['removed_dots']:,} dots (B2 is a subset of that base: {bvb['b2_subset_of_base']}). All removed dots lie {bvb['removed_dist_min_m']:.0f}–{bvb['removed_dist_max_m']:.0f} m from the catalogue. B2 has {b2_n:,} binary dots, none on the USGS/INGENIOUS catalogue and {b2_zero}. Its outside convention is zeros, and a NaN twin with identical dots is also published. Share of dots within 200 m of the catalogue: {zero_sites} at 0.0%; the other {other_n} files range from {other_lo} to {other_hi}.</li>
<li><b>Hypothesis, not proven:</b> the metric charges false positives at 0.2 and false negatives at 0.8. Dots within 200 m of a mapped fault mainly duplicate structure that is already mapped, and the hidden labels are new faults, so those dots add false-positive weight. The only difference between B2 and its base is that removal, which is measured. The score difference is not: the 0.2708 attribution for the base is flagged as unsupported by the owner's own forensic note (GEMSDOE33 repo, <code>knowledge/01_why_0.2708_won.md</code>), and AGENTS.md states the top six sites are statistically tied. The 0.007 gap is therefore within noise and unverified.</li>
<li><b>Not established:</b> whether any file can beat 0.2778 on the organizer's private set. The leaderboard leader is 0.4544 on the live page.</li>
</ul></section>

<section><h2>4 · Leaderboard (live page, fetched 2026-10-29)</h2>
<table><tr><th>Rank</th><th>Participant</th><th>Best public DW-Tversky</th></tr>{lb}</table>
<p><small>Source: <a href="{e(s['leaderboard_pinned']['source'])}">{e(s['leaderboard_pinned']['source'])}</a>. The prompt also cites 0.4413 and 0.3195 as the top score; those values do not match the live page.</small></p>
</section>

<section><h2>5 · Experiments and budget</h2>
<table><tr><th>ID</th><th>Status</th><th>Dots</th><th>Holdout DTI</th><th>95% CI</th></tr>{exp_rows}</table>
<p>Budget: {s['budget']['experiments_used']} of {s['budget']['experiments_allowed']} experiments used. The first run (E1) had a gate bug and is kept for audit in <code>evidence/tip_continuation_20261029/superseded_E1_gate_bug/</code>.</p>
<p><b>Why the holdout is negative:</b> the shared evaluator's 15 px collar removes any truth within 1.5 km of a visible fault, and this candidate only emits dots within 1.5 km of a visible fault tip. The test cannot credit this hypothesis even if it were right. The uniqueness result is a separate, real finding.</p>
</section>

<section><h2>6 · Irregularities flagged for review</h2><ol>{irr}</ol></section>
<section><h2>7 · Limitations</h2><ul>{lim}</ul></section>

<section><h2>8 · Next steps (ranked)</h2><ol>
<li>Obtain authenticated access to <code>training_features.tif</code> and the DrivenData data tab (login required). Without it no holdout can use the full feature stack.</li>
<li>Use one weekly slot only after a passing holdout and a lane-unique file. A portal format test costs a slot, so decide that explicitly.</li>
<li>Test a distinct mechanism (for example, a feature-based scarp or magnetic lineament detector) against the full feature stack. Stop the lane if overlap exceeds 70% with any of the 754 binary registry rasters.</li>
<li>Ask the holdout owner to review the 15 px collar, which makes near-catalogue hypotheses untestable.</li>
</ol></section>

<section><h2>9 · Sources (verify manually)</h2><ul>{src}</ul></section>
</main></body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
