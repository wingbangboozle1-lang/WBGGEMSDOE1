# Normalized standing owner request — 2026-10-26

This is a structured preservation of the operative request. It is not evidence that every URL or owner-reported score was independently verified.

## Objective

Place as high as possible in the DOE GEMS fault-mapping competition while protecting weekly slots. Focus first on the best artifacts from GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Produce an executive comparison that names the exact file, available score evidence, uniqueness, and download/submit decision for each site.

## Highest urgency

Generate a genuinely unique GeoTIFF rather than renaming, perturbing or copying an old prediction. The first screen of the site must make `DOWNLOAD` and `SUBMIT` status obvious. A machine validator—not a human inspector—must decide format and release gates. Give the file a unique name and a useful note no longer than 140 characters.

## Scientific workflow

1. Review the repository and prior next steps.
2. Before implementation, rank 3–5 untried hypotheses. Name layers, transform/signature, missing-fault rationale, non-fault mimic, novelty relative to prior code, expected DTI direction and cost.
3. Verify that required external data are free, official and obtainable before marking a candidate viable.
4. Execute only the top preregistered lane, up to three experiments or two hours.
5. Use whole-segment spatial hide-and-recover with a buffer, visible-only catalogue features, exact visible-fault masking and pooled distance-weighted Tversky (α=0.2, β=0.8, 300 m triangular kernel).
6. Test every actual feature alone; AUC above 0.90 is suspected leakage.
7. Compare the score surface before placement and final dots after placement to the registry. Stop on `|rho| > 0.90` or directed 3-pixel overlap `> 0.70` against one registry raster.
8. Never spend a slot unless the candidate beats the current comparable holdout best. Slot selection and portal upload are separate.

## Evidence vocabulary

- `HOLDOUT-DTI`: must include evaluator version, withheld-positive count and 95% CI.
- `ORGANIZER-CONFIRMED`: only with an artifact-linked submission-page receipt.
- `OWNER-REPORTED / UNVERIFIED`: public text or user prompt without such a receipt.
- `MODEL PROJECTION`: may be discussed only as a projection, never as a score. This repository chooses not to publish a numeric leaderboard projection without a calibrated receipt set.

## Required run card

One JSON record must contain hypothesis, mechanism, named non-fault mimic, holdout and CI, registry correlation/overlap, exact raster SHA-256, validator output, submission name and <=140-character note, and `promote` or `negative`. Negative results remain deliverables.

## Product requirements

- GitHub Pages-compatible static site.
- Executive summary and download/submit status first.
- Dedicated contest-submission guide.
- Nine-site comparison table.
- Strict single-band GeoTIFF validation: CRS, shape, transform, dtype, finite values, `[0,1]`, and no NaN inside the footprint.
- All-finite `-zeros.tif` recommended for the reported portal range error; NaN-outside files must not be recommended to this portal without organizer confirmation.
- Official/manual-review source links, immutable GitHub pins and hashes, explicit irregularities and limitations.
- Automated source-refresh workflow that is clearly a repository feed, not a live leaderboard.
- Preserve this brief in the repository and reread it each session.
- Three passes: implement/verify; review/fix bugs and edge cases; recheck requirements and improve quality.
- Open a pull request from the fixed Arena branch, merge it after checks, and report remaining blockers honestly.

## Focus-site historical claims supplied by owner

These numbers do not become organizer-confirmed by repetition.

| Site | Historical artifact | Owner-reported value |
|---|---|---:|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 |

The user also supplied newer claims for some sites and conflicting leaderboard highs. Those belong in the generated evidence snapshot with provenance, not in scientific score comparisons.

## Access limits

The sandbox permits outbound traffic only to GitHub and package registries. DrivenData login data cannot be downloaded directly. Pinned owner mirrors can be integrity-checked but are not organizer authentication. Do not request passwords, tokens or 2FA. No automatic competition upload is implemented.
