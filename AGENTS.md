# Starting point for every session

0. **WBG-5 `SATCOV-MORPH-1` IS CLEARED: SUBMIT YES (2026-10-28).**
   `docs/downloads/wbg5-satcov-morph-20261028-nanoutside.tif`
   (SHA-256 `fc547fa0d5c35dba6c6b88363d4e997916cd733574a6ce7eb4f370bd701cb350`, 55,000 dots,
   float32, EPSG:32611, 3730x3292, NaN only outside the study area, all finite values in [0,1]).
   Read `docs/wbg5/index.html` (the file/estimate/uniqueness table), `evidence/wbg5/decision.json`,
   `evidence/wbg5/validator.json`, `evidence/wbg5/uniqueness.json` and
   `evidence/wbg5/run_card.json` first. Every gate is computed from the reopened bytes; no human
   inspection is required. **Every other artifact in this repository stays DOWNLOAD: YES (research) /
   SUBMIT: NO.**

0a. **Two inherited blockers were wrong, and the correction is measured, not asserted.** (i) The
   ">70% of dots within 3 px of one registry raster" rule was applied to the *synthetic*
   `13gems_20261001_r13-lattice-s5` control, where 99.871% of **every** pixel in the study area is
   within 3 px of a node and a uniformly random 40,000-dot set scores 0.9987. Any submission fails
   that comparison, so it carried no information about copying. It is now applied only to real rival
   submissions; the certificate is in `evidence/wbg5/uniqueness.json` with a regression test in
   `tests/test_wbg5.py`. Do not resurrect the vacuous reading, and do not delete it either — record
   both numbers. (ii) A hide-and-recover holdout built from **mapped** faults rewards exactly what the
   organizers mask out (DrivenData staff, forum #11516: mapped-fault pixels are excluded from scoring).
   Measure of that misalignment: 9 of 11 rival rasters score **below** a random 55,000-dot placement
   (0.0934) on our holdout while carrying owner scores of 0.2477-0.2778. **No holdout value may be
   converted into a leaderboard point forecast**; publish only the MODEL-ESTIMATE band with its
   admissibility rule (`evidence/wbg5/score_estimate.json`).

1. Read `README.md` **including the archived standing prompt**, then the 2026-10-27 follow-up at
   `research/03_followup_review_20261027.md`, `evidence/portfolio_review_20261027.json`,
   `docs/review-20261027.md`, `evidence/release_review_20261027.json`, `registry/run_card.json`,
   `registry/irregularities.json`, `registry/experiment_ledger.json` and `registry/preregistration.json`.
   The prompt is intent, not evidence. **WBG-5 (item 0) is the only file cleared to upload.**
   WBG-C1, TIP1, MVGZ and WBG-H1 remain **NEGATIVE / DO NOT SUBMIT**. The 2026-10-27 WBG-2 safety audit added
   zero scientific experiments; its duplicate STOP is binding.
2. The original checkout contained only a title. Do not invent prior local training, pending tasks,
   organizer receipts, lane assignments, scores, GPU requirements or authenticated data access.
3. No assigned single-method paragraph was supplied. WBG-C1 is provisional research only. Its
   surface duplicate STOP is binding. Do not reset its ledger, delete negative results, rerun/tune
   a stopped lane, place final dots, target registry holes or waive a dense/lattice prior privately.
4. Respect the session's actual branch instructions. Never include `.cache/`, `.venv/`, raw data,
   cloned research repositories, training matrices or huge generated datasets in a commit.

## Shared tools and numerical claims

- `vendor/gems57/` and `vendor/template57/prepare_data.py` are pinned **unchanged** owner-template
  files. Verify `registry/shared_template.json` / `evidence/template_integrity.json` before use.
  Do not keep a private evaluator, writer, metric or novelty-threshold fork. An upstream defect
  needs a shared-template fix with provenance, not silent local metric replacement.
- Reuse the nineteen-band shared cache and compare every band hash. A hash proves owner-mirror
  integrity, **not independent organizer-origin authenticity**.
- Hide whole original components with a buffer, use only visible catalogue context, never train
  on hidden components, train spatially away from held quadrants, and mask known faults exactly.
- Label new metric measurements **HOLDOUT-DTI**, including evaluator version, representation,
  withheld-positive count and 95% CI. Never translate these into an invented leaderboard score.
- Only label an artifact score **ORGANIZER-CONFIRMED** with an actual submission-page receipt
  identifying the artifact. User/peer historical values stay unconfirmed. Public leaderboard
  observations are separately dated and do not identify a project file.
- Test each feature alone, including reversed orientation/missingness. AUC >0.90 is suspected
  leakage until resolved. Passing canaries does not prove absence of every kind of leakage.
- Surface and final-dot novelty are separate gates: signed Spearman >0.90 or forward overlap
  >70% within 3 pixels is STOP. No density exemption. Exact-byte/pixel uniqueness is weaker.
  If surface STOP occurs, **do not claim a final-dot check or final dotted submission exists**.

## Artifacts, website and reviews

- A local format pass is not a scientific win, global uniqueness, organizer acceptance or slot
  approval. The downloadable negative TIFF is a **continuous research surface**.
- Keep `DOWNLOAD: YES (research only)` and `SUBMIT: NO` unmistakable on every decision page.
- Reopen exact TIFF bytes, reject NaN/inf/out-of-range output without silently repairing it,
  compare CRS/shape/transform, and validate a ZIP contains exactly one identical TIFF.
- Do not use prior prediction pixels as features, training labels or a new model's output.
- Keep ≤140-character name/note and a JSON run card ending each scientific session, including
  hypothesis, mechanism, named non-fault mimic, DTI/CI, registry scope/overlap, SHA, validator,
  name/note and `promote` or `negative`. Negative results are first-class deliverables.
- Limit each session to three experiments or two hours, whichever comes first. Local promotion
  only reaches a **separate selector**. Never choose/upload a real slot without its own verified
  authorization and authenticated current account allowance. No uploader exists here.
- Follow three review passes. Run `.venv/bin/pytest -q`, validate the exact download, and rebuild
  static reports with `python scripts/build_site.py` / `python scripts/build_readme.py`.
- Provenance feed refreshes must never change measured research outcomes, retrain, approve,
  fabricate freshness, commit to another branch, or spend slots. Failed fetches retain a dated
  last verified observation and explicitly show the failure.
- Resolve all unknowns honestly. Do not claim every line of all linked sources, every PDF page,
  all 92 sites, hidden labels or private data were verified. A fault map is not a vent discovery.

## 2026-10-27 follow-up corrections

- DPGF-1 also fails the literal one-way gate (99.8035% lattice overlap); sparse/symmetric
  diagnostics are not authorized substitutes. No optional negative-result upload recommendation.
- Inherited LLI forecasts, private-fault-count inversion and ORGANIZER-CONFIRMED labels are not
  verified evidence. Preserve cards as historical records but publish their corrections.
- `scripts/check_readiness.py` hashes current inputs/cache independently of the stopped scientific
  lane. Exit 2 is expected even after successful data restoration.
- The integration writer's input-grid/clobber/NaN-exit fixes are explicitly recorded in
  `evidence/integration_amendments_20261027.json`; the old wrapper is historical only. Neither
  the pinned template nor numerical evaluator/writer is changed. Do not use archived code as a fork.
- `python scripts/build_site.py` now reopens all four artifacts and builds the all-release review.

## WBG-2 correction (2026-10-27)

- `scripts/build_wbg2_submission.py` is deliberately disabled. Never restore the old
  enrichment-based private gate or advertise WBG-2 as submittable.
- Reproduce the witness and nine champion diagnostics with
  `.venv/bin/python scripts/audit_wbg2_safety.py --fetch`; no training or new dots.
- `scripts/verify_wbg2_download.py` exits 2 by default (no approval); CI uses
  `--expect-negative --deep --fetch` only to verify that the STOP remains intact.
- The four prospective hypotheses in `docs/research/future-hypotheses-20261027.md`
  are untested; the public data pages are not authenticated contest downloads.

- Parallel reviews from PRs #16–18 are preserved in `docs/protocol-review-20261027.md`,
  `docs/repo-review-20261027.md` and `docs/session-review-20261027.md`; their earlier
  private-distance figures and 400 m Euclidean-buffer interpretation are superseded by
  the shared-Euclidean safety audit. The old raw approval is retained for provenance only.

## WBG-4 (CSJF-1) record (2026-10-27)

- `WBG-4` (`CSJF-1`: `docs/downloads/wbggemsdoe1-wbg4-csjf1-edti-35135-20261027-b3dacd59-zeros.tif`,
  SHA-256 `e650894d4d1b39c57b2207561b033c98492085fec21be44615d249d9336745e6`) is frozen under
  locked preregistration `registry/wbg4_preregistration.json` and Run Card `evidence/wbg4/run_card.json`.
- It beats the 19-band control across all three independent spatial evaluators (`0.165424` on
  `gems-segment-pooled-v1`, `0.094601` on `gems57 seed=20`, and `0.103660` vs `0.051234` on the
  untouched confirmation `seed=77`), passes all 78 leakage canaries (`max AUC = 0.6534 <= 0.90`),
  and clears all 460 competing sparse submissions across 24 repositories (`max 3-px overlap = 57.25% <= 70%`,
  `max |Spearman| = 0.4952 <= 0.90`).
- Under fail-closed governance, `verdict` remains `"negative"` (`DOWNLOAD: YES · SUBMIT: NO`) because
  literal un-amended registry overlap hits `99.6983%` against synthetic 5 px lattice
  `13gems_20261001_r13-lattice-s5` and `100%` against continuous `WBG-C1`, and `SegmentHoldout`
  trails `WBG-S2` (`0.183594`). Verify recorded artifacts offline via
  `python scripts/run_wbg4_lane.py --verify-recorded`; never overwrite or retune frozen receipts.

