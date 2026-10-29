# Repository review — 29 October 2026

## Decision

**No TIFF is cleared for competition submission. Do not submit any current download.** This review generated no new raster, ran no geological experiment, and used no competition slot. That is the evidence-consistent outcome, not a claim that a higher score was achieved.

The standing parallel-run protocol declares a single method lane in a paragraph “below,” but no such assignment appears in the supplied prompt or `PROMPT.md`. It also requires stopping upon a registry duplicate, and the prior WBG-C1 lane is stopped. The checked-in WBG-C1 experiment record reports a negative efficacy outcome and a literal registry overlap STOP; it explicitly prohibits further placement or tuning in that lane. The most recent competitor candidate, the adjacency-distance TIFF, used the full catalogue for placement and checked only six champions, so its apparent holdout result is leakage-prone and its registry screen incomplete. Re-running it or treating its number as a validated score would violate the protocol. These are concrete stop conditions; no numerical leaderboard projection is warranted.

## Focus-9 decision table

The durable executive summary remains [`docs/executive-summary.html`](executive-summary.html), with the machine-readable table in [`docs/data/nine_site_executive_summary.json`](data/nine_site_executive_summary.json). Its nine supplied historical bests remain **OWNER-REPORTED / UNVERIFIED**, not organizer-confirmed receipts. The best supplied claim is GEMSDOE32 B2 at 0.2778; this number is not a current model result or an independently verified organizer score.

| Site | Supplied historical winner | Supplied value | Current action |
|---|---|---:|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5` | 0.2477 | Historical only; do not submit |
| GEMSDOE25 | `dotted-h19-5-d2-8` | 0.2600 | Historical only; do not submit |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5` | 0.2449 | Historical only; do not submit |
| GEMSDOE28 | `h36-1-rung30-blind-r1` | 0.2710 | Historical only; do not submit |
| GEMSDOE30 | `d28-poisson300m-offcat-44090` | 0.2600 | Decoded predictions duplicate GEMSDOE25 D2.8; do not submit |
| GEMSDOE31 | `h27-4-solo-d28` | 0.2708 | Historical only; do not submit |
| GEMSDOE32 | `h33-h33-2-b2` | **0.2778** | Highest supplied claim; unverified; do not submit |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30` | 0.2632 | Historical only; do not submit |
| GEMSDOE36 | `anderson-geothermal-pinn-38854` | 0.2750 | Historical only; do not submit |

The established explanation for B2 is explicitly only plausible: it is a pruned descendant of the D2.8 dot field, removing catalogue-near predictions. Under a precision-heavy sparse max-cover metric, reducing low-value positives could improve the score. But budget and catalogue-distance changed together, hidden labels are unavailable, and the cited score receipt is absent; this does not establish causality. Do not copy its dots into a new file.

## Ranked candidate hypotheses — proposal only, no experiments started

The prior review's four candidates satisfy the requested candidate format. Ranking is qualitative and not a forecast; no fresh slot or experiment follows until a lane is expressly assigned and the stop state is resolved by the project's governance, not by tuning around a duplicate.

| Rank | Layer(s) and signature | Blind-fault rationale | Named non-fault mimic | Difference/readiness | Expected DTI vs cost |
|---:|---|---|---|---|---|
| 1 | Cached RTP/TMI and depth-to-basement: lagged, orientation-conditioned magnetic texture anisotropy; detect cross-scale fabric discontinuity, not edge amplitude alone. | Basement fabric offsets might continue beneath areas without mapped surface traces. | Dike or pluton contact, remanence boundary, flight-line leveling seam. | Distinct operator from scalar magnetic edges and prior MTA texture proposal, but implementation exists in prior research queue; novelty is not global. Cached inputs theoretically suffice, currently absent. | Qualitative moderate / medium; not validated. |
| 2 | DEM + isostatic gravity + TMI: cross-scale displacement between independently derived gradient ridges. | Coincident ridge displacement may reveal buried structure attenuated at the surface. | Intrusion/lithologic contact, volcanic construction, gridding seam. | Cross-layer offset rather than a single ridge/edge. No verified local gravity inputs; requires official data and coverage validation. | Uncertain-moderate / medium-high. |
| 3 | Official well temperature/heat-flow observations plus magnetic/gravity gradients: spatially cross-fitted residual anomaly with sampling-density controls. | Persistent thermal residuals near structure may be consistent with fluid circulation away from catalogued traces. | Groundwater flow, survey/sample clustering, well-depth or measurement bias. | Observation-level residual design differs from existing raster-only signals. Requires a named official public source, primary download, and spatial/temporal provenance checks before viability. | Uncertain / high. |
| 4 | DOE INGENIOUS shallow-temperature observations plus DEM derivatives: cross-fitted terrain/season-adjusted temperature residual with spatial support. | A localized thermal residual could indicate fluid flow not represented by mapped faults. | Soil moisture, vegetation, insolation, seasonality, conductive lithology. | Point-data residual rather than another catalogue-derived raster. Archive coverage and usable raw data need verification before claiming viable. | Uncertain / high. |

These proposals do **not** override the explicit stop. No candidate was trained or tested on this review. No DTI is assigned to them.

## Verification — three passes

### Pass 1: inspect state and implement review

- Confirmed branch `arena/938e5ea1-wbggemsdoe1`; working tree was clean at start.
- Read the standing brief, current review, focus-site summary, protocol, candidate run card, shared evaluator/writer entrypoints, readiness report and irregularity ledger.
- Confirmed there is no fresh experiment permission: the lane text is missing, existing WBG-C1 is stopped, and the latest adjacency candidate admits full-catalogue placement and incomplete registry comparison.
- Added this dated review and linked it prominently from README; did not modify frozen rasters, experiment receipts, shared evaluator, or writer.

### Pass 2: test and edge-condition review

- Initial system Python lacked project dependencies. Created ignored `.venv` and installed declared project plus test dependencies from `pyproject.toml`; no dependency files were edited.
- `.venv/bin/pytest -q`: **232 passed, 15 Rasterio pending-deprecation warnings**.
- First CI-equivalent Ruff scan found a pre-existing unused `dti_score_fast` import in `scripts/build_wbg7_submission.py`; removed that dead import (no runtime behavior changed). Re-ran `.venv/bin/ruff check scripts src tests --select E9,F --exclude test_template_evaluator.py`: **passed**.
- First hosted CI attempt then failed the static report rebuild because the README generator template still emitted the stale 28 Oct review link. Updated the generator template, rebuilt site/readme/staged pages, and verified generated files are stable (`git diff` is limited to the intentional source-template change). Hosted checks have not yet been rerun on this amended commit.
- `.venv/bin/python scripts/validate_release.py`: **passed**, but its receipt validates the archived TIP1 release package and expressly records `ok_to_submit: false`; it is not current authorization.
- `.venv/bin/python scripts/check_readiness.py`: correctly exits non-zero with **BLOCKED_INPUTS**. `training_features.tif`, core `labels.tif`, `sample_submission.tif`, and cached bands are absent. Small bridge files do not substitute for the full input stack.
- Static audit confirms no project artifact has organizer receipt evidence linking its bytes to an official score; historical numbers remain user-reported.

### Pass 3: reconcile against the original request

- Nine sites are tabulated and each row clearly distinguishes historical supplied values from a submit recommendation.
- The table does not make an unsupported leaderboard estimate. No score is labeled HOLDOUT-DTI unless bound to evaluator, withheld-positive count and interval in its source record; historical values are not promoted to that class.
- A downloadable unique TIFF is **not** declared safe merely because it is byte-unique or passes GeoTIFF range/CRS checks. Existing downloads are research-only; in particular, the 0.4657 adjacency candidate is invalid for promotion due to leakage and incomplete registry coverage.
- The user's demand for a generated TIFF and higher score cannot be honestly satisfied under the mandatory stop rules. The correct explicit status is **DO NOT SUBMIT** until the stated evidence gaps are resolved.
- User-facing limitation: this checkout cannot retrieve the gated DrivenData inputs or private submission receipt. No credentials were requested. The current official leaderboard and remaining weekly allowance were not re-queried in this review.

## Remaining work / blockers

1. Provide an actual method-lane paragraph and decide through the separate selector process whether the stopped literal all-entry 70% gate remains authoritative. Never silently reinterpret it or optimize around a registry raster.
2. Restore and hash-check full feature, labels and sample submission inputs from an authenticated or independently provenance-verified source; the readiness check currently blocks.
3. Retire/revalidate the stopped WBG-C1 candidate only through a separately authorized process. For the adjacency-distance candidate, repeat the existing holdout correctly with catalogue features built from each fold's visible faults only; run every-feature-alone leakage canaries; perform pre-placement surface correlation and final-dot overlap against the complete registry. A previous contaminated score is not a usable comparator.
4. Establish a same-evaluator current-best baseline and paired uncertainty before any sparse emission. Do not compare unlike evaluator versions, representations, or split designs as a ranking.
5. Require all local file checks, full registry clearance, and a separate selector decision before considering a weekly submission slot; retrieve the account's remaining allowance and preserve the organizer receipt if a submission is later made.
6. Recheck official rules for outside-footprint nodata and competition upload acceptance. Local `[0,1]` validation does not explain or prove a resolution of the historical portal range error.
7. Refresh the 9-site GitHub snapshot inventory and public leaderboard feed before using old peer scores or file identities as current.

## Run card

```json
{
  "hypothesis": "No submission should be promoted until a non-leaking, same-instrument candidate beats the current holdout benchmark and clears the full registry gate.",
  "mechanism": "The active protocol forbids continuing a stopped lane; the newest candidate used full-catalogue placement and checked only a subset of registry champions, so its reported holdout cannot establish eligibility.",
  "named_non_fault_mimic": "For the adjacency-distance method, linear topographic/DEM scarp edges unrelated to faults can mimic the distance-from-catalogue response.",
  "holdout_dti": {"status": "not run this review", "evaluator_version": null, "withheld_positives": null, "95_percent_ci": null},
  "correlation_overlap_vs_registry": {"surface_before_placement": "not newly measured", "final_dots": "not newly measured for a new candidate; prior stopped artifacts remain stopped"},
  "raster_sha256": null,
  "validator_output": {"no_nan_inside_footprint": null, "values_in_0_1": null, "crs_shape_transform_match": null, "status": "no new raster generated; release validator only validated a historical research package and reported ok_to_submit=false"},
  "submission_name": null,
  "submission_note": "No current TIFF is approved; existing artifacts are research-only.",
  "verdict": "negative"
}
```
