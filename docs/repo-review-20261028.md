# Repository review — 28 October 2026

## Decision

**No current TIFF is approved for competition submission.** This review made no geological experiment, generated no TIFF, selected no weekly slot, and submitted nothing. The user-requested aim of beating GEMSDOE32's reported `0.2778` cannot be established from the local holdout records; no leaderboard score estimate is defensible.

The freshest run in this checkout is the WBG-4 (CSJF-1) negative result. It records `HOLDOUT-DTI 0.165424` on `gems-segment-pooled-v1` (60,988 withheld positives; 95% CI `[0.152338, 0.178931]`) and an untouched `HOLDOUT-DTI 0.103660` on `gems57-pooled-hide-v2-confirm-seed77` (11,326 withheld positives; 95% CI `[0.086121, 0.120534]`). These are holdout metrics, **not** competition scores. Its final candidate is blocked by literal registry overlap: 99.6983% against `r13-lattice-s5` and 100% against WBG-C1, exceeding the repository's 70% stop rule. See [WBG-4 run card](../evidence/wbg4/run_card.json) and [executive summary](wbg4/index.html).

Existing TIFF links are research artifacts and are **not safe to submit**. For example, the WBG-4 TIFF's local raster-format checks are recorded in its validation evidence, but the duplicate/overlap stop is decisive. Do not interpret a successful download or format validator as scientific eligibility, uniqueness, or organizer acceptance.

## Focus-9 historical summary

The figures below are the user-supplied/frozen historical record, not fresh leaderboard checks. Scores are labeled **OWNER-REPORTED / UNVERIFIED**, not ORGANIZER-CONFIRMED; no linked organizer receipt for each exact TIFF is present in this repository. The prior immutable audit also marks each candidate non-unique under its 70% cross-site overlap rule. Its snapshots are historical and the upstream heads changed, so this is not a current global uniqueness guarantee.

| Site | Highest recorded historical file (short name) | OWNER-REPORTED score | Eligibility now |
|---|---|---:|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5` | 0.2477 | No — historical, frozen audit fails uniqueness |
| GEMSDOE25 | `dotted-h19-5-d2-8` | 0.2600 | No — historical, frozen audit fails uniqueness |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5` | 0.2449 | No — historical, frozen audit fails uniqueness |
| GEMSDOE28 | `h36-1-rung30-blind-r1` | 0.2710 | No — historical, frozen audit fails uniqueness |
| GEMSDOE30 | `d28-poisson300m-offcat-44090` | 0.2600 | No — historical, decoded prediction is identical to GEMSDOE25 D2.8 |
| GEMSDOE31 | `h27-4-solo-d28` | 0.2708 | No — historical, frozen audit fails uniqueness |
| GEMSDOE32 | `h33-h33-2-b2` | **0.2778** | No — highest supplied claim; not organizer-confirmed; historical/duplicate-risk |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30` | 0.2632 | No — historical, frozen audit fails uniqueness |
| GEMSDOE36 | `anderson-geothermal-pinn-38854` | 0.2750 | No — historical, frozen audit fails uniqueness |

### What can be inferred about GEMSDOE32 B2

The preserved pixel audit supports a *raster lineage* interpretation: the B2 mask is a thinned subset of the earlier dense D2.8 mask. If its supplied score is accurate, pruning redundant or low-value predictions could improve a distance-weighted precision/recall metric by lowering false-positive cost while retaining useful coverage. This is a plausible metric mechanism, not a demonstrated cause: hidden test labels and an artifact-linked organizer receipt are unavailable. No score for a new candidate can be projected from that history. See [the source-linked Focus-9 forensic analysis](research/why-02778.html) and [the frozen audit JSON](data/nine-site-audit.json).

## Ranked, untested hypotheses

These are candidate scientific questions, not implementation permission or numeric score forecasts. Specific forms below are not claimed novel across all external GEMSDOE repos.

| Rank | Candidate and cached layers | Target signature and missing-catalogue rationale | Non-fault mimic | Relative expected DTI / cost |
|---:|---|---|---|---|
| 1 | **Multiscale magnetic-texture anisotropy:** cached RTP band 2, TMI band 14, optionally depth-to-basement band 15; compare autocorrelation/structure-tensor anisotropy parallel and normal to local basement-depth contours at fixed 300/800 m scales. | Covered displacement may interrupt coherent basement magnetic fabric when no surface scarp was mapped. | Dike/pluton contacts, remanence changes, flight-line leveling. | Moderate qualitative potential; medium cost. |
| 2 | **Potential-field/terrain edge displacement:** detrended elevation band 12, isostatic gravity band 13, TMI band 14; measure scale-dependent offset/orientation among gradient maxima. | Buried structure may remain in potential fields while surface relief is muted. | Intrusions, volcanic contacts, survey seams. | Uncertain-to-moderate; medium cost. |
| 3 | **Uncertainty-aware well heat-flow residuals:** requires official USGS Great Basin well residual data plus cached gravity/magnetic gradients; account for well sampling and uncertainty, with spatially independent well splits. | Fluid-related heat transport may spatially align with a buried structure missed by surface mapping. | Groundwater, measurement bias, clustered drilling. | Potentially useful but high cost and not currently data-ready. Official source: [USGS heat-flow maps and supporting data](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa), DOI 10.5066/P9BZPVUC. Dataset bytes/coverage not verified in this checkout. |
| 4 | **Cross-fitted shallow-temperature residuals:** DOE INGENIOUS 2 m probe observations and relief; adjust for season/elevation and sampling density before comparing with structural gradients. | A shallow thermal anomaly may indicate fluid flow near a concealed boundary. | Soil moisture, vegetation, sun/shade, season, conductive lithology. | Uncertain and high cost; not data-ready here. Official source: [DOE GDR INGENIOUS](https://gdr.openei.org/submissions/1391), which links the dataset; archive bytes/coverage not verified locally. |

The complete hypothesis context is in [future hypotheses](research/future-hypotheses-20261027.md). **The top candidate was not run.** The parallel-run instructions require one assigned lane paragraph, but none is specified in the request. The active lane is stopped, and the current checkout also lacks the three full core input rasters (`training_features.tif`, `labels.tif`, `sample_submission.tif`) and 19-band cache. Starting a new method, building a private replacement, or probing alternate registry gaps would violate the lane/reuse/stop conditions. `scripts/check_readiness.py` currently reports `BLOCKED_INPUTS` (exit 2), not a scientific green light.

## Current checkout limitations and irregularities

- Full competition rasters/cache are absent. `data/bridge/` contains only small bridge fixtures and does not replace them.
- The code can run local format/registry checks when required references are present, but local checks cannot prove the DrivenData portal will accept a file.
- Historical scores in user materials (including 0.2778, 0.3195, and 0.4413) conflict in scope and provenance. They are not all comparable measurements; the current report does not treat them as current official leaderboard values.
- Repo pages contain older status snapshots. The machine-readable readiness check in this checkout is the fresh status check for this review.
- This environment did not authenticate to DrivenData and cannot retrieve private competition data or hidden labels.

## Three review passes

1. **Inventory:** read `PROMPT.md`, repository instructions, README, current run cards, Focus-9 audit and candidate research. Confirmed the available TIFFs/run cards and that no new file should be generated under a stopped/unspecified lane.
2. **Verification:** installed the pinned test dependencies in the ignored local `.venv`; ran tests, Ruff's CI static subset and `git diff --check`. Results: **216 tests passed**, **15 rasterio pending-deprecation warnings**, Ruff passed, whitespace check passed. Ran readiness separately: **BLOCKED_INPUTS** because core competition rasters/cache are absent.
3. **Requirement reconciliation:** checked whether an output could be called unique, score-winning, portal-valid, or submit-ready. Answer: no. Existing WBG-4 and WBG-3 artifacts have frozen negative registry decisions; the nine-site audit is stale as a global uniqueness census; no current score estimate or organizer receipt exists. Kept the outcome negative rather than issuing a misleading download-as-approved signal.

No submission slot was used. No fresh holdout value or registry statistic was measured in this review; all numbers cited as holdout values above are explicitly from the frozen WBG-4 run card.

## Next actions

1. Resolve the missing single-method lane assignment and registry policy centrally; do not restart a stopped lane or tune around registry overlap.
2. Restore official or hash-pinned full competition inputs and shared feature cache using the repository's documented shared workflow; distinguish owner-mirror integrity from organizer-origin authentication.
3. Refresh current focus-site raster artifacts and a current comparison benchmark from immutable upstream refs; archive receipts and decoded-pixel overlap results. Do not use stale nine-site uniqueness as current clearance.
4. Only after authorization, preregister one candidate, run its feature-alone leakage canaries, then shared whole-segment buffered holdout against the matched current comparator. Promote only if its paired improvement is supported and all registry gates pass; keep slot selection separate.
5. Before any future upload, re-run the automated single-band/float32/CRS/shape/transform/range/footprint validator on the exact TIFF and test the portal's [submission requirements](https://www.drivendata.org/competitions/306/competition-doe-gems/). Make no causal score claim without the organizer receipt.
