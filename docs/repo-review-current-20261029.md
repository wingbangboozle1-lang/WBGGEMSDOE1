# Repository review — 29 October 2026

## Decision

**No new TIFF was generated or approved in this review. Do not submit any repository artifact.** The supplied parallel-run protocol refers to a single-method paragraph “below,” but no paragraph is present. The pre-existing lane registry reports the lane stopped. Choosing a different idea, modifying a stopped method, or creating a fresh raster would violate the stated lane/budget constraints. No submission slot was used.

This is a review of the checked-out repository, not an organizer score or a new experiment. Prior reports and measurements below retain their original evidence classes; none are silently upgraded.

## Reproducible findings

1. **Checkout:** branch `arena/7d1a82e4-wbggemsdoe1`; initial worktree clean; HEAD `0eb41440179a10890762241763cc91422779f9c0` (same as the checked-out `origin/main` snapshot).
2. **Primary competition rasters are absent:** `data/training_features.tif`, `data/labels.tif`, and `data/sample_submission.tif` are not present. Running `scripts/check_readiness.py` prints `BLOCKED_INPUTS` and exits 2; its expected SHA-256 pins are not evidence that the missing bytes were obtained. Some bridge rasters exist, but they do not supply these missing inputs.
3. **Template availability:** the shared `vendor/gems57` holdout/evaluator/writer files are present and hash-matched to the local expected pins recorded by readiness. That verifies local file identity, not competition-organizer provenance or scientific validity.
4. **Existing candidate evidence is disqualifying, not promotable.** The 28 October `WBGGEMSDOE1-blind-fault-adjacency-distance-decay` run card records a high *local* HOLDOUT-DTI, but explicitly flags leakage because dot placement used the full catalogue instead of each fold's visible catalogue, and its comparison covered only six champion rasters rather than the full registry. Its verdict is negative. It must not be presented as a valid high-scoring prediction or submitted.
5. **WBG-6 is also not cleared:** the 28 October review card records final-dot 3-pixel overlap `0.9967666667`, greater than the protocol's `0.70` STOP threshold. Historical approval is superseded. Do not download it for submission.
6. **Historical nine-site values:** the existing executive summary marks the listed values, including GEMSDOE32's `0.2778`, OWNER-REPORTED / UNVERIFIED and has no organizer receipts. The exact-subset forensic record supports a plausible catalogue-adjacent pruning explanation for B2, but it does not establish causation or hidden-label performance. No calibrated leaderboard-score estimate is justified.
7. **Tests:** the system Python initially lacked dependencies. A repository-local ignored virtual environment was created from `requirements-lock.txt`; `.venv/bin/python -m pytest -q` then passed all 232 tests (15 Rasterio pending-deprecation warnings). This does not substitute for the full CI workflow, which also checks lint, TIFF/ZIP validation, frozen receipts and rendered pages.
8. **Scope caveat:** the prior reports contain frozen registry scans and owner-mirror data claims with explicit limited scopes. They are not a complete current scan of every site/raster mentioned by the user. A positive byte/hash distinction is not proof of scientific uniqueness.

## Candidate-hypothesis gate

The repository's `docs/research/future-hypotheses-20261027.md` already documents four prospective, explicitly qualified ideas, including two based on local cached geophysical/terrain layers and two requiring external thermal data. The top-ranked potential-field/terrain lag idea is still reported as untested. This review does **not** promote it to viable or claim an expected DTI: (a) no user-assigned lane paragraph authorizes it, (b) the prior lane is stopped, and (c) the competition training/label/template inputs needed for correct fold-safe evaluation are absent. The report identifies the specific official USGS heat-flow release and DOE GDR INGENIOUS archive for the external-data ideas, but prior records say their data bytes/coverage were not validated here; neither is being represented as obtainable-and-ready for this experiment.

## Why no “best submission” or numeric projection is provided

The `0.2778` historical claim is not organizer-confirmed; the local high 0.4657 value is leakage-contaminated; and neither is an estimate for a new raster. HOLDOUT-DTI is not the hidden leaderboard metric. Reporting a guessed projected score or generating a novelty-evasive substitute would conflict with the protocol's evidence labels and STOP conditions. Consequently there is no TIFF that is OK to submit; existing research downloads must remain labeled **research only / do not submit**.

## Actions required before a future experiment

- Restore the exact competition `training_features.tif`, `labels.tif`, and `sample_submission.tif` from an authorized source, verify against trusted hashes and preserve provenance. Current competition portal downloads require authentication; this environment cannot impersonate an account or bypass that gate.
- Provide/establish a valid, single method paragraph and resolve the centrally shared literal registry stop policy. Do not work around registry overlap thresholds or target gaps in reference masks.
- Only then, preregister at most three experiments and run each leakage canary and hide/recover using whole fault segments, buffer withholding, fold-visible catalogue features, exact masking, pooled DTI with α=0.2/β=0.8/300 m triangular kernel, and confidence intervals.
- Compare candidate surfaces before placement and final dots against the complete in-scope authorized registry. A fail at either phase is a STOP, not a tuning invitation.
- Require efficacy versus the current same-evaluator control with a paired interval excluding zero, an exact-grid/range validator pass, and independent selector authorization before considering a weekly slot. Never infer an organizer score without a submission-page receipt.

## Verification record

- `python scripts/check_readiness.py`: exits 2 and records `BLOCKED_INPUTS` (expected, due to the missing three core TIFFs).
- `.venv/bin/python -m pytest -q`: **232 passed**, 15 Rasterio pending-deprecation warnings.
- `.venv/bin/python -m ruff check scripts src tests --select E9,F --exclude test_template_evaluator.py`: **passed** after removing an unused `dti_score_fast` import from `scripts/build_wbg7_submission.py`.
- No training, holdout experiment, feature extraction, TIFF generation, raster placement, upload, or selector step was performed.

## Run card (this review only)

```json
{
  "hypothesis": "No new geologic hypothesis tested; the active lane is unspecified and the inherited work is stopped.",
  "mechanism": "Repository and evidence audit only; no raster computation or placement.",
  "named_non_fault_process_that_could_mimic_it": "Not applicable: no geologic prediction was tested.",
  "holdout_dti": {"evidence_class": "NOT RUN", "evaluator_version": null, "withheld_positives": null, "dti": null, "ci95": null},
  "correlation_overlap_vs_registry": {"new_surface": "NOT MEASURED", "new_final_dots": "NOT GENERATED", "inherited_WBG6_max_3px_overlap": 0.9967666667, "threshold": 0.70, "verdict": "STOP; do not reuse WBG-6"},
  "raster_sha256": null,
  "validator_output": {"no_nan_inside_footprint": "NOT RUN", "values_in_0_1": "NOT RUN", "CRS_shape_transform_match": "NOT RUN"},
  "submission_name": null,
  "submission_note": "Review only; no raster generated. Do not submit inherited research artifacts.",
  "verdict": "negative"
}
```
