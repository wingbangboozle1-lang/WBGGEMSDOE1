# Preregistered candidate hypotheses — 2026-10-26

**Locked before implementation.** This document defines the only scientific lane executed in this repository. It does not claim that the owner supplied a method paragraph; none was present. The lane is self-selected under the owner's explicit instruction to rank 3–5 untried hypotheses and validate the top candidate. Maximum: three fixed arms or two hours; no competition upload.

## Decision baseline

The newest comparable point-best found in the pinned focus-site review is **HOLDOUT-DTI 0.166060** (95% CI `[0.151858, 0.180339]`, `gems-segment-pooled-v1`, 60,988 withheld positives) for GEMSDOE24 S3DEP1. It is not an organizer score and is itself `DO_NOT_SUBMIT`. A candidate cannot be promoted unless it beats that point estimate with a strictly positive paired 95% block-bootstrap interval, passes every other gate, and then passes a separate selector.

Expected improvements below are qualitative rankings, **not score projections**.

| Rank | Candidate and exact layers | Physical signature | Why it could find a catalogue-missing fault | Named non-fault mimic | Difference from reviewed implementations | Expected value / cost / data status |
|---:|---|---|---|---|---|---|
| **1 — execute once** | **TIP1: orientation-following fault-tip damage gradient.** Cached USGS 3DEP-derived LiDAR bands `step_max`, `lapneg_max`, `lappos_max`, `coh100`, `strike`, `cross_max`, `upface_max`, `downface_max`, `valid`. | Decode the fixed quantization; sample `coh100` at ±2 and ±4 cells **along each cell's own axial strike**; take a fixed multi-offset terminal-gradient response; multiply by balanced crest/base curvature, square-root step amplitude, valid support, and a fixed channel-bank veto. | A mapped trace often ends where a scarp becomes buried by fan gravel. A short damage/splay zone can retain a curvature sign pair and an along-strike collapse of coherence for 200–500 m beyond the mappable free face. The score uses no catalogue, catalogue distance, or old prediction. | Road-cut terminus, fan-channel avulsion lobe edge, terrace-riser end, landslide toe. | H33D grafted tip/stepover dots onto an older H19-5/B2-family mask; OJ1 measured neighbourhood orientation dispersion; SAHG1 measured persistence/amplitude. TIP1 measures a **directional derivative of coherence along the local strike**, independently of catalogue tips and prior rasters. | Highest probability of passing method-family novelty; low CPU; all required bytes are available in the SHA-pinned GitHub cache. DTI upside expected low-to-moderate because tips are sparse. |
| 2 | **CLR1: compositional radiometric closure residual.** GeoDAWN `K`, `Th`, `U`, `Th/K`, `U/K`, `U/Th`; robust centred-log-ratio residual at 300–1,500 m scales; gravity-gradient corroboration. | A narrow K-metasomatic or U-redox alteration front that violates local ternary K–Th–U closure while lying on a basement-density edge. | Buried hydrothermal faults can alter regolith chemistry without a fresh scarp. | Lithologic contact, felsic ash-rich fan, playa salt redistribution. | Reviewed lanes used raw ratios or products; none in the inspected focus-site code used a local multiscale compositional log-ratio closure residual as the primary detector. | Medium novelty, low cost, cached official GeoDAWN-derived stack. Lower rank because radiometric footprints are broad at 100 m. |
| 3 | **DIFF1: scarp diffusion-shape age invariant.** LiDAR `step_max`, positive/negative LoG curvature, slope excess and relief; fixed dimensionless curvature/step ratios. | A diffusion-degraded normal-fault scarp has paired convex/concave lobes and a scale-consistent height/curvature ratio rather than merely high slope. | Old low-throw scarps can be below mapping thresholds but retain a diffusion profile. | Lacustrine shoreline, terrace riser, road embankment. | Existing lanes used point amplitude, balanced curvature, or 10 m monoclinal asymmetry; this would estimate profile-shape consistency/relative degradation. | Moderate geologic plausibility, medium cost. Full cross-profile fidelity ultimately needs raw 1 m DEM tiles, so the cached 100 m maxima make current validation weaker. |
| 4 | **MT3D: depth-persistent conductivity edge (prospective only).** USGS Great Basin 3-D MT integrated-conductance layers at 2–12, 12–20 and 20–50 km, plus `cond_surf`, basement depth and strain proxies. | Compare gradient orientation between depth-integrated layers; these are not 0.3, 3 and 8 km slices and may be too deep/coarse for the proposed scale. | Deep intrabasin structures may lack a surface trace, but regional conductance alone cannot establish a fault. | Graphitic or sulfidic shale and basin-scale conductive structure. | No inspected focus implementation used this exact cross-depth operator; global novelty unknown. | High cost; metadata and CC0 release available at [USGS DOI 10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU). Binary download, coverage, resolution and independence from labels are not verified. |
| 5 | **SWIR1: vegetation-masked SWIR alteration lineament.** Sentinel-2 L2A B04/B08/B11/B12, 20 m → 100 m, plus conductivity edge. | High-pass Al–OH/carbonate absorption residual aligned with a conductive clay-cap edge. | Altered fault gouge, sinter fissures and travertine can expose a conduit with no geomorphic scarp. | Evaporite playa margin, mine waste, volcanic lithologic boundary. | No inspected lane used optical SWIR spectroscopy as its primary physical view. | Medium/high potential, high acquisition QA cost. **Not viable here:** required Copernicus/USGS STAC/S3 hosts are outside the allowlist. Official manual-review source: https://www.usgs.gov/landsat-missions/sentinel-2 |

## Locked TIP1 experiment

One lane, three preregistered arms, all using identical support, `0.73%` fold budget and 3-pixel minimum spacing:

1. **A — amplitude control:** `coh100 × balanced_curvature × sqrt(step_max) × channel_veto`.
2. **B — primary TIP1:** `max(|coh(+2)-coh(-2)|, |coh(+4)-coh(-4)|) × balanced_curvature × sqrt(step_max) × channel_veto` sampled along local axial strike.
3. **C — scale-persistence ablation:** `sqrt(|Δ2| × |Δ4|) × balanced_curvature × sqrt(step_max) × channel_veto`.

No arm reads catalogue geometry. The catalogue is used only by the shared hide-and-recover evaluator and pixel-exact visible-fault mask. Every raw layer and transformed descriptor is tested by the two-polarity leakage canary before trust. Arm B is the fixed candidate; A and C are mechanism checks, not a post-hoc arm-selection search.

## Fixed gates

- **Surface before placement:** `|Spearman rho| <= 0.90` against every obtainable registry raster; otherwise stop.
- **Final dots:** at most 70% of candidate dots within 3 pixels of every registry raster; otherwise duplicate/negative, with no registry-driven relocation.
- **Holdout:** whole connected fault components hidden with 1.5 km buffer; every catalogue-derived feature visible-only (TIP1 has none); visible faults pixel-exactly masked; pooled DTI with α=0.2, β=0.8 and 300 m triangular kernel; 10 km block-bootstrap 95% CI.
- **Promotion efficacy:** Arm B must exceed HOLDOUT-DTI 0.166060 with a strictly positive paired 95% CI against an independently replayed current best. If the replay is unavailable, promotion fails closed.
- **Format:** one float32 band, EPSG:32611, `(3730, 3292)`, exact transform, no NaN/Inf in the footprint, and strict whole-array finite `[0,1]` for the downloadable `-zeros.tif`.
- **Governance:** a real weekly slot is a separate selector step. No upload occurs here.

## Source obtainability

The selected cache is restored only from a pinned GitHub object and checked against SHA-256. Its metadata identifies USGS 3DEP 1 m DEM tiles and provides the official source link. A GitHub mirror hash verifies bytes; it does **not** convert the owner mirror into organizer-authenticated competition data.


**2026-10-27 source correction:** A previously cited ScienceBase item `5fb70a0ad34eb413d5e14873` and a USGS publication `70247315` returned not found; they must not be cited as verified. The USGS MT conductance release at DOI `10.5066/P9TWT2LU` lists 2–12, 12–20, 20–50, 50–90, and 90–200 km integrated-depth ranges. This public source does not establish the provenance or semantics of owner-mirrored feature bands. Do not execute these prospective hypotheses without a newly assigned method and the hard protocol gates.
