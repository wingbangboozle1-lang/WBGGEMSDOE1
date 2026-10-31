# Geological hypotheses ranked on 31 Oct 2026 (WBG31 lane)

**Status:** research only. DOWNLOAD: research only. **SUBMIT: NO.** `submission_slots_used` = 0 in this lane; promotion authorised: false.

Every number here is labelled. HOLDOUT-DTI = shared instrument `gems57-pooled-hide-v2`, with n withheld positives and a 95% paired CI. REGISTRY-MEASUREMENT = local overlap or Spearman against cached rasters. OWNER-REPORTED = scores from the owner's uploads, not organizer-confirmed. No projection is written as a score. The public leaderboard figures in the README are ORGANIZER-CONFIRMED page reads, not receipts for any file here.

## Candidates (3 to 5), ranked

| Rank | Hypothesis | Layers / signature | Why it might catch a blind fault | Named non-fault mimic | How it differs from what is in the repo | Status |
|---|---|---|---|---|---|---|
| 1 | **Multi-index Euler solution density** (WBG31-E1) | Magnetic TMI band 14 with vertical derivative band 9 (N=0 contact, N=1 thin sheet); gravity band 13 with band 11 (N=0 and N=1). Solutions kept in their 7x7-cell window at 50–3000 m depth; Gaussian density σ=3 cells. | Potential-field contacts from a juxtaposition can be visible without a mapped scarp; the solutions localize the source edge. | Dike and sill margins, lithologic or basin contacts, leveling seams, noise on straight edges. | No Euler operator found in src/, vendor/ or scripts/. Neighbours that differ: WBG-C1 Hessian commutator, WBG-S2 CGMD cross-gradient, WBG-3 SPI and phase congruency, WBG-5 contour-relative texture, PJMF Frangi ridges. Novelty is within this repository only. | **Tested, negative** (below). |
| 2 | Conductivity/depth Hessian non-coaxiality (WBG-C1) | Bands 17, 15, 8; scale-normalized Hessian commutator. | Misaligned curvature directions may mark a concealed contact. | Oblique basin-fill boundaries. | Already in repo as a pre-registered test. | Tested earlier, negative: HOLDOUT-DTI 0.014045 vs control 0.014146 (gems57-pooled-hide-v2, n withheld 11,330); paired delta −0.000101, 95% CI [−0.000232, +0.000030]. |
| 3 | Depth-contour magnetic texture transport (WBG-2 / WBG-MTA-1 family) | Bands 2, 14, 15; lagged texture change along vs across depth-contour tangents. | A covered offset can change the direction and continuity of magnetic fabric without a scarp. | Volcanic or intrusive contacts, survey leveling. | Related peer texture proposals exist in the repo. | Tested, null: HOLDOUT-DTI 0.131586 vs control 0.130847 (gems-segment-pooled-v1, n withheld 60,988), paired delta +0.000738, 95% CI [−0.004010, +0.005391]. Different instrument from the E1 numbers. |
| 4 | GeoDAWN K/Th/U saddle compositional change | USGS GeoDAWN K/Th/U with terrain saddles; tangent-coherent change across a saddle. | Fracture-controlled alteration can leave a compositional boundary outside mapped traces. | Sorting, weathering, lithology. | Ratio features already exist in peer code; original band semantics and coverage are not yet verified. | Untested; blocked on source verification. |
| 5 | Anisotropic conductivity-boundary persistence | Bands 17 and 15; boundary survival under smoothing along vs across a local orientation tensor. | An elongated concealed discontinuity may persist along strike when a noisy edge does not. | Saline deposits, gridding seams. | Related coherence operators exist; the anisotropic persistence statistic is different. | Untested. |

## Validation of the top candidate (WBG31-E1)

Pre-registration `registry/wbg31_e1_preregistration.json` (SHA-256 817d1eb2…2802da after amendment 2). Spatially blocked holdout: whole catalogue components withheld across four quadrants, with an 8 km training collar. Control: the 19-band HGB model. Candidate: the same model with four Euler density channels added.

**Attempt history (one experiment, counted once):**
- Attempt 1 failed closed with `KeyError 'bootstrap'` because the registration omitted the bootstrap block. Ledger and failure record are kept in `registry/wbg31/`.
- Amendment 2 copied the WBG-C1 bootstrap values verbatim (1000 draws, seed 71614, 95%). The run was then repeated unchanged.

**Results (HOLDOUT-DTI, gems57-pooled-hide-v2, n withheld positives = 11,330):**

| Arm | DTI | 95% CI | Paired delta vs control | Paired 95% CI |
|---|---|---|---|---|
| Control, continuous (WBG-C1 anchor) | 0.014146 | [0.011931, 0.016500] | – | – |
| Candidate, continuous | 0.014076 | [0.011778, 0.016506] | −0.000070 | [−0.000213, +0.000071] |
| Control, dotted 37k | 0.051213 | [0.040839, 0.061867] | – | – |
| Candidate, dotted 37k | 0.051605 | [0.041652, 0.060673] | +0.000392 | [−0.004810, +0.005401] |

- Control reproduces the WBG-C1 anchor exactly (difference 0.0; gate tolerance 1e-6).
- Efficacy gate (candidate paired CI lower bound > 0, for the primary dotted arm): **FAILED**. The secondary continuous arm also fails.
- Canary (single-feature AUC, 23 features): **PASSED**; max orientation-invariant AUC 0.6124 (limit 0.90).
- Registry gate: not run as a promotion gate, but measured anyway (below). The file is not approved.

**Registry measurement** (`scripts/check_uniqueness_full.py`, 453 of 454 distinct accessible rasters; receipt `evidence/wbg31/uniqueness_e1_dots.json`):
- G1 format: PASS (validate.py, all checks).
- G2 exact copy: PASS (none).
- G3 Spearman, full footprint: PASS (max 0.0570 < 0.90).
- G4 literal 3-px overlap: FAIL (max 0.9569 against the r13 lattice; six rasters above 0.70).
- Density-matched lift (`scripts/density_matched_lift.py`, `evidence/wbg31/density_matched_lift_e1.json`): the r13 lattice (206,895 dots, chance overlap 0.9987) has lift 0.958, so the literal test is degenerate there. The real overlaps are 12GEMSDOE r7 scarp (literal 0.622, lift 1.93), GEMSDOE67 ovtr (0.767, lift 1.40), GEMSDOE22 h23-b (0.753, lift 1.41), GEMSDOE77 (0.712, lift 1.29), GEMSDOE3 pindrop (0.812, lift 1.11; 0.758, lift 1.03).

**Decision: closed as negative.** The efficacy gate failed, so no confirmation run is pre-registered and no slot is authorised. Under the protocol, a negative result that prevents a wasted slot counts as a win.

## Irregularities and limitations

- The registry comparison is incomplete by one raster: `14GEMSDOE r5-geom-horse-ensemble` is on a different grid (origin 500000/4500000 instead of 243350/4508550). The offsets are not whole cells, so an exact comparison needs resampling. This row is excluded and flagged.
- The gravity Euler channels are effectively empty (grav N0 0 solutions; N1 9). The primary test is therefore essentially magnetic Euler only.
- Units of the vertical-derivative bands 9 and 11 are unverified. Depth acceptance is a stated assumption.
- Holdout evaluator `gems57-pooled-hide-v2` is a different instrument from the 0.1661 `gems-segment-pooled-v1` benchmark. Numbers are not comparable across the two.
- Inputs are OWNER-MIRROR-INTEGRITY, not organizer-authenticated. The DrivenData data tab requires login and cannot be downloaded from the sandbox. This is a blocker, not worked around.
- The validator requires all values finite. This is stricter than the portal contract (NaN outside footprint may be allowed), so it is conservative.
- Band 6 metadata conflicts with its use as GeoDAWN total count (irregularity from earlier sessions, unresolved).
- Scope: public-catalogue hide-and-recover is not a hidden-new-fault leaderboard estimate.

## Code review (this session)

- `vendor/gems57/metric.py`: exact DTI paths (`dti_binary`, `dti_exact`) agree with the brute-force oracle `dti_bruteforce` as implemented; the kernel, the FP definition and the denominator are as published. No defect found. The docstring warning about IR-57-BAR-01 is consistent with the code.
- `vendor/gems57/validate.py`: no defect found. Limitation above (all-finite policy is stricter than the portal).
- `vendor/gems57/uniqueness.py`: used unmodified. Its registry schema differs from `registry/wbg_h1/uniqueness_registry.json`, which has `cache_path` entries and no `rasters` key. The check script builds a deduplicated index from the SHA-verified fetches instead. Fixing the schema mismatch in the registry file was not done (out of scope for this lane).

## Next

- No further experiment in this lane. E1 is closed.
- The remaining open hypotheses (3 and 5) need source verification and a pre-registration before any run.
- No slot. Promotion is a separate selector step and is not authorised.
