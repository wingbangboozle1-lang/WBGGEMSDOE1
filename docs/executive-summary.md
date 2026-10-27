# Executive summary — updated 27 October 2026

## DOWNLOAD: YES (research/audit only). SUBMIT: NO.

[Download the best newly generated unique TIFF](downloads/wbggemsdoe1-tasc-label-free-physical-response-20261027-c3464cfa30d0-zeros.tif) · [one-TIFF ZIP](downloads/wbggemsdoe1-tasc-label-free-physical-response-20261027-c3464cfa30d0-zeros.zip) · [submission decision page](submission-decision.html) · [new run card](data/run-card-tasc-best-arm-20261027.json)

> A new single-band float32 GeoTIFF was generated and reopened: values are finite in [0,1], CRS/shape/transform match, outside-footprint values are zero, and known catalogue faults are excluded. It is **NOT** cleared for a weekly DrivenData slot. Two new files were produced; neither beat the frozen HOLDOUT-DTI 0.166060 current-best point estimate, neither passed the literal all-entry 3 px registry gate, and zero competition slots were used.

## The decision table

| File to download | Measured evidence | Estimate (NOT a score) | Unique? | OK to submit? |
|---|---|---|---|---|
| [wbggemsdoe1-tasc-label-free-physical-response-20261027-c3464cfa30d0-zeros.tif](downloads/wbggemsdoe1-tasc-label-free-physical-response-20261027-c3464cfa30d0-zeros.tif) — NEW 2026-10-27 · best-scoring arm of the frozen TASC screen | HOLDOUT-DTI 0.061528, 95% CI [0.049811, 0.073808] | **0.0716** LLI projection ±0.0353; not an organizer score | competing-method unique yes; literal lattice gate FAIL | **NO** |
| [wbggemsdoe1-tasc-tip-strain-corridor-20261027-f3270cad4a7f-zeros.tif](downloads/wbggemsdoe1-tasc-tip-strain-corridor-20261027-f3270cad4a7f-zeros.tif) — NEW 2026-10-27 · preregistered primary TASC candidate | HOLDOUT-DTI 0.001825, 95% CI [0.000431, 0.003717] | **0.0000** LLI projection ±0.0353; not an organizer score | competing-method unique yes; literal lattice gate FAIL | **NO** |
| [wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif](downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif) — INHERITED 2026-10-26 · strongest unique research TIFF in this repository | HOLDOUT-DTI 0.123310, 95% CI [0.108921, 0.137557] | **0.1898** LLI projection ±0.0353; not an organizer score | competing-method unique yes; literal lattice gate FAIL | **NO** |

The inherited WBG-H1 EXP-3 TIFF remains the strongest unique research file in this repository (HOLDOUT-DTI 0.123310, LLI projection 0.1898), but it is also negative and was not generated in this session. The new TASC primary arm failed because hide-and-recover removes visible catalogue faults from each test quadrant, leaving a visible-tip-derived corridor with almost no support there.

## Nine focus sites — best file, estimate and uniqueness

Historical values are **USER-REPORTED / NOT ORGANIZER-CONFIRMED**. LLI numbers are empirical projections on 118 user-reported historical rasters (LOO MAE 0.0353), **not organizer scores**.

| Site / lineage | File to download (audit only) | Estimate | Unique? | OK to submit? |
|---|---|---|---|---|
| GEMSDOE32 — B2 nested-pruning benchmark | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/400b60d4a6d99f425ee90504e6c4552227556dd1/docs/downloads/gemsdoe32-h47-lli-unique-coupling-49231-20261026T230000Z-33464ce2-zeros.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/07806249f4ed3efe70b4fbf866183c32392b7853/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif?raw=1) | USER-REPORTED 0.2778 historical / **0.1328** LLI projection ±0.0353 latest | yes vs sparse peers; max 3 px overlap 65.0% | **NO** |
| GEMSDOE36 — Anderson-labelled augmentation | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/79ddf4aa6fd5fa93887345f4bffeb6edd9d76401/docs/downloads/gemsdoe36-gvsc36-exp3-20261026-5fb822bdfb60-zeros.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/05979971df4775aadad34ae6749b0a7ac56d7832/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif?raw=1) | USER-REPORTED 0.2750 historical / **0.1905** LLI projection ±0.0353 latest | yes vs sparse peers; max 3 px overlap 69.3% | **NO** |
| GEMSDOE28 — Rung30 / B1-family variant | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/2c839d10f57ec9b074829e93c84bc39935f52896/docs/downloads/gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/2c839d10f57ec9b074829e93c84bc39935f52896/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif?raw=1) | USER-REPORTED 0.2710 historical / **0.0407** LLI projection ±0.0353 latest | no vs sparse peers; max 3 px overlap 90.4% | **NO** |
| GEMSDOE31 — Catalogue-distance B1 pruning | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/e14b466b88601149e30ed8decb2fa753ca040beb/docs/downloads/gemsdoe31-h31y-kinpied-37654-20261026-46a5b6c3-zeros.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/776bf4668a8c10631908c9bba9443a8f11ce5036/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif?raw=1) | USER-REPORTED 0.2708 historical / **0.0738** LLI projection ±0.0353 latest | no vs sparse peers; max 3 px overlap 91.3% | **NO** |
| GEMSDOE33 — Analog-tip / stepover extension | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/efa438d3104893c3e8aedf3817ac22167b1c681a/docs/downloads/gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/1d99d73fe14d9a87126ffca2db52c69336d6099b/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif?raw=1) | USER-REPORTED 0.2632 historical / **0.1582** LLI projection ±0.0353 latest | yes vs sparse peers; max 3 px overlap 69.2% | **NO** |
| GEMSDOE25 — D2.8 parent field | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/b9dc627b767b052ca6963e175ef43ad2d0831ebd/docs/downloads/gems25-h73-pm-deapron-sapd2-8-k3p0-20261026-1b7533ebb62b-zeros.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/af2b6f2543e5422a7e917638b70e038e6fd91cad/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif?raw=1) | USER-REPORTED 0.2600 historical / **0.1437** LLI projection ±0.0353 latest | yes vs sparse peers; max 3 px overlap 67.7% | **NO** |
| GEMSDOE30 — Repackaged D2.8 dots | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/9c0d637c0171407196b61b780444bc772ce75438/docs/research/2026-10-26-gdx/gems30-GDX1-44090-20261026-2992ee3619f5.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/9c0d637c0171407196b61b780444bc772ce75438/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif?raw=1) | USER-REPORTED 0.2600 historical / **0.1368** LLI projection ±0.0353 latest | yes vs sparse peers; max 3 px overlap 57.0% | **NO** |
| GEMSDOE24 — Sparse ridge thinning | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/a433b430b74b813a9118ebd4ec438b12cbc69f46/docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/7ab1c8f77f0b4b8644e3929403a0dab65838b008/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif?raw=1) | USER-REPORTED 0.2477 historical / **0.1866** LLI projection ±0.0353 latest | yes vs sparse peers; max 3 px overlap 62.9% | **NO** |
| GEMSDOE27 — Topographic gap closure | [latest candidate](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/21687996529d4e3bcb83e7d8ac56fa29864acf97/docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif) · [historical champion](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/bef7ae8e8f63b69d299c9214c75988c8f5055f9c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif?raw=1) | USER-REPORTED 0.2449 historical / **0.1778** LLI projection ±0.0353 latest | yes vs sparse peers; max 3 px overlap 69.0% | **NO** |

## Why GEMSDOE32 leads the supplied historical records

Exact raster identities: D2.8 44,090 dots → remove 3,891 within 100 m of the catalogue → B1 40,199 → remove 2,545 more within 200 m → B2 37,654. GEMSDOE25 and GEMSDOE30 have identical decoded predictions. GEMSDOE36 contains all B2 pixels plus 1,200 additions. Sparse support and low-marginal-credit pruning can reduce redundant false-positive cost under the official max-cover metric. Hidden labels are unavailable, so that mechanism is plausible, not a proved causal account. A 200 m exclusion is not an organizer rule.

GEMSDOE32's supplied 0.2778 is USER-REPORTED, not a verified file receipt. The direct official public leaderboard observation on 2026-10-27 was 0.4544; it is not a result for any project TIFF. The prompt's 0.4413 and 0.3195 targets are stale/inconsistent.

## Frozen 26 October 2026 WBG-C1 control (kept for audit)

wbg-c1-commutator-research-surface-20261026-acea88448272.tif: HOLDOUT-DTI 0.014045, 95% CI [0.011831, 0.016396], paired delta -0.000101 (95% CI [-0.000232, +0.000030]). Continuous unplaced confidence surface, not a matched-budget dotted submission. Verdict: negative.

## Five preregistered 2026-10-27 hypotheses

1. TASC tip-aligned strain-transfer corridor — executed, negative (visible-tip support collapses under hide-and-recover).
2. PCE1 potential-field phase congruency — label-free, viable with the local 19-band cache; next candidate.
3. CLR1 radiometric compositional closure residual — viable with restored GeoDAWN-derived bands.
4. DIFF1 diffusion-degraded scarp shape invariant — needs raw 3DEP 1 m/10 m DEM profiles; not bulk-obtainable in this sandbox.
5. MT3D depth-persistent conductivity edge — needs USGS 3-D MT conductance slices; official source verified, bulk host outside allowlist.

[Full ranked hypotheses, official sources and data obtainability](research/03_ranked_hypotheses_2026-10-27.md). No numerical improvement was forecast.

## Site-by-site findings

### GEMSDOE32 — B2 nested-pruning benchmark
The 37,654-pixel supplied historical leader is exactly D2.8 restricted to catalogue distance >2 pixels. It removes a further 2,545 pixels from B1. This identity is verified from the actual files, not inferred from their names. It is the highest USER-REPORTED historical value among these nine supplied records, not an independently confirmed score.
Inspected SHA-256: `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE32/tree/07806249f4ed3efe70b4fbf866183c32392b7853).

### GEMSDOE36 — Anderson-labelled augmentation
Every GEMSDOE32 B2 dot is retained, with 1,200 additions, for 38,854 positives. The filename includes PINN, but the measured set relation does not establish that a new physics-informed neural network generated this particular artifact. The supplied value is below the B2 parent's reported value.
Inspected SHA-256: `e15891020b9c57056ac7fa874a5e506fbd6ed9314a4ea8e73af0753887a3708a`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE36/tree/05979971df4775aadad34ae6749b0a7ac56d7832).

### GEMSDOE28 — Rung30 / B1-family variant
Rung30 has 37,660 positive pixels and the largest supplied historical value among the four listed GEMSDOE28 variants. It is not a new independent field relative to the ridge-thinning family. The earlier SOLO variant is pixel-identical to GEMSDOE31's base.
Inspected SHA-256: `5556aa1438fd67376b60d5ffc99228ec09dcc11a8408298a743ccb88d6163641`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE28/tree/2c839d10f57ec9b074829e93c84bc39935f52896).

### GEMSDOE31 — Catalogue-distance B1 pruning
The 40,199-pixel field is exactly D2.8 with dots at distance ≤1 pixel from the public catalogue removed: 3,891 removals. It reproduces GEMSDOE28's SOLO variant. Pixel-exact masking is an evaluation rule; this additional distance buffer is a model choice.
Inspected SHA-256: `07b6db440535404bb41ec8ddc797713e200d308e3da35937393efde5eb84bc40`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE31/tree/776bf4668a8c10631908c9bba9443a8f11ce5036).

### GEMSDOE33 — Analog-tip / stepover extension
The historical analog-tip file contains 41,865 positive pixels and remains heavily overlapping with the inherited family. The supplied value is below the unextended GEMSDOE31 base's reported value, so extra structural plausibility did not by itself establish better scoring. The actual source must be consulted before attributing any algorithmic causality.
Inspected SHA-256: `87f857d505e23247e991ccfab2cbe9f49a04df4f9c8028dce7ea261554690757`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE33/tree/1d99d73fe14d9a87126ffca2db52c69336d6099b).

### GEMSDOE25 — D2.8 parent field
The 44,090-pixel D2.8 field has exactly the same decoded predictions as GEMSDOE30's historical champion despite different file encodings. Its name alone is not a verified physical separation parameter.
Inspected SHA-256: `91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE25/tree/af2b6f2543e5422a7e917638b70e038e6fd91cad).

### GEMSDOE30 — Repackaged D2.8 dots
Its 44,090 positive pixels match GEMSDOE25 D2.8 exactly. Different TIFF bytes or outside-footprint encoding do not constitute different predictions. It must not be copied as a unique new submission.
Inspected SHA-256: `8cf893ead5667df21d3288a9968c35fd5385c425b029d82ee71d311715b129fd`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE30/tree/9c0d637c0171407196b61b780444bc772ce75438).

### GEMSDOE24 — Sparse ridge thinning
The historical D1.5 file contains 60,069 positive pixels. It is part of the inherited H19-5 ridge-thinning family, not an independent new geological detector. Later user-reported negative results are not improvements over this supplied historical value.
Inspected SHA-256: `68d0e2e4fcc594f9a23f56c44b885fee733d026d39be55e18ad2a07289525310`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE24/tree/7ab1c8f77f0b4b8644e3929403a0dab65838b008).

### GEMSDOE27 — Topographic gap closure
The supplied historical leader contains 61,328 positive pixels, 1,259 more than D1.5. Its lower user-reported value suggests that adding topographic bridges was not automatically beneficial; hidden labels are unavailable to establish a cause. The later H29 value in the prompt is also below this site's supplied historical leader.
Inspected SHA-256: `33003374335d84bf885f2d8f5e9dd4c57044c8ec58fa6a0d7fa581e8bc41c11d`. [Pinned source](https://github.com/buffedlizard55-lab/GEMSDOE27/tree/bef7ae8e8f63b69d299c9214c75988c8f5055f9c).

## Limitations and next actions

- No assigned single-method lane paragraph was supplied; TASC is provisional research.
- The retained spacing-5 calibration lattice makes the literal final-dot overlap gate unsatisfiable for any substantial new dot set; a protocol owner must resolve this.
- Core data and all 19 band-cache hashes match public owner mirrors, not an independently authenticated organizer-origin manifest.
- Literal band metadata are ambiguous. Do not claim physical units, heat, permeability or geothermal vent discovery from these numbers.
- Historical file scores lack organizer submission-page receipts. No hidden test labels or private-score access exists.
- The nine frozen snapshots are not the entire 92-site/competition registry. No global uniqueness is claimed.
- The current account allowance is unknown; the rules PDF's three-per-week limit is not proof of remaining allowance.
- Inherited WBG-H1 pages that mislabelled owner-reported values as ORGANIZER-CONFIRMED were corrected in this session.
- A future authorized lane needs a clean same-instrument current-best comparator, untouched confirmation, resolved registry policy and exact-artifact validation before a separate selector considers a slot.

[How to submit a future promoted file](how-to-submit.html) · [official sources and irregularities](evidence.html) · [full prompt](standing-prompt.md)

## Run cards

[2026-10-27 TASC primary](data/run-card-tasc-20261027.json) · [2026-10-27 best new arm](data/run-card-tasc-best-arm-20261027.json) · [frozen WBG-C1](data/run-card.json). All verdicts: **negative**.
