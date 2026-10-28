# Session operating prompt (read at the start of every working session)

This file is the standing brief for WBGGEMSDOE1. The original user message is longer (many GEMSDOE URLs). The requirements that actually bind work are here.

## Goal

Place a **unique**, portal-valid GeoTIFF on the DrivenData DOE GEMS Prize (competition 306) path — but **do not spend a weekly slot** unless hide-and-recover DTI beats the current same-evaluator best.

Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
Problem: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
About: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
Reference: https://github.com/drivendataorg/gems-prize-reference-solution

## Parallel-run protocol

1. **LANE.** Stay in the declared method. If rank-correlation with any registry raster exceeds 0.90, or more than 70% of dots fall within 3 px of one registry raster, log a duplicate and stop.
2. **REUSE.** Use `scripts/evaluate_holdout.py` and `scripts/submission_writer.py`. Holdout = hide-and-recover: withhold whole fault segments with a buffer; catalogue-based features from visible faults only; mask visible faults pixel-exactly; pooled DTI (α=0.2, β=0.8, 300 m triangular kernel).
3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, n withheld positives, 95% CI) or ORGANIZER-CONFIRMED / OWNER-REPORT. A projection is never a score.
4. **LEAKAGE CANARY.** Test each feature alone on the holdout. AUC > 0.90 means leakage until proven otherwise.
5. **RUN CARD.** JSON: hypothesis; mechanism; named non-fault mimic; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator; submission name + ≤140 char note; verdict promote / negative.
6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick live slots.

## Current artifact (2026-10-28) — WBG-6 ON HOLD (NOT CLEARED TO SUBMIT)

- **WBG-6 `wbg6-qmh-kdisjoint-30000-20261028`** (zeros-outside: `docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif`;
  **recommended format** NaN-outside: `docs/downloads/wbg6-qmh-kdisjoint-30000-20261028-nan.tif`, same dots,
  built by `scripts/make_wbg6_nan_variant.py`, 13/13 checks PASS).
- **HOLD reason (measured, reproducible):** the literal 3-px registry gate (STOP above 70%) gives **99.68%** against the
  r13 lattice. A random in-footprint field of the same size gives **99.86%**. The gate therefore rejects every dotted
  in-footprint file while r13 is registered. The owner must choose the gate (see `docs/wbg6/gate-decision-20261028.html`).
- **Estimated score: unknown.** The earlier 0.247 MODEL-ESTIMATE is withdrawn as a decision number, because the repo's
  holdout failed external validation (Spearman 0.144, n=118).
- **Nine-site byte check** (`evidence/nine_sites_bytes_20261028.json`): 16–19% of each named file's dots lie within 3 px of a WBG-6 dot (17–19% in reverse).
  Within the ten named rows, the score ordering tracks the share of dots within 3 px of the mapped catalogue (ρ=−0.997, n=10,
  about seven distinct dot sets). This is descriptive, not validated.
- Older rasters (WBG-C1, TIP1, MVGZ, WBG-H1, WBG-2, WBG-S2, WBG-3, WBG-4) remain **DO NOT SUBMIT**.
- **Do not** claim WBG-6 beats 0.2778 or reaches the leaderboard top. It is not cleared.

## Submission contract

- Single-band float32 GeoTIFF, EPSG:32611, 3730×3292, 100 m, sample geotransform.
- Values in [0, 1]. The reported portal error was “Predicted values must be in range [0, 1]”; its cause is unverified. The local research file uses an all-finite, zero exterior convention, while official instructions say data outside the bounds should be null/NaN. Local validation does not establish organizer acceptance; no current file is approved.
- Unique name + short note.
- Homepage must make **OK TO SUBMIT / DO NOT SUBMIT** obvious. Validation is automatic; no human inspector.

## Nine focus sites

GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36.

Highest OWNER-REPORT among them: GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` = **0.2778**.

Question this repo must answer: why that file scored 0.2778, and whether a *unique* file can beat it.

## Core values

Maximize P(Win). Own the Outcome. A negative unique result that prevents a wasted slot is a win relative to a duplicate upload.
