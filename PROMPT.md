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

## Current artifact (2026-10-27)

**DOWNLOAD: research only. SUBMIT: NO.** WBG-2 is locally format-valid, but
fails the literal 3-pixel registry gate against the GEMSDOE24 lattice and lacks
an eligible holdout. There is no approved current TIFF. Its former model
projection and claimed interval are withdrawn. See `evidence/wbg2/run_card.json`
and run `python scripts/review_wbg2.py --check`. No new experiment or slot was
used in this review.

## Submission contract

- Single-band float32 GeoTIFF, EPSG:32611, 3730×3292, 100 m, sample geotransform.
- Values in [0, 1]. **Zeros-mode** (no NaN anywhere) is the upload file — the portal has rejected NaN with “Predicted values must be in range [0, 1]”.
- Unique name + short note.
- Homepage must make **OK TO SUBMIT / DO NOT SUBMIT** obvious. Validation is automatic; no human inspector.

## Nine focus sites

GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36.

Highest OWNER-REPORT among them: GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` = **0.2778**.

Question this repo must answer: why that file scored 0.2778, and whether a *unique* file can beat it.

## Core values

Maximize P(Win). Own the Outcome. A negative unique result that prevents a wasted slot is a win relative to a duplicate upload.
