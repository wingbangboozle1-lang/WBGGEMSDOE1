# WBG-D1 ranked geological hypotheses — registered 2026-10-27

**Evidence class.** Benefit rankings below are pre-experiment conjectures, not
score forecasts. Every measured number produced by this lane is labeled
**HOLDOUT-DTI** with evaluator version, withheld-positive count and 95% CI
(`gems57-pooled-hide-v2`, n = 11,330). Historical competition values remain
**OWNER/USER-REPORTED and unverified** — no artifact-linked organizer receipt
exists in this checkout. No hidden labels, portal access or slot allowance is
available here.

The lane was self-declared because the prompt's referenced "single method
paragraph" was not supplied (`registry/preregistration_wbg_d1.json`).

| Rank | Hypothesis · specific layers · physical signature | Why it could catch a fault missing from the catalogue | Named non-fault mimic | Difference from prior repo work · readiness · result |
|---|---|---|---|---|
| **1 (executed)** | **Radiometric alteration + shallow magnetic edge (WBG-D1).** USGS GeoDAWN `K, Th, U, TC` and `Th/K, U/K, U/Th, TMI_up150` (uint8 grids, DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)) plus cached RTP (band 2) and TMI (band 14). Robust-z Gaussian high-pass residuals at 500 m/1 km, gradient-magnitude edges, and a TMI − upward-continued-TMI shallow residual. | Concealed basin/interior faults with no topographic ridge cannot be seen by the ridge-thinning family that dominates the registry; fluid upflow along them can produce K enrichment relative to Th and compositional lineaments where cover is thin. | Playa/evaporite and Pleistocene Lake Lahontan paleo-lacustrine clays, K-bearing basin fill, weathering/sorting, flight-line leveling, cultural magnetic noise. | No radiometric channel appears in any prior model in this repo (the idea was queued but untested in `docs/hypotheses.md` #3). Seven new channels + frozen deterministic composite + 19+7 HGB; all data restored from hash-pinned mirrors. **Result: negative.** EXP-1 composite 0.0283 vs random-dot 0.0345 (paired Δ −0.0062, CI strictly below 0); EXP-2 candidate 0.014072 vs control 0.014146 (Δ −7.4e-05, CI [−2.8e-4, +1.1e-4]). |
| **2 (queued)** | **Isostatic gravity vertical-gradient density boundaries under basin fill.** `iso_grav_anom_vg` (band 11) and `iso_grav_anom_hg` (band 18), multiscale horizontal-gradient maxima restricted to thick-basin cells (`depth_to_base_surf`, band 15). | A concealed basin-bounding fault offsets dense basement against light fill, giving a gravity edge where magnetic coverage is quiet and no scarp exists. | Basin compaction gradients, paleotopography, gridding/inversion seams. | Prior repo work uses gravity bands inside HGB but never a basin-restricted vertical-gradient edge detector. 19-band cache only; no new external data. Not yet run; budget exhausted at three WBG-D1 experiments. |
| **3 (queued)** | **Conductivity–basement-depth anisotropic boundary persistence.** `cond_surf` (17) and `depth_to_base_surf` (15) smoothed anisotropically parallel vs normal to a local structure tensor at 300–900 m. | A buried fault boundary persists along strike under smoothing where random saline-clay edges do not. | Elongated saline basin deposits, groundwater salinity gradients, survey lineaments. | Distinct from WBG-C1's Hessian *commutator* (curvature non-coaxiality): this tests directional *survival*, not curvature. Same cache; untested. |
| **4 (queued)** | **Shallow magnetic residual intrabasin edges with cultural screening.** `TMI − TMI_up150` residual, kept only where RTP edge direction is stable across two scales and radiometric `TC` shows no corresponding anomaly. | Upward continuation removes deep regional sources; the residual isolates shallow intrabasin fault edges beneath alluvium. | Well casings, pipelines, fences, alluvial-channel magnetic concentrations. | A standalone shallow-residual lane (WBG-D1 used the residual only as one HGB channel and one composite term). Needs an explicit cultural-mask validation step before it is viable. |
| **5 (queued)** | **Extensional dilatation jogs in a depth-contour frame.** `geod_dilaterate` (8) extrema transported along `depth_to_base_surf` contours over several lags, requiring multi-lag persistence. | Dilational relays and stepovers are preferred geothermal conduits (Faulds et al. 2019, [DOI 10.2172/1724080](https://doi.org/10.2172/1724080)) and can be unmapped where cover is continuous. | Inversion artifacts and non-tectonic strain nodules in the geodetic product. | Extends the untested texture-transport idea in `docs/hypotheses.md` #2 with a specific dilatation-jog target; no catalogue geometry enters the feature. |

## Why the top candidate was expected to be novel

The nine focus sites' historical leaders are one ridge/lineament-thinning family
(verified pixel identities in `evidence/nine_site_executive_summary_20261026.json`):
GEMSDOE25 and GEMSDOE30 contain identical 44,090-dot predictions, and the
GEMSDOE32 B2 leader is a distance-pruned subset. A radiometric alteration lane
targets a different physical field (gamma-ray composition vs topography/magnetic
ridges) and different placements (basin/interior alteration cells). The
measurement confirms the spatial novelty — worst forward 3 px overlap with any
**real geological** dot-field prior is 0.4846 (limit 0.70) and worst Spearman
0.106 (limit 0.90) — but novelty without efficacy cannot be promoted.

## Data and source readiness (free, official, verified in-repo)

- USGS GeoDAWN airborne magnetic and radiometric surveys, Northwestern Great
  Basin — sciencebase item `657e1d85d34e23d3533209f7`, DOI
  [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ); local grids
  `data/external/geodawn_rad_u8.tif` (sha256 `c22420f7…`) and
  `geodawn_extensions_u8.tif` (sha256 `a35a9c6d…`), restored from hash-pinned
  owner mirrors. Live USGS re-verification was not possible from this sandbox's
  network allowlist; the DOI link is provided for manual review.
- Competition grid and 19-band feature stack: hash-pinned public bridge,
  restored via `vendor/template57/prepare_data.py`; organizer origin is not
  independently authenticated.
- Structural controls on geothermal localization: Siler et al. 2023,
  [DOI 10.1144/geoenergy2023-009](https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa);
  Faulds et al. 2019, [DOI 10.2172/1724080](https://doi.org/10.2172/1724080).
- No external download beyond the restored mirrors is required for hypotheses
  2, 3 or 5; hypothesis 4 additionally needs a cultural-mask source to be named
  and verified before use.

## Stopping rule

Three experiments executed (EXP-1, EXP-2, EXP-3), zero submission slots used.
The radiometric hypothesis is retained as a measured negative. Hypotheses 2–5
await a future preregistered lane; none may be tuned against registry holes or
lattice gaps to manufacture uniqueness.
