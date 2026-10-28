# WBG-3 parallel lane — corrected research summary (2026-10-27)

> **DOWNLOAD: YES, for research only. SUBMIT: NO — DO NOT SUBMIT.** This is the archived **EXP3DET** lane. It is separate from the current SPI-PMR-WCS lane at [`docs/wbg3/`](wbg3/index.html). Neither artifact is approved for a submission slot.

## Executive decision

- **Leaderboard estimate: unavailable.** No validated forecast is published. The legacy EXP3DET JSON run card retains a two-anchor `MODEL-ESTIMATE` for historical provenance; its own caveats say the ratio is a ranking device, **not a forecast**. Do not use it as a score, forecast, or slot-selection input.
- **Superseded selector wording:** the frozen legacy run card also contains an earlier sentence calling this the designated file if a slot were spent. That sentence is not authorization or a current recommendation; this corrected summary supersedes it, while the raw card remains unchanged for audit.
- **No organizer-confirmed score:** no artifact-linked DrivenData receipt is present.
- **No submission slot was used by the archived run.** Current account allowance and selector authorization are not verified.
- **Do not conflate lanes:** the EXP3DET HOLDOUT-DTI and historical estimate do not belong to the current SPI-PMR-WCS card. The SPI-PMR-WCS card reports a null leaderboard estimate and a literal uniqueness STOP.

## Archived EXP3DET research TIFF

**Research download:** [`wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif`](downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif) · [one-TIFF ZIP](downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.zip)

- SHA-256: `30901f894a84f6150a65a86e6556d3b4d3b3f5054dd4f8f3b597d754115447c1`
- **Local format validation: PASS** for the one-band float32 GeoTIFF on the competition grid; finite values in `[0, 1]`, no NaN, and one-member ZIP byte identity are recorded in the run card. This is a local format result, **not** organizer acceptance or uniqueness clearance.
- **HOLDOUT-DTI:** `0.138233` (95% CI `[0.125701, 0.151956]`), evaluator `gems-segment-pooled-v1`, 60,988 withheld positives. The paired difference against EXP2 has a 95% CI that includes zero.
- The recorded **S3DEP1 HOLDOUT-DTI benchmark** is `0.166060` on the same named evaluator. Its fold masks are unpublished, so the required paired replay is unavailable; no paired superiority claim is made.
- Its recorded uniqueness audit covers only the nine focus-site champion rasters: maximum forward 3-pixel overlap `45.06%` and maximum absolute Spearman correlation `0.03595` within that limited set. **This is not a full-registry uniqueness pass.** The artifact is not globally cleared and remains **DO NOT SUBMIT**.
- Portal note from the archived run card (metadata only): `WBG-3 supervised multi-physics detector, dotted clear2 37654, zeros no NaN`.

A format-valid, downloadable TIFF is not a validated leaderboard prediction. Do not infer organizer acceptance from local validation, a research download, or an owner-reported historical value.

## Nine-site comparison

The values below are **OWNER-REPORTED / UNVERIFIED** historical claims. There are no artifact-linked organizer receipts in this evidence set. Positive-pixel counts and raster relations are local file measurements; they do not authenticate the reported scores.

| Site | Measured positive pixels | Supplied historical value | Raster lineage / comparison |
|---|---:|---:|---|
| GEMSDOE32 | 37,654 | **0.2778 — OWNER-REPORTED / UNVERIFIED** | B2; exact deletion-only subset of D2.8; removes 6,436 parent dots within 200 m, adds none |
| GEMSDOE36 | 38,854 | 0.2750 — OWNER-REPORTED / UNVERIFIED | Contains every B2 dot plus 1,200 additions; set relation does not prove the filename's claimed training method |
| GEMSDOE28 | 37,660 | 0.2710 — OWNER-REPORTED / UNVERIFIED | Rung30 member of the related ridge/dot family |
| GEMSDOE31 | 40,199 | 0.2708 — OWNER-REPORTED / UNVERIFIED | D2.8 minus 3,891 catalogue-near dots (within one 100 m pixel); B1 |
| GEMSDOE33 | 41,865 | 0.2632 — OWNER-REPORTED / UNVERIFIED | Analog-tip / stepover variant; heavily related to the inherited family |
| GEMSDOE25 | 44,090 | 0.2600 — OWNER-REPORTED / UNVERIFIED | D2.8 parent field |
| GEMSDOE30 | 44,090 | 0.2600 — OWNER-REPORTED / UNVERIFIED | Decoded positive set is pixel-identical to GEMSDOE25 |
| GEMSDOE24 | 60,069 | 0.2477 — OWNER-REPORTED / UNVERIFIED | Earlier D1.5 ridge-thinning field |
| GEMSDOE27 | 61,328 | 0.2449 — OWNER-REPORTED / UNVERIFIED | Topographic gap-closure variant; adds pixels to the D1.5 field |

The table is ordered by the supplied historical values, **not** by organizer-verified scores. Closely related pixel sets are not independent methods. See the [nine-site raster audit](data/nine-site-audit.json) for pinned-file identities and measured overlap scope.

## GEMSDOE32 B2: what can and cannot explain the reported 0.2778

The byte-verified ancestry is D2.8 (44,090 positive pixels) → B1 (40,199; 3,891 removed within one 100 m pixel of the public catalogue) → B2 (37,654; 2,545 more removed within two pixels). Overall, B2 removes exactly 6,436 parent dots, all within 200 m of the catalogue, and adds zero. This is a measured pixel relation, not proof about the hidden labels or the file submitted to the organizer.

The official metric is a distance-weighted Tversky index. Under its 300 m triangular kernel and `α = 0.2`, `β = 0.8`, removing predictions that receive little or no hidden-truth credit **could** reduce false-positive cost. But hidden faults may also occur near catalogue faults. The hidden `TP_w`, `FP_w`, and `FN_w` contributions and the exact evaluated upload are unavailable. Therefore the evidence **does not prove** that catalogue-near pruning caused the reported change from 0.2600 to 0.2778. The difference `0.0178` is only arithmetic on two owner-reported values—not an organizer-confirmed paired score delta.

No score ceiling near 0.28 is established. No fixed increase in `TP_w` required to reach another value is established. The nine owner-reported values do not support a leaderboard estimate.

## Ranked hypotheses and validation status

The current four-item WBG-3 hypothesis queue, named non-fault mimics, previous package-level HOLDOUT-DTI evidence, literal uniqueness STOP, and lane authorization limitation are documented in the [forensics and hypotheses page](wbg3/forensics-and-hypotheses.html). Those hypotheses are not verified geological detections. **No candidate was re-run or newly validated in this documentation review**: no assigned lane-method paragraph was found, and the relevant scientific lane is stopped.

## Official references and limits

- [Official competition page, metric and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — authenticated download required
- [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — public observations do not identify a project TIFF
- [Competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE/GDR INGENIOUS](https://gdr.openei.org/submissions/1391)
- [USGS Great Basin heat-flow data](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa)
- [NASA ASF OPERA data portal](https://asf.alaska.edu/datasets/daac/opera/)

These are source links for review, not claims that every page or raw dataset was freshly retrieved or independently validated in this continuation. Owner-mirror hashes establish byte integrity against the pinned mirror, **not organizer-origin authentication**. Hidden labels, exact submission receipts, and current weekly allowance remain unavailable.

**Maximize P(Win):** do not spend a slot on an unvalidated estimate.
**Own the Outcome:** preserve the negative decision and the unproven parts as such.
