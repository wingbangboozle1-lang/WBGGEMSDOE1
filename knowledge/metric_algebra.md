# Metric algebra: why the leaderboard looks the way it does

Competition: DOE GEMS Prize, DrivenData #306. Metric: distance-tolerant Tversky index.

## 1. Official definition (as transcribed from the problem page)

- `DTI = TPw / (TPw + 0.2*FPw + 0.8*FNw)`, i.e. alpha = 0.2, beta = 0.8.
- `k(d) = max(1 - d/300m, 0)` triangular kernel; at 100 m cells, R = 3 px.
- Known-catalogue fault pixels are **masked** (pixel-exactly per staff clarification):
  predictions on them earn no credit and the hidden truth contains only *new* faults.

Exact terms for binary prediction P and truth T (verified in `src/wbg1/metric.py`,
unit-tested in `tests/test_metric.py`):

- `A = sum_{x in P} k(dist(x, T))` (truth-side credit, TPw)
- `B = sum_{y in T} k(dist(y, P))` (prediction-side credit)
- `N = |P|`, `T = |T|`, `FPw = N - A`, `FNw = T - B`

## 2. The marginal (break-even) rule — the single most important equation

Adding one emitted pixel with expected kernel credit `a` raises DTI **iff**
`a > 0.2 * DTI`. Dropping a pixel raises DTI iff its credit `a < 0.2 * DTI`.

| DTI level | break-even credit |
|---|---|
| 0.1922 (H19-5 solid) | 0.0384 |
| 0.2477 (dotted d1.5) | 0.0495 |
| 0.2600 (dotted d2.8) | 0.0520 |
| 0.2778 (H33-B2 champion) | 0.0556 |
| 0.3195 (older public top, owner-reported) | 0.0639 |
| 0.44 (current public top, owner-reported, unverified here) | 0.088 |

Consequence: every emitted dot costs 0.2 in the denominator, so dots earning
near-zero credit (e.g. dots whose only nearby faults are *masked catalogue*
pixels) are pure cost. Removing them raises the score without finding anything.

## 3. Naive closure (one-to-one matching, A ~= B)

`DTI = a / (0.8 + 0.2*N/|G|)`, where `a = A/T` is the credit fraction and `|G|`
the hidden-truth mass. Used ONLY for labelled PROJECTIONS, never as a score.

## 4. Binary optimality

For a fixed support, DTI is linear in each `p(x)`, so the optimum is attained at
corners `p in {0,1}`: soft probability fields cannot beat the best binary set.
All shipped artifacts are binary {0,1} rasters — consistent with this.

## 5. Why dotted thinning beat solid emission (0.1922 -> 0.2600)

The 300 m triangular kernel bridges ~280 m gaps, so thinning the H19-5 solid to
dotted spacings d=1.5 (60,069 px) and d=2.8 (44,090 px) cuts N (denominator)
while retaining most kernel coverage (numerator). Ordering solid < d1.5 < d2.8
is reproduced out-of-sample by the naive closure (see GEMSDOE28
`analyze_why_026_won.py`, verified logic).

## 6. Why B=2 flank exclusion won (0.2600 -> 0.2778)

Dots within 200 m of catalogue faults earn ~0 live credit (their only nearby
truth is masked) but cost 0.2 each. The champion removes exactly the 6,436
D2.8 dots within the flank (44,090 -> 37,654), cutting pure-cost mass.

## 7. Holdout floor effect (found in this repo, 2026-10-26)

Hide-and-recover **against catalogue truth** scores the 0.2778 champion at
HOLDOUT-DTI = 0.0032: B-excluded dots avoid all catalogue by design, so
catalogue-truth credit is a floor effect and the instrument **cannot rank**
B-excluded candidates (it anti-correlates with the live-optimal move).
Valid ranking instruments must use **off-catalogue truth** (SGMC faults >300 m
from labels, 62,122 px; champion scores 0.0444 there, discriminative).
This repo therefore ranks on `WBG1-SGMC-CAL-v1.0` (primary) and reports
`WBG1-HIDE-RECOVER-v1.0` as diagnostic.

## 8. What beating 0.2778 requires

At N = 37,654 and the sibling lattice calibration |G| ~= 12,226 px, reaching
0.3195 at fixed credit needs ~half the dots, or credit must rise ~50% at fixed
dots. Both are *ranking* problems (put dots where hidden faults are), not
geometry problems. Denominator pruning has diminishing returns (remaining dots
earn above break-even on average); the remaining headroom is numerator:
finding hidden faults the H19-5 lineage misses.
