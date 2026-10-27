# WBG-2 — executive summary

**Download for research:** `docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif` (or `wbg2-offcatalogue-density-36k-20261027.zip`). **Submit:** NO.

- Comparable HOLDOUT-DTI: **unavailable**. Validated leaderboard score estimate: **unavailable**.
- Former 0.2824 exploratory regression output: withdrawn; not a score and not for slot selection.
- Organizer-confirmed score: **none**.
- Unique vs the nine focus sites: **YES** — max 1.18× chance overlap, max |ρ| 0.009, 9/9 sites audited.
- Format: single-band float32, EPSG:32611, 3730×3292, values in [0,1], no NaN, 36,000 positive pixels.
- sha256: `f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3`

## What to download

| Site | File | OWNER-REPORTED historical value | Overlap with WBG-2 | Unique? |
|---|---|---|---|---|
| **WBG-2 research artifact** | `wbg2-offcatalogue-density-36k-20261027.tif` | unavailable | reference | limited audit only; DO NOT SUBMIT |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 (OWNER-REPORTED) | 1.18× chance | Unique |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 (OWNER-REPORTED) | 1.18× chance | Unique |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif` | 0.2710 (OWNER-REPORTED) | 1.12× chance | Unique |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif` | 0.2708 (OWNER-REPORTED) | 1.12× chance | Unique |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e-nanoutside.tif` | 0.2632 (OWNER-REPORTED) | 1.09× chance | Unique |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` | 0.2600 (OWNER-REPORTED) | 1.04× chance | Unique |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca-nanoutside.tif` | 0.2600 (OWNER-REPORTED) | 1.04× chance | Unique |
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif` | 0.2477 (OWNER-REPORTED) | 1.04× chance | Unique |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif` | 0.2449 (OWNER-REPORTED) | 1.08× chance | Unique |

## Why GEMSDOE32 is the highest supplied owner-reported result

Raster forensics show the B2 field is a strict deletion-only subset of D2.8: 6,436 dots removed, none added, with every removed pixel within 200 m of the mapped catalogue. This supports a precision-cleanup hypothesis. It does not prove the deleted dots were false positives or that this deletion caused the reported score, because hidden labels and an artifact-linked submission receipt are unavailable. The reported 0.2778 is OWNER-REPORTED, not ORGANIZER-CONFIRMED.

## Levers, measured

1. Catalogue exclusion — used by WBG-2 as a placement rule, not proven to improve hidden-fault detection.
2. Continuous-trace and fixed-budget comparisons remain exploratory; they do not authorize a submission without a prospective holdout.
3. Dot-budget effects are confounded with catalogue proximity in these related artifacts; do not treat the historical association as a causal score law.

## Negative results

- A detector built from official GeoDAWN radiometrics and 3DEP terrain descriptors scored AUC 0.549 against mapped faults and 0.0303 versus 0.0695 for random at the real budget. Rejected.
- The official 418 MB `training_features.tif` is absent (login-gated), so no feature-based model could be trained here.

## Irregularities

- All nine reported scores are third-party values with no receipt.
- GEMSDOE25 and GEMSDOE30 share an identical positive-pixel set.
- Leaderboard current value is unresolved: a prior dated repository observation is 0.4544; the current user brief reports 0.3195. Neither is refreshed by this build.
- External geophysical layers are peer re-distributions, not primary-download bytes; not used by WBG-2.
