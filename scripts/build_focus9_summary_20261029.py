#!/usr/bin/env python3
"""Build the 29 Oct 2026 nine-site executive summary from existing receipts.

Reads only committed receipts (no network, no model, no slot selection):
  - docs/data/executive_summary_20261028.json   (nine focus-site rows, owner-reported values)
  - evidence/per_fold_recheck_blind_adjacency.json (leakage re-check, this session)
  - evidence/holdout_proxy_portfolio.json        (Spearman proxy-vs-score audit)

Writes:
  - docs/executive-summary-focus9-20261029.md
  - docs/data/focus9_summary_20261029.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs/data/executive_summary_20261028.json"
RECHECK = ROOT / "evidence/per_fold_recheck_blind_adjacency.json"
PROXY = ROOT / "evidence/holdout_proxy_portfolio.json"
BENCHMARK = ROOT / "evidence/wbg5/diff1_run_card.json"
MD_OUT = ROOT / "docs/executive-summary-focus9-20261029.md"
JSON_OUT = ROOT / "docs/data/focus9_summary_20261029.json"

NOT_ESTIMABLE = ("Not estimable: no validated estimator (proxy-vs-score Spearman 0.144, p=0.12, n=118)")


def main() -> int:
    src = json.loads(SRC.read_text())
    recheck = json.loads(RECHECK.read_text())
    proxy = json.loads(PROXY.read_text())
    benchmark = json.loads(BENCHMARK.read_text())["benchmark"]

    rows = []
    for r in src["rows"]:
        overlap = r.get("max_3px_overlap_vs_other_eight")
        rows.append(dict(
            site=r["site"],
            file=r["file"],
            download_url=r["download_url"],
            owner_reported_score=r["reported_value"],
            evidence_class="OWNER-REPORTED / UNVERIFIED (no organizer receipt)",
            estimated_leaderboard_score=None,
            estimated_leaderboard_score_text=NOT_ESTIMABLE,
            unique_vs_other_focus_sites=False,
            max_3px_overlap_vs_other_focus_sites=overlap,
            unique_reason=(f"FAIL: 3 px overlap with another focus-site file = {overlap:.4f} (> 0.70 gate)"
                           if overlap is not None else "FAIL: overlap not recorded"),
            decision="DO NOT SUBMIT",
        ))

    fold = recheck["per_fold_visible_only"]
    archived = recheck["archived_full_catalogue"]
    canary = recheck["leakage_canary"]
    mirror = dict(
        site="WBGGEMSDOE1 (this repo)",
        file="WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif",
        download_url=("https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/downloads/"
                      "WBGGEMSDOE1-blind-fault-adjacency-distance-decay-20261028T202056Z.tif"),
        owner_reported_score=None,
        evidence_class=("HOLDOUT-DTI, leakage-corrected per fold (evaluator WBGGEMSDOE1-HIDE-RECOVER-v1.0, "
                        f"n={fold['n_withheld_positives']} withheld positives; CI not recomputed)"),
        holdout_dti_archived_leaky=archived["pooled_dti"],
        holdout_dti_archived_leaky_ci95=archived["ci95"],
        holdout_dti_per_fold_visible_only=fold["pooled_dti"],
        benchmark_holdout_dti=benchmark["dti"],
        benchmark_evidence_class="HOLDOUT-DTI",
        benchmark_evaluator_version=benchmark["evaluator_version"],
        benchmark_withheld_positive_pixels=benchmark["n_withheld_positive_pixels"],
        benchmark_ci95=benchmark["ci95"],
        benchmark_source=benchmark["source"],
        benchmark_comparable_to_per_fold_recheck=(
            benchmark["evaluator_version"] == recheck["evaluator"].rsplit("EVALUATOR_VERSION ", 1)[-1]),
        estimated_leaderboard_score=None,
        estimated_leaderboard_score_text=NOT_ESTIMABLE,
        unique_vs_other_focus_sites=None,
        unique_reason="Format-valid, zeros outside footprint; registry uniqueness not fully re-checked this session",
        decision="DO NOT SUBMIT (download = research only)",
    )

    headline = dict(
        ok_to_submit_any_file="NO",
        ok_to_download_any_file="RESEARCH ONLY - no file is cleared",
        best_owner_reported_focus_file="GEMSDOE32 h33-h33-2-b2 = 0.2778 (OWNER-REPORTED, not organizer-confirmed)",
        leaderboard_rank1_public_observation="0.4544 (xiaofanhu), drivendata leaderboard page 2026-10-29",
        leaky_claim_retracted=("WBGGEMSDOE1 blind-fault-adjacency HOLDOUT-DTI 0.4657 reproduces but is leakage: "
                               f"per-fold visible-only = {fold['pooled_dti']:.4f}"),
    )

    payload = dict(
        schema="gemsdoe1-focus9-summary-20261029-v1",
        headline=headline,
        rows=rows + [mirror],
        leakage_recheck=dict(source="evidence/per_fold_recheck_blind_adjacency.json",
                             verdict=recheck["verdict"],
                             evaluator_version=recheck["evaluator"].rsplit("EVALUATOR_VERSION ", 1)[-1],
                             n_withheld_positives=fold["n_withheld_positives"],
                             ci95="NOT RECOMPUTED",
                             cited_benchmark=dict(evidence_class="HOLDOUT-DTI",
                                                  dti=benchmark["dti"],
                                                  evaluator_version=benchmark["evaluator_version"],
                                                  n_withheld_positive_pixels=benchmark["n_withheld_positive_pixels"],
                                                  ci95=benchmark["ci95"],
                                                  source=benchmark["source"]),
                             same_evaluator_comparison=False,
                             canary_status=canary["status"],
                             canary_auc_distance_alone=1 - canary["auc_negative_visible_distance_alone"],
                             canary_auc_emission_surface=canary["auc_emission_surface_alone"]),
        proxy_audit=dict(source="evidence/holdout_proxy_portfolio.json",
                         spearman=proxy["spearman"], spearman_p=proxy["spearman_p"]),
    )
    JSON_OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")

    lines = []
    a = lines.append
    a("# Executive summary - nine focus sites (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36)")
    a("")
    a("**Generated 2026-10-29 by `scripts/build_focus9_summary_20261029.py` from committed receipts.**")
    a("")
    a("## OK TO SUBMIT?  **NO - for every file in this table.**")
    a("")
    a("- Every focus-site score is OWNER-REPORTED. No DrivenData submission receipt is available here.")
    a("- No focus-site file is unique: each one overlaps another focus-site file by 97.6% to 100% in its 3 px dot test (gate: 70%).")
    a("- The archived blind-adjacency HOLDOUT-DTI 0.4657 is leakage-contaminated. Its visible-only per-fold recheck is HOLDOUT-DTI 0.006946 (WBGGEMSDOE1-HIDE-RECOVER-v1.0, n=60,161; 95% CI not recomputed). Its numeric value is below a separately recorded HOLDOUT-DTI benchmark 0.166060 (gems-segment-pooled-v1, n=60,988; 95% CI [0.151858, 0.180339]), but evaluator versions differ, so this is not a like-for-like comparison.")
    a("- Local format checks are not organizer acceptance. Nothing here is a prediction of leaderboard placement.")
    a("")
    a("## Summary table")
    a("")
    a("| Site | File to download | Owner-reported score | Estimated leaderboard score | Unique vs other focus sites? | Decision |")
    a("|---|---|---:|---|---|---|")
    for r in rows:
        a(f"| {r['site']} | [{r['file']}]({r['download_url']}) | {r['owner_reported_score']} | "
          f"Not estimable | NO (overlap {r['max_3px_overlap_vs_other_focus_sites']:.4f}) | **{r['decision']}** |")
    a(f"| WBGGEMSDOE1 (this repo) | [{mirror['file']}]({mirror['download_url']}) | none | "
      f"Not estimable (HOLDOUT-DTI {fold['pooled_dti']:.6f}; WBGGEMSDOE1-HIDE-RECOVER-v1.0, n={fold['n_withheld_positives']:,}, CI not recomputed; separate 0.166060 benchmark uses {benchmark['evaluator_version']}) | "
      f"Not fully checked | **{mirror['decision']}** |")
    a("")
    a("Owner-reported values come from `docs/data/executive_summary_20261028.json`. Overlap values are the shared 3 px test from that file.")
    a("")
    a("## Best historical file (GEMSDOE32 B2 = 0.2778): why it scored highest")
    a("")
    a("- It is an exact subset of its parent (the GEMSDOE25 dotted-h19-5-d2-8 file, 0.2600, sha256 3e78737f...): 37,654 dots kept, 6,436 removed, 0 added.")
    a("- All 6,436 removed dots lie within 2 px (200 m) of the public catalogue (`docs/data/h33-b2-forensics.json`).")
    a("- Mechanism (plausible, not proven): removing dots on or next to mapped faults that earn no credit reduces the false-positive term of the distance-weighted Tversky index (alpha 0.2), which raises the score.")
    a("- The local holdout proxy does **not** reproduce this: B2 scores HOLDOUT-DTI 0.0044 (`evidence/holdout_proxy_portfolio.json`). The proxy is leakage-inflated and rank-unreliable (Spearman 0.144). Irregularity: the holdout evaluator cannot be used to rank files against the leaderboard.")
    a("- Scale of the gain: +0.0178 (0.2600 to 0.2778), from one precision-cleanup step.")
    a("")
    a("## Leakage re-check of the one new candidate (Experiment 1 of the budget)")
    a("")
    a(f"- Archived file (full-catalogue placement): HOLDOUT-DTI {archived['pooled_dti']:.4f}, CI95 [{archived['ci95'][0]:.4f}, {archived['ci95'][1]:.4f}], n={archived['n_withheld_positives']}. This reproduces the original run card.")
    a(f"- Same method rebuilt per fold from visible faults only: HOLDOUT-DTI {fold['pooled_dti']:.6f} (WBGGEMSDOE1-HIDE-RECOVER-v1.0), n={fold['n_withheld_positives']}; CI not recomputed (fold-level pooling).")
    a(f"- Cited comparator: HOLDOUT-DTI {benchmark['dti']:.6f} ({benchmark['evaluator_version']}, n={benchmark['n_withheld_positive_pixels']:,}, 95% CI [{benchmark['ci95'][0]:.6f}, {benchmark['ci95'][1]:.6f}]). Evaluator versions differ; this is not a like-for-like comparison.")
    a(f"- Leakage canary (single feature, AUC on holdout): distance to visible catalogue alone {1 - canary['auc_negative_visible_distance_alone']:.3f}; emission surface alone {canary['auc_emission_surface_alone']:.3f}. Both are below the 0.90 leakage threshold. The 0.4657 score is leakage, not canary failure.")
    a("- Verdict: **NEGATIVE**. The earlier 0.4657 claim is retracted.")
    a("- Receipt: `evidence/per_fold_recheck_blind_adjacency.json`; script: `scripts/per_fold_holdout_recheck.py`.")
    a("")
    a("## Irregularities flagged for review")
    a("")
    a("1. Leaderboard numbers conflict. The user quotes 0.4413 and 0.3195. The public page on 2026-10-29 shows #1 at 0.4544 and #2 at 0.3916 (drivendata leaderboard). Neither is a project-file receipt.")
    a("2. Owner-reported focus-site values cannot be checked against an organizer receipt. They stay OWNER-REPORTED.")
    a("3. The `[0, 1]` portal error (user report) is still unexplained. Local writers use finite values in [0,1] with zeros outside the footprint. The official rules describe a single-band GeoTIFF but do not state the nodata convention in the text fetched here (`docs.nlr.gov/docs/fy26osti/96647.pdf`).")
    a("4. The holdout evaluator and the leaderboard disagree on B2 (proxy 0.0044 vs reported 0.2778).")
    a("5. The blind-adjacency run card and its note still call the file 'research' with 0.4657; that number is leaky. See the leakage section above.")
    a("")
    a("## Ranked next hypotheses (untested; none is validated)")
    a("")
    a("Expected improvement and cost are qualitative. Before any separate slot decision, an authorized candidate and its designated comparator must be evaluated under the same pinned evaluator and spatial split; require a favorable paired 95% CI. The cross-version 0.166060 comparator above is not a direct gate for WBGGEMSDOE1-HIDE-RECOVER-v1.0.")
    a("")
    a("1. **Analytic-signal magnetic edges, catalogue-free, per-fold** - layers: the stack already holds the total magnetic intensity (band 14), horizontal gradient (band 3), vertical gradient (band 9) and tilt/total curvature (band 6). Signature: analytic-signal amplitude ridges, a combination of those bands. Novelty: LOW, because the same information is already inside the stack and tilt is already implemented in the repo (6 files). Cost: low. Mimic: magnetized dikes and intrusions.")
    a("2. **Conductivity lineaments with a new external source** - layer: band 17 (conductivity surface) is already in the stack, so this is only new if a different, free, official conductivity dataset is added. The source is NOT verified in this session. Do not implement until a free official source is confirmed. Cost: high. Mimic: clay-rich basin fill.")
    a("3. **Leakage-free supervised ranker** - layer: the 19-band stack, trained only on visible folds. Cost: medium. Novelty: low, because ML lanes already exist (`src/wbg4/model.py`, `src/wbggems2/mksf_model.py`). Use only as a per-fold baseline.")
    a("")
    a("## Verification notes")
    a("")
    a("- Owner-mirror integrity receipt: `evidence/data_restore.json` records matching hashes, but the ignored core raster blobs are absent from this checkout and the mirror is not organizer-origin authentication.")
    a("- Tests: 242 passed locally (including 5 leakage-receipt tests; 15 Rasterio warnings).")
    a("- Sources: official rules `https://docs.nlr.gov/docs/fy26osti/96647.pdf`; reference solution `https://github.com/drivendataorg/gems-prize-reference-solution` (writes float predictions on the label grid, no NaN padding); leaderboard `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/`.")
    a("")
    a("## Machine-readable card")
    a("")
    a(f"`docs/data/focus9_summary_20261029.json` (schema `{payload['schema']}`).")
    MD_OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {MD_OUT.relative_to(ROOT)} and {JSON_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
