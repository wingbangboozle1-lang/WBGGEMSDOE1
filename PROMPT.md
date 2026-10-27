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

No file is approved for submission.
- **WBG-3 (`SPI-PMR-WCS-1`, 1m-LiDAR-free & 10m-DEM-free):** `docs/downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.tif` (+ `.zip`, SHA-256 `f158a890dcb5f897ef35282ed05d291e54c4df9b83cf891870193d329b160fb4`). Passes 15/15 zeros-mode `[0, 1]` checks and competing-sparse uniqueness across all 207 sparse rasters (max 3-px overlap 59.38% <= 70%; 27.55% vs GEMSDOE32 B2; 43.40% vs WBG-S2; 38.96% vs WBG-3 EXP3DET), and beats 19-band control across 4/4 spatial folds (`HOLDOUT-DTI = 0.118180` on `gems-segment-pooled-v1`; `0.121862` on `gems57-pooled-hide-v2`), but hits literal un-amended registry overlap **99.9946%** vs `r13-lattice-s5` and **100%** vs `WBG-C1` and trails `S3DEP1` (`0.166060`). Verdict: `negative` (`DOWNLOAD: YES · SUBMIT: NO`). See `docs/wbg3/index.html`, `docs/wbg3/how-to-submit.html`, and `evidence/wbg3_spipmr/run_card.json`.
- **WBG-3 (`EXP3DET`, parallel supervised detector):** `docs/downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif` (`HOLDOUT-DTI 0.1382` `[0.1257, 0.1520]`, `MODEL-ESTIMATE` `0.21 [0.17-0.26]`, unique vs the nine focus sites, format-valid, verdict `negative` — does not beat the `0.1661` benchmark; see `docs/wbg3.html` and `evidence/wbg3/run_card.json`).
- **WBG-2 (revoked research download):** `docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif` (+ identical one-member ZIP).
  Its local all-finite format passes, but **99.8972%** of its existing dots overlap a registered
  lattice within 3 px (>70% STOP), and fold-safe replay measures `HOLDOUT-DTI = 0.000341` on `gems-segment-pooled-v1` (`0.097610` on `gems57-pooled-hide-v2`).
  See `docs/wbg2.html` and `evidence/wbg2/safety_audit_20261027.json`.

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
