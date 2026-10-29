# Starting point for every session

0. **Current artifacts (read before any session work):**
   - **WBG-6 — RESEARCH DOWNLOAD ONLY · DO NOT SUBMIT.** `docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif` (SHA-256 `e9111de909c6c9669baf71321539e2b30e742334a7dbc66c8ea021d5539401e9`). Its archived registry audit reports 99.6767% of final dots within 3 px of a registry raster, exceeding the active 70% STOP threshold. Its 0.247 value is a MODEL-ESTIMATE with an externally invalidated leaderboard proxy; not a HOLDOUT-DTI or organizer result. Earlier density-adjusted approval is superseded. See the corrected `docs/wbg6/index.html` and `docs/wbg6/how-to-submit.html`, and retain the frozen receipts as provenance only.
   - **WBG-7 (this branch) — DOWNLOAD FOR RESEARCH · SUBMIT NO.** `docs/downloads/wbg7-blind-tip-splay-relay-30000-20261028-zeros.tif` (SHA-256 `701ff7a4d916dd843da402ecf5f95126dc3ecfce0597ab71933ccacb16689e3a`). Local format/range checks pass; values are in [0,1]. Its recorded HOLDOUT-DTI is 0.0149 (95% CI [0.01382, 0.01590], `gems-segment-pooled-v1`, n=60,988), below the recorded 0.1661 same-evaluator result; not a leaderboard estimate. Its run card compares 2 focus-site champions and its companion audit checks 6/9; full current registry uniqueness is not established. Do not claim it beats 0.2778 or upload it. See `evidence/wbg7/run_card.json` and `docs/executive-summary-focus-sites.html`.
   - **WBGGEMSDOE1-blind-fault-adjacency-distance-decay (main lane) — research only, verdict NEGATIVE pending re-evaluation.** `docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif` (SHA-256 `0806bb30573094bf889bcb55d15878cc66cdd3851f9b40119ab96d7716437815`). Format VALID, unique vs checkable focus-site champions, but its HOLDEDTI 0.4657 (CI [0.4563, 0.4748]) **may be leaked** because dot placement used the full catalogue rather than per-fold visible faults; per-fold re-evaluation is required before any slot promotion. **SUBMIT: NO.** See `docs/executive-summary-unique.html`.
   - Older WBG-C1/TIP1/MVGZ/WBG-H1/WBG-2/S2/WBG-3/WBG-4 rasters remain research-only / DO NOT SUBMIT (WBG-2's literal registry STOP and WBG-S2's 99.5538% r13 / 100% WBG-C1 overlap are binding).

0b. **Four instrument defects are binding on future work:**
   (i) the shared hide-and-recover holdout does **not** rank real submissions (Spearman 0.144, p=0.12, n=118) — never report it as a score estimate; (ii) the user's literal ">70% of dots within 3 px" registry rule is binding: stop on a violation and do not substitute density-adjusted overlap lift; (iii) 118 history files are only 22 families, so grouped cross-validation is mandatory for any fitted claim; (iv) reported scores differ by up to 0.086 for near-identical rasters, so the nine-site top six are statistically tied. Receipts: `evidence/holdout_proxy_portfolio.json`, `evidence/wbg6_submission_audit.json`, `evidence/wbg6_score_model.json`, `evidence/score_consistency.json`, `evidence/wbg6_irregularities.json`.

   Read `docs/repo-review-20261029.md` and `evidence/repo_review_20261029.json` for the latest review. The Focus-9 synthetic generator is disabled after a binding STOP; its existing TIFF and receipts are frozen and must not be regenerated.

1. **No file is approved for submission except via its own verified run card.** The previously promoted WBG-2 file

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
