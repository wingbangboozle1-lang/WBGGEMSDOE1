# Follow-up review — 27 October 2026

## Decision: no eligible contest file

This is a continuation of the frozen WBG-C1 lane, not a new experiment allowance.
The active branch started at `998878029d02b749fbb7e5c71003d89c1a177320` with four
research TIFFs, several parallel evaluators, and a binding WBG-C1 duplicate STOP.
No single-method lane paragraph is present in the repeated request. No budget,
registry threshold, or negative verdict has been reset. No real slot was used.

All four local releases have now been reopened using the unchanged pinned
`gems57.validate` validator. Checks additionally bind exact file hashes to the
source cards, compare the saved CRS/shape/transform with the hash-pinned mirror
reference, and reopen each existing ZIP to verify its sole member equals the TIFF.
See [the full review](../evidence/portfolio_review_20261027.json).
This is file validation, **not a new scientific efficacy or registry experiment**.
The four decoded arrays differ from each other; that does not establish lane
uniqueness against the competition registry.

## Findings corrected in the published project

1. **Receipt laundering.** The inherited WBG-H1 page called supplied scores
   ORGANIZER-CONFIRMED. Its source cards contain no submission-page receipt
   binding those exact bytes to those values. The replacement page labels the
   GEMSDOE32 historical value USER-REPORTED / NOT ORGANIZER-CONFIRMED. The
   original cards are preserved as historical records, not endorsed forecasts.
2. **Unauthorized uniqueness exemption.** DPGF-1's recorded one-way overlap is
   99.8035% against the registered lattice and 88.32% against a dense slab. Passing
   sparse-only or symmetric overlap cannot override the literal >70% STOP.
   The site no longer invites optional uploads of this negative result.
3. **Private-label inversion is not identified.** A rounded reported lattice
   result and an assumed mean kernel response cannot reveal the hidden fault
   count or weighted recall. The response depends on unknown fault locations,
   footprint effects and max-cover geometry. Many truth configurations can
   produce the same scalar result. Exact raster set relations are useful;
   inferring private labels from a spatial mean is not verified evidence.
4. **Range-error certainty.** A locally strict all-finite [0,1] file is a prudent
   export policy, not proof about the portal implementation or the cause of a
   previous rejection without its exact bytes. No organizer acceptance is claimed.
5. **Writer integration bug.** `scripts/submission_writer.py` accepted TIFF arrays
   after discarding mismatched source georeferencing. The shared integration CLI
   now checks the input grid before calling the same existing writer. It rejects
   output/receipt aliases of input files, and returns non-success for explicit
   NaN-exterior compatibility twins under the local portal-safe policy.
   The pinned template and numerical metric/writer are untouched. The old wrapper
   is archived for provenance with an explicit hash amendment, not used as a fork.
6. **Stale readiness.** The old readiness command looked for an unused DEM-links
   CSV, ignored the actual nineteen-band cache, and always reported no generated
   TIFF. The replacement hashes the three real core inputs, all template sources,
   cache files, and the existing artifact. It still fails closed on the stopped lane.

## Autonomous data placement completed

Executed the existing `bash scripts/download_competition_data.sh` and
`.venv/bin/python scripts/prepare_data.py`. The three core mirror digests and all
nineteen expected cached band hashes match the pins. Large data/cache files remain
ignored by Git; a fresh clone must restore them again. A CPU is sufficient for
these operations. Nothing here authenticates the bytes independently to the
organizer or resolves ambiguous layer semantics.

## Hypothesis status and next-session ordering

The four preregistered candidate hypotheses, with layers, physical signatures,
missing-catalogue rationale, mimics, novelty limitations and cost ranking, are in
[the existing hypothesis register](../docs/hypotheses.md). WBG-C1 was tried and
stopped. Magnetic texture transport, radiometric saddle composition, and
conductivity-boundary persistence remain proposals, not validated improvements.
It would violate the lane protocol to execute another method in this session.
No numerical DTI improvement forecast or new claimed geological discovery is made.

Before a future authorized lane starts:

1. Resolve the missing lane and near-saturating registry obstruction centrally;
   do not privately exempt priors, optimize against registry holes, or reset WBG-C1.
2. Authenticate input provenance and original layer meanings; reserve untouched
   confirmation and a reproducible same-instrument current-best comparator.
3. Reuse shared canaries and whole-segment buffered holdout; derive all catalogue
   features only from visible faults and mask visible faults pixel-exactly.
4. Compare efficacy with paired uncertainty, then literal surface/final-dot novelty
   and exact-artifact validation. A local promotion is still not a live slot.
5. Keep leaderboard estimates unavailable until there is a defensible, independent
   calibration; keep historical claims unconfirmed without receipts.

## Sources and verification scope

- Official reference solution, immutable README inspected through GitHub API on
  2026-10-27:
  https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md
  It directs users to download competition data separately and supports CPU-only
  execution; it does not establish this project's data provenance or artifact scores.
- Official competition/problem/manual-review links (not freshly retrievable under
  this sandbox's outbound allowlist):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  and https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Pinned reused template (owner code, not organizer-authenticated evaluator):
  https://github.com/buffedlizard55-lab/57GEMSDOE/tree/822a0ce5546c7b6749cdd82eb145b6b3e616603d
- [Frozen nine-site audit and immutable artifact links](../docs/executive-summary.md).
- [Current GitHub-only provenance refresh](../docs/data/feed.json). Upstream heads
  were checked without changing scientific measurements. The official leaderboard
  observation remains dated 2026-10-26; it is **not** a current-page verification.

No claim is made that every line of every linked repository, paper or external
site was verified. New host access to DrivenData/USGS/NLR/GDR would be required
for direct source refreshes; an authenticated account allowance/receipt is needed
only at the separate real-slot selector step. No credentials were requested.
