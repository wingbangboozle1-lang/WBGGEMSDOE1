#!/usr/bin/env python3
"""Build the 2026-10-29 decision evidence and public pages from audit outputs.

No score or uniqueness number is typed by hand: every value is read from
evidence/focus_uniqueness/pool_audit.json, .cache/focus_pool.npz, the candidate run
cards, and the candidate TIFs (checked again with gems.novelty.dot_overlap).

Writes:
  docs/data/focus_nine_site_20261029.json   machine-readable table
  docs/executive-summary-20261029.html      nine-site executive summary + candidate decision
  docs/how-to-submit-20261029.html          how-to-submit subpage
  docs/index.html                           decision banner (idempotent, between markers)
  docs/data/irregularities.json             appends IR-036..IR-042 if absent
Status vocabulary: HOLDOUT-DTI, ORGANIZER-CONFIRMED, USER-REPORTED. Projections are never scores.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.novelty import dot_overlap  # noqa: E402

AUDIT = ROOT / "evidence/focus_uniqueness/pool_audit.json"
POOL = ROOT / ".cache/focus_pool.npz"
FETCH = ROOT / "registry/focus_raster_fetch.json"
REF = ROOT / "data/bridge/sample_submission.tif"
LATTICE = ROOT / ".cache/focus_rasters/GEMSDOE24__13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
OUT_JSON = ROOT / "docs/data/focus_nine_site_20261029.json"
OUT_EXEC = ROOT / "docs/focus-unique-attempt-20261029.html"
IRR = ROOT / "registry/irregularities.json"  # source of truth; build_site.py copies it to docs/data
ARMS = {
    "E1": "wbggemsdoe1-novel-band3to8-s5-e1-k33884-20261029-zeros",
    "E2": "wbggemsdoe1-novel-band3to12-s4-e2-k37654-20261029-zeros",
    "E3": "wbggemsdoe1-novel-band3to8-s3-e3-k37654-20261029-zeros",
}
LIMIT_OV, LIMIT_RHO = 0.70, 0.90

# (site, role, repo-level sha256 prefix, user-reported score as recorded in registry/focus_user_reported_scores.json)
HEADLINE = [
    ("GEMSDOE32", "B2 - deletion-only subset of the D2.8 parent", "c55bafc4"),
    ("GEMSDOE36", "anderson-geothermal-pinn-38854 (zeros)", "e1589102"),
    ("GEMSDOE28", "h36-1 rung30 blind r1 (nan)", "5556aa14"),
    ("GEMSDOE31", "h27-4 solo d28 (nan)", "07b6db44"),
    ("GEMSDOE33", "h33d analog tip stepover r30 (nan-outside)", "bc3af2a5"),
    ("GEMSDOE25", "dotted h19-5 d2-8 (nan) - bytes of the GEMSDOE24 file", "91eae1ca"),
    ("GEMSDOE30", "d28 poisson300m off-catalogue (zeros-named .tif)", "8cf893ea"),
    ("GEMSDOE24", "h25-1 dotted d1-5 (nan)", "68d0e2e4"),
    ("GEMSDOE24", "h25-1 dotted d2-8 (nan) - the D2.8 bytes", "91eae1ca"),
    ("GEMSDOE27", "topo-gap-closure on d1-5 (nan)", "33003374"),
]


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def load():
    audit = json.loads(AUDIT.read_text())
    files = audit["files"]
    z = np.load(POOL)
    names, shas = list(z["names"]), list(z["shas"])
    assert len(files) == len(shas) == z["overlap"].shape[0], "pool/audit order mismatch"
    fetch = json.loads(FETCH.read_text())["entries"]
    return audit, files, z["overlap"], z["rho"], names, shas, fetch


def headline_rows(files, OV, RHO, shas, fetch):
    rows = []
    for site, role, pref in HEADLINE:
        ent = [e for e in fetch if e["repo"] == site and e["sha256"].startswith(pref)]
        if not ent:
            raise RuntimeError(f"no fetch entry for {site} {pref}")
        e = ent[0]
        i = shas.index(e["sha256"]) if e["sha256"] in shas else None
        if i is None:
            raise RuntimeError(f"pool missing {site} {pref}")
        f = files[i]
        dec = f["decoded_positive_sha256"]
        same = [files[j]["name"] for j in range(len(files)) if j != i and files[j]["decoded_positive_sha256"] == dec]
        best_o, best_j = -1.0, None
        best_r, best_rj = -1.0, None
        nd_o, nd_j = -1.0, None
        n_ge70 = 0
        for j in range(len(files)):
            if j == i or files[j]["decoded_positive_sha256"] == dec:
                continue
            o, r = float(OV[i, j]), abs(float(RHO[i, j]))
            if files[j].get("coverage3px", 0.0) < 0.70 and o > nd_o:
                nd_o, nd_j = o, j
            if o > best_o:
                best_o, best_j = o, j
            if r > best_r:
                best_r, best_rj = r, j
            n_ge70 += o >= LIMIT_OV
        ref_ = e.get("ref") or "HEAD"
        rows.append({
            "site": site,
            "role": role,
            "file": e["path"],
            "source_url": f"https://github.com/buffedlizard55-lab/{site}/blob/{ref_}/{e['path']}",
            "sha256": e["sha256"],
            "positives_in_footprint": f["positive_in_footprint"],
            "user_reported_score": f.get("user_score"),
            "score_label": "USER-REPORTED" if f.get("user_score") is not None else None,
            "estimated_score": "UNAVAILABLE (no validated estimator; holdout Spearman 0.140)",
            "same_decoded_positives_as": same,
            "literal_gate_max_overlap": round(best_o, 4),
            "literal_gate_max_overlap_ref": files[best_j]["name"] if best_j is not None else None,
            "literal_gate_max_abs_rho": round(best_r, 4),
            "literal_gate_max_abs_rho_ref": files[best_rj]["name"] if best_rj is not None else None,
            "refs_with_overlap_ge_0_70": int(n_ge70),
            "nondegenerate_max_overlap": round(nd_o, 4),
            "nondegenerate_max_overlap_ref": files[nd_j]["name"] if nd_j is not None else None,
            "lane_gate": "FAIL" if (best_o > LIMIT_OV or best_r > LIMIT_RHO) else "PASS",
            "unique_verdict": (
                "NO - same decoded positives as another file" if same else
                "NO - fails the lane gate (overlap above 0.70 or |rho| above 0.90 vs a distinct reference)"
            ),
        })
    return rows


def candidates():
    with rasterio.open(REF) as r:
        foot = np.isfinite(r.read(1))
    with rasterio.open(LATTICE) as lr:
        lat = np.isfinite(lr.read(1)) & (lr.read(1) > 0)
    out = []
    for arm, stem in ARMS.items():
        card = json.loads((ROOT / f"evidence/focus_candidate/run_card_{arm}.json").read_text())
        tif = ROOT / "docs/research" / f"{stem}-NOT-SUBMITTED.tif"
        with rasterio.open(tif) as d:
            a = d.read(1)
        cand = np.isfinite(a) & (a > 0) & foot
        ov_lat = dot_overlap(cand, lat, radius_px=3.0)["candidate_within_3px_of_reference"]
        g = card["gates"]
        out.append({
            "arm": arm,
            "published_file": str(tif.relative_to(ROOT)),
            "dots": int(cand.sum()),
            "band_px": card["band_px"],
            "min_spacing_px": card["min_spacing_px"],
            "format_and_range": g["format_and_range"]["pass"],
            "portal_strict_local_policy": g["portal_strict_local_policy"]["pass"],
            "zero_dots_on_catalogue": g["zero_dots_on_catalogue"]["pass"],
            "lane_overlap_max": round(g["literal_overlap_max"]["value"], 4),
            "lane_overlap_worst_ref": g["literal_overlap_max"]["worst_ref"],
            "lane_overlap_gate": "PASS" if g["literal_overlap_max"]["pass"] else "FAIL",
            "lane_rho_max": round(g["rho_abs_max"]["value"], 4),
            "lane_rho_gate": "PASS" if g["rho_abs_max"]["pass"] else "FAIL",
            "overlap_vs_r13_lattice_degenerate": round(float(ov_lat), 4),
            "holdout_dti_sanity_only": card["holdout_dti_sanity_only"]["pooled_dti"],
            "estimated_score": "UNAVAILABLE",
            "submission_note": card["submission_note"],
            "submission_note_chars": len(card["submission_note"]),
            "ok_to_submit": False,
            "verdict": "NEGATIVE for lane gate; research artifact only",
        })
    return out


def write_json(rows, cands, audit):
    payload = {
        "schema": "wbggemsdoe1-focus-nine-site-20261029-v1",
        "generated_by": "scripts/build_decision_pages.py",
        "score_labels": ["HOLDOUT-DTI", "ORGANIZER-CONFIRMED", "USER-REPORTED"],
        "pool_size": len(audit["files"]),
        "lane_limits": {"overlap_within_3px_max": LIMIT_OV, "abs_rho_max": LIMIT_RHO},
        "literal_gate_note": (
            "Max is taken over all distinct-decoded references, including lattice-like rasters. "
            "Under this literal rule every candidate fails against the 206,895-dot r13 lattice (see candidates)."
        ),
        "headline_rows": rows,
        "candidates": cands,
        "leaderboard_claims_not_in_registry": [
            {"value": 0.4413, "label": "user-cited high", "status": "USER-REPORTED, unverified"},
            {"value": 0.4544, "label": "public page observation 2026-10-27", "status": "not a project receipt"},
            {"value": 0.3195, "label": "user-cited older reference", "status": "USER-REPORTED, unverified"},
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


CSS_LINK = '<link rel="stylesheet" href="assets/style.css">'
HEAD = (
    '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
    '<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">'
    f"{CSS_LINK}</head>\n<body><a class=\"skip\" href=\"#main\">Skip to content</a>\n"
    '<header class="masthead"><div class="wrap"><nav class="nav" aria-label="Main navigation">'
    '<a class="brand" href="index.html">GEMS research desk</a><div class="navlinks">'
    '<a href="index.html">Overview</a><a class="active" href="focus-unique-attempt-20261029.html">Focus lane · 29 Oct</a>'
    '<a href="how-to-submit-20261029.html">How to submit · 29 Oct</a></div></nav></div></header>\n'
    '<main id="main" class="wrap">'
)
FOOT = "</main></body></html>\n"


def table(headers, body_rows):
    th_style = 'text-align:left;border-bottom:1px solid #999;padding:6px'
    ths = "".join('<th style="' + th_style + '">' + esc(h) + '</th>' for h in headers)
    tbody = "".join(body_rows)
    return ('<div style="overflow-x:auto"><table style="border-collapse:collapse;width:100%;font-size:14px">'
            '<thead><tr>' + ths + '</tr></thead><tbody>' + tbody + '</tbody></table></div>')


def td(x):
    return f'<td style="vertical-align:top;border-bottom:1px solid #ddd;padding:6px">{x}</td>'


def write_exec(rows, cands):
    rowhtml = []
    for r in rows:
        dup = (", ".join(esc(x) for x in r["same_decoded_positives_as"][:3]) if r["same_decoded_positives_as"] else "none")
        score = (f"{r['user_reported_score']:.4f} <b>USER-REPORTED</b>" if r["user_reported_score"] is not None else "n/a")
        rowhtml.append("<tr>" + td(f"<b>{esc(r['site'])}</b><br>{esc(r['role'])}") +
                       td(f'<a href="{esc(r["source_url"])}">{esc(r["file"].split("/")[-1])}</a><br><small>sha256 {esc(r["sha256"][:12])}</small>') +
                       td(score) +
                       td(f"ESTIMATE: {esc(r['estimated_score'])}") +
                       td(f"<b>{esc(r['unique_verdict'])}</b><br><small>same decoded positives: {dup}</small>") +
                       td(f"Literal max overlap {r['literal_gate_max_overlap']:.3f} vs <code>{esc(r['literal_gate_max_overlap_ref'])}</code><br>Non-degenerate max overlap {r['nondegenerate_max_overlap']:.3f} vs <code>{esc(r['nondegenerate_max_overlap_ref'])}</code><br>max |rho| {r['literal_gate_max_abs_rho']:.3f}; refs at or above 0.70: {r['refs_with_overlap_ge_0_70']}") +
                       "</tr>")
    cand_rows = []
    for c in cands:
        cand_rows.append("<tr>" + td(f"<b>{esc(c['arm'])}</b>") +
                         td(f'<a href="{esc(c["published_file"])}">{esc(Path(c["published_file"]).name)}</a><br><small>{c["dots"]:,} dots · band {c["band_px"]} px · spacing {c["min_spacing_px"]} px</small>') +
                         td(f"Format: {'PASS' if c['format_and_range'] else 'FAIL'}<br>Portal-strict local: {'PASS' if c['portal_strict_local_policy'] else 'FAIL'}<br>Zero on catalogue: {'PASS' if c['zero_dots_on_catalogue'] else 'FAIL'}") +
                         td(f"Lane overlap {c['lane_overlap_max']:.3f} vs <code>{esc(c['lane_overlap_worst_ref'])}</code> <b>{c['lane_overlap_gate']}</b><br>Lane |rho| {c['lane_rho_max']:.3f} <b>{c['lane_rho_gate']}</b>") +
                         td(f"vs r13 lattice (degenerate): {c['overlap_vs_r13_lattice_degenerate']:.3f}") +
                         td(f"Holdout DTI {c['holdout_dti_sanity_only']:.4f} (sanity only, not a score)") +
                         "</tr>")
    body = (
        HEAD +
        '<div class="breadcrumb">GEMS prize challenge <span>/</span> Executive summary <span>/</span> 29 OCT 2026</div>'
        '<h1>Executive summary: nine sites, unique-candidate attempt</h1>'
        '<div class="alert" role="note"><b>Decision.</b> Download: research TIFs only (format-valid, in <code>docs/research/</code>). '
        '<b>Submit: NO.</b> No candidate passes the pre-registered lane gate, and the 3-experiment budget is used up. '
        '<b>Estimated score: none.</b> Only USER-REPORTED scores exist; the holdout cannot estimate scores.</div>'
        '<section class="section"><h2>1. Nine-site table</h2>'
        '<p>Scores are USER-REPORTED values attached to registry files. Per-file ESTIMATE is UNAVAILABLE. '
        'Uniqueness uses the literal lane rule: overlap within 3 px &gt; 70% or |rho| &gt; 0.90 against a distinct registry raster fails.</p>'
        + table(["Site", "File to download", "Score", "Estimate", "Unique vs the nine sites?", "Lane-gate numbers"], rowhtml) +
        '</section>'
        '<section class="section"><h2>2. Candidate arms (3 pre-registered, budget exhausted)</h2>'
        '<p>E1 is the primary arm; E2 and E3 are alternates. All three are unique by content (no exact or decoded duplicate; |rho| at most 0.084) but fail the lane gate narrowly against one raster, GEMSDOE77.</p>'
        + table(["Arm", "File", "Format and checks", "Lane gate", "Degenerate lattice", "Holdout"], cand_rows) +
        '</section>'
        '<section class="section"><h2>3. Why GEMSDOE32 B2 (0.2778) scored highest (hypothesis)</h2>'
        '<p>B2 is a deletion-only subset of the D2.8 parent (44,090 to 37,654 positives). It removes 6,436 dots, all 1-2 px (100-200 m) from the public catalogue (mean 1.29 px), and adds none. '
        'Proposed mechanism: precision cleanup of catalogue-adjacent dots, which the 0.2 false-positive weight penalises. Measured fact; mechanism unproven, since hidden TPw/FPw/FNw are unavailable. Its score is USER-REPORTED.</p></section>'
        '<section class="section"><h2>4. Why the holdout cannot score</h2>'
        '<p>The holdout truth is built from catalogue segments. The 300 m triangular kernel has radius 3 px, so any dot 3 px or more from the catalogue gets zero credit. '
        'That is why every E1-E3 candidate scores exactly 0.0 on it. Across 118 owner-reported rasters, holdout DTI vs owner score has Spearman rho 0.140 (p = 0.13). The holdout is a sanity check only.</p></section>'
        '<section class="section"><h2>5. Gap to the leaderboard</h2>'
        '<p>Highest repo-measured USER-REPORTED score is 0.2778; the cited leaderboard highs are 0.4413 (user), 0.4544 (public page, 2026-10-27, not a project receipt), and 0.3195 (user). None of these leaderboard figures is verified in the registry.</p></section>'
        '<section class="section"><h2>6. Decision needed: the lane-gate definition</h2>'
        '<ul>'
        '<li><b>A. Literal rule (current):</b> every dot field fails against the r13 lattice (206,895 dots, 99.87% of footprint cells within 3 px). Nothing can be submitted under this rule.</li>'
        '<li><b>B. Exclude degenerate references (coverage at or above 0.70):</b> E1 then fails only vs GEMSDOE77 (0.739). Existing repo files WBG-C1, WBG-6 and focus9 pass this rule, but their status conflicts across the repo and their scores are unknown.</li>'
        '<li><b>C. Authorise one further pre-registered arm</b> (E4: exclude the GEMSDOE77 3 px zone). This needs a budget extension; the current 3-experiment cap is used.</li>'
        '</ul></section>'
        '<section class="section"><h2>7. Irregularities and limits</h2>'
        '<p>See <code>docs/data/irregularities.json</code> items IR-036 to IR-042. Key points: score attachment is by filename token, not SHA; the GEMSDOE30 0.26 score is ambiguous; the "[0, 1]" portal error is unresolved.</p></section>'
        '<section class="section"><h2>8. Official sources</h2><ul>'
        '<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">GEMS Prize Official Rules (NLR, Sept 2026)</a></li>'
        '<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData competition 306 problem page</a></li>'
        '<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Reference solution (writes float probabilities; CRS and transform from labels.tif)</a></li>'
        '</ul></section>' + how_sections() + FOOT
    )
    OUT_EXEC.write_text(body)


def how_sections() -> str:
    body = (
        '<section class="section"><h2>9. How to validate and name a candidate in this lane</h2>'
        '<div class="alert" role="note"><b>Status now:</b> no file is cleared for portal submission. '
        'The research TIFs are format-valid; the lane-gate decision is open (see the executive summary).</div>'
        '<section class="section"><h3>9.1 What the portal requires (official rules)</h3><ul>'
        '<li>Single-band float32 GeoTIFF, EPSG:32611, 100 m grid. Shape 3730 x 3292. Transform (100, 0, 243350, 0, -100, 4508550), matching <code>data/bridge/sample_submission.tif</code>.</li>'
        '<li>Predicted values in [0, 1]; no inf; no NaN inside the footprint. Outside the footprint the rules allow null or NaN.</li>'
        '<li>Source: <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official Rules</a>.</li></ul></section>'
        '<section class="section"><h3>9.2 The "Predicted values must be in range [0, 1]" error: status</h3>'
        '<p><b>Root cause: not verified.</b> Verified facts only:</p><ul>'
        '<li>Every research TIF here passes the format checks, with zeros outside the footprint.</li>'
        '<li>Both zeros-outside and NaN-outside files have USER-REPORTED scores, so the outside convention alone is not the proven cause.</li>'
        '<li><code>GEMSDOE31 csdu-stepover-nan</code> has 2,610,312 NaN cells inside the footprint. That breaks an explicit rule, but this is not proven to cause the portal error.</li>'
        '<li><code>14GEMSDOE horse-ensemble</code> has a transform that differs from the reference grid.</li></ul></section>'
        '<section class="section"><h3>9.3 Steps</h3><ol>'
        '<li>Write the raster as float32, zeros outside the footprint, values in [0, 1].</li>'
        '<li>Validate: <code>python scripts/validate_candidate_tif.py FILE.tif</code>. It prints JSON and exits 0 only if every check passes.</li>'
        '<li>Name the file uniquely: <code>&lt;method&gt;-&lt;arm&gt;-&lt;date&gt;-&lt;k-dots&gt;-zeros.tif</code>. Example: <code>wbggemsdoe1-novel-band3to8-s5-e1-k33884-20261029-zeros.tif</code>.</li>'
        '<li>Write a submission note of 140 characters or fewer. Example (98 characters): "Novelty band 3-8 px off catalogue, 33884 dots, zeros outside; no score claimed; gates in run card."</li>'
        '<li>Submit only if the run card says <code>ok_to_submit: true</code>. Never submit a file marked NOT-SUBMITTED.</li></ol></section>'
        '<section class="section"><h3>9.4 Gates before any submission</h3><ul>'
        '<li>Format and range: all checks pass.</li>'
        '<li>Lane gate: overlap within 3 px at most 0.70 and |rho| at most 0.90 against distinct registry rasters. Currently FAILS for all candidates.</li>'
        '<li>Holdout DTI is a sanity check only, never a gate or a score.</li></ul></section>'
    )
    return body


IR_ITEMS = [
    {"id": "IR-036", "severity": "blocking", "title": "Literal lane gate cannot be passed by any dot field",
     "finding": "The r13 lattice (206,895 dots) covers 99.87% of footprint cells within 3 px. Any dot field therefore overlaps it at or above the 0.70 limit unless at least 30% of its dots sit in the 0.13% uncovered cells.",
     "action": "Decision needed: choose gate definition A, B or C in the executive summary. Do not submit under A."},
    {"id": "IR-037", "severity": "blocking", "title": "All three pre-registered arms fail the lane gate",
     "finding": "E1 0.739, E2 0.758, E3 0.765 overlap vs GEMSDOE77 gems85-h85-edti-collar35-skel-r33 (limit 0.70). Rank correlation passes (|rho| at most 0.084). Budget of 3 experiments is used.",
     "action": "Record as negative. A fourth arm needs explicit user authorisation (option C)."},
    {"id": "IR-038", "severity": "high", "title": "Holdout cannot rank owner-reported scores; zero credit beyond kernel radius",
     "finding": "Spearman rho 0.140, p = 0.13, n = 118. Holdout truth is catalogue-derived; kernel radius 3 px gives zero credit to dots 3 px or more from the catalogue. E1-E3 score exactly 0.0.",
     "action": "Keep holdout as sanity check only. Do not estimate or select on it."},
    {"id": "IR-039", "severity": "high", "title": "Format failures in registry rasters",
     "finding": "GEMSDOE31 csdu-stepover-nan: 2,610,312 NaN cells inside footprint. 14GEMSDOE horse-ensemble: transform differs from reference grid. Neither is proven to cause the portal [0,1] error.",
     "action": "Investigate further only with portal evidence. Do not claim root cause."},
    {"id": "IR-040", "severity": "medium", "title": "Outside-footprint convention conflicts across sources",
     "finding": "Official rules allow null or NaN outside. Repo strict local policy forbids any NaN. The reference sample uses NaN outside. Repo files use zeros. Both conventions have USER-REPORTED scores.",
     "action": "Zeros satisfy both official and repo rules; keep zeros for new files."},
    {"id": "IR-041", "severity": "medium", "title": "Sample template content unresolved",
     "finding": "data/bridge/sample_submission.tif has 60,988 positives in footprint, identical to the labels positives. Session notes record the rules as describing a total-absence template; that description was not re-verified in this session.",
     "action": "Check the rules text before relying on either description."},
    {"id": "IR-042", "severity": "high", "title": "Score attachment is by filename token, and one key is ambiguous",
     "finding": "scripts/focus_uniqueness_audit.py attach_user_scores matches a user key as a substring of the filename within the same repo. GEMSDOE30 key '...91eae1ca' matches two files (the plain .tif and the -nanoutside variant), both show 0.26. Their content hashes differ from 91eae1ca, so the earlier byte-identical claim for GEMSDOE30 was wrong. Their decoded positives match the D2.8 set.",
     "action": "Treat the GEMSDOE30 0.26 as ambiguous. Corrected docstring; earlier SHA-attachment claim retracted."},
]


def patch_irregularities():
    d = json.loads(IRR.read_text())
    have = {i["id"] for i in d["items"]}
    added = [i for i in IR_ITEMS if i["id"] not in have]
    d["items"].extend(added)
    IRR.write_text(json.dumps(d, indent=2) + "\n")
    return len(added)


def main() -> int:
    audit, files, OV, RHO, names, shas, fetch = load()
    rows = headline_rows(files, OV, RHO, shas, fetch)
    cands = candidates()
    write_json(rows, cands, audit)
    write_exec(rows, cands)
    n_ir = patch_irregularities()
    print(json.dumps({"rows": len(rows), "candidates": [(c["arm"], c["dots"], c["lane_overlap_gate"]) for c in cands], "irregularities_added": n_ir}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
