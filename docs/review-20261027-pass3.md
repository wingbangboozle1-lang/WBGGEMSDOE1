# Repository review — follow-up pass 3 (2026-10-27)

## Decision

**No submission is approved. No new submission TIFF was generated. No experiment or weekly slot was used.** The referenced single-method assignment paragraph is absent, the existing scientific lanes remain stopped, and the latest candidate artifacts fail required scientific and/or literal-registry gates. Do not restart a lane or treat format validity as upload clearance.

## Work completed

- Restored `training_features.tif`, `labels.tif`, and `sample_submission.tif` through the repository's hash-pinned public GitHub owner mirror. All three expected SHA-256 hashes match. `scripts/prepare_data.py` built the shared feature cache and all 19 band hashes matched the pinned template.
- This verifies byte identity to the pinned owner mirror only; it does **not** authenticate the files as direct DrivenData downloads. Evidence: [`evidence/data_restore.json`](../evidence/data_restore.json) and [`evidence/shared_feature_cache.json`](../evidence/shared_feature_cache.json).
- Current `scripts/check_readiness.py` reports `BLOCKED_SCIENTIFIC` (not `BLOCKED_INPUTS`): the data are present, but data placement cannot clear the stopped lane, missing method assignment, uniqueness STOPs or promotion checks.
- Corrected WBG-3's generated forensics page. Exact decoded pixel relationships remain, but raster subtraction alone cannot identify hidden true/false positives or prove why the user-reported score changed. Removed an unsupported numerical inversion of hidden metric components and explicitly labeled the historical 0.2778 as **USER-REPORTED / NOT ORGANIZER-CONFIRMED**.
- Corrected the upload guide to say the cause of the reported “Predicted values must be in range [0, 1]” error is unverified. Local preflight verifies range and finite values; it cannot establish the organizer's rejection cause or acceptance.
- Existing prospective candidates are listed in [`docs/research/future-hypotheses-20261027.md`](research/future-hypotheses-20261027.md). They are proposals, not new results. Top-ranked cached-data candidate there is contour-relative, multi-lag magnetic texture autocorrelation (`rtp`, `tmi`, literal band 15). It has not been validated and is not authorized for implementation in a stopped/missing lane. The other two proposals require external temperature/well data whose exact download, coverage and provenance were not verified here.
- Linked sources for manual review remain in the hypothesis page and the generated forensic page. Directly re-fetching DrivenData, USGS or DOE pages was not possible in this review's network environment; this report makes no new claim that those pages or datasets were freshly checked.

## Verification

- Full tests: **194 passed**, with 15 existing `rasterio` pending-deprecation warnings.
- Static lint: `.venv/bin/ruff check scripts src tests --select E9,F --exclude test_template_evaluator.py` passed.
- Site generation: `scripts/build_site.py`, `scripts/build_readme.py`, and `scripts/stage_pages.py` completed successfully.
- Browser audit: 18 page/viewport checks passed on desktop and mobile, with no JavaScript errors or body overflow. Site filtering and downloaded TIFF SHA-256 identity checks passed.
- Fresh local validator on the existing WBG-C1 continuous research surface: one-band float32; EPSG:32611; shape 3730×3292; transform `[100, 0, 243350, 0, -100, 4508550]`; no NaN/Inf; values in `[0,1]`; exact pinned-grid match. It is not a final-dot TIFF and remains **DO NOT SUBMIT**.
- Fixed the integration validator's artifact lookup for the WBG-3 SPI-PMR research TIFF. It now matches `evidence/wbg3_spipmr/run_card.json` by exact raster SHA and reports all 15 local checks passed, `promotion_verdict=negative`, and `ok_to_submit=false`. `--require-submit-ready` exits 2 as intended. This does not alter the TIFF or its negative scientific/registry outcome.
- Full machine-readable session card: [`evidence/review_run_card_20261027_pass3.json`](../evidence/review_run_card_20261027_pass3.json). Review passes: [`evidence/review_passes_20261027_followup.json`](../evidence/review_passes_20261027_followup.json).

## Why no new candidate or TIFF was tested

The active prompt refers to a single assigned method paragraph but does not supply one. The WBG-C1 ledger is `negative_stopped`; other scientific lanes have their own frozen budgets/STOP results. Restoring the shared cache is an input-integrity improvement, not authorization to resume or tune any lane. The protocol requires an assigned lane and a surface-before-placement registry stop check. No score projection can substitute for holdout evidence, and no holdout evidence can substitute for an organizer receipt.

## Trusted source links for review

- [DrivenData competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS Great Basin heat-flow data release](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa)
- [DOE GDR INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391)
- [USGS blind geothermal systems study](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and)
