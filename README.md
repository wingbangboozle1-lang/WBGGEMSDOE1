# GEMS fault-discovery research and submission gate

> **Read this brief before every project task.** The project is to build an auditable, scientifically defensible workflow for discovering unmapped faults associated with geothermal resources and producing a valid GEMS Prize Challenge GeoTIFF. Maximize the probability of a genuine, generalizable result; own the outcome, report failures, and never present a projection or an unverified external result as a measured score. This charter distills the user's requirements; use the executive-summary page as the live, dated evidence register.

## Executive status

**STOP — there is no submission-ready TIFF in this repository. Do not download or submit a file from this project yet.** This checkout contains no competition data, cached feature stack, trained model, holdout evaluator, submission writer, registry rasters, or historical TIFFs. Accordingly, no local score estimate, holdout result, raster uniqueness test, or scientifically grounded submission can be produced here. A made-up/synthetic raster would not satisfy the challenge or the user's uniqueness and high-score gates.

The official competition specification requires one float32 GeoTIFF in EPSG:32611, at 100 m resolution and the training-data bounds, with one band of predictions in [0, 1]; outside the data bounds must be null/NaN. The official metric is distance-weighted Tversky with alpha 0.2, beta 0.8 and a 300 m triangular distance kernel. See the [official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login required).

For the direct answer about the nine focus sites, user-/owner-reported historic scores, uncertainty about duplicate lineages, research hypotheses, official source links, and the exact upload steps, open the [executive summary](docs/executive-summary.html). The page clearly says no file is approved and labels historical scores as unverified context. The [submission guide](docs/submission-guide.html) explains format checks and the DrivenData form.

## Non-negotiable workflow

1. **No invented numbers.** Each candidate/model score must be labelled `HOLDOUT-DTI` (include evaluator version, withheld-positive count, and 95% CI) or `ORGANIZER-CONFIRMED` (copied from that submission's receipt). Historical user-/owner-reported values and official public leaderboard snapshots must be explicitly labelled as context, not as our measured score or receipt. A model projection is never a score.
2. **One scientific lane.** Before experimentation, state one mechanism and stay within it. The prompt refers to a “single method paragraph below,” but no such lane paragraph was present in the request received for this session. No experiment was started until that lane is specified. Compare the surface before placement and final raster against every available registry raster; if absolute rank correlation exceeds 0.90 or more than 70% of dots lie within 3 px of one registry raster, record the duplicate and stop.
3. **Use shared assets, not a private reimplementation.** Reuse the template feature cache, `evaluate_holdout.py`, and `submission_writer.py` when present. Hold out whole fault segments with a buffer; derive catalogue features only from visible faults; mask visible faults pixel-exactly; evaluate pooled DTI with alpha 0.2, beta 0.8 and the 300 m triangular kernel. Fix shared tools at their source, not in an untracked fork.
4. **Leakage canary.** Score every feature alone on the holdout before trusting it. AUC above 0.90 is a leakage warning until independently explained.
5. **Hard budget.** At most 3 experiments or 2 hours, whichever comes first. Do not select/promote a candidate or use a weekly submission slot until the separate selector step confirms it beats the current holdout best and respects the live weekly cap.
6. **Fail-closed submission gate.** Do not label anything “OK to submit” until the actual TIF passes structural checks (CRS, dimensions, transform, one float32 band), finite/range checks ([0, 1] inside the footprint; no NaN inside), footprint/nodata checks, leakage checks, and duplicate checks. Only then provide the actual downloadable file, a unique name, and a short note.
7. **Auditability.** Keep evidence, source links, assumptions, failed tests, hashes, validator output, and an experiment/run card. Distinguish official evidence from site-reported claims. No human visual inspection substitutes for programmatic validation; expert geological interpretation is a separate scientific question.
8. **No copying.** Prior submissions may be studied or used as collision references only. Never copy one as the competition prediction or claim a modified raster is unique without the specified registry comparisons.

## Current state and next actions

- This session added an executive-summary subpage, a project front page, a submission guide, a run card, a GeoTIFF validator with synthetic-fixture tests, and a file-presence readiness script. No competition data, model, holdout evaluator, submission writer, registry raster or prediction TIFF was added.
- `python scripts/check_readiness.py` currently reports `BLOCKED` (expected exit code 2). It lists the required official data files and requested shared evaluator/writer that are missing. It checks file presence only; it does not certify pipeline or scientific readiness.
- `scripts/validate_submission.py` verifies a prediction raster against an official sample grid. It can catch errors such as predicted values outside [0,1], but it cannot validate model quality, novelty, or score. The tests use generated temporary rasters and need no competition files.
- The linked DrivenData data page requires sign-in. No competition files or authenticated data download are present here. Do not claim otherwise or bypass access controls. The official [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) instructs users to obtain challenge data from DrivenData and place it in its data directory.
- The official problem description confirms the target is faults and that the initial prize test includes expert-labelled faults missing from the public USGS fault database. It describes GeoDAWN data and USGS/INGENIOUS fault labels. It does **not** establish that any particular prior submission is scientifically correct or unique.
- Historical submission names/scores quoted in the request are leads, not verified receipts. A score or filename suffix alone does not reveal a raster's construction or why it performed. See the executive summary's nine-site table; it uses the user-provided score values and reports a sibling site's duplicate claims as unverified, not independently tested.
- The official public leaderboard page retrieved 2026-10-26 displayed a #1 public result of 0.4437 (an `ORGANIZER-PUBLIC-LEADERBOARD` snapshot, not a submission-page receipt for our work). The request also stated 0.3195 and 0.4413; those conflict with one another and the retrieved snapshot. The live leaderboard is time-sensitive, and public performance is not a private/final award score. This repository currently records a static dated snapshot; automatic refresh is still future work.
- **Next:** place legally obtained competition files in ignored `data/`; recover/configure the shared template cache, evaluator, and writer; obtain the complete registry rasters; resolve the missing lane paragraph; then preregister and run the bounded leakage-controlled holdout. These are blockers, not tasks that can be solved by guessing.

## Candidate hypotheses for later testing (not results or score estimates)

These are a scientifically grounded shortlist based on layers described on the official competition page. The repository currently has no feature/model implementation, so “distinct from this repo” means no local implementation exists; it does not prove novelty relative to all GEMSDOE sites. The hypotheses are untested, and their expected DTI improvement is **unquantified**.

| Rank (priority, not a score) | Hypothesis and layers | Physical signature / missing-fault mechanism | Difference from known approaches / non-fault mimic / cost |
|---|---|---|---|
| 1 | **Paired magnetic-contact and source-depth discontinuity:** total magnetic intensity, horizontal/vertical magnetic derivatives, and top-of-crustal magnetic source-depth estimate. | Test whether persistent, scale-consistent magnetic edge ridges co-locate with a source-depth step. A buried structural boundary may offset or juxtapose magnetic sources where there is no mapped surface trace. | Composite cross-layer edge agreement rather than a raw catalogue buffer. Must be checked against prior edge-style submissions. **Mimics:** lithologic contacts, intrusive bodies, survey seams. **Cost:** medium/high. |
| 2 | **Strain-tensor orientation/coherence breaks:** dilatation, shear strain rate, and second invariant of strain rate; earthquake density only as secondary corroboration. | A persistent narrow discontinuity in strain orientation/invariant may mark mechanical localization along an unrecorded structure. | Explicitly tests gradients/coherence rather than only high strain magnitude. **Mimics:** regional strain gradients, basin boundaries, gridding artifacts, unrelated earthquake swarms. **Cost:** medium. |
| 3 | **Detrended-relief curvature persistence:** detrended elevation/slope, optionally official linked 1 m DEM tiles if accessible; corroborate with magnetic edge orientation. | A multi-scale concave/convex break or drainage deflection may show a subtle, low-relief fault trace not represented in the catalogue. | Conditional curvature-plus-geophysics test rather than a standalone scarp/ridge ranking. Historical site names already include scarp/topographic-gap/curvature approaches, so novelty risk is high. **Mimics:** drainage incision, alluvial fan margins, landslides, roads/terraces, lithologic benches. **Cost:** high. |
| 4 | **Gravity–magnetic structural discordance:** isostatic gravity anomaly/slope jointly with magnetic derivatives. | Co-located gradients or a systematic offset between density and magnetization boundaries may reveal basement structure masked in surface mapping. | Cross-physics discordance rather than a single edge or generic weighted sum. Multi-physics concepts appear in the wider site history, so global novelty is unproven. **Mimics:** lithologic contacts/intrusions and processing seams. **Cost:** medium/high. |

Priority is a qualitative judgment about physical rationale and testability, not a score prediction. The top candidate should be validated first only after lane resolution, single-feature leakage canaries, surface novelty checks, and restoration of the shared evaluator/baseline. It can be tested with the official feature stack; the 1 m DEM is not needed for the first two candidates. No new third-party dataset is proposed as a viable requirement. If future work requires terrain tiles, the specific source to check is the official competition `1m_DEM_links.csv` after authorized access is available.

## Submission instructions

There is no valid downloadable submission file at this time. Do **not** submit a historical site's file as a newly generated unique artifact, or submit a zero/synthetic placeholder. After a candidate passes all holdout, uniqueness, and format gates, follow the [executive summary](docs/executive-summary.html) and [submission guide](docs/submission-guide.html). Official requirements and current rules are on the [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [rules](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/).

Run the structural validator against a candidate and the official sample raster (after authorized data placement):

```sh
python -m pip install -r requirements.txt
python scripts/validate_submission.py path/to/candidate.tif data/sample_submission.tif
python -m unittest discover -s tests -v
```

The validator checks the grid/footprint, EPSG:32611, 100 m pixels, one float32 band, finite [0,1] values inside the footprint, null/NaN outside, and candidate SHA-256. It cannot assess model quality or originality. The readiness script reports missing file inputs only.

## End-of-run JSON card

Every experiment report must end with a machine-readable card containing: hypothesis; mechanism; named non-fault mimic; `HOLDOUT-DTI` evaluator/version, withheld-positive count and 95% CI (or explicitly `not run`); registry correlation/overlap (or `not testable`); raster SHA-256 (or `not generated`); validator output; submission name/note (≤140 characters or `not eligible`); verdict `promote` or `negative`. Never fill unavailable fields with estimates. The current negative card is [`evidence/run-card.json`](evidence/run-card.json).

## Verified sources and project pages

- [DrivenData challenge description, metric, and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData challenge background](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData data download page (sign-in may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData rules](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/)
- [DrivenData live public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official GEMS reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN survey data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS ScienceBase GeoDAWN area](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611 reference](https://epsg.io/32611)
