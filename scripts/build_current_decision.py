#!/usr/bin/env python3
"""Build the 2026-10-27 executive decision payload from frozen receipts.

No model is trained, no file is uploaded and no score is invented.  Historical
values remain USER-REPORTED / NOT ORGANIZER-CONFIRMED.  LLI numbers are labelled
projections with their leave-one-out MAE, never organizer scores.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/data/current_decision_20261027.json"


def load(rel):
    return json.loads((ROOT / rel).read_text())


def main():
    audit = load("evidence/nine_site_audit.json")
    focus = load("docs/wbg-h1-dpgf1/data/site_payload.json")["focus9_summary"]
    tasc_b = load("evidence/tasc_run_card_20261027.json")
    tasc_a = load("evidence/tasc_best_arm_run_card_20261027.json")
    wbg_h1 = load("evidence/wbg_h1/run_card.json")
    feed = load("docs/data/feed.json")

    focus_by_site = {r["site"]: r for r in focus}
    sites = []
    for row in audit["rows"]:
        site = row["site"]
        f = focus_by_site[site]
        u = f["uniqueness_vs_all_gemsdoe"]
        proj = f["lli_empirical_projection"]
        sites.append({
            "site": site,
            "lineage": next((h for h in load("docs/data/nine_site_executive_summary.json")["sites"]
                             if h["site"] == site), {}).get("historical_best_file", row["file"]),
            "historical_best_file": row["file"],
            "historical_best_url": row["immutable_file_url"],
            "historical_value": row["reported_historical_value"],
            "historical_value_label": "USER-REPORTED / NOT ORGANIZER-CONFIRMED",
            "latest_candidate_file": f["latest_download_file"],
            "latest_candidate_url": f["latest_download_url"],
            "latest_candidate_sha256": f["sha256"],
            "latest_holdout_dti": f["latest_holdout_dti_numeric"],
            "estimate_label": "LLI-PROJECTION (NOT a score)",
            "estimate_value": proj["projected_value"],
            "estimate_interval_pm_1mae": proj["approx_interval_pm_1mae"],
            "estimate_loo_mae": proj["loo_mae"],
            "estimate_calibration_label": "calibrated on 118 USER-REPORTED / NOT ORGANIZER-CONFIRMED historical values",
            "unique_vs_sparse_peers": bool(u["passed_sparse_dot_peers_le_100k"]),
            "max_sparse_peer_3px_overlap": u["max_3px_dot_overlap"],
            "max_abs_spearman": u["max_abs_spearman_rho"],
            "peer_technical_safe_claim": bool(f["safe_to_submit"]),
            "ok_to_download": True,
            "ok_to_submit": False,
            "recommendation": "Audit / research only. Already-submitted historical champion or failed frozen gates; do not spend a weekly slot.",
        })

    def card_row(card, extra, holdout=None):
        reg = card.get("correlation_overlap_vs_registry",
                       card.get("registry_correlation_and_overlap", {}))
        if holdout is None:
            holdout = card.get("holdout", card.get("holdout_dti"))
        if "dti" not in holdout and "B" in holdout:
            holdout = holdout["B"]
        raw_sha = card.get("raster_sha256")
        sha = raw_sha["tif_sha256"] if isinstance(raw_sha, dict) else raw_sha
        raw_artifact = card.get("artifact")
        if raw_artifact is None and isinstance(raw_sha, dict):
            raw_artifact = raw_sha["tif_file"]
        artifact = extra.pop("_artifact", raw_artifact)
        sha = extra.pop("_sha256", sha)
        return {
            **extra,
            "file": Path(artifact).name,
            "url": "downloads/" + Path(artifact).name,
            "sha256": sha,
            "holdout_dti": holdout["dti"],
            "holdout_ci95": holdout["ci95"],
            "estimate_value": (card.get("leaderboard_estimate") or card["lli_empirical_projection"])["projected_value"],
            "estimate_interval_pm_1mae": (card.get("leaderboard_estimate") or card["lli_empirical_projection"])["approx_interval_pm_1mae"],
            "literal_gate_passed": reg.get("final_dots_literal_unseparated_passed", False),
            "competing_method_gate_passed": reg.get("final_dots_competing_method_passed", reg.get("sparse_dot_submissions_le_100k_max_3px_overlap", 1.0) <= 0.70),
            "max_literal_overlap": reg.get("max_literal_dot_overlap_within_3px"),
            "max_competing_overlap": reg.get("max_competing_dot_overlap_within_3px", reg.get("sparse_dot_submissions_le_100k_max_3px_overlap")),
            "ok_to_download": True,
            "ok_to_submit": False,
            "verdict": card["verdict"],
        }

    new_files = [
        card_row(tasc_a, {
            "id": "TASC-A",
            "label": "NEW 2026-10-27 · best-scoring arm of the frozen TASC screen",
            "method": "Label-free 300 m geophysical edge/strain response",
            "why": "Highest HOLDOUT-DTI of the three newly generated arms; still below the 0.166060 current-best benchmark.",
        }),
        card_row(tasc_b, {
            "id": "TASC-B",
            "label": "NEW 2026-10-27 · preregistered primary TASC candidate",
            "method": "Visible-tip-aligned strain-transfer corridor",
            "why": "Primary hypothesis failed: hide-and-recover removes visible faults from the test quadrant, so tip corridors have almost no support there.",
        }),
        card_row(wbg_h1, {
            "id": "WBG-H1",
            "label": "INHERITED 2026-10-26 · strongest unique research TIFF in this repository",
            "method": "66-channel dip-projected basement coupling + two-regime 300 m CELF",
            "why": "Higher holdout DTI and LLI projection than either new TASC file, but still below the 0.166060 benchmark and negative under the frozen protocol.",
        }),
    ]

    payload = {
        "schema": "gemsdoe1-current-decision-2026-10-27-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "decision": {
            "status": "NEGATIVE",
            "download": "YES — for research/audit only",
            "submit": "NO — no file is cleared for a weekly DrivenData slot",
            "headline": "A new unique TIFF was generated, but no new file beat the frozen holdout benchmark or passed the literal registry gate.",
            "best_download": new_files[0]["file"],
            "best_download_url": new_files[0]["url"],
            "best_estimate": new_files[0]["estimate_value"],
            "best_estimate_label": "LLI-PROJECTION, NOT a leaderboard score",
            "highest_repository_unique_estimate": new_files[2]["estimate_value"],
            "highest_repository_unique_file": new_files[2]["file"],
            "slots_used": 0,
        },
        "target_context": {
            "prompt_claims": [0.4413, 0.3195],
            "observed_official_leaderboard": feed["leaderboard"]["public_dw_tversky"],
            "observed_utc": feed["leaderboard"].get("observed_date_utc"),
            "observed_source": feed["leaderboard"]["source"],
            "note": "The official leaderboard observation is not a score for any project file. Prompt values are stale/inconsistent.",
        },
        "new_files": new_files,
        "sites": sites,
        "why_02778": {
            "finding": "GEMSDOE32 B2 is an exact 37,654-dot subset of the GEMSDOE25/GEMSDOE30 D2.8 field: 6,436 dots at catalogue distance <= 200 m were removed, zero added. GEMSDOE36 is a 1,200-dot superset of B2.",
            "interpretation": "Distance-weighted Tversky gives each truth pixel the maximum nearby prediction credit. Redundant near-catalogue dots add false-positive mass with little new coverage, so sparse pruning can improve DTI. This is a metric/geometry explanation, not proof about hidden labels.",
            "can_we_beat_it": "Not in this session. No newly generated or inherited unique file cleared the frozen promotion gates; an organizer receipt for 0.2778 was never supplied.",
            "evidence": ["evidence/h33_b2_forensics.json", "evidence/nine_site_audit.json", "docs/research/why-02778.md"],
        },
        "hypotheses": {
            "document": "research/03_ranked_hypotheses_2026-10-27.md",
            "count": 5,
            "top": "TASC (executed, negative)",
            "next": "PCE1 potential-field phase congruency (label-free; viable with the local 19-band cache)",
            "not_viable_here": ["DIFF1 raw 3DEP 1 m/10 m DEM profiles", "MT3D USGS 3-D MT conductance slices"],
        },
        "official_sources": [
            {"name": "DrivenData problem / metric / submission format", "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"},
            {"name": "DrivenData public leaderboard", "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"},
            {"name": "GEMS Prize Official Rules (3/week, AI disclosure)", "url": "https://docs.nlr.gov/docs/fy26osti/96647.pdf"},
            {"name": "USGS GeoDAWN data release", "url": "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and"},
            {"name": "DOE GDR INGENIOUS submission 1391", "url": "https://gdr.openei.org/submissions/1391"},
            {"name": "USGS Siler (2023) structural discontinuities", "url": "https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa"},
            {"name": "USGS 3DEP 1/3 arc-second DEM collection", "url": "https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5"},
            {"name": "USGS Great Basin 3-D MT conductance maps", "url": "https://doi.org/10.5066/P9TWT2LU"},
            {"name": "USGS EROS Sentinel-2 decommission notice", "url": "https://www.usgs.gov/centers/eros/science/usgs-eros-archive-sentinel-2"},
            {"name": "DrivenData reference solution", "url": "https://github.com/drivendataorg/gems-prize-reference-solution"},
        ],
        "irregularities": [
            "No assigned single-method lane paragraph was supplied; the TASC lane is provisional research.",
            "The retained spacing-5 calibration lattice covers >=70% of the footprint within 3 px, making the literal final-dot overlap gate unsatisfiable for any substantial new dot set. The shared tool reports a competing-method diagnostic, but the frozen literal gate remains binding.",
            "All historical values are USER-REPORTED / NOT ORGANIZER-CONFIRMED; peer pages that label them ORGANIZER-CONFIRMED are corrected in this session's pages.",
            "No authenticated submission page or artifact-linked receipt was available; the rules PDF's three-per-week limit is not proof of current allowance.",
            "Some inherited official links were dead (USGS Sentinel-2 landsat-missions page and an obsolete ScienceBase MT item); they are replaced with verified official URLs.",
            "The prompt's leaderboard targets 0.4413 and 0.3195 conflict; the official page was observed at " + str(feed["leaderboard"]["public_dw_tversky"]) + " on 2026-10-27.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)} with {len(sites)} sites and {len(new_files)} new/inherited files")


if __name__ == "__main__":
    main()
