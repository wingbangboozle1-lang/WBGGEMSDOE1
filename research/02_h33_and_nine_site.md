# Nine-site executive review and H33-B2 forensics — 2026-10-26

## Decision table

**No historical file below is recommended for resubmission.** No artifact-linked DrivenData receipt was found, so each numeric historical value is labeled **OWNER-REPORTED / UNVERIFIED**, not ORGANIZER-CONFIRMED. Pairwise overlap comes from the pinned nine-site audit and is directional candidate-to-reference within 3 pixels.

| Site | Historical best file | Score/evidence | Max overlap vs other 8 | Unique ≤70%? | Recommendation |
|---|---|---:|---:|:---:|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | `0.2477` OWNER-REPORTED / UNVERIFIED | 100.00% | No | **DO NOT SUBMIT** |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | `0.2600` OWNER-REPORTED / UNVERIFIED | 100.00% | No | **DO NOT SUBMIT** |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | `0.2449` OWNER-REPORTED / UNVERIFIED | 98.02% | No | **DO NOT SUBMIT** |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | `0.2710` OWNER-REPORTED / UNVERIFIED | 100.00% | No | **DO NOT SUBMIT** |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | `0.2600` OWNER-REPORTED / UNVERIFIED | 100.00% | No | **DO NOT SUBMIT** |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | `0.2708` OWNER-REPORTED / UNVERIFIED | 100.00% | No | **DO NOT SUBMIT** |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | `0.2778` OWNER-REPORTED / UNVERIFIED | 100.00% | No | **DO NOT SUBMIT** |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | `0.2632` OWNER-REPORTED / UNVERIFIED | 99.71% | No | **DO NOT SUBMIT** |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | `0.2750` OWNER-REPORTED / UNVERIFIED | 97.58% | No | **DO NOT SUBMIT** |

These are historical owner claims, not a ranking of reproducible holdout performance. The conflicting leaderboard claims `0.3195` and `0.4413` also lack receipts and remain unverified.

## What H33-B2 actually changed

The SHA-verified raster for H33-B2 is a strict subset of the D2.8 ancestor:

- D2.8 ancestor: 44,090 dots
- H33-B2: 37,654 dots
- Removed: exactly 6,436 dots
- Added: **0 dots**
- All removed dots are 1–2 pixels (100–200 m) from the public catalogue; 3,891 are within 1 pixel and all 6,436 are within 2 pixels.

Therefore B2 did not discover a new geological target. It performed catalogue-halo precision cleanup. With `DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw)`, deleting a no-credit prediction reduces the false-positive term and can raise DTI. That is a plausible mechanism for an increase from the owner-reported D2.8 `0.2600` to B2 `0.2778`.

It is **not proof of causality**: hidden labels, the organizer TP/FP/FN components and an artifact-linked submission receipt are absent. The available bytes prove ancestry, not which bytes were uploaded or why the hidden score changed. For that reason this project cannot honestly apply the requested ORGANIZER-CONFIRMED label.

## Can a distinct approach exceed it?

Scientifically, yes in principle: genuine off-catalogue fault discovery could add hidden-truth credit rather than merely remove catalogue-halo predictions. Empirically, it is unproven. TIP1 is catalogue-independent and scientifically distinct, but its primary achieved only **HOLDOUT-DTI 0.082434** (95% CI `[0.072872, 0.091733]`, `gems-segment-pooled-v1`, 60,988 withheld positives), far below the local `0.166060` promotion benchmark. It also fails the retained literal lattice gate. No live-score projection is defensible.

## Auditable records

- [`evidence/h33_b2_forensics.json`](../evidence/h33_b2_forensics.json) — exact subset, distance and SHA evidence
- [`evidence/nine_site_executive_summary_20261026.json`](../evidence/nine_site_executive_summary_20261026.json) — machine-readable table and current refs
- [`registry/registry.json`](../registry/registry.json) — 179 unique, restored, byte-pinned comparator rasters; zero rejected sources
- Historical table source: [GEMSDOE36 README at `32c2660`](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/32c2660001d98f6fa9084a0971b3a9d5062d49b9/README.md)
