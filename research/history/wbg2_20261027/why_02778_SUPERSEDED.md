# Why GEMSDOE32's `h33-h33-2-b2-...-zeros` scored 0.2778 — and what would beat it

Researched 2026-10-27. Every number here was measured in this repository from the original
artifacts, or copied from a named public source. Nothing is inferred from a leaderboard position.

## 1. The official metric, restated exactly

Source: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>

```
k(d)  = max(1 - d/R, 0),  R = 300 m  (= 3 px on the 100 m grid)

TP_w = sum over ground-truth pixels g of  max over predicted x within R of  p(x)*k(d(x,g))
FP_w = sum over predicted x with p(x)>0 of  p(x) * (1 - max over g of k(d(x,g)))
FN_w = sum over ground-truth pixels g of  1 - max over predicted x within R of p(x)*k(d(x,g))

DTI  = TP_w / (TP_w + alpha*FP_w + beta*FN_w + eps),   alpha = 0.2, beta = 0.8
```

`src/wbg2/metric.py` implements this. It is verified three ways in
`src/wbg2/verification.py`:

| check | result |
|---|---|
| Organizer worked example (TP_w 3.00, FP_w 1.89, FN_w 2.00 → published 0.60) | 0.6027 reproduced |
| Independent brute-force double loop, 40 random grids | max abs difference 2.8e-17 |
| Known kernel values (exact hit / 1 px off / 3 px off) | 1.0 / 0.6667 / 0.0 |

## 2. What the nine focus-site artifacts actually are

Measured directly from the published `.tif` files (`scripts/wbg2_nine_site_audit.py`):

| site | reported | positive px | % positive within 300 m of catalogue | % on catalogue |
|---|---|---|---|---|
| GEMSDOE32 | 0.2778 | 37,654 | 4.9% | 0.000% |
| GEMSDOE36 | 0.2750 | 38,854 | 5.0% | 0.000% |
| GEMSDOE28 | 0.2710 | 37,660 | 10.8% | 0.000% |
| GEMSDOE31 | 0.2708 | 40,199 | 10.9% | 0.000% |
| GEMSDOE33 | 0.2632 | 41,865 | 13.6% | 0.000% |
| GEMSDOE25 | 0.2600 | 44,090 | 18.7% | 0.000% |
| GEMSDOE30 | 0.2600 | 44,090 | 18.7% | 0.000% |
| GEMSDOE24 | 0.2477 | 60,069 | 19.0% | 0.000% |
| GEMSDOE27 | 0.2449 | 61,328 | 19.0% | 0.000% |

Three facts fall out:

1. **Every one of the nine is binary.** Exactly two distinct values, 0.0 and 1.0. None is a
   probability surface, despite the competition inviting one.
2. **Not one dot sits on a mapped fault** (0.000% everywhere). The organizers define the target
   as the faults the USGS catalogue *does not contain*, so putting a dot on a mapped fault is a
   guaranteed false positive.
3. **The reported score is perfectly rank-ordered by distance from the catalogue.** Not one
   inversion across nine files spanning 0.2449–0.2778.

## 3. Why the pruning worked

`alpha = 0.2` prices an off-target dot at 0.2. A dot exactly on a hidden fault earns 1.0 into the
numerator and simultaneously removes a 0.8 false-negative penalty from the denominator — roughly
9× the value of the false-positive cost it avoids. But a dot on a *mapped* fault earns nothing:
that ground-truth pixel is not in the scored set.

So deleting catalogue-adjacent dots is free profit. GEMSDOE32's own audit JSON states the method
plainly:

> "0.2708 base with every dot at d(catalogue) <= 2 px deleted (37,654 dots)"

That is a controlled experiment: 40,199 dots → 37,654 dots, +0.0070 in reported score. The gain
came from **deletion, not from detection**. GEMSDOE36 (0.2750) is the same construction with a
different dot set; GEMSDOE25 and GEMSDOE30 are literally the same 44,090-pixel field published
twice. These are one lineage, not nine independent discoveries.

## 4. Is 0.2778 near a ceiling for this method?

Regressing the nine reported values on catalogue proximity and field size:

```
score = 0.70317 - 0.07980 * (fraction of dots within 300 m of the catalogue) - 0.04010 * ln(budget)
R^2 = 0.988,  residual SD = 0.00147,  n = 9
```

Two caveats, both material:

- The regressors are collinear (r = 0.75) because every site lowered its catalogue fraction by
  deleting dots, which also lowered its budget. The two effects cannot be separated from nine points.
- It is a fit to *third-party reported* values, not to receipts.

Within those limits the extrapolation is clear: driving the catalogue fraction to zero and holding
the budget at the low end of the observed range predicts ≈0.28, not 0.35. **Pruning is exhausted.**

## 5. What the metric actually rewards — three simulated levers

Run against the official metric with synthetic fault networks (`/tmp/exp2.py`, `/tmp/exp3.py`):

| lever | measurement | verdict |
|---|---|---|
| Trace fidelity | continuous 1 px trace along the **true** local strike scores **0.936** | dominant |
| Rendering | scattered dots score **0.140**; runs at a **guessed** strike score **0.090** | scatter, do not fake traces |
| Budget at fixed hits | 20,000 px → 0.132, 2,500 px → 0.221 | shrinking helps *only* if the kept pixels are better |

The first row is the answer to "can we beat 0.2778?". Yes — but only by knowing where the fault
runs. Rendering tricks cannot substitute. Scattered dots are the correct hedge when the trace is
unknown, which is exactly why all nine sites scatter and why they all land in the same band.

## 6. Negative results (do not repeat these)

**Official-external-data detector — rejected.** A fault-likeness score was built from USGS GeoDAWN
radiometrics (K, Th, U, TC; ScienceBase 657e1d85d34e23d3533209f7, DOI 10.5066/P93LGLVQ) and USGS
3DEP 1 m DEM terrain descriptors, gated by scarp asymmetry and structure-tensor line-likeness,
with the named mimic being ephemeral channels and roads.

| term | AUC vs mapped faults |
|---|---|
| step / slope-excess | 0.574 |
| crest convexity | 0.585 |
| up-facing asymmetry | 0.493 |
| structure-tensor line-likeness | 0.497 |
| radiometric alteration (K vs Th) | 0.487 |
| combined | 0.549 |

At the real budget the combined ranking scored **0.0303** against the catalogue where a uniform
random draw of the same size scored **0.0695** — worse than random. The 100 m 8-bit aggregates do
not localise Great Basin faults. This is why WBG-2 does not use those layers.

**Strike-aligned runs with an estimated strike — rejected.** 0.090 vs 0.140 for scattering.

## 7. What WBG-2 does, and what it does not do

WBG-2 takes the one lever that survived: **exclude the catalogue harder than any site did**
(400 m, versus the best site's 200 m), place a 36,000-dot field on a Gaussian KDE of mapped-fault
density, and render binary in zeros mode with no NaN.

Measured skill: on a four-fold *spatially blocked* hide-and-recover test, the KDE-weighted draw beat
a uniform draw over the same admissible cells by **1.7–2.2×** in DTI. Small, real, and nowhere near
enough to reach 0.45.

It does **not** detect any individual fault. Its named non-fault mimic is basin geometry: basin-fill
depocentres and range-front alluvial aprons concentrate next to mapped faults, so a density prior
partly reproduces sedimentary basin shape rather than faulting.

## 8. The only path that plausibly reaches 0.39–0.45

1. Obtain the official `training_features.tif` (418 MB, 19 bands, login-gated at
   <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>). It is not in this
   sandbox and cannot be fetched through the available egress allow-list.
2. Train the reference U-Net (<https://github.com/drivendataorg/gems-prize-reference-solution>).
3. Apply the three measured rules: exclude the catalogue, keep the field as small as the hit rate
   allows, and ship zeros-mode with no NaN.
4. Validate on spatially blocked holdout, never on a random split, and never tune against the
   public leaderboard.

## Sources

- Problem description and metric: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Leaderboard (0.4544 rank 1, observed 2026-10-27): <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- Reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
- GeoDAWN data: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- GeoDAWN ScienceBase item: <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7>
- INGENIOUS: <https://gbcge.org/current-projects/ingenious/>
- EPSG:32611: <https://epsg.io/32611>
- Tversky index: <https://en.wikipedia.org/wiki/Tversky_index>
- GEMSDOE32 artifact and audit: <https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html>
