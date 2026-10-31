> **31 Oct 2026 update:** start with [README §31 OCT START HERE](README.md) and **[docs/executive-summary-wbg8-20261031.html](docs/executive-summary-wbg8-20261031.html)**. **WBG-8 lane: DOWNLOAD YES · SUBMIT CLEARED for the owner's selector** (`evidence/wbg8/run_card.json`: `verdict: promote`, `ok_to_submit: true`). All other lanes' files remain DOWNLOAD research-only · SUBMIT NO under their own run cards (H2, fold-safe, WBG31-E1, RTP, focus, etc.).

# Starting point for every session

0-31oct. **31 Oct 2026: read `docs/executive-summary-h2-20261031.html` first.** DOWNLOAD YES (research) · SUBMIT NO. The literal 70% gate fails for every dot file (a random-dot control included). The holdout rewards catalogue proximity (exec summary §5), so it cannot test the B2 pruning mechanism.

0a. **Read `docs/owner-brief-20261029.md` at the start of every session** (owner standing requirements, official links). Then read `README.md`. The 29 Oct executive summary is `docs/executive-summary-20261029.html`; no file is cleared unless its run card shows `ok_to_submit: true`.

0. **Current artifacts (read before any session work):**
   - **WBG-8 (31 Oct 2026, this lane) — CLEARED CANDIDATE: `decision.ok_to_submit: true`, verdict `promote`.** `docs/downloads/wbg8-mridge-pois300-offcat3-37654-20261031-1cfe8cc8-zeros.tif` (+ one-TIFF `.zip`), SHA-256 `8adb3dbc89bd15e31312bf9e09df47a39447f4319a47141b15d7b18cfd9c5150`, 37,654 binary dots, zeros exterior (all-finite, values strictly in [0,1] — fixes the portal `[0,1]` error). Blind multi-layer ridge composite (RTP/TC Hessian ridges, geodetic strain, gravity edges, basement steps, topo fronts) + visible-catalogue ring/tip/relay priors; coverage-stratified Poisson-300 m; d≥3 px off-catalogue; seed 20261031. Gates: independent validator 15/15 format PASS (`evidence/wbg8/preflight.json`, `ok_to_submit: true`; writer receipt 10/10 hard + strict whole-array [0,1] PASS, 3 soft NaN-compat checks fail by design), canary PASS, registry uniqueness PASS (max literal 3-px overlap 0.659 non-degenerate / 0.469 same-budget; max |ρ| 0.040 vs 118 rasters) and unique vs all nine focus-site bests (max 0.347; the nine bests mutually overlap ≥0.867 — one nested family, `evidence/wbg8/focus9_family_matrix.json`: **do not re-submit them**). **MODEL-ESTIMATE 0.1393** (95% band −0.083–0.361; B2-parity reference 0.1532), **HOLDOUT-DTI 0.09438** (95% CI [0.08145, 0.10726], `gems-segment-pooled-v1`, n=60,988) — a diagnostic, not a forecast. Spending the weekly slot remains the owner's selector step; the repo never uploads. Budget 2/3 experiments, <2 h, 0 slots. Pages: `docs/executive-summary-wbg8-20261031.html`, `docs/how-to-submit-wbg8-20261031.html`.
   - **WBG-6 — NOT APPROVED (superseded 2026-10-28; withdrawn under the active 70% literal gate, archived 3-px overlap 99.6767%).** The earlier run card's approval text is provenance only. `docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif` (SHA-256 `e9111de909c6c9669baf71321539e2b30e742334a7dbc66c8ea021d5539401e9`). Unique, format-valid, zero dots on the mapped catalogue, max surface |Spearman| 0.0148 versus all 118 scored rasters. **Estimated score 0.247 (MODEL-ESTIMATE, range 0.142–0.286; NULL-FLOOR 0.0425)** — not an organizer result, and *not* a top-20 contender (public leaderboard leader 0.4544, retained observation). Read `evidence/wbg6_run_card.json`, `evidence/wbg6_submission_audit.json`, `evidence/wbg6_score_estimate.json` and `docs/wbg6/index.html` before changing anything.
   - **WBGGEMSDOE1 tip-continuation (29 Oct 2026, research only) — NEGATIVE, do not submit.** `docs/downloads/wbggemsdoe1-tipcont-catalogue-strike-20261029-1c5b292c-zeros.tif` (SHA-256 `9e5df9f7a02cad153b1d84c89cfc96a83bddea8b9752b3eca49210b98f814c32`), 18,611 dots. Catalogue-proxy HOLDOUT-DTI 0.000434 vs matched null 0.0240–0.0270; 35 GEMSDOE25-family rasters exceed the 70% 3 px gate. Page: `docs/tipcont-experiment-20261029.html`.
  - **WBG-7 (this branch) — DOWNLOAD YES · SUBMIT NOT CLEARED.** `docs/downloads/wbg7-blind-tip-splay-relay-30000-20261028-zeros.tif` (SHA-256 `701ff7a4d916dd843da402ecf5f95126dc3ecfce0597ab71933ccacb16689e3a`). Unique, format-valid, values in [0,1] (no "[0,1]" portal error), 30,000 off-catalogue kernel-disjoint dots from blind trace-tip splay lobes blended with distance rings. Holdout-DTI 0.0149 (95% CI [0.01382, 0.01590]) is a catalogue-fault proxy below the 0.1661 same-evaluator best; no organizer score receipt exists. **Do not claim it beats 0.2778.** See `evidence/wbg7/run_card.json` and `docs/executive-summary-focus-sites.html`.
   - **WBGGEMSDOE1-blind-fault-adjacency-distance-decay (main lane) — research only, verdict NEGATIVE — leakage CONFIRMED 2026-10-29 (per-fold visible-only HOLDOUT-DTI 0.0069, `evidence/per_fold_recheck_blind_adjacency.json`).** `docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif` (SHA-256 `0806bb30573094bf889bcb55d15878cc66cdd3851f9b40119ab96d7716437815`). Format VALID, unique vs checkable focus-site champions, but its HOLDEDTI 0.4657 (CI [0.4563, 0.4748]) **was leaked**: dot placement used the full catalogue; the per-fold re-evaluation is done and it fails. **SUBMIT: NO.** See `docs/executive-summary-unique.html`.
   - Older WBG-C1/TIP1/MVGZ/WBG-H1/WBG-2/S2/WBG-3/WBG-4 rasters remain research-only / DO NOT SUBMIT (WBG-2's literal registry STOP and WBG-S2's 99.5538% r13 / 100% WBG-C1 overlap are binding).

0b. **Four instrument defects are binding on future work:**
   (i) the shared hide-and-recover holdout does **not** rank real submissions (Spearman 0.144, p=0.12, n=118) — never report it as a score estimate; (ii) the literal ">70% of dots within 3 px" registry gate is degenerate against any dense raster (a 206,895-dot lattice captures 99.68% of any dot field) — use the density-matched overlap lift instead; (iii) 118 history files are only 22 families, so grouped cross-validation is mandatory for any fitted claim; (iv) reported scores differ by up to 0.086 for near-identical rasters, so the nine-site top six are statistically tied. Receipts: `evidence/holdout_proxy_portfolio.json`, `evidence/wbg6_submission_audit.json`, `evidence/wbg6_score_model.json`, `evidence/score_consistency.json`, `evidence/wbg6_irregularities.json`.

   Read `docs/review-20261028.md` and `docs/data/review-20261028.json` for the latest review. The Focus-9 synthetic generator is disabled after a binding STOP; its existing TIFF and receipts are frozen and must not be regenerated.

1. **Current submission decision (31 Oct 2026): WBG-8 is the single cleared candidate** (`evidence/wbg8/run_card.json`: `verdict: promote`, `decision.ok_to_submit: true`, `registry.passes_literal_uniqueness: true`, `submission_slots_used: 0`). Every older artifact and every other 31 Oct lane remains DO NOT SUBMIT per its own run card. The 31 Oct WBG-8 executive summary (`docs/executive-summary-wbg8-20261031.html`) and `docs/data/nine_site_audit_20261029.json` are the current references; the 29 Oct pages and other lanes' 31 Oct pages are provenance.

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
