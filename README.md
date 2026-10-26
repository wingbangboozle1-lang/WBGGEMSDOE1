# WBGGEMSDOE1 — evidence-gated DOE GEMS submission research

> **Read this first every session.** Maximize P(Win) by protecting scarce submission slots. Own the outcome end-to-end. Never call a projection a score, never copy a prior submission as a new method, and never turn format validity into scientific authorization.

## Current decision

# **DOWNLOAD FOR AUDIT: YES · SUBMIT: NO · `negative`**

The fixed three-arm TIP1 experiment is complete. Its uniquely named, competition-format GeoTIFF is:

[**Download `gemsdoe1-tip1-directional-tip-gradient-20261026-9a4b9b4bc8cd-zeros.tif`**](docs/downloads/gemsdoe1-tip1-directional-tip-gradient-20261026-9a4b9b4bc8cd-zeros.tif) — **research/audit only; DO NOT SUBMIT**

SHA-256 `148718d31ea75cfa3b7c643dfa25643cb0353483b2fa0e2696a62af2a107dca8`; 37,722 dots; strict whole-array finite `[0,1]` PASS. Primary Arm B achieved **HOLDOUT-DTI 0.082434**, evaluator `gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.072872, 0.091733]`. It misses the pinned local promotion benchmark `0.166060`; paired replay is unavailable; and final dots overlap the retained spacing-5 lattice by `99.9523% > 70%`. No relocation, arm switching, upload or slot use occurred.

[GitHub Pages dashboard](docs/index.html) · [submission instructions](docs/submission-instructions.html) · [full run card](evidence/tip1_run_card_20261026.json) · [TIP1 findings](research/01_tip1_findings.md) · [nine-site table and H33 analysis](research/02_h33_and_nine_site.md)

### Preserved parallel archive from current `main`

The merge with current `main` retains the separately completed **MVGZ** negative artifact and its evidence at [`evidence/run_card.json`](evidence/run_card.json). MVGZ remains **DO NOT SUBMIT**. It used evaluator `WBGGEMSDOE1-HIDE-RECOVER-v1.0` with 60,161 withheld positives, so its HOLDOUT-DTI cannot be treated as protocol-comparable to TIP1's `gems-segment-pooled-v1` result. TIP1 is the sole lane executed by this branch; inherited evidence was preserved rather than deleted.

## Mission

Review the highest-scoring owner-reported artifacts from **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33 and GEMSDOE36**; explain the GEMSDOE32 H33-B2 result without hidden-label speculation; test one genuinely distinct geological hypothesis; produce an automatically validated, uniquely named GeoTIFF; and state unambiguously whether it is safe to spend a leaderboard slot.

The competition target is DrivenData DOE GEMS. The output grid is a single-band float32 GeoTIFF in EPSG:32611 with shape `3730 × 3292` and exact organizer-template transform. A `-zeros.tif` must be finite and in `[0,1]` across the entire stored array to avoid the reported portal error `Predicted values must be in range [0, 1]`.

## Operative owner request (preserved)

> **Highest urgency:** MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT IS FOR LEARNING AND EDUCATION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.
>
> Before implementing, generate 3–5 candidate geological hypotheses not yet tried. For each name the exact layers, physical transform/signature, reason it could find a fault missing from the USGS/INGENIOUS catalogue, and difference from prior implementations. Rank expected DTI benefit and cost. Validate the top candidate on a spatially blocked holdout before touching a weekly slot. If new external data are needed, identify the free official source and verify obtainability.
>
> Use the cached feature stack and shared `evaluate_holdout.py` / `submission_writer.py`. Hide whole fault segments with a buffer; derive every catalogue feature from visible faults only; mask visible faults pixel-exactly; pool DTI at α=0.2, β=0.8 with a 300 m triangular kernel. Test every feature alone; AUC above 0.90 is leakage until proved otherwise.
>
> Stop a lane when surface rank-correlation exceeds 0.90 or more than 70% of final dots fall within 3 pixels of one registry raster. End with one JSON card containing hypothesis, mechanism, named non-fault mimic, HOLDOUT-DTI plus evaluator/withheld count/95% CI, registry correlation/overlap, raster SHA-256, validator output, submission name and a note of at most 140 characters, and `promote` or `negative`. Negative results are deliverables. Stop after three experiments or two hours. Slot selection is separate.
>
> Build a clean GitHub Pages site with an executive summary at the top, an obvious download, an exact filename and short note, a nine-site table, official manual-review links, limitations, and automated—not human—validation. Preserve the project goal in the README. Run three implementation/review passes, then open and merge a pull request.

The full normalized requirements record is in [`research/owner_request.md`](research/owner_request.md). The original message's long historical score catalogue is user-supplied context, not independent evidence; machine-readable focus-site claims and immutable source pins belong in `evidence/`.

## Parallel-run protocol

1. **One lane per autonomous branch.** The owner message contains no actual assigned method paragraph. This branch explicitly records that irregularity and self-preregisters TIP1 only because the same request directs autonomous ranking and validation. Separately merged MVGZ evidence is an inherited frozen archive, not a fourth TIP1 experiment.
2. **No private metric/writer fork.** Shared evaluator/writer/emission modules are pinned to audited upstream commit `7790c3b`; exact template CLIs are retained as `scripts/template_*`, while repository-level wrappers preserve both frozen TIP1 verification and inherited MVGZ compatibility. One shared novelty performance fix is explicitly hashed, tested and recorded in `evidence/shared_source_lock.json`.
3. **Labels on numbers.** Performance is either `HOLDOUT-DTI` with evaluator, withheld positives and 95% CI, or `ORGANIZER-CONFIRMED` with an artifact-linked receipt. Owner-reported leaderboard values remain `OWNER-REPORTED / UNVERIFIED`. A model projection is never labeled a score.
4. **Leakage canary first.** Every source and transform used by the candidate is checked alone in both polarities.
5. **Automated fail-closed selector.** Format, scientific efficacy, novelty, nuisance and governance gates are separate.
6. **Budget.** Maximum three fixed arms / two hours, zero automated portal uploads.

## Locked scientific plan

Read [`research/00_ranked_hypotheses.md`](research/00_ranked_hypotheses.md). The selected lane is **TIP1**, a catalogue-independent, orientation-following LiDAR coherence-gradient detector for short fault-tip damage zones. It is distinct from H33D's old-raster tip grafts and from OJ1's neighbourhood orientation dispersion. Arm B is fixed before execution; controls cannot be substituted after seeing results.

## Why H33-B2 may have scored 0.2778

Artifact forensics in the reviewed projects show that H33-B2 is a **subset** of the older D2.8/H19-5 family: it removes 6,436 dots near the public catalogue and adds no new dots. The defensible observation is geometric pruning. The causal story—those removed dots had low hidden-truth credit and mostly false-positive cost—is plausible under pixel-exact known-fault masking and asymmetric DTI, but cannot be proved without hidden labels and an organizer receipt. Therefore `0.2778` remains **OWNER-REPORTED / UNVERIFIED**, not `ORGANIZER-CONFIRMED`, and the artifact is prohibited as a template to copy.

## Evidence policy and limitations

- DrivenData, ScienceBase, OpenEI, NLR and other non-allowlisted hosts cannot be accessed automatically in this sandbox. Manual-review URLs are retained; GitHub-hosted official reference code and owner mirrors can be hash-pinned.
- No DrivenData account/session or submission-page receipt is available. The agent cannot verify remaining weekly quota or upload automatically.
- A local validator proves bytes/grid/range, not organizer acceptance or leaderboard performance.
- HOLDOUT-DTI measures recovery of withheld **mapped** fault segments. It is a proxy for discovering missing faults, not proof of a geothermal vent or productive reservoir.
- The user supplied conflicting leaderboard-high values (`0.3195`, `0.4413`; newer reviewed text also mentions `0.4437`). None is a team receipt, so the site does not present one as current fact.

## Reproduction and automated verification

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
.venv/bin/python scripts/restore_inputs.py
.venv/bin/python scripts/restore_registry.py
PYTHONPATH=src .venv/bin/python scripts/run_tip1_lane.py --verify-recorded
PYTHONPATH=src .venv/bin/python scripts/validate_release.py
.venv/bin/pytest -q
```

The scientific runner refuses a rerun after writing its frozen receipt; `--verify-recorded` reopens the exact TIFF, recomputes its validator, checks SHA identities and re-pools every fold receipt. No GPU or manual inspection is required.

## Manual-review sources

- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [DOE/NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [OpenEI GDR 1391](https://gdr.openei.org/submissions/1391)
- [INGENIOUS](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)

## Core values

### Maximize P(Win)

Weigh scientific upside, leakage risk, uniqueness, implementation cost and slot scarcity. Prefer an honest negative to an unsupported upload.

### Own the Outcome

Act on defects, preserve exact evidence, expose irregularities, automate checks, and distinguish what was measured from what is merely claimed.
