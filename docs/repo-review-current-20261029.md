# Repository review — 29 October 2026

## Executive decision

**No new TIFF was generated. No file is cleared to submit.** This review did not start an experiment, run placement, select a competition slot, or claim a leaderboard score. The requested method paragraph that defines the one permitted lane is absent from the prompt/archive. The only local preregistration is explicitly provisional, and the WBG-C1 ledger is closed as `negative_stopped`. Starting a different idea or silently treating the unused portion of its experiment budget as permission would violate the lane/stop rules.

**The 0.2778 GEMSDOE32 B2 value is OWNER-REPORTED / NOT ORGANIZER-CONFIRMED.** The checked forensic record shows a plausible explanation for the historical ordering, but not proof of hidden-test causality: B2 is a strict subset of the D2.8 parent, deleting 6,436 of 44,090 parent positives and adding none; all removed pixels are 1–2 pixels from the public fault catalogue. Under the official distance-weighted Tversky objective, nearby predictions can have reduced false-positive cost, so removing low-credit dots could improve the score. The missing hidden labels and missing artifact-linked DrivenData receipt prevent us from saying that this deletion caused the **0.0178 difference between the two OWNER-REPORTED values**. No new-file leaderboard estimate is supportable.

**Next scientific priority (proposal only):** estimate signed, scale-dependent displacement between magnetic and gravity edge ridges relative to detrended-elevation structure (candidate P1 below). It is distinct from the repo's implemented up-dip back-projection and curvature-complexity transforms, but it is not authorized or tested. Current core TIFFs and the 19-band feature cache are absent in this checkout, and the official competition data URL redirects to login. `python scripts/check_readiness.py` reports `BLOCKED_INPUTS`; its exit code is 2. Do not treat the public owner-mirror restore as organizer authentication.

## Decision table: the nine requested sites

All values in this table are **USER/OWNER-REPORTED historical values**, not organizer-confirmed receipts. “New-file estimate” is **unavailable**. The referenced prediction masks are historical and must not be copied or resubmitted; the repository's frozen audits find overlap/duplicate relations that fail the stated uniqueness policy. The exact site-by-site files, hashes, lineage, and comparisons are also available in [`docs/focus9-executive-summary.html`](focus9-executive-summary.html) and [`docs/data/nine-site-audit.json`](data/nine-site-audit.json).

| Site | Highest supplied historical file | Historical value | New-file score estimate | Reuse / submit decision |
|---|---|---:|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | Unavailable | No; historical reference only |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 | Unavailable | No; decoded predictions duplicate GEMSDOE30 |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | Unavailable | No; historical reference only |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | Unavailable | No; historical reference only |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | Unavailable | No; pixel predictions match GEMSDOE25 |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 | Unavailable | No; same prediction family as GEMSDOE28 |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778** | Unavailable | No; highest supplied claim, historical learning only |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | Unavailable | No; historical reference only |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | Unavailable | No; recorded as B2 plus 1,200 pixels |

These historical files are not safe “download-and-submit” choices. The explicit current answer is **DO NOT SUBMIT**. The site's research TIFFs are not a substitute for a validated competition prediction.

## B2 forensic interpretation

The official problem describes the target as **faults** missing from the public USGS/INGENIOUS catalogue, not confirmed geothermal vents. The published metric uses a 300 m triangular distance kernel, alpha 0.2 and beta 0.8. Thus, a prediction near a newly labelled fault can receive partial distance-weighted credit, while a prediction near only an existing/catalogued fault may incur false-positive cost. On the pinned B2 and D2.8 rasters, the reproducible ancestry is:

- D2.8 parent: 44,090 positive pixels; B2: 37,654.
- B2 deletes 6,436 parent pixels and adds zero; every removed pixel lies within 200 m of the public catalogue (in fact 1–2 raster pixels in the recorded forensic calculation).
- The exact uploaded result, hidden truth, TP/FP/FN decomposition, and official submission receipt are unavailable. Therefore, deleting low-marginal-credit positives is a **plausible metric mechanism**, not established causation or a recipe for a new submission.

This is also not an independent geological discovery: B2 is a deletion-only descendant of D2.8. Matching its output or merely pruning the same places would violate the user's uniqueness objective.

## Submission format, leaderboard, and current artifact status

The official problem page requires a single-band float32 GeoTIFF in EPSG:32611 at the training grid's 100 m resolution and bounds, with values in [0,1] and null/NaN outside the study bounds. The earlier reported portal error (“Predicted values must be in range [0, 1]”) cannot be diagnosed without the rejected bytes and organizer receipt. Existing local format checks do not prove organizer acceptance; some archived research TIFFs use zero outside the footprint, which differs from the published null/NaN instruction. **No new file is approved.**

The public leaderboard numbers in the long-standing prompt (0.3195 and 0.4413) conflict with a retained project feed observation of 0.4544 dated 27 October 2026. That feed is explicitly not refreshed in this review. Do not represent any of those values as a current verified observation or as a score for a project TIFF.

## Ranked prospective hypotheses (not experiments or score forecasts)

This is a qualitative research-priority ranking, **not a numeric estimate of DTI improvement**. “Not tested” means the exact operator is not recorded as an executed experiment in the inspected checkout; related methods exist, and fleet-wide novelty is not claimed. Each candidate remains unauthorized while the lane assignment and current registry policy are unresolved.

| Rank / expected incremental benefit / cost | Layers and proposed signature | Why it could find an uncatalogued fault; named non-fault mimic | Difference from implemented repo work | Data/source readiness |
|---|---|---|---|---|
| **P1 · highest priority, uncertain/moderate potential · medium cost** | Existing feature bands: `tmi` (14), `iso_grav_anom` (13), `det_elev` (12). At fixed physical scales, find local gradient-ridge positions and estimate the **signed cross-normal displacement** between magnetic and gravity ridges, then measure whether the displacement changes coherently relative to the detrended-elevation structural frame. | A buried or dipping density/magnetization boundary may produce spatially offset field responses relative to muted surface relief; the offset geometry may expose a concealed structure not represented by the catalogue. **Mimics:** intrusive/dike contacts, lithologic boundaries, magnetic remanence changes, and survey-line leveling seams. | Unlike DPGF-1's assumed dip-guided up-dip advection and the C1 conductivity/depth Hessian commutator, this estimates observed relative edge displacement between independent channels; it does not use catalogue distances or prior prediction pixels. An untested concept appears in the repository's historical proposal notes, so it is new as an unrun candidate here, not globally novel. | The 19-band source is supposed to contain the named channels, but the TIFF/cache is absent locally. The competition's official data page currently redirects to login. A pinned public owner-mirror restore route exists, but it does **not** authenticate organizer origin. No new external source is required for an initial test. Not presently testable in this checkout. |
| **P2 · uncertain/moderate potential · medium-high cost** | Official GeoDAWN K, Th, U radiometric grids plus isostatic-gravity gradient. Compute robust, multiscale centred-log-ratio residuals (local K–Th–U compositional departure), then test for a narrow compositional boundary that is spatially coherent with, but not copied from, a gravity edge. | Fracture-guided fluid alteration could change near-surface element ratios along a concealed structure without a mapped scarp. **Mimics:** lithologic contacts, felsic ash, weathering, soil sorting, playa redistribution, and flight-height/processing artifacts. | Prior repo/peer methods include raw bands, ratios, and combined radiometric priors. The specific local compositional-closure residual plus spatial edge-conditioned test is not recorded as executed in this repo. | USGS GeoDAWN's official data release (DOI 10.5066/P93LGLVQ) was reachable in this review, identifies downloadable grids, and states CC0. The source page's availability is verified; raster bytes, exact overlap, scaling, and resampling metadata have **not** been downloaded or checked here. External acquisition and metadata audit are prerequisites. |
| **P3 · uncertain/low-to-moderate potential · high cost** | Well-level residuals in the USGS Great Basin heat-flow release, conditioned on the release's background model; spatially cross-fit a local anomaly statistic and test association with cached conductance/gravity edges. Use individual residuals, **not** the background conductive map as a hydrothermal signal. | A well residual may mark convective or groundwater influence near a hidden conduit that the broad, smoothed structure catalogue misses. **Mimics:** groundwater flow, measurement/thermal-conductivity error, uneven well sampling, and spatially clustered drilling. | Existing local code uses 2 m temperature probes, springs, and geothermal/geophysical priors; it does not establish this USGS well-residual estimator. The novel element is a sampling-aware, cross-fitted residual association—not simply proximity to wells. | The official USGS source page and DOI 10.5066/P9BZPVUC were reachable; it describes point well coverage with residual attributes and marks the release CC0. Individual points, the exact residual field, footprint coverage, and metadata have not been fetched/verified. Viable only after that audit. |
| **P4 · uncertain/low potential · high cost** | 1–10 m bare-earth elevation/hydrology from USGS 3DEP; extract channel/valley centerlines, then test repeated cross-slope channel offsets or knickpoint pairs for geometric alignment and persistence across scales. | Fault displacement can deflect or offset drainage where a sharp scarp is absent or eroded. **Mimics:** lithologic knickpoints, landslides, road/ditch diversions, and drainage-network extraction errors. | Existing LiDAR work detects scarp shape, curvature, relief and coherence; this targets drainage-network geometry rather than scarp amplitude or a lineament ridge. No exact channel-offset operator is recorded as an experiment here. | USGS 3DEP documentation confirms free products and links data access/spatial metadata. Coverage, acquisition dates, and quality across the exact competition footprint were not checked. Therefore it is **not yet viable** as a full-footprint candidate; run a tile-availability audit before any preregistration. |

### Why P1 was not evaluated

The requested validation condition is not met. The current checkout lacks `data/training_features.tif`, `data/labels.tif`, `data/sample_submission.tif`, and all 19 cached bands. `scripts/check_readiness.py` checked the working tree and returned `BLOCKED_INPUTS`; it does not trust historic receipts to pretend those files are present. The official competition data URL resolved to the DrivenData login page in this review. The single-method lane paragraph was not present, and the local WBG-C1 ledger is `negative_stopped`. Consequently there is **no new HOLDOUT-DTI, no canary output, no raster, no new validator receipt, and no basis to report a projected score**. Running P1 now would both lack inputs and lack lane authorization. No slot was touched.

## Three-pass review and repository findings

1. **Pass 1 — inventory/evidence:** read `AGENTS.md`, `PROMPT.md`, README and the 920-line archived user prompt; inspected the current run cards, registry, experiment ledger, source manifests, candidate implementations, site generator, and focus-nine audit. Rechecked the official DrivenData problem page, its login-walled data URL, USGS GeoDAWN, USGS heat-flow and USGS 3DEP source pages. Confirmed the local README/PROMPT already preserve the complete original request in an expandable archived section.
2. **Pass 2 — defects/edge cases:** found `AGENTS.md` still claimed WBG-6 was approved and called WBG-7 “this branch,” while the current README correctly says no TIFF is cleared; found old hypothesis docs/site copy still described magnetic texture as untested even though WBG-5/MTA-1 had already run and was null; found the website's visible WBG-7 callout could be read as an approved “unique submission” despite its later no-clearance clause. Corrected these stale pointers and made the current negative status explicit; did not alter frozen score/run receipts.
3. **Pass 3 — requirement check:** cross-checked the nine-site table against the dated current review and machine-readable audit; ensured OWNER-REPORTED values are not described as measured scores; confirmed the candidate ranking states layers, signature, missing-fault rationale, mimic, local difference, and data/source readiness; confirmed no new experiment/placement/upload/slot action occurred. Added a machine-readable negative review card and tests to prevent stale approval language returning.

### Important irregularities / limitations

- Historical values, including 0.2778, lack organizer-page receipts in this repository. No causal hidden-truth explanation or new leaderboard projection is justified.
- `docs/data/feed.json` is retained feed evidence, not proof of a fresh leaderboard or repository-raster audit. Upstream heads changed after the frozen focus audit; a changed commit alone does not prove changed files/scores.
- Core TIFFs and feature cache are absent locally. Public mirror hash integrity does not establish organizer origin; official download access is login-walled here.
- Official submission format says data outside the region must be null/NaN. Some frozen research TIFFs use zeros outside for local compatibility. A local validator pass is not portal acceptance.
- The user-requested literal novelty gates are not replaced with density-normalized exceptions. A dense registry raster can make the >70% proximity gate uninformative, but that is a policy issue to resolve centrally—not permission to weaken or evade it.
- Competition target is mapped faults indicative of geothermal resources, not geothermal vents themselves. Faults are not proof of permeability, heat, or a commercially viable resource.

## Official links checked in this review

- [DrivenData problem description, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — official page read during this review; fault target, DTI definition, and raster requirements.
- [DrivenData competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — resolves to login in this environment; no authenticated data download attempted.
- [USGS GeoDAWN official release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) — page identifies public downloadable data products and CC0 rights.
- [USGS Great Basin heat-flow maps and supporting data](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa) · [DOI 10.5066/P9BZPVUC](https://doi.org/10.5066/P9BZPVUC) — page describes background conductive heat-flow maps and point-well residuals; CC0 rights.
- [DOE OpenEI GDR INGENIOUS compilation](https://gdr.openei.org/submissions/1391) — public listing, CC BY 4.0; includes a 1.03 MB 2 m temperature-probe archive. Local model code already contains probe-derived features, so this is not presented as a new data source for this review.
- [USGS 3D Elevation Program](https://www.usgs.gov/3d-elevation-program) — free products and access tools; footprint tile availability not verified.

## Review run card

See [`docs/data/repo-review-20261029.json`](data/repo-review-20261029.json). Verdict: **negative**. No new TIFF or HOLDOUT-DTI exists for this review. No file is approved for download-and-submit.
