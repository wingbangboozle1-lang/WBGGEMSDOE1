# Starting point for every session

0. **Current submittable artifact (2026-10-27): `docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif`.**
   Unique against all nine focus sites (max 1.18x chance overlap, max |rho| 0.009), format-valid,
   zeros-mode, sha256 `f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3`.
   Estimated score **0.2824** (MODEL-ESTIMATE; 95% 0.2795-0.2853) - **not** organizer-confirmed and
   only +0.0046 over the best focus-site artifact, i.e. a tie within model error. Read
   `docs/wbg2.html` and `evidence/wbg2/run_card.json` first. The WBG-C1/TIP1/MVGZ/WBG-H1 artifacts
   remain NEGATIVE; nothing else here is cleared to upload.

1. Read `README.md` **including the archived standing prompt**, then the 2026-10-27 follow-up at
   `research/03_followup_review_20261027.md`, `evidence/portfolio_review_20261027.json`,
   `docs/review-20261027.md`, `evidence/release_review_20261027.json`, `registry/run_card.json`,
   `registry/irregularities.json`, `registry/experiment_ledger.json` and `registry/preregistration.json`.
   The prompt is intent, not evidence. **Only the WBG-2 file in item 0 is cleared to upload.**
   WBG-C1, TIP1, MVGZ and WBG-H1 remain **NEGATIVE / DO NOT SUBMIT**. The 2026-10-27 follow-up added
   zero experiments.
2. The original checkout contained only a title. Do not invent prior local training, pending tasks,
   organizer receipts, lane assignments, scores, GPU requirements or authenticated data access.
3. No assigned single-method paragraph was supplied. WBG-C1 is provisional research only. Its
   surface duplicate STOP is binding. Do not reset its ledger, delete negative results, rerun/tune
   it, place final dots, target registry holes or waive a dense/lattice prior privately.
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
