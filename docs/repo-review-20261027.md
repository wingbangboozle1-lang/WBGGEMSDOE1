# Repository review — 2026-10-27

> **Historical parallel review — superseded in part by the current shared-Euclidean safety audit.**
> Its earlier nine-champion overlap figures used a different private distance diagnostic; use
> [the WBG-2 executive audit](wbg2.html) and [current safety receipt](data/wbg2-safety.json)
> instead. The existing final TIFF fails the literal rule (99.8972% overlap with the pinned
> lattice), its prior was reconstructed only retrospectively, and 813 existing dots are
> less than 400 m Euclidean from the catalogue because the historical buffer was Manhattan.
> Owner-mirror inputs were restored later; organizer-origin authentication remains unavailable.
> Historical forecasts are withdrawn, and no file is approved for submission.

> Preserved parallel review from PR #16. Its historical model estimate and test count
> are superseded by the [protocol correction](protocol-review-20261027.md): forecast
> withdrawn, literal overlap STOP, 149 tests. No upload approval.

## Decision

**No new experiment, TIFF, or competition upload is authorized by this review.** The working tree contains a prior, explicit STOP for the WBG-C1 lane: its surface had 99.87% forward 3-pixel overlap with a registry lattice and paired efficacy did not establish improvement. The standing protocol says stop after a duplicate gate. Starting another method here would violate the lane rule; changing method lanes requires a separately assigned lane and a fresh, complete registry audit. No submission slot has been used.

This review therefore assesses the repository and preserves candidate ideas for a future authorized session. It does **not** claim to validate them, nor label a projection as a score.

## Candidate hypotheses for a future, separately authorized lane

Ranking is qualitative prioritization, not a measured result. All ideas assume the existing 19-band cached feature stack is complete and trustworthy; that assumption is currently false in this checkout because only the small bridge files exist under `data/` and the ignored feature cache is absent. The official competition feature bundle is login-gated, as recorded in `data/README.md`. Restore and hash-check the pinned template inputs before any holdout run. Do not fetch unreviewed third-party inputs.

| Rank | Candidate and specific layers | Target physical signature | Why it may find an uncatalogued fault | Difference from methods already recorded | Expected DTI gain | Cost / blocking test |
|---|---|---|---|---|---|---|
| 1 | **Multi-scale magnetic analytic-signal edge persistence** — magnetic-field bands in the existing feature stack | Edge/analytic-signal ridge that persists across smoothing scales and has consistent horizontal gradient orientation | Buried or weakly expressed structures may create coherent magnetic boundaries even where surface fault mapping is incomplete; persistence suppresses isolated cultural/noise edges | Tests a scale-persistence edge representation, not WBG-C1's cross-depth conductance Hessian commutator, TIP1's LiDAR directional derivative, or historical catalogue-derived dot thinning | Low-to-moderate, unmeasured; geophysical boundaries are not uniquely faults | Medium; feature-only leakage/AUC canary, then spatial hide-and-recover against matched control. Named mimic: lithologic contact / magnetic susceptibility boundary. |
| 2 | **Radiometric contact plus terrain-break concordance** — K, eTh, eU radiometric bands plus DEM-derived slope/curvature from cached terrain if present | Co-located, multi-scale radiometric gradient and slope-break edge, penalizing single-sensor edges | Shallow alteration/weathering or structural juxtaposition may create coincident surface geochemical and topographic boundaries missed in the catalogue | Multisensor concordance, rather than prior HGB combination, single-sensor scarp ranking, or radial/circular vent priors | Low, unmeasured | Medium-high; confirm required bands exist and assess missingness; feature-only AUC; grouped holdout. Mimics: lithology, soil moisture, vegetation/flight-line artifacts. |
| 3 | **Gravity residual lineament persistence** — gravity Bouguer/residual band only if part of the official cached stack | Directional second-derivative or curvature ridge persistent across physically plausible wavelengths | Faults may juxtapose density contrasts or bound basin structures that are not expressed as mapped surface scarps | Long-wavelength potential-field structure, unlike WBG-C1's conductance depth surfaces and the historical topographic gap closure | Low, unmeasured; uncertain fault specificity | High; first verify data availability/provenance. No new external source proposed absent evidence the feature is missing. Mimics: basin margin and lithologic boundary. |
| 4 | **DEM drainage/valley deflection at fault crossings** — DEM and derivatives from cached terrain | Abrupt, repeated channel deflection / valley alignment supported by local relief and curvature, not raw lineament density | Displaced drainage can expose active or geomorphically preserved structures absent from a geologic fault catalogue | Hydrologic network geometry differs from scarp-only scoring, dotted ridge, and catalogue-distance exclusion | Low, unmeasured | High; extraction and resolution sensitivity; feature-only canary and spatial holdout. Mimics: lithologic control, drainage engineering, glacial/landslide terrain. |
| 5 | **Thermal-radiometric anomaly with magnetic corroboration** — thermal channel plus magnetic band only if present in official cached stack | Spatially coherent thermal contrast co-located with magnetic structure, with local background correction | Potential geothermal alteration/heat expression could indicate a system beyond mapped fault traces | Directly tests thermal/geothermal expression rather than fault-geometry priors or catalogue thinning | Very uncertain; geothermal signal likely weak at airborne resolution | High; verify thermal data provenance and coverage before proceeding; feature-only canary. Mimics: lithology, emissivity, elevation, acquisition conditions. |

These are **hypotheses**, not established geological detections. None is deemed viable or ordered for implementation until a lane is assigned, feature provenance is verified, each feature passes the leakage canary, and the registered holdout beats a same-evaluator control. If needed layers are absent, this review does not authorize acquiring replacements; first identify a specific official source and verify access, spatial coverage, license, and compatible resolution.

## Current best comparison and why H33-B2 scored higher (reported)

The repository's forensic record identifies GEMSDOE32 H33-B2 as an exact subset of a 44,090-pixel parent: it removed 6,436 predictions, all within 200 m of the public mapped-fault catalogue, without adding detections. The reported score changed from 0.2600 to 0.2778. This supports the **mechanism hypothesis** that deleting low-credit predictions can improve a precision-sensitive DTI; it does not prove causation because hidden truth, organizer receipt, and exact uploaded-file receipt are absent. The value **0.2778 is OWNER-REPORTED / UNVERIFIED**, not HOLDOUT-DTI or ORGANIZER-CONFIRMED.

The WBG-2 artifact in the repository is locally described as unique against the nine focus-site files and format-valid. Its 0.2824 is a **MODEL-ESTIMATE** with a narrow calibration interval, not a leaderboard score or holdout measurement. The estimated +0.0046 over 0.2778 does not establish a real improvement, particularly because the reference value is unverified and the candidate was not cleared against every registry raster. Accordingly, the repository's “SUBMIT: YES” callout is too strong relative to the parallel-run protocol's global registry/holdout gates. Treat that file as **downloadable for audit; not cleared for upload under the present lane protocol** until a complete, current surface-and-final-dot audit and same-evaluator efficacy comparison are documented. This is a governance correction, not a claim that the file is invalid.

## Verification completed in this checkout

- Read `PROMPT.md`, README, the lane experiment record, follow-up run card, WBG-2 summary, nine-site evidence, and existing experiment cards.
- Confirmed the nine focus sites in the evidence registry are GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Their historical score values are labeled owner-reported/unverified in the evidence record.
- Confirmed the WBG-C1 follow-up card records no new experiment, no new TIFF, no final dots, and zero slots used.
- Confirmed `data/` does not contain `training_features.tif` or the ignored cached 19-band feature stack; only small bridge inputs and provenance files are present.
- Initial system Python lacked pytest and scientific dependencies. Installed the exact `requirements-lock.txt` into ignored `.venv/`; then `python -m pytest -q` passed **143 tests** (17 dependency/deprecation or constant-input warnings).
- `.venv/bin/ruff check --select E9,F scripts src tests` passed; `git diff --check` passed. A broader unfiltered Ruff run reported 173 existing style/metadata findings (e.g. executable-bit/import-order and advisory rules); this change did not attempt unrelated cleanup.
- Ran `scripts/build_site.py`, `scripts/build_readme.py`, `scripts/stage_pages.py`, and `scripts/build_wbg2_site.py`; the report rebuilt and the generated homepage and README preserve the fail-closed status. Static browser CI passed. Full verify CI initially failed at its deterministic rebuild step before generator sources were updated; rerun required after push.
- Working tree was clean before this review. No model experiment or submission raster was modified; generator/documentation code was changed to avoid reintroducing the overconfident submit approval.

## Required next steps / release blockers

1. Obtain the official competition bundle through an authorized login on an unrestricted machine; run the repository's pinned restore/prepare path and verify every SHA-256 before research. Do not claim data-independent model results in its absence.
2. Assign a single new method lane and freeze its hypothesis, control, evaluator, budget, and registry snapshot. Do not resume WBG-C1 or bypass its duplicate stop.
3. Restore dependencies and run the full test suite, lint, build and local TIFF validator from a clean checkout.
4. Run feature-alone leakage canaries before fitting a combined model; then compare against an identical spatial holdout control with pooled DTI and paired spatial-block confidence interval.
5. Before any live upload, perform surface correlation and literal 3-pixel dot-overlap checks against all nine target sites and every available registry raster, both before and after final placement. Missing registry coverage must remain an explicit failure, never a pass.
6. Reconcile all score assertions with organizer receipts. Keep leaderboard estimates, public leaderboard observations, owner reports, and HOLDOUT-DTI in separate evidence classes.
7. Do not spend a weekly submission slot unless the candidate beats the same-evaluator control and passes format, range, uniqueness, and provenance gates. A local format pass is not organizer acceptance.

## Source links for manual verification

- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data page (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data description](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [Competition submission instructions PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

**Run-card verdict: negative.** No new method was run, so this review has no new HOLDOUT-DTI, no candidate TIFF hash, and no promotion verdict. Existing negative/STOP evidence remains controlling.
