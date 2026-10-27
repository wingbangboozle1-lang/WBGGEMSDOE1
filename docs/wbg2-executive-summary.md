# WBG-2 — research artifact review

**DOWNLOAD: YES, research only. SUBMIT: NO.** The local format pass does not override the missing lane, missing pre-placement check, strict overlap STOP, absent HOLDOUT-DTI, or absent organizer receipt.

- Research TIFF: [`docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif`](downloads/wbg2-offcatalogue-density-36k-20261027.tif) (or [`wbg2-offcatalogue-density-36k-20261027.zip`](downloads/wbg2-offcatalogue-density-36k-20261027.zip)).
- SHA-256: `f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3`.
- Local format validation: **PASS**; one float32 band, EPSG:32611, shape 3730×3292, [0,1], no NaN, exact sample-template affine transform revalidated.
- HOLDOUT-DTI: **NOT MEASURED**; no evaluator version, withheld-positive count, or 95% CI.
- Organizer-confirmed score: **none**. Current leaderboard estimate: **unavailable**.
- Focus-nine pairwise audit: 9/9 exact artifacts; max forward overlap 0.1861; max sampled |ρ| 0.0095 (diagnostic only). This is not full-registry clearance.
- Partial local registry scan: 8 rasters; maximum literal forward 3 px overlap 1.0000 against WBG-C1 research surface. **STOP** under the no-exemption rule.
- Surface-before-placement check: **not recorded**. Method lane: **not authorized**.

## Why GEMSDOE32 B2 led the supplied focus-site results

GEMSDOE32 B2 is the highest supplied value, **USER-REPORTED 0.2778 / NOT ORGANIZER-CONFIRMED**. The stored raster lineage is D2.8 (44,090 dots) → B1 (40,199) → B2 (37,654), removing catalogue-near predictions at each step. Under a max-cover DTI, removing low-marginal-coverage predictions can reduce false-positive cost; this is consistent with the reported ordering but is not proven without hidden labels and a receipt. It does not establish a universal exclusion buffer.

Whether a genuinely unique artifact can beat 0.2778 is **unknown**. WBG-2 has no valid HOLDOUT-DTI and no defensible score estimate.

## Artifact mechanism and mimic

A Gaussian KDE of mapped-fault density (1.5 km) supplies the placement prior, with a 400 m catalogue exclusion and 36,000 scattered cells. This is a spatial prior, not a fault detector. Basin-fill depocentres and range-front alluvial aprons are named non-fault mimics.

The recorded PROXY-DTI against mapped catalogue faults is 0.0 by construction and is not a score. The former regression projection was withdrawn because it used unverified user reports, included duplicate prediction fields, had collinear predictors, and extrapolated beyond its fit domain.

## Three-pass review

1. **Audit:** found a false submit approval, an unauthorized chance-enrichment exception, a withdrawn projection, and no pre-placement surface gate.
2. **Correct:** reclassified the unchanged TIFF/ZIP as research-only; made score and eligibility fields fail closed; kept the focus-nine result explicitly scoped.
3. **Verify:** the exact TIFF and one-member ZIP passed the shared format validator; 146 repository tests, Ruff E9/F, Chromium 153 desktop/mobile checks for 10 pages, and all local CI validation commands passed. Download identities matched pinned hashes. GitHub Actions remains pending PR creation; none of these checks constitute organizer acceptance or global uniqueness clearance.

## Manual-review sources

- [DrivenData problem / metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/) · [DOE/NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [DOE GDR 1391](https://gdr.openei.org/submissions/1391) · [EPSG:32611](https://epsg.io/32611)

External sources and the competition portal were not freshly accessed in this review. No experiment, TIFF regeneration, upload, or slot use occurred.
