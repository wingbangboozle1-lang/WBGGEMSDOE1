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

## Archived artifact (2026-10-28) — WBG-6 NOT APPROVED UNDER ACTIVE LITERAL GATE

- Archived WBG-6 `wbg6-qmh-kdisjoint-30000-20261028`: `docs/downloads/wbg6-qmh-kdisjoint-30000-20261028.tif`
  (+ identical one-member `.zip`), SHA-256 `e9111de909c6c9669baf71321539e2b30e742334a7dbc66c8ea021d5539401e9`. **Research download only; do not submit under the active literal registry gate.**
  30,000 dots, min separation 5 px, zero dots on the catalogue, distance-to-catalogue profile matched to
  the best reported file (median 20.1 px, p90 73.1 px). Format: 8/8 local checks plus the shared
  `gems57` gate. Uniqueness: no byte copy among 118 scored rasters, max surface |Spearman| 0.0148,
  overlap lift 1.47x over a density-matched independent field.
- Archived score estimate: `0.247` (MODEL-ESTIMATE, range 0.142–0.286; NULL-FLOOR 0.0425), not an observed score. The run card says the underlying holdout fails external validation; do not use this number as leaderboard prediction or submit justification.
- **Measured hidden-truth size K ≈ 12,395 cells**, calibrated on the one submission with a provably
  uniform layout (reported 0.0904 reproduced to 0.0002).
- Older rasters (WBG-C1, TIP1, MVGZ, WBG-H1, WBG-2, WBG-S2, WBG-3, WBG-4) remain **DO NOT SUBMIT**.
- **Do not** claim this file beats 0.2778 or reaches the leaderboard top. It is a legitimate unique
  entry with an honest, wide estimate; reaching 0.33–0.45 requires the login-gated 19-band stack.

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
