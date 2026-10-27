#!/usr/bin/env python3
"""Keep the README decision current and embed the complete supplied standing brief."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    card = json.loads((ROOT / "registry/run_card.json").read_text())
    wbg_h1_rc = json.loads((ROOT / "evidence/wbg_h1/run_card.json").read_text())
    h, c, d = card["holdout"], card["control_holdout"], card["paired_delta_holdout"]
    tif = Path(card["artifact"]).name
    h1_tif = wbg_h1_rc["raster_sha256"]["tif_file"]
    h1_zip = wbg_h1_rc["raster_sha256"]["zip_file"]
    standing = (ROOT / "docs/standing-prompt.md").read_text()
    w2 = json.loads((ROOT / "evidence/wbg2/run_card.json").read_text())
    w2tif = Path(w2["artifacts"]["tif"]).name
    w2est = w2["score_estimate"]["value"]
    w2lo, w2hi = w2["score_estimate"]["ci95"]
    w2nine = json.loads((ROOT / "evidence/wbg2/nine_site_uniqueness.json").read_text())
    d1 = json.loads((ROOT / "registry/run_card_wbg_d1.json").read_text())
    d1h = d1["holdout"]
    d1_tif = Path(d1["artifact"]).name
    d1_block = f'''## Newest lane — WBG-D1 radiometric alteration (2026-10-27): unique TIF, verdict negative

**[Open the WBG-D1 dashboard](docs/wbg-d1.html)** · [Five ranked hypotheses](docs/wbg-d1-hypotheses.md) ·
[Download the unique research TIF](docs/downloads/{d1_tif}) · [Run card](registry/run_card_wbg_d1.json)

A self-declared, preregistered lane (`registry/preregistration_wbg_d1.json`) built seven new channels
from official USGS GeoDAWN radiometric grids (K, Th/K, U/Th high-pass/edge transforms and a
TMI−upward-continuation shallow residual; DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)) and
ran all three budgeted experiments on `gems57-pooled-hide-v2` (n=11,330 withheld positives):

- EXP-1 deterministic radiometric composite: **HOLDOUT-DTI {d1["exp1_deterministic"]["deterministic_rad_composite"]["dti"]:.4f}** vs fixed-seed random dots **{d1["exp1_deterministic"]["random_dot_baseline"]["dti"]:.4f}** — the off-ridge alteration placements underperform random catalogue recovery.
- EXP-2 19-band control **HOLDOUT-DTI {d1h["control_dti"]:.6f}** vs 19+7 channel candidate **{d1h["candidate_dti"]:.6f}**; paired Δ **{d1h["paired_delta"]:+.6f}**, 95% CI [{d1h["paired_ci95"][0]:+.6f}, {d1h["paired_ci95"][1]:+.6f}] — no improvement established.
- EXP-3 fixed 37,654-dot NMS emission: dotted intrinsic HOLDOUT-DTI **{d1h["dotted_holdout_intrinsic_no_collar_dti"]:.4f}** (collar-packaged pessimistic bound **{d1h["dotted_holdout_collar_pessimistic_dti"]:.4f}**).

The shipped TIF passes all 10 automated portal gates (0 NaN/inf across 12,279,160 cells, strict [0,1],
EPSG:32611, exact grid, 200 m dead-collar clean) and is byte/pixel-unique across the aligned registry
plus parallel-lane rasters; against every real geological dot-field prior (including the WBG-2 file,
3 px overlap 0.180, Spearman ~0.000) the worst 3 px overlap is **0.4846 ≤ 0.70** and worst Spearman
**0.106 ≤ 0.90**. Literal STOPs come only from the synthetic r13 calibration lattice (pigeonhole
artifact) and the project's own dense continuous WBG-C1 surface. Because the efficacy gate failed,
**DOWNLOAD: YES (research) · SUBMIT: NO · zero slots used**. No leaderboard projection is made from a
local HOLDOUT-DTI.

'''

    header = f'''# WBG GEMS — evidence-first fault mapping

## SUBMIT THIS FILE: [{w2tif}](docs/downloads/{w2tif})

**[Executive summary + one-click download](docs/wbg2.html)** · [ZIP](docs/downloads/{w2tif.replace('.tif', '.zip')}) ·
[markdown summary](docs/wbg2-executive-summary.md) · [run card](evidence/wbg2/run_card.json) ·
[live site](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/wbg2.html)

| | |
|---|---|
| File to submit | `docs/downloads/{w2tif}` (+ identical one-member `.zip`) |
| Estimated score | **{w2est:.4f}** — MODEL-ESTIMATE, 95% interval {w2lo:.4f}–{w2hi:.4f}, R² {w2["score_estimate"]["r2"]:.3f}, n=9. **Not organizer-confirmed.** |
| Unique vs GEMSDOE24/25/27/28/30/31/32/33/36 | **YES** — {w2nine["n_audited"]}/9 audited; max {w2nine["max_enrichment_vs_chance"]:.2f}× chance overlap, max \|ρ\| {w2nine["max_abs_spearman"]:.3f} |
| Format | single-band float32, EPSG:32611, 3730×3292, values in [0,1], no NaN anywhere (zeros mode) |
| sha256 | `{w2["raster_sha256"]}` |
| Slots used | 0 |

> **Honest reading.** WBG-2 is unique and format-valid, so it is safe to upload. Its estimate is only
> **{w2est - 0.2778:+.4f}** above the best focus-site artifact (0.2778), which is *within model error*:
> it ties that artifact rather than beating it. The route to the 0.39–0.45 leaderboard band is the
> login-gated official `training_features.tif`; see [the executive summary](docs/wbg2.html).

## Older file — DOWNLOAD: YES, for research. SUBMIT: **NO**.

**27 October 2026 follow-up: [all four releases, exact-byte revalidation and trust corrections](docs/portfolio-review.html)** ·
[Machine-readable review](docs/data/portfolio-review.json). No new experiment: the lane remains stopped.
All four are negative research downloads, not recommended contest submissions. Leaderboard estimates remain unavailable.
The [parallel exact-reference audit](docs/release-review.html) and its [review notes](docs/review-20261027.md) are also preserved; both reviews reach the same negative decision.

**[Open the research desk](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/)** ·
[Executive summary](docs/executive-summary.md) · [Submission guide](docs/how-to-submit.html) ·
[Exact JSON run card](registry/run_card.json)

**[Download the frozen research TIFF](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/downloads/{tif})** ·
[One-TIFF ZIP](docs/downloads/{tif.replace('.tif', '.zip')}) ·
[TIFF in repository](docs/downloads/{tif}) · [Validation receipt](docs/downloads/{tif.replace('.tif', '.json')})

> **NEGATIVE RESULT.** This is a genuinely generated, format-valid **continuous research surface**,
> not a final dotted or promoted competition submission. It fails paired efficacy and the literal
> registry-overlap gate. The method lane was not assigned in the prompt. **Do not upload it.**
> No final dots were placed, no real submission was selected, and **zero competition slots were used**.
> “Different bytes” is not “lane unique”; “local format pass” is not organizer acceptance.

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

The direct **official public-leaderboard observation on 2026-10-26 was 0.4437**, not the prompt's
older targets. That is **not** an organizer result for any project TIFF. A higher project score
was not obtained or credibly projected in this session.

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
- **[WBG-H1 / DPGF-1 corrected result page](docs/wbg-h1-dpgf1/index.html)** — research only, **DO NOT SUBMIT**.
  [TIFF]({h1_tif}) · [ZIP]({h1_zip}) · SHA-256 `{wbg_h1_rc['raster_sha256']['tif_sha256']}`.
  Name `{wbg_h1_rc['submission_name']}`. Frozen **HOLDOUT-DTI {wbg_h1_rc['holdout_dti']['dti']:.6f}**,
  95% CI [{wbg_h1_rc['holdout_dti']['ci95'][0]:.6f}, {wbg_h1_rc['holdout_dti']['ci95'][1]:.6f}],
  `{wbg_h1_rc['holdout_dti']['evaluator_version']}`, {wbg_h1_rc['holdout_dti']['n_withheld_positives']:,} withheld positives.
  Literal lattice overlap **99.8035%** exceeds 70%; sparse/symmetric checks do not authorize an exemption.
  The inherited LLI forecast, claims of organizer-confirmed scores, and private-count inversion are
  **not verified evidence**. Original cards remain frozen with explicit corrections on the live page.
- Older two-argument `validate_submission.py candidate.tif reference.tif` callers retain their
  supplied-reference format API; this is compatibility only and never confers slot approval.
  WBG-C1 still uses the unchanged, pinned `gems57` all-finite validator/writer.
  The separate integration CLI now rejects mismatched source grids, input overwrite aliases and
  portal-unsafe NaN twins; [explicit source amendment](evidence/integration_amendments_20261027.json)
  preserves its prior hash/archive. No metric, evaluator or pinned-template fork was introduced.
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
bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py
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

# Reopen all four local releases (no modelling, no slot):
.venv/bin/python scripts/build_portfolio_review.py

# Rebuild report pages from persisted measured JSON (no modelling):
python scripts/refresh_feed.py --offline
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

The browser check visits all nine current pages at desktop/mobile sizes, rejects body overflow and
JavaScript page errors, tests the site filter, and hashes all four actual downloaded TIFFs.
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
    (ROOT / "README.md").write_text(header + d1_block + standing + "\n</details>\n", encoding="utf-8")
    print("README updated with current decision and the complete archived standing request.")


if __name__ == "__main__":
    main()
