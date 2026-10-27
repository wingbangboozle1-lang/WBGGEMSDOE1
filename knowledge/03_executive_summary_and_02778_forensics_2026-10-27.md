# WBG-S2 research audit — DO NOT SUBMIT

The parallel run produced three experiments and this research TIFF. This integration did not
retrain, place dots, select a weekly slot or submit. **WBG-S2 is negative and is not eligible
for a selector**. Its final forward overlap is **99.5538%** with pinned r13 and **100%** with
WBG-C1; both exceed 70%. The pre-placement Spearman sample is not the full literal overlap gate.
See [the independent forensic audit](../evidence/wbg_s2/safety_review_20261027.json) and
[run card](../evidence/wbg_s2/run_card.json). Local all-finite, range and grid checks pass;
that is not proof of portal acceptance and does not resolve the prior range error.

The parallel run reports **HOLDOUT-DTI 0.183594** (95% CI [0.170313, 0.196956],
`gems-segment-pooled-v1`, 60,988 positives) and **0.147773** (95% CI [0.128077, 0.167791],
`gems57-pooled-hide-v2`, 11,330 positives). These results were not independently replayed
here; arm selection used these holdouts and untouched confirmation has not been established.
They are not organizer scores or leaderboard forecasts. Input hashes are owner-mirrored, not
authenticated organizer downloads. The original report, source and card are retained in
`research/history/wbg_s2_20261027/` as historical, non-authoritative records.

## Peer-specific diagnostics (not overall uniqueness clearance)

| Site | File reported by the parallel run | Holdout reported | Historical live claim | Decision / scope |
|---|---|---|---|---|
| WBGGEMSDOE1 (This Repo · WBG-S2 EXP-3) | `docs/downloads/wbggemsdoe1-wbg-s2-exp3-mksf-vierbeincoulomb-20261027-e9b4a3c09065-zeros.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); HOLDOUT-DTI 0.183594 (95% CI [0.170313, 0.196956], gems-segment-pooled-v1, n=60,988) <br> HOLDOUT-DTI 0.147773 (95% CI [0.128077, 0.167791], gems57-pooled-hide-v2, n=11,330) | NONE (0 competition slots spent; never inferred or projected from holdout) | RESEARCH DOWNLOAD ONLY · DO NOT SUBMIT · NO SELECTOR ELIGIBILITY |
| GEMSDOE24 | `docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif (latest) / gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif (prior)` | PARALLEL-REPORTED (some peer metadata may be incomplete); HOLDOUT-DTI 0.166060 (95% CI [0.151839, 0.179725], gems-segment-pooled-v1, n=60,988; S3DEP1) <br> HOLDOUT-DTI 0.163792 (DPRF1) | Historical H24-0 mirror: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2477 (100% H19-5 clone). Oct 26 gvc1: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0859. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| GEMSDOE25 | `docs/downloads/gems25-h74-rmps-subsurf-catfree-b2-37654-20261026-3751606e1ce5-zeros.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); HOLDOUT-DTI 0.039060 (95% CI [0.02561, 0.05635], subsurface-only H74) <br> H73-PM: HOLDOUT-DTI 0.0954 | Historical D2.8: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2600 (100% identical dot set to GEMSDOE30). Oct 26 h66: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0742. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| GEMSDOE27 | `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); HOLDOUT-DTI 0.143678 (95% CI [0.130198, 0.157302], 24-block holdout, n=76,120) | Oct 26 H31-1: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2250 (highest Oct 26 live ML/hybrid submission). Historical H27-5: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2449. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| GEMSDOE28 | `NONE generated in S22 (stopped on pre-placement surface Spearman 0.9036); prior S21: gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); S22: HOLDOUT-DTI 0.095452 (surface stopped, no dots) <br> S21: HOLDOUT-DTI 0.1038 | Historical H24-2-q990: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2710 (95.4% H19-5 family overlap). Oct 26 S21 PU-HGB: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0206. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| GEMSDOE30 | `docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); HOLDOUT-DTI 0.158160 (95% CI [0.14502, 0.17142], gems-segment-pooled-v1, n=60,988) | Historical D2.8: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2600 (100% clone of GEMSDOE25). Oct 26 MSDB1: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.1462. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| GEMSDOE31 | `docs/downloads/gemsdoe31-h31x-piedmont-junction-37654-20261026-5a956da9-zeros.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); HOLDOUT-DTI 0.166100 (95% CI [0.1465, 0.1859], 8-block spatial CV, n=76,120) | Historical union-b-p060: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2708 (93.2% H19-5 family overlap). Oct 26 H31-A: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0882. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| GEMSDOE32 | `docs/downloads/gemsdoe32-h47-ldgi-dualhorizon-corridor-37654-20261026T230609Z-0eb8a25c-zeros.tif (latest) / h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif (historical 0.2778)` | PARALLEL-REPORTED (some peer metadata may be incomplete); H47-1-LDGI: HOLDOUT-DTI 0.119765 (95% CI [0.100357, 0.140466], gems57-pooled-hide-v2, n=11,330) | Historical H33-2-B2 (`e5eb6e7e`): USER-REPORTED / PEER-REPO-CLAIMED 0.2778 (NOT ORGANIZER-CONFIRMED by this repo; recorded in peer file `GEMSDOE32/registry/submissions/sub-20261004T234342Z-h33-b2.json`). Oct 26 H38-G1: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.1456. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| GEMSDOE33 | `docs/downloads/gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); S33-SEISDIL: HOLDOUT-DTI 0.044577 (block CV) <br> G33-COHERENCE: HOLDOUT-DTI 0.025120 (7,949 dots) | Historical H24-1-d2.6: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2632 (97.5% H19-5 overlap). Oct 26 s33-seisdil: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0963. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| GEMSDOE36 | `docs/downloads/gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); HOLDOUT-DTI 0.170100 (95% CI [0.15660, 0.18440], gems-segment-pooled-v1, n=60,988) | Historical H36-4: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2750 (86.7% H33-B2 overlap). Oct 26 KPL-36 EXP-3: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.1647. | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |
| KANLERGEMSDOE2 (External Peer Benchmark) | `docs/downloads/kanlergemsdoe2-kg2-mghv-exp-1-37654-20261026-f5a469e94b14-zeros.tif` | PARALLEL-REPORTED (some peer metadata may be incomplete); HOLDOUT-DTI 0.177056 (95% CI [0.163689, 0.190497], gems-segment-pooled-v1, n=60,988) | NONE reported | RESEARCH COMPARISON ONLY; no full registry or submission clearance established |


## Why the GEMSDOE32 0.2778 is not proof of a new score

`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` and 0.2778 are owner-reported;
we have no organizer receipt binding the score to these bytes. D2.8, B1 and B2 progressively
reduce 44,090, 40,199 and 37,654 predicted dots. Sparse kernel coverage and avoiding
low-credit predictions are plausible explanations, not established causal facts: hidden
labels and exact per-dot contributions are unavailable. A genuinely unique model might
outperform it, but there is no verified forecast, no proven submission, and no copy or
retuning of a stopped lane is allowed. See
[the corrected analysis](../docs/research/wbg2-why-02778.md) and
[future hypotheses](../docs/research/future-hypotheses-20261027.md).
