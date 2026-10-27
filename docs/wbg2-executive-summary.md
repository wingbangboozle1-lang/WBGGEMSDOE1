# WBG-2 — executive summary

**Download:** `docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif` (or `wbg2-offcatalogue-density-36k-20261027.zip`). **Submit:** YES.

- Estimated score: **0.2824** (MODEL-ESTIMATE, 95% 0.2795–0.2853, R² 0.988, n=9).
- Organizer-confirmed score: **none**.
- Unique vs the nine focus sites: **YES** — max 1.18× chance overlap, max |ρ| 0.009, 9/9 sites audited.
- Format: single-band float32, EPSG:32611, 3730×3292, values in [0,1], no NaN, 36,000 positive pixels.
- sha256: `f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3`

## What to download

| Site | File | Reported score | Overlap with WBG-2 | Unique? |
|---|---|---|---|---|
| **WBG-2 (this)** | `wbg2-offcatalogue-density-36k-20261027.tif` | **0.2824** (estimate) | reference | — |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 | 1.18× chance | Unique |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | 1.18× chance | Unique |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif` | 0.2710 | 1.12× chance | Unique |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif` | 0.2708 | 1.12× chance | Unique |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e-nanoutside.tif` | 0.2632 | 1.09× chance | Unique |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` | 0.2600 | 1.04× chance | Unique |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca-nanoutside.tif` | 0.2600 | 1.04× chance | Unique |
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif` | 0.2477 | 1.04× chance | Unique |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif` | 0.2449 | 1.08× chance | Unique |

## Why 0.2778 won

All nine artifacts are binary dot fields (only 0.0 and 1.0). Their reported score is perfectly rank-ordered by how far their dots sit from the mapped catalogue: 0.190→0.2477, 0.187→0.2600, 0.136→0.2632, 0.109→0.2708, 0.050→0.2750, 0.049→0.2778. The GEMSDOE32 winner is documented in its own audit as the 0.2708 base with every dot within 200 m of the catalogue deleted. The gain came from deletion, not detection.

## Levers, measured

1. Exclude the catalogue — proven, used by WBG-2 at 400 m.
2. Continuous traces — only with the true strike (0.936) vs scattered (0.140) vs guessed strike (0.090). WBG-2 scatters.
3. Smaller budget at fixed hits — monotone gain (0.132→0.221 from 20k→2.5k pixels), but confounded with lever 1 across the nine sites (r=0.75).

## Negative results

- A detector built from official GeoDAWN radiometrics and 3DEP terrain descriptors scored AUC 0.549 against mapped faults and 0.0303 versus 0.0695 for random at the real budget. Rejected.
- The official 418 MB `training_features.tif` is absent (login-gated), so no feature-based model could be trained here.

## Irregularities

- All nine reported scores are third-party values with no receipt.
- GEMSDOE25 and GEMSDOE30 share an identical positive-pixel set.
- Public leaderboard observed 2026-10-27 at 0.4544 (rank 1), superseding 0.4437/0.4413.
- External geophysical layers are peer re-distributions, not primary-download bytes; not used by WBG-2.
