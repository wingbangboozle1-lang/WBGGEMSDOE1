# Preregistration: Lane `WBG-4` (`CSJF-1`) — Four Untried Geological Hypotheses & Untouched Confirmation Design

**Locked UTC:** `2026-10-27T23:48:00Z`  
**Preregistration JSON:** `registry/wbg4_preregistration.json`  
**Budget:** Maximum 3 experiments, maximum 2 hours wall-clock, **0 competition submission slots used**.

---

## 1. Pre-Implementation Candidate Geological Hypotheses (Ranked by Expected DTI Gain / Cost)

Before writing or running model code, we formulate four geological hypotheses not previously implemented in `WBGGEMSDOE1`:

### Rank #1 (Selected Top Candidate — Executed in `WBG-4`): `CSJF-1` — Depth-Adaptive Listric Hanging-Wall Back-Projection (`DALBP`) × Conjugate Structural-Junction Tensor (`CSJT`) × 2-Stage Spatial Context-Pyramid Expected-DTI Optimization
- **Specific Layers Involved:**
  - Cached 19-band competition stack (`data/template57/`, all 19 SHA-256 hashes verified): `depth_to_base_surf` (15), `iso_grav_anom` (13), `iso_grav_anom_hg` (18), `iso_grav_anom_vg` (11), `rtp` (2), `tmi_hg` (3), `tmi_vg` (9), `cond_surf` (17), `geod_shearrate` (7), `geod_dilaterate` (8), `geod_2ndinv` (4), `ieq_n100a15` (16), `det_elev` (12), and Band 6 (`tc`, verified GeoDAWN radiometric Total Count).
  - Seamless 100%-coverage USGS 3DEP 1/3 arc-second (~10 m) terrain summaries (`data/dem10/`) + missingness-isolated USGS 3DEP 1 m LiDAR scarp summaries (`lidar_scarp_features_u8.tif`, strictly excluded from the Seamless specialist so missing LiDAR tiles never induce survey-footprint artifacts).
  - USGS GeoDAWN radiometric & 150 m upward-continued magnetic grids ([DOI: 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)) + label-free DOE OpenEI GDR #1391 INGENIOUS 2 m temperature probes (`F2mDAB`), silica/cation geothermometry, and paleo-geothermal sinter/travertine/opaline deposits ([gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391), `dist_known_fault_px` stripped) + US Census TIGER 2024 road/rail distance (`tiger_road_distance_m.tif`).
  - Strictly fold-visible fault mask (`fold["visible"]`) for Pollard-Segall tensile horsetail and en-echelon relay stress transfer.
- **Physical Signature Targeted:**
  1. **Depth-Adaptive Listric Back-Projection (`DALBP`):** Warps subsurface gravity HGM, Thurston-Smith potential-field local wavenumber $k_{\text{SPI}}$, and MT conductivity gradients up-dip along $-\nabla Z_b / \|\nabla Z_b\|$ by spatially varying listric offset $\Delta x_\perp(x) = Z_b(x)\cot\delta_{\text{eff}}(Z_b)$ ($\delta_{\text{eff}}$ shallowing from $58^\circ$ near surface to $46^\circ$ in $>2\text{ km}$ basins).
  2. **Conjugate Structural-Junction Tensor (`CSJT`):** Extracts the Harris-Förstner minor eigenvalue $\sqrt{\lambda_2(J_\sigma)}$ of the multi-physics gradient outer-product structure tensor $J_\sigma = G_\sigma * (\nabla \Phi \nabla \Phi^\top)$ across 10 m terrain, gravity, and magnetics at $\sigma \in \{300\text{ m}, 800\text{ m}\}$, explicitly preserving intersecting NNE Basin-and-Range × NW Walker Lane fault junctions that standard Frangi 1D ridge filters suppress.
  3. **2-Stage Out-of-Fold Spatial Context-Pyramid + Self-Credit-Penalized Expected-DTI CELF:** Combines inner-OOF multi-scale ring/steerable context of Stage-1 probabilities with a dedicated expected self-credit regressor $q_{\text{self}}(x) = \mathbb{E}[\max_{g \in T} k(d(x, g))] \in [0, 1]$, penalizing diffuse apron false-positive cost $\alpha(1 - q_{\text{self}}(x))$ analytically per `vendor/gems57/metric.py`.
- **Why Missing from USGS/INGENIOUS Catalogue:** Subaerial scarp mapping systematically misses buried intrabasinal faults shifted 100–1,200 m basinward at basement depth and fragmented conjugate intersections / accommodation zones (~39% of blind Great Basin geothermal systems; [Faulds et al., 2019](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and); [Siler, 2023](https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa)).
- **Named Non-Fault Mimic:** Intersecting bajada alluvial-fan distributary channels, buried Tertiary caldera ring-fracture/dike intersections, Pleistocene Lake Lahontan shoreline cusps/spits, and highway/railroad interchanges.

### Rank #2 (Incorporated in Static Physics): `BFRC-1` — Thin-Plate Flexural Basement Rollover Biharmonic Hinge ($\nabla^4 Z_b$) × Shallow MT Conductance Steepening
- **Layers:** `depth_to_base_surf` (15), `cond_surf` (17), `iso_grav_anom` (13), `det_elev` (12), `geod_dilaterate` (8).
- **Signature & Rationale:** Scale-normalized biharmonic flexural curvature $\nabla^2(\nabla^2 Z_b)$ localizes blind listric master-fault hanging-wall rollover monoclines that terminate beneath unconsolidated basin fill without brittle surface rupture. **Mimic:** Differential compaction over buried paleovalleys.

### Rank #3 (Incorporated in Static Physics): `RGFD-1` — Directional Quadrature Gabor Along-Strike Phase-Termination Discontinuity
- **Layers:** `dem10_hgm50_max`, `dem10_onesided`, `rtp` (2), `iso_grav_anom_hg` (18).
- **Signature & Rationale:** Detects abrupt lateral truncations of magnetic and range-front fabric across low-vertical-throw strike-slip accommodation/transfer faults. **Mimic:** Orthogonal erosional canyon breaches across volcanic hogbacks.

### Rank #4 (External Network Gate — Verified Official Free Sources): `OPERA-INSAR-1` — NASA/JPL OPERA Sentinel-1 DInSAR Secular Velocity-Gradient Discontinuities + USGS Heat-Flow Well Residuals
- **Official Free Sources:** [NASA ASF DAAC OPERA L3 DISP-S1](https://asf.alaska.edu/datasets/daac/opera/) and [USGS Great Basin Heat-Flow Release DOI: 10.5066/P9BZPVUC](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa) (CC0 Public Domain).
- **Obtainability Check:** Both official US Government sources are free and publicly obtainable on an unrestricted machine, but `asf.alaska.edu` and `sciencebase.gov` are blocked by this sandbox's outbound host allowlist; therefore `OPERA-INSAR-1` is documented for unrestricted follow-up rather than claimed here.

---

## 2. Three-Evaluator Validation Protocol (Including Untouched Confirmation)

1. **Primary (`gems-segment-pooled-v1`):** `SegmentHoldout` (`buffer_px=15`, `n=60,988` withheld positives across 4 spatial quadrants, 10 km block-bootstrap 95% CI).
2. **Secondary (`gems57-pooled-hide-v2`):** `buffered_component_draw(seed=20, hide_frac=0.20, buffer_px=3, boundary_px=12)` (`n=11,330` withheld positives, 8 km training collar, 20 km cluster bootstrap 95% CI).
3. **Untouched Confirmation (`gems57-pooled-hide-v2-confirm-seed77`):** `buffered_component_draw(seed=77, hide_frac=0.20, buffer_px=3, boundary_px=12)` — independent whole-component draw evaluated **strictly once** after freezing `ARM3_CSJF_MSCP_STACK_EDTI`, directly addressing `AGENTS.md` / `README.md` Limitation #4.
