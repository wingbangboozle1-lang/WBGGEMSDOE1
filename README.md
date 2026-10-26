# GEMS fault-prediction research and submission gate

> **Read this brief before every project task.** The project is to build an auditable, scientifically defensible workflow for discovering unmapped faults associated with geothermal resources and producing a valid GEMS Prize Challenge GeoTIFF. Maximize the probability of a genuine, generalizable result; own the outcome, report failures, and never present a projection or an unverified external result as a measured score.

## Executive status

**STOP — there is no submission-ready TIFF in this repository. Do not download or submit a file from this project yet.** This checkout contains no competition data, cached feature stack, trained model, holdout evaluator, submission writer, registry rasters, or historical TIFFs. Accordingly, no local estimate, holdout score, raster uniqueness test, or scientifically grounded submission can be produced here. A made-up/synthetic raster would not satisfy the challenge or the user's uniqueness and high-score gates.

The official competition specification requires one float32 GeoTIFF in EPSG:32611, at 100 m resolution and the training-data bounds, with one band of predictions in [0, 1]; outside the data bounds must be null/NaN. The official metric is distance-weighted Tversky with alpha 0.2, beta 0.8 and a 300 m triangular distance kernel. See the [official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login required).

## Non-negotiable workflow

1. **No invented numbers.** Each reported score must be explicitly tagged `HOLDOUT-DTI` (include evaluator version, withheld-positive count, and 95% CI) or `ORGANIZER-CONFIRMED` (copied from a submission-page receipt). Public leaderboard values, third-party pages, user-pasted results, and model projections are not either of those. Label them as unverified context or omit them; never call a projection a score.
2. **A distinct scientific lane.** Before experimentation, state one mechanism and stay within it. Compare the final raster with every available registry raster before placement and after final dot selection; if rank correlation exceeds 0.90 or more than 70% of dots lie within 3 px of one registry raster's dots, record a duplicate and stop.
3. **Use shared assets, not a private reimplementation.** Reuse the template feature cache, `evaluate_holdout.py`, and `submission_writer.py` when they are actually present. Hold out whole fault segments with a buffer; derive catalogue features only from visible faults; mask visible faults pixel-exactly; evaluate pooled DTI with the official alpha/beta/kernel. Fix shared tools at their source, not in an untracked fork.
4. **Leakage canary.** Score every feature alone on the holdout before trusting it. AUC above 0.90 is a leakage warning until independently explained.
5. **Hard budget.** At most 3 experiments or 2 hours, whichever comes first. Do not select/promote a candidate or use a weekly submission slot until the separate selector step confirms it beats the current holdout best and respects the weekly cap.
6. **Submission gate.** Do not label anything “OK to submit” until the actual TIF passes structural checks (CRS, dimensions, transform, one float32 band), finite/range checks ([0, 1] inside the footprint; no NaN inside), footprint/nodata checks, and duplicate checks. Only then provide the actual downloadable file, a unique name, and a short note.
7. **Auditability.** Keep evidence, source links, assumptions, failed tests, hashes, validator output, and an experiment/run card. Distinguish official evidence from site-reported claims. No human inspection is a substitute for programmatic validation, but expert review of possible geological discoveries is outside the scope of raster validation.

## Current state and next actions

- At initial review this checkout contained only the README. This pass adds a static executive-summary site, a GeoTIFF format validator, and synthetic-fixture tests; no competition data, prediction model, holdout evaluator, submission writer, registry raster or historical TIFF was added. No previous-session implementation or local evidence is present in this checkout.
- The repository's existing GitHub Pages source is the legacy `main` branch root. The landing page at [`index.html`](index.html) forwards visitors to the executive summary in `docs/`; the static site is intended to appear at [the project Pages URL](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/). The Pages settings API could not be changed by this session, so the project keeps the already-configured legacy publisher instead of claiming an Actions-based deployment.
- The linked DrivenData data page requires sign-in. No competition files or credentials are present here, so the data cannot be acquired autonomously in this environment. Do not claim otherwise or bypass the access control. The official [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) also instructs users to obtain challenge data from DrivenData and place it in its data directory.
- The official [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) confirms the target is faults; the initial prize test includes expert-labelled faults missing from the existing public USGS fault database. It describes GeoDAWN magnetic/radiometric data and other features, plus USGS and INGENIOUS fault labels. It does **not** establish that any particular previously reported submission is scientifically correct or unique.
- Historical submission names/scores quoted in the project request are leads, not verified receipts. In particular, a score and filename suffix alone do not reveal how a raster was constructed or why it performed. Obtain the actual raster, run metadata, evaluator version, and receipt before drawing that conclusion.
- **Next:** place legally obtained competition files in a local ignored `data/` directory; inspect the official template/cache and shared evaluator/writer; recover the registry rasters and candidate TIFFs needed for duplicate testing; then run the documented leakage-controlled holdout. The exact data-page access and the missing shared workflow are blockers, not tasks that can be solved by guessing.

## Candidate hypotheses for later testing (not results or score estimates)

These are shortlist ideas based only on the official description of the available layers. The repository is empty, so “distinct from this repo” means no method is implemented here; this does not prove novelty relative to all historical GEMSDOE sites. No candidate is currently viable for submission until the holdout and leakage tests can run.

| Rank (priority, not a score) | Hypothesis and layers | Physical signature / missing-fault mechanism | Relation to existing approaches; cost |
|---|---|---|---|
| 1 | **Paired magnetic-contact and source-depth discontinuity:** total magnetic intensity (TMI), horizontal/vertical TMI derivatives, and top-of-crustal magnetic source-depth estimate. | Test whether persistent, scale-consistent edge ridges and a source-depth step co-locate; a buried structural boundary may offset or juxtapose magnetic sources even where no mapped surface trace exists. | Composite cross-layer edge agreement, not a raw catalogue buffer. Medium cost; all listed layers are described by DrivenData. Must be compared to the historical h33/edge-style submissions and the feature-alone leakage canary. |
| 2 | **Strain-tensor orientation/coherence breaks:** dilatation, shear strain rate, and second invariant of strain rate. | A narrow discontinuity in strain orientation or invariant could indicate a mechanically localized zone not yet catalogued. | Tensor-derived local discontinuity statistic rather than simply high strain magnitude. Medium cost; listed in the official feature description. Spatial independence and feature-alone AUC are essential. |
| 3 | **Detrended-relief curvature persistence:** detrended elevation and its slope, augmented only by official linked DEM tiles if accessible. | A persistent, multi-scale concave/convex break or aligned drainage deflection can mark a surface expression of an unmapped fault. | Must distinguish from scarp/topographic-gap and dotted-ridge families already represented in the user's historical list; high duplication risk. High cost because DEM coverage, licensing, resampling, and tile seams need checks. |
| 4 | **Gravity–magnetic structural discordance:** isostatic gravity anomaly/slope jointly with magnetic derivatives. | Coincident gradients or a systematic offset between density and magnetization boundaries may reveal basement structure masked in surface mapping. | Cross-physics discordance rather than a single geophysical edge or generic ensemble. Medium cost; listed layers are available in principle. Geologic interpretation and held-out validation required. |

**Priority rationale:** candidate order is a qualitative ranking of testability and expected mechanism relevance, not a DTI prediction. The required shared holdout scripts, cached features and labels are absent, so no experiment has been run and no improvement is established. The DEM idea is less ready because it depends on additional tile access. No candidate needs a new external dataset merely to formulate a first test; if one is needed for terrain, the official competition DEM-links CSV is the specific permitted source, but its data-page access is currently blocked here.

## Submission instructions

There is no valid downloadable submission file at this time. Do **not** submit a historical site's file as a newly generated unique artifact, and do not submit a zero/synthetic placeholder. Once a local candidate passes every holdout, uniqueness and file-format gate, see the [executive summary](docs/index.html) and the dedicated [submission guide](docs/submission-guide.html) for the final checklist. For the official submission format and challenge rules, use the [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [rules](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/).

A structural validator is provided at `scripts/validate_submission.py`. After placing an official sample raster locally (ignored by Git), install `requirements.txt` and run:

```sh
python scripts/validate_submission.py path/to/candidate.tif data/sample_submission.tif
python -m unittest discover -s tests -v
```

This checks matching grid/footprint, EPSG:32611, 100 m pixels, one float32 band, no non-finite values inside the footprint, [0, 1] probability bounds, null/NaN outside, and candidate SHA-256. It cannot assess model quality or originality. The tests use generated temporary fixtures and require no competition data.

## End-of-run JSON card

Every experiment report must end in a machine-readable card with: hypothesis; mechanism; named non-fault process that could mimic it; `HOLDOUT-DTI` including evaluator version, withheld-positive count and 95% CI (or explicitly `not run`); registry correlation/overlap (or `not testable`); raster SHA-256 (or `not generated`); validator output; submission name and note (at most 140 characters, or `not eligible`); verdict `promote` or `negative`. Never fill unavailable fields with estimates.
