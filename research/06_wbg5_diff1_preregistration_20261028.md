# WBG-5 / DIFF1 preregistration — locked 2026-10-28

**Hypothesis ID:** WBG-5 · **Method code:** DIFF1-SCARP-LOBE-1
**Status:** locked before implementation. No parameter is tuned on the holdout.

## Why this lane

The prompt requires 3–5 candidate geological hypotheses not yet tried, each naming the
specific layers, the physical signature, why it should find a fault missing from the
USGS/INGENIOUS catalogue, and how it differs from anything already implemented. The
repository's ranked list (`research/00_ranked_hypotheses.md`) already ranks DIFF1 as
candidate **#3, untested**. It is the highest-ranked *executable* candidate whose required
bytes are present in the pinned GitHub mirror (`data/external/lidar_scarp_features_u8.tif`),
because the 19-band `training_features.tif` stack is **not** obtainable in this sandbox
(DrivenData login wall) and the two higher-ranked lanes need it.

## Layers used (pinned 1 m-LiDAR-derived 100 m stack, SHA `d580bb8b…`)

`step_max` (scarp height), `lapneg_max` / `lappos_max` (concave/convex curvature lobes),
`cross_max` (cross-slope), `upface_max` / `downface_max` (scarp faces), `relief`, `valid`.

## Physical signature targeted

A diffusion-degraded normal-fault scarp retains **paired convex/concave curvature lobes
whose curvature amplitude scales with the scarp height**. This is a *shape* invariant, not
an amplitude: it survives where a fresh free face has been smoothed by diffusive
slope retreat, i.e. exactly where subaerial scarp mapping stops. The detector multiplies a
crest/base **symmetry** term (geometric mean / arithmetic mean of the two lobe amplitudes)
by a **height proxy** `sqrt(step) * sqrt(relief)` and a **face-dominance veto**.

## Why it should catch a catalogue-missing fault

Unmapped Great Basin faults are commonly older, lower-throw and more degraded than the
mapped Quaternary scarps, so their surface expression is a subtle diffusion profile rather
than a fresh escarpment. DIFF1 reads no catalogue and no previous prediction, so it is not
anchored to mapped traces.

## Named non-fault mimic (must be named, not ignored)

Pleistocene pluvial **shoreline benches / terrace risers** (paired curvature lobes with
height), and **road / canal embankments** across flat playas (high face dominance, low
symmetry). The veto and symmetry terms are the explicit discriminators; passing the holdout
is the test, not the naming.

## Difference from every reviewed implementation

| Existing lane | What it measures | DIFF1 difference |
|---|---|---|
| TIP1 | coherence gradient along strike (terminal damage) | DIFF1 uses **no coherence**; it uses curvature-lobe symmetry × height |
| H19-5 / D2.8 / B2 | catalogue-distance pruning of a prior dot field | DIFF1 reads **no catalogue** and emits from a morphology surface |
| S3DEP1 / WBG-S2 / WBG-4 | 19-band supervised HGB ensembles | DIFF1 uses **LiDAR-only**, unsupervised, fixed transforms |
| CLR1 / SWIR1 | radiometric / optical alteration | DIFF1 is purely geomorphic |

## Fixed arms (identical support, fixed 3-px minimum spacing)

1. **A — amplitude control:** `sqrt(step)·sqrt(relief)·veto·support` (no symmetry term).
2. **B — primary:** `balance·sqrt(step)·sqrt(relief)·veto·support`.
3. **C — asymmetry ablation:** `(1−balance)·sqrt(step)·sqrt(relief)·veto·support`.

Arm B is the fixed candidate; A and C are mechanism checks, never a post-hoc switch.

## Gates (identical to the shared template)

* **Leakage canary:** every raw and transformed channel tested alone in both polarities;
  `|AUC| > 0.90` stops the lane before scoring.
* **Surface novelty:** `|Spearman rho| <= 0.90` against every restored registry raster.
* **Holdout:** `SegmentHoldout(buffer_px=15)`, whole components hidden, visible faults
  pixel-exactly masked, pooled DTI α=0.2 β=0.8 300 m kernel, 10 km block-bootstrap 95% CI.
* **Promotion efficacy:** Arm B must exceed the pinned benchmark
  `HOLDOUT-DTI 0.166060` (`gems-segment-pooled-v1`, 60,988 withheld positives) with a
  strictly positive paired 95% CI against an independently replayed comparator. The
  benchmark's fold-aligned predictions are not published, so the comparator cannot be
  replayed; promotion therefore **fails closed** unless that changes.
* **Format:** one float32 band, EPSG:32611, `(3730, 3292)`, exact transform, no NaN/Inf in
  the footprint, strict whole-array finite `[0,1]` (zeros exterior) for the downloadable
  `-zeros.tif`.
* **Uniqueness:** final dots checked against all 179 restored rasters plus the retained
  spacing-5 calibration lattice; literal all-entry gate and competing-method gate reported
  separately. No relocation or threshold waiver.
* **Governance:** 3 experiments / 2 h cap; zero weekly slots; promotion reaches a separate
  selector only.

## Budget

Maximum 3 fixed arms or 2 hours. Submission slots used: **0**.
