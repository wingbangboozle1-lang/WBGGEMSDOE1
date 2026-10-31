# Repository review — 31 October 2026

## Decision in one sentence

**No current TIFF is cleared for a competition slot.** The repository does contain generated, downloadable TIFFs, but they are research artifacts with explicit negative gates. I did not create a new raster, run a geological experiment, choose a submission, or use a slot: the assigned method paragraph is missing, the active WBG-C1 surface lane has a recorded duplicate STOP, the required full training inputs are absent, and the protocol explicitly separates promotion from slot selection.

**Do not download any file from this repo and upload it as a competition submission.** The C1 file linked below is locally format-valid and can be downloaded for research, but it is a continuous research surface—not a promoted final candidate—and is marked **DOWNLOAD: research only · SUBMIT: NO**.

## Executive decision table: requested nine sites

The filenames and values below are the historical bests supplied in the project’s frozen nine-site audit. Their numeric scores are **OWNER-REPORTED / UNVERIFIED**, not `HOLDOUT-DTI` and not `ORGANIZER-CONFIRMED`: there are no artifact-linked submission-page receipts. The recorded comparisons are within the nine historical masks, not a complete audit of every competition submission. Every row is historical/already submitted and fails the active literal 70% 3-pixel uniqueness rule. No valid forecast is available for a new candidate.

| Site | Historical file (reference only; do not re-submit) | Historical value | New-submission leaderboard estimate | Unique vs the other eight under literal gate? | Decision |
|---|---|---:|---|---|---|
| GEMSDOE24 | [`gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | **OWNER-REPORTED 0.2477** | Unavailable | **No**; maximum 3 px overlap 100% | Do not submit; historical file |
| GEMSDOE25 | [`gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/e40b9b5e3871cb34d138f586bde97f5099658d01/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | **OWNER-REPORTED 0.2600** | Unavailable | **No**; maximum 3 px overlap 100% | Do not submit; historical file |
| GEMSDOE27 | [`gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/927322eadbde56be42ae129ccdfb9b37540d8e60/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | **OWNER-REPORTED 0.2449** | Unavailable | **No**; maximum 3 px overlap 98.02% | Do not submit; historical file |
| GEMSDOE28 | [`gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/e6321461066f89080e3b1bb670d3951ab20d3638/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | **OWNER-REPORTED 0.2710** | Unavailable | **No**; maximum 3 px overlap 100% | Do not submit; historical file |
| GEMSDOE30 | [`gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif`](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/760af3005dd40b9f36d8fef97d6dc384fd9f2a2f/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | **OWNER-REPORTED 0.2600** | Unavailable | **No**; decoded predictions duplicate the GEMSDOE25 D2.8 field | Do not submit; historical file |
| GEMSDOE31 | [`gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/597b04cd1afb65d1ebbe3e9417fd952be48e3d74/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | **OWNER-REPORTED 0.2708** | Unavailable | **No**; maximum 3 px overlap 100% | Do not submit; historical file |
| GEMSDOE32 | [`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/5fc7792c5887735ecd3aa9a612787da588a7bf2c/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | **OWNER-REPORTED 0.2778** | Unavailable | **No**; maximum 3 px overlap 100% | Highest supplied focus-site claim; do not re-submit |
| GEMSDOE33 | [`GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif`](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/f618cc54773bd9b4d6c2b3ebf78103a05cc10cb6/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | **OWNER-REPORTED 0.2632** | Unavailable | **No**; maximum 3 px overlap 99.71% | Do not submit; historical file |
| GEMSDOE36 | [`gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/c5a8ae7da3bd2fcff5aa5855afd44c7a3346c16/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | **OWNER-REPORTED 0.2750** | Unavailable | **No**; maximum 3 px overlap 97.58% | Do not submit; historical file |

**Interpretation:** GEMSDOE32 B2 is the highest *supplied* historical Focus-9 value; it is not an independently established current score. It is not appropriate to claim that any newly generated raster will beat it. `evidence/nine_site_audit.json` and `docs/data/nine_site_audit_20261029.json` retain the immutable artifact hashes, snapshots and measurements behind this table.

## Why the reported GEMSDOE32 B2 value could be high—and what is not established

The stored SHA-verified raster analysis says B2 has 37,654 dots and is a strict subset of the 44,090-dot D2.8 ancestor: **6,436 dots removed and zero added**. The deleted dots lie close to the mapped fault catalogue (3,891 within 1 pixel; all 6,436 within 2 pixels in the stored analysis). This pattern is consistent with a *catalogue-halo cleanup* rather than newly discovered fault segments.

A plausible metric mechanism is that removing predictions receiving little or no weighted true-positive credit reduces the false-positive contribution. The official problem description specifies distance-weighted Tversky scoring with α = 0.2, β = 0.8, and a 300 m triangular kernel. But a hidden fault can also lie near a mapped fault, so a fixed exclusion distance can delete true positives. The score receipt, hidden labels, and TP/FP/FN decomposition are not present; budget and pruning changed together. Therefore this is a **plausible explanation, not a causal finding**. Do not clone B2’s pixels or call it a general optimum.

Historical reported values D2.8 = 0.2600 and B2 = 0.2778 are **OWNER-REPORTED / UNVERIFIED**. New-candidate leaderboard estimates remain **unavailable**. The repository contains earlier `HOLDOUT-DTI` results, but the review audit found that the shared holdout was not reliably predictive of real submission ranking; a holdout result is not a leaderboard projection.

## Research ideas for a separately authorized future lane (not tested or viable today)

These are ranked proposals, not score projections. A method paragraph and explicit governance resolution are prerequisites; the stopped WBG-C1 lane must not be tuned around registry rasters. Specific operators below are described as not tested *in the exact paired form described* according to the stored research reviews—not as globally novel.

| Rank | Inputs and target signature | Why a hidden fault could respond | Non-fault mimic | Difference / cost / present viability |
|---:|---|---|---|---|
| 1 | Cached detrended elevation, isostatic gravity, and TMI: measure cross-scale, orientation-aware displacement between gradient-ridge maxima rather than merely summing edge strength. | A buried basement discontinuity may remain expressed in potential fields where topographic expression is muted. | Dike swarm, intrusive/lithologic contact, volcanic boundary, survey/gridding seam. | Paired terrain–potential-field lag, distinct as an operator from C1 curvature commutator and MTA texture anisotropy. Qualitative expected DTI upside: moderate but uncertain; implementation cost: medium. Requires restoring the hash-pinned 19-band input stack and a fresh novelty screen. This checkout lacks the full inputs; not viable to validate now. |
| 2 | Official Great Basin heat-flow well observations: spatially cross-fitted residuals from background conductive heat-flow expectations, corroborated by cached gravity/magnetic gradients; control for sampling density and well uncertainty. | Fluid-influenced thermal residuals may persist near a concealed conduit without a mapped surface break. | Groundwater flow, well-depth/thermal-conductivity bias, clustered drilling. | Observation-level thermal residual rather than another catalogue-proximity surface. Qualitative expected DTI upside: uncertain; implementation cost: high. Source cited in project research: [USGS Great Basin heat-flow maps and supporting data](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa). The source and input bytes/coverage are **not verified obtainable in this session**, so this remains nonviable pending acquisition and provenance review. |
| 3 | INGENIOUS 2 m temperature-probe measurements plus relief and geophysical gradients: cross-fitted spatial/seasonal/elevation residual, with support and sampling-density controls. | A reproducible shallow temperature anomaly might indicate fluid flow outside mapped fault traces. | Soil moisture, vegetation, insolation/shade, seasonality, conductive lithology, uneven sampling. | Point-observation residual, distinct from current raster-only derivatives. Qualitative expected DTI upside: uncertain; implementation cost: high. The repository cites [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391) and a public probe archive, but the data host/bytes, study-area coverage, usable metadata and alignment are **not checked in this session**. Not viable until obtained and audited. |
| 4 | USGS GeoDAWN K, Th, U and detrended elevation: locally normalized multiscale log-ratio/closure residual across terrain saddles, not raw counts or a single Th/K ratio. | A shallow alteration/weathering boundary associated with a concealed structure might cross a low-relief saddle without a catalogue trace. | Sediment sorting, soil moisture/attenuation, ash-rich deposits, playa redistribution, lithologic contact. | Distinct from existing raw ratios/products by the local ternary closure operator; ratios alone are already known and do not establish new information. Expected DTI upside low-to-moderate and uncertain; medium-high cost. Official source cited in repo: [USGS GeoDAWN, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). Input bytes, quantization semantics and footprint were not independently confirmed here; not viable now. |

### Evidence-gated experiment plan if governance is resolved

1. Restore the missing feature/label/submission rasters only from an access-authorized source; verify their bytes and provenance. Current readiness reports `BLOCKED_INPUTS`.
2. Reconfirm the shared evaluator/writer pins and full registry inventory; do not create a private metric or a competing-raster exception.
3. Obtain a written single-method lane assignment and resolve the literal 70% rule conflict centrally. No inference or “hole avoidance” is permitted.
4. Preregister one top hypothesis with fixed parameters, a named mimic, and a paired control. Use visible-fault-only catalogue-derived features, whole-segment buffered holdout, exact visible-pixel mask, pooled DTI with α = 0.2, β = 0.8 and the official 300 m kernel; test every feature alone. AUC > 0.90 is a leakage alarm.
5. Test surface correlation before placement and final dot overlap against the complete authorized registry. Stop on a literal duplicate; do not relocate dots to evade a gate.
6. Require a same-evaluator current-best paired interval, untouched confirmation and all local format/uniqueness checks before a separate selector considers a slot. The selector and any portal receipt are outside this review.

No new data source is asserted available solely because a link appears in a research note. No external source was freshly fetched from this restricted environment on this review date.

## Current downloadable research artifact (not approved)

- File: [`wbg-c1-commutator-research-surface-20261026-acea88448272.tif`](downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif)
- SHA-256: `8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875`
- Status: **DOWNLOAD: YES (research only) · SUBMIT: NO**. It is a continuous research surface, not a final dotted or selector-promoted submission.
- Recorded science result: **HOLDOUT-DTI 0.014045**, evaluator `gems57-pooled-hide-v2`, 11,330 withheld positive pixels, 95% CI [0.011831, 0.016396]. Paired with its control: **HOLDOUT-DTI delta −0.000101**, same evaluator and withheld positives, 95% CI [−0.000232, +0.000030]; no improvement established. These are frozen prior measurements, not rerun in this review.
- Recorded surface comparison: maximum |Spearman ρ| = 0.152331; maximum forward 3 px overlap = 99.8724%; checked inventory was 360 unique rasters from nine frozen snapshots and was explicitly incomplete relative to the full owner-listed sites. The literal overlap gate failed. No final dots were generated after the surface STOP.
- Local validation was rerun in this review: one float32 band, EPSG:32611, 3,730 × 3,292, transform matching the local sample-submission mirror, all array values finite and in [0,1] (observed min 0, max 0.880929), no NaN in the footprint. The validator explicitly classifies this as a local preflight—not organizer acceptance.
- No authenticated organizer receipt, complete all-site uniqueness proof, current account allowance, or approved lane is present.

## Three-pass review and verification

### Pass 1 — inspect repo and frozen evidence

- Read `AGENTS.md`, `PROMPT.md`, `README.md`, the owner brief, the 29 Oct repository review, the Focus-9 audit, WBG-C1 run card, shared-template pins, and the WBG-32 forensics.
- Confirmed the working branch is `arena/bd5d22f3-wbggemsdoe1`; the starting tree was clean and at the supplied base commit.
- Confirmed the README already contains the user's standing prompt, the Arena Core Values, and the instruction to read the prompt each session. This review adds a current-status summary/link rather than duplicating the whole prompt again.
- Recorded irreconcilable provenance caveats: the user's current leaderboard figure **0.3195** is not accompanied by a receipt; the project feed's last dated official public-page observation is **0.4544 observed 2026-10-27**, refreshed in the feed on 2026-10-28 and explicitly marked retained/not refreshed. Neither should be represented as a verified 2026-10-31 current leaderboard value. No DrivenData login or submission receipt is available here.

### Pass 2 — run code and artifact checks

- Installed exact versions from `requirements-lock.txt` in ignored `.venv` after the system Python correctly rejected global package installation under PEP 668.
- `.venv/bin/python -m pytest -q`: **261 passed**, 15 Rasterio `PendingDeprecationWarning`s, in 41.79 seconds.
- `.venv/bin/ruff check scripts src tests --select E9,F --exclude test_template_evaluator.py`: **passed**.
- `.venv/bin/python -m compileall -q scripts src tests`: **passed**.
- Re-ran `scripts/validate_submission.py` on the C1 TIFF and ZIP: all local format/range checks passed; both point back to the stored negative promotion verdict. This is not an upload acceptance test.
- `scripts/validate_release.py`: passed the historical TIP1 package’s integrity checks while reporting `ok_to_submit: false`. It validates a frozen archive, not permission to submit.
- `scripts/check_readiness.py`: correctly returned `BLOCKED_INPUTS` (exit 2). The required full `training_features.tif`, core `labels.tif`, `sample_submission.tif`, and feature cache are absent. The small bridge files do not satisfy those inputs. Shared-template file pins match; organizer provenance is not authenticated.

### Pass 3 — reconcile with the full user request and governance

- Verified the Focus-9 table’s exact nine rows and historical values from the stored machine-readable audit; all are labeled owner-reported and none has a receipt. No historical raster is recommended for re-submission.
- Confirmed the run card's negative verdict: low recorded holdout relative to its control, a literal pre-placement overlap STOP, incomplete nine-snapshot registry coverage, no final dot clearance, no assigned lane, and no slot approval.
- Did not run a new geological experiment because doing so would conflict with the missing lane assignment, the active STOP, and the explicit instruction not to pick a submission or spend a slot.
- Did not create a new TIFF. The already-generated download linked above satisfies the requirement that there be an easily downloadable **research** TIFF, but does not satisfy the user's desired outcome of a new high-scoring, submit-cleared file. This distinction is intentional and visible.
- Did not freshly fetch DrivenData, USGS, GDR, or the public leaderboard: outbound access is restricted to GitHub, codeload, npm and PyPI hosts. Official source links are retained for later manual review; the fresh-access limitation is not hidden.

## Limitations, irregularities, and next work

1. **No submission recommendation or score forecast.** There is no candidate that beats the relevant same-evaluator control and clears the active literal registry gate. The score `0.2778` and the user's `0.3195` are unreceipted owner-provided claims; the latest stored public leaderboard observation is stale, not current.
2. **Missing data/authentication.** Full competition training inputs and the 19-band cached feature stack are absent locally. Hash-matching mirrors establish byte integrity against repository pins, not organizer provenance. DrivenData submission/account access is unavailable; no credentials were requested.
3. **Governance conflict.** The prompt references one method paragraph but does not supply it. The previous C1 method has stopped. The literal 70% overlap test is known to behave pathologically against a dense registered lattice; this is not permission to waive it, replace it silently, or optimize around its occupied cells.
4. **Incomplete uniqueness scope.** The frozen C1 check covered 360 raster files across nine historical snapshots—not every user-listed site, private file, or later release. Do not state global uniqueness.
5. **No external-data validation.** Heat-flow and INGENIOUS links in the research notes are candidates for future source checks, not evidence that their data are currently downloadable, spatially adequate, or aligned.
6. **Review outcome is negative by design.** Resolving these constraints requires data authorization/provenance, a written lane and policy decision, full registry refresh, a held-out candidate that beats a paired current comparator, and a separate selector. Do not upload a research-only artifact.

## Run card (this review; no new experiment)

```json
{
  "hypothesis": "Do not promote a candidate until a newly authorized, non-leaking candidate beats a same-evaluator baseline and clears the full registry rules.",
  "mechanism": "The method lane is unspecified and the previous WBG-C1 surface already triggered the literal registry overlap STOP; further placement or tuning is not authorized. The current downloadable C1 file is retained for research and does not qualify for promotion.",
  "named_non_fault_mimic": "Oblique saline-clay basin fill or lithologic contacts and shared inversion/interpolation artifacts can produce the WBG-C1 curvature signature without a geothermal fault.",
  "holdout_dti": {
    "status": "NOT RUN IN THIS REVIEW; frozen prior measurement only",
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": "gems57-pooled-hide-v2",
    "dti": 0.01404466519440323,
    "withheld_positive_pixels": 11330,
    "95_percent_ci": [0.01183137469362976, 0.01639563940835171],
    "paired_control_delta": -0.00010087213406997399,
    "paired_delta_95_percent_ci": [-0.00023195991478308924, 0.00003045384564565667],
    "source": "registry/run_card.json"
  },
  "correlation_overlap_vs_registry": {
    "status": "frozen pre-placement surface check; registry coverage incomplete",
    "max_abs_spearman_rho": 0.15233060870020235,
    "max_forward_3px_overlap": 0.9987243421716145,
    "checked_unique_rasters": 360,
    "snapshots": 9,
    "literal_gate": "FAIL: overlap exceeds 70%; stop recorded",
    "final_dots": "NOT GENERATED after STOP"
  },
  "raster_sha256": "8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875",
  "validator_output": {
    "source": "fresh local scripts/validate_submission.py run on 2026-10-31",
    "single_band_float32": true,
    "no_nan_inside_footprint": true,
    "values_in_0_1": true,
    "crs_shape_transform_match": true,
    "crs": "EPSG:32611",
    "shape": [3730, 3292],
    "transform_matches_local_sample_submission_mirror": true,
    "local_format_checks": "PASS; not organizer acceptance",
    "promotion": "FAIL / negative"
  },
  "submission_name": "wbg-c1-commutator-research-surface-20261026-acea88448272",
  "submission_note": "WBG-C1 curvature non-coaxiality; spatial OOF research surface; no dot placement; NOT approved for submission.",
  "verdict": "negative"
}
```

## Sources for review

- Official [competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem/metric/submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [about page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), and [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- Official domain-specific source links in the preserved research register: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [USGS Great Basin heat-flow data](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa), and [DOE GDR INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391).
- Local evidence and review records: [`evidence/nine_site_audit.json`](../evidence/nine_site_audit.json), [`docs/data/nine_site_audit_20261029.json`](data/nine_site_audit_20261029.json), [`evidence/h33_b2_forensics.json`](../evidence/h33_b2_forensics.json), [`registry/run_card.json`](../registry/run_card.json), [`registry/data_manifest.json`](../registry/data_manifest.json), [`evidence/review_passes.json`](../evidence/review_passes.json), [`scripts/check_readiness.py`](../scripts/check_readiness.py).
