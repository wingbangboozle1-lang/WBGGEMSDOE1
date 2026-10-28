# WBG-3 evidence and presentation correction review — 2026-10-27

**Scope:** documentation, generated reports, and exact-file preflight reconciliation only. No experiment, model run, raster edit, new TIFF, or submission-slot action was taken. The missing assigned-lane authorization remains unresolved; the scientific lane is stopped.

## Pass 1 — evidence, score classes, and causal language

- Compared `scripts/build_wbg3_site.py`, its generated `docs/wbg3/forensics-and-hypotheses.html`, `docs/wbg3-executive-summary.md`, `docs/wbg3.html`, `docs/research/why-02778.md`, `evidence/h33_b2_forensics.json`, the nine-site raster audit, and the two distinct WBG-3 run cards.
- Preserved the measured B2 ancestry: D2.8 has 44,090 positive pixels; B1 has 40,199 after 3,891 catalogue-near deletions; B2 has 37,654 after 2,545 further deletions. B2 removes 6,436 parent pixels within 200 m and adds none. The reported 0.2778 remains **OWNER-REPORTED / UNVERIFIED**; no hidden labels or artifact-linked receipt establishes its cause.
- Replaced assertions that pruning caused the reported change with a conditional metric interpretation. Removed the unsupported ~0.28 ceiling, fixed `TP_w` increases to reach named scores, and the claim that a particular NaN comparison explains a prior portal error. The current prose states that the portal-error cause is unverified.
- Kept the legacy EXP3DET JSON card unchanged. Its two-anchor `MODEL-ESTIMATE` is mentioned only as historical, explicitly unvalidated and not a forecast; the numeric estimate is suppressed from current summaries. The frozen card's former “designated file if a slot were spent” sentence is expressly superseded and is not a selection recommendation.
- Kept the current SPI-PMR-WCS result distinct from EXP3DET: its own leaderboard estimate is null, its HOLDOUT-DTI is labeled as such, and its verdict remains negative.

## Pass 2 — exact artifact, format, registry, and submit-status checks

- Reopened the current SPI-PMR-WCS research TIFF: `docs/downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.tif`; SHA-256 `f158a890dcb5f897ef35282ed05d291e54c4df9b83cf891870193d329b160fb4`; one float32 band, EPSG:32611, shape 3730×3292, finite values in `[0, 1]`, 36,800 positive pixels. Local validation passes; it is not organizer acceptance.
- Corrected `scripts/validate_submission.py` so exact WBG-3 TIFF bytes resolve to the appropriate archived run card rather than being mislabeled untracked. Current SPI-PMR-WCS and legacy EXP3DET both format-pass, match their exact cards, report `verdict=negative` and `ok_to_submit=false`. `--require-submit-ready` returns exit 2 for both.
- The current SPI-PMR-WCS file passes the competing-sparse comparison across 207 recorded comparators (max forward 3-pixel overlap 59.3777%), but fails the binding literal gate: 99.9946% against the spacing-5 calibration lattice and 100% against WBG-C1. It is therefore **not globally unique or submission-cleared**.
- The current run card reports HOLDOUT-DTI `0.118180`, 95% CI `[0.103658, 0.132432]`, evaluator `gems-segment-pooled-v1`, 60,988 withheld positives. It is a research measurement, not a leaderboard estimate. Zero slots were used; no organizer-origin authentication is claimed.
- The independent release review reports `all_exact_artifacts_format_valid=true`, `any_ok_to_submit=false`, `new_experiments=0`.

## Pass 3 — request coverage, source limits, site rebuild, and regression checks

- The active WBG-3 summaries compare all nine focus sites, label all historical values **OWNER-REPORTED / UNVERIFIED**, distinguish measured positive-pixel counts and file ancestry, and state that no leaderboard estimate is available.
- The generated forensics page ranks four prospective geological hypotheses with named mimics and provenance/coverage limitations. No candidate was newly validated: no assigned lane-method paragraph was found and the scientific lane is stopped. The earlier SPI-PMR-WCS package HOLDOUT-DTI is explicitly identified as a prior package-level result, not validation of any individual mechanism or of the new Rank 1 proposal.
- Official competition, rules, USGS, DOE/GDR, and NASA source links are included for review. They do not imply every current page or raw dataset was freshly retrieved. The mirror restore verifies hashes against the owner mirror, not organizer-origin authenticity.
- Regenerated the static site with `scripts/build_site.py` and README with `scripts/build_readme.py`; both completed. Checked 81 local links across the six affected HTML/Markdown pages; no broken local target was found.
- Full test suite: **195 passed, 15 warnings** (Rasterio `PendingDeprecationWarning` only). Targeted WBG-3/CLI/site tests: **67 passed, 1 warning**. `scripts/review_releases.py --check` passed; `git diff --check` and Python compilation passed.

**Final review decision: DOWNLOAD: YES, research only. SUBMIT: NO — DO NOT SUBMIT. No weekly slot was selected.**

**Maximize P(Win):** do not spend a slot based on an unverified estimate.

**Own the Outcome:** preserve the negative verdict and the limits of the evidence.

## Integration follow-up — merged-main reconciliation

- Fetched `origin/main` at `6d1643ee` (including the merged Focus-9 and fail-closed registry updates) and integrated it into this branch without switching branches. Resolved the exact-card lookup to retain WBG-3 and add Focus-9 negative-card matching.
- Audited the newly active Focus-9 executive page. Removed unsupported B2 false-positive causation, denominator arithmetic, ~0.28 ceiling, fixed-TP targets, and the unmeasured `≈0.0003` expectation. The page now distinguishes the deletion-only raster ancestry from score causation, labels all estimates unavailable, presents four prospective hypotheses as untested, and states the current owner-mirror/readiness limitations.
- Focus-9 synthetic TIFF SHA-256 `e8c4bf7607cec72c54981b90aa60e7e85163b429b58ebd6f2a7c3126e8c1e351`: local format preflight passes, but it has no geological model or HOLDOUT-DTI; competing-sparse overlap is unmeasured, and the 36,800-dot literal lattice lower bound is 81.932%. Its exact negative card matches; strict submit-ready mode exits 2. **DOWNLOAD: YES for research/UX only; SUBMIT: NO.**
- Rebuilt the static site, WBG-2/WBG-3 reports, README, and Pages staging. The main branch's earlier `BLOCKED_INPUTS` snapshot is explicitly superseded: current readiness is `BLOCKED_SCIENTIFIC` because local inputs/cache hashes match owner mirrors but scientific authorization and organizer-origin authentication remain unavailable.
- Post-integration verification: **203 tests passed, 15 warnings**; Ruff E9/F passed; exact-release review passed with zero approvals and zero new experiments; strict submit-ready validation exited 2 for Focus-9, WBG-3 SPI-PMR-WCS, and legacy EXP3DET. Readiness returned `BLOCKED_SCIENTIFIC` / expected exit 2. No experiment, raster generation, lane validation, or slot action occurred.
