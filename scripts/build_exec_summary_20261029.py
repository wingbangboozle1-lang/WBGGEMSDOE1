#!/usr/bin/env python3
"""Build docs/executive-summary-20261029.html from the verified nine-site audit JSON.

Every measured number on the page is read from docs/data/nine_site_audit_20261029.json
(produced by scripts/nine_site_audit.py from pinned GitHub snapshots). Scores are shown only
as USER-REPORTED values from the session prompt, or as "UNAVAILABLE" where no evaluator exists.
Leaderboard figures are copied from the official DrivenData leaderboard page, retrieved 2026-10-29.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "data" / "nine_site_audit_20261029.json"
OUT = ROOT / "docs" / "executive-summary-20261029.html"

# Official sources (retrieved 2026-10-29 with the fetch tool; URLs are the pages cited on the page).
SRC = {
    "competition": "https://www.drivendata.org/competitions/306/competition-doe-gems/",
    "problem": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
    "leaderboard": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
    "rules": "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
    "reference": "https://github.com/drivendataorg/gems-prize-reference-solution",
    "geodawn": "https://doi.org/10.5066/P93LGLVQ",
    "ingenious": "https://doi.org/10.15121/1881483",
}

# Official leaderboard rows retrieved 2026-10-29 (display rank, participant, best public DW-Tversky).
LEADERBOARD = [
    ("#1", "xiaofanhu", "0.4544"), ("#2", "cfld__", "0.3916"), ("#5", "op01", "0.3642"),
    ("#10", "zeaal", "0.3405"), ("#47", "kpomazi", "0.3195"), ("#48", "drjy", "0.3180"),
    ("#49", "twang", "0.3169"), ("#50", "kinneso_outlook", "0.3167"),
]


def esc(x) -> str:
    return html.escape(str(x))


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def main() -> None:
    audit = json.loads(AUDIT.read_text())
    files = audit["files"]
    pairs = audit["pairwise"]

    # Lane statistic: for each file, the largest fraction of its dots within 3 px of another named file.
    max_overlap: dict[str, tuple[float, str]] = {}
    identical_to: dict[str, str] = {}
    for p in pairs:
        for x, y, frac in ((p["a"], p["b"], p["frac_a_within_3px_of_b"]), (p["b"], p["a"], p["frac_b_within_3px_of_a"])):
            if frac > max_overlap.get(x, (-1.0, ""))[0]:
                max_overlap[x] = (frac, y)
            if p["identical_positive_sets"]:
                identical_to[x] = y

    rows = []
    for f in files:
        mo, other = max_overlap[f["key"]]
        if f["key"] in identical_to:
            uniq = f'<span class="bad">NO</span> — identical positive set to {esc(identical_to[f["key"]])}'
        elif mo > 0.70:
            uniq = f'<span class="bad">NO</span> — {pct(mo)} of dots within 3 px of {esc(other)} (&gt;70% lane rule)'
        else:
            uniq = f'<span class="good">YES</span> vs the named files (max {pct(mo)})'
        rows.append(f"""<tr>
<td><b>{esc(f["site"])}</b></td>
<td><a href="https://github.com/{esc(f["repo"])}/blob/{esc(f["commit"])}/{esc(f["path"])}?raw=1">{esc(Path(f["path"]).name)}</a><br><small>SHA-256 <code>{esc(f["sha256"][:16])}…</code></small></td>
<td>{f["user_reported_score"]:.4f}<br><small>USER-REPORTED, not organizer-confirmed</small></td>
<td>{f["n_positive"]:,}</td>
<td>{pct(f["frac_positive_within_3px"])} <small>(within 300 m of catalogue)</small></td>
<td><b>UNAVAILABLE</b><br><small>no evaluator or organizer receipt; not inferred</small></td>
<td>{uniq}</td>
<td><span class="bad">NO</span> — do not submit</td>
</tr>""")

    lb = "".join(f"<tr><td>{r}</td><td>{esc(u)}</td><td>{s}</td></tr>" for r, u, s in LEADERBOARD)
    stats = {f["key"]: f for f in files}
    b2 = next(f for f in files if f["site"] == "GEMSDOE32")
    d28 = next(f for f in files if f["key"] == "GEMSDOE25:dotted-h19-5-d2-8-20261002-e56ea318af89-nan")
    b1 = next(f for f in files if f["key"] == "GEMSDOE31:h27-4-solo-d28-20261004-8acb75e1-nan")
    rho = audit["descriptive_spearman_frac_within_3px_vs_user_reported"]
    assert b2["n_positive"] == 37654 and b2["n_positive_within_2px"] == 0, "B2 identity changed"
    assert d28["n_positive"] == 44090 and b1["n_positive"] == 40199, "lineage counts changed"

    lineage = f"""<table><thead><tr><th>Step</th><th>File family</th><th>Positives</th><th>Removed</th><th>USER-REPORTED</th><th>Within 300 m of catalogue</th></tr></thead><tbody>
<tr><td>D2.8</td><td>GEMSDOE25 / GEMSDOE30 (identical sets)</td><td>{d28["n_positive"]:,}</td><td>—</td><td>0.2600</td><td>{pct(d28["frac_positive_within_3px"])}</td></tr>
<tr><td>B1</td><td>GEMSDOE31 (= GEMSDOE28 solo)</td><td>{b1["n_positive"]:,}</td><td>{d28["n_positive"] - b1["n_positive"]:,} within 100 m (≤1 px); measured {d28["n_positive_within_1px"]:,}</td><td>0.2708</td><td>{pct(b1["frac_positive_within_3px"])}</td></tr>
<tr><td>B2</td><td>GEMSDOE32 · 0.2778 file</td><td>{b2["n_positive"]:,}</td><td>{b1["n_positive"] - b2["n_positive"]:,} more within 200 m (≤2 px); measured {b1["n_positive_within_2px"]:,} at ≤2 px in B1</td><td>0.2778</td><td>{pct(b2["frac_positive_within_3px"])} (0 within 200 m)</td></tr>
</tbody></table>"""

    checks = "".join(f"<li><b>{esc(f['site'])}</b> <code>{esc(f['name'][:44])}</code>: float32, EPSG:{f['crs_epsg']}, shape {f['shape'][0]}×{f['shape'][1]}, transform matches reference: {f['transform_matches_official']}, values in [0,1]: {f['n_outside_0_1'] == 0} ({f['value_min']:g}–{f['value_max']:g}), NaN footprint matches official sample: {f['nan_mask_matches_official_sample']}</li>" for f in files)

    html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GEMS submission decision · 29 Oct 2026</title>
<link rel="stylesheet" href="styles.css">
<style>
body{{font-family:system-ui,Segoe UI,Roboto,sans-serif;max-width:1180px;margin:0 auto;padding:20px;color:#10161c;background:#f4efe6;line-height:1.45}}
table{{border-collapse:collapse;width:100%;margin:12px 0;background:#fffaf3;font-size:14px}}
th,td{{border:1px solid #d7cbb8;padding:7px 9px;vertical-align:top;text-align:left}}
th{{background:#e9e0cf}}
.banner{{border:4px solid #a32626;background:#fff;padding:16px 20px;border-radius:8px;margin:14px 0}}
.banner h1{{margin:0 0 6px;font-size:26px;color:#a32626}}
.good{{color:#1b6b3a;font-weight:700}} .bad{{color:#a32626;font-weight:700}}
code{{background:#efe8da;padding:1px 4px;border-radius:3px}}
section{{margin:26px 0}}
small{{color:#4a5a60}}
</style></head>
<body>
<p><a href="index.html">← Research desk overview</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/main/README.md">README</a></p>
<div class="banner">
<h1>SUBMIT: NO · no file is cleared</h1>
<p><b>DOWNLOAD:</b> research only. <b>Estimated leaderboard score:</b> <b>UNAVAILABLE</b> for every file in this repo. This sandbox cannot reach the DrivenData data, the 19-band feature stack or the submission page, so no holdout score, organizer score or leaderboard estimate exists for any new file.</p>
<p>The competition closes <b>3 Dec 2026, 11:59 p.m. UTC</b> (about 35 days from 29 Oct 2026). Official rules allow <b>one final submission</b> and <b>three submissions per week</b>. <a href="{SRC["competition"]}">Competition page</a> · <a href="{SRC["rules"]}">Official rules PDF</a></p>
</div>

<section>
<h2>1 · Answer in one paragraph</h2>
<p>The highest <i>user-reported</i> file among the nine focus sites is <b>GEMSDOE32 B2, 0.2778</b>. Its positive set is already in the competition, so uploading it again is a duplicate. Every one of the eleven named files places at least 97.6% of its dots within 3 px of another named file, so the whole set is one family. Any new file built here would have no validated score. The repo's other unique-named files (for example WBG-7, HOLDOUT-DTI 0.0149, and WBG-6, archived 3 px overlap 99.68%) are format-valid but <b>not cleared</b>: no organizer score exists, and their own receipts fail the benchmark or the overlap gate. The first of four blockers (Section 5) is the 19-band feature stack, which must be restored on an unrestricted machine before any new candidate can be validated.</p>
</section>

<section>
<h2>2 · Best submission per site (decision table)</h2>
<p>Columns come from the verified audit JSON <a href="data/nine_site_audit_20261029.json">docs/data/nine_site_audit_20261029.json</a>. The "Estimated leaderboard score" column is intentionally <b>UNAVAILABLE</b>: an estimate would require a scorer we do not have.</p>
<div style="overflow-x:auto"><table>
<thead><tr><th>Site</th><th>File to download (pinned GitHub snapshot)</th><th>Score</th><th>Positive cells</th><th>Near catalogue</th><th>Estimated leaderboard score</th><th>Unique vs the other named files?</th><th>Submit?</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p><small>"Unique" applies the repo's lane statistic (&gt;70% of dots within 3 px of another named raster = duplicate) and an exact positive-set comparison. It is this lab's protocol, not a DrivenData rule: the official rules text (all seven PDF chunks reviewed 2026-10-29) contains no uniqueness or duplicate test. It does not cover the other rasters on the nine sites or the rest of the leaderboard.</small></p>
</section>

<section>
<h2>3 · Official public leaderboard (retrieved 2026-10-29)</h2>
<p>The live page shows #1 at 0.4544. The prompt's figures 0.4413 and 0.3195 do not match that page: 0.3195 is rank #47, not the highest score. Source: <a href="{SRC["leaderboard"]}">official leaderboard</a>.</p>
<table><thead><tr><th>Rank</th><th>Participant</th><th>Best public score</th></tr></thead><tbody>{lb}</tbody></table>
<p>The historical nine-site values (0.2477–0.2778) sit below the visible top-50 cutoff of 0.3167. Whether those values correspond to a DrivenData public score is unknown: the page does not show the owners' accounts.</p>
</section>

<section>
<h2>4 · Why GEMSDOE32 B2 scored 0.2778 (verified mechanism, user-reported scores)</h2>
{lineage}
<p><b>Verified from the raster bytes:</b> B2 has zero dots within 200 m of the catalogue. Its 2,171 near-catalogue dots lie between 200 m and 300 m from the catalogue. D2.8 → B1 → B2 is a pure removal ladder: B2 ⊂ B1 ⊂ D2.8, and GEMSDOE36 = B2 + 1,200 dots. The user-reported lineage rises +0.0108 then +0.0070 with each removal.</p>
<p><b>Mechanism (plausible, not proven):</b> under the official metric (α = 0.2 for false positives, β = 0.8 for false negatives, 300 m triangular kernel), a dot near a <i>known</i> mapped fault is charged as a false positive unless a hidden new fault lies within the kernel. Removing dots that carry no hidden-fault credit lowers the false-positive term at little cost to true-positive credit. This is the "precision by exclusion" explanation, consistent with the lineage. It is not a causal proof: hidden labels are unavailable and the scores are user-reported.</p>
<p><b>Descriptive pattern (n = {rho["n_distinct_positive_sets"]} distinct positive sets):</b> Spearman ρ = {rho["rho"]:.2f}, p ≈ {rho["p_value"]:.1g} between the share of dots within 300 m of the catalogue and the user-reported score. Fewer near-catalogue dots goes with a higher reported score. This is the strongest pattern we found, and it is the first hypothesis to test. The caveat is that the scores are unverified and the files come from one family.</p>
<p><b>Why you cannot submit a "better" pruned B2:</b> any further pruning of B2 yields a subset of B2, so 100% of its dots overlap B2. That is a copy under the user's rule and a lane duplicate under the protocol.</p>
</section>

<section>
<h2>5 · Can a unique file beat 0.2778? Honest answer: not demonstrated</h2>
<ul>
<li><b>Blocker 1 (data):</b> the 19-band feature stack (<code>training_features.tif</code>, 418,912,844 bytes in five 94,371,840-byte parts per <code>data/bridge/manifest.json</code>) is not in this checkout; none of the five parts is present. The sandbox can reach GitHub and PyPI only; Dropbox, DrivenData and NLR are unreachable (checked 2026-10-29). Restore on an unrestricted machine with <code>bash scripts/download_competition_data.sh</code>. The bridge manifest's own reassembly route is not usable: it names <code>scripts/make_data_bridge.py</code> and <code>scripts/assemble_data_bridge.py</code>, and neither file exists in the repo (see Section 7).</li>
<li><b>Blocker 2 (scorer):</b> the holdout evaluator is the only score proxy. Its withheld positives are <i>known</i> faults, held out with a 300 m context buffer. The competition scores <i>new</i> faults. Whether the buffer and holdout distribution represent the hidden set is untested.</li>
<li><b>Blocker 3 (uniqueness rule):</b> the best family's derivatives are duplicates by construction. A genuinely new family has no evidence behind it.</li>
<li><b>Blocker 4 (portal):</b> the reported "[0, 1]" error cannot be reproduced. All eleven named files and the repo's research TIFFs have values only in [0, 1]. We need the exact file that failed, and a DrivenData login to test it.</li>
</ul>
</section>

<section>
<h2>6 · Candidate hypotheses (ranked, none tested; none may be presented as a score)</h2>
<table><thead><tr><th>Rank · cost · expected benefit</th><th>Layers and operator</th><th>Physical signature / why a missing fault would respond</th><th>Named non-fault mimic</th><th>Difference from the repo</th></tr></thead><tbody>
<tr><td>1 · low cost (labels only) · highest measured lead</td><td>Public catalogue <code>labels.tif</code> only. Test the 0.2778 removal ladder (D2.8 → B1 → B2 → ≥3 px) on the holdout with per-fold visible catalogues.</td><td>Hidden new faults are not on mapped traces. If they lie more than 300 m from known faults, near-catalogue dots are false positives. Signature: distance-to-catalogue histogram of hidden positives.</td><td>Mapping bias: faults are mapped where they are already known or accessible (roads, claims).</td><td>Tests the metric prior directly. The lineage was built with the full catalogue, so it must be regenerated per fold before any score claim.</td></tr>
<tr><td>2 · medium–high cost (needs stack) · uncertain</td><td>19-band stack. Compute a calibrated per-cell posterior of "hidden fault within 300 m" and choose dots by the metric's expected-value rule (α = 0.2, β = 0.8), not by fixed coverage.</td><td>Expected value of a dot = P(hidden fault in kernel) minus the false-positive cost. The metric's asymmetry makes thresholds matter more than ranking.</td><td>Calibration drift between catalogue-trained labels and hidden labels.</td><td>Differs from max-cover/CELF families: the decision is made on calibrated probabilities, not coverage.</td></tr>
<tr><td>3 · low cost · methodological</td><td>Labels only. Measure how close withheld catalogue segments lie to visible segments at buffers of 0, 1, 2, 3 px, and compare with the nine-site near-catalogue shares.</td><td>Checks whether the holdout's 3 px buffer matches the hidden set's distance distribution. If it does not, the holdout will mis-rank catalogue-adjacent strategies.</td><td>Holdout artefact: buffers remove the very adjacency the metric rewards.</td><td>A check on the evaluator, not a new geology claim. Required before H1 or H2 is trusted.</td></tr>
</tbody></table>
</section>

<section id="irregularities">
<h2>7 · Irregularities flagged for review</h2>
<ol>
<li><b>AGENTS.md said WBG-6 was "APPROVED FOR SUBMISSION"</b>, contradicting README, PROMPT and the homepage (no file cleared). Corrected in this session.</li>
<li><b>Leaderboard figures conflict:</b> prompt 0.4413 and 0.3195 vs live #1 0.4544 (retrieved 2026-10-29). 0.3195 is rank #47.</li>
<li><b>Official sample vs mirror:</b> the rules describe the sample as predicting total absence. The mirror <code>data/bridge/sample_submission.tif</code> has 60,988 positive cells, and they are exactly the catalogue's positives. The mirror is therefore not a zero-fault sample, or the description is wrong. Do not use it as a template for values.</li>
<li><b>Format convention:</b> the rules say values must be in [0, 1] and data outside the bounds must be null or NaN. The official sample's NaN footprint covers 7,111,787 cells (5,167,373 finite). The 0.2778 file and most research TIFFs are all-finite with zeros outside. That is allowed by the rule text, but it differs from the sample. Whether the portal accepted zeros outside is only user-reported, so any new upload should copy the sample's NaN footprint.</li>
<li><b>"[0, 1]" portal error:</b> not reproducible from any named or repo TIFF (see checks below). The failing file must be identified before a fix can be claimed.</li>
<li><b>Missing bridge tooling:</b> <code>data/bridge/manifest.json</code> names <code>scripts/make_data_bridge.py</code> (generator) and <code>scripts/assemble_data_bridge.py</code> (reassembly). Neither exists in the repo, and the five 94,371,840-byte parts are absent, so the 19-band stack cannot be rebuilt from this checkout.</li>
<li><b>Holdout buffer:</b> the shared holdout's 3 px context buffer may not represent the hidden set (see H3).</li>
<li><b>Lineage scores:</b> B2, B1 and D2.8 values are user-reported only. The repo's older claim that "scores differ by up to 0.086 for near-identical rasters" is not supported by the identical pairs here (25 = 30 at 0.2600; 28-solo = 31 at 0.2708). The 0.086 claim concerns other sites and was not re-verified here.</li>
<li><b>Generative-AI disclosure:</b> the rules require a narrative disclosure of any generative-AI use in the submission. This applies to any future submission.</li>
</ol>
</section>

<section>
<h2>8 · Format checks (local, not portal acceptance)</h2>
<ul>{checks}</ul>
<p><small>Checks are from <a href="data/nine_site_audit_20261029.json">nine_site_audit_20261029.json</a>, reproduced by <code>scripts/nine_site_audit.py</code>.</small></p>
</section>

<section>
<h2>8b · How to submit, if a file is ever cleared</h2>
<p><b>Today the answer is no.</b> These steps apply only after a file has its own verified run card with a PASS verdict. None of the eleven files above qualifies.</p>
<ol>
<li><b>Choose the file by its run card, not by score.</b> Its SHA-256 must match the run card, and its positive set must pass the lane test (≤70% of dots within 3 px of another named raster) and the exact-duplicate test.</li>
<li><b>Validate locally:</b> <code>python scripts/validate_submission.py path/to/file.tif</code>, then add <code>--require-submit-ready</code>. Required: single-band float32 GeoTIFF, EPSG:32611, 3730×3292, 100 m, values in [0, 1], and data outside the bounds as NaN (the official sample's convention).</li>
<li><b>Name and note:</b> a unique file name, plus a note of at most 140 characters that says what the file is.</li>
<li><b>Disclose generative-AI use</b> in the narrative, as the official rules require.</li>
<li><b>Upload only through the DrivenData portal.</b> The rules allow one final submission and three per week. Do not upload from a script, and never enter or store DrivenData credentials here.</li>
<li><b>Record the receipt.</b> Only an organizer or portal receipt makes a score ORGANIZER-CONFIRMED. Until then every number is HOLDOUT-DTI (with its evaluator version, n, and CI), USER-REPORTED, or a projection, and a projection is never a score.</li>
</ol>
<p><b>Duplicate note:</b> <code>data/bridge/labels.tif</code> and <code>data/bridge/existing_faults.tif</code> are byte-identical (SHA-256 7ba308cc…, 425,830 bytes). Treat them as one file.</p>
<h2>9 · Run card (JSON)</h2>
<pre style="background:#fffaf3;border:1px solid #d7cbb8;padding:12px;overflow-x:auto">{esc(json.dumps({
    "date": "2026-10-29",
    "hypothesis": "No new file is cleared. Historical near-catalogue pruning (D2.8 → B1 → B2) is the best-supported explanation of the top user-reported result; a new unique file is not yet justified.",
    "mechanism": "Metric prices false positives at alpha=0.2; dots within 300 m of a known fault carry little hidden-fault credit, so removing them reduces false-positive cost.",
    "named_nonfault_mimic": "Mapping bias (faults mapped where already known or accessible).",
    "holdout_dti": "NOT MEASURED (feature stack unavailable in this sandbox)",
    "leaderboard_estimate": "UNAVAILABLE",
    "registry_correlation_overlap": "Named-file lane statistic: " + "; ".join(f"{f['key']} max {pct(max_overlap[f['key']][0])}" for f in files),
    "raster_sha256_reference": b2["sha256"],
    "validator": "float32, EPSG:32611, shape 3730x3292, transform match, values in [0,1] for all 11 named files; NaN footprint matches the official sample only for NaN-convention files",
    "submission_name": None,
    "submission_note": "No new upload. Historical GEMSDOE32 B2 is a duplicate; do not submit.",
    "verdict": "negative (do not promote)",
    "sources": SRC,
}, indent=2))}</pre>
</section>

<section>
<h2>Sources (official, for manual review)</h2>
<ul>
<li><a href="{SRC["competition"]}">Competition home</a> — competition end date, prize structure, how to enter.</li>
<li><a href="{SRC["problem"]}">Problem description</a> — metric (distance-weighted Tversky, α = 0.2, β = 0.8, 300 m triangular kernel), submission format (float32, EPSG:32611, 100 m, values in [0, 1], outside bounds null/NaN).</li>
<li><a href="{SRC["rules"]}">Official rules (NLR PDF, Sept 2026)</a> — one final submission, three per week, generative-AI disclosure, original-work warranty.</li>
<li><a href="{SRC["leaderboard"]}">Leaderboard</a> — the rows listed in section 3.</li>
<li><b>Note on the file links:</b> the "?raw=1" links resolve through GitHub to raw.githubusercontent.com. This sandbox cannot reach that host, so the bytes were verified from the same commits' codeload tarballs (SHA-256 in the table), not through those links.</li>
<li><a href="{SRC["reference"]}">Reference solution</a> and the <a href="{SRC["geodawn"]}">GeoDAWN</a> and <a href="{SRC["ingenious"]}">INGENIOUS</a> DOIs for the input data.</li>
</ul>
</section>
</body></html>
"""
    OUT.write_text(html_doc, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
