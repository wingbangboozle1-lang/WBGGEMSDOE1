# WBG GEMS — evidence-first fault mapping

## NO FILE APPROVED FOR SUBMISSION

**[WBG-4 (CSJF-1) Executive Summary & Master Decision Table](docs/wbg4/index.html)** ·
**[How to Submit Subpage](docs/wbg4/how-to-submit.html)** ·
**[0.2778 PhD Forensics & 4 Hypotheses](docs/wbg4/forensics-and-hypotheses.html)** ·
[Download WBG-4 TIFF (research only)](docs/downloads/wbggemsdoe1-wbg4-csjf1-edti-35135-20261027-b3dacd59-zeros.tif) ·
[WBG-4 ZIP](docs/downloads/wbggemsdoe1-wbg4-csjf1-edti-35135-20261027-b3dacd59-zeros.zip) ·
[WBG-4 Run Card JSON](evidence/wbg4/run_card.json) ·
[464-Raster Uniqueness Audit](evidence/wbg4/uniqueness_audit.json)

**[WBG-3 Executive Summary & Master Decision Table](docs/wbg3/index.html)** ·
**[How to Submit Subpage](docs/wbg3/how-to-submit.html)** ·
**[0.2778 PhD Forensics & 4 Hypotheses](docs/wbg3/forensics-and-hypotheses.html)** ·
[Download WBG-3 TIFF (research only)](docs/downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.tif) ·
[WBG-3 ZIP](docs/downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.zip) ·
[WBG-3 Run Card JSON](evidence/wbg3_spipmr/run_card.json) ·
[Parallel EXP3DET Summary](docs/wbg3.html) ·
[Parallel EXP3DET Run Card](evidence/wbg3/run_card.json)

**[Executive audit and nine-site table](docs/wbg2.html)** ·
[Download WBG-2 TIFF for research only](docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif) ·
[ZIP for research](docs/downloads/wbg2-offcatalogue-density-36k-20261027.zip) ·
[run card](evidence/wbg2/run_card.json) · [shared-gate audit](evidence/wbg2/safety_audit_20261027.json)

| Artifact | Local format | Score estimate / holdout | Literal registry decision |
|---|---|---|---|
| `wbggemsdoe1-wbg4-csjf1-edti-35135-20261027-b3dacd59-zeros.tif` | One float32 band, zeros mode `[0, 1]`, 0 NaN/Inf, 35,135 binary dots; 15/15 checks PASS | **HOLDOUT-DTI 0.165424** (`gems-segment-pooled-v1`, n=60,988, 95% CI [0.152338, 0.178931], +78.0% vs ctrl); **HOLDOUT-DTI 0.094601** (`seed=20`, n=11,321); **Untouched Confirm HOLDOUT-DTI 0.103660** (`seed=77`, n=11,326, +102.3% vs 0.051234 ctrl). Leaderboard est.: **Unavailable**. | **DO NOT SUBMIT**. Competing sparse (460 rasters across 24 repos): **PASS 57.25% <= 70%** (max \|rho\| = 0.4952 <= 0.90). Literal overlap: **99.6983%** vs `r13-lattice-s5` & **100%** vs `WBG-C1` (>70% STOP). |
| `wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.tif` | One float32 band, zeros mode `[0, 1]`, 0 NaN/Inf, 36,800 binary dots; 15/15 checks PASS | **HOLDOUT-DTI 0.118180** (`gems-segment-pooled-v1`, n=60,988, 95% CI [0.103658, 0.132432], 4/4 fold wins vs 0.090781 ctrl); **HOLDOUT-DTI 0.121862** (`gems57-pooled-hide-v2`, n=11,330). Leaderboard est.: **Unavailable**. | **DO NOT SUBMIT**. Competing sparse (206 rasters): **PASS 59.38% <= 70%** (27.55% vs GEMSDOE32 B2; 43.40% vs WBG-S2). Literal overlap: **99.9946%** vs `r13-lattice-s5` & **100%** vs `WBG-C1` (>70% STOP). |
| `wbg2-offcatalogue-density-36k-20261027.tif` | One float32 band, finite [0,1], grid matches pinned mirror; TIFF/ZIP bytes verified | **Unavailable**; fold-safe replay measures `HOLDOUT-DTI 0.000341` (`gems-segment-pooled-v1`) / `0.097610` (`gems57-pooled-hide-v2`); no organizer receipt | **DO NOT SUBMIT**. 99.8972% final-dot overlap with a registered lattice exceeds 70%. |

The previous WBG-2 "safe to upload" claim and numerical projection are **withdrawn**. The old
code applied a private enrichment exception, checked eight local references and a separate nine-champion
diagnostic rather than the full registry. The shared literal rule has no such exception. A retrospective surface check also fails and cannot establish that
pre-placement checks happened. This safety integration did no new training or placement and used no competition slot.
The historic catalogue buffer was Manhattan, not a 400 m Euclidean disc: 813 existing dots are
closer than 400 m Euclidean. The owner-mirror 19-band stack was restored and hash-checked, not
authenticated by DrivenData.
See [four untested research hypotheses](docs/research/future-hypotheses-20261027.md) and
[the 27 October source audit](evidence/official_source_audit_20261027.json) and
[three safety-review passes](evidence/wbg2/review_passes_20261027.json).
Concurrent reviews are preserved as historical context: [protocol](docs/protocol-review-20261027.md),
[repository](docs/repo-review-20261027.md), and [session](docs/session-review-20261027.md).
Their older private-distance metrics and 400 m buffer interpretation are superseded by the
shared-Euclidean safety audit above. The earlier raw approval remains archived, never authorized.

## Earlier file — DOWNLOAD: YES, for research. SUBMIT: **NO**.

**27 October 2026 follow-up: [four earlier releases, exact-byte revalidation and trust corrections](docs/portfolio-review.html)** ·
[Machine-readable review](docs/data/portfolio-review.json). No new experiment: the lane remains stopped.
All four are negative research downloads, not recommended contest submissions. Leaderboard estimates remain unavailable.
The [parallel exact-reference audit](docs/release-review.html) and its [review notes](docs/review-20261027.md) are also preserved; both reviews reach the same negative decision.

**[Open the research desk](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/)** ·
[Executive summary](docs/executive-summary.md) · [Submission guide](docs/how-to-submit.html) ·
[Exact JSON run card](registry/run_card.json)

**[Download the frozen research TIFF](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif)** ·
[One-TIFF ZIP](docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.zip) ·
[TIFF in repository](docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif) · [Validation receipt](docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.json)

> **NEGATIVE RESULT.** This is a genuinely generated, format-valid **continuous research surface**,
> not a final dotted or promoted competition submission. It fails paired efficacy and the literal
> registry-overlap gate. The method lane was not assigned in the prompt. **Do not upload it.**
> No final dots were placed, no real submission was selected, and **zero competition slots were used**.
> “Different bytes” is not “lane unique”; “local format pass” is not organizer acceptance.

| Artifact / decision | Measured evidence | Estimated leaderboard result | Exact-copy / literal uniqueness |
|---|---|---|---|
| [wbg-c1-commutator-research-surface-20261026-acea88448272.tif](docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif) — **research download only** | **HOLDOUT-DTI 0.014045**, 95% CI [0.011831, 0.016396], `gems57-pooled-hide-v2`, 11,330 withheld positives | **Unavailable**. Not inferred from holdout. Organizer-confirmed artifact result: **none**. | Byte- and normalized-pixel distinct from all 360 checked hashes; **FAIL** literal forward overlap 99.87% >70%. |

- Same-instrument 19-band control: **HOLDOUT-DTI 0.014146**, 95% CI [0.011931, 0.016500], same evaluator, 11,330 positives.
- Paired difference: **HOLDOUT-DTI -0.000101**, 95% CI [-0.000232, +0.000030], same evaluator/positives. No improvement established.
- Scientific representation: **unplaced continuous OOF confidence**, not matched-budget sparse dots, calibrated probabilities or a hidden-test leaderboard forecast.
- Leakage canaries: all 23 individual inputs tested in four folds; max orientation/missingness AUC **0.612397**, below 0.90. AUC is not DTI and passing this screen is not proof of no possible leakage.
- Local GeoTIFF: one float32 band, EPSG:32611, 3,730 × 3,292, 100 m, exact reference transform; all finite, min **0.000000**, max **0.880929**, zero outside the footprint and on the known catalogue.
- SHA-256: `8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875`.
- Name: `wbg-c1-commutator-research-surface-20261026-acea88448272`.
- Note (≤140 characters): `WBG-C1 curvature non-coaxiality; spatial OOF research surface; no dot placement; NOT approved for submission.`.

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

The official public leaderboard displayed **0.4544 on 2026-10-27** (public-page observation, not a project-file receipt), rather than the prompt's older targets. That is **not** an organizer result for any project TIFF. A higher project score
was not obtained or credibly projected in this session.

## Parallel work preserved during integration

- **[WBG-3 / SPI-PMR-WCS-1 (100% 1m-LiDAR-free & 10m-DEM-free)](docs/wbg3/index.html): DO NOT SUBMIT; no selector eligibility.**
  [How-to-submit subpage](docs/wbg3/how-to-submit.html) · [0.2778 PhD forensics & 4 hypotheses](docs/wbg3/forensics-and-hypotheses.html) ·
  [Research TIFF](docs/downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.tif) · [ZIP](docs/downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.zip) ·
  [run card](evidence/wbg3_spipmr/run_card.json) · [209-raster uniqueness audit](evidence/wbg3_spipmr/uniqueness_audit.json) ·
  [40-feature leakage canary](evidence/wbg3_spipmr/leakage_canary.json) · [preregistration](registry/wbg3_preregistration.json).
  TIFF SHA-256 `f158a890dcb5f897ef35282ed05d291e54c4df9b83cf891870193d329b160fb4`; ZIP SHA-256 `1fff1657506895e3b0a0a0bc1e3c590dfcc1134d4d5b15606ce2ccfc1ba23e0a`; name `wbggemsdoe1-wbg3-spipmr-wcs-1458d60c`; note `WBG-3 SPI+PPDR+MonogenicPC+WCS 36800d zeros | segDTI=0.1182 iDTI=0.1219 | research DO NOT SUBMIT` (96 chars).
  3/3 preregistered arms executed on 100 m competition geophysics + label-free SGMC/GDR (`444.3s`, 0 slots used).
  Beats 19-band control across 4/4 spatial folds: **HOLDOUT-DTI 0.118180** vs **0.090781** (`gems-segment-pooled-v1`, paired ΔDTI `+0.027399`, 95% CI `[+0.014361, +0.041700]`) and **HOLDOUT-DTI 0.121862** vs **0.076470** (`gems57-pooled-hide-v2`).
  Passes full-footprint pre-placement correlation (`max |ρ| = 0.644883 <= 0.90`) and competing-sparse overlap across all 206 sparse rasters (`max 59.38% <= 70%`; `27.55%` vs `GEMSDOE32 B2`; `43.40%` vs `WBG-S2`), while binding literal overlap hits **99.9946%** vs `r13-lattice-s5` and **100%** vs `WBG-C1` and trails 10m-3DEP `S3DEP1` (`0.166060`).
- **[WBG-S2 / MKSF-1 result](docs/wbg-s2-mksf1/index.html): DO NOT SUBMIT; no selector eligibility.**
  [Research TIFF](docs/downloads/wbggemsdoe1-wbg-s2-exp3-mksf-vierbeincoulomb-20261027-e9b4a3c09065-zeros.tif) · [ZIP](docs/downloads/wbggemsdoe1-wbg-s2-exp3-mksf-vierbeincoulomb-20261027-e9b4a3c09065-zeros.zip) ·
  [run card](evidence/wbg_s2/run_card.json) · [independent two-witness safety audit](evidence/wbg_s2/safety_review_20261027.json) ·
  [three safety-review passes](evidence/wbg_s2/safety_review_passes_20261027.json).
  TIFF SHA-256 `6992387620fcb2d7f3a06d867b79b6ad770d7006b87d35b131e27a5035c62880`. Local format checks pass, but final dots overlap pinned
  r13 by **99.5538%** and WBG-C1 by **100%**; both exceed 70%. The sampled pre-placement
  Spearman screen is not full literal clearance. Three arms were run in the parallel session;
  this integration did not retrain or place new dots. Parallel-reported selected-arm
  **HOLDOUT-DTI 0.183594**, 95% CI [0.170313, 0.196956], `gems-segment-pooled-v1`, n=60,988;
  **HOLDOUT-DTI 0.147773**, 95% CI [0.128077, 0.167791], `gems57-pooled-hide-v2`, n=11,330.
  Arms were selected on these splits, not independently replayed here or confirmed on untouched data.
  They are not a verified fleet ranking, organizer score or leaderboard forecast.

While this branch was working from the one-line initial checkout, other sessions merged TIP1 and
MVGZ negative results into `main` (integrated snapshot `b9a2d5301c0c971dcc1219f9ad6b29c68f68ee21`).
Their frozen scientific modules, receipts and artifacts are retained; they were **not rerun**.
The earlier WBG-C1 screen used one experiment; the parallel WBG-S2 run used three separate arms.
This safety integration started no experiment and did not reset any inherited budget.
Different evaluator/split/representation results must not be pooled or ranked as comparable scores.

- [Original parallel site, with its own frozen assets and data](docs/parallel/main-b9a2d53/index.html)
- [Original main README](research/inherited-main-README-b9a2d53.md) (historical commands/paths)
- [Byte-preservation/integration receipt](evidence/parallel_main_integration.json)
- [Frozen TIP1 card](evidence/tip1_run_card_20261026.json) and [MVGZ card](evidence/run_card.json)
- **[WBG-H1 / DPGF-1 corrected result page](docs/wbg-h1-dpgf1/index.html)** — research only, **DO NOT SUBMIT**.
  [TIFF](docs/downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif) · [ZIP](docs/downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.zip) · SHA-256 `e46e4c175c5afceac148d0475a23808c3ae8bf6e5edad8faea919ed847b0d7dd`.
  Name `wbggems1-dpgf1-exp-3-20261026-0749b3c8195f`. Frozen **HOLDOUT-DTI 0.123310**,
  95% CI [0.108921, 0.137557],
  `gems-segment-pooled-v1`, 60,988 withheld positives.
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

- [Four earlier ranked hypotheses](docs/hypotheses.md), with layers, transforms,
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
.venv/bin/python scripts/validate_submission.py docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif
# Deliberately exits 2 for this locally valid but unapproved artifact:
.venv/bin/python scripts/validate_submission.py --require-submit-ready docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif

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
2. **Missing lane and registry policy:** establish an actual single-method assignment and a separately
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

# Standing user prompt — supplied 2026-10-26

> **CURRENT STATE — updated 2026-10-27.** The prior WBG-2 upload recommendation and
> numerical projection were withdrawn. The exact TIFF is a local-format-passing **research-only**
> artifact and fails the literal 70% registry rule: 99.8972% of its existing dots are within
> 3 pixels of the pinned lattice. Its prior surface also fails a retrospective test. No verified
> holdout result or organizer receipt is available. **DO NOT SUBMIT.** See `docs/wbg2.html`
> and `evidence/wbg2/safety_audit_20261027.json`. This status supersedes any prior approval.
> The user request below is archived intent, not independently verified evidence.


## Active follow-up instructions (2026-10-27 summary, not a verbatim transcript)

- Compare GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36, give an obvious research download and honest submission decision, explain the reported GEMSDOE32 0.2778, and never turn an unreceipted score or model projection into organizer confirmation. Public leaderboards are dated observations, not project receipts.
- The user requests a high-scoring genuinely unique GeoTIFF and automated checks without human inspection. If literal novelty, leakage, holdout, format or authorization gates fail, publish a negative card instead of a false success. A local no-human preflight does not replace the organizer's expert review.
- For a future specifically assigned single-method lane, rank 3–5 physical hypotheses first, state data, transforms, off-catalogue rationale, named non-fault mimics, distinctions, costs and source availability. The referenced assigned method paragraph was not present here. Do not reset stopped lanes.
- Use the shared cached stack, holdout evaluator and submission writer. Withhold whole fault components with buffer, recompute catalogue-derived features from visible faults in each fold, mask visible faults pixel-exactly, and test every feature separately for leakage (AUC >0.90 is suspect). Report pooled triangular-kernel DTI at α=0.2, β=0.8, 300 m with evaluator version, withheld count and 95% CI.
- Before placement compare the surface against every registry raster and stop for Spearman >0.90 or forward 3-pixel overlap >70%; check final dots again. Do not exempt dense/lattice fields, silently skip registry entries, copy past predictions or tune around gaps. At most three experiments or two hours. A real slot requires an independently validated current-best comparison and a separate selector step; do not spend it implicitly.
- Each session ends with one JSON card containing hypothesis, mechanism, mimic, HOLDOUT-DTI/CI, registry correlation and overlap, raster SHA-256, exact validator results, submission name and ≤140-character note, and promote/negative verdict. The portal error “Predicted values must be in range [0, 1]” must be addressed with finite/range checks without inventing its cause.
- Link trusted official sources and flag access or provenance limits. Use eligible free sources only when needed; external data must be shareable and appropriately licensed. Record the standing request, conduct three review/fix passes, and create/merge a PR when authorized by repository permissions.

This is the user's request, retained as project intent, **not verified factual findings**. Historical scores, blocker claims, dates, source availability, and proposed capabilities below must be checked against current evidence. Read it together with the current README status, `registry/run_card.json`, and `registry/irregularities.json` before each session. The requested single-method lane paragraph was not supplied. The original request follows (trailing whitespace normalized; wording retained).

---

Review the repo.

I want to focus on  the highest scoring submissions from the following sites, GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36.  I want an executive summary on every site that is clear and obvious which is the best submission to submit to obtain a high score on the leaderboard.  It should also be unique and not an exact duplicate of any previous submission that is the same as below.  Keep iterating and testing until we have the highest scoring submission to download and submit.

We should be able to estimate the score for a submission.  I want a table in the executive summary that clearly lists what file to download, what the estimate score is, and whether it is a unique submission unlike any of the other GEMDOE sites listed below.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.  DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION.  BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION.  IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt.  Read the entire prompt.  A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.

PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this same prompt.

1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.

2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_[holdout.py](http://holdout.py) and submission_[writer.py](http://writer.py). Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.

3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.

4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.

5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.

6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

The following sites should serve as a starting point for understanding how to generate TIF submissions.  These websites are researched, and tested and have generated TIF submissions.  But we need to generate high scoring submissions.

Here are the results from submissions into the competition, separated by ....:

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score:

0.4413

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score:

0.4413

[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html)

gems-submission-20260925T001403Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/)

gems6_hgb88-topk03_33cec71ff0: 0.0286

....

[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html)

pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193

pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830

pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html)

gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560

....

[https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/)

gems-submission-20260926T163915Z-237f0063: 0.0343

....

[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html)

gems-submission-20260926T175114Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/)

lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461

....

[https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/)

Hedge-v2_submission: 0.1563

....

[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html)

2314b599: 0.0107

....

[https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html)

gems-structural-area06-v1: 0.0202

....

[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html)

r7-nms3-dem10-scarp_0c9199f14e62:0.1294

r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294

....

[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html)

gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782

....

[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html)

GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020

....

[https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/)

17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187

....

[https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/)

H19-C_20260930T212401Z_c11e495e: 0.0297

....

[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html)

h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894

h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922

....

[https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/)

h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461

h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921

H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280

h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839

....

[https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/)

20261001_r13-lattice-s5_v2_nan-outside:0.0904

....

[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html)

h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855

h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976

h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360

....

[https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/)

h19-4-reference-20260930-691e4dfa: 0.1894

....

[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html)

h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890

h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan: 0.1859

....

[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html)

h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002

h23-b-dti-optimal-emission-10pct-20261002-86176698-nan: 0.0748

....

[https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/)

h30-arrangement-matched-habitat-20261002-0d4e02e8-nan: 0.1352

....

[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)

h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477

....

[https://buffedlizard55-lab.github.io/GEMSDOE25/](https://buffedlizard55-lab.github.io/GEMSDOE25/)

dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE26/](https://buffedlizard55-lab.github.io/GEMSDOE26/)

dilcond-oof-v1-20261003-47629f496133-nan: 0.1223

....

[https://buffedlizard55-lab.github.io/GEMSDOE27/](https://buffedlizard55-lab.github.io/GEMSDOE27/)

topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan: 0.2449

....

[https://buffedlizard55-lab.github.io/GEMSDOE30/](https://buffedlizard55-lab.github.io/GEMSDOE30/)

d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE31/docs/](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)

h27-4-solo-d28-20261004-8acb75e1-nan:0.2708

....

[https://buffedlizard55-lab.github.io/GEMSDOE33/](https://buffedlizard55-lab.github.io/GEMSDOE33/)

h33d-analog-tip-stepover-r30-20261004-cb490425926e: 0.2632

....

[https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html)

h34-scatter-q50-arr-matched-20261004T223317Z: 0.0778

....

[https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html)

h35-06-aaa86efb25-20261004T225420098147Z-candidate: 0.0418

....

[https://buffedlizard55-lab.github.io/GEMSDOE36/docs/](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)

anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros: 0.2750

....

[https://buffedlizard55-lab.github.io/GEMSDOE37/](https://buffedlizard55-lab.github.io/GEMSDOE37/)

h6-physics-dotted-80k-20261005T055000Z-0bef9211631c: 0.1193

....

[https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html)

D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48-zero: 0.0763

....

[https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html)

xscale-worm-persistence-20261006T000541Z-nan: 0.0581

....

[https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html)

sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan: 0.0424

....

[https://buffedlizard55-lab.github.io/GEMSDOE45/](https://buffedlizard55-lab.github.io/GEMSDOE45/)

h51-km-faultzone-20261006-zeros: 0.0106

....

[https://buffedlizard55-lab.github.io/GEMSDOE49/](https://buffedlizard55-lab.github.io/GEMSDOE49/)

gate_ortho_w0.25-40k-20261006T213721Z-nan: 0.2376

....

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

....

[https://buffedlizard55-lab.github.io/GEMSDOE28/](https://buffedlizard55-lab.github.io/GEMSDOE28/)

h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan: 0.2708

h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan: 0.2649

h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan: 0.2710

h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan: 0.2707

....

[https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html)

efd28-repro-20261003-1cc7dc534d51-nan: 0.2600

repo-c0-habitat-emission-20261003-a4d439b07426-nan: 0.0041

sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan: 0.0512

wormrank-d28-20261003-59dcaf6dd11d-zeros:0.2560

wormsurv-filter-20261003-921f10960d6e-zeros: 0.0532

xfit-c0-habitat-20261003-ca879db0089a-zeros:0.0439

xfit-h41-union-qfaults-20261003-9edb34b99e3a-zeros:0.0356

....

[https://buffedlizard55-lab.github.io/GEMSDOE46/](https://buffedlizard55-lab.github.io/GEMSDOE46/)

r11f-scarp-radiometric-fusion-00e049b51218-zeros:0.1589

r12-scarp-rad-concordance-23e807e2de9f-zeros: 0.0843

....

[https://buffedlizard55-lab.github.io/GEMSDOE39/](https://buffedlizard55-lab.github.io/GEMSDOE39/)

h40-e-disc-h40e-30k-zeros: 0.0339

....

[https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html)

h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1: 0.0355

h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1-hard: 0.0397

h45-eulerdepthreadcluster-20261006-f28e5cff6826-zeros: 0.0984

....

[https://buffedlizard55-lab.github.io/GEMSDOE41/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE41/docs/index.html)

h42-submission-primary: 0.0245

....

[https://buffedlizard55-lab.github.io/GEMSDOE44/docs/](https://buffedlizard55-lab.github.io/GEMSDOE44/docs/)

h46-twostageAB_20261006T160000Z_b0cfe956-zeros: 0.0715

....

[https://buffedlizard55-lab.github.io/GEMSDOE47/](https://buffedlizard55-lab.github.io/GEMSDOE47/)

h60-lidarscarp-s2p0-20261007-nanoutside: 0.0430

....

[https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html)

h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8: 0.2296

....

[https://buffedlizard55-lab.github.io/GEMSDOE50/](https://buffedlizard55-lab.github.io/GEMSDOE50/)

h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite: 0.0764

....

[https://buffedlizard55-lab.github.io/GEMSDOE51/](https://buffedlizard55-lab.github.io/GEMSDOE51/)

h53-twostage-20261008T040951Z-9a0b32c871: 0.1047

....

[https://buffedlizard55-lab.github.io/GEMSDOE52/](https://buffedlizard55-lab.github.io/GEMSDOE52/)

h97b-candidate: 0.0856

....

[https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html)

h8-tiprelay-ridgeconcord-pr2-n80000-20261009-49bec522-zeros: 0.0159

....

[https://buffedlizard55-lab.github.io/GEMSDOE54/docs/](https://buffedlizard55-lab.github.io/GEMSDOE54/docs/)

h54c-manifest-edge-20261009T025732Z-73454bc5:0.0449

....

[https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html)

tensor_full-n16000-sep3-20261009T211747Z-nan: 0.0290

....

[https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html)

h56-final-dotted-ridge-d2p8-20261009T190421Z:0.0658

....

[https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html)

h57r-joint-strata-38000-20261010T214547Z-00cf5b2066f1-zeros: 0.0254

....

[https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html)

ml-binary-ridge-20261012T000000Z: 0.0180

....

[https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html)

gems59j-coherence-consensus-dotted-20261011T043000Z: 0.0499

....

[https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html)

h73-chi-coherent-corridor-12000-20261011T195818Z-zeros: 0.0351

....

[https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html)

h61a-basement-step-20000dots-20261011T012029Z-eb2ae4bb024b-zeros: 0.0009

h61o-vardepth-none-40000dots-20261011T160711Z-28d4fac611ea-zeros-zeros:0.0751

....

[https://buffedlizard55-lab.github.io/62GEMSDOE/](https://buffedlizard55-lab.github.io/62GEMSDOE/)

datum-lahontan-strain-gauge-defensible-440dots-zeros: 0.0000

....

[https://buffedlizard55-lab.github.io/GEMSDOE63/](https://buffedlizard55-lab.github.io/GEMSDOE63/)

cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4-zeros: 0.2303

....

[https://buffedlizard55-lab.github.io/GEMSDOE64/](https://buffedlizard55-lab.github.io/GEMSDOE64/)

h64-lidar-scarp-cv-20261011T220000Z:0.0383

....

[https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html)

sar-em-propensity-half-20261011T223500Z-5e4660cd-zeros:0.0431

....

[https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html)

gems66-lidar03-cvretrain-reliefdecile-37654dots-20261020T190152Z-zeros:0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE67/](https://buffedlizard55-lab.github.io/GEMSDOE67/)

h67a-orientip-lane-29447dots-20261012T021226Z-allfinite:0.0356

ovtr-ml-cover-tau3p0-20261012-nan:0.1426

....

[https://buffedlizard55-lab.github.io/GEMSDOE68/](https://buffedlizard55-lab.github.io/GEMSDOE68/)

gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-nan:0.0437

gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-zeros: 0.0437

....

[https://buffedlizard55-lab.github.io/GEMSDOE69/](https://buffedlizard55-lab.github.io/GEMSDOE69/)

gems69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5:0.0053

....

[https://buffedlizard55-lab.github.io/GEMSDOE70/](https://buffedlizard55-lab.github.io/GEMSDOE70/)

gems70-p5-dual-submod300-oof38k-20261020:0.2478

....

[https://buffedlizard55-lab.github.io/GEMSDOE71/](https://buffedlizard55-lab.github.io/GEMSDOE71/)

gems71-hydro-conduit-38800-20261020T120000Z-zeros: 0.0558

....

[https://buffedlizard55-lab.github.io/GEMSDOE72/](https://buffedlizard55-lab.github.io/GEMSDOE72/)

gemsdoe72-h72-1-sgmc-offcatalogue-20261020T195456Z-6e6525e5-zeros: 0.0492

....

[https://buffedlizard55-lab.github.io/GEMSDOE73/](https://buffedlizard55-lab.github.io/GEMSDOE73/)

gems73-h73-mcsc-seamfree-blakely-37654dots-20261021T073716Z-b27ac445-zeros: 0.1917

....

[https://buffedlizard55-lab.github.io/GEMSDOE74/](https://buffedlizard55-lab.github.io/GEMSDOE74/)

gemsdoe74-triregime-radon-piedmont-37654-20261021T051000Z-zeros:0.0669

....

[https://buffedlizard55-lab.github.io/GEMSDOE75/](https://buffedlizard55-lab.github.io/GEMSDOE75/)

gems75-trlt-radon-loco-ridge-20261021-zeros:0.1627

....

[https://buffedlizard55-lab.github.io/GEMSDOE76/](https://buffedlizard55-lab.github.io/GEMSDOE76/)

gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros:0.1555

gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros:0.2343

....

[https://buffedlizard55-lab.github.io/GEMSDOE77/](https://buffedlizard55-lab.github.io/GEMSDOE77/)

gems85-h85-edti-collar35-skel-r33-20261021-d97b248e-zeros:0.0964

....

[https://buffedlizard55-lab.github.io/GEMSDOE78/](https://buffedlizard55-lab.github.io/GEMSDOE78/)

gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros:0.1564

....

[https://buffedlizard55-lab.github.io/GEMSDOE79/](https://buffedlizard55-lab.github.io/GEMSDOE79/)

gems79-tilt-ring-100000dots-20261022T212135Z-50a5d7498c71-zeros:0.0005

....

[https://buffedlizard55-lab.github.io/GEMSDOE80/](https://buffedlizard55-lab.github.io/GEMSDOE80/)

gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros:0.0943

....

[https://buffedlizard55-lab.github.io/GEMSDOE81/](https://buffedlizard55-lab.github.io/GEMSDOE81/)

gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros:0.0041

....

[https://buffedlizard55-lab.github.io/GEMSDOE82/](https://buffedlizard55-lab.github.io/GEMSDOE82/)

gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros:0.1886

....

[https://buffedlizard55-lab.github.io/GEMSDOE83/](https://buffedlizard55-lab.github.io/GEMSDOE83/)

gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros:0.0573

....

[https://buffedlizard55-lab.github.io/GEMSDOE84/](https://buffedlizard55-lab.github.io/GEMSDOE84/)

gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros:0.0132

....

[https://buffedlizard55-lab.github.io/GEMSDOE85/](https://buffedlizard55-lab.github.io/GEMSDOE85/)

gemsdoe85-hjcd-ventbridge-submod-zeros: 0.1110

....

[https://buffedlizard55-lab.github.io/GEMSDOE86/](https://buffedlizard55-lab.github.io/GEMSDOE86/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE87/](https://buffedlizard55-lab.github.io/GEMSDOE87/)

h87-h87-cmgep-20261022T060000Z-8f394f43:0.0500

....

[https://buffedlizard55-lab.github.io/GEMSDOE88/](https://buffedlizard55-lab.github.io/GEMSDOE88/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE89/](https://buffedlizard55-lab.github.io/GEMSDOE89/)

gemsdoe89-bh-rtp-habc-20261024-d7e1507c-zeros:0.0301

....

[https://buffedlizard55-lab.github.io/GEMSDOE90/](https://buffedlizard55-lab.github.io/GEMSDOE90/)

gems90-cnc-35000dots-20261024T084324Z:0.0749

....

[https://buffedlizard55-lab.github.io/GEMSDOE91/](https://buffedlizard55-lab.github.io/GEMSDOE91/)

gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros:0.1367

gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros:0.1823

gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405:

....

[https://buffedlizard55-lab.github.io/GEMSDOE92/](https://buffedlizard55-lab.github.io/GEMSDOE92/)

gemsdoe92-listricdip-updip50-37654-20261025T190000Z-zeros:0.0255

....

[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)

h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477

gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros:0.0859

....

[https://buffedlizard55-lab.github.io/GEMSDOE25/](https://buffedlizard55-lab.github.io/GEMSDOE25/)

dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600

gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros:0.0742

....

[https://buffedlizard55-lab.github.io/GEMSDOE27/](https://buffedlizard55-lab.github.io/GEMSDOE27/)

topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan: 0.2449

gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite:0.2190

gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite:

....

[https://buffedlizard55-lab.github.io/GEMSDOE28/](https://buffedlizard55-lab.github.io/GEMSDOE28/)

h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan: 0.2708

h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan: 0.2649

h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan: 0.2710

h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan: 0.2707

gems28-s18-mxtp-20261025-3e95505c011a-allfinite:0.0217

....

[https://buffedlizard55-lab.github.io/GEMSDOE30/](https://buffedlizard55-lab.github.io/GEMSDOE30/)

d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca: 0.2600

gems30-MSDB1-edge44090-20261025-e7856ec3f14a:0.1462

....

[https://buffedlizard55-lab.github.io/GEMSDOE31/docs/](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)

h27-4-solo-d28-20261004-8acb75e1-nan:0.2708

....

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

....

[https://buffedlizard55-lab.github.io/GEMSDOE33/](https://buffedlizard55-lab.github.io/GEMSDOE33/)

h33d-analog-tip-stepover-r30-20261004-cb490425926e: 0.2632

....

[https://buffedlizard55-lab.github.io/GEMSDOE36/docs/](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)

anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros: 0.2750

....

I think it makes sense that in order for a submission to be validated that it needs to pass certain high scoring validation gates before confirming whether a file is unique and can be submitted for scoring.

The following is the leaderboard for the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)

See below for more links and information related to the competition:

[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)

[https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)

[https://gbcge.org/current-projects/ingenious/](https://gbcge.org/current-projects/ingenious/)

[https://epsg.io/32611](https://epsg.io/32611)

[https://en.wikipedia.org/wiki/Tversky_index](https://en.wikipedia.org/wiki/Tversky_index)

We need to quickly look at the results and results from the GEMSDOE websites above.

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above.  We need to come up with distinct and unique strategies to score higher in this competition leaderboard.  We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents.  We should store all of our information and knowledge that we can gather from official verified sources.  This will serve as a starting point for other projects as well.  We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for.  So it's important to be contrarian but be smart about it.  We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents.  We need to do deep research and critical thinking and come up with new hypothesis to test.

0.3195	is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website.  It should be unique, take unique approaches to generating a submission that can score higher than 0.3195.

Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use.  It should solve the problem of having to manually check everything ourselves and having an up to date current feed.

Review the repo.

The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.

Our Core Values

Maximize P(Win)

“Maximize the Probability of Winning”: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). “Maximize P(Win)” frees us from constraints and clarifies that we must put Arena first.

Own the Outcome

We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

We need to focus on being able to generate a submission into the competition.

The site should be able to generate a TIF file that is required for submission.  It should be as easy as download to click a File to submit into the competition.  This needs to be in the executive summary or the very beginning of the site.  it should be obvious when you visit the site.

I tried to submit the document that i downloaded from the site but it returned this error on the submission form:

"Predicted values must be in range [0, 1]"

Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Here is the submission page when i click submit file

New submission

File to submitNo file chosen

You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF, with your predictions. It must match the submission format's CRS, shape, and geotransform. You may wish to review the competition rules first.

Note (optional)

A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Create a executive summary subpage that explains exactly how to make a submission into the contest.

Work on the next steps from the previous sessions first.

The goal of this project is to place top of the leaderboard in this competition.  The following is the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)

We need to create a project that can compete and place top of the leaderboard.  We need to understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification.

This is the guidelines we need to follow.[https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/)

Get familiar with the problem through the overview and problem description,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). You might also want to reference additional resources available on the about page,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/).

Download the data from the data,[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), tab.

Create and train your own model. This reference solution,[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) implements a simple approach.

Use your model to generate predictions that match the submission format.

Tell me what are you limitations and what you need access to during this project.  We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.

this pdf outlines how submissions must be entered into the competition.

[https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

You must be able to do your own research, deep research, scientific literature research and organize the knowledge so that we can critically think through the problem and generate a solution through scientific and free publicly available information.  this must be done autonomously and must be constantly reviewed and improved upon.  Provide suggestions and improvements and implement them.

❌ No DrivenData auth → cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (verified redirect to login)

See below for links from the above site.  See attached files for links from the above site.

[https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)

Download competition data from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (requires login) to data/

See links below for competition data:

[https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0)

[https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0)

[https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0)

[https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0)

[https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

Site creation

Create a github page for this repo that has clean ui, user friendly, simple and easy to use.  It should be organized and clean.

It should include all relevant information in an easy to read format with official verified links as sources for review.  Work line by line verify everything no hallucinations.

**The single remaining blocker to training is data placement**: run `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready to run (GPU needed for training; metric/losses/validation all verified working here on CPU).

you need to complete the above task by yourself.  Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

Run this task through multiple passes.

Pass 1: Implement the task completely and verify the result.

Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find.

Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.

Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request.  Work line by line verify everything no hallucinations.

Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.  It should be worked on in this next session or the next session.  Work line by line verify everything no hallucinations.

</details>
