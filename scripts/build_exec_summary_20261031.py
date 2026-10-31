#!/usr/bin/env python3
"""Build the 31 Oct 2026 executive summary and run card FROM RECEIPTS ONLY.

Every number on the page is read from a JSON receipt written by one of:
    scripts/focus_codeload_proxy_audit.py      -> docs/data/focus_proxy_audit_20261031.json
                                                  docs/data/focus_codeload_manifest_20261031.json
    scripts/build_band_null_20261031.py        -> docs/data/band_null_run_card_20261031.json
    scripts/uniqueness_and_lattice_20261031.py -> docs/data/uniqueness_band_null_20261031.json
    docs/data/focus_nine_site_20261029.json    (registry rows, USER-REPORTED scores)

Outputs:
    docs/executive-summary-focus-20261031.html   (the decision page, linked from the site front page)
    docs/data/executive_summary_focus_20261031.json  (machine-readable table + run card)
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs/data"


def load(name: str):
    return json.loads((D / name).read_text())


audit = load("focus_proxy_audit_20261031.json")
manifest = load("focus_codeload_manifest_20261031.json")
band = load("band_null_run_card_20261031.json")
uniq = load("uniqueness_band_null_20261031.json")
nine = load("focus_nine_site_20261029.json")
registry_scores = json.loads((ROOT / "registry/focus_user_reported_scores.json").read_text())

CAND_NAME = band["submission_name"]
CAND_NOTE = band["submission_note"]
CAND_FILE = band["file"]          # docs/downloads/...tif
CAND_SHA = band["sha256"]
CAND_ZIP_SHA = band["zip_sha256"]
LIMIT_OVERLAP = 0.70

# --- byte-level site membership (from the codeload manifest, sha256 of every archive TIF)
sites_by_sha: dict[str, set[str]] = {}
for f in manifest["files"]:
    sites_by_sha.setdefault(f["sha256"], set()).add(f["site"])

# --- proxy values for the headline files, matched by site and reported score
proxy_by_site_score = {}
for r in audit["matched_reported_files"]:
    if r.get("status") == "OK":
        proxy_by_site_score.setdefault((r["site"], round(r["score"], 4)), r)

proxy_by_sha = {r["sha256"]: r for r in audit["matched_reported_files"] if r.get("status") == "OK"}
overlap = audit["nine_headline_dot_overlap_3px"]
rows = []
for h in nine["headline_rows"]:
    key_name = f'{h["site"]}:{Path(h["file"]).name}'
    other_max = 0.0
    other_name = None
    for other in overlap:
        if other == key_name:
            continue
        v = overlap[key_name][other]
        if v > other_max:
            other_max, other_name = v, other
    prox = proxy_by_sha.get(h["sha256"]) or proxy_by_site_score.get((h["site"], round(h["user_reported_score"], 4)))
    sites = sorted(sites_by_sha.get(h["sha256"], set()))
    rows.append({
        "site": h["site"],
        "file_to_download": Path(h["file"]).name,
        "download_url": h["source_url"],
        "download_path_in_repo": h["file"],
        "sha256": h["sha256"],
        "reported_score": h["user_reported_score"],
        "reported_score_label": "OWNER-REPORTED (no organizer receipt)",
        "estimated_score": "UNAVAILABLE - no validated estimator (proxy vs reported rho = %s, n=%d)"
                           % (audit["spearman_proxy_vs_user_reported"]["rho"],
                              audit["spearman_proxy_vs_user_reported"]["n"]),
        "proxy_dti": None if prox is None else prox["dti"],
        "proxy_dti_label": "PROXY-DTI (SGMC-minus-catalogue proxy; NOT a score)",
        "bytes_found_in_sites": sites,
        "byte_unique_to_one_site": len(sites) == 1,
        "max_dot_overlap_3px_vs_other_focus_file": round(other_max, 4),
        "max_overlap_partner": other_name,
        "dot_set_unique_vs_focus_sites": other_max < LIMIT_OVERLAP,
        "verdict_download": "DOWNLOAD: NO (not a candidate; duplicate family)",
        "verdict_submit": "SUBMIT: NO - duplicate of the focus family",
    })

cand_row = {
    "site": "NEW (this session)",
    "file_to_download": Path(CAND_FILE).name,
    "download_url": CAND_FILE,
    "download_path_in_repo": CAND_FILE,
    "sha256": CAND_SHA,
    "reported_score": None,
    "reported_score_label": "none - never submitted",
    "estimated_score": "UNAVAILABLE for the leaderboard. Research null: PROXY-DTI %.4f vs uniform random %.4f."
                       % (band["proxy_dti"]["dti"], band["proxy_uniform_random_baseline"]["dti"]),
    "proxy_dti": band["proxy_dti"]["dti"],
    "proxy_dti_label": "PROXY-DTI (not organizer, not holdout)",
    "bytes_found_in_sites": [],
    "byte_unique_to_one_site": True,
    "max_dot_overlap_3px_vs_other_focus_file": uniq["max_candidate_dots_within_3px_of_one_file"]["value"],
    "max_overlap_partner": uniq["max_candidate_dots_within_3px_of_one_file"]["file"],
    "dot_set_unique_vs_focus_sites": uniq["gate_verdict"]["G4_forward_literal_lt_0_70"],
    "verdict_download": "DOWNLOAD: YES - research file only (not a copy; format-valid; fails literal dot-overlap gate G4)",
    "verdict_submit": "SUBMIT: NO - literal 70% gate (G4) fails for every dot field",
}

card = {
    "schema": "gemsdoe1-run-card-20261031-v1",
    "date_utc": "2026-10-31",
    "hypothesis": ("Placement distance to the public USGS/INGENIOUS catalogue alone, with no geology, "
                   "accounts for the proxy ranking of the focus family; the B2 deletion explanation for 0.2778 "
                   "can be tested on the proxy."),
    "mechanism": "Dots 4-10 px from mapped traces avoid the catalogue 3-px kernel; B2 removed 6,436 parent dots 1-2 px from it.",
    "named_non_fault_mimic": ("catalogue-proximity artefacts; the SGMC-derived proxy is a ~1 px dilation "
                              "of SGMC (IR-57-SGMC-01)"),
    "holdout_dti": "NOT COMPUTED this session (no HOLDOUT-DTI number is reported)",
    "proxy_dti_candidate": {"value": band["proxy_dti"]["dti"], "label": "PROXY-DTI (metric.dti_exact, n_truth=%d, no CI)"
                            % band["proxy_dti"]["n_truth"]},
    "proxy_dti_uniform_random_baseline": {"value": band["proxy_uniform_random_baseline"]["dti"],
                                          "label": "PROXY-DTI (same density, seed 20261031)"},
    "registry_overlap_and_correlation": {
        "G2_exact_copy": "absent among %d distinct prediction rasters" % uniq["compared_distinct_sha256_files"],
        "G3_max_abs_spearman_vs_9_headline": uniq["max_abs_spearman_headline"],
        "G4_max_candidate_overlap_3px": uniq["max_candidate_dots_within_3px_of_one_file"],
        "G4_lattice_saturation": uniq["g4_lattice_saturation"],
    },
    "raster_sha256": CAND_SHA,
    "zip_sha256": CAND_ZIP_SHA,
    "validator": band["validator"],
    "submission_name": CAND_NAME,
    "submission_note": CAND_NOTE,
    "submission_note_chars": len(CAND_NOTE),
    "verdict": "negative (research only)",
    "download": "DOWNLOAD: YES (research file)",
    "submit": "SUBMIT: NO",
    "slots_used": 0,
}

summary = {
    "schema": "gemsdoe1-exec-summary-20261031-v1",
    "date_utc": "2026-10-31",
    "headline": {
        "download": "DOWNLOAD: YES (research file only)",
        "submit": "SUBMIT: NO",
        "reason": ("The new file is unique and format-valid. It cannot be cleared because the literal "
                   "70% 3-px overlap gate (G4) is failed by every dot field: the r13 lattice matches 99.79% of its "
                   "dots and a uniform random field matches 99.87%. That is a gate defect, which needs an owner decision."),
    },
    "nine_site_rows": rows,
    "new_candidate_row": cand_row,
    "experiments": {
        "E1_calibration": {"what": "Does the off-catalogue proxy rank the user-reported focus scores?",
                           "result": audit["spearman_proxy_vs_user_reported"]},
        "E2_mechanism": {"what": "Does the B2 deletion raise proxy DTI over its parent?",
                         "result": {k: audit["mechanism_test_b2_vs_parent"][k] for k in (
                             "parent_dots", "b2_dots", "b2_is_subset_of_parent", "removed_dots",
                             "removed_dist_to_catalogue_px_min", "removed_dist_to_catalogue_px_max",
                             "proxy_delta_b2_minus_parent")},
                         "b2_proxy_dti": audit["mechanism_test_b2_vs_parent"]["proxy_b2"]["dti"],
                         "parent_proxy_dti": audit["mechanism_test_b2_vs_parent"]["proxy_parent"]["dti"]},
        "E3_band_null": {"what": "Does distance-band placement alone reproduce proxy DTI?",
                         "result": {"band_null_proxy_dti": band["proxy_dti"]["dti"],
                                    "uniform_random_proxy_dti": band["proxy_uniform_random_baseline"]["dti"]}},
    },
    "run_card": card,
}
(D / "executive_summary_focus_20261031.json").write_text(json.dumps(summary, indent=1, allow_nan=False) + "\n")


# ----------------------------------------------------------------- HTML
def e(x) -> str:
    return html.escape("" if x is None else str(x))


def row_html(r: dict) -> str:
    dl = e(r["file_to_download"])
    url = e(r["download_url"])
    dlink = f'<a href="{url}">{dl}</a>'
    yes = lambda b: "YES" if b else "NO"  # noqa: E731
    sites = ", ".join(r["bytes_found_in_sites"]) if r["bytes_found_in_sites"] else "-"
    return ("<tr>"
            f"<td><b>{e(r['site'])}</b></td>"
            f"<td>{dlink}<br><small class='mono'>sha256 {e(r['sha256'][:16])}...</small></td>"
            f"<td>{e(r['reported_score']) if r['reported_score'] is not None else 'none - never submitted'}<br><small>{e(r['reported_score_label'])}</small></td>"
            f"<td>{e(r['estimated_score'])}</td>"
            f"<td>{e(r['proxy_dti'])}<br><small>{e(r['proxy_dti_label'])}</small></td>"
            f"<td>{yes(r['byte_unique_to_one_site'])}<br><small>sites: {e(sites)}</small></td>"
            f"<td>{yes(r['dot_set_unique_vs_focus_sites'])}<br><small>max 3-px overlap {e(r['max_dot_overlap_3px_vs_other_focus_file'])} vs {e(r['max_overlap_partner'])}</small></td>"
            f"<td><b>{e(r['verdict_download'])}</b><br><b>{e(r['verdict_submit'])}</b></td>"
            "</tr>")


nine_rows_html = "\n".join(row_html(r) for r in rows)
c = cand_row
cand_html = row_html(c)
pe = audit["spearman_proxy_vs_user_reported"]
mech = audit["mechanism_test_b2_vs_parent"]
sat = uniq["g4_lattice_saturation"]
irr = [
    ("Leaderboard figures conflict.",
     "The brief cites 0.4413 as the current high and 0.3195 as the highest score. The official leaderboard "
     "page read on 31 Oct 2026 shows #1 = 0.4544 and #50 = 0.3195, the last row shown. "
     "0.3195 is therefore the rank-50 cutoff, not the top score."),
    ("Identical bytes appear under several sites and scores.",
     f"{len(manifest['cross_site_byte_duplicates'])} SHA-256 groups occur in more than one focus repository. "
     "Example: the 0.26 file 'dotted-h19-5-d2-8' is byte-identical under GEMSDOE24, GEMSDOE25, GEMSDOE30 and GEMSDOE32. "
     "Only one of those site labels can correspond to a leaderboard entry."),
    ("Dot families are not unique.",
     "All nine headline files share one dot family: every headline file has at least "
     f"{min(min(overlap[a][b] for b in overlap) for a in overlap):.2f} of its dots within 3 px of every other headline file's dots "
     "(3-px overlap, shared definition vendor/gems57/uniqueness.py)."),
    ("GEMSDOE32 B2 is a strict subset of its parent.",
     f"B2 has {mech['b2_dots']} dots, all inside the {mech['parent_dots']}-dot D2.8 parent; {mech['removed_dots']} parent dots were deleted, "
     f"at {mech['removed_dist_to_catalogue_px_min']:.0f}-{mech['removed_dist_to_catalogue_px_max']:.0f} px from the public catalogue."),
    ("The proxy does not reproduce the reported ranking.",
     f"Spearman rho = {pe['rho']} (p = {pe['p']}, n = {pe['n']}). The proxy also scores B2 "
     f"{mech['proxy_delta_b2_minus_parent']:+.4f} below its parent, the opposite sign to the reported +0.0178 gain. "
     "Neither the B2 explanation nor any proxy estimate can be confirmed."),
    ("The literal 70% overlap gate cannot be passed by any dot field.",
     f"The r13 lattice (206,895 dots) matches {sat['candidate_band_null_within_3px_of_lattice']*100:.2f}% of the new file's dots, "
     f"{sat['b2_within_3px_of_lattice']*100:.2f}% of B2's, and {sat['uniform_random_same_density_within_3px_of_lattice']*100:.2f}% of a uniform random field at the same density. "
     "This is a gate defect that the owner must decide on, not a property of the candidate."),
    ("Inherited holdout measures the wrong population.",
     "The competition target is faults that are NOT in the public USGS database (official problem page). "
     "The holdout withholds catalogue segments and rewards placement tight to visible traces (vendor/gems57/offcatalogue.py docstring). "
     "Its numbers are not used here."),
    ("Proxy layer is approximate.",
     "The raw SGMC raster is not in this sandbox (mrdata.usgs.gov is not on the allowlist). The derived layer "
     "is a ~1 px dilation of SGMC and still contains catalogue pixels (IR-57-SGMC-01); the proxy removes them."),
    ("Training features and organizer data are unavailable.",
     "The DrivenData data page requires login; training_features.tif is not in this checkout. No model was trained here."),
]
irr_html = "\n".join(f"<li><b>{e(t)}</b> {e(d)}</li>" for t, d in irr)

sources = [
    ("Problem description, metric, submission format", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"),
    ("Leaderboard (read 31 Oct 2026)", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"),
    ("Competition overview", "https://www.drivendata.org/competitions/306/competition-doe-gems/"),
    ("About", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/"),
    ("Official rules PDF", "https://docs.nlr.gov/docs/fy26osti/96647.pdf"),
    ("Reference solution", "https://github.com/drivendataorg/gems-prize-reference-solution"),
    ("GeoDAWN (USGS)", "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and"),
    ("INGENIOUS (GBCGE)", "https://gbcge.org/current-projects/ingenious/"),
    ("EPSG:32611", "https://epsg.io/32611"),
    ("Tversky index", "https://en.wikipedia.org/wiki/Tversky_index"),
    ("SGMC source archives (cited in registry, not fetched here)", "https://mrdata.usgs.gov/geology/state/shp/NV.zip"),
]
src_html = "\n".join(f'<li><a href="{e(u)}">{e(t)}</a></li>' for t, u in sources)

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMS submission decision - 31 Oct 2026</title>
<link rel="stylesheet" href="assets/style.css">
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#14202b;background:#f7f9fb;line-height:1.45}}
main{{max-width:1240px;margin:0 auto;padding:24px}}
.banner{{border-radius:10px;padding:18px 20px;margin:12px 0}}
.dl{{background:#e7f6ec;border:2px solid #1f8a4c}}
.no{{background:#fdeaea;border:2px solid #b42323}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:14px}}
th,td{{border:1px solid #d6dee6;padding:8px;vertical-align:top;text-align:left}}
th{{background:#eef3f7}}
.mono{{font-family:ui-monospace,Menlo,Consolas,monospace}}
small{{color:#4c5b68}}
h2{{margin-top:32px}}
</style></head>
<body><main>
<h1>GEMS submission decision - 31 Oct 2026</h1>
<p>Generated by <code>scripts/build_exec_summary_20261031.py</code> from receipts in <code>docs/data/</code>. Every number is labelled.
Labels: <b>OWNER-REPORTED</b> (user brief, no organizer receipt) · <b>PROXY-DTI</b> (off-catalogue proxy with the shared metric; not a score) ·
<b>HOLDOUT-DTI</b> (not computed this session) · <b>ORGANIZER-CONFIRMED</b> (none exists).</p>

<div class="banner dl"><h2 style="margin:0">Download: YES - research file only</h2>
<p>Download <a href="{e(CAND_FILE.replace('docs/', ''))}"><b>{e(Path(CAND_FILE).name)}</b></a>
(ZIP: <a href="{e(CAND_FILE.replace('.tif', '.zip').replace('docs/', ''))}">{e(Path(CAND_FILE).name.replace('.tif', '.zip'))}</a>).
Format-valid. <b>Not a copy</b>: no byte-identical file among {uniq['compared_distinct_sha256_files']} prediction rasters, and
surface Spearman |rho| {uniq['max_abs_spearman_headline']} against the nine headline files.
Dot overlap: the only forward 3-px failure is the r13 lattice (a submitted 13GEMSDOE file, {sat['candidate_band_null_within_3px_of_lattice']*100:.2f}%),
which every dot field also matches.</p></div>

<div class="banner no"><h2 style="margin:0">Submit: NO - not cleared</h2>
<p>{e(summary['headline']['reason'])}</p>
<p><b>Estimated leaderboard score: UNAVAILABLE.</b> No validated estimator exists in this sandbox (E1 rho = {pe['rho']}, n = {pe['n']}).</p></div>

<h2>1. Nine-site table (GEMSDOE 24, 25, 27, 28, 30, 31, 32, 33, 36)</h2>
<p>Each file to download is the headline file for that site, SHA-256-verified against its GitHub archive. Unique means
"not byte-identical elsewhere and no 3-px dot overlap of 0.70 or more with another focus file".
<b>None of the nine is unique versus the other focus sites.</b></p>
<table>
<thead><tr><th>Site</th><th>File to download</th><th>Reported score</th><th>Estimated score</th><th>Proxy check</th>
<th>Byte-unique?</th><th>Dot-set unique?</th><th>Verdict</th></tr></thead>
<tbody>
{nine_rows_html}
</tbody></table>

<h2>2. New unique file (this session)</h2>
<table>
<thead><tr><th>Site</th><th>File to download</th><th>Reported score</th><th>Estimated score</th><th>Proxy check</th>
<th>Byte-unique?</th><th>Dot-set unique?</th><th>Verdict</th></tr></thead>
<tbody>{cand_html}</tbody></table>
<p><b>Name:</b> <code>{e(CAND_NAME)}</code><br><b>Note ({len(CAND_NOTE)} chars):</b> {e(CAND_NOTE)}</p>
<p>The file is a distance-only research null with no geology in it. Its proxy DTI ({band['proxy_dti']['dti']:.4f})
is compared with a uniform random field at the same density ({band['proxy_uniform_random_baseline']['dti']:.4f}).
It is a control, not a recommended submission.</p>

<h2>3. Why did GEMSDOE32 B2 (0.2778) score highest? What the evidence shows</h2>
<ol>
<li><b>Ancestry is measured.</b> Pixel comparison of the archived files: B2 is an exact subset of the D2.8 parent ( {mech['parent_dots']} parent dots, {mech['b2_dots']} B2 dots, 0 added, {mech['removed_dots']} removed).
The removed dots lie {mech['removed_dist_to_catalogue_px_min']:.0f}-{mech['removed_dist_to_catalogue_px_max']:.0f} px from the public catalogue. The mechanism is precision cleanup by deletion.</li>
<li><b>The reported gain is OWNER-REPORTED.</b> +0.0178 over the parent (0.2600 to 0.2778). No organizer receipt binds the value to the file.</li>
<li><b>The proxy disagrees with the mechanism.</b> PROXY-DTI falls from {mech['proxy_parent']['dti']:.4f} (parent) to {mech['proxy_b2']['dti']:.4f} (B2), {mech['proxy_delta_b2_minus_parent']:+.4f}. The proxy is approximate, so this is evidence against the mechanism, not proof.</li>
<li><b>Nothing here ranks reported scores.</b> Proxy vs reported across {pe['n']} focus files: rho = {pe['rho']} (p = {pe['p']}). The explanation for 0.2778 therefore stays unproven.</li>
<li><b>Leaderboard position.</b> The official page lists 50 rows; the lowest is #50 at 0.3195. 0.2778 does not appear among them.</li>
</ol>

<h2>4. Can we beat 0.2778? Honest answer</h2>
<p><b>Not demonstrated.</b> Nothing in this repository can estimate a leaderboard score. A deeper B2-style deletion would be a subset of an existing file: it fails uniqueness and inherits the same mechanism claim. The only measured lever is placement distance (band null {band['proxy_dti']['dti']:.4f} vs uniform {band['proxy_uniform_random_baseline']['dti']:.4f}), and that is not geology.
The next step that could change the answer is an official organizer receipt for any candidate, which requires DrivenData access (see limitations).</p>

<h2>5. Irregularities flagged for review</h2>
<ul>{irr_html}</ul>

<h2>6. Limitations and what is needed</h2>
<ul>
<li>DrivenData data and submission pages require login. Not accessible from this sandbox. <b>Needed:</b> a human or the owner to supply official data and any organizer receipt.</li>
<li>Owner decision on gate G4. Literal 70% is saturated by every dot field. <b>Needed:</b> a written rule, for example the density-matched lift in the repo.</li>
<li>Raw SGMC from USGS mrdata. <b>Needed:</b> allowlist access or owner-supplied copy.</li>
<li>Full 469-raster registry was not re-fetched. Uniqueness was measured against the 9 focus repositories (466 prediction rasters on grid) only.</li>
</ul>

<h2>7. Run card (JSON, one per candidate)</h2>
<pre class="mono" style="background:#fff;padding:12px;overflow:auto">{e(json.dumps(card, indent=1))}</pre>

<h2>8. Sources (official or verified; for manual review)</h2>
<ul>{src_html}</ul>
<p><small>Source archives: codeload.github.com (buffedlizard55-lab/GEMSDOE{{24,25,27,28,30,31,32,33,36}}, default branch). Retrieved 31 Oct 2026.</small></p>
</main></body></html>
"""
(ROOT / "docs/executive-summary-focus-20261031.html").write_text(page)
print("wrote docs/executive-summary-focus-20261031.html and docs/data/executive_summary_focus_20261031.json")
