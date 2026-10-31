# Session operating prompt (read at the start of every working session)

This file is the standing brief for WBGGEMSDOE1. The full original user message is archived in
[`docs/standing-prompt.md`](docs/standing-prompt.md). The requirements that actually bind work are here.

## Goal

Place a **unique**, portal-valid GeoTIFF on the DrivenData DOE GEMS Prize (competition 306) path —
keep iterating and testing until the highest-scoring candidate we can honestly defend is ready to
download and, at the owner's discretion, submit. Promotion to a real weekly slot is a separate
selector step within the weekly cap shown on the submission page.

Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
Problem: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
About: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
Reference: https://github.com/drivendataorg/gems-prize-reference-solution
Rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf

## Parallel-run protocol

1. **LANE.** Stay in the declared method. If rank-correlation with any registry raster exceeds 0.90,
   or more than 70% of *my* dots fall within 3 px of one registry raster's dots (the literal rule is
   evaluated over non-degenerate rasters; dense-field overlap is mechanically forced — see AGENTS.md
   defect ii), log a duplicate and stop.
2. **REUSE.** Use `scripts/evaluate_holdout.py` and `scripts/submission_writer.py` (shared
   `src/gems/*` + pinned `vendor/gems57/`). Holdout = hide-and-recover: withhold whole fault
   segments with a buffer; catalogue-based features from visible faults only; mask visible faults
   pixel-exactly; pooled DTI (α=0.2, β=0.8, 300 m triangular kernel).
3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, n withheld positives, 95% CI) or
   ORGANIZER-CONFIRMED / OWNER-REPORT / MODEL-ESTIMATE. A projection is never written as a score.
4. **LEAKAGE CANARY.** Test each feature alone on the holdout. AUC > 0.90 means leakage until
   proven otherwise.
5. **RUN CARD.** JSON: hypothesis; mechanism; named non-fault mimic; holdout DTI + CI;
   correlation/overlap vs registry; raster sha256; validator; submission name + ≤140 char note;
   verdict promote / negative.
6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick live slots.

## Binding instrument defects (AGENTS.md, receipts in evidence/)

(i) The shared hide-and-recover holdout does **not** rank real submissions (Spearman 0.144,
p=0.12, n=118) — never report it as a leaderboard forecast. (ii) The literal ">70% within 3 px"
registry gate is degenerate against any dense raster (a 206,895-dot lattice captures ~99.7% of any
dot field) — use the same-budget non-degenerate evaluation plus density-matched lift. (iii) 118
history files are only 22 families — grouped CV for any fitted claim. (iv) Reported scores differ by
up to 0.086 for near-identical rasters — the nine-site top six are statistically tied.

## Submission contract (portal)

- Single-band float32 GeoTIFF, EPSG:32611, 3730×3292, 100 m, sample geotransform.
- **Values in [0, 1] with an all-finite exterior (outside=zero).** A NaN-outside file triggered the
  portal error "Predicted values must be in range [0, 1]" (verified cause in the writer docstring,
  `src/gems/submission.py`: some portal validators inspect every stored cell). WBG-8 candidates are
  written outside=zero and re-validated by `scripts/validate_submission.py` before any hand-off.
- Unique name + note ≤140 chars. Validation is automatic; no human inspector.
- Homepage must make **OK TO DOWNLOAD / OK TO SUBMIT** obvious, with a download button at the top.

## Nine focus sites

GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36.
Highest OWNER-REPORT among them: GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` =
**0.2778** (USER-REPORTED, not organizer-confirmed). Question this repo must answer: why that file
scored 0.2778, and whether a *unique* file can beat it. Current external claims: leaderboard #1
0.4544 (public read, retained observation 2026-10-28/29); the owner also cites 0.3195/0.4413 —
label all as UNVERIFIED from this sandbox (no DrivenData auth).

## Why 0.2778 (established forensics, `knowledge/03_*`, `docs/research/wbg2-why-02778.md`)

Nested dot family: D2.8 (44,090 dots, d≥1 px) → B1 (40,199, d≥2) → B2 (37,654, d≥3), each pruning
raise coincided with a higher reported score (0.2600 → 0.2708 → 0.2778). B2 = Poisson-300 m
kernel-disjoint off-catalogue dots, zero dots on the catalogue, coverage 0.92 of 6-km blocks,
p90 distance ~68 px. GEMSDOE25=GEMSDOE30 share one dot set; GEMSDOE36 ⊃ B2; GEMSDOE31=GEMSDOE28
(h27-4). Differences within this band are within the ±0.086 reported-score noise (defect iv).

## Core values

Maximize P(Win). Own the Outcome. A negative unique result that prevents a wasted slot is a win
relative to a duplicate upload.
