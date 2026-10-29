# Agent instructions for WBGGEMSDOE1

Read `PROMPT.md`, the current README status, and [`docs/repo-review-current-20261029.md`](docs/repo-review-current-20261029.md) before starting project work. The full original user request is archived in the README and `docs/standing-prompt.md`.

## Current binding status — 29 October 2026

- **NO CURRENT TIFF CLEARED — DO NOT SUBMIT.** Downloadable, byte-unique, and locally format-valid do not mean upload-approved.
- GEMSDOE32 B2 `0.2778` is **OWNER-REPORTED / NOT ORGANIZER-CONFIRMED**. Never copy a historical prediction or report a new-file leaderboard estimate without validated evidence.
- The blind-fault-adjacency archived result's HOLDOUT-DTI 0.4657 is **leakage-confirmed** because dot placement used the full catalogue. Its visible-only per-fold recheck is HOLDOUT-DTI 0.006946 (evaluator `WBGGEMSDOE1-HIDE-RECOVER-v1.0`, n=60,161, CI not recomputed), numerically below the separate HOLDOUT-DTI 0.166060 comparator (`gems-segment-pooled-v1`, n=60,988, 95% CI [0.151858, 0.180339]), but the recorded evaluator versions differ, so this is not a like-for-like benchmark comparison. Receipt: `evidence/per_fold_recheck_blind_adjacency.json`. Do not submit it.
- `data/training_features.tif`, `data/labels.tif`, `data/sample_submission.tif`, and the 19-band cache are absent from this checkout. An owner-mirror integrity receipt exists, but the ignored blobs are not present and it does not establish organizer-origin provenance. `scripts/check_readiness.py` returns `BLOCKED_INPUTS` (exit 2).
- The assigned single-method paragraph is absent. The local WBG-C1 lane ledger is `negative_stopped`; do not restart it, retune it, or use its unused budget as authorization for another method. No new experiment or submission slot was used in the 29 Oct repository review.
- The official public leaderboard was observed at 0.4544 on 29 Oct 2026. This is a **public-page observation**, not a score for a project TIFF. The official competition data page resolves to login here.
- Read `registry/experiment_ledger.json`, `registry/preregistration.json`, `registry/irregularities.json`, and the Focus-9 executive summary before changing claims. Keep frozen receipts intact.

## Parallel-run protocol

1. Stay within the explicitly assigned single method. If the assignment is missing, stop at research planning. For an authorized lane, compare the pre-placement surface and final dots against the full authorized registry; Spearman absolute correlation >0.90 or >70% forward 3-pixel overlap is a stop. Do not replace the literal threshold with density-adjusted exemptions or tune around registry gaps.
2. Reuse the pinned shared template/cache, `scripts/evaluate_holdout.py`, and `scripts/submission_writer.py`. Hide whole fault segments with buffers; derive catalogue features from visible faults only in each fold; mask visible faults pixel-exactly; use pooled DTI with α=0.2, β=0.8, and a 300 m triangular kernel. Fix shared-tool defects centrally, not in a private fork.
3. Label numeric results **HOLDOUT-DTI** (evaluator version, withheld-positive count, 95% CI) or **ORGANIZER-CONFIRMED** (artifact-linked receipt). Preserve OWNER-REPORTED historical values as such. HOLDOUT-DTI is not a leaderboard score or projection.
4. Test each feature alone for leakage; AUC >0.90 is leakage until explained. Do not claim canary validation if skipped.
5. Preserve a complete JSON run card: hypothesis, mechanism, named non-fault mimic, measured HOLDOUT-DTI and CI or explicit “not run,” registry correlation/overlap, raster SHA-256 or null, validator output, submission name and ≤140-character note, verdict promote/negative.
6. Stop at 3 experiments or 2 hours per authorized run. Do not select a live slot; promotion is a separate selector step. Never upload automatically.

## Working standards

- Prefer official primary sources. State whether the page or actual bytes were checked; a public listing does not establish download, coverage, semantics, license suitability, or scientific utility.
- The competition target is mapped faults indicative of geothermal resources, not confirmed geothermal vents. Faults are not proof of heat, permeability, or commercial viability.
- Do not use hide-and-recover holdout as a leaderboard score estimate. If no estimator is externally validated, report the estimate as unavailable.
- Official output format requires a single-band float32 GeoTIFF in EPSG:32611 at the sample grid, values in [0,1], and null/NaN outside the region. Local validator success is not organizer acceptance.
- Keep large generated data out of Git unless required. Never request or store DrivenData or GitHub credentials.
- Run tests, static checks, and three review passes for substantial changes. Keep README and generated Pages in sync with the no-go status.

## Core values

**Maximize P(Win). Own the Outcome.** A supported negative decision that prevents an unvalidated or duplicate upload is preferable to a fabricated high score.
