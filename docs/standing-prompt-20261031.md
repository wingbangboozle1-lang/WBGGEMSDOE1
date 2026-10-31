# 31 OCT 2026 SESSION PROMPT (STANDING) — read every session, in full

> This is the verbatim working prompt for the 31 Oct 2026 session. It is intent, not
> evidence. Its official claims need manual checks; its numbers are labelled where the
> prompt itself labels them. Read it at the start of every session.

## Goal

Build a project that places top of the DrivenData DOE GEMS leaderboard
(https://www.drivendata.org/competitions/306/competition-doe-gems/).

Requirements:

1. Study the highest-scoring submissions from focus sites GEMSDOE24, 25, 27, 28, 30, 31,
   32, 33, 36 (esp. GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` = 0.2778
   USER-REPORTED, from https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html).
2. Answer at PhD level why it scored 0.2778 and whether we can beat it.
3. GENERATE A UNIQUE (never duplicate) submission TIF that is one-click downloadable,
   auto-validated in-project (no human inspection), format = single-band GeoTIFF matching
   submission CRS/shape/geotransform, values strictly in [0,1] (a prior upload failed with
   "Predicted values must be in range [0, 1]"), with unique name + ≤140-char note.
4. Executive summary must contain a table: file to download | estimated score (labelled
   HOLDOUT-DTI / ORGANIZER-CONFIRMED / OWNER-REPORTED) | unique yes/no vs the listed
   GEMDOE sites, plus an obvious SUBMIT-OK verdict and a how-to-submit subpage.
5. PARALLEL-RUN PROTOCOL: declared lane; rank-corr ≤0.90 and <70% dots within 3 px of any
   registry raster (known-degenerate gate — also report density-matched overlap lift);
   reuse shared cached feature stack / evaluate_holdout.py / submission_writer.py (no
   private forks); leakage canary (per-feature AUC ≤0.90); one JSON run card per experiment
   (hypothesis, mechanism, named non-fault mimic, HOLDOUT-DTI + 95% CI, registry
   corr/overlap, raster sha256, validator output, name+note, verdict promote/negative);
   budget 3 experiments or 2 h; negatives are deliverables.
6. Generate 3–5 novel ranked geological hypotheses before implementing (named layers,
   physical signature, why it catches an uncatalogued fault, how it differs from repo
   work); deep research into geothermal-vent science from free official sources; verify
   line-by-line, no hallucinations, flag irregularities; store prompt in README and re-read
   every session; core values Maximize P(Win) / Own the Outcome.
7. Context targets: user states leaderboard high 0.4413, "highest right now" 0.3195,
   repo-retained public #1 observation 0.4544 (all unverified owner/page reports).
8. End of task: PR created and merged to main + remaining-work/limitations suggestions.

## Standing constraints (accumulated)

- MUST generate a unique TIF submission; never copy a previous submission except for
  learning/education. It must be obvious whether it is OK to download and submit.
- No manual input: validation must run through the project without human intervention;
  anything needing a human (DrivenData login) is a blocker to report, never worked around.
- Every number labelled HOLDOUT-DTI (evaluator version, n withheld positives, 95% CI) or
  ORGANIZER-CONFIRMED; a projection is never written as a score. (WBG-8 labels: HOLDOUT-DTI,
  PROXY-DTI, MODEL-ESTIMATE, OWNER-REPORTED.)
- Keep the Executive Summary and a very obvious download button/verdict at the top of the
  site; add an executive-summary subpage explaining exactly how to submit (file type, unique
  name, short note).
- Stay in the declared method lane; log duplicate drift (>0.90 rank corr or >70% 3px dot
  overlap vs one registry raster) and stop. Do not spend a weekly submission slot on a
  candidate that hasn't beaten the holdout best. Do not pick submissions in the run-card
  step — promotion is a separate selector step within the weekly cap.
- Fix shared-template defects once in the template and report them; never keep private forks.
- Work line by line from official verified sources with links for manual review; flag
  irregularities; no hallucinations; multi-pass verification (implement → review/fix →
  re-check/improve).
- Read the prompt/README/AGENTS.md/owner brief at the start of every session; put the
  prompt in the repo README.
- Provide limitations and what access/data is needed; external data only from free official
  sources.
- Create a PR and merge onto main at the end; list next steps and blockers.

## Core values

Maximize P(Win) · Own the Outcome · Report bad news early · Plan, execute, record ·
Quality compounding · Common sense · Deliberate choices · Alignment/truth · No regressions.
