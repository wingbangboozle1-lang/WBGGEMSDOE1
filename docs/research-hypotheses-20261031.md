# Geothermal-fault / vent discovery from free official data — durable research note, 31 Oct 2026

Companion to `docs/hypotheses-20261031.html` (site rendering of the same ranking) and to the
`## 31 OCT 2026 STANDING BRIEF` section of `README.md`. This file is the durable knowledge store the
owner asked for: what the open literature and the open datasets actually offer against *this*
competition, what is falsified, and what to build next. Every external claim below carries a link and
its verification status; nothing here is inferred from a name.

## 0. The frame that makes the rest of this short

The organizer metric, for any field whose dots are ≥ 7 px apart, is exactly

```
DTI = TP_w / (0.2 N + 0.8 K)          (derivation: README brief §1)
```

so at a fixed dot budget **one extra hit is worth 1/18,470 = 5.4 × 10⁻⁴ of score** (our N = 42,771,
K = 12,395). Consequences that re-order every intuitive priority:

| idea | naive expectation | what the identity says |
|---|---|---|
| find a better *macro*-habitat (new geology map) | big win | worthless if it re-concentrates the field: at fixed N, coverage, not habitat, separates 0.28 from 0.02 (§2 of the brief; `evidence/portfolio_descriptors.json`) |
| place each dot 1–2 px better on structure | small win | **free**: FP_w counts dots, not position, so a 2 px nudge can only convert miss→hit |
| drop 25 % of the dots | risky | worth +0.043 *if* the dropped dots carry no credit — it is a precision claim, and precision is the only unidentified parameter in this dataset |
| add 5,000 confident new dots | small win | each dot costs 0.2/18,470 = 1.08 × 10⁻⁵; it pays iff its expected credit > 0.2, i.e. iff it is a >20 % likely hit |

So the ranking below is ordered by *expected hit gain per engineering hour*, and the two hypotheses
that merely redraw the favourability map are deliberately at the bottom — contrary to what most of the
INGENIOUS literature would suggest if you read it as "predict favourability".

## 1. Verified open sources (all free, all checked 31 Oct 2026)

| source | what it contains, in the operators' own words | how we would use it | verification status |
|---|---|---|---|
| OpenEI Geothermal Data Repository submission **1391** — *INGENIOUS – Great Basin Regional Dataset Compilation*, DOI [10.15121/1881483](https://doi.org/10.15121/1881483), CC-BY 4.0, 116.98 MB / 9 packages ([submission page](https://gdr.openei.org/submissions/1391)) | "2-meter temperature probe surveys, quaternary faults and volcanic features, geodetic shear and dilation models, heat flow, magnetotellurics (conductance), magnetics, gravity, paleogeothermal features (such as sinter and tufa deposits), seismicity, spring and well temperatures, spring and well aqueous geochemistry analyses, thermal conductivity, and fault slip and dilation tendency" | direct layer inventory for N1–N5; also the only public list of *updated* Quaternary fault traces for the study region, i.e. a candidate **independent** fault catalogue to measure our dots against | page fetched and read in full 31 Oct 2026; per-package URLs are `https://gdr.openei.org/files/1391/<name>.zip`. **Not byte-verified from this sandbox**: the egress allow-list excludes `gdr.openei.org`, so a `HEAD` request returns nothing. First action next session: download, record `sha256`, and store in `data/external/` (gitignored) |
| USGS **GeoDAWN** — *Airborne magnetic and radiometric surveys of the northwestern Great Basin, Nevada and California*, GDR search hit [gdr.openei.org/search?q=pressure+data&tp[]=mag](https://gdr.openei.org/search?q=pressure+data&tp%5B%5D=mag), "Publicly accessible" | flight-line magnetics + radiometrics over exactly the competition's tectonic province; the radiometric K/Th/U ratios are the alteration vector the competition's own 19-band stack lacks | N2 | listed as publicly accessible in the GDR index (31 Oct 2026); the same search also surfaces the *New Mexico Geothermal Play Fairway Analysis* and *Lightning Dock* GIS packages, so the index itself is live |
| USGS **Earth MRI** airborne mag/radiometric releases, e.g. [catalog.data.gov dataset for the south-central NM alkaline belt](https://catalog.data.gov/dataset/airborne-magnetic-and-radiometric-survey-alkaline-igneous-belt-south-central-new-2023-2024) (accessLevel public, metadata updated 3 Aug 2026) | demonstrates the release format (flight-line CSV/GeoTIFF + survey-parameter report) we would have to grid | N2 method template | public, machine-readable, dated — verified 31 Oct 2026 |
| USGS Mineral Resources Online Spatial Data catalog, e.g. [helicopter-borne magnetic survey over Dixie Valley geothermal field, NV](https://mrdata.usgs.gov/catalog/science.php?b=0&n=657&order=alpha&term=fLD10&thcode=1) ("gridded data from helicopter study of shallow geologic structures") | a *geothermal-specific* very-high-resolution magnetics precedent for the same basin-and-range style | N3 calibration target: how fine can a grid be before it becomes lithology rather than structure | verified in the catalog index 31 Oct 2026 |
| GBCGE **INGENIOUS** project site [gbcge.org/current-projects/ingenious/](https://gbcge.org/current-projects/ingenious/) | the project's own description of which input features its favourability model uses — the reason N1's layer set is not novel by itself | scoping only | linked from the GDR submission page (same fetch) |

Not used, and why: the Deep Warm Sedimentary Play Fairway products, FORGE well data and the DOE
forecasts are point data at locations that are mostly outside the 3 730 × 2 922 cell grid; they cannot
be turned into a per-cell field without inventing values, which would be a hallucination risk, not a
modelling choice.

## 2. Five new hypotheses, ranked

Each names its layer(s), the transform, why it can catch a fault that the published 118-raster
registry and our own catalogue-avoidance rule both miss, and its difference from existing repo code
(`src/wbg8/estimator.py`, `scripts/wbg8_emit5.py`, the WBG-6 tip/stepover lane and the
topo-gap-closure family — all of which are *catalogue-geometry* or *provided-band* methods).

**N1 — Paleo-geothermal vent fingerprint (sinter + tufa) as a positive-only dot source.**
*Layers:* GDR 1391 `paleo_geothermal_regional.zip` (spring deposits, shapefile + CSV, NAD83).
*Transform:* rasterise siliceous sinter / tufa polygons → distance decay with a 1–2 km scale →
**only cells within the deposit halo are admissible**, then place the lattice seeds inside the halo and
let `emit5`'s micro-argmax pick the pixel. This inverts the usual favourability logic: instead of
"high score everywhere geology looks good", it is "dots only where a vent once existed".
*Why it can find an uncatalogued fault:* a sinter mound requires a *conduit*; mounds are mapped where
no fault was mapped, and the deposit survives burial that destroys the fault scarp — the exact failure
mode of `labels.tif`-derived and relief-deficit methods (our H1 falsification). Vents also cluster
along the buried strand, so a handful of mounds constrains a whole trace.
*Difference from repo code:* every closed lane here inferred structure from the geophysics or from
catalogue geometry; none used a *vent* observation as an anchor, and none used a positive-only mask.
*Cost/benefit:* 1 download + ~120 lines. Expected hit gain: if a halo contains even one hidden trace,
20–40 of our dots convert from miss to hit (+0.011 to +0.021); if the hidden label set contains only
Quaternary *faults* and no vent pixels, the halo mask merely reduces N — which the identity prices as
a *gain* (0.2 per dropped dot) provided the dropped dots were misses. **Asymmetric: the mask can lose
little and win a lot**, which is why it is first.

**N2 — Radiometric K/Th/U alteration ratio as the sub-pixel ranking field.**
*Layers:* GeoDAWN aeroradiometrics (Nevada/California) gridded to 100 m; ratio transforms `Th/K`,
`U/Th` rather than raw K.
*Transform:* replace `hab` in `emit5` (currently the coarse registry consensus) by a z-scored
clay/alteration proxy, *keeping the lattice and the ±2 px window unchanged*.
*Why:* hydrothermal clay halos are centred on the flow path and are a 1-cell-wide signal at 100 m, i.e.
exactly the scale at which a ±2 px nudge decides hit vs miss; magnetic/gravity gradients peak on
lithologic contact, not on the alteration halo — which is the most probable reason H1 failed.
*Difference:* the provided 19 bands contain no radiometrics; `src/wbg8/habitat.py` uses only those bands.
*Cost/benefit:* gridding flight-line data is the expensive part (2–4 h, and it is where a gridline
orientation or a tie-line level error would silently poison everything). Same lattice ⇒ **zero
duplication risk and zero geometry risk**; the change is a pure re-ranking, so it is the ideal second
test on the blocked holdout because the *only* moving part is the ranking field.

**N3 — InSAR-derived dilation-tendency / geodetic shear ridge, thresholded to *extending* quadrants.**
*Layers:* GDR 1391 `geodetics_INGENIOUS_regional_data.zip` (51.99 MB, geodetic shear + dilation models).
*Transform:* take `max(dilatation, 0)` × `shear-rate ridge`, i.e. keep only quadrants where the modern
strain field is opening; add it as a multiplicative term with weight ≤ 0.5 inside the ±2 px window.
*Why:* the hidden labels are *recent* fault traces; a Quaternary trace that is currently slipping
produces the strain signature, whereas a geophysical lineament may be entirely inherited. This targets
precisely the population the mapped catalogue under-represents (re-mapped active strands), which is the
one mechanism the registry itself supports: `GEMSDOE33 seisdil` tried strain *as a habitat* and scored
0.0963, while our brief shows habitat changes do nothing — strain's value is per-cell, not per-region.
*Difference:* repo code never used geodesy; the WBG-8 `relief_deficit` term is static topography.
*Cost/benefit:* cheap (already a GeoTIFF, same projection family). Honest prior on the gain is small —
the registry's own strain attempt failed as a habitat, and as a per-cell field we cannot validate it
without labels. Ranked third because it is cheap and composable, not because we expect a jump.

**N4 — Independent Quaternary-fault catalogue for *subtraction*, not addition (novelty + FP control).**
*Layers:* GDR 1391 `qfaults_ingenious_nad83conus117_2023-06-27.zip` (v2, supersedes v1).
*Transform:* rasterise the *updated* traces on our grid; compare against `labels.tif`. Cells in the
updated catalogue but absent from `labels.tif` are (a) provably faulted and (b) invisible to the
provided label set: an empirical, non-speculative blind-fault prior. Then measure our submission's
distance statistics against *that* set and report it on the site.
*Why:* it is the only available way to get a *labelled* evaluation without the organizer's hidden
labels; it converts today's impossible "is my ranking good?" question into a measurable recall/precision
number on a proxy that is at least built from real interpreted traces.
*Difference:* `scripts/evaluate_holdout.py` hides and recovers the *same* catalogue (documented defect:
Spearman 0.144 against real submissions). An external catalogue is a genuinely different population.
*Cost/benefit:* ~1 h. Its second use is defensive and immediate: if a hidden-truth cell is already
inside an updated fault trace that we score 0 on, that is a real, quotable miss on a known structure —
far more persuasive than another internal proxy. Also the only proposal here that can *raise* precision
by letting us drop dots sitting on mapped-but-unlabelled traces (worth 0.2 each in the denominator).

**N5 — New macro-habitat (heat-flow / MT conductance / merged magnetics favourability).**
*Layers:* GDR 1391 heat-flow maps (DOI 10.5066/P9BZPVUC), MT conductance (10.5066/P9TWT2LU), gravity +
magnetics (10.5066/P9Z6SA1Z).
*Why it is last and says so out loud:* §2 of the brief shows that at plateau counts, coverage decides
the score, and H1/H3b show that re-concentrating on a geophysical favourability map either does not beat
uniform (H1) or actively lands in the low-score band (H3b). A heat-flow field is 1–2 km scale, i.e.
purely macro, and the metric gives zero credit for macro improvement at fixed N. **This is the
contrarian claim**: the discipline's own best data are the least useful here, because the competition's
score is a nearest-neighbour assignment problem on a fixed budget, not a favourability ranking. Keep the
layers for the *map* we publish on the site (it is a geothermal deliverable in its own right), not for
the dot placement.

## 3. What to validate, on what, before spending a slot

1. Validate **N1** and **N4** together on a *spatially blocked* holdout — 8 blocks of ≈ 40 km,
   leave-one-block-out, scoring with `vendor/gems57/metric.py` on the block's own labels, never the
   pooled hide-and-recover proxy. Report `ΔTP_w` (dots converting miss→hit) as the primary statistic:
   the identity turns it into score without a model.
2. Gate before any submission: (i) N4's external-recall must improve, (ii) coverage must stay in
   0.92–1.00 and `n_components == n_dots` must hold, (iii) the literal and density-matched overlap
   numbers must be re-measured and reported even though the literal one is degenerate,
   (iv) leakage canary per new feature (AUC > 0.90 ⇒ leak until proven otherwise — the sinter layer is
   the one with real leakage risk, because a sinter map is compiled from the same field work that drew
   the labels; if its canary AUC is high, N1 dies and we say so).
3. Budget: two experiments, one slot. If N1's halo mask is empty inside the footprint after
   reprojection, that is the whole answer for N1 — a 20-minute falsification, not a submission.

## 4. Reproducibility

`data/external/` is gitignored; the download step must write `evidence/external_fetch.json`
(`url`, `bytes`, `sha256`, `retrieved_utc`) exactly as `scripts/fetch_scored_rasters.py` does for the
registry, and the site's feed reads that file. Until a `sha256` exists there, every number derived
from an external layer is to be labelled **UNVERIFIED-FETCH** in any table, and no file built on it may
be marked `SUBMIT: CLEARED` — the same rule that currently keeps the nine focus-site scores at
OWNER-REPORTED.
