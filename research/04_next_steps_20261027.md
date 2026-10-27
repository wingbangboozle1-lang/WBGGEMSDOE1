# Next work and limitations — 2026-10-27

## Current status (measured, not aspirational)

- **DOWNLOAD: YES (research/audit). SUBMIT: NO.** Two new unique, format-validated TIFFs were
  generated; three preregistered TASC arms were scored on the shared spatially blocked holdout.
  HOLDOUT-DTI: Arm A `0.061528` [0.049811, 0.073808], Arm B `0.001825` [0.000431, 0.003717],
  Arm C `0.005295` [0.002686, 0.008724], `gems-segment-pooled-v1`, n=60,988 withheld positives.
- None beats the frozen current-best point estimate `0.166060`. The best new file is Arm A, not the
  preregistered primary; post-hoc best-arm selection is explicitly **not** a promotion test.
- LLI projections are empirical estimates on 118 USER-REPORTED historical rasters
  (LOO MAE 0.0353), never organizer scores. The official public leaderboard was observed at
  `0.4544` on 2026-10-27; the prompt's `0.4413` / `0.3195` targets are stale.
- Zero weekly slots used. No uploader, authenticated allowance or artifact-linked organizer receipt
  exists here.

## Highest-priority blockers

1. **Resolve the lane.** The prompt still supplies no single-method paragraph. A future session must
   receive an explicit assigned lane before any promotion work.
2. **Resolve the registry policy.** The retained spacing-5 calibration lattice covers ≥70% of the
   footprint within 3 px. By the pigeonhole principle the literal all-entry final-dot overlap gate
   is unsatisfiable for any substantial new dot set. The shared tool's
   `separate_calibration_controls` diagnostic is reported, but this project keeps the literal
   unseparated gate binding. A protocol owner must decide whether space-filling calibration
   controls should be excluded from the 3 px overlap rule while retaining rank gates for all
   entries. Do not privately waive them or target lattice holes.
3. **Obtain an independently authenticated official data manifest.** The core rasters and all 19
   cached band hashes match the pinned public owner mirrors. That proves mirror integrity, not
   organizer-origin authenticity. Resolve ambiguous `tc` / `depth_to_base_surf` band semantics
   before claiming physical mechanisms.
4. **Verify the current weekly allowance and submission receipts.** The official rules allow three
   submissions per week; the submissions page requires login. No credential is stored here. An
   ORGANIZER-CONFIRMED score requires a receipt linking an exact artifact SHA-256 to the result.
5. **Replay the current best.** The `0.166060` S3DEP1 card lacks fold-aligned prediction masks, so
   a paired bootstrap replay is unavailable. A future promotion test needs an identically rerun
   current-best comparator and untouched confirmation.

## Next scientific lane (highest expected value)

**PCE1 — potential-field phase congruency.** Use the already restored 19-band cache (`rtp`,
`tmi_hg`, `tmi`, `iso_grav_anom_hg`). Compute Gaussian-derivative phase congruency at 300, 900 and
1500 m and require cross-field sign persistence. It is **label-free**, so it is not disadvantaged
by hide-and-recover removing visible catalogue faults from the test quadrant — the exact structural
reason TASC failed. Preregister fixed scales and a single emission policy before running; test every
channel with the shared single-feature AUC canary; compare against a replayed label-free control
with a paired 10 km block bootstrap. No external download needed.

Second queue item: **CLR1 radiometric compositional closure residual** using the restored
GeoDAWN-derived K/Th/U bands. Third: **DIFF1** raw 3DEP scarp-profile diffusion invariant — needs
raw 1 m/10 m DEM tiles (official public-domain source:
[USGS 3DEP collection](https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5)) whose
bulk hosts are outside this sandbox's allowlist. Fourth: **MT3D** depth-persistent conductivity
edges using [USGS Great Basin 3-D MT conductance maps](https://doi.org/10.5066/P9TWT2LU), also
not bulk-obtainable here. Both official pages were verified; no hallucinated local mirror is
claimed.

## Engineering / audit improvements

- Add a small 2-D U-Net or steerable-ridge baseline to the shared CPU pipeline (the official
  [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) uses a
  Monte-Carlo U-Net). It should be evaluated with the same `SegmentHoldout`, not a private split.
- Package the LLI calibrator's mean/std with its standardized weights so projections can be
  recomputed without refitting all 118 rasters; keep the corrected
  `USER-REPORTED / NOT ORGANIZER-CONFIRMED` label.
- Extend the registry snapshot beyond nine focus sites and 179 unique rasters; the user listed
  many more sites and later upstream commits changed after the audit.
- Preserve the three-pass review discipline: rebuild pages from measured JSON, run `pytest`,
  validate exact TIFF/ZIP bytes, run the optional rendered-site check, and never let a feed refresh
  alter a scientific verdict.

## What NOT to do

- Do not resubmit GEMSDOE32 B2 (`0.2778`) or any decoded clone of GEMSDOE25/GEMSDOE30.
- Do not treat an LLI projection, HOLDOUT-DTI or public leaderboard value as an organizer score for
  a project file.
- Do not place dots in lattice holes to manufacture uniqueness.
- Do not claim geothermal vents were discovered; the competition target is faults, and expert
  verification is required.
