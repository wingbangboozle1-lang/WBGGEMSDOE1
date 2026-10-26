# AGENTS.md — how to work in this repo

Read `README.md` (standing prompt) first, every session.

## Lane (stay inside it)

Blind geothermal-discharge-anchored fault inference: label-free lineament
transforms ranked by INGENIOUS discharge coincidence + Andersonian strike gate.
No catalogue-derived features, no prior-submission rasters, no H19-5 lineage
input. Duplicate trip-wires: rank-corr > 0.90 or > 70% of dots within 3 px of
any `registry/focus9.json` raster (checked on surface AND final dots) → log as
duplicate and stop.

## Protocol (parallel-run)

1. Reuse this repo's `src/wbg1` (metric/holdout/submission/validate). Fix shared
   tools in place; never keep a private fork.
2. Label EVERY number HOLDOUT-DTI (evaluator id, withheld N, 95% CI) or
   ORGANIZER-CONFIRMED (submission-page receipt) — owner-reported scores are
   neither; call them OWNER-REPORTED. A projection is never written as a score.
3. Leakage canary on each feature alone before trusting results (AUC > 0.90 =
   leakage until proven otherwise).
4. End runs with the JSON run card (see `scripts/build_final_submission.py`).
5. Budget: 3 experiments per campaign. No slot spent unless the idea beats the
   current holdout best. Promotion to a real slot is a separate selector step.

## Instruments

- PRIMARY `WBG1-SGMC-CAL-v1.0`: off-catalogue SGMC truth (>300 m from labels),
  visible/catalogue masked pixel-exactly, pooled DTI (a=0.2, b=0.8, R=300 m),
  256-block bootstrap CI.
- DIAGNOSTIC `WBG1-HIDE-RECOVER-v1.0`: 5-strip hide-and-recover vs catalogue
  (flooded for B-excluded emissions — see `knowledge/metric_algebra.md` §7).

## Commands

- `bash scripts/download_competition_data.sh` — fetch + verify data (github mirrors)
- `python3 scripts/prepare_data.py` — hash/grid verification
- `PYTHONPATH=src python3 scripts/evaluate_holdout.py --input X.tif` — score any raster
- `PYTHONPATH=src python3 scripts/build_h1_surface.py` — E1
- `PYTHONPATH=src python3 scripts/sweep_emission.py` — E2
- `PYTHONPATH=src python3 scripts/build_final_submission.py` — E3
- `bash scripts/run_checks.sh` — unit tests + artifact revalidation
- `PYTHONPATH=src python3 scripts/build_site.py` — regenerate `docs/`

## Conventions

- Evidence over narrative: every claim links a file + hash + command.
- Fail closed: missing data, failed gates, unverified scores → DO NOT SUBMIT.
- Keep `docs/` regenerable from `evidence/` + `registry/` (no hand edits).
- Never commit `data/` or `work/` (gitignored); commit `docs/downloads/*.tif`
  only for the single headlined artifact + its audit JSON.
