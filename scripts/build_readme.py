#!/usr/bin/env python3
"""Keep the README decision current and embed the complete supplied standing brief."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def wbg6_readme_block():
    """Fail-closed top-of-README status under the active literal 70% rule."""
    audit = json.loads((ROOT / "evidence/wbg6_submission_audit.json").read_text())
    tif = Path(audit["tif"]).name
    overlap = audit["duplicate_screen"]["max_forward_overlap_3px"]
    newer = json.loads((ROOT / "docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.run-card.json").read_text())
    newer_tif = Path(newer["download_url"]).name
    holdout = newer["holdout_dti"]
    return f"""## ⛔ SUBMISSION STATUS (29 Oct 2026): SUBMIT NO — NO FILE IS CLEARED

**Start here:** [29 Oct executive summary — nine-site decision table, why GEMSDOE32 B2 scored 0.2778, blockers, ranked hypotheses](docs/executive-summary-20261029.html) · [verified nine-site audit](docs/data/nine_site_audit_20261029.json) · [irregularities flagged for review](docs/executive-summary-20261029.html#irregularities).

**Focus lane (three pre-registered arms E1 to E3, nine-site duplicate audit, gate decision):** [focus-unique-attempt-20261029.html](docs/focus-unique-attempt-20261029.html). Research-only TIFs are in [`docs/research/`](docs/research/). All three arms are format-valid and not copies, but each fails the 70% lane gate (overlap 0.739 to 0.765 vs GEMSDOE77). The literal lane rule cannot be passed by any dot field (r13 lattice).

Estimated leaderboard score: **UNAVAILABLE** for every file here (no holdout or organizer score is computable in this sandbox). Live public leaderboard #1 is **0.4544**; the 50th row read this session is **0.3169** (the board moves: another read recorded 0.3167) (DrivenData page retrieved 2026-10-29). GEMSDOE32 B2 (0.2778, USER-REPORTED) is already in the competition: re-uploading it is a duplicate.

---

## ⛔ Earlier status (28 Oct 2026, retained for provenance): NO CURRENT TIFF CLEARED — DO NOT SUBMIT

The historical WBG-6 approval is superseded: its archived maximum 3-pixel registry overlap is {overlap:.4%}, exceeding the active 70% stop threshold. Its 0.247 value is a MODEL-ESTIMATE, not HOLDOUT-DTI or organizer-confirmed. **Research download only:** [`{tif}`](docs/downloads/{tif}).

A newer concurrently added candidate [`{newer_tif}`](docs/downloads/{newer_tif}) records HOLDOUT-DTI {holdout:.4f}, 95% CI [{newer["holdout_ci95"][0]:.4f}, {newer["holdout_ci95"][1]:.4f}], evaluator `{newer["evaluator_version"]}`, n={newer["n_withheld_positives"]:,}. **This is NEGATIVE / DO NOT SUBMIT:** its own run card states it used the full catalogue during placement (holdout leakage risk) and checked only {newer["registry_champions_checked"]} champion rasters, not the full registry. Re-evaluate with per-fold visible catalogues and complete registry checks before promotion.

See [latest review (29 Oct 2026)](docs/repo-review-20261029.md), [Focus-9 site comparison](docs/executive-summary.html), and [the standing brief](PROMPT.md). Core values: **Maximize P(Win)** and **Own the Outcome**. Read `PROMPT.md` at the start of every working session; it preserves the operating requirements and links.

> Historical approval claims and frozen receipts below are retained for provenance only; these no-go notices supersede them.

"""

def brief_20261029_block():
    """Top-of-README pointer to the 29 Oct 2026 owner brief, executive summary and live verdict."""
    run = json.loads((ROOT / "evidence/candidates/wbggemsdoe1-tipgap2km-K12395-20261029.run_card.json").read_text())
    name = run["name"]
    canary = run["leakage_canary"]["detached_max_auc"]
    dup = run["registry_comparison"]["duplicate_count"]
    return f"""## 29 OCT 2026 STANDING BRIEF — READ FIRST EVERY SESSION

**Owner brief (condensed, official links kept):** [`docs/owner-brief-20261029.md`](docs/owner-brief-20261029.md). Read it at the start of every session, together with this README and [`AGENTS.md`](AGENTS.md).

**Unique-lane summary:** [Unique-lane results, 29 Oct 2026](docs/unique-lane-summary-20261029.html) (holdout arms, canary, the candidate file) · [How to submit](docs/how-to-submit-20261029.html) · [29 Oct executive summary](docs/executive-summary-20261029.html)

**Verdict now:** the new research TIFF `{name}` is **DOWNLOAD: {"YES (research)" if run["ok_to_download"] else "NO"}** and **SUBMIT: {"YES" if run["ok_to_submit"] else "NO"}**. Failed gates: leakage canary (detached max AUC {canary:.4f}, above the 0.90 limit) and the literal 70% uniqueness rule ({dup} registry rasters). No slot has been used. GEMSDOE32 B2's 0.2778 is USER-REPORTED, not organizer-confirmed.

"""


def tipcont_experiment_readme_block():
    """WBGGEMSDOE1 tip-continuation experiment (29 Oct 2026): research only, numbers from the measured JSON."""
    summ = json.loads((ROOT / "docs/data/tipcont_experiment_20261029.json").read_text())
    nf = summ["new_file"]
    h = nf["holdout_dti_catalogue_proxy"]
    u = nf["uniqueness"]
    zip_name = Path(nf["zeros_zip"]).name
    return f"""## WBGGEMSDOE1 tip-continuation experiment (29 Oct 2026) · research only · negative

- **Experiment page:** [tipcont-experiment-20261029.html](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/tipcont-experiment-20261029.html) (source [docs/tipcont-experiment-20261029.html](docs/tipcont-experiment-20261029.html)).
- **Research ZIP:** [`{zip_name}`](docs/downloads/{zip_name}) · SHA-256 `{nf['sha256_zeros_tif']}` · {nf['dots']:,} binary dots · run card [evidence/tip_continuation_20261029/run_card.json](evidence/tip_continuation_20261029/run_card.json).
- **Catalogue-proxy HOLDOUT-DTI** (`{h['evaluator']}`): {h['pooled_dti']:.6f}, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]; matched random null {h['matched_random_null_dti_2_5_97_5'][0]:.4f}–{h['matched_random_null_dti_2_5_97_5'][1]:.4f}. Lane STOP: {u['of_which_GEMSDOE25_family']} GEMSDOE25-family rasters exceed the 70% 3 px gate.
- **Estimated leaderboard score: UNAVAILABLE.** Not a submission candidate.

"""


def main():
    card = json.loads((ROOT / "registry/run_card.json").read_text())
    wbg_h1_rc = json.loads((ROOT / "evidence/wbg_h1/run_card.json").read_text())
    h, c, d = card["holdout"], card["control_holdout"], card["paired_delta_holdout"]
    tif = Path(card["artifact"]).name
    h1_tif = wbg_h1_rc["raster_sha256"]["tif_file"]
    h1_zip = wbg_h1_rc["raster_sha256"]["zip_file"]
    standing = (ROOT / "docs/standing-prompt.md").read_text()
    w2 = json.loads((ROOT / "evidence/wbg2/run_card.json").read_text())
    w2tif = Path(w2["artifacts"]["tif"]).name
    s2 = json.loads((ROOT / "evidence/wbg_s2/run_card.json").read_text())
    s2_tif = Path(s2["artifact"]["tif_path"]).name
    w3 = json.loads((ROOT / "evidence/wbg3_spipmr/run_card.json").read_text())
    w3_tif = Path(w3["artifact"]).name
    w3_zip = Path(w3["zip_artifact"]).name
    w3_seg = w3["holdout_dti"]["primary_segment_holdout"]
    w3_in = w3["holdout_dti"]["secondary_intrabasin_holdout"]
    w3_comp = w3["correlation_overlap_vs_registry"]["final_dots_competing_sparse"]
    w4 = json.loads((ROOT / "evidence/wbg4/run_card.json").read_text())
    w4_uniq = json.loads((ROOT / "evidence/wbg4/uniqueness_audit.json").read_text())
    w4_tif = Path(w4["artifact"]["tif_relpath"]).name
    w4_zip = Path(w4["artifact"]["zip_relpath"]).name
    w4_seg = w4["holdout_dti"]["primary_segment_holdout"]
    w4_in20 = w4["holdout_dti"]["secondary_intrabasin_holdout"]
    w4_c77 = w4["holdout_dti"]["untouched_confirmation_holdout"]
    w4_comp = w4["registry_uniqueness"]["competing_sparse_max_forward_3px_overlap"]
    w4_r13 = w4_uniq["two_phase_summary"]["like_for_like_reading"]["worst_forward_overlap_dot_fields"] * 100
    w2audit = json.loads((ROOT / "evidence/wbg2/safety_audit_20261027.json").read_text())
    w2overlap = w2audit["already_placed_final_dots_witness"]["my_dots_within_3px_of_theirs"] * 100
    feed = json.loads((ROOT / "docs/data/feed.json").read_text())
    changed_head_count = sum(bool(row.get("changed_since_audit")) for row in feed.get("repository_heads", []))
    monitored_head_count = len(feed.get("repository_heads", []))
    leaderboard = feed.get("leaderboard") or {}
    leaderboard_value = leaderboard.get("public_dw_tversky")
    leaderboard_value_text = f"{leaderboard_value:.4f}" if isinstance(leaderboard_value, (int, float)) else "unavailable"
    leaderboard_date = leaderboard.get("observed_utc", leaderboard.get("observed_date_utc", "date unavailable"))

    f9 = json.loads((ROOT / "evidence/focus9_exec/run_card.json").read_text())
    f9_tif = Path(f9["artifact"]).name
    f9_zip = Path(f9["artifact"]).with_suffix(".zip").name
    w5 = json.loads((ROOT / "evidence/wbg5/diff1_run_card.json").read_text())
    w5_arms = w5["arms"]
    w5_tif = w5["submission_name"]
    w5_zip = Path(w5_tif).with_suffix(".zip").name
    w5_arm_b = w5_arms["B"]["holdout"]
    w5_arm_c = w5_arms["C"]["holdout"]
    w5_ci_b = w5_arm_b["ci95"]["interval"]
    w5_ci_c = w5_arm_c["ci95"]["interval"]
    w5_ci_a = w5_arms["A"]["holdout"]["ci95"]["interval"]
    w5_comp = w5["correlation_overlap_vs_registry"]["final_dots_competing_method"]
    w5_lit = w5["correlation_overlap_vs_registry"]["final_dots_literal"]
    w5_bench = w5["benchmark"]["dti"]
    header = brief_20261029_block() + wbg6_readme_block() + tipcont_experiment_readme_block() + f'''# WBG GEMS — evidence-first fault mapping

**[START HERE — 29 Oct 2026 executive summary (download / submit verdicts, estimates, nine-site table)](docs/start-here-20261029.html)** · No file is cleared for submission under the 70% protocol.
**[Repository review (2026-10-29)](docs/repo-review-current-20261029.md)** · no new TIFF approved; core competition inputs are absent and the active method lane is unspecified. Local tests and lint pass. Treat all existing candidate downloads according to their individual negative/STOP decisions.

**[28 October review of earlier lanes](docs/review-20261028.md)** · [Review run card](docs/data/review-20261028.json) · No file is cleared; WBG-6 fails the active literal overlap gate.

**[Current repository review (2026-10-28)](docs/repo-review-current-20261028.md)** · [Detailed repository review](docs/repo-review-20261028.md) · [Earlier repository review and ranked future hypotheses](docs/repo-review-20261027-session.md) ·
[Session JSON card](evidence/repo_review_session_20261027.json) · [Current provenance feed](docs/data/feed.json)

**Freshness check:** at `{feed.get("generated_utc", "timestamp unavailable")}`, {changed_head_count}/{monitored_head_count} monitored focus-site GitHub heads differed from the frozen raster audit. This is a head check, not a current raster/score audit. The official leaderboard status is `{feed.get("leaderboard_status", "unknown")}`; the last retained public observation is {leaderboard_value_text} ({leaderboard_date}), not a score for any project TIFF.

## FOCUS-9 EXECUTIVE SUMMARY — DOWNLOAD: RESEARCH ONLY · SUBMIT: NO

[Focus-9 site table, forensics and hypotheses](docs/focus9-executive-summary.html) ·
[How to submit](docs/how-to-submit.html) · [Hypotheses](docs/hypotheses.html)

**Research TIFF (synthetic random null; not a geological model):** [{f9_tif}](docs/downloads/{f9_tif}) · [ZIP](docs/downloads/{f9_zip}) · [Run card](evidence/focus9_exec/run_card.json). Format checks pass; no holdout score was measured. The output is byte-unique only within the checked snapshot inventory; the fixed-36,800-dot literal 3-pixel lattice-overlap lower bound is **81.932% (>70%)**; the full competing-sparse overlap is unmeasured. **DOWNLOAD: YES for research · SUBMIT: NO.**

GEMSDOE32 B2's **0.2778 is USER-REPORTED, not organizer-confirmed**. The supplied history suggests D2.8 → B1 → B2 pruning removed catalogue-near dots; this is a plausible precision/false-positive mechanism, not proof of new-fault discovery. Leaderboard score estimates for a new file are unavailable.

## 2026-10-28 SESSION — WBG-5 / DIFF1 (LiDAR scarp-lobe morphology) · NEGATIVE

**[Executive summary and decision table (28 Oct 2026)](docs/executive-summary-20261028.md)** ·
[Machine-readable summary](docs/data/executive_summary_20261028.json) ·
[DIFF1 run card](evidence/wbg5/diff1_run_card.json) ·
[Preregistration](research/06_wbg5_diff1_preregistration_20261028.md)

WBG-5 is a 28 October 2026 release carrying **two frozen sub-lanes**, both NEGATIVE and neither
approved: this **DIFF1** lane and the merged **MTA-1** lane
([docs/wbg5/index.html](docs/wbg5/index.html), [run card](evidence/wbg5/run_card.json)).

Executed the ranked-#3 untested hypothesis: a **catalogue-free, LiDAR-only diffusion-shape
scarp-lobe morphology detector** (crest/base curvature-lobe symmetry × scarp-height proxy ×
face-dominance veto). Three fixed arms, 281 s, **zero slots**.

| Arm | HOLDOUT-DTI (`gems-segment-pooled-v1`, 60,988 withheld positives) | 95% CI | Decision |
|---|---:|---|---|
| B — primary (symmetric lobe) | **{w5_arm_b['dti']:.5f}** | [{w5_ci_b[0]:.5f}, {w5_ci_b[1]:.5f}] | fails efficacy gate |
| A — amplitude control | {w5_arms['A']['holdout']['dti']:.5f} | [{w5_ci_a[0]:.5f}, {w5_ci_a[1]:.5f}] | control only |
| C — asymmetry ablation | {w5_arm_c['dti']:.5f} | [{w5_ci_c[0]:.5f}, {w5_ci_c[1]:.5f}] | ablation only |

Benchmark to beat: **HOLDOUT-DTI {w5_bench:.6f}** (GEMSDOE24 S3DEP1). Leakage canary **PASS**
(25 features, max |AUC| 0.583 ≤ 0.90). Surface novelty **PASS** (max |ρ| 0.564 ≤ 0.90). Final dots
**FAIL**: competing-method 3 px overlap **{w5_comp['max_competing_dot_overlap']*100:.2f}% > 70%**
(vs a published LiDAR-scarp raster) and literal all-entry overlap
**{w5_lit['max_dot_overlap']*100:.2f}% > 70%** (vs the retained spacing-5 lattice).

Artifact (research only): `{w5_tif}` (+ `{w5_zip}`, SHA-256 `{w5['raster_sha256']}`). Format PASS,
strict whole-array `[0,1]` PASS. **DOWNLOAD: YES · SUBMIT: NO.** A real upload needs a HOLDOUT-DTI
strictly above {w5_bench:.4f} with a positive paired 95% CI and full registry uniqueness; neither holds.

Verified public leaderboard #1 on 2026-10-28: **0.4544** (xiaofanhu) — a page observation, not a
score for any project file. The nine focus-site historical values remain OWNER-REPORTED / UNVERIFIED.

## NO FILE APPROVED FOR SUBMISSION

**[WBG-4 (CSJF-1) Executive Summary & Master Decision Table](docs/wbg4/index.html)** ·
**[How to Submit Subpage](docs/wbg4/how-to-submit.html)** ·
**[0.2778 PhD Forensics & 4 Hypotheses](docs/wbg4/forensics-and-hypotheses.html)** ·
[Download WBG-4 TIFF (research only)](docs/downloads/{w4_tif}) ·
[WBG-4 ZIP](docs/downloads/{w4_zip}) ·
[WBG-4 Run Card JSON](evidence/wbg4/run_card.json) ·
[464-Raster Uniqueness Audit](evidence/wbg4/uniqueness_audit.json)

**[WBG-3 Executive Summary & Master Decision Table](docs/wbg3/index.html)** ·
**[How to Submit Subpage](docs/wbg3/how-to-submit.html)** ·
**[0.2778 PhD Forensics & 4 Hypotheses](docs/wbg3/forensics-and-hypotheses.html)** ·
[Download WBG-3 TIFF (research only)](docs/downloads/{w3_tif}) ·
[WBG-3 ZIP](docs/downloads/{w3_zip}) ·
[WBG-3 Run Card JSON](evidence/wbg3_spipmr/run_card.json) ·
[Parallel EXP3DET Summary](docs/wbg3.html) ·
[Parallel EXP3DET Run Card](evidence/wbg3/run_card.json)

**[Executive audit and nine-site table](docs/wbg2.html)** ·
[Download WBG-2 TIFF for research only](docs/downloads/{w2tif}) ·
[ZIP for research](docs/downloads/{w2tif.replace('.tif', '.zip')}) ·
[run card](evidence/wbg2/run_card.json) · [shared-gate audit](evidence/wbg2/safety_audit_20261027.json)

**[Current repository review (2026-10-27)](docs/repo-review-current-20261027.md)** · [Review-only run card](evidence/current_review_card_20261027.json). No new raster, experiment, or slot; the lane remains stopped.

| Artifact | Local format | Score estimate / holdout | Literal registry decision |
|---|---|---|---|
| `{w4_tif}` | One float32 band, zeros mode `[0, 1]`, 0 NaN/Inf, 35,135 binary dots; 15/15 checks PASS | **HOLDOUT-DTI {w4_seg['dti']:.6f}** (`{w4_seg['evaluator_version']}`, n={w4_seg['withheld_positives_n']:,}, 95% CI [{w4_seg['ci95'][0]:.6f}, {w4_seg['ci95'][1]:.6f}], +78.0% vs ctrl); **HOLDOUT-DTI {w4_in20['dti']:.6f}** (`seed=20`, n={w4_in20['withheld_positives_n']:,}); **Untouched Confirm HOLDOUT-DTI {w4_c77['dti']:.6f}** (`seed=77`, n={w4_c77['withheld_positives_n']:,}, +102.3% vs 0.051234 ctrl). Leaderboard est.: **Unavailable**. | **DO NOT SUBMIT**. Competing sparse (460 rasters across 24 repos): **PASS {w4_comp*100:.2f}% <= 70%** (max \|rho\| = 0.4952 <= 0.90). Literal overlap: **{w4_r13:.4f}%** vs `r13-lattice-s5` & **100%** vs `WBG-C1` (>70% STOP). |
| `{w3_tif}` | One float32 band, zeros mode `[0, 1]`, 0 NaN/Inf, 36,800 binary dots; 15/15 checks PASS | **HOLDOUT-DTI {w3_seg['dti']:.6f}** (`{w3_seg['evaluator_version']}`, n={w3_seg['withheld_positive_pixels']:,}, 95% CI [{w3_seg['ci95'][0]:.6f}, {w3_seg['ci95'][1]:.6f}], 4/4 fold wins vs 0.090781 ctrl); **HOLDOUT-DTI {w3_in['dti']:.6f}** (`{w3_in['evaluator_version']}`, n={w3_in['withheld_positive_pixels']:,}). Leaderboard est.: **Unavailable**. | **DO NOT SUBMIT**. Competing sparse (206 rasters): **PASS {w3_comp['max_forward_3px_overlap']*100:.2f}% <= 70%** (27.55% vs GEMSDOE32 B2; 43.40% vs WBG-S2). Literal overlap: **99.9946%** vs `r13-lattice-s5` & **100%** vs `WBG-C1` (>70% STOP). |
| `{w2tif}` | One float32 band, finite [0,1], grid matches pinned mirror; TIFF/ZIP bytes verified | **Unavailable**; fold-safe replay measures `HOLDOUT-DTI 0.000341` (`gems-segment-pooled-v1`) / `0.097610` (`gems57-pooled-hide-v2`); no organizer receipt | **DO NOT SUBMIT**. {w2overlap:.4f}% final-dot overlap with a registered lattice exceeds 70%. |

The previous WBG-2 "safe to upload" claim and numerical projection are **withdrawn**. The old
code applied a private enrichment exception, checked eight local references and a separate nine-champion
diagnostic rather than the full registry. The shared literal rule has no such exception. A retrospective surface check also fails and cannot establish that
pre-placement checks happened. This safety integration did no new training or placement and used no competition slot.
The historic catalogue buffer was Manhattan, not a 400 m Euclidean disc: 813 existing dots are
closer than 400 m Euclidean. The owner-mirror 19-band stack was restored and hash-checked, not
authenticated by DrivenData.
See [four untested research hypotheses](docs/research/future-hypotheses-20261027.md) and
[the 27 October source audit](evidence/official_source_audit_20261027.json) and
[three safety-review passes](evidence/wbg2/review_passes_20261027.json).
Concurrent reviews are preserved as historical context: [protocol](docs/protocol-review-20261027.md),
[repository](docs/repo-review-20261027.md), and [session](docs/session-review-20261027.md).
Their older private-distance metrics and 400 m buffer interpretation are superseded by the
shared-Euclidean safety audit above. The earlier raw approval remains archived, never authorized.

## Earlier file — DOWNLOAD: YES, for research. SUBMIT: **NO**.

**27 October 2026 follow-up: [four earlier releases, exact-byte revalidation and trust corrections](docs/portfolio-review.html)** ·
[Machine-readable review](docs/data/portfolio-review.json). No new experiment: the lane remains stopped.
All four are negative research downloads, not recommended contest submissions. Leaderboard estimates remain unavailable.
The [parallel exact-reference audit](docs/release-review.html) and its [review notes](docs/review-20261027.md) are also preserved; both reviews reach the same negative decision.

**[Open the research desk](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/)** ·
[Executive summary](docs/executive-summary.md) · [Submission guide](docs/how-to-submit.html) ·
[Exact JSON run card](registry/run_card.json)

**[Download the frozen research TIFF](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/downloads/{tif})** ·
[One-TIFF ZIP](docs/downloads/{tif.replace('.tif', '.zip')}) ·
[TIFF in repository](docs/downloads/{tif}) · [Validation receipt](docs/downloads/{tif.replace('.tif', '.json')})

> **NEGATIVE RESULT.** This is a genuinely generated, format-valid **continuous research surface**,
> not a final dotted or promoted competition submission. It fails paired efficacy and the literal
> registry-overlap gate. The method lane was not assigned in the prompt. **Do not upload it.**
> No final dots were placed, no real submission was selected, and **zero competition slots were used**.
> “Different bytes” is not “lane unique”; “local format pass” is not organizer acceptance.

| Artifact / decision | Measured evidence | Estimated leaderboard result | Exact-copy / literal uniqueness |
|---|---|---|---|
| [{tif}](docs/downloads/{tif}) — **research download only** | **HOLDOUT-DTI {h['dti']:.6f}**, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}], `{card['holdout_instrument']['evaluator_version']}`, {h['withheld_positive_pixels']:,} withheld positives | **Unavailable**. Not inferred from holdout. Organizer-confirmed artifact result: **none**. | Byte- and normalized-pixel distinct from all {card['registry']['checked_unique_file_hashes']} checked hashes; **FAIL** literal forward overlap {card['registry']['max_forward_3px_overlap']*100:.2f}% >70%. |

- Same-instrument 19-band control: **HOLDOUT-DTI {c['dti']:.6f}**, 95% CI [{c['ci95'][0]:.6f}, {c['ci95'][1]:.6f}], same evaluator, {h['withheld_positive_pixels']:,} positives.
- Paired difference: **HOLDOUT-DTI {d['delta']:+.6f}**, 95% CI [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}], same evaluator/positives. No improvement established.
- Scientific representation: **unplaced continuous OOF confidence**, not matched-budget sparse dots, calibrated probabilities or a hidden-test leaderboard forecast.
- Leakage canaries: all 23 individual inputs tested in four folds; max orientation/missingness AUC **{card['leakage_canary']['maximum_orientation_invariant_auc']:.6f}**, below 0.90. AUC is not DTI and passing this screen is not proof of no possible leakage.
- Local GeoTIFF: one float32 band, EPSG:32611, 3,730 × 3,292, 100 m, exact reference transform; all finite, min **{card['validator']['range_min']:.6f}**, max **{card['validator']['range_max']:.6f}**, zero outside the footprint and on the known catalogue.
- SHA-256: `{card['raster_sha256']}`.
- Name: `{card['submission_name']}`.
- Note (≤140 characters): `{card['submission_note']}`.

## Review outcome and historical learning

The starting checkout at `5d2236b` contained only `README.md` with a one-line title: no existing
training pipeline, data cache, previous-session tasks or site were present locally. This work built
an auditable project, restored the public mirrors and shared cache, and ran one preregistered screen.

The [nine-site executive summary](docs/executive-summary.md) covers **GEMSDOE24, 25, 27, 28, 30, 31,
32, 33 and 36**, linking exact original files and immutable source snapshots. Historical values
provided in the prompt are quarantined as **USER-REPORTED / NOT ORGANIZER-CONFIRMED** because no
submission-page receipt binds those bytes to a result. They are not relabelled HOLDOUT-DTI.

The largest supplied historical claim is **GEMSDOE32 B2, USER-REPORTED 0.2778**. The exact raster
identity is D2.8 44,090 dots → B1 40,199 → B2 37,654 by progressively removing catalogue-near dots.
GEMSDOE25 and GEMSDOE30 have identical decoded predictions. GEMSDOE36 is B2 plus 1,200 additions.
These are closely related fields, not nine independent geological discoveries. Sparse max-cover
credit and avoiding low-marginal-credit predictions are plausible reasons for the historical
ordering, not a causal proof from unavailable hidden labels. A 200 m exclusion is **not** an
organizer rule. No historical file should be copied into a new "unique" entry.

The official public leaderboard displayed **0.4544 on 2026-10-27** (public-page observation, not a project-file receipt), rather than the prompt's older targets. That is **not** an organizer result for any project TIFF. A higher project score
was not obtained or credibly projected in this session.

## Parallel work preserved during integration

- **[WBG-3 / SPI-PMR-WCS-1 (100% 1m-LiDAR-free & 10m-DEM-free)](docs/wbg3/index.html): DO NOT SUBMIT; no selector eligibility.**
  [How-to-submit subpage](docs/wbg3/how-to-submit.html) · [0.2778 PhD forensics & 4 hypotheses](docs/wbg3/forensics-and-hypotheses.html) ·
  [Research TIFF](docs/downloads/{w3_tif}) · [ZIP](docs/downloads/{w3_zip}) ·
  [run card](evidence/wbg3_spipmr/run_card.json) · [209-raster uniqueness audit](evidence/wbg3_spipmr/uniqueness_audit.json) ·
  [40-feature leakage canary](evidence/wbg3_spipmr/leakage_canary.json) · [preregistration](registry/wbg3_preregistration.json).
  TIFF SHA-256 `{w3['raster_sha256']}`; ZIP SHA-256 `{w3['zip_sha256']}`; name `{w3['submission_name']}`; note `{w3['submission_note']}` ({w3['submission_note_length']} chars).
  3/3 preregistered arms executed on 100 m competition geophysics + label-free SGMC/GDR (`444.3s`, 0 slots used).
  Beats 19-band control across 4/4 spatial folds: **HOLDOUT-DTI {w3_seg['dti']:.6f}** vs **0.090781** (`{w3_seg['evaluator_version']}`, paired ΔDTI `+0.027399`, 95% CI `[+0.014361, +0.041700]`) and **HOLDOUT-DTI {w3_in['dti']:.6f}** vs **0.076470** (`{w3_in['evaluator_version']}`).
  Passes full-footprint pre-placement correlation (`max |ρ| = 0.644883 <= 0.90`) and competing-sparse overlap across all 206 sparse rasters (`max 59.38% <= 70%`; `27.55%` vs `GEMSDOE32 B2`; `43.40%` vs `WBG-S2`), while binding literal overlap hits **99.9946%** vs `r13-lattice-s5` and **100%** vs `WBG-C1` and trails 10m-3DEP `S3DEP1` (`0.166060`).
- **[WBG-S2 / MKSF-1 result](docs/wbg-s2-mksf1/index.html): DO NOT SUBMIT; no selector eligibility.**
  [Research TIFF](docs/downloads/{s2_tif}) · [ZIP](docs/downloads/{s2_tif.replace('.tif', '.zip')}) ·
  [run card](evidence/wbg_s2/run_card.json) · [independent two-witness safety audit](evidence/wbg_s2/safety_review_20261027.json) ·
  [three safety-review passes](evidence/wbg_s2/safety_review_passes_20261027.json).
  TIFF SHA-256 `{s2['artifact']['tif_sha256']}`. Local format checks pass, but final dots overlap pinned
  r13 by **99.5538%** and WBG-C1 by **100%**; both exceed 70%. The sampled pre-placement
  Spearman screen is not full literal clearance. Three arms were run in the parallel session;
  this integration did not retrain or place new dots. Parallel-reported selected-arm
  **HOLDOUT-DTI 0.183594**, 95% CI [0.170313, 0.196956], `gems-segment-pooled-v1`, n=60,988;
  **HOLDOUT-DTI 0.147773**, 95% CI [0.128077, 0.167791], `gems57-pooled-hide-v2`, n=11,330.
  Arms were selected on these splits, not independently replayed here or confirmed on untouched data.
  They are not a verified fleet ranking, organizer score or leaderboard forecast.

While this branch was working from the one-line initial checkout, other sessions merged TIP1 and
MVGZ negative results into `main` (integrated snapshot `b9a2d5301c0c971dcc1219f9ad6b29c68f68ee21`).
Their frozen scientific modules, receipts and artifacts are retained; they were **not rerun**.
The earlier WBG-C1 screen used one experiment; the parallel WBG-S2 run used three separate arms.
This safety integration started no experiment and did not reset any inherited budget.
Different evaluator/split/representation results must not be pooled or ranked as comparable scores.

- [Original parallel site, with its own frozen assets and data](docs/parallel/main-b9a2d53/index.html)
- [Original main README](research/inherited-main-README-b9a2d53.md) (historical commands/paths)
- [Byte-preservation/integration receipt](evidence/parallel_main_integration.json)
- [Frozen TIP1 card](evidence/tip1_run_card_20261026.json) and [MVGZ card](evidence/run_card.json)
- **[WBG-H1 / DPGF-1 corrected result page](docs/wbg-h1-dpgf1/index.html)** — research only, **DO NOT SUBMIT**.
  [TIFF]({h1_tif}) · [ZIP]({h1_zip}) · SHA-256 `{wbg_h1_rc['raster_sha256']['tif_sha256']}`.
  Name `{wbg_h1_rc['submission_name']}`. Frozen **HOLDOUT-DTI {wbg_h1_rc['holdout_dti']['dti']:.6f}**,
  95% CI [{wbg_h1_rc['holdout_dti']['ci95'][0]:.6f}, {wbg_h1_rc['holdout_dti']['ci95'][1]:.6f}],
  `{wbg_h1_rc['holdout_dti']['evaluator_version']}`, {wbg_h1_rc['holdout_dti']['n_withheld_positives']:,} withheld positives.
  Literal lattice overlap **99.8035%** exceeds 70%; sparse/symmetric checks do not authorize an exemption.
  The inherited LLI forecast, claims of organizer-confirmed scores, and private-count inversion are
  **not verified evidence**. Original cards remain frozen with explicit corrections on the live page.
- Older two-argument `validate_submission.py candidate.tif reference.tif` callers retain their
  supplied-reference format API; this is compatibility only and never confers slot approval.
  WBG-C1 still uses the unchanged, pinned `gems57` all-finite validator/writer.
  The separate integration CLI now rejects mismatched source grids, input overwrite aliases and
  portal-unsafe NaN twins; [explicit source amendment](evidence/integration_amendments_20261027.json)
  preserves its prior hash/archive. No metric, evaluator or pinned-template fork was introduced.
- The older bridge-specific restore entry point is retained as `scripts/download_bridge_legacy.sh`
  with `scripts/prepare_bridge_legacy.py`; current WBG-C1 commands below are unchanged.

## What is implemented

- [Four earlier ranked hypotheses](docs/hypotheses.md), with layers, transforms,
  missing-catalogue rationale, mimics, novelty limits and data readiness. Only WBG-C1 was tested.
- A catalogue-blind conductivity/depth Hessian-commutator transform and scale/strain support.
- **Unchanged shared template** at `buffedlizard55-lab/57GEMSDOE@822a0ce5546c7b6749cdd82eb145b6b3e616603d`:
  cache builder, buffered whole-component holdout, `evaluate_holdout.py`, metric, registry gates
  and fail-closed `submission_writer.py`. [All 24 source hashes](evidence/template_integrity.json).
- All **19 original cache hashes** reproduced. Inputs are **owner mirrors**, not independently
  authenticated organizer downloads. Large inputs/cache/research clones are ignored by Git.
- Frozen spatial LOQO screen: whole components withheld globally, feature buffer, 8 km training
  collar, visible faults masked pixel-exactly, pooled alpha=0.2/beta=0.8/300 m DTI, paired 20 km
  physical-cluster bootstrap. [Full output](evidence/experiment.json).
- Single-feature leakage canaries, exact-file format/ZIP validation, **360-hash / 377-source-path**
  nine-snapshot registry audit with no lattice/density exemption, fail-closed promotion decision.
- Clean static GitHub Pages desk, executive-summary and submission-guide subpages, direct TIFF/ZIP
  downloads, immutable source links, JSON evidence, explicit stale/unknown feed behavior.
- Scheduled public-provenance refresh. It checks the official public leaderboard and upstream heads,
  but **never retrains, changes an approval, spends a slot, commits, or uploads a competition file**.

## Setup, data placement and verification

CPU research is supported; a GPU is **not** a universal prerequisite for this project.
GitHub access is needed for the hash-pinned public bridges; no DrivenData credentials are stored.

```bash
python -m venv .venv
.venv/bin/pip install -e '.[test]'
# For exact research dependency versions, use requirements-lock.txt.
bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py
.venv/bin/pytest -q

# Reopen the actual downloadable bytes. Exit 0 means FORMAT pass only.
.venv/bin/python scripts/validate_submission.py docs/downloads/{tif}
# Deliberately exits 2 for this locally valid but unapproved artifact:
.venv/bin/python scripts/validate_submission.py --require-submit-ready docs/downloads/{tif}

# Restore frozen peer corpus only for audit, never model inputs:
.venv/bin/python scripts/fetch_repositories.py
.venv/bin/python scripts/audit_repositories.py
# The next command audits the unchanged surface; it does NOT retrain/place dots:
.venv/bin/python scripts/audit_registry.py

# Reopen all four local releases (no modelling, no slot):
.venv/bin/python scripts/build_portfolio_review.py

# Rebuild report pages from persisted measured JSON (no modelling):
python scripts/refresh_feed.py --offline
python scripts/build_site.py
python scripts/build_readme.py
# Preview, not for production deployment:
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

Optional rendered-site checks on Linux (not needed to build or deploy the site):

```bash
npm ci
# Against the running static preview on the test machine:
BASE_URL=http://127.0.0.1:8000/ npm run test:browser
# Minimal containers without NSS/NSPR may also need BROWSER_COMPAT_LIBS=1.
```

The browser check visits all nine current pages at desktop/mobile sizes, rejects body overflow and
JavaScript page errors, tests the site filter, and hashes all four actual downloaded TIFFs.
Screenshots stay in ignored `.cache/browser-review/`; the JSON receipt is inspectable in
[evidence/browser_checks.json](evidence/browser_checks.json). These are site checks, not evidence
of scientific efficacy or organizer upload acceptance.

`scripts/run_experiment.py` contains the exact frozen training screen. Its persisted experiment
ledger and result guard deliberately **prevent silent reruns or retuning of this stopped lane**.
Recomputing DTI/CI from persisted block terms and revalidating artifacts is allowed; another
hypothesis needs a separately authorized prospective record, not deletion of the failed result.
There is no competition uploader. This static site serves a real pre-generated artifact; it does
not falsely claim that a browser button trains the model.

## Limitations and highest-priority next work

1. **No final high-scoring upload-ready submission was produced.** The unique-byte research TIFF
   fails the scientific and literal-overlap gates. Stop is binding; no final-dot check is claimed.
2. **Missing lane and registry policy:** establish an actual single-method assignment and a separately
   authorized scope policy. Do not privately exempt lattices/dense surfaces or target lattice holes.
3. **Input provenance and semantics:** verify official-origin data and original per-band meanings.
   `tc` and the depth-surface interpretation are ambiguous in mirror/peer materials. Do not claim
   physical units, heat or permeability from a classifier on unverified descriptors.
4. **Honest current-best comparison:** the clean 19-band control was refitted, but an identically
   rerun cross-repository best and untouched confirmation were not established. Static historical
   catalogue-derived rasters must not be scored as if they were leak-free refitted models.
5. **Authentication and weekly cap:** the official submissions endpoint redirects to login.
   The rule PDF says up to three weekly; the account's actual remaining allowance and exact-file
   score receipts are unavailable. Never request or store credentials in chat or Git.
6. **Coverage and confidence:** nine frozen snapshots are not all 92 sites, releases/private files
   or later commits. Hide-and-recover and conditional bootstrap intervals are not hidden-new-fault
   leaderboard estimates. Negative/background labels remain incomplete. Separately fitted OOF
   models can create confidence seams; geometric patterns in the thumbnail are not verified faults.
7. **Scientific target:** competition faults are not direct vent/resource confirmation. Future
   geothermal discovery needs convergent independent evidence, not just a probability map.
8. **Pages administration scope:** the integration cannot change Pages settings (HTTP 403).
   The existing main/root publisher is retained; `scripts/stage_pages.py` gives workflow deploys
   the same root-to-`/docs/` layout. This avoids incompatible download paths without a manual
   configuration change. Only actual GitHub run/deployment receipts establish publication.

[Official-source claim register](registry/sources.json) · [Irregularities](registry/irregularities.json)
· [Frozen preregistration](registry/preregistration.json) · [Review passes](evidence/review_passes.json)

## Project principles

**Maximize P(Win):** prioritize reliable out-of-sample evidence and scientific novelty over
more submissions, cosmetic file changes or public-leaderboard overfitting.
**Own the Outcome:** validate exact output bytes, preserve negative results, surface access gaps,
and never hand an unapproved file to the user as an upload recommendation.

## Starting point for every future session

Read this current status, `registry/run_card.json`, `registry/irregularities.json`, and the full
standing request below before work. Historical claims and intended capabilities in the prompt are
not verified facts. The measured run card takes precedence over stale factual assumptions.

<details>
<summary><strong>Complete standing user request — archived intent, not verified findings</strong></summary>

'''
    (ROOT / "README.md").write_text(header + standing + "\n</details>\n", encoding="utf-8")
    print("README updated with current decision and the complete archived standing request.")


if __name__ == "__main__":
    main()
