# WBGGEMSDOE1 review — 27 October 2026

> **Historical parallel review — superseded in part by the current shared-Euclidean safety audit.**
> Its earlier nine-champion overlap figures used a different private distance diagnostic; use
> [the WBG-2 executive audit](wbg2.html) and [current safety receipt](data/wbg2-safety.json)
> instead. The existing final TIFF fails the literal rule (99.8972% overlap with the pinned
> lattice), its prior was reconstructed only retrospectively, and 813 existing dots are
> less than 400 m Euclidean from the catalogue because the historical buffer was Manhattan.
> Owner-mirror inputs were restored later; organizer-origin authentication remains unavailable.
> Historical forecasts are withdrawn, and no file is approved for submission.

## Decision at a glance

**No artifact in this repository is currently cleared to submit.** The WBG-2 GeoTIFF remains downloadable as a research artifact. Its single-band/CRS/shape/transform/range/finite-value checks pass, and its recorded *scoped* comparison includes all nine requested focus sites. However, the literal repository-wide registry audit records **100% forward 3 px overlap** with the dense WBG-C1 research surface, exceeding the protocol's 70% stop threshold. There is also no measured pre-placement surface check, no comparable `HOLDOUT-DTI` for WBG-2, no positive paired interval against a same-instrument best, and no separate selector authorization. Do not upload it or any negative research file.

- WBG-2 TIFF: [`docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif`](downloads/wbg2-offcatalogue-density-36k-20261027.tif)
- SHA-256: `f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3`
- Validated as research download: **yes**. Scoped focus-site forward overlap max 18.61%, max |Spearman| 0.0095; repository-wide literal forward-overlap STOP: **100%** against WBG-C1. Cleared to submit: **no**.
- Score estimate: **unavailable**. The former 0.2824 regression output is withdrawn as a score estimate; it used nine unverified reported values, including two sites with identical decoded predictions.
- Experiment count this review: 0. Competition slots used: 0.

## Nine-site executive comparison

The values below are copied from the user-provided historical report and the repository's frozen raster audit. Each listed value is **OWNER-REPORTED / NOT ORGANIZER-CONFIRMED** because no artifact-linked submission-page receipt is present here. They must not be treated as current leaderboard scores or HOLDOUT-DTI.

| Site | Best listed artifact | Historical value | Evidence status | WBG-2 focus-site uniqueness audit |
|---|---|---:|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5` | 0.2477 | OWNER-REPORTED | compared; not an exact pixel copy |
| GEMSDOE25 | `dotted-h19-5-d2-8` | 0.2600 | OWNER-REPORTED | compared; its pixel set is identical to GEMSDOE30 |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5` | 0.2449 | OWNER-REPORTED | compared; not an exact pixel copy |
| GEMSDOE28 | `h36-1-rung30-blind-r1` | 0.2710 | OWNER-REPORTED | compared; not an exact pixel copy |
| GEMSDOE30 | `d28-poisson300m-offcat-44090` | 0.2600 | OWNER-REPORTED | compared; pixel-identical to GEMSDOE25 |
| GEMSDOE31 | `h27-4-solo-d28` | 0.2708 | OWNER-REPORTED | compared; not an exact pixel copy |
| GEMSDOE32 | `h33-h33-2-b2` | 0.2778 | OWNER-REPORTED | compared; not an exact pixel copy |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30` | 0.2632 | OWNER-REPORTED | compared; not an exact pixel copy |
| GEMSDOE36 | `anderson-geothermal-pinn-38854` | 0.2750 | OWNER-REPORTED | compared; not an exact pixel copy |
| WBG-2 | `wbg2-offcatalogue-density-36k-20261027.tif` | unavailable | no comparable HOLDOUT-DTI | 9/9 focus artifacts audited (max overlap 18.61%, max |rho| 0.0095), but global literal registry gate FAILS: 100% forward 3 px overlap with WBG-C1; pre-placement surface gate not measured |

Do not infer the focus-site row proves global uniqueness. Its nine-site audit is scoped to those frozen artifacts and passes the numerical limits within that scope. The separate literal registry audit includes a WBG-C1 dense surface with 100% forward overlap and must STOP; the protocol provides no density/enrichment exemption. The pre-placement surface check is also absent. Numerical detail and source references are in [`evidence/wbg2/nine_site_uniqueness.json`](../evidence/wbg2/nine_site_uniqueness.json), [`evidence/wbg2/run_card.json`](../evidence/wbg2/run_card.json), and [`evidence/registry_surface_audit.json`](../evidence/registry_surface_audit.json).

## What the GEMSDOE32 B2 forensics establish

The on-disk raster audit identifies the GEMSDOE32 B2 field as a strict subset of the D2.8 parent: **6,436 positive pixels removed, zero added**, with every removed pixel within 200 m of the mapped public catalogue. This is consistent with a precision-cleanup explanation under a metric that values matching missing catalogue faults while charging false-positive predictions. It does **not** establish that every removed pixel was a hidden false positive, does not reveal hidden labels, and does not prove that deletion caused the owner-reported 0.2778. The reported historical value is unverified without an artifact-linked receipt. This distinction is documented in [`evidence/h33_b2_forensics.json`](../evidence/h33_b2_forensics.json).

## Preregistered hypothesis menu and experiment status

The existing [`research/00_ranked_hypotheses.md`](../research/00_ranked_hypotheses.md) contains five ranked proposals with physical mechanisms, layers, confounds, novelty and data/access cost. Its top TIP1 directional LiDAR-coherence-tip gradient was previously tested and **negative**; it must not be rerun or tuned. CLR1 compositional radiometric closure and DIFF1 scarp-diffusion shape use cached features but remain untested. MT3D depth-persistent magnetotelluric edges and SWIR1 optical alteration are not viable in the current sandbox because their required official data hosts are not obtainable under the present outbound allowlist and no audited local official-origin mirror was found.

No candidate is run in this review: the required single-method assignment paragraph is absent; prior lane STOPs are binding; the local WBG-2 file has no matched holdout result. Any new experiment requires an explicitly authorized lane and prospective preregistration. No submission slot is to be selected here.

| Existing rank | Hypothesis and targeted signature | Readiness / decision |
|---:|---|---|
| 1 (previously executed) | TIP1 orientation-following LiDAR coherence gradient at candidate fault tips; 3DEP-derived `coh100`, local strike, step and balanced curvature. | Already tested as a prior lane; negative efficacy and duplicate-lattice STOP. Do not rerun or retune. |
| 2 | CLR1 multiscale K–Th–U compositional log-ratio closure residual, optionally corroborated by gravity-gradient structure. | Cached inputs are listed, but semantic/provenance and blocked holdout validation remain. Untested here. |
| 3 | DIFF1 scale-normalized paired curvature / relief ratios for diffusion-degraded scarps. | Coarse cached maxima limit profile interpretation; the raw 1 m terrain source is required for stronger validation. Untested here. |
| 4 | MT3D depth-persistent strike-aligned conductivity edge from Great Basin 3-D magnetotellurics. | Potentially valuable but no locally audited official-origin volume; the cited USGS ScienceBase resource is outside this session's outbound allowlist. Not viable for this run. |
| 5 | SWIR1 Sentinel-2 shortwave-infrared alteration residual aligned to conductivity boundaries. | Requires a vetted cloud/season mosaic and official Copernicus/USGS access not available in this sandbox. Not viable for this run. |

The full preregistration provides the feature transforms, physical rationales, non-fault mimics, expected value/cost ranking, official-source URLs, and limitations. This summary does not claim that any untested proposal improves DTI.

## Irregularities and limitations

1. **Leaderboard conflict:** the newest user brief reports a current high of 0.3195. The repository retains public-page observations of 0.4437 (2026-10-26) and 0.4544 (2026-10-27), plus an earlier brief's 0.4413. These conflict; the current number is unresolved. DrivenData is outside this sandbox's outbound allowlist, so this review could not refresh the official page. None is a result for a project TIFF.
2. **Historical score provenance:** no submission-page receipt is available to bind the nine focus-site raster hashes to their reported values. The repo has corrected their labels to OWNER-REPORTED.
3. **WBG-2 performance is unmeasured:** its regression number is withdrawn. A catalogue-distance/budget fit to reported submissions is not a validation design and cannot establish a score for a new TIFF.
4. **Official training data is unavailable here:** the competition download endpoint requires authenticated access, unavailable in this environment. Mirrored/peer files do not establish organizer-origin provenance.
5. **External research access:** DrivenData, USGS/ScienceBase, GDR, Dropbox, and NLR hosts are not in the current outbound allowlist. Source links remain for review but were not freshly fetched in this session.
6. **No upload automation or account state:** there is no uploader, current weekly allowance, submission receipt, or slot selector authorization in the repository.
7. **Competition target:** mapping faults is not direct validation of a geothermal vent or resource. A fault-probability raster is not a vent discovery.

## Three review passes completed

1. **Implementation:** changed WBG-2 and the root README from “submit” to “research download only / DO NOT SUBMIT”; withdrew its historic regression as a slot-selection score estimate; made the generator and exact-file preflight fail closed on the binding literal-registry STOP, missing comparable HOLDOUT-DTI evidence, and missing selector authorization.
2. **Bug/assumption review:** updated the static-site builders and exact-file preflight so a format pass cannot print “safe to upload.” The current run card explicitly records the 100% literal-overlap STOP, missing holdout and no live selector approval. The historic score provenance and current-leaderboard discrepancy are visible.
3. **Final verification:** rebuilt the static reports; ran the full unit suite (**149 passed**); confirmed the local research TIFF and one-member ZIP against their recorded bytes; checked the generated pages for a clear no-submit decision. No geological experiment or slot was used.

## Official manual-review links

- [Competition overview / metric / format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — not freshly fetched in this sandbox.
- [Competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — authenticated download required.
- [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — current value unresolved in this review.
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — repository mirror reviewed at a dated Git commit in prior audit.
- [USGS GeoDAWN source](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — source link, not a fresh retrieval here.
- [DOE/GDR project data](https://gdr.openei.org/submissions/1391) and [competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — source links, not freshly fetched here.

**Bottom line:** download the WBG-2 TIFF only if you want to inspect the research artifact. It is **not OK to submit**. The safe next step is resolve official training-data access and leaderboard/source provenance, establish an authorized lane and same-evaluator current-best baseline, and validate a novel method prospectively before any separate slot selector considers it.
