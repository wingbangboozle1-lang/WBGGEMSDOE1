# WBGGEMSDOE1

**DrivenData competition 306 — DOE GEMS Prize (geologic faults / geothermal structure, GeoDAWN, Nevada).**

Read [`PROMPT.md`](PROMPT.md) at the start of every session. That is the operating brief.

---

## Is there a file to submit today?

# 🔴 DO NOT SUBMIT

| | |
|---|---|
| **OK to download (research/audit)** | YES |
| **OK to submit to DrivenData** | **NO** |
| File | [`docs/downloads/wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros.tif`](docs/downloads/wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros.tif) |
| Zip | [`docs/downloads/wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros.zip`](docs/downloads/wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros.zip) |
| Unique name | `WBGGEMSDOE1-H1-MVGZ-AC61AFDA` |
| Note (≤140) | `MVGZ unique 23402d B2 \| HR 0.0032 vs champ 0.0048 \| DO NOT SUBMIT` |
| SHA-256 | `0c2516fa5e5727eab1150750b72c189a454968aba4f9afbc5e2aac84dcc8faba` |
| Validator | 12/12 PASS · all 12,279,160 cells finite in [0, 1] · EPSG:32611 3730×3292 |
| Unique | YES (max \|ρ\|=0.017; max 3 px overlap 0.459 vs 37 rasters; 0.260 vs nine-site bests) |
| HOLDOUT-DTI | **0.00318** [0.00242, 0.00397] · WBGGEMSDOE1-HIDE-RECOVER-v1.0 · n=60,161 |
| Champion proxy HOLDOUT-DTI | **0.00476** [0.00428, 0.00526] on the same evaluator |
| Live estimate | **not claimed** (a projection is never a score) |
| Verdict | **negative** |

Site: [`docs/index.html`](docs/index.html) (enable GitHub Pages → `/docs`). Executive summary: [`docs/executive-summary.html`](docs/executive-summary.html). How to submit: [`docs/how-to-submit.html`](docs/how-to-submit.html).

---

## Why GEMSDOE32 `h33-h33-2-b2` scored 0.2778 (OWNER-REPORT)

Byte-verified this session: 37,654 dots, 0 on catalogue, SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`.

It is **not a new detector**. It is the H19-5 ridge network (19GEMSDOE, live 0.1922) Poisson-thinned to 2.8 px (44,090 dots, live 0.2600 on GEMSDOE25/30) then stripped of every dot within 2 px of the published USGS/INGENIOUS catalogue (B1 40,199 → 0.2708; B2 37,654 → 0.2778).

Official metric (page 967): distance-weighted Tversky index, α=0.2, β=0.8, 300 m triangular kernel. Known catalogue pixels are not scored. Near-catalogue dots are almost pure false positives on the test set, so deleting them raises DTI.

All nine focus-site “bests” (G24/25/27/28/30/31/32/33/36) are that one family: this session measured **97.6–100%** of each file’s dots within 3 px of another listed file.

**Can a unique file beat 0.2778?** Not with the two unique detectors tested here (TSML, MVGZ). The uniqueness rule forces ≥30% of dots off the H19-5 network; those strata have not paid for themselves on holdout. Current public leaderboard #1 is **0.4437** (xiaofanhu, 2026-10-26) — a different performance regime than the GEMSDOE family.

---

## Lane (IR-WB1-LANE: prompt method paragraph was missing)

**MVGZ / TSML — magnetic-contact discovery, not DEM Hessian ridges.**

- E1 leakage canary: only distance-to-full-catalogue AUC=1.00. All 19 official bands 0.45–0.57. PASS.
- E2 TSML: strain-gated magnetic HGM ridges. Unique. HOLDOUT-DTI 0.0022 < 0.0048.
- E3 MVGZ: TMI vertical-gradient zero-crossings × HGM. Unique. HOLDOUT-DTI 0.00318 < 0.0048. Shipped as the unique artifact. **negative**.

Run card: [`evidence/run_card.json`](evidence/run_card.json).

---

## Reproduce

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
bash scripts/download_competition_data.sh    # GitHub bridge; no DrivenData login
.venv/bin/python scripts/prepare_data.py     # SHA-256 pins
.venv/bin/python tests/test_metric.py
.venv/bin/python scripts/run_experiments.py
.venv/bin/python scripts/evaluate_holdout.py docs/downloads/wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros.tif
```

Official rasters (SHA-256 pinned in `src/gems1/grid.py`):

| File | sha256 |
|---|---|
| example_submission.tif | `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` |
| existing_faults.tif | `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` |
| gems-geodawn-numerical-features.tif | `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5` |

---

## Competition links (official)

- https://www.drivendata.org/competitions/306/competition-doe-gems/
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- https://www.drivendata.org/competitions/306/competition-doe-gems/data/ (login)
- https://github.com/drivendataorg/gems-prize-reference-solution
- https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- https://gbcge.org/current-projects/ingenious/
- https://gdr.openei.org/submissions/1391
- https://epsg.io/32611
- https://en.wikipedia.org/wiki/Tversky_index

---

## Limitations (next session)

- No DrivenData auth → no organizer receipts, no private test insight.
- Sandbox egress is GitHub/PyPI only → no 1 m 3DEP, no GDR shapefiles, no Dropbox.
- Hide-and-recover of *mapped* faults is a biased proxy for hidden test faults (champion live 0.2778 vs holdout 0.0048 here).
- Beating 0.2778 without duplicating H19-5 needs a detector with large off-network lift, or an owner decision to allow H19-5 family refinements (IR-47-UNIQ-CEILING on GEMSDOE32).
- GitHub Pages must be enabled on `/docs`.

Negative results are deliverables. Do not burn a weekly slot on this TIF.
