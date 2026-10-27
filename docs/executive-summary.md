# Executive summary — 27 October 2026 — Master Decision Table

**One-click answer: download [wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif](downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif) ([ZIP](downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.zip), SHA-256 `e46e4c175c5afceac148d0475a23808c3ae8bf6e5edad8faea919ed847b0d7dd`) — the only generated file that is both portal-valid ([0,1], no NaN) and registry-unique (64.49% ≤70%). WBG-C1 is a research surface that fails uniqueness (99.87%). All nine historical files are learning references — do not re-upload.**

## Master decision table — file to download · estimated score · unique?

| Priority | File to download | Measured evidence & estimated score (labeled) | Portal valid? | Unique vs 9 GEMSDOE? | OK to download & submit? |
|---|---|---|---|---|---|
| **★ RECOMMENDED — Generated dotted submission** | [wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif](downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif) (ZIP) — WBG-H1 / DPGF-1 EXP-3, 37,654 binary dots, DipShift+TFSDI+DualLiDAR+CELF300m | **HOLDOUT-DTI 0.123310**, 95% CI [0.108921, 0.137557], `gems-segment-pooled-v1`, 60,988 withheld positives — beats B0 0.103855 by +0.019455 on 4/4 folds. **LLI-PROJECTION 0.1898** ≈ [0.1545, 0.2251] ±1 MAE on n=118 organizer-confirmed rasters — NOT an organizer score. | **PASS · 10/10 gates** — 0 NaN/0 Inf across 12,279,160 cells, [0.0,1.0], outside=zero, EPSG:32611 3730×3292 | **PASS · unique** — Focus9 max 3 px forward overlap 64.49% ≤70%, \|ρ\|=0.0347 ≤0.90 | **YES — download** — technically submittable (no “[0,1]” error). Verdict `negative` per selector (trails DPRF1 0.1638_holdout) — not promoted as guaranteed to beat 0.2778. |
| Generated — research only | [wbg-c1-commutator-research-surface-20261026-acea88448272.tif](downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif) ([ZIP](downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.zip)) — WBG-C1, 5,106,385 px dense confidence | **HOLDOUT-DTI 0.014045**, 95% CI [0.011831,0.016396], `gems57-pooled-hide-v2`, 11,330 positives — Δ vs control -0.000101 (no gain). Estimated leaderboard: **Unavailable** (not dotted, not inferred). | **PASS · format only** — finite [0,0.88] ⊂[0,1], grid match, outside=zero | **FAIL · 99.87% >70%** — literal duplicate surface vs lattice, no final-dot clearance | **NO — research only** |
| Historical #1 — GEMSDOE32 B2 (highest historical claim) | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/07806249f4ed3efe70b4fbf866183c32392b7853/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif?raw=1) — 37,654 dots, SHA c55bafc47005… | **OWNER-REPORTED 0.2778** — Not ORGANIZER-CONFIRMED (no receipt binding bytes→score) | Historic · zeros-mode (no NaN exterior) | **No — family duplicate** — 100% of D2.8 family | **NO — do not copy** |
| Historical #2 — GEMSDOE36 anderson PINN | [gemsdoe36 … anderson … 9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/05979971df4775aadad34ae6749b0a7ac56d7832/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif?raw=1) — 38,854 dots (B2+1,200) | **OWNER-REPORTED 0.2750** | Historic zeros-mode | **No — contains all B2 dots** | **NO — do not copy** |
| Historical #3 — GEMSDOE28 rung30 | [gems28 … rung30 … b531dae0a36f-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/2c839d10f57ec9b074829e93c84bc39935f52896/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif?raw=1) — 37,660 dots | **OWNER-REPORTED 0.2710** | **FAIL · exterior NaN** — triggers “[0,1]” portal error | No — family | **NO — do not copy** |
| Historical #4 — GEMSDOE31 B1 solo | [gemsdoe31 … solo … 8acb75e1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/776bf4668a8c10631908c9bba9443a8f11ce5036/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif?raw=1) — 40,199 dots, D2.8 minus 3,891 ≤100 m | **OWNER-REPORTED 0.2708** | **FAIL · NaN** | No — family | **NO** |
| Historical #5 — GEMSDOE33 analog-tip | [GEMSDOE33 … analog-tip … cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/1d99d73fe14d9a87126ffca2db52c69336d6099b/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif?raw=1) — 41,865 dots | **OWNER-REPORTED 0.2632** | Check needed | No — 99.7% vs G27 | **NO** |
| Historical #6a — GEMSDOE25 D2.8 parent | [gems25 … d2-8 … e56ea318af89-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/af2b6f2543e5422a7e917638b70e038e6fd91cad/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif?raw=1) — 44,090 dots | **OWNER-REPORTED 0.2600** | **FAIL · NaN** | **No — identical to G30** | **NO** |
| Historical #6b — GEMSDOE30 repackaged D2.8 | [gemsdoe30 … poisson300m … 91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/9c0d637c0171407196b61b780444bc772ce75438/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif?raw=1) — 44,090 dots, identical to G25 | **OWNER-REPORTED 0.2600** | **FAIL · NaN** | **No — identical to G25** | **NO** |
| Historical #8 — GEMSDOE24 D1.5 | [gems24 … d1-5 … 989f59505db1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/7ab1c8f77f0b4b8644e3929403a0dab65838b008/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif?raw=1) — 60,069 dots | **OWNER-REPORTED 0.2477** | **FAIL · NaN** | No — family | **NO** |
| Historical #9 — GEMSDOE27 gap-closure | [gems27 … gap-closure … 5512495c6bd1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/bef7ae8e8f63b69d299c9214c75988c8f5055f9c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif?raw=1) — 61,328 dots | **OWNER-REPORTED 0.2449** | **FAIL · NaN** | No — 98% vs G24 | **NO** |

**How to read evidence labels:** HOLDOUT-DTI = local hide-and-recover on withheld whole fault components (pooled α=0.2/β=0.8/300 m), **not** the organizer’s hidden-test leaderboard. LLI-PROJECTION = empirical Ridge on 118 organizer-confirmed rasters (LOO MAE 0.0353) — a forecast, not a score. OWNER-REPORTED = value copy-pasted from a site README with no submission-page receipt proving those bytes earned it. Only a receipt showing submission ID + SHA-256 + score counts as ORGANIZER-CONFIRMED — none of the nine historical claims meet that bar in this repository. Official public leaderboard observation is separate: **0.4437** by `xiaofanhu` on 2026-10-26 ([source](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)), not a score for our files.

## Why GEMSDOE32 leads the supplied historical records (PhD-level forensic)

**Verified byte identity (0-XOR across 5,167,373 footprint pixels):** D2.8 parent (G25/G30) 44,090 dots → B1 40,199 → B2 37,654 by `EDT(~existing_faults) > threshold`. B1 removes 3,891 at ≤100 m; B2 removes another 2,545 at ≤200 m. GEMSDOE36 = B2 +1,200. GEMSDOE25 and GEMSDOE30 are exact pixel duplicates despite different encodings. Source: [`evidence/wbg_h1/forensic_proof_02778.json`](../evidence/wbg_h1/forensic_proof_02778.json) and [`data/nine-site-audit.json`](data/nine-site-audit.json).

**Metric mechanism: Distance-weighted Tversky (DTI) = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)** with 300 m triangular kernel (`max(0,1-d/300)` per truth pixel, max-cover per truth cell, catalogue pixels excluded). Two consequences: (1) redundant dots near same hidden fault add little TP_w but each adds ~1 FP_w; (2) dots within 200 m of known catalogue are almost certainly FP_w because hidden faults are disjoint by design. Pruning catalogue-near dots thus reduces FP_w with near-zero TP_w loss, raising DTI. The 0.2600→0.2778 gain (+0.0178) for deleting 6,436 collar dots fits: each deleted dot removed ≈0.00277 DTI of FP cost at ≈0 TP cost.

**Why unique files necessarily score lower without new physics:** Private test set |G_private| ≈12,366 px (≈1,237 km) estimated from `r13-lattice-s5` (206,895 dots, 99.871% coverage, DTI 0.0904, inversion proof in `forensic_proof_02778.json`). At 37,654 dots, the family already saturates most hidden length via 300 m kernels. A “unique” file (≥30% dots >3 px from family) must place ~11k dots into off-network strata at ~0.04 TP_w/dot vs 0.13 on-network — a direct DTI trade-off without a new signal.

**Four defects capping H19-5 at 0.2778 (and WBG-H1’s fixes):** (1) Zero dip back-projection: 50–65° normal faults displace 500 m-deep basement steps 400–1,000 m basinward — outside the 300 m kernel; H19-5 used 0 m shift. *Fix: DipShift 500/1,000 m updip along ∇G15(det_elev).* (2) Fluvial wash contamination: 35–45% dot waste on cross-contour washes (`lid_cross_max`). *Fix: TFSDI.* (3) 24.63% 3DEP LiDAR gap blindness. *Fix: LiDAR-blind specialist.* (4) Isotropic d=2.8 px NMS vs submodular 300 m CELF. *Fix: two-regime CELF (72% piedmont / 28% concealed).*

**Can 0.3195 / 0.4413 / 0.4437 be beaten?** Those are prompt claims / public-leaderboard observation (`xiaofanhu` 0.4437 on 2026-10-26), not scores for our files. Inverting DTI at 37,654 dots: 0.2778 → 40.38% weighted recall; 0.3195 → 46.66%; 0.4437 → 65.73% (0.2158 TP_w/dot vs H19-5’s 0.1326). No file here reaches that; it would require holding WBG-H1 gains plus depth-persistent MT / InSAR compartment signals (blocked in this sandbox — documented as viable in `knowledge/01_preregistration_wbg_hypotheses_2026-10-26.md`) and untouched confirmation.

## Site-by-site findings (historical → audit only)

### GEMSDOE32 — B2 nested-pruning benchmark (37,654 dots)
Highest OWNER-REPORTED among nine; exactly D2.8 where EDT >2 px. Not independently organizer-confirmed in this repo. SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`. [Pinned snapshot](https://github.com/buffedlizard55-lab/GEMSDOE32/tree/07806249f4ed3efe70b4fbf866183c32392b7853).

### GEMSDOE36 — Anderson-labelled augmentation (38,854 dots)
All B2 dots +1,200; PINN filename not verified as new physics. OWNER-REPORTED 0.2750. SHA `e15891020b9c57056ac7fa874a5e506fbd6ed9314a4ea8e73af0753887a3708a`.

### GEMSDOE28 — Rung30 / B1-family variant (37,660 dots)
Best among four G28 variants; SOLO variant pixel-identical to G31 B1. OWNER-REPORTED 0.2710. SHA `5556aa1438fd67376b60d5ffc99228ec09dcc11a8408298a743ccb88d6163641`.

### GEMSDOE31 — Catalogue-distance B1 pruning (40,199 dots)
D2.8 minus 3,891 at ≤100 m. Reproduces G28 SOLO. OWNER-REPORTED 0.2708. SHA `07b6db440535404bb41ec8ddc797713e200d308e3da35937393efde5eb84bc40`.

### GEMSDOE33 — Analog-tip / stepover extension (41,865 dots)
Extra structural dots did not beat B1’s reported value. OWNER-REPORTED 0.2632. SHA `87f857d505e23247e991ccfab2cbe9f49a04df4f9c8028dce7ea261554690757`.

### GEMSDOE25 — D2.8 parent field (44,090 dots)
Exact pixel duplicate of G30. OWNER-REPORTED 0.2600. SHA `91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8`.

### GEMSDOE30 — Repackaged D2.8 dots (44,090 dots)
Identical to G25. OWNER-REPORTED 0.2600. SHA `8cf893ead5667df21d3288a9968c35fd5385c425b029d82ee71d311715b129fd`.

### GEMSDOE24 — Sparse ridge thinning (60,069 dots)
D1.5 family root. OWNER-REPORTED 0.2477. SHA `68d0e2e4fcc594f9a23f56c44b885fee733d026d39be55e18ad2a07289525310`.

### GEMSDOE27 — Topographic gap closure (61,328 dots)
D1.5 +1,259 bridges; lower reported value suggests bridges were not beneficial on hidden labels. OWNER-REPORTED 0.2449. SHA `33003374335d84bf885f2d8f5e9dd4c57044c8ec58fa6a0d7fa581e8bc41c11d`.

## Limitations and next actions

- No assigned lane paragraph; provisional research only.
- Core data matches owner mirrors, not independently authenticated organizer-origin manifest.
- Historical scores lack receipts; hidden test labels/private data unavailable.
- Nine frozen snapshots ≠ all 92 sites; no global uniqueness claimed — single duplicate suffices for STOP.
- Weekly allowance unknown (login required); rules PDF 3/week is not proof of remaining.
- Future promoted lane needs same-instrument current-best victory + untouched confirmation + surface & final-dot uniqueness + exact-artifact format validation before selector considers a slot.

[How to submit](how-to-submit.html) · [official sources and irregularities](evidence.html) · [full prompt](standing-prompt.md)

## Run card

[Download complete JSON run card](data/run-card.json). Verdict: **negative** (WBG-C1). Best portal-valid unique file is separately documented in [`evidence/wbg_h1/run_card.json`](../evidence/wbg_h1/run_card.json) — verdict `negative` per selector (trails DPRF1 0.1638), but passes format/uniqueness.

