# WBG-3 — five ranked candidate hypotheses (pre-registered 2026-10-27, before WBG-3 fitting)

Evidence classes: HOLDOUT-DTI = locally measured with `gems-segment-pooled-v1`;
OWNER-REPORTED = value in the session brief / site README, no organizer receipt;
MODEL-ESTIMATE = projection, never a score. Official problem statement (fetched
2026-10-27): the scored test faults are *expert-identified faults not in the
USGS catalogue* — https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
Metric: DTI α=0.2, β=0.8, triangular kernel R=300 m (same page, "Performance metric").

| Rank | Hypothesis | Layers | Physical signature | Why it should catch a catalogue-missing fault | Named non-fault mimic | Difference from this repo | Expected value / cost / data |
|---:|---|---|---|---|---|---|---|
| 1 — EXECUTED (WBG-3) | Learned multi-physics detector + clearance dotted emission | Official `training_features.tif` 19 bands (SHA-256 `4371c82e…23bc5`); 3DEP LiDAR scarp stack 12 bands (`d580bb8b…e568`); GeoDAWN radiometric 4 bands (`c22420f7…a682`) + extensions 4 bands (`a35a9c6d…e82e`); gradient magnitudes of depth-to-basement, conductivity, detrended elevation, gravity, RTP | HGB learns the joint signature of mapped faults (magnetic/gravity gradients, basement step, conductivity edge, scarp step/coherence, radiometric alteration); emission is dotted (≥3 px spacing), excludes ≤2 px around the visible catalogue | Expert-mapped new faults share the geophysical expression of mapped faults but were missed because they are subtle/buried; a joint detector ranks them above single-layer lanes. Clearance removes dots that merely retrace known faults, which earn no credit against new-fault truth (measured: champion deleted exactly 6,436 such dots, `evidence/h33_b2_forensics.json`) | Range-front alluvial aprons and lithologic contacts produce coincident gravity/magnetic steps without faulting | Prior lanes here used single physics families, hand-weighted products (WBG-2 `features.py`), or catalogue geometry only (WBG-2 prior). None trained a supervised detector on the restored 19-band official stack in this repo (it was previously declared absent — see IR below) | Highest / ~20 min CPU / all bytes restored and hash-verified this session from the pinned GitHub bridge (`buffedlizard55-lab/6GEMSDOE@e2fe3f41`, `GEMSDOE24@07345ea0`) |
| 2 | Upward-continuation structural-index attenuation | `tmi`, `tmi_hg`, `tmi_vg`, `TMI_up150` | Persistence of magnetic gradient from 0→150 m continuation separates deep fault contacts (slow decay) from surficial volcanic float (fast decay) | Buried intrabasin faults keep coherent contacts at depth | Dipping pluton contacts; flight-line levelling stripes | Euler lanes solved local inversions; nobody used the 0→150 m decay rate as primary in this repo | Moderate / low / bytes present (`geodawn_extensions_u8.tif`) — viable next lane |
| 3 | MT clay-cap perimeter + K/Th halo asymmetry | `cond_surf`, `depth_to_base_surf`, GeoDAWN K/Th/U | Rangeward lateral gradient of log-conductivity gated by K-enrichment, playa toe excluded | Blind geothermal faults bound conductive alteration caps with no scarp | Saline playa / lithium-brine margins | Prior lanes used isotropic conductivity products, not asymmetric perimeter gradients | Moderate, localized / low / bytes present |
| 4 | Fault-tip & stepover continuation of the visible catalogue | `labels.tif` only | Terminal strike projection + en-échelon stepover linking, geometry only | New faults commonly continue or step over from mapped segments | Paleo-shorelines and terrace edges collinear with tips | H33D grafted tips onto an inherited mask; a standalone geometry-only lane was not holdout-tested here | Low-moderate / very low / bytes present. Ranked below detector lanes because B2 forensics show near-catalogue dots earn little |
| 5 | Wash-deflection collinearity on raw 1 m DEM | USGS 3DEP 1 m tiles via `1m_DEM_links.csv` | Multi-catchment lateral channel offsets (5–30 m) | Strike-slip faults with no vertical scarp offset drainages | Strike ridges causing stream capture | DKRN1 ran D8 at 100 m and was negative | Potentially high in Walker Lane / very high (>200 GB). Official free source: USGS 3DEP https://www.usgs.gov/3d-elevation-program — obtainable but not viable in this sandbox session |

## Irregularities flagged

- **IR-WBG3-01 (leakage by construction, found and fixed in Pass 2).** WBG-3 v1 fed
  log-distance-to-visible and visible-KDE as detector features while sampling
  negatives ≥9 px from the catalogue. Every positive sits at distance 0 to the
  visible set (itself), so the features separated training classes perfectly;
  the fold surface degenerated to a constant off-catalogue (fold AUC 0.500,
  HOLDOUT-DTI 0.0479 for all arms, E1≡E2). Fixed: catalogue-distance features
  dropped from the detector; negatives are all non-positive train pixels.
  Canary on the 42 static features passed before and after (max symmetric AUC 0.598 < 0.90).
- **IR-WBG2-EST (invalid score estimator, WBG-2 demoted).** The WBG-2 estimate
  0.2824 came from regressing nine OWNER-REPORTED live values on
  near-catalogue fraction + log-budget. Those nine artifacts are one nested
  deletion family, so the regression fits lineage, not a general law; it assigns
  0.2824 to WBG-2's scattered off-catalogue field whose measured DTI against
  the champion field is 0.067 and which has zero measured catalogue-holdout
  support by construction. WBG-2 is reclassified **DO NOT SUBMIT** (research
  download only). See run card.
- **IR-HOLDOUT-REVERSE.** The champion raster scored HOLDOUT-DTI 0.0067 when
  passed whole to `SegmentHoldout`, because its catalogue clearance was computed
  against the *full* catalogue including withheld components. That number is a
  pessimistic artifact of evaluation design, not evidence the champion is weak;
  it is reported only with this caveat and never used as a comparator.
