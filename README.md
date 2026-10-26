# GEMS Fault-Discovery Research — Project Charter

> **Start every project session here.** Read this charter and [`docs/executive-summary.html`](docs/executive-summary.html) before proposing experiments, editing code, or producing a competition file. Update the evidence ledger when facts change. Do not silently upgrade a projection, owner-reported number, or internal holdout result into an organizer-confirmed score.

## Mission

Develop an auditable, scientifically defensible way to identify previously unmapped geological faults in the DOE GEMS Prize Challenge, and improve our probability of ranking highly without compromising scientific validity. Core values: **Maximize P(Win** (use evidence and explicit risk gates) and **Own the Outcome** (expose defects, distinguish evidence classes, and fix what we can).

## Non-negotiable operating rules

1. **No copied prediction rasters.** Previously published submissions may be studied for methods or used as collision references only. A prediction raster must be independently generated from the permitted data and pass byte, surface-correlation, and point-overlap checks against the complete available registry before it can be labelled unique.
2. **A download is not approval.** The page must show a fail-closed verdict at the top: `OK TO SUBMIT` only after format, novelty, leakage, and blocked holdout gates pass. Otherwise display `DO NOT SUBMIT`; never offer a misleading competition-ready download button.
3. **Use the shared template, not a private copy.** Reuse its cached features, `evaluate_holdout.py`, and `submission_writer.py`. The holdout is spatial hide-and-recover: withhold complete fault segments and a buffer; derive all catalogue features from visible faults only; pixel-exactly mask visible faults; evaluate pooled distance-weighted Tversky (alpha 0.2, beta 0.8, triangular 300 m kernel). Fix a shared-tool defect in the shared template and report it.
4. **Leakage canary.** Evaluate every feature on the holdout by itself. AUC above 0.90 is a leakage alarm until explained and independently ruled out.
5. **Evidence labels are mandatory.** Every candidate/model score must be labelled `HOLDOUT-DTI` (evaluator/version, withheld-positive count, 95% CI) or `ORGANIZER-CONFIRMED` (copied from that submission's receipt). Historical values must be explicitly marked user-/owner-reported; official public leaderboard snapshots must be explicitly labelled as such and not confused with a submission receipt. A projection is never a score.
6. **Registry novelty checks happen twice.** Check correlation and dot overlap before candidate placement and on final predictions. Stop if absolute raster rank-correlation exceeds 0.90 or more than 70% of candidate dots are within 3 pixels of any registry raster. Log the collision and stop; do not tune around an unknown failing registry silently.
7. **Bound the work.** Maximum three experiments or two hours per research cycle. Promotion to a real competition slot is a separate selector decision subject to the current weekly cap; do not spend a slot before the candidate beats the current holdout best under a paired, spatially blocked comparison.
8. **Reproducibility.** Preserve hypothesis, mechanism, a named non-fault mimic, source links, code/config version, random seeds, holdout evaluator and withheld-positive count, 95% CI, novelty audit, saved-file validator output, and SHA-256 in a machine-readable run card. Negative findings are valid deliverables.
9. **No invented scores, data, validation, or sources.** The competition portal and data downloads may require DrivenData login. Do not claim access, successful training, human inspection, leaderboard submission, or uniqueness without evidence.

## Submission target (official rules)

The competition asks for a single-band GeoTIFF predicting fault presence over the full region. The official problem description specifies UTM zone 11N / EPSG:32611, 100 m resolution, matching bounds/shape/geotransform, float32 probabilities in `[0,1]`, and null/NaN outside the training footprint. The published scorer is distance-weighted Tversky, with alpha 0.2, beta 0.8 and a triangular kernel of 300 m. Full detail and the source URL are in the executive summary. **This checkout currently contains no competition rasters, no cached feature stack, and no holdout or submission-writing tools, so it cannot honestly generate or validate a competition-ready TIF yet.**

## Session-start status (verified against this checkout)

- Repository initially contained only this README and the initial commit; no `data/`, `scripts/`, site, registry rasters, evaluator, or writer were present.
- No DrivenData authentication is available in this checkout. A login-gated competition download must not be described as completed.
- Therefore there is **no generated TIF**, no raster SHA-256, no holdout score/CI, and no independent uniqueness result. Do not upload a placeholder, all-zero raster, screenshot, or prior submission.
- The current public leaderboard and focus-site figures are recorded with their evidence class in [`docs/executive-summary.html`](docs/executive-summary.html). Leaderboard values are time-sensitive.

## Workflow

1. Run `python scripts/check_readiness.py` before analysis. It checks whether required data/tool files are placed; it does not establish pipeline or scientific readiness.
2. Stage authorized competition files in `data/` and the shared template tools in this checkout or an explicitly configured shared location. Verify checksums, grids, licences, and provenance.
3. Read and validate the source data. Preregister at most three candidate hypotheses. Do not develop a model on test labels.
4. Run the leakage canary, the segment-buffered holdout using the shared evaluator, and the full registry novelty checks. Compare paired fold results and confidence intervals to the current holdout best.
5. Only if all gates pass, invoke the shared writer, re-open the saved GeoTIFF and validate its saved bytes against the official sample grid, range, mask and uniqueness rules. Create a run card and explicitly state whether download/submission is permitted.
6. Refresh the source ledger and current leaderboard snapshot; keep dated evidence and clearly flag discrepancies.

## Current task outcome

The next useful work is data placement plus recovery/configuration of the intended shared template and registry—not an invented TIFF. The current site front page makes this state explicit and gives the user the official manual submission instructions. See [`docs/executive-summary.html`](docs/executive-summary.html), [`evidence/run-card.json`](evidence/run-card.json), and [`scripts/check_readiness.py`](scripts/check_readiness.py).
