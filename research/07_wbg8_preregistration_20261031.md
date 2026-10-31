# WBG-8 preregistration — multi-physic hidden-corridor emission (31 Oct 2026)

**Status:** preregistered before any WBG-8 dot is placed. This file fixes the hypotheses, the
channels, the instruments, the selection rules and the budget. Deviations must be recorded in the
run card, not silently applied.

**Lane (single method paragraph).** WBG-8 estimates where faults exist that are *not* in the public
USGS/INGENIOUS catalogue by rank-blending four **catalogue-free** propensity channels — (1) LiDAR
scarp expression (2 m `ex_max` × `coh100` from USGS 3DEP), (2) buried-basement lineament corridors
(`depth_to_base_surf` + `det_elev` gradient coherence with a thin-cover gate), (3) potential-field
edge concordance (`tmi_hg` × `iso_grav_anom_hg`), (4) radiometric alteration × conductance
(GeoDAWN K/Th alteration × `cond_surf`) — and emitting a fixed budget of ≥3-px non-redundant binary
dots by descending propensity, with zero support within 3 px (300 m) of the mapped catalogue. No
catalogue-derived feature enters the propensity; the catalogue enters only as the neutral mask the
organizer also applies. This is a different lane from every previous WBGGEMSDOE1 artifact: none of
them blended LiDAR geomorphology, basement-cover morphometry, potential-field concordance and
radiometric alteration into a budgeted, catalogue-neutral dot field selected by an off-catalogue
proxy truth.

## Why the metric rewards this (from the official formula, verified in `vendor/gems57/metric.py`)

- `TP_w` saturates per truth pixel (max over dots × triangular kernel, R = 3 px) → redundant dots
  only add `FP_w`; sparse, non-redundant dot sets dominate continuous corridors (empirically:
  dotted d2.8 0.2600 vs its continuous parent 0.1922, OWNER-REPORTED).
- `FN_w` carries β = 0.8 versus α = 0.2 for `FP_w` → coverage of hidden faults is 4× more valuable
  per unit than precision; spread over all plausible corridors rather than a few confident spots.
- Catalogue pixels are excluded from both TP and FP → dots on the catalogue are wasted budget, and
  dots 1–2 px off it earn almost nothing (B2's deletion of 6,436 such dots, +0.0178 OWNER-REPORTED).
- A non-redundant dot helps iff its kernel self-credit `k > α·DTI ≈ 0.056`, i.e. hidden truth within
  ≈2.8 px. Placement must maximise the chance that a hidden fault passes within ~280 m.

## Ranked candidate hypotheses (all catalogue-free; layers + signature + why non-catalogue + novelty)

| Rank | ID | Layers | Physical signature | Why it catches a fault missing from USGS/INGENIOUS | Difference from anything implemented in this repo | Expected DTI gain | Cost |
|---|---|---|---|---|---|---|---|
| 1 | H8-1 blend | LiDAR `ex_max`,`coh100` + `depth_to_base_surf` (15), `det_elev` (12) | Youthful scarp expression (2 m slope excess coherent along strike) over buried-basement lineaments in thin cover | Expert-mapped new faults are small-throw geomorphic detections that regional compilations miss; basement lineaments under thin cover are where they survive | `wbg2.features.fault_evidence` gated lidar by alteration but had no basement-cover morphometry; `scarp_offcat` (29 Oct) used `ex_max×coh100` alone at K=36,800; DIFF1 used lobe symmetry; none blended basement-cover windows with the marginal-budget emission | highest (frontier family mechanism + burial targeting) | low (all rasters local) |
| 2 | H8-2 rad-cond | GeoDAWN K/Th/U (`geodawn_rad_u8`) + `cond_surf` (17) | K-enrichment (adularia/lichenite upflow) co-located with conductive clay alteration, off-catalogue | Blind geothermal systems express as alteration halos without surface rupture; the hidden-fault experts use exactly this convergent evidence (Faulds et al. 2019) | Radiometric alteration appears only as a 0.6+0.4·alter gate inside `wbg2.fault_evidence`; no repo lane emitted alteration×conductance windows; peer GEMSDOE46 r11f (scarp+radiometric fusion, 0.1589) is a different operator and is a registry raster we audit against | moderate | low |
| 3 | H8-3 pf-nodes | `tmi_hg` (3), `iso_grav_anom_hg` (18) | Co-located magnetic and gravity horizontal-gradient ridges = crustal-scale fault zones with damage-zone splays | Blind splays and step-over segments cluster near through-going basement faults that offset both density and magnetization; many are unmapped at Quaternary scale | Focus-9 `novel-band3to8/12` emitted per-band edges, not co-located ridge nodes; C1 commutator used cross-scale curvature misalignment; no repo lane emitted magnetic×gravity concordance nodes | moderate | low |
| 4 | H8-4 strain-fabric | `geod_shearrate` (7), `geod_2ndinv` (4), `rtp` (2) texture | Geodetic shear-direction misalignment with basement magnetic fabric → distributed faulting corridors | Interseismic strain accrues on buried faults too; fabric misalignment marks accommodation zones where unmapped faults concentrate | MKSF (WBG-S2) used geodetic stress invariants as an emission field; this uses the *misalignment angle* between strain and magnetic texture, never used in-repo | low-moderate | medium |
| 5 | H8-5 sgmc-react | SGMC off-catalogue traces (`sgmc_faults_100m.tif`) | Distance-decay corridors along pre-Quaternary bedrock faults outside the mapped union | Geothermal conduits reactivate older bedrock faults omitted from Holocene-scarp-centric catalogues (WBG-S2 H3 rationale) | WBG-S2 proposed SGMC-DualPop as a *training weight* (never run); peers' SGMC-only fields scored 0.0492–0.0512 (OWNER-REPORTED); here it is one propensity channel only | low alone | low |

**Named non-fault mimics (all channels):** roads/canal banks/terrace risers/paleo-shorelines
(Lake Lahontan)/landslides/mines (LiDAR); depositional pinch-outs and volcanic flow fronts
(basement morphometry); intrusive contacts and remanence changes (potential fields); sediment
sorting, weathering/moisture attenuation and lithologic contacts (radiometrics).

## Instruments (labels fixed here)

1. **HOLDOUT-DTI** — `gems57-pooled-hide-v2`: `buffered_component_draw(seed=71614, hide_frac=0.2,
   buffer_px=3, boundary_px=12)`; per-fold fold-safe replay (dots regenerated from the fold's
   visible catalogue mask only — channels are catalogue-free so they never change); pooled summary
   with 20 km block bootstrap (`pooled_summary`, 1000 draws, seed 520810). Known defect (AGENTS 0b-i):
   this instrument does not rank real submissions (Spearman 0.144); it is reported, never called a
   score.
2. **PROXY-DTI** — `gems57` off-catalogue proxy truth `sgmc & ~catalogue & footprint` rebuilt from
   template-pinned `sgmc_faults_100m.tif` (sha256 26d142c4…). Distance-weighted Tversky against
   faults that exist in the state compilation but not in the competition catalogue: the closest
   available analogue of "faults not contained in the current public USGS database". Labelled
   `PROXY-DTI (gems57-offcatalogue-proxy)`, never a score.
3. **Leakage canary** — per-channel AUC of the channel alone vs withheld truth inside the fold's
   scorable domain; AUC > 0.90 ⇒ leakage until proven otherwise ⇒ channel dropped.
4. **Uniqueness** — two-phase (surface before placement, final dots): Spearman on a deterministic
   200k-pixel footprint sample and literal 3-px forward dot overlap against every cached registry
   raster (focus-site downloads + scored registry + this repo's own downloads), plus byte and
   normalised-pixel hash comparison. The literal 70 % gate is degenerate against dense lattices
   (AGENTS 0b-ii): literal results are reported per raster, and the density-matched overlap lift is
   the working drift test.

## Pre-registered experiments (budget: 3)

- **EXP1 — channel screens and blend selection.** Compute all four channels; run canaries; score
  every single channel, the equal-rank blend of all, and the top-2 blend at K = 37,654 on the
  selection draw (seed 71614) with PROXY-DTI; score the 11 focus champions plus `scarp_offcat` and
  `wbg2` on the same PROXY instrument and correlate with OWNER-REPORTED scores (estimator check).
  Selection rule R1: drop canary failures. R2: highest selection-draw PROXY-DTI wins; ties within
  0.002 prefer the blend with more channels.
- **EXP2 — budget and efficacy.** On the winning surface, K ∈ {30,000; 34,000; 37,654; 42,000;
  50,000}, min separation 3 px, NMS window 7. R3: highest selection-draw PROXY-DTI wins; ties
  within 0.002 prefer the smaller K. Report-draw instruments: HOLDOUT-DTI (fold-safe) and PROXY-DTI
  with paired CIs versus (a) a same-mask Poisson control at the same budget and (b) the B2 champion
  raster on the same instruments.
- **EXP3 — gates and packaging.** Final raster through `submission_writer.write_submission` (name +
  ≤140-char note, catalogue-neutral, zeros outside), full validator receipt, two-phase uniqueness
  audit, score estimate (family band + proxy-calibrated model, both labelled MODEL-ESTIMATE), one
  JSON run card, executive summary + how-to-submit pages, tests.

## Score-estimate policy (labels)

Every number in the deliverables is `HOLDOUT-DTI` (evaluator version, withheld positives, 95 % CI),
`PROXY-DTI`, `MODEL-ESTIMATE` (method + interval stated), `OWNER-REPORTED` (copied from the session
history, unverified) or `ORGANIZER-CONFIRMED` (submission-page receipt — none exists in this
project). A projection is never written as a score. Promotion to a weekly slot is a separate
selector step (weekly cap per the official rules §3.2).

## Data provenance (hash-pinned owner mirrors; organizer origin not authenticated)

- 19-band GeoDAWN stack `training_features.tif` sha256 `4371c82e…` (bridge, assembled from 5 parts).
- `labels.tif`/`existing_faults.tif` sha256 `7ba308cc…` (the public catalogue = 60,988 px).
- `sample_submission.tif` sha256 `2176d08e…` (grid template).
- `lidar_scarp_features_u8.tif` sha256 `d580bb8b…` (USGS 3DEP-derived, GEMSDOE24 mirror).
- `geodawn_rad_u8.tif` (GeoDAWN radiometrics, GEMSDOE24 mirror) and `sgmc_faults_100m.tif` sha256
  `26d142c4…` + `derived_sgmc_faults_100m.tif` sha256 `643cbe99…` (57GEMSDOE template pins).
- Official sources: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ ,
  https://docs.nlr.gov/docs/fy26osti/96647.pdf ,
  https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
  (DOI 10.5066/P93LGLVQ), https://gbcge.org/current-projects/ingenious/ ,
  https://gdr.openei.org/submissions/1391 (DOI 10.15121/1881483).
