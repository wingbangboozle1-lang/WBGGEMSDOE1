#!/usr/bin/env python3
"""Keep the README decision current and embed the complete supplied standing brief."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    card = json.loads((ROOT / "registry/run_card.json").read_text())
    wbg_h1_rc = json.loads((ROOT / "evidence/wbg_h1/run_card.json").read_text())
    current = json.loads((ROOT / "docs/data/current_decision_20261027.json").read_text())
    feed = json.loads((ROOT / "docs/data/feed.json").read_text())
    h, c, d = card["holdout"], card["control_holdout"], card["paired_delta_holdout"]
    tif = Path(card["artifact"]).name
    h1_tif = wbg_h1_rc["raster_sha256"]["tif_file"]
    h1_zip = wbg_h1_rc["raster_sha256"]["zip_file"]
    standing = (ROOT / "docs/standing-prompt.md").read_text()
    new_rows = "\n".join(
        f"| [{r['file']}](docs/{r['url']}) — {r['label']} | HOLDOUT-DTI {r['holdout_dti']:.6f}, 95% CI "
        f"[{r['holdout_ci95'][0]:.6f}, {r['holdout_ci95'][1]:.6f}] | **{r['estimate_value']:.4f}** "
        f"(LLI projection ±0.0353; **not a score**) | competing-method unique: "
        f"{'yes' if r['competing_method_gate_passed'] else 'no'}; literal lattice gate: "
        f"{'pass' if r['literal_gate_passed'] else 'FAIL'} | **NO** |"
        for r in current["new_files"]
    )
    site_rows = "\n".join(
        f"| {s['site']} | [{s['latest_candidate_file']}]({s['latest_candidate_url']}) | "
        f"USER-REPORTED {s['historical_value']:.4f} (historical champion) / "
        f"**{s['estimate_value']:.4f}** LLI projection ±{s['estimate_loo_mae']:.4f} (latest candidate) | "
        f"{'yes' if s['unique_vs_sparse_peers'] else 'no'} vs sparse peers; "
        f"max 3 px overlap {s['max_sparse_peer_3px_overlap']*100:.1f}% | **NO** |"
        for s in current["sites"]
    )
    session_section = f'''## 2026-10-27 session — new unique TIFF, fail-closed decision

**[Open the submission decision page](docs/submission-decision.html)** ·
**[Download the best newly generated unique TIFF](docs/{current['decision']['best_download_url']})** ·
[One-TIFF ZIP](docs/downloads/{current['decision']['best_download'].replace('.tif', '.zip')}) ·
[Decision JSON](docs/data/current_decision_20261027.json) ·
[Ranked hypotheses](research/03_ranked_hypotheses_2026-10-27.md) ·
[Next work and limitations](research/04_next_steps_20261027.md)

> **DOWNLOAD: YES, for research/audit. SUBMIT: NO.** Two new, single-band, all-finite `[0,1]`
> GeoTIFFs were generated from a preregistered three-arm lane. No file beat the frozen
> **HOLDOUT-DTI 0.166060** current-best point estimate, no file passed the literal all-entry
> 3 px registry gate, and **zero weekly slots were used**. A projection is not a leaderboard score.

| File to download | Measured evidence | Estimate (explicitly not a score) | Unique? | OK to submit? |
|---|---|---|---|---|
{new_rows}

The inherited WBG-H1 EXP-3 TIFF remains the strongest unique research file in this repository
(HOLDOUT-DTI 0.123310; LLI projection 0.1898), but it is also **negative** and not a newly
generated 2026-10-27 file. The new TASC primary arm failed for a structural reason: the
hide-and-recover holdout removes all visible catalogue faults from each test quadrant, so a
visible-tip-derived corridor has almost no support there. That negative result is retained.

### Nine focus sites — best file, estimate and uniqueness

Historical values are **USER-REPORTED / NOT ORGANIZER-CONFIRMED**. LLI numbers are empirical
projections on 118 user-reported historical rasters (LOO MAE 0.0353), **not organizer scores**.

| Site | File to download (latest unique candidate; audit only) | Estimate | Unique vs other GEMSDOE sites? | OK to submit? |
|---|---|---|---|---|
{site_rows}

The highest supplied historical value remains **GEMSDOE32 B2, USER-REPORTED 0.2778**, already
submitted and not a new unique entry. The official public leaderboard was observed at
**{feed['leaderboard']['public_dw_tversky']:.4f}** on 2026-10-27; the prompt's 0.4413 and 0.3195
targets are stale/inconsistent. No project file has an organizer receipt linking it to a score.

'''
    header = f'''# WBG GEMS — evidence-first fault mapping

## DOWNLOAD: YES, for research. SUBMIT: **NO**.

**[Open the research desk](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/)** ·
[Executive summary](docs/executive-summary.md) · [Submission guide](docs/how-to-submit.html) ·
[Exact JSON run card](registry/run_card.json)

**[Download the newly generated research TIFF](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/downloads/{tif})** ·
[One-TIFF ZIP](docs/downloads/{tif.replace('.tif', '.zip')}) ·
[TIFF in repository](docs/downloads/{tif}) · [Validation receipt](docs/downloads/{tif.replace('.tif', '.json')})

> **NEGATIVE RESULT.** This is a genuinely generated, format-valid **continuous research surface**,
> not a final dotted or promoted competition submission. It fails paired efficacy and the literal
> registry-overlap gate. The method lane was not assigned in the prompt. **Do not upload it.**
> No final dots were placed, no real submission was selected, and **zero competition slots were used**.
> “Different bytes” is not “lane unique”; “local format pass” is not organizer acceptance.

{session_section}

| Artifact / decision | Measured evidence | Estimated leaderboard result | Exact-copy / literal uniqueness |
|---|---|---|---|
| [{tif}](docs/downloads/{tif}) — **research download only** | **HOLDOUT-DTI {h['dti']:.6f}**, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}], `{card['holdout_instrument']['evaluator_version']}`, {h['withheld_positive_pixels']:,} withheld positives | **Unavailable**. Not inferred from holdout. Organizer-confirmed artifact result: **none**. | Byte- and normalized-pixel distinct from all {card['registry']['checked_unique_file_hashes']} checked hashes; **FAIL** literal forward overlap {card['registry']['max_forward_3px_overlap']*100:.2f}% >70%. |

- Same-instrument 19-band control: **HOLDOUT-DTI {c['dti']:.6f}**, 95% CI [{c['ci95'][0]:.6f}, {c['ci95'][1]:.6f}], same evaluator, {h['withheld_positive_pixels']:,} positives.
- Paired difference: **HOLDOUT-DTI {d['delta']:+.6f}**, 95% CI [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}], same evaluator/positives. No improvement established.
- Scientific representation: **unplaced continuous OOF confidence**, not matched-budget sparse dots, calibrated probabilities or a hidden-test leaderboard forecast.
- Leakage canaries: all 23 individual inputs tested in four folds; max orientation/missingness AUC **{card['leakage_canary']['maximum_orientation_invariant_auc']:.6f}**, below 0.90. AUC is not DTI and passing this screen is not proof of no possible leakage.
- Local GeoTIFF: one float32 band, EPSG:32611, 3,730 × 3,292, 100 m, exact reference transform; all finite, min **{card['validator']['range_min']:.6f}**, max **{card['validator']['range_max']:.6f}**, zero outside the footprint and on the known catalogue.
- SHA-256: `{card['raster_sha256']}`.
- Name: `{card['submission_name']}`.
- Note (≤140 characters): `{card['submission_note']}`.

## Review outcome and historical learning

The starting checkout at `5d2236b` contained only `README.md` with a one-line title: no existing
training pipeline, data cache, previous-session tasks or site were present locally. This work built
an auditable project, restored the public mirrors and shared cache, and ran one preregistered screen.

The [nine-site executive summary](docs/executive-summary.md) covers **GEMSDOE24, 25, 27, 28, 30, 31,
32, 33 and 36**, linking exact original files and immutable source snapshots. Historical values
provided in the prompt are quarantined as **USER-REPORTED / NOT ORGANIZER-CONFIRMED** because no
submission-page receipt binds those bytes to a result. They are not relabelled HOLDOUT-DTI.

The largest supplied historical claim is **GEMSDOE32 B2, USER-REPORTED 0.2778**. The exact raster
identity is D2.8 44,090 dots → B1 40,199 → B2 37,654 by progressively removing catalogue-near dots.
GEMSDOE25 and GEMSDOE30 have identical decoded predictions. GEMSDOE36 is B2 plus 1,200 additions.
These are closely related fields, not nine independent geological discoveries. Sparse max-cover
credit and avoiding low-marginal-credit predictions are plausible reasons for the historical
ordering, not a causal proof from unavailable hidden labels. A 200 m exclusion is **not** an
organizer rule. No historical file should be copied into a new "unique" entry.

The direct **official public-leaderboard observation on 2026-10-27 was {feed['leaderboard']['public_dw_tversky']:.4f}**,
not the prompt's older 0.4413 / 0.3195 targets. That is **not** an organizer result for any project
TIFF. A higher project score was not obtained or credibly projected in this session.

## Parallel work preserved during integration

While this branch was working from the one-line initial checkout, other sessions merged TIP1 and
MVGZ negative results into `main` (integrated snapshot `b9a2d5301c0c971dcc1219f9ad6b29c68f68ee21`).
Their frozen scientific modules, receipts and artifacts are retained; they were **not rerun**.
The current **one-experiment count is WBG-C1 only**, not a sum or reset of the inherited lane budgets.
Different evaluator/split/representation results must not be pooled or ranked as comparable scores.

- [Original parallel site, with its own frozen assets and data](docs/parallel/main-b9a2d53/index.html)
- [Original main README](research/inherited-main-README-b9a2d53.md) (historical commands/paths)
- [Byte-preservation/integration receipt](evidence/parallel_main_integration.json)
- [Frozen TIP1 card](evidence/tip1_run_card_20261026.json) and [MVGZ card](evidence/run_card.json)
- **[Parallel WBG-H1 (DPGF-1 / EXP-3) Interactive Dashboard & 9-Site Audit](docs/wbg-h1-dpgf1/index.html)** ·
  [Step-by-step DrivenData upload guide](docs/wbg-h1-dpgf1/executive-summary.html) ·
  [1-Click Validated `[0,1]` GeoTIFF (`{Path(h1_tif).name}`)]({h1_tif}) (`SHA-256: {wbg_h1_rc['raster_sha256']['tif_sha256']}`) ·
  [ZIP archive]({h1_zip}) ·
  [WBG-H1 Run Card (`evidence/wbg_h1/run_card.json`)](evidence/wbg_h1/run_card.json)
  - **Method (`WBG-H1 / DPGF-1`, pre-registered in [`knowledge/01_preregistration_wbg_hypotheses_2026-10-26.md`](knowledge/01_preregistration_wbg_hypotheses_2026-10-26.md)):** 66-channel label-free feature stack (`DipShift` 500 m / 1,000 m updip subsurface-to-surface projection, `TFSDI` tectonic-vs-fluvial scarp index, E–W notched GeoDAWN magnetics, MT/GDR 1391 perimeter, 3DEP LiDAR completeness dual `HGB+ET` ensemble + two-regime `300 m` CELF submodular emitter, `37,654` zero-exterior binary dots).
  - **Canary & Holdout (`gems-segment-pooled-v1`, `n=60,988` withheld positives):** `66/66` single-feature canaries PASS (`max_symmetric_auc = 0.68971 <= 0.90`). `EXP-3` achieves **`HOLDOUT-DTI = {wbg_h1_rc['holdout_dti']['dti']:.6f}`** (`95% CI [{wbg_h1_rc['holdout_dti']['ci95'][0]:.6f}, {wbg_h1_rc['holdout_dti']['ci95'][1]:.6f}]`), beating matched 31-ch tree baseline `B0 = {wbg_h1_rc['holdout_dti']['baseline_b0_dti']:.6f}` across **4/4 spatial folds** (`paired Δ = +{wbg_h1_rc['holdout_dti']['paired_delta_vs_b0']:.6f}`, `95% CI [+{wbg_h1_rc['holdout_dti']['paired_delta_vs_b0_ci95'][0]:.6f}, +{wbg_h1_rc['holdout_dti']['paired_delta_vs_b0_ci95'][1]:.6f}]`, surging `+34.9%` to `0.17974` in `NE_LidarGapHeavy`).
  - **Automated `[0,1]` Portal & Uniqueness Gates:** `10/10` portal checks PASS (`0` NaN, `0` Inf across all `12,279,160` cells, `outside="zero"`, `nodata=None`); pre-placement surface `|ρ| = 0.2404 <= 0.90`; sparse/Focus-9 3 px dot overlap `64.49% <= 70%`, `|ρ| = 0.0347 <= 0.90`; symmetric 3 px overlap across all 206 non-lattice rasters `56.05% <= 70%`. Submission name `{wbg_h1_rc['submission_name']}`, note `{wbg_h1_rc['submission_note']}` (`{wbg_h1_rc['submission_note_length']}` chars).
  - **Selector Verdict (`verdict: "{wbg_h1_rc['verdict']}"`):** Hold live 3/week DrivenData slot standalone because `0.123310` trails analytical scarp-ridge reference `GEMSDOE24 DPRF1` (`HOLDOUT-DTI = 0.163792`); see [`evidence/wbg_h1/focus9_executive_audit.json`](evidence/wbg_h1/focus9_executive_audit.json) (catching `GEMSDOE30`'s `7,111,787` exterior `NaN` `[0,1]` portal failure and `GEMSDOE28/31` `>90%` peer duplicates) and [`evidence/wbg_h1/forensic_proof_02778.json`](evidence/wbg_h1/forensic_proof_02778.json) (`0`-XOR proof + `r13-lattice-s5 = 0.0904 -> |G_private| = 12,366` px inversion).
- Older two-argument `validate_submission.py candidate.tif reference.tif` callers retain their
  supplied-reference format API; this is compatibility only and never confers slot approval.
  WBG-C1 still uses the unchanged, pinned `gems57` all-finite validator/writer.
- The older bridge-specific restore entry point is retained as `scripts/download_bridge_legacy.sh`
  with `scripts/prepare_bridge_legacy.py`; current WBG-C1 commands below are unchanged.

## What is implemented

- [Four ranked pre-implementation hypotheses](docs/hypotheses.md), with layers, transforms,
  missing-catalogue rationale, mimics, novelty limits and data readiness. Only WBG-C1 was tested.
- A catalogue-blind conductivity/depth Hessian-commutator transform and scale/strain support.
- **Unchanged shared template** at `buffedlizard55-lab/57GEMSDOE@822a0ce5546c7b6749cdd82eb145b6b3e616603d`:
  cache builder, buffered whole-component holdout, `evaluate_holdout.py`, metric, registry gates
  and fail-closed `submission_writer.py`. [All 24 source hashes](evidence/template_integrity.json).
- All **19 original cache hashes** reproduced. Inputs are **owner mirrors**, not independently
  authenticated organizer downloads. Large inputs/cache/research clones are ignored by Git.
- Frozen spatial LOQO screen: whole components withheld globally, feature buffer, 8 km training
  collar, visible faults masked pixel-exactly, pooled alpha=0.2/beta=0.8/300 m DTI, paired 20 km
  physical-cluster bootstrap. [Full output](evidence/experiment.json).
- Single-feature leakage canaries, exact-file format/ZIP validation, **360-hash / 377-source-path**
  nine-snapshot registry audit with no lattice/density exemption, fail-closed promotion decision.
- Clean static GitHub Pages desk, executive-summary and submission-guide subpages, direct TIFF/ZIP
  downloads, immutable source links, JSON evidence, explicit stale/unknown feed behavior.
- Scheduled public-provenance refresh. It checks the official public leaderboard and upstream heads,
  but **never retrains, changes an approval, spends a slot, commits, or uploads a competition file**.

## Setup, data placement and verification

CPU research is supported; a GPU is **not** a universal prerequisite for this project.
GitHub access is needed for the hash-pinned public bridges; no DrivenData credentials are stored.

```bash
python -m venv .venv
.venv/bin/pip install -e '.[test]'
# For exact research dependency versions, use requirements-lock.txt.
bash scripts/download_competition_data.sh   # 2026-10-27: completed; all core pins verified
.venv/bin/python scripts/prepare_data.py      # 2026-10-27: 19/19 shared cache bands verified
.venv/bin/python scripts/restore_registry.py  # 231 sources -> 179 unique comparators
.venv/bin/python scripts/run_tasc_lane.py --build-features
.venv/bin/python scripts/run_tasc_lane.py --execute
.venv/bin/python scripts/package_tasc_best_arm.py
.venv/bin/python scripts/build_current_decision.py
.venv/bin/pytest -q

# Reopen the actual downloadable bytes. Exit 0 means FORMAT pass only.
.venv/bin/python scripts/validate_submission.py docs/downloads/{tif}
# Deliberately exits 2 for this locally valid but unapproved artifact:
.venv/bin/python scripts/validate_submission.py --require-submit-ready docs/downloads/{tif}

# Restore frozen peer corpus only for audit, never model inputs:
.venv/bin/python scripts/fetch_repositories.py
.venv/bin/python scripts/audit_repositories.py
# The next command audits the unchanged surface; it does NOT retrain/place dots:
.venv/bin/python scripts/audit_registry.py

# Rebuild report pages from persisted measured JSON (no modelling):
python scripts/refresh_feed.py --offline
python scripts/build_current_decision.py
python scripts/build_site.py
python scripts/build_readme.py
# Preview, not for production deployment:
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

Optional rendered-site checks on Linux (not needed to build or deploy the site):

```bash
npm ci
# Against the running static preview on the test machine:
BASE_URL=http://127.0.0.1:8000/ npm run test:browser
# Minimal containers without NSS/NSPR may also need BROWSER_COMPAT_LIBS=1.
```

The browser check visits all five pages at desktop/mobile sizes, rejects body overflow and
JavaScript page errors, tests the site filter, and hashes the actual downloaded TIFF.
Screenshots stay in ignored `.cache/browser-review/`; the JSON receipt is inspectable in
[evidence/browser_checks.json](evidence/browser_checks.json). These are site checks, not evidence
of scientific efficacy or organizer upload acceptance.

`scripts/run_experiment.py` contains the exact frozen training screen. Its persisted experiment
ledger and result guard deliberately **prevent silent reruns or retuning of this stopped lane**.
Recomputing DTI/CI from persisted block terms and revalidating artifacts is allowed; another
hypothesis needs a separately authorized prospective record, not deletion of the failed result.
There is no competition uploader. This static site serves a real pre-generated artifact; it does
not falsely claim that a browser button trains the model.

## Limitations and highest-priority next work

1. **No final high-scoring upload-ready submission was produced.** The unique-byte research TIFF
   fails the scientific and literal-overlap gates. Stop is binding; no final-dot check is claimed.
2. **Missing lane and registry policy:** obtain an actual single-method assignment and a separately
   authorized scope policy. Do not privately exempt lattices/dense surfaces or target lattice holes.
3. **Input provenance and semantics:** verify official-origin data and original per-band meanings.
   `tc` and the depth-surface interpretation are ambiguous in mirror/peer materials. Do not claim
   physical units, heat or permeability from a classifier on unverified descriptors.
4. **Honest current-best comparison:** the clean 19-band control was refitted, but an identically
   rerun cross-repository best and untouched confirmation were not established. Static historical
   catalogue-derived rasters must not be scored as if they were leak-free refitted models.
5. **Authentication and weekly cap:** the official submissions endpoint redirects to login.
   The rule PDF says up to three weekly; the account's actual remaining allowance and exact-file
   score receipts are unavailable. Never request or store credentials in chat or Git.
6. **Coverage and confidence:** nine frozen snapshots are not all 92 sites, releases/private files
   or later commits. Hide-and-recover and conditional bootstrap intervals are not hidden-new-fault
   leaderboard estimates. Negative/background labels remain incomplete. Separately fitted OOF
   models can create confidence seams; geometric patterns in the thumbnail are not verified faults.
7. **Scientific target:** competition faults are not direct vent/resource confirmation. Future
   geothermal discovery needs convergent independent evidence, not just a probability map.
8. **Pages administration scope:** the integration cannot change Pages settings (HTTP 403).
   The existing main/root publisher is retained; `scripts/stage_pages.py` gives workflow deploys
   the same root-to-`/docs/` layout. This avoids incompatible download paths without a manual
   configuration change. Only actual GitHub run/deployment receipts establish publication.
9. **Unsatisfiable literal lattice gate:** the retained spacing-5 calibration lattice covers at
   least 70% of the footprint within 3 px, so by the pigeonhole principle every substantial new
   dot set has >70% directional overlap with it. The shared tool reports a competing-method
   diagnostic, but this session keeps the literal unseparated gate binding. A protocol owner must
   decide how space-filling calibration controls should be handled; we did not waive them privately.
10. **Inherited mislabeling corrected:** WBG-H1 peer pages previously called owner-reported values
   “ORGANIZER-CONFIRMED”. The generator, frozen cards and this session's pages now label them
   **USER-REPORTED / NOT ORGANIZER-CONFIRMED**. Two inherited official links were dead and were
   replaced with verified USGS/Copernicus-era official URLs.

[Official-source claim register](registry/sources.json) · [Irregularities](registry/irregularities.json)
· [Frozen preregistration](registry/preregistration.json) · [Review passes](evidence/review_passes.json)

## Project principles

**Maximize P(Win):** prioritize reliable out-of-sample evidence and scientific novelty over
more submissions, cosmetic file changes or public-leaderboard overfitting.
**Own the Outcome:** validate exact output bytes, preserve negative results, surface access gaps,
and never hand an unapproved file to the user as an upload recommendation.

## Starting point for every future session

Read this current status, `registry/run_card.json`, `registry/irregularities.json`, and the full
standing request below before work. Historical claims and intended capabilities in the prompt are
not verified facts. The measured run card takes precedence over stale factual assumptions.

<details>
<summary><strong>Complete standing user request — archived intent, not verified findings</strong></summary>

'''
    (ROOT / "README.md").write_text(header + standing + "\n</details>\n", encoding="utf-8")
    print("README updated with current decision and the complete archived standing request.")


if __name__ == "__main__":
    main()
