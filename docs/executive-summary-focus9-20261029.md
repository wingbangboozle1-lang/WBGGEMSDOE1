# Executive summary - nine focus sites (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36)

**Generated 2026-10-29 by `scripts/build_focus9_summary_20261029.py` from committed receipts.**

## OK TO SUBMIT?  **NO - for every file in this table.**

- Every focus-site score is OWNER-REPORTED. No DrivenData submission receipt is available here.
- No focus-site file is unique: each one overlaps another focus-site file by 97.6% to 100% in its 3 px dot test (gate: 70%).
- The one new candidate from this repo had a leaky holdout score. The leak-corrected score is 0.0069, which is below the 0.1661 benchmark.
- Local format checks are not organizer acceptance. Nothing here is a prediction of leaderboard placement.

## Summary table

| Site | File to download | Owner-reported score | Estimated leaderboard score | Unique vs other focus sites? | Decision |
|---|---|---:|---|---|---|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | 0.2477 | Not estimable | NO (overlap 1.0000) | **DO NOT SUBMIT** |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/e40b9b5e3871cb34d138f586bde97f5099658d01/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | 0.26 | Not estimable | NO (overlap 1.0000) | **DO NOT SUBMIT** |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/927322eadbde56be42ae129ccdfb9b37540d8e60/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | 0.2449 | Not estimable | NO (overlap 0.9802) | **DO NOT SUBMIT** |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/e6321461066f89080e3b1bb670d3951ab20d3638/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | 0.271 | Not estimable | NO (overlap 1.0000) | **DO NOT SUBMIT** |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/760af3005dd40b9f36d8fef97d6dc384fd9f2a2f/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.26 | Not estimable | NO (overlap 1.0000) | **DO NOT SUBMIT** |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/597b04cd1afb65d1ebbe3e9417fd952be48e3d74/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | 0.2708 | Not estimable | NO (overlap 1.0000) | **DO NOT SUBMIT** |
| GEMSDOE32 | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/5fc7792c5887735ecd3aa9a612787da588a7bf2c/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | 0.2778 | Not estimable | NO (overlap 1.0000) | **DO NOT SUBMIT** |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/f618cc54773bd9b4d6c2b3ebf78103a05cc10cb6/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 | Not estimable | NO (overlap 0.9971) | **DO NOT SUBMIT** |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/c5a8ae7da3bd2fcff5aa5855afd44c7a3346c16/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.275 | Not estimable | NO (overlap 0.9758) | **DO NOT SUBMIT** |
| WBGGEMSDOE1 (this repo) | [WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/downloads/WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif) | none | Not estimable (leak-corrected HOLDOUT-DTI 0.0069 vs benchmark 0.1661) | Not fully checked | **DO NOT SUBMIT (download = research only)** |

Owner-reported values come from `docs/data/executive_summary_20261028.json`. Overlap values are the shared 3 px test from that file.

## Best historical file (GEMSDOE32 B2 = 0.2778): why it scored highest

- It is an exact subset of its parent (the GEMSDOE25 dotted-h19-5-d2-8 file, 0.2600, sha256 3e78737f...): 37,654 dots kept, 6,436 removed, 0 added.
- All 6,436 removed dots lie within 2 px (200 m) of the public catalogue (`docs/data/h33-b2-forensics.json`).
- Mechanism (plausible, not proven): removing dots on or next to mapped faults that earn no credit reduces the false-positive term of the distance-weighted Tversky index (alpha 0.2), which raises the score.
- The local holdout proxy does **not** reproduce this: B2 scores HOLDOUT-DTI 0.0044 (`evidence/holdout_proxy_portfolio.json`). The proxy is leakage-inflated and rank-unreliable (Spearman 0.144). Irregularity: the holdout evaluator cannot be used to rank files against the leaderboard.
- Scale of the gain: +0.0178 (0.2600 to 0.2778), from one precision-cleanup step.

## Leakage re-check of the one new candidate (Experiment 1 of the budget)

- Archived file (full-catalogue placement): HOLDOUT-DTI 0.4657, CI95 [0.4563, 0.4748], n=60161. This reproduces the original run card.
- Same method rebuilt per fold from visible faults only: HOLDOUT-DTI 0.0069, n=60161. CI not recomputed (fold-level pooling).
- Leakage canary (single feature, AUC on holdout): distance to visible catalogue alone 0.829; emission surface alone 0.378. Both are below the 0.90 leakage threshold. The 0.4657 score is leakage, not canary failure.
- Verdict: **NEGATIVE**. The earlier 0.4657 claim is retracted.
- Receipt: `evidence/per_fold_recheck_blind_adjacency.json`; script: `scripts/per_fold_holdout_recheck.py`.

## Irregularities flagged for review

1. Leaderboard numbers conflict. The user quotes 0.4413 and 0.3195. The public page on 2026-10-29 shows #1 at 0.4544 and #2 at 0.3916 (drivendata leaderboard). Neither is a project-file receipt.
2. Owner-reported focus-site values cannot be checked against an organizer receipt. They stay OWNER-REPORTED.
3. The `[0, 1]` portal error (user report) is still unexplained. Local writers use finite values in [0,1] with zeros outside the footprint. The official rules describe a single-band GeoTIFF but do not state the nodata convention in the text fetched here (`docs.nlr.gov/docs/fy26osti/96647.pdf`).
4. The holdout evaluator and the leaderboard disagree on B2 (proxy 0.0044 vs reported 0.2778).
5. The blind-adjacency run card and its note still call the file 'research' with 0.4657; that number is leaky. See the leakage section above.

## Ranked next hypotheses (untested; none is validated)

Expected improvement and cost are qualitative. Each candidate must pass the per-fold holdout (point estimate above 0.1661 with a positive CI) before any slot decision.

1. **Analytic-signal magnetic edges, catalogue-free, per-fold** - layers: the stack already holds the total magnetic intensity (band 14), horizontal gradient (band 3), vertical gradient (band 9) and tilt/total curvature (band 6). Signature: analytic-signal amplitude ridges, a combination of those bands. Novelty: LOW, because the same information is already inside the stack and tilt is already implemented in the repo (6 files). Cost: low. Mimic: magnetized dikes and intrusions.
2. **Conductivity lineaments with a new external source** - layer: band 17 (conductivity surface) is already in the stack, so this is only new if a different, free, official conductivity dataset is added. The source is NOT verified in this session. Do not implement until a free official source is confirmed. Cost: high. Mimic: clay-rich basin fill.
3. **Leakage-free supervised ranker** - layer: the 19-band stack, trained only on visible folds. Cost: medium. Novelty: low, because ML lanes already exist (`src/wbg4/model.py`, `src/wbggems2/mksf_model.py`). Use only as a per-fold baseline.

## Verification notes

- Restored inputs: `scripts/restore_data.py` verified hashes for the core rasters (`evidence/data_restore.json`). This is owner-mirror integrity, not organizer-origin authentication.
- Tests: 232 existing tests plus 5 new leakage-receipt tests pass locally (237 total, `pytest`).
- Sources: official rules `https://docs.nlr.gov/docs/fy26osti/96647.pdf`; reference solution `https://github.com/drivendataorg/gems-prize-reference-solution` (writes float predictions on the label grid, no NaN padding); leaderboard `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/`.

## Machine-readable card

`docs/data/focus9_summary_20261029.json` (schema `gemsdoe1-focus9-summary-20261029-v1`).
