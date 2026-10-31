## 31 OCT 2026 STANDING BRIEF — READ FIRST EVERY SESSION (supersedes nothing below it; it re-ranks it)

**Read in this order at session start:** this section → [`AGENTS.md`](AGENTS.md) (binding instrument
defects and lane gates) → [`PROMPT.md`](PROMPT.md) (submission contract) →
[`docs/owner-brief-20261029.md`](docs/owner-brief-20261029.md) (the owner's seven requirements verbatim).

**Project page (keep this updated — it is the owner's feed):**
[Unique-lane results and the nine-site decision table](docs/index.html) ·
[executive summary / how to submit](docs/executive-summary-20261031.html)

---

### 1. The metric, reduced to one identity (verified line by line, 31 Oct)

For a dot field whose dots are mutually farther apart than `2R+1 = 7 px`, no two dots can claim the
same hidden truth cell, and with `FN_w = K - TP_w` and `FP_w = N - A` (where
`A = sum_x max_g k(d(x,g))` is each *dot's* own best credit, and `0 <= TP_w - A` because one dot may be
the best claimant of several truth cells) the organizer metric is

```
DTI = TP_w / (0.2 N + 0.8 K + 0.2 (TP_w - A))        ->  DTI ~= TP_w / (0.2 N + 0.8 K)
```

The correction term is small but real and its sign is known: the naive form flatters by
`0.2(TP_w - A) / denom`. Measured with the canonical `vendor/gems57/metric.py:dti_exact` on our shipped
field against the visible catalogue (`labels.tif`, a proxy truth): `TP_w = 820.5273`, `A = 561.5`,
`N = 42,771`, `K = 60,988` -> `DTI = 0.014296` exact vs `0.014309` naive, a 0.09% overstatement. Every
number below uses the naive form and inherits that < 1% error, which is smaller than the registry's own
noise floor (median 0.0175 between near-identical rasters).

Consequences, arithmetic on the naive form unless stated:

* score is **linear in claimed credit to within that 1% correction**; every extra dot costs a fixed
  0.2 of denominator, so a dot is worth adding iff its expected credit exceeds 0.2 - which is what the
  shared allocator's accept bar (`vendor/gems57/emit.py`) encodes;
* GEMSDOE32 `h33-h33-2-b2` (OWNER-REPORTED 0.2778, n = 37,654) implies `TP_w = 0.2778 × 17,447 =
  4,847`, i.e. a 12.9% weighted hit rate, **given** the only truth scale in this repo reproduced
  against a scored file (`K = 12,395`, `evidence/wbg6_null_calibration.json`);
* K and the hit rate are **not separately identified**: K = 8,441 reproduces the same 0.2778 from
  3,968 full-credit hits (10.5%). An earlier session note said "3,968 reproduces 0.278" — true only
  in that second case. Both are recorded so nobody re-derives it;
* the champion's own +0.0178 over its parent (`44,090 → 37,654` dots, 6,436 removed, none added, all
  within 2 px of the visible catalogue — exact ancestry in `evidence/h33_b2_forensics.json`) costs
  ≈24 units of credit and buys 0.0178 of score. The identity reproduces **both** scores from one K.

Manual-review links: rules page 967 (metric text), `vendor/gems57/metric.py` (canonical
implementation), `evidence/portfolio_descriptors.json` (all 118 measured descriptors),
`evidence/scored_raster_fetch.json` (118 sha256-verified rasters + owner-reported scores).

### 2. Why 0.2778 is the site best, and whether we can beat it

The registry answers this directly, at fixed dot count. Stratify the 118 owner-reported files by
`n ∈ [36k, 46k]`:

| group | n files | `roi_coverage_frac` (share of footprint within 2 km of a dot) |
|---|---|---|
| score ≥ 0.24 | 15 | 0.921 – 0.948 (median 0.929) |
| score < 0.10 | 28 | median **0.737** |

Same budget, same kernel-disjointness, same catalogue avoidance — the difference is **spread**. The
hidden truth is distributed over the whole off-catalogue region, so a field that concentrates on
consensus peaks can only claim a fraction of it. Hence: *the plateau is coverage-limited, not
habitat-limited*, and 0.2778 is what a maximally spread, kernel-disjoint, ≥2 px off-catalogue
lattice at the count where 0.2N and 0.8K balance looks like. Beating it needs **more credit at the
same count** — either genuinely better ranking skill (which this dataset cannot demonstrate: see §3)
or sub-2-pixel placement luck. Break-even for our 42,771-dot field is `TP_w > 5,131` (+6% credit,
≈290 extra hits) versus the champion's 4,847.

### 3. Hypotheses tested and **falsified** in this lane (negative results are deliverables)

| # | hypothesis | test | verdict |
|---|---|---|---|
| H1 | concealed-cover inter-field concordance locates hidden blind faults *better than the plateau habitat* | anchor the inverted truth on the foreign champion: solve the level that predicts its 0.2778 | **falsified** — no level reaches it (best 0.0729); the champion captures 4.6% of H1's weighted mass vs 5.9% of a uniform field, i.e. H1 ranks the truth *worse than uniform* (`evidence/wbg8/emit2.json`) |
| H2 | the free (ungrouped) inversion of all 118 scores generalizes | grouped leave-one-family-out CV over the 22 template families | **falsified for absolute scores** — LOFO MAE 0.1062 > score sd 0.0833, champion underpredicted 4× (`evidence/wbg8/fit.json`). Use the model only with the level *anchored* on a foreign raster, never as a leaderboard projection |
| H2b | a truth field built from the top rasters' 3-px coverage fields can rank designs | rank by that field, place dots | **structurally degenerate** — a coverage field is non-zero only inside 3 px of its own raster's dots, so 99.98% of placed dots landed on the champion's buffer (0.008% outside). Recorded as the general trap: *no prior assembled from published dot buffers can be scored against those same buffers* (`evidence/wbg8/emit3.json`) |
| H3b | concentrate the budget on the 2 km consensus peaks | 40,000 dots, max-packing, coverage | **falsified** — coverage 0.744, i.e. exactly the low-score band of §2, predicted 0.0705 by the anchored model (`evidence/wbg8/emit4.json`) |
| H3c | keep the plateau geometry, use the consensus only to pick the best pixel inside each lattice cell | built, gated, validated | **the shipped candidate**, §4 |

### 4. Shipped candidate and the gate (auto-validated; there is no human inspection step)

`docs/downloads/wbg8-h3-lattice-microplace-42771-20261031-nanoutside.tif` (primary — NaN outside the
footprint is the official text) with the all-finite zeros twin beside it; 42,771 dots, `nn_min = 7 px`
(0% below), `cluster_frac 0.0`, `n_components == n_dots`, coverage 1.000, 0% on the catalogue, 8.3%
within 3 px of it, median catalogue distance 22.5 px.

* format: shared `scripts/validate_submission.py` — all hard checks pass, both portal conventions;
* uniqueness vs the champion: 17.0% of our dots within 3 px of its dots (limit 70%), dot-set Jaccard
  0.0048, no byte or pixel identity → **not a copy**;
* the *literal* registry gate still fails (99.9% within 3 px of the 206,895-dot r13 lattice) for the
  documented reason in §5; reported, not hidden;
* score: **MODEL-ESTIMATE bracket 0.23 – 0.35** (equal-budget enrichment 1.00× → 1.64×; the 1.64× is
  a mass-overlap ratio, *not* a validated precision multiplier). No organizer-confirmed number exists.

**DOWNLOAD: YES (research + submission-ready). SUBMIT: PROBE ONLY.** The gate says the file is valid,
in range, and unique; it does **not** say it beats 0.2778, and nothing in this repo can currently say
that. Promotion remains a separate selector decision under the weekly cap; no slot has been used.

### 5. Instrument defects found (fixed once, in shared code, reported — do not re-fix)

1. `scripts/wbg8_finalize.py` / `scripts/wbg8_estimate.py` computed `cluster_frac` and
   `n_components` from a **dilated** mask, so every isolated dot became a 29-pixel blob and a perfect
   lattice reported `cluster_frac 1.0` (would have failed a gate it actually passes). Now uses the
   canonical definition from `scripts/fit_scored_portfolio.py` (`near > 3` in a 7×7 window;
   8-connected components of the undilated dots).
2. **IR-WBG8-02:** `gems57.uniqueness.surface_rho` applied to two 0/1 dot surfaces is a monotone
   function of their overlap, so on binary submissions it measures the same thing as the 3-px rule and
   cannot identify copying. It is valid only for continuous probability surfaces. Do not treat a
   Spearman "failure" on a dot field as evidence of copying; use Jaccard + byte/pixel identity for
   that, and keep reporting the literal number.
3. `cKDTree.query(...)` returns `(distances, indices)`; `[1]` is the **index** array. Three receipts in
   `evidence/wbg8/` published neighbour indices as `nn_min_px`/`nn_median_px` (they read 0.0 / 6451).
   No conclusion changed — the blob verdict rested on connected components and area coverage — but any
   future nn statistic must take `[0]`.
4. The shared hide-and-recover holdout remains a **diagnostic only** (Spearman 0.144, p = 0.12,
   n = 118 vs real submissions) and rewards catalogue overlap, which every plateau file avoids by
   design; `beats_holdout_instrument_best_of_118` must never gate a submission on its own.

### 6. Next session, in priority order

1. Ask the owner for one **organizer submission receipt** (page screenshot / `submission_id`) for any
   of the nine focus sites. One receipt converts an OWNER-REPORTED number into ORGANIZER-CONFIRMED and
   is worth more than any further modelling: it is the only way to test §1's K identification.
2. Only remaining lever with a plausible +6% credit: **external free data** (named and obtainability
   checked in `docs/research-hypotheses-20261031.md`): USGS GeoDAWN aeromag/radiometric grids, OpenEI
   GDR submission 1391, GBCGE INGENIOUS. Use it to rank *within* lattice cells, not to redefine the
   habitat — §2 says the habitat is not the binding constraint at plateau counts.
3. **Stale receipt, re-run before quoting it:** `evidence/wbg8/fit.json` was produced *before* two
   corrections landed in `scripts/wbg8_lane.py` (measured dcat-band representatives replacing the
   band-index proxies, and the leave-one-family-out `argmin` bug). The code is fixed; the receipt is
   not. Re-run `.venv/bin/python scripts/wbg8_lane.py fit` **after** any finalize step (they share
   `.cache/wbg8`) and re-derive the H2 verdict — if the grouped LOFO MAE comes back below the score sd
   0.0833, the "absolute scores are not predictable" conclusion must be revisited, and `combos.npz`
   plus the `sensitivity_in_K` block will finally exist.
4. If the owner wants a second probe in the band, the cheap variation is `STEP_PX`/`MICRO_PX` in
   `scripts/wbg8_emit5.py` (n ∈ [37.6k, 44.1k]) — a count-only ablation of the plateau, not a new
   hypothesis. Do not re-run `emit`, `emit2` or `emit3`; their verdicts are final.
5. Portal-side open item: the reported "Predicted values must be in range [0, 1]" error is still
   unreproduced. Both twins pass all hard checks locally, so if the portal rejects one, submit the
   other; keep the receipts beside the files.

### 7. Housekeeping that bit us (repeat after me)

* every band of `training_features.tif` uses the sentinel `-3.4028e38`: load **only** through
  `src/wbg8/habitat.py:load_band`, or the statistic is silently poisoned;
* `data/` is gitignored: a fresh sandbox must re-run the assembly step and
  `scripts/fetch_scored_rasters.py` before any lane stage will work;
* `np.roll` wraps at array edges — use the clipped-slice shift in `scripts/wbg8_emit2.py:shift_max`;
* `scripts/wbg8_finalize.py` reads `.cache/wbg8/emit_surface.npy`; `wbg8_emit5.py` writes it — run the
  emitter last, always.
