# Starting point for every session

## Current status (2026-10-28)

0. **APPROVED FOR SUBMISSION: WBG-6** — `docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif`
   (SHA-256 `e9111de909c6c9669baf71321539e2b30e742334a7dbc66c8ea021d5539401e9`). Unique, format-valid,
   zero dots on the mapped catalogue, max surface |Spearman| 0.0148 versus all 118 scored rasters.
   **Estimated score 0.247 (MODEL-ESTIMATE, range 0.142–0.286; NULL-FLOOR 0.0425)** — not an organizer
   result, and *not* a top-20 contender (leader 0.4544). Read `evidence/wbg6_run_card.json`,
   `evidence/wbg6_submission_audit.json`, `evidence/wbg6_score_estimate.json` and
   `docs/wbg6/index.html` before changing anything.

0a. **NEW UNIQUE TIF GENERATED (research only, verdict: NEGATIVE):**
    `docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif`
    (SHA-256 `0806bb30573094bf889bcb55d15878cc66cdd3851f9b40119ab96d7716437815`).
    Format VALID, unique vs 6 checkable focus-site champions (max |ρ|=0.0551, max 3-px overlap=0.3932),
    HOLDOUT-DTI 0.4657 (CI [0.4563, 0.4748]) — **may be leaked** because dot placement used the full
    catalogue rather than per-fold visible faults. Per-fold re-evaluation required before slot promotion.
    **SUBMIT: NO** pending re-evaluation. See `docs/executive-summary-unique.html` and the run card
    `docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.run-card.json`.

1. **No other file is approved.** Older WBG-C1/TIP1/MVGZ/WBG-H1/WBG-2/S2/WBG-3/WBG-4 rasters are
   research-only (DO NOT SUBMIT). Literal registry-overlap STOP binds on those lanes.

2. Read `README.md` (including the archived standing prompt below), then `registry/run_card.json`,
   `registry/irregularities.json`, and the executive summary at `docs/executive-summary-unique.html`.
   The prompt is intent, not evidence. **No file is cleared to upload without a separate selector step.**

3. **Shared tools:** `vendor/gems57/` and `vendor/template57/prepare_data.py` are pinned unchanged owner-template
   files. Do not keep a private evaluator, writer, metric or novelty-threshold fork. Fix shared-template
   defects once and report them.

4. **Parallel-run protocol:**
   - LANE: stay in the declared method. If rank-correlation with any registry raster exceeds 0.90, or more
     than 70% of dots fall within 3 px of one registry raster's dots, log it as a duplicate and stop.
   - REUSE: use `scripts/evaluate_holdout.py` and `scripts/submission_writer.py`. Holdout = hide-and-recover:
     withhold whole fault segments with a buffer, derive catalogue features from visible faults only,
     mask visible faults pixel-exactly, score pooled DTI (α=0.2, β=0.8, 300 m triangular kernel).
   - LABEL: every number as HOLDOUT-DTI (evaluator version, n withheld positives, 95% CI) or
     ORGANIZER-CONFIRMED (submission-page receipt). A projection is never written as a score.
   - LEAKAGE CANARY: test each feature alone on the holdout. AUC > 0.90 means leakage until proven otherwise.
   - RUN CARD: end with one JSON card (hypothesis, mechanism, mimic, HOLDOUT-DTI + CI, registry correlation/
     overlap, raster SHA-256, validator output, submission name + ≤140 char note, verdict promote/negative).
   - BUDGET: stop after 3 experiments or 2 hours. Do not pick submissions; promotion is a separate selector step.

5. **No DrivenData auth:** cannot auto-download training data or submit. The submissions page redirects to login.
   Never request or store credentials.

## Focus sites (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36)

Best supplied historical claim: GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` = **0.2778**
(USER-REPORTED / NOT ORGANIZER-CONFIRMED). All nine historical files fail cross-site uniqueness and are
DO NOT SUBMIT. See `docs/executive-summary-unique.html` for the full table.

## Core values

Maximize P(Win). Own the Outcome. A negative unique result that prevents a wasted slot is a win relative
to a duplicate upload.
