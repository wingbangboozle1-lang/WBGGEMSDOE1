# Repository review — 27 October 2026

## Decision

**No newly generated TIFF is approved for competition submission.** This review did not start a new geological experiment, place dots, select a weekly slot, or upload a file. The existing downloads remain research artifacts only: **DOWNLOAD: YES (research/audit only) · SUBMIT: NO**.

This is intentional. The active WBG-C1 lane is recorded as `negative_stopped`; its surface hit a literal registry-overlap stop. The request's supposed single method paragraph is not present as an assigned new lane, and no permission exists to restart/retune a stopped lane or privately waive a registry witness. Generating a new “unique” raster now would violate the declared protocol rather than satisfy it.

- [WBG-3 decision and downloadable research artifact](wbg3/index.html) — format passes locally, but literal registry overlap is reported as 99.9946% against `r13-lattice-s5` and 100% against WBG-C1; **DO NOT SUBMIT**.
- [Nine-site comparison](executive-summary.html) — highest supplied focus-site value is GEMSDOE32 B2, **USER-REPORTED 0.2778, not ORGANIZER-CONFIRMED**. No defensible leaderboard estimate exists for a new candidate.
- [Four prospective hypotheses](research/future-hypotheses-20261027.md) — proposals only; none was executed in this review. A separate five-hypothesis WBG-3 preregistration is archived in `research/04_wbg3_hypotheses_20261027.md`.
- [Machine-readable review card](../evidence/current_review_card_20261027.json).

## Focus-site findings

The requested sites are all represented in the existing nine-site review. The reported historic values below originate from the owner prompt and are not tied here to artifact-linked organizer receipts. They are not holdout scores or score estimates for a new file.

| Site | Highest cited artifact in the supplied record | Reported value and evidence class | New-file recommendation |
|---|---|---:|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 — USER-REPORTED / unverified | None; do not copy historical predictions |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 — USER-REPORTED / unverified | None; same decoded prediction field as GEMSDOE30's cited D2.8 |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 — USER-REPORTED / unverified | None; historic submission, not evidence for a new one |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 — USER-REPORTED / unverified | None; highly related to the H27/H32 family |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 — USER-REPORTED / unverified | None; decoded predictions match GEMSDOE25 D2.8 |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 — USER-REPORTED / unverified | None; same prediction field as GEMSDOE28 SOLO per frozen audit |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778 — USER-REPORTED / unverified; highest of these supplied claims** | Learning/forensics only; not a fresh unique submission |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 — USER-REPORTED / unverified | None; historical analogue/extension result |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 — USER-REPORTED / unverified | None; related to GEMSDOE32 B2 plus additions |

The underlying raster comparisons and immutable owner-repository snapshots are linked in the existing nine-site report/evidence. The table is not a fresh external source audit. “Unique” is not claimed merely because filenames or TIFF bytes differ; the shared rule is a STOP if the candidate's rank correlation exceeds 0.90 or more than 70% of its dots fall within 3 px of any one registry raster.

## Exact-file and readiness checks performed

- `.venv/bin/pytest -q`: **192 passed**, with 15 Rasterio `PendingDeprecationWarning`s.
- `.venv/bin/ruff check --select E9,F scripts src tests`: passed.
- `git diff --check`: passed before this documentation-only change.
- `scripts/review_releases.py --check`: passed exact-release checks; reported all listed artifacts locally format-valid, none submit-ready, and zero new experiments.
- Reopened the C1, WBG-2, and WBG-3 TIFFs and their ZIPs with `scripts/validate_submission.py`. Local checks include single-band float32, EPSG:32611, 3,730 × 3,292, exact mirrored reference transform, all-finite values, and min/max in [0,1]. These are **format-only** results, not organizer acceptance, scientific efficacy or uniqueness clearance.
- The strict `--require-submit-ready` check on WBG-3 exited 2, as expected for a negative/unapproved artifact.
- `scripts/check_readiness.py` returned `BLOCKED_INPUTS` / exit 2: `data/training_features.tif`, `data/labels.tif`, and `data/sample_submission.tif` are absent. The pinned template files are present and hash-matched; the 19-band cache is not present in this checkout. Owner-mirror hash records do not authenticate organizer origin.

## Three review passes

1. **Implement / verify:** Re-read `PROMPT.md`, the full archived request in `README.md`, `AGENTS.md`, current preregistration/ledger, the nine-site audit, run cards, evidence, and export validators. The nine-site table and prior hypothesis queue already satisfy the documented analysis requirements; the missing assigned lane and negative stop preclude a new experiment. Added this dated audit and a machine-readable negative card without touching a raster or template.
2. **Bug / edge-case review:** Exercised the exact TIFF/ZIP validator, including its strict approval mode, and the release-integrity check. Confirmed format pass is not conflated with submit approval; the strict command fails closed. Verified missing full inputs are explicitly reported as blocked rather than treating successful unit tests as training readiness.
3. **Original-request recheck:** Confirmed each requested focus site is enumerated, historical values are labeled unverified, the leading reported artifact is not proposed for copying, estimates are withheld rather than invented, and no file is labelled safe to submit. The current file-download pages prominently say **DO NOT SUBMIT**. The one unresolved request is the desired newly generated unique/high-scoring TIFF; it cannot be produced under the active stop and missing authorized lane without violating the protocol.

## Irregularities and limitations

1. The 0.2778 GEMSDOE32 value and all other listed focus-site values are supplied owner claims in the local evidence, without artifact-linked organizer receipts.
2. The public competition data requires account access in this environment; the three core competition inputs and feature cache are absent. Existing mirrored files and recorded hashes are not independently authenticated DrivenData downloads.
3. Current official DrivenData, USGS, DOE/GDR, and NLR pages were not freshly fetched during this review. Links are provided for manual source review in [the source catalogue](sources.html); this environment's outbound allowlist prevents fetching those hosts. No new external-data candidate is declared obtainable or viable.
4. The published historical `HOLDOUT-DTI` measurements use their stated evaluators and splits. They do not constitute an organizer score, a calibrated leaderboard estimate, or a directly comparable test of the nine historical files.
5. Local all-finite zero-outside-footprint TIFF validation may differ from the published official instruction about outside-bounds nulls. Local format checks cannot establish organizer acceptance or explain the previously reported range error without the rejected bytes and portal receipt.
6. A TIFF can be byte-unique yet fail the literal spatial registry gate. No user-requested high-scoring final candidate passed all gates, so **no submission name/note is approved**.

## Next session priorities

1. Resolve the shared registry saturation/uniqueness protocol and assign a new method paragraph centrally. Do not revive or privately fork the stopped lane.
2. Through authorized access, restore the official competition bundle; verify hashes and provenance, then build the exact pinned feature cache.
3. Reconfirm the current same-evaluator benchmark and holdout setup before any newly preregistered lane. Rank the existing five proposals, verify required layers and free official source availability, and run each individual feature's leakage canary.
4. Run no more than three experiments or two hours; require pre-placement and final-dot literal registry checks, a positive paired holdout result, untouched confirmation, and strict format validation before referring a candidate to the separate slot selector.
5. If a real upload is eventually made by an authorized selector, archive the exact submission-page receipt, file hash, note, and result. Until then, keep the feed and reports explicit that organizer-confirmed project scores are unavailable.

**Review verdict: negative.** No TIFF was generated or approved in this review; zero experiments and zero competition slots were used.
