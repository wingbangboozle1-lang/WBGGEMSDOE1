# Ranked geological hypotheses — preregistered 2026-10-27 (before implementation)

**This file is the single-method lane for the 2026-10-27 session.** The supplied prompt still
refers to “the single method paragraph below” but contains no such paragraph; this lane is
therefore explicitly **provisional research**, not authorization to spend a weekly DrivenData
slot. It is new relative to `research/00_ranked_hypotheses.md` (TIP1), `docs/hypotheses.md`
(WBG-C1) and `knowledge/01_preregistration_wbg_hypotheses_2026-10-26.md` (WBG-H1/DPGF-1).

Decision baseline: the highest *replayable* same-instrument point estimate retained in this
repository is **HOLDOUT-DTI 0.166060** (95% CI `[0.151858, 0.180339]`,
`gems-segment-pooled-v1`, 60,988 withheld positives) for GEMSDOE24 S3DEP1. Its fold-aligned
prediction masks were not archived, so an independent paired replay is unavailable. A candidate
is **not** promoted unless its own 95% CI lower bound exceeds that point estimate *and* it passes
every other gate. No leaderboard projection is a score.

Expected benefit below is a qualitative ranking, **not a score forecast**.

## Official-source grounding verified this session

| Fact used | Official source (verified 2026-10-27) |
|---|---|
| Hidden labels are newly expert-identified faults **not** in the public USGS/INGENIOUS catalogue; public labels are incomplete and may be inaccurate | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| DTI: α=0.2, β=0.8, 300 m triangular kernel; submission = one float32 GeoTIFF, EPSG:32611, 100 m, values in `[0,1]` | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric) and [submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format) |
| Up to three submissions per week; a single GeoTIFF is selected for both prize rounds; generative-AI use must be disclosed in the narrative | [GEMS Prize Official Rules, §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| Geodetic shear/dilatation, gravity, magnetics, conductivity, elevation and earthquake density are official provided features | [DrivenData datasets](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#datasets) |
| Fault stepovers and terminations produce the largest localized stress/strain effects in Great Basin hydrothermal settings | [USGS / Siler (2023), DOI 10.1144/geoenergy2023-009](https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa) |
| GeoDAWN magnetic/radiometric source and 3DEP lidar coordination; CC0 data release | [USGS GeoDAWN, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) |
| INGENIOUS geodetic, conductance, gravity, magnetic, thermal, spring/well, fault and volcanic resources; CC BY 4.0 | [DOE GDR submission 1391, DOI 10.15121/1881483](https://gdr.openei.org/submissions/1391) |
| 1/3 arc-second 3DEP DEM collection (public domain) | [USGS ScienceBase `4f70aa9fe4b058caae3f8de5`](https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5) |
| Great Basin 3-D MT conductance slices at 2–200 km (five depth ranges) | [USGS / Peacock & Bedrosian (2022), DOI 10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU) |
| Sentinel-2 is **no longer distributed by USGS EROS**; use Copernicus Data Space | [USGS EROS Sentinel-2 notice](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-sentinel-2) |
| Reference baseline is a Monte-Carlo U-Net on the official features | [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) |
| Public leaderboard observation this session: **0.4544** (xiaofanhu), not 0.4413 or 0.3195 in the prompt | [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |

## Ranked candidates

| Rank | Hypothesis and exact layers | Physical signature | Why it could find a catalogue-missing fault | Named non-fault mimic | Difference from this repo | Expected benefit / cost / data status |
|---:|---|---|---|---|---|---|
| **1 — execute now** | **TASC: tip-aligned strain-transfer corridor.** Per fold, skeletonize only `fold.visible` public faults; estimate each endpoint’s outward tangent. Multiply a 0–3 km along-strike, ±1 km across-strike anisotropic corridor by a 300 m Gaussian gradient response of `geod_shearrate` (band 7), positive `geod_dilaterate` (8), `iso_grav_anom` (13), `tmi` (14), and `depth_to_base_surf` (15). | A **directional strain lobe** at a mapped tip: elevated shear-gradient and positive dilatation, coincident with a basement/gravity/magnetic edge, inside a forward continuation wedge. No pixel of a withheld component is read. | USGS/INGENIOUS traces commonly end where scarps are buried by fan gravel. Siler (2023) shows terminations/stepovers localize stress and strain; a soft-linked or blind continuation can therefore be geophysically detectable beyond the mapped free face without being in the catalogue. | Alluvial-fan channel avulsion lobe, road/rail cut-and-fill, pluvial shoreline bench, intrusive/lithologic contact. | WBG-H1’s 66 channels use “worm” advection, dip coupling and ratio products but **no visible-tip tangent geometry**. TIP1 measures LiDAR coherence drop along a scarp’s own strike (catalogue-independent). H33D grafted tip/stepover dots onto an inherited H19-5/B2 mask. TASC is the first fold-local **visible-tip tangent × geodetic/strain-edge conjunction**. | **Highest expected benefit / medium cost.** Uses the verified 19-band cache and the public catalogue only. All bytes are already hash-pinned locally; no new external download required. |
| 2 | **PCE1: potential-field phase congruency.** `rtp` (2), `tmi_hg` (3), `tmi` (14), `iso_grav_anom_hg` (18); Gaussian-derivative phase congruency at 300/900/1500 m. | An edge where magnetic and gravity gradient signs stay congruent across scales but amplitude varies — a “persistent contact” rather than a single high gradient. | A concealed basement fault can offset density/magnetization without a surface scarp; multiscale persistence rejects flight-line leveling noise and single-scale lithologic edges that dominate catalogued traces. | Flight-line leveling seam, volcanic-flow contact, survey-block boundary. | WBG-C1 used a Hessian commutator at 300/800 m; WBG-H1 used Miller-tilt gradients and persistence at 150 m. No reviewed code computes **cross-field phase congruency over three physical scales**. | Medium expected benefit / medium cost. 19-band cache sufficient. |
| 3 | **CLR1: radiometric compositional closure residual.** GeoDAWN-derived `gd_K`, `gd_Th`, `gd_U`, `gd_TC`, `gd_ThK`, `gd_UK`, `gd_UTh` plus `cond_surf` (17). | Robust centred-log-ratio residual of K against Th/U at 300–1500 m scales, retained only where it coincides with a conductive-edge gradient. | Hydrothermal K-metasomatism or U-redox fronts can mark a buried fluid conduit with no geomorphic scarp; the public catalogue is surface-mapping biased. | Felsic ash-rich fan, playa evaporite redistribution, weathering/moisture attenuation. | WBG-H1 has `hyd_rad_k_th_adularia` and raw ratios; no reviewed lane uses a **local multiscale compositional log-ratio closure residual** as the primary detector. | Medium / low-medium cost. The 8 radiometric/extensions bands are already restored from a pinned owner mirror of the CC0 USGS release; original raw grids were not re-downloaded here. |
| 4 | **DIFF1: diffusion-degraded scarp shape invariant.** USGS 3DEP 1 m DEM → `step_max`, `lapneg_max`, `lappos_max`, `det_elev` (12), `det_elev_slope` (19). | Fit a dimensionless curvature/step ratio across a scarp profile; select paired convex/concave lobes whose height–curvature relation matches a diffusion-degraded normal-fault scarp, not a symmetric wash. | Old low-throw scarps can fall below mapping thresholds yet retain a diffusion profile; these are preferentially missing from the catalogue. | Lacustrine shoreline, terrace riser, road embankment. | TIP1 uses a coherence tip gradient, SAHG1 persistence/amplitude, WBG-H1 `dpgf_tfsdi_scarp` / `ms_piedmont_inflection`; none fits a **profile-shape diffusion invariant**. | Moderate / high cost. Official source is public-domain [3DEP 1/3″ DEM](https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5) and 1 m lidar listed by the competition; raw tiles cannot be bulk-fetched from this sandbox’s egress allowlist. A hash-pinned 100 m aggregate is available locally, but raw 1 m profiles are needed for a fair test. **Not viable this session.** |
| 5 | **MT3D: depth-persistent subvertical conductivity edge.** USGS 3-D MT conductance slices (2–12, 12–20, 20–50 km) plus `cond_surf` (17), `depth_to_base_surf` (15), `geod_2ndinv` (4). | A strike-aligned conductivity gradient that persists from shallow to mid-crustal depth, discriminating a crustal fluid conduit from a conductive playa. | Deep intra-basin fault roots can lack any surface trace; depth persistence is the only way to separate them from shallow saline sediments. | Graphitic/sulfidic Paleozoic shale belt, saline basin fill, inversion artifact. | Reviewed lanes use only 2-D `cond_surf` and derived clay-cap perimeters; no inspected implementation uses **3-D MT depth slices**. | Potentially high scientific value / high cost. Official free source verified at [DOI 10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU), but ScienceBase bulk file hosts are outside this sandbox’s allowlist and no reviewed local mirror exists. **Not viable this session.** |

## Locked TASC experiment (three arms, no post-hoc selection)

All arms use the same `gems.holdout.SegmentHoldout` (buffer 15 px = 1.5 km), the same
`0.73%` per-fold dot budget, 3 px minimum spacing, and the shared
`gems.emission.priority_poisson` / `gems.metric` / `gems.submission` tools. Every
catalogue-derived channel is computed **only from `fold.visible`** for that fold; visible
faults are masked pixel-exactly. The four fold-local surfaces are stitched into their own
quadrants, so the shared canary sees the correct per-fold feature without reading a hidden
component.

1. **Arm A — label-free physical control:** `R` only (multiscale geophysical edge/strain
   response, no catalogue geometry).
2. **Arm B — primary TASC candidate:** `C × (0.5 + R)` where `C` is the fold-local
   visible-tip corridor.
3. **Arm C — orientation ablation:** `D × (0.5 + R)` where `D` is an isotropic
   visible-fault distance annulus (3–28 px). It isolates whether the oriented tip corridor,
   not merely catalogue proximity, adds information.

Fixed constants (no tuning after results): corridor `s∈[1,30]` px, `|t|≤10` px,
`s`-peak 8 px/`σ=10`, `t`-`σ=5`; response Gaussian `σ=3` px; annulus 3–28 px;
dot budget `0.0073 × fold footprint`; min separation 3 px; seed 20261027.

## Fixed gates

- **Leakage canary:** shared `SegmentHoldout.canary` on every raw source channel, every
  transformed channel and each fold-stitched arm surface, both polarities; any
  orientation-invariant AUC > 0.90 stops efficacy claims.
- **Surface before placement:** `|Spearman ρ| ≤ 0.90` against all 179 restored registry
  rasters; a duplicate stops before final dots.
- **Final dots:** at most 70% of candidate dots within 3 px of each registry raster under the
  literal rule; also report the shared tool’s `separate_calibration_controls=True` diagnostic,
  which keeps all entries in `rows`, applies rank gates to every entry, and applies 3 px
  overlap only to non-space-filling competing methods. The literal unseparated result remains
  binding for the frozen protocol.
- **Holdout:** pooled DTI, α=0.2, β=0.8, 300 m triangular kernel, whole components hidden
  with 1.5 km buffer, visible faults masked exactly, 1,999 10 km spatial-block bootstrap
  draws, 95% CI.
- **Promotion efficacy:** Arm B must exceed HOLDOUT-DTI 0.166060 with a 95% CI lower bound
  above it and a strictly positive paired 95% CI against replayed Arm A. Fail closed if the
  S3DEP1 fold predictions remain unavailable.
- **Format:** one float32 band, EPSG:32611, `(3730, 3292)`, exact transform, all values finite
  in `[0,1]` (zeros outside the footprint), one-TIFF ZIP, note ≤140 chars.
- **Governance:** no weekly slot is selected or spent. Promotion only makes a candidate
  eligible for a separate selector. No uploader or authenticated allowance exists here.

## Source obtainability statement

The top candidate needs only the 19-band owner-mirrored competition feature stack and the
public catalogue raster, both already restored and SHA-256 verified against
`registry/data_manifest.json` / `registry/template_pins.json`. No new external dataset is
needed. Candidates 2 and 3 are viable with the same local cache. Candidate 4 needs raw 3DEP
1 m/10 m DEM tiles (official public-domain source linked above) and candidate 5 needs the
USGS 3-D MT conductance GeoTIFFs (official CC0/USGS source linked above); both official pages
were verified this session, but their bulk-download hosts are outside this sandbox’s outbound
allowlist. They are recorded as future work, not proposed as validated this session.
