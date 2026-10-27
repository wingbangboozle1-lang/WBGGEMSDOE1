# Corrected WBG-2 decision and official-source review — 27 October 2026

## Decision, scope and measurement

No new experiment, feature search, retraining, dot placement, weekly-slot selection or upload was performed. The candidate is the existing `wbg2-offcatalogue-density-36k-20261027.tif`, SHA-256 `f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3`. The pinned shared validator passes its single float32 band, `3730 × 3292` grid, EPSG:32611, exact affine transform, all-finite `[0,1]` array, footprint and known-catalogue masks. Its ZIP contains exactly those TIFF bytes. These are **local format checks**, not a DrivenData portal acceptance receipt.

The shared literal uniqueness routine reopens a hash-pinned, space-filling GEMSDOE24 lattice (SHA-256 `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`) and the registered WBG-C1 continuous raster. In that order, forward positive-pixel overlap within three Euclidean pixels is **99.8972%** and **100%**, so both exceed the binding 70% limit. Spearman is about −0.000491 and +0.013617; correlation is not the failing criterion. `scripts/review_wbg2.py --check` reproduces the measurements. Two witnesses are not a complete registry scan, but either STOP is decisive. The result is a literal protocol conflict with dense/space-filling support, **not proof that WBG-2 copied another artifact**. No exemption is authorized. No eligible pre-placement comparison was found.

The prior scan was one champion per site rather than every registry raster; it used a Manhattan neighborhood and a sampled rank statistic and applied an unauthorized chance-enrichment exemption. `src/wbg2/validate.py` also failed to enforce the full affine transform and tolerated outside-footprint NaNs under its inferred-mask convention. Those legacy APIs and the placement and nine-site audit entry points now fail closed. The generated card, Pages and README do not mark this candidate submit-ready. Original code and claims remain in `research/history/wbg2_20261027/` as explicitly superseded audit text.

The previous "four-pixel exclusion" was a four-connected Manhattan dilation, not a 400 m Euclidean exclusion. The audited TIFF has 813 dots within 400 m Euclidean distance of the mirrored catalogue and a minimum distance of sqrt(13) pixels. This does not by itself fail the separate exact mapped-fault mask; it invalidates the earlier exclusion claim.

## Evidence and forecast

No WBG-2 HOLDOUT-DTI satisfying whole-component buffered withholding, visible-only catalogue feature derivation, feature-specific leakage canaries and the shared pooled evaluator was found. The zero DTI against full visible catalogue does not measure hide-and-recover performance. The prior nine-row regression relied on unconfirmed historical values, duplicated/related artifacts and correlated predictors, and used an in-sample residual interval while extrapolating in positive-pixel budget. It has not been prospectively validated and is withdrawn. No leaderboard forecast or 95% prediction interval is justified. USER-REPORTED GEMSDOE32 B2 0.2778 versus parent 0.2600 remains without file-linked organizer receipts. See `docs/research/wbg2-why-02778.md` for the strictly measured deletion-only ancestry and the limits of the false-positive explanation.

The 19 cached band hashes match the pinned owner mirror after restoring the public 418,912,844-byte raster. Mirror integrity is not authentication that the organizer distributed those bytes, and physical units/band semantics remain unresolved.

## Sources retrieved or checked

| Source | What is confirmed | What remains uncertain |
|---|---|---|
| [DrivenData overview](https://www.drivendata.org/competitions/306/competition-doe-gems/) | Initial private and final expert-expanded labels; the same selected submission is evaluated twice; competition end 3 December 2026 23:59 UTC. | Account allowance, project scores and receipts are login-gated. |
| [Problem and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Fault-mapping target; new-fault initial evaluation; 300 m triangular kernel, α=.2, β=.8; one float32 band, UTM 11N, 100 m and values `[0,1]`; reference file geometry. | The official text asks for null/NaN beyond bounds. The local conservative all-finite exterior responds to the reported range rejection; its acceptance by the portal is unverified. |
| [Official rules PDF, §§3.2–3.6](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Up to three prediction submissions per week as website specifies; one final choice for both rounds; finalist code/data reproducibility and AI-use disclosure requirements. | Three is the published limit, not proof of remaining account slots. |
| [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | A direct official-page retrieval on 2026-10-27 showed rank-one public value **0.4544**. | A public rank is not a receipt for a repository artifact, and may change. Scheduled feeds keep dated observations when refresh fails. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE INGENIOUS](https://gdr.openei.org/submissions/1391) | Public survey/data catalogues and respective CC0 and CC BY 4.0 metadata are available. | The independent original data bytes, coverage, resampling and license compliance of each owner-derived feature still require verification. |
| [USGS MT conductance maps DOI 10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU) | Published depth-integrated intervals are 2–12, 12–20, 20–50, 50–90 and 90–200 km. | Prior proposed `~0.3, 3, 8 km` slice descriptions were wrong for this release; local download and coverage were not verified. |
| [USGS slip/dilation tendency](https://www.usgs.gov/data/shapefile-slip-tendency-and-dilation-tendency-calculated-quaternary-faults-great-basin) | It derives from a public Quaternary fault database; CC0 metadata. | Catalogue-derived attributes can leak withheld faults; derive any such features from visible faults separately in each fold. |
| [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) | Free access/use of 3DEP products. | Raw local DEM tiles and owner-derived lidar processing have not been independently reproduced here. |
| [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) | Official baseline code is public at the verified immutable commit. | It is not a validated result for this project or a reason to ignore the user’s separate lane and uniqueness rules. |

The previously named ScienceBase item `5fb70a0ad34eb413d5e14873` and USGS publication `70247315` returned not found; neither is treated as verified. Direct shell requests to non-allowlisted domains failed; retrieved webpage text came through `fetch_page`. Login-gated data, organizer receipts, raw external binaries, dataset-wide license checks, and hidden labels were not accessed.

## Next steps (separate authorization required)

1. Clarify the missing assigned single-method paragraph and the practical contradiction between the literal 70% gate and space-filling or continuous registry layers; do not waive or work around the STOP privately.
2. Independently verify official input provenance/band descriptions, complete the authorized registry scope and freeze an identically evaluated current-best comparison.
3. Only then preregister one genuinely different lane with named mimic; run per-feature canaries, visible-only buffered segment holdout, paired bootstrap and untouched confirmation using the shared tools. A fresh surface must clear the literal registry gate **before** placement; final dots must clear it again.
4. Reopen and validate exact TIFF/ZIP bytes, then use a distinct selector step to decide whether to spend a slot. Preserve all previous negative evidence. Disclose AI use as the official rules require.
