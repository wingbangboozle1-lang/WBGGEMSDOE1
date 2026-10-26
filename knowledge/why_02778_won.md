# PhD-level analysis: why `h33-h33-2-b2` scored 0.2778, and can it be beaten?

Owner-reported score 0.2778 for
`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`
(37,654 dots, 0 on-catalogue). All raster relations below were recomputed in
this repo from exact bytes (see `evidence/`); the 0.2778 figure itself is
owner-reported, not an organizer receipt for these bytes.

## 1. What the champion raster IS (measured, not narrated)

- It is a **strict subset** of the 0.2600 D2.8 emission: all 37,654 dots coincide
  exactly with D2.8 dots; 6,436 D2.8 dots were removed (44,090 -> 37,654).
- The removed dots are exactly the near-catalogue flank (B = 2 px = 200 m):
  the champion has 0 dots within 200 m of `labels.tif`.
- Lineage: H19-5 solid (0.1922) -> dotted d1.5 (0.2477) -> dotted d2.8 (0.2600)
  -> H27-4-solo prune to 40,199 (0.2708) -> H33-B2 prune to 37,654 (0.2778).
- GEMSDOE36's PINN (0.2750) contains ALL champion dots plus 1,200 extras
  (rank-corr 0.984): the extra dots cost -0.0028. GEMSDOE30's "poisson300m"
  (0.2600) is **bit-identical** to D2.8 (corr 1.000). The whole focus-9 family
  sits at 86-100% mutual 3-px overlap: it is ONE lineage, not nine ideas.

## 2. Why it won (mechanism, in metric units)

1. **Denominator surgery, not discovery.** Live scoring masks known faults, so a
   dot within ~300 m of *only* catalogue faults earns ~0 but costs 0.2. At
   DTI = 0.26 the break-even is 0.052; flank dots earn below it. Deleting 6,436
   below-break-even dots mechanically raises DTI. No new fault was found.
2. **Kernel-matched sparsity.** The 300 m triangular kernel lets ~280 m-spaced
   dots cover the same fault mass as the solid; thinning had already cut the
   denominator 60k -> 44k; B2 cut 44k -> 37.7k. Each cut kept numerator while
   shrinking denominator.
3. **Zero on-catalogue waste.** All 37,654 dots are off-catalogue; none pay the
   masked-pixel tax directly.

## 3. Why this lineage is now exhausted (diminishing returns)

- The remaining 37,654 dots earn above break-even *on average* (else cutting
  more would have continued to win — the family tried: rung30 37,660 at 0.2710
  and PINN+1200 at 0.2750 both fall short of 0.2778, bracketing the optimum).
- Further pruning cuts into above-break-even credit; further additions at the
  same detector quality earn below break-even. The lineage has converged to its
  detector's break-even frontier.
- The public top has reportedly moved to ~0.44 (unverified from this sandbox):
  no break-even re-budgeting of THIS detector reaches that; it requires a
  detector with substantially higher credit fraction (numerator), i.e. genuinely
  new hidden faults.

## 4. Can a submission score higher than 0.2778? (judgement)

- **By pruning/adding within the H19-5 lineage: almost certainly not** beyond
  noise (+/-0.003). The 0.2708/0.2710/0.2750/0.2778 cluster IS the frontier.
- **By a new detector finding hidden faults the lineage misses: possibly.**
  Requirements: (a) expected per-dot credit above 0.0556 on *hidden* truth;
  (b) proof on an off-catalogue instrument (SGMC) before spending a slot;
  (c) strict uniqueness (the lineage already occupies the H19-5 support).
- **Honest base rate:** every unique (non-lineage) artifact in the sibling fleet
  with a reported holdout (G28-S21, G31-H31X, G32-H47, G33-SEISDIL) scored BELOW
  its lineage anchor on holdout and was marked DO NOT SUBMIT. A new lane starts
  as the underdog; the holdout decides.

## 5. What this repo does about it

Lane H1 (geothermal-discharge-anchored blind-fault inference) is built to be
maximally disjoint from the lineage support (discharge-first ranking, no H19-5
input), ranked on the SGMC off-catalogue instrument, and gated by uniqueness
(corr < 0.90, 3-px overlap < 70% vs all nine). The automated verdict (promote /
negative) is computed from exact bytes — no human inspector.
