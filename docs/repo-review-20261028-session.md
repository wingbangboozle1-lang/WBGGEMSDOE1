# Repository review — Arena session, 2026-10-28

## Outcome

This was a review and consistency pass, not a model experiment. No TIFF was generated, no score claimed, and no competition slot used. The current work branch began clean at `0af5732`.

**Submission decision: no file is approved by this review.** The WBG-6 run card says “promote” and `PROMPT.md`/the first README section previously said “approved to submit.” However, that same run card reports a **99.6767% final-dot forward overlap** with the spacing-5 registry raster (`max_forward_3px_overlap: 0.9967667`). The active protocol sets a >70% stop rule. Its separate density-adjusted “overlap lift” cannot supersede that literal gate. Its holdout is explicitly not used to support the decision because the recorded holdout-to-score external validation failed. This is a direct decision-status contradiction, not evidence that the raster would score poorly or that its format checks failed.

I corrected the top-level README and standing `PROMPT.md` to mark WBG-6 as an archived research artifact, not approved under the active literal gate. The TIFF remains available as a research download. I also corrected the README's unsupported “honest ceiling” language so a model estimate is not presented as a score forecast.

## Scope review

- The Focus-9 summary covers GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, and 36. Its data explicitly labels the historical values `OWNER-REPORTED / UNVERIFIED`, not organizer receipts. It reports historical rasters as non-unique under the recorded 70% comparison rule. Snapshots are stale; they do not establish current cross-site uniqueness.
- The B2 explanation is appropriately qualified as plausible thinning/false-positive pruning, not a demonstrated causal explanation. Hidden labels and exact organizer receipts are unavailable here.
- No current evidence justifies a score estimate for a newly generated raster. A holdout DTI is not a DrivenData leaderboard score. The existing WBG-6 model estimate is especially not decision-grade because its run card itself flags poor external holdout validation.
- The active parallel-run instructions cap work at three experiments/two hours, disallow selecting a live slot, require pre-placement and final registry checks, and prohibit going over the stop thresholds. Therefore this review did not launch another hypothesis or generate a candidate.
- The repository documents missing official competition inputs and lack of DrivenData authentication as blockers. We did not attempt to bypass them or claim hidden data access.

## Verification

- Read `PROMPT.md`, README, WBG-6 run card, Focus-9 executive-summary JSON, and the existing 2026-10-28 review.
- Independently computed the displayed WBG-6 overlap percent from the run-card field: `0.9967666667 × 100 = 99.6767%`; compared it against the active 70% threshold.
- Created an ignored `.venv`, installed project test extras, and ran the full suite: **232 passed**, 15 Rasterio `PendingDeprecationWarning`s. No failures.
- Initial system Python lacked pytest; isolated venv used rather than changing system Python. `.venv/` is ignored.
- `gh pr list --head arena/5efaaa25-wbggemsdoe1` returned no PR. No PR has been opened or merged by this review.

## Current limitations / recommended next actions

1. Resolve the contradiction between the active literal >70% overlap prohibition and prior project exceptions that substituted density-adjusted lift. Keep one policy in the shared evaluator and user-facing documentation; do not relabel an exception as compliance.
2. Restore the authenticated official competition rasters and cached stack using the permitted competition account/workflow. Record hashes and provenance. Current fixtures/mirrors are not a substitute for authenticated source evidence.
3. Refresh all nine sites' rasters and scores from immutable upstream references, then execute the pre-placement and final-dot uniqueness audit. Historical summaries are not live feeds.
4. Have a single declared method lane and its preregistration selected by the authorized selector. Then run the feature-alone leakage canaries and shared buffered-segment holdout; do not run parallel private forks.
5. Ensure the exact sample-submission footprint convention is reconciled with the user-reported portal `[0,1]` error and organizer instructions. Format checks are local evidence, not a portal receipt.
6. Only call a score ORGANIZER-CONFIRMED when a submission-page receipt ties the exact submitted raster/name to that score. Do not publish a projected leaderboard number as a score.

## Run card

```json
{
  "hypothesis": "An explicit literal registry overlap stop rule must dominate any archived adjusted-overlap promotion claim.",
  "mechanism": "Re-evaluate final-dot overlap shown in WBG-6 run-card against the active >70% rule; its archived 99.6767% value exceeds the stop threshold.",
  "named_non_fault_mimic": "The apparent geological lineament signal can be mimicked by lithologic contacts, pluvial strandlines, survey seams, and other non-fault linear structures; this review evaluates no geology.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_label": "No holdout rerun in this review; no score number asserted.",
  "correlation_overlap_vs_registry": "Archived WBG-6 record: forward 3-pixel overlap 99.6767% vs spacing-5 registry raster; >70% stop. No correlation recomputed.",
  "raster_sha256": "e9111de909c6c9669baf71321539e2b30e742334a7dbc66c8ea021d5539401e9 (archived WBG-6; not newly generated)",
  "validator_output": "Archived WBG-6 format checks report single-band float32, matching grid, finite values in [0,1], and zero outside footprint. Not rerun here; no NaN inside footprint per its recorded check. This does not override uniqueness stop.",
  "submission_name": "wbg6-qmh-kdisjoint-30000-20261028",
  "note": "WBG-6 archived research raster; active literal registry gate fails; do not submit.",
  "verdict": "negative"
}
```
