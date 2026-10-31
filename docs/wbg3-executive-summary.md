# WBG-3 Executive Summary — 2026-10-27 (this session)

## ⛔ SUBMIT DECISION: **DO NOT SUBMIT YET** — download for research: YES

**File:** `docs/downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif`
(+ identical one-member `.zip`)
**sha256:** `30901f894a84f6150a65a86e6556d3b4d3b3f5054dd4f8f3b597d754115447c1`
**Portal note (≤140 chars):** `WBG-3 supervised multi-physics detector, dotted clear2 37654, zeros no NaN`
**Archived format receipt (automated local checks only):** single-band float32, EPSG:32611,
3730×3292, 100 m, values in [0,1], **no NaN anywhere**, 37,654 positive pixels. Local range/finite checks passed for this historical file; portal acceptance and the cause of the reported “Predicted values must be in range [0, 1]” error remain unverified. Local checks are not organizer approval.

**Why not submit:** on the shared hide-and-recover evaluator the file's detector scored
**HOLDOUT-DTI 0.1382** (95% CI [0.1257, 0.1520], `gems-segment-pooled-v1`, 60,988 withheld
positives), which does **not** beat the current benchmark 0.1661 (GEMSDOE24 S3DEP1, same
evaluator; its fold masks are unpublished, so the paired replay the protocol requires is
unavailable and the gate fails closed). The calibrated **MODEL-ESTIMATE is 0.21
[0.17–0.26]**, below the champion's OWNER-REPORTED 0.2778. Spending a weekly slot on it
is a separate owner/selector decision; this project does not recommend it.
It **is** the best reproducible unique detector in this repo (Exp2 0.1320, B0 0.1039,
TIP1 0.0824 — same evaluator) and the designated file if a slot is spent anyway.

**Slots used: 0. Organizer-confirmed score: none (no file in this repo has one).**

## What file to download — the table

| File to download | Estimated score | Evidence class | Unique vs GEMSDOE24/25/27/28/30/31/32/33/36? | OK to submit? |
|---|---|---|---|---|
| **`wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif` (THIS session)** | **0.21 [0.17–0.26]** | MODEL-ESTIMATE (holdout × 2-anchor ratio; see run card) | **YES** — max 3-px dot overlap 45.1% (limit 70%), max \|ρ\| 0.036 (limit 0.90), per-raster gate PASS vs all 9 | **NO — not yet** (holdout gate vs 0.1661 not cleared). Designated file if owner spends a slot anyway |
| `wbg2-offcatalogue-density-36k-20261027.tif` (previous session) | ~~0.2824~~ **retracted** | Estimator invalid (IR-WBG2-EST) | Yes (max overlap 18.6%) | **NO** — scattered off-catalogue field; DTI vs champion field 0.067; no measured detector support |
| GEMSDOE32 `h33-h33-2-b2…-zeros` (champion, learning only) | 0.2778 | OWNER-REPORTED, no receipt | It *is* a focus site | NO — already submitted by its owner; copying it is a duplicate |
| GEMSDOE36 `anderson-geothermal-pinn-38854…` | 0.2750 | OWNER-REPORTED | focus site | NO — historical |
| GEMSDOE28 `h36-1-rung30…` | 0.2710 | OWNER-REPORTED | focus site | NO — historical |
| GEMSDOE31 `h27-4-solo-d28…` | 0.2708 | OWNER-REPORTED | focus site | NO — historical |
| GEMSDOE33 `h33d-analog-tip-stepover…` | 0.2632 | OWNER-REPORTED | focus site | NO — historical |
| GEMSDOE25 / GEMSDOE30 `dotted-h19-5-d2-8` / `d28-poisson300m` | 0.2600 / 0.2600 | OWNER-REPORTED | focus sites; **identical dot sets to each other** | NO — historical duplicates of each other |
| GEMSDOE24 `h25-1-dotted-h19-5-d1-5…` | 0.2477 | OWNER-REPORTED | focus site | NO — historical |
| GEMSDOE27 `topo-gap-closure…` | 0.2449 | OWNER-REPORTED | focus site | NO — historical |

Official leaderboard observed 2026-10-27 (https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/):
rank 1 = **0.4544**. The brief's 0.3195 / 0.4413 figures are superseded.

## Why 0.2778 won (measured this session, line by line)

1. The scored truth is **expert-mapped faults NOT in the USGS catalogue**
   (official problem page, fetched 2026-10-27:
   https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
   Dots that retrace known faults earn no credit and pay FP cost.
2. The champion is a **strict deletion subset** of the 44,090-dot D2.8 field:
   exactly 6,436 dots removed, **all within 200 m of the catalogue**, 0 added
   (`evidence/h33_b2_forensics.json`). The gain came from precision pruning, not new detection.
3. All nine focus artifacts are nested members of one dotted-ridge family
   (measured pairwise overlaps 98–100%); that is why none of them is a unique
   submission for us, and why regressing their scores on budget/proximity
   (the old WBG-2 estimator) fits lineage, not a transferable law.
4. Measured DTI of each artifact against the *catalogue* is **negatively**
   correlated with its reported live score (r = −0.92, `evidence/wbg3/nine_site_measured_metrics.json`):
   catalogue-tracing is anti-predictive for this leaderboard.

## What WBG-3 did differently

- Restored the official 19-band `training_features.tif` from the hash-pinned
  GitHub bridge (SHA-256 `4371c82e…23bc5` verified) — removing the "login-gated,
  absent" blocker recorded by earlier sessions — plus 3DEP LiDAR scarp
  (`d580bb8b…`), GeoDAWN radiometric (`c22420f7…`) and extension (`a35a9c6d…`) stacks.
- Trained a supervised HGB detector per holdout fold on **visible faults only**
  (42 static features; leakage canary max AUC 0.598 < 0.90), then added 10 local
  lineament features (contrast-8, structure-tensor line-likeness, Laplacians).
- Found and fixed a leakage bug (IR-WBG3-01): catalogue-distance features
  perfectly separated v1 training classes (fold AUC 0.500, degenerate surface);
  they were removed and the experiment rerun.
- Fixed the shared uniqueness gate, which combined worst-overlap and
  worst-enrichment from *different* rasters and false-STOPped every candidate
  (fixed per-raster, in `src/wbg2/uniqueness.py`, with tests).
- Emitted 37,654 dots, ≥3 px spacing, >2 px from the catalogue, zeros mode.

## Experiments (budget of 3, exhausted)

| Exp | Design | HOLDOUT-DTI (`gems-segment-pooled-v1`, 60,988 withheld, 95% CI) |
|---|---|---|
| 1 | Detector + catalogue-distance features | **Invalid** — IR-WBG3-01 leakage (AUC 0.500 degenerate); no valid measurement |
| 2 | Detector (42 features), dotted clear0/clear2, 37,654 | 0.1320 [0.1204, 0.1445] (clearance was a measured no-op: no top dot within 2 px of visible faults) |
| 3 | + 10 local lineament features, dotted clear2 | **0.1382 [0.1257, 0.1520]**; paired Δ vs Exp2 +0.0063 [−0.0006, +0.0129] (not strictly positive) |

Benchmarks, same evaluator: S3DEP1 0.1661 [0.1519, 0.1803] (uses 10 m DEM
features not obtainable in this sandbox; paired replay unavailable), B0 0.1039, TIP1 0.0824.

## How to submit (when a future file clears the gate)

1. Download the `.tif` (or the one-member `.zip`) from `docs/downloads/`.
2. DrivenData → competition 306 → New submission → upload the file.
3. Paste the portal note above (≤140 chars) → Create submission.
4. Record the organizer receipt; until then every number here is
   HOLDOUT-DTI or MODEL-ESTIMATE, never a score.

## Next steps / limitations

- Beat 0.1661 on a paired replay: add 10 m 3DEP DEM step features (the S3DEP1
  ingredient) — official free source USGS 3DEP
  (https://www.usgs.gov/3d-elevation-program); tile hosts are outside this
  sandbox's outbound allowlist, so this needs an unrestricted runner.
- Rank-2 hypothesis (upward-continuation structural index) is untested and all
  bytes are local — cheapest next lane.
- No organizer receipt exists for any historical score; all remain OWNER-REPORTED.
- Full run card: `evidence/wbg3/run_card.json`. Hypotheses: `research/04_wbg3_hypotheses_20261027.md`.
