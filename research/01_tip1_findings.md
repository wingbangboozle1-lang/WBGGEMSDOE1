# TIP1 findings — frozen 2026-10-26

## Executive decision

**DOWNLOAD FOR RESEARCH/AUDIT: YES · SUBMIT: NO · VERDICT: `negative`.**

The uniquely named, strict all-finite GeoTIFF is:

[`gemsdoe1-tip1-directional-tip-gradient-20261026-9a4b9b4bc8cd-zeros.tif`](../docs/downloads/gemsdoe1-tip1-directional-tip-gradient-20261026-9a4b9b4bc8cd-zeros.tif)

- SHA-256: `148718d31ea75cfa3b7c643dfa25643cb0353483b2fa0e2696a62af2a107dca8`
- Content ID: `9a4b9b4bc8cd`
- 37,722 binary dots; one float32 band; EPSG:32611; shape `3730 × 3292`; exact template transform
- Complete validator: **PASS**, including strict whole-array finite `[0,1]`
- Submission note (102 characters): `TIP1 directional LiDAR coherence-tip gradient | format-valid research; DO NOT SUBMIT | id 9a4b9b4bc8cd`

Formatting readiness is not scientific authorization. No weekly slot was used.

## Frozen three-arm result

Every number below is **HOLDOUT-DTI**, evaluator `gems-segment-pooled-v1`, 60,988 withheld-positive pixels, with a 95% 10 km spatial-block bootstrap CI. Whole connected fault components were hidden with a 1.5 km buffer, visible faults were pixel-exactly masked, and the pooled metric used α=0.2, β=0.8 and a 300 m triangular kernel.

| Arm | Fixed role | HOLDOUT-DTI | 95% CI | Decision |
|---|---|---:|---:|---|
| **B** | preregistered TIP1 primary: max ±2/±4 strike-following coherence contrast | **0.082434** | `[0.072872, 0.091733]` | Primary remains fixed; fails efficacy gate |
| A | coherence-amplitude control | 0.085478 | `[0.075594, 0.095604]` | Control only; cannot replace B |
| C | geometric-mean scale-persistence ablation | 0.082549 | `[0.073559, 0.091368]` | Ablation only; cannot replace B |

Arm B is far below the pinned S3DEP1 benchmark **HOLDOUT-DTI 0.166060**, evaluator `gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.151858, 0.180339]`. In addition, S3DEP1's fold-aligned predictions and 10 km block components were not published, so the required paired replay was impossible and promotion failed closed. This comparison is local validation, not a leaderboard estimate.

## Integrity gates

- **Leakage canary:** PASS. All 29 raw layers/transforms/arm surfaces were tested alone in both AUC polarities; none exceeded `0.90`.
- **Surface novelty:** PASS for all arms against 179 restored unique rasters. Maximum absolute rank correlation: A `0.501735`, B `0.482280`, C `0.468474` (limit `0.90`).
- **Competing-raster final novelty:** Arm B's largest 3-pixel overlap excluding the synthetic lattice was `0.643948`, below `0.70`; maximum final rank statistic was `0.506292`.
- **Literal all-entry final novelty:** FAIL. The retained spacing-5 calibration lattice covered `99.9523%` of candidate dots within 3 pixels. It is retained deliberately, so no relocation or exception was applied.
- **Format:** PASS. The portal-risk correction is the `-zeros.tif` all-finite exterior; no stored cell is outside `[0,1]`.
- **Governance:** three fixed experiments, 132.4 seconds, zero slot use, no rerun, no post-hoc arm switch.

## Scientific interpretation

TIP1 is genuinely distinct from H33-B2: it computes a directional derivative of LiDAR coherence along each cell's local axial strike and never reads a catalogue tip or previous prediction. The low holdout result indicates that terminal coherence collapse at 200–400 m offsets is too sparse and/or too confounded by road ends, terrace ends, fan channels and landslide toes to recover the withheld mapped segments at the fixed budget. The amplitude control performing slightly better does not authorize switching arms; it weakens the tip-gradient mechanism.

No evidence supports a claim that TIP1 would exceed the unverified owner-reported `0.2778`. Local HOLDOUT-DTI and a live organizer value are not interchangeable.

## Reproduction

```bash
python scripts/restore_inputs.py
python scripts/restore_registry.py
PYTHONPATH=src python scripts/run_tip1_lane.py --verify-recorded
```

The lane refuses a scientific rerun once its frozen receipt exists. See [`evidence/tip1_run_card_20261026.json`](../evidence/tip1_run_card_20261026.json) for every fold, CI, registry row, input/code hash, validator check and stop reason.
