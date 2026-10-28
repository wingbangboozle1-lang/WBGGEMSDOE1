# Repository review and decision — 28 October 2026

## Executive decision

**DO NOT SUBMIT any TIFF from the current checkout.** No new TIFF or experiment was produced in this review, and no competition slot was used. The available WBG-6 TIFF remains downloadable for research, but fails the explicit protocol's final-dot proximity rule: its archived registry audit reports maximum within-3-pixel overlap **0.9967667 (99.6767%)**, greater than the stated 70% stop threshold. Its reported 0.247 is a **MODEL-ESTIMATE**, not a HOLDOUT-DTI, not a leaderboard result and not an organizer-confirmed score. The earlier approval used a different density-adjusted overlap interpretation; that approval is explicitly superseded here.

The request to “keep iterating” does not permit bypassing the user's own lane and budget rules. The current evaluator readiness check returns `BLOCKED_INPUTS`; core competition `training_features.tif`, `labels.tif`, and `sample_submission.tif` are absent. There is no assigned single-method lane paragraph in the operating prompt. Thus no honest new hide-and-recover experiment, confidence interval, all-feature leakage screen, or fresh final-dot registry comparison can be run from this checkout. The base system Python initially lacked test dependencies; an ignored local `.venv` was created and the declared project/test dependencies were installed. The full suite then passed: **232 passed, 15 Rasterio pending-deprecation warnings**.

## Focus-9 historical winners

The durable site comparison is [Executive Summary: nine sites](executive-summary.html), backed by [`docs/data/nine_site_executive_summary.json`](data/nine_site_executive_summary.json) and the frozen audit. The reported score values are **OWNER-REPORTED / UNVERIFIED**, not organizer receipts. Each row identifies the highest historical file among the listed submissions, not a presently eligible candidate.

| Site | Highest supplied historical file | Reported value | Current disposition |
|---|---|---:|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5` | 0.2477 | Historical; do not submit |
| GEMSDOE25 | `dotted-h19-5-d2-8` | 0.2600 | Historical; do not submit |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5` | 0.2449 | Historical; do not submit |
| GEMSDOE28 | `h36-1-rung30-blind-r1` | 0.2710 | Historical; do not submit |
| GEMSDOE30 | `d28-poisson300m-offcat-44090` | 0.2600 | Decoded prediction identical to GEMSDOE25 D2.8; do not submit |
| GEMSDOE31 | `h27-4-solo-d28` | 0.2708 | Historical; do not submit |
| GEMSDOE32 | `h33-h33-2-b2` | **0.2778** | Top supplied claim, unverified; do not submit |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30` | 0.2632 | Historical; do not submit |
| GEMSDOE36 | `anderson-geothermal-pinn-38854` | 0.2750 | Historical; do not submit |

### GEMSDOE32 B2: what evidence supports

The frozen pixel forensics record says B2 is an exact subset of the D2.8 parent: it removes 6,436 dots, adds none, and every removed dot was within two pixels (200 m at 100 m/pixel) of the mapped public catalogue. Given the competition description that hidden test faults are absent from the public catalogue, removing catalogue-adjacent predictions plausibly reduces false-positive penalty while preserving candidate coverage. This is a plausible mechanism for the owner-reported change 0.2600 to 0.2778; it is **not causal proof** because hidden labels and an organizer receipt linking the exact file to that score are unavailable. The site table's scores are not comparable as fresh controlled experiments.

## Ranked hypotheses on record (not run in this session)

These are candidates recorded in the prior repo review, not claims of worldwide novelty. The present rules require selection of a lane, cached stack, feature-alone leakage canaries and the shared buffered segment holdout before a submission slot. None is validated now.

| Rank | Candidate / layers | Physical signature and rationale | Named non-fault mimic | Expected benefit / implementation cost |
|---:|---|---|---|---|
| 1 | Multiscale magnetic texture anisotropy: cached RTP, TMI and optionally depth-to-basement bands | Scale-persistent structure-tensor/autocorrelation anisotropy or breaks in magnetic fabric may indicate concealed basement displacement where no surface scarp is mapped | Dike/pluton contact, remanence boundary, flight-line leveling seam | Moderate qualitative potential; medium cost; related MTA lane exists and was negative on its recorded paired holdout, so a distinct preregistered variant is needed |
| 2 | Potential-field/terrain edge displacement: DEM, isostatic gravity, TMI | Cross-scale offset between gradient ridges may reveal buried displacement muted in topography | Intrusion, volcanic/lithologic boundary, survey seam | Uncertain-to-moderate potential; medium cost; data stack currently unavailable |
| 3 | Uncertainty-weighted well heat-flow residuals plus gravity/magnetic gradients | A spatially cross-fitted thermal residual associated with structure could indicate fluid pathways | Groundwater circulation, sparse/clustered well sampling, measurement bias | Potentially informative; high cost and requires external official observations |
| 4 | Cross-fitted shallow-temperature residuals from DOE INGENIOUS 2 m probes, adjusted for terrain/sampling | Local thermal anomaly may indicate fluid flow near concealed structures | Soil moisture, vegetation, insolation, season, conductive lithology | Uncertain; high cost, dataset archive coverage/bytes not verified locally |

Potential official sources identified in the existing research notes: [USGS Great Basin heat-flow maps and supporting data](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa) and [DOE GDR INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391). This review did not fetch or verify dataset bytes, footprint coverage, license, nor usability. Accordingly, these are not declared viable or ready-to-run. The cached feature stack itself is absent, so even candidates 1–2 cannot be honestly tested now.

## Three review passes

1. **Inventory and provenance:** read `PROMPT.md`, README, current readiness output, nine-site executive table, Focus-9 forensics, WBG-6 run card and registry audit. Found conflicting WBG-6 “approved” text in the landing page and README versus the run-card audit's recorded 99.6767% overlap and prior review's no-go status.
2. **Safety and implementation review:** applied the literal user-defined 70% overlap stop rule (rather than the earlier normalized-density exception), checked the WBG-6 score class, and ran `python scripts/check_readiness.py`. Result: `BLOCKED_INPUTS`; the three core training rasters are absent. Ran `python -m pytest -q`; it did not start because pytest is not installed in system Python. No full test claim is made.
3. **Requirement reconciliation and corrections:** changed the README and public landing page to put **DO NOT SUBMIT** first, put a status override on WBG-6's executive page, corrected the standing `PROMPT.md` artifact status, and linked this review. Retained old JSON receipts as frozen history rather than rewriting them. Confirmed this review generated no TIFF, ran no experiment, used no slot, and asserts no score prediction. Verification: `pytest -q` **232 passed** (15 Rasterio deprecation warnings); the CI Ruff syntax/undefined-name command (`ruff check scripts src tests --select E9,F --exclude test_template_evaluator.py`) **passed**; `git diff --check` passed. A broader default Ruff lint was also tried and reports pre-existing style/executable-bit issues across the repository; no mass formatting changes were made. The headless browser regression suite was rerun after correcting its download selector to target WBG-2 explicitly; all 22 checked page/viewport combinations passed, with download hashes verified.

## Irregularities and limitations

- WBG-6 was previously called “submittable” despite its recorded 99.6767% final-dot overlap against a registry raster under the prompt's literal rule. The approval depended on a separate density-normalized lift interpretation. Those rules conflict; this report follows the explicit 70% stop protocol and withdraws the approval.
- The site scores (including 0.2778) are owner-provided history without artifact-linked organizer receipts in the local evidence. They must not be relabeled organizer-confirmed.
- The repository contains historical pages with stale or mutually inconsistent approval copy and JSON run cards. New README/landing/page notices supersede, but older frozen evidence remains unmodified for audit trail.
- Full official input rasters and feature cache are absent; data restore requires authenticated competition access or verified mirror. Current checkout cannot produce fresh holdout results or train the reference model.
- Local format validation cannot guarantee portal acceptance. In particular, the known earlier form error (“Predicted values must be in range [0, 1]”) is not conclusively attributed or resolved for an approved current file.
- Scores 0.3195, 0.4413 and 0.4544 mentioned across prior user/repo text have differing timestamps/provenance; none is asserted here as the present official leaderboard value.

## Next work

1. Restore the full competition stack and cached features from an authenticated or provenance-verified source; run `scripts/check_readiness.py` until integrity checks pass.
2. Resolve and explicitly assign one method lane, including how the literal overlap rule is defined and which registry snapshot is authoritative. Do not silently replace the user's fixed 70% threshold.
3. Update tests tooling (`pytest` dependency environment) and run the full suite plus static checks.
4. Preregister no more than three candidate experiments. For each, test every feature alone for leakage, use the shared hide/recover whole-segment buffered evaluator and paired uncertainty, perform surface uniqueness before placement, and re-check final dots. Stop on any explicit lane gate failure.
5. Only consider a separate selector after a candidate genuinely beats the current same-evaluator holdout benchmark with adequate uncertainty and clears all gates. Do not use any slot until that independent decision.

## Run card

```json
{
  "hypothesis": "Review finding: WBG-6's density-adjusted approval is incompatible with the user's literal registry proximity stop rule.",
  "mechanism": "Its archived final-dot registry audit reports maximum 3-pixel overlap 0.9967667, above the 0.70 threshold; therefore stop, without selecting a submission.",
  "named_non_fault_mimic": "Not applicable: this was a repository governance review, not a geological predictor.",
  "holdout_dti": {"status": "not run", "evaluator_version": null, "withheld_positives": null, "95_percent_ci": null},
  "correlation_overlap_vs_registry": {"surface_before_placement": "not newly measured", "final_dots": {"value": 0.9967667, "basis": "archived WBG-6 audit; maximum 3-pixel registry overlap", "threshold": 0.70, "verdict": "stop"}},
  "raster_sha256": "e9111de909c6c9669baf71321539e2b30e742334a7dbc66c8ea021d5539401e9",
  "validator_output": {"artifact_validation": "historical local report only", "no_nan_inside_footprint": true, "values_in_0_1": true, "crs_shape_transform_match": true, "current_revalidation": false},
  "submission_name": "wbg6-qmh-kdisjoint-30000-20261028",
  "submission_note": "Research artifact only; registry gate failed; do not submit.",
  "verdict": "negative"
}
```
