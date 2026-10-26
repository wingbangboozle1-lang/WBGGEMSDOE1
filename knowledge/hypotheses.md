# Candidate geological hypotheses (H1–H5), ranked

Rule: no weekly slot is spent on an idea that has not beaten the current
holdout best. Holdout = `WBG1-SGMC-CAL-v1.0` (primary, off-catalogue truth) +
`WBG1-HIDE-RECOVER-v1.0` (diagnostic). Leakage canary: feature-alone
two-sided AUC > 0.90 = leakage until proven otherwise.

## H1 (IMPLEMENTED, top rank): geothermal-discharge-anchored blind faults

- **Layers:** INGENIOUS wellspring CSV (temp-weighted) + volcanic vents +
  paleo-geothermal sites (anchors); `cond_surf` (MT clay-cap conductor);
  `rtp`/`tmi`/`tmi_hg` (magnetic basement steps); 1 m LiDAR scarp composite
  (`ex_max`, `step_max`, laplacians) with `det_elev` curvature fallback;
  `iso_grav_anom` + `iso_grav_anom_hg` (gravity steps).
- **Signature:** rank-consensus of >=2 lineament transforms coinciding within
  1 km of discharge, soft-gated by Andersonian strike (NNE ~15° / conjugate
  ~140°, tol 45°, floor 0.15); priority Poisson-disk emission, B=2 flank.
- **Why off-catalogue:** discharge requires permeability; blind/dilational
  faults that conduct fluid to springs and vents are systematically under-mapped
  (catalogue maps surface rupture, not blind conduits). Catalogue-flank dots are
  masked (= zero live credit), so discharge-first ranking spends budget where
  masked-catalogue detectors cannot.
- **Differs from focus-9:** no H19-5 input, no dotted-thinning, no prior raster;
  discharge-first (siblings used geothermal only as auxiliary features).
- **Expected DTI / cost:** uncertain (holdout decides); medium cost. Ranked #1
  because it is the only candidate whose support is disjoint-by-construction
  from the exhausted lineage while remaining physically grounded.
- **Mimic:** Lake Lahontan shorelines / basalt flow margins (identical curvature
  + conductivity steps; dominant expected FP).

## H2 (proposed): Euler-depth-cluster thread continuity

- **Layers:** `rtp`, `tmi`, contractor `TMI_up150` (upward-continued 150 m).
- **Signature:** Euler deconvolution depth solutions (contact structural index),
  clustered by depth + location; emission along depth-coherent threads > 1 km.
- **Why off-catalogue:** depth continuity filters shallow noise that dominates
  mapped scarps; deep-rooted threads mark through-going faults with no surface
  trace in cover.
- **Differs:** GEMSDOE40 tried Euler lineaments (0.0355–0.0984) without
  depth-cluster threading or break-even budgeting.
- **Expected / cost:** low–medium / HIGH (Euler implementation + validation).
  Ranked #4: expensive, and magnetic depth needs careful QC.

## H3 (proposed): radiometric alteration-halo lineaments

- **Layers:** `geodawn_rad_u8` (K/Th/U/TC) + `ThK`/`UK`/`UTh` ratios; masked to
  piedmont/alluvium (deep cover) via `depth_to_base_surf`.
- **Signature:** K-enrichment / U-depletion corridors with structure-tensor
  lineament coherence (hydrothermal alteration flanking faults in cover).
- **Why off-catalogue:** alteration halos exist where no scarp was ever mapped.
- **Differs:** GEMSDOE46 fused scarp+radiometrics (0.1589) as a blend, not a
  cover-masked alteration-lineament emission.
- **Expected / cost:** low–medium / medium. Ranked #2: cheap, independent
  physics from H1 (complementary errors).

## H4 (proposed): knickpoint / drainage-deflection lineaments

- **Layers:** `det_elev` + `det_elev_slope` now; USGS 3DEP 1 m DEM later.
- **Signature:** drainage network knickpoint density ridges aligned along
  strike (active bedrock scarps deflect channels without mapped traces).
- **Why off-catalogue:** knickpoints record recent vertical motion the catalogue
  missed.
- **Differs:** GEMSDOE60 tried chi-coherence corridors (0.0351); knickpoint
  density emission differs.
- **Expected / cost:** low / medium-high. Ranked #5: 100 m DEM is too coarse
  for real knickpoints; needs the 1 m DEM links (free, official, obtainable —
  but a heavy lift: 706+ tiles).

## H5 (IMPLEMENTED as control): strain × seismic conjunction

- **Layers:** `geod_2ndinv`, `geod_dilaterate`, `ieq_n100a15`, `deq_n100a15`.
- **Signature:** high 2nd-invariant + dilatant strain where background seismicity
  is elevated but no catalogue fault within 500 m (strain without mapped
  structure = missing fault). Off-catalogue by construction.
- **Differs:** siblings used strain inside supervised stacks; pure conjunction
  emission is untried standalone.
- **Expected / cost:** low (100 km/15° seismic kernels are too smooth; strain is
  smooth) / LOW. Ranked #3 as the cheap negative control: if H5 beats H1, the
  discharge anchor adds nothing and H1 must be revised.

## External-data check

All hypotheses use data already in hand (competition stack + mirrors). H4-at-1m
would need USGS 3DEP tiles (free, official: https://apps.nationalmap.gov/downloader/;
obtainable) — flagged as not-yet-obtained, so H4-full is NOT currently viable;
only its 100 m pilot is.
