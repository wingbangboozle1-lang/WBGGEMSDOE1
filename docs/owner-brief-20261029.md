# Owner brief — GEMS / WBGGEMSDOE1 (received 29 October 2026)

**Status of this document:** a condensed transcription of the owner's standing requirements from the
29 October 2026 session message, with every official link kept. Earlier standing briefs remain in
[`PROMPT.md`](../PROMPT.md) and [`AGENTS.md`](../AGENTS.md). Read this file, the
[README](../README.md) and [`docs/executive-summary-20261029.html`](executive-summary-20261029.html) (main's decision page) and [`docs/unique-lane-summary-20261029.html`](unique-lane-summary-20261029.html) (unique-lane results)
before any project work.

## 1. Goal

Place **first** on the DrivenData DOE GEMS Prize leaderboard
([competition](https://www.drivendata.org/competitions/306/competition-doe-gems/),
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)).
The project must generate a **unique, format-valid GeoTIFF** that the owner can download with one click
and submit, and it must state clearly whether that file is OK to download and submit.

## 2. Non-negotiable requirements

1. **Unique TIFF.** The submission must not be a copy of any earlier submission (byte-identical or
   pixel-identical). Copying a previous submission is allowed only for learning and education.
2. **Obvious download/submit status.** Every downloadable file carries one visible verdict:
   `DOWNLOAD` and `SUBMIT`. A file may be marked `SUBMIT: OK` only when it passes every gate in §4.
3. **Format.** Single-band float32 GeoTIFF, EPSG:32611, 100 m, the training grid's bounds, values in
   [0, 1], nothing outside the bounds except null/NaN. Official source:
   [problem description, submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/);
   [official rules PDF §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
4. **Validation without human intervention.** The gates run in the project, not by a human inspector.
5. **Name and note.** Each submission has a unique name and a short note (≤140 characters) that tells
   submissions apart later.
6. **Executive summary.** A table that lists, for each site, the file to download, its estimated score
   (with its label), and whether it is unique.
7. **Estimates are labelled.** Every number is one of: `HOLDOUT-DTI` (evaluator version, number of
   withheld positives, 95 % CI), `ORGANIZER-CONFIRMED` (copied from a submission-page receipt), or
   `OWNER-REPORTED`. A projection is never written as a score.
8. **No manual input.** Work is autonomous; anything needing a human (e.g., a DrivenData login) is listed
   as a blocker, not worked around.
9. **Line-by-line verification and sources.** Every claim is traced to an official or verified source with
   a link for manual review. Flag irregularities. No hallucinated values.
10. **Core values.** *Maximize P(Win)*: weigh tradeoffs and risk and choose the path that maximizes the
    probability of winning. *Own the Outcome*: act on problems without waiting for permission, and
    treat failure as a signal.

## 3. Method rules (parallel-run protocol, from `PROMPT.md`)

- **LANE.** Stay in the declared method. Rank correlation > 0.90 or > 70 % of dots within 3 px of one
  registry raster means a duplicate: log it and stop.
- **REUSE.** Use the shared holdout (`vendor/gems57`), the shared writer and validator. Do not fork a private
  evaluator. Shared-tool defects are fixed once in the template and reported.
- **LEAKAGE CANARY.** Test each feature alone on the holdout. AUC > 0.90 means leakage until proven otherwise.
- **RUN CARD.** One JSON card per candidate: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI,
  overlap and correlation versus the registry, SHA-256, validator output, name, note, verdict.
- **BUDGET.** Three experiments or two hours per lane. Promotion to a real upload is a separate selector step
  inside the weekly cap shown on the submission page (three per week, per the
  [official rules §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf)).

## 4. Gates a file must pass before it may be marked `SUBMIT: OK`

| Gate | Source of rule | Pass condition |
|---|---|---|
| G1 format | [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | single band, float32, EPSG:32611, 3730 × 3292, transform = training grid, values finite in [0,1] |
| G2 exact copy | owner brief §2.1 | no SHA-256 or normalised-pixel match to any registry raster |
| G3 rank correlation | PROMPT.md LANE | Spearman < 0.90 vs every registry raster (full footprint) |
| G4 literal overlap | PROMPT.md LANE | < 70 % of dots within 3 px of any registry raster's dots |
| G5 leakage canary | PROMPT.md LANE 4 | per-feature AUC ≤ 0.90 on the holdout (both withholding modes) |
| G6 holdout | owner brief §2.7 | HOLDOUT-DTI reported with CI; a winning claim needs a paired CI above the comparator |

G4 is known to be **degenerate** against dense registry rasters: a 206,895-dot lattice captures
99.68 % of any dot field ([shared uniqueness module](../vendor/gems57/uniqueness.py)). Any file that
fails G4 is reported with its failure, not silently relabelled.

## 5. Official sources (verified 29 Oct 2026)

- Competition: <https://www.drivendata.org/competitions/306/competition-doe-gems/>
- Problem description and metric (distance-weighted Tversky, α = 0.2, β = 0.8, 300 m triangular kernel):
  <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- About: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>
- Official rules (PDF, September 2026): <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- Leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- Reference solution (raster U-Net, no scoring code): <https://github.com/drivendataorg/gems-prize-reference-solution>
- GeoDAWN (USGS): <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- INGENIOUS (GBCGE): <https://gbcge.org/current-projects/ingenious/>
- CRS: <https://epsg.io/32611>
- Tversky index: <https://en.wikipedia.org/wiki/Tversky_index>
- The DrivenData data page requires login and cannot be accessed from this sandbox. Every input used here is an
  owner GitHub mirror, SHA-256-checked against `registry/data_manifest.json`, and labelled
  `OWNER-MIRROR-INTEGRITY`, not organizer-origin.

## 6. Owner-reported history (not organizer-confirmed)

The owner's brief lists nine focus sites (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36) and about 120 other
GitHub-hosted submissions with scores. Those scores are **OWNER-REPORTED**: no submission-page receipt binds
them to a file. The 118 files that are on GitHub are fetched, SHA-256-matched and used for uniqueness only
(`registry/wbg_h1/scored_registry.json`, `evidence/scored_raster_fetch.json`).
