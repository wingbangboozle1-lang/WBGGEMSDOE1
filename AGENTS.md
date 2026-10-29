# Starting point for every session

0. **Current artifacts (read before any session work):**
   - **WBG-6 — NOT APPROVED (superseded 2026-10-28; withdrawn under the active 70% literal gate, archived 3-px overlap 99.6767%).** The earlier run card's approval text is provenance only. `docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif` (SHA-256 `e9111de909c6c9669baf71321539e2b30e742334a7dbc66c8ea021d5539401e9`). Unique, format-valid, zero dots on the mapped catalogue, max surface |Spearman| 0.0148 versus all 118 scored rasters. **Estimated score 0.247 (MODEL-ESTIMATE, range 0.142–0.286; NULL-FLOOR 0.0425)** — not an organizer result, and *not* a top-20 contender (public leaderboard leader 0.4544, retained observation). Read `evidence/wbg6_run_card.json`, `evidence/wbg6_submission_audit.json`, `evidence/wbg6_score_estimate.json` and `docs/wbg6/index.html` before changing anything.
   - **WBG-7 (this branch) — DOWNLOAD YES · SUBMIT NOT CLEARED.** `docs/downloads/wbg7-blind-tip-splay-relay-30000-20261028-zeros.tif` (SHA-256 `701ff7a4d916dd843da402ecf5f95126dc3ecfce0597ab71933ccacb16689e3a`). Unique, format-valid, values in [0,1] (no "[0,1]" portal error), 30,000 off-catalogue kernel-disjoint dots from blind trace-tip splay lobes blended with distance rings. Holdout-DTI 0.0149 (95% CI [0.01382, 0.01590]) is a catalogue-fault proxy below the 0.1661 same-evaluator best; no organizer score receipt exists. **Do not claim it beats 0.2778.** See `evidence/wbg7/run_card.json` and `docs/executive-summary-focus-sites.html`.
   - **WBGGEMSDOE1-blind-fault-adjacency-distance-decay (main lane) — research only, verdict NEGATIVE pending re-evaluation.** `docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif` (SHA-256 `0806bb30573094bf889bcb55d15878cc66cdd3851f9b40119ab96d7716437815`). Format VALID, unique vs checkable focus-site champions, but its HOLDEDTI 0.4657 (CI [0.4563, 0.4748]) **may be leaked** because dot placement used the full catalogue rather than per-fold visible faults; per-fold re-evaluation is required before any slot promotion. **SUBMIT: NO.** See `docs/executive-summary-unique.html`.
   - Older WBG-C1/TIP1/MVGZ/WBG-H1/WBG-2/S2/WBG-3/WBG-4 rasters remain research-only / DO NOT SUBMIT (WBG-2's literal registry STOP and WBG-S2's 99.5538% r13 / 100% WBG-C1 overlap are binding).

0b. **Four instrument defects are binding on future work:**
   (i) the shared hide-and-recover holdout does **not** rank real submissions (Spearman 0.144, p=0.12, n=118) — never report it as a score estimate; (ii) the literal ">70% of dots within 3 px" registry gate is degenerate against any dense raster (a 206,895-dot lattice captures 99.68% of any dot field) — use the density-matched overlap lift instead; (iii) 118 history files are only 22 families, so grouped cross-validation is mandatory for any fitted claim; (iv) reported scores differ by up to 0.086 for near-identical rasters, so the nine-site top six are statistically tied. Receipts: `evidence/holdout_proxy_portfolio.json`, `evidence/wbg6_submission_audit.json`, `evidence/wbg6_score_model.json`, `evidence/score_consistency.json`, `evidence/wbg6_irregularities.json`.

   Read `docs/review-20261028.md` and `docs/data/review-20261028.json` for the latest review. The Focus-9 synthetic generator is disabled after a binding STOP; its existing TIFF and receipts are frozen and must not be regenerated.

1. **No file is approved for submission (29 Oct 2026: SUBMIT NO).** WBG-2 was never cleared (literal registry STOP). The 29 Oct executive summary (`docs/executive-summary-20261029.html`) and `docs/data/nine_site_audit_20261029.json` are the current reference.

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
