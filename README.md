# WBGGEMSDOE1 — blind geothermal fault discovery for DOE GEMS (DrivenData #306)

**Site (GitHub Pages):** `docs/` → enable Pages on `main`, `/docs`.
**Status:** <!--STATUS-->experiments running<!--/STATUS-->

## The one-paragraph brief

Nine sibling sites (GEMSDOE24/25/27/28/30/31/32/33/36) report 0.2449–0.2778,
but byte-level forensics proves they are **one lineage** (H19-5 dotted +
break-even pruning; G30 ≡ G25 bit-identical; H33 ⊂ D2.8; PINN = H33+1200).
This repo works a **new lane** — geothermal-discharge-anchored blind-fault
inference — ranks it on an **off-catalogue holdout** (SGMC faults >300 m from
labels, the honest mimic of the hidden test), and lets **automated gates**
decide: format (incl. the `[0,1]` portal rule) · uniqueness (corr < 0.90,
3-px overlap < 70% vs all nine) · holdout bar. Any failure → 🛑 DO NOT SUBMIT.

## Quickstart

```bash
bash scripts/download_competition_data.sh   # fetch + hash-verify data/ (github mirrors)
PYTHONPATH=src python3 scripts/build_h1_surface.py    # E1: surfaces + canary
PYTHONPATH=src python3 scripts/sweep_emission.py      # E2: operating sweep + baselines
PYTHONPATH=src python3 scripts/build_final_submission.py  # E3: unique TIF + run card
PYTHONPATH=src python3 scripts/build_site.py          # regenerate docs/
bash scripts/run_checks.sh                  # unit tests + artifact revalidation
```

## Repo map

| Path | What |
|---|---|
| `src/wbg1/` | metric, holdout, features, emission, submission, validate, paths |
| `scripts/` | download, prepare, evaluate_holdout, E1/E1b/E2/E3, analyze_focus9, build_site, run_checks |
| `registry/` | focus9.json (uniqueness trip-wires), hypotheses, sources, irregularities, selector, data_manifest |
| `evidence/` | E1/E1b/E2/E3 JSON, focus9_lineage.json (byte forensics) |
| `knowledge/` | metric_algebra, why_02778_won, hypotheses (H1–H5), data_inventory |
| `docs/` | GitHub Pages: index, executive-summary, how-to-submit, hypotheses, research, sources, downloads/ |
| `tests/` | metric + validator unit tests |
| `data/`, `work/` | gitignored: verified mirrors, feature stack, registry rasters |

## Lane

> Blind geothermal-discharge-anchored fault inference: hidden faults predicted
> only from label-free multi-scale lineament transforms of the 19-band GeoDAWN
> stack + 1 m LiDAR scarp + radiometric externals, ranked by coincidence with
> independent geothermal discharge (INGENIOUS wellspring temperatures, volcanic
> vents, paleo-geothermal sites), soft-gated by Andersonian strike. No
> catalogue-derived feature, no prior-submission raster, no H19-5 input.
> Emission: priority Poisson-disk, B=2 flank exclusion, budget on holdout.

## Standing operating prompt

Read this every session. (Full session prompt, kept verbatim as the project base.)

<details><summary>Click to expand the full standing prompt</summary>

Review the repo. Focus on the highest scoring submissions from GEMSDOE24,
GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33,
GEMSDOE36. Executive summary on every site, clear which is best to submit for a
high leaderboard score; unique, never an exact duplicate of a previous
submission. Iterate and test until we have the highest scoring submission to
download and submit. Estimate the score. The executive summary carries a table:
file to download, estimated score, uniqueness vs the other GEMSDOE sites.

HIGHEST URGENCY: MUST GENERATE A UNIQUE TIF SUBMISSION. Do not copy a previous
submission except for learning. It must be obvious whether it is OK to download
and submit the generated TIF. Easy-download submission TIF. Inspection is done
through the project and validated for submission without human intervention.

PARALLEL-RUN PROTOCOL: (1) LANE — stay inside the single method paragraph;
rank-corr > 0.90 or > 70% dots within 3 px of a registry raster = drifted into
another lane: log as duplicate and stop (check surface before placement AND
final dots). (2) REUSE, DON'T REBUILD — cached feature stack,
evaluate_holdout.py, submission_writer.py; holdout = hide-and-recover with
whole-segment withholding + buffer, visible-only features, visible faults masked
pixel-exactly, pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel); fix
shared tools once in the template, never a private fork. (3) LABEL EVERY NUMBER
HOLDOUT-DTI (evaluator, withheld N, 95% CI) or ORGANIZER-CONFIRMED (receipt);
a projection is never a score. (4) LEAKAGE CANARY — feature-alone AUC > 0.90 =
leakage until proven otherwise. (5) RUN CARD — hypothesis; mechanism; named
non-fault mimic; holdout DTI + CI; correlation/overlap vs registry; raster
sha256; validator output; submission name + ≤140-char note; verdict
promote/negative (negatives are deliverables). (6) BUDGET — stop after 3
experiments or 2 hours; promotion to a real slot is a separate selector step
within the weekly cap.

Study the highest focus-site score (GEMSDOE32 h33-h33-2-b2, 0.2778): why/how did
it win, can we beat it — PhD-level judgement, no hallucinations, verified line
by line from official sources with links. Generate 3–5 untried geological
hypotheses (layers, physical signature, why off-catalogue, how it differs),
ranked by expected DTI gain vs cost; validate the top candidate on the
spatially-blocked holdout before spending a slot; name any needed free official
external data and confirm obtainability. Core values: Maximize P(Win); Own the
Outcome. Submission must pass validation gates (values in [0,1] — the portal
rejected a previous upload with "Predicted values must be in range [0, 1]"),
carry a unique name + short comment, and ship with an executive-summary subpage
explaining exactly how to submit. Three review passes before finishing. Open a
PR, merge to main, and list remaining work + limitations.

</details>

## Key links

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Data: https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Competition PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS: https://gbcge.org/current-projects/ingenious/
- GDR 1391: https://gdr.openei.org/submissions/1391

## Limitations (owned, not hidden)

1. drivendata.org unreachable from this sandbox → leaderboard + all submission
   scores are OWNER-REPORTED, never organizer-confirmed here.
2. No organizer receipt ties any score to exact bytes (fleet-wide).
3. Data arrives via hash-pinned GitHub mirrors (integrity ✓, organizer-auth ✗).
4. Hidden test is unobservable; SGMC off-catalogue is a proxy with transfer risk
   (documented in `knowledge/`).
