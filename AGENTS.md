# Agent instructions for WBGGEMSDOE1

Read `PROMPT.md`, the current README status, and [`docs/repo-review-current-20261029.md`](docs/repo-review-current-20261029.md) before starting project work. The complete user brief is archived in the README's expandable section and `docs/standing-prompt.md`.

## Current binding status (2026-10-29)

- **NO CURRENT TIFF CLEARED — DO NOT SUBMIT.** Do not imply that “downloadable,” “unique bytes,” or local format validation means upload approval.
- GEMSDOE32 B2 `0.2778` is **OWNER-REPORTED / NOT ORGANIZER-CONFIRMED**. Do not copy prior submissions or present a leaderboard estimate without validated evidence.
- The working tree lacks the competition core TIFFs and shared feature cache. `python scripts/check_readiness.py` reports `BLOCKED_INPUTS` and exits 2. Public owner-mirror hash matches are not organizer-origin authentication.
- The prompt's assigned single-method lane paragraph is absent. The local WBG-C1 ledger is `negative_stopped`; do not resume or retune it. Do not start a different lane, test, or dot placement without valid lane authorization and preregistration. The present review started zero experiments and used zero competition slots.
- Read `registry/experiment_ledger.json`, `registry/preregistration.json`, `registry/irregularities.json`, and the focus-site executive summary before changing research claims. Frozen receipts are historical evidence and must not be rewritten to look current.

## Parallel-run protocol

1. Stay inside the explicitly assigned single method. If the assignment is missing, stop at research planning. For a permitted lane, compare the pre-placement surface and final dots against the authorized registry; Spearman absolute correlation >0.90 or >70% forward 3-pixel overlap is a stop. Do not silently substitute density-normalized gates or tune around registry gaps.
2. Reuse the pinned shared template/cache, `scripts/evaluate_holdout.py`, and `scripts/submission_writer.py`. Hide whole fault segments with buffers; recompute catalogue-derived features from visible faults only; pixel-exactly mask visible faults; use pooled DTI with α=0.2, β=0.8, and the 300 m triangular kernel. Fix shared tooling only in the shared template and report the change.
3. Label each numeric result **HOLDOUT-DTI** (evaluator, withheld-positive count, 95% CI), **ORGANIZER-CONFIRMED** (artifact-linked receipt), or **OWNER-REPORTED**. Holdout DTI is not a leaderboard score or projection.
4. Run each feature-alone leakage canary; AUC >0.90 is leakage until explained. Do not claim leakage-free validation if a canary was skipped.
5. Preserve a complete JSON run card: hypothesis, mechanism, named non-fault mimic, measured HOLDOUT-DTI and CI or explicit “not run,” registry correlation/overlap, raster SHA-256 or null, validator output, submission name/note ≤140 characters, and promote/negative verdict.
6. Stop at 3 experiments or 2 hours per authorized run. Do not select a live slot; promotion is a separate selector step. Never upload automatically.

## Working standards

- Prefer official primary sources and link them. Record whether a source page or the actual data bytes were checked; a listing is not proof of downloaded data, coverage, metadata, license compatibility, or scientific usefulness.
- Do not call mapped faults geothermal vents, active conduits, or proven resources. Faults are the competition's prediction target; geothermal interpretation requires independent corroboration.
- Do not use a model-derived holdout as an estimated hidden leaderboard result. Report estimates as unavailable where no calibration is validated.
- Keep generated data out of Git unless expressly required. Do not request or store DrivenData or GitHub credentials.
- Run tests/static checks and at least three review passes for substantial changes. Keep the README generated from `scripts/build_readme.py` and the static Pages site generated from `scripts/build_site.py` consistent with the same no-go status.

## Core values

**Maximize P(Win). Own the Outcome.** A well-supported negative decision that prevents a duplicate or unvalidated upload is preferable to a fabricated high score.
