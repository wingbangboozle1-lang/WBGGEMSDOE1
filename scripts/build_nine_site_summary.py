#!/usr/bin/env python3
"""Build the evidence-labeled nine-site executive summary and current TIP1 decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIP_CARD = ROOT / "evidence/tip1_run_card_20261026.json"
H33 = ROOT / "evidence/h33_b2_forensics.json"
OUTPUT = ROOT / "evidence/nine_site_executive_summary_20261026.json"
DOCS_OUTPUT = ROOT / "docs/data/nine_site_executive_summary.json"

READ_ME_REFS = {
    "GEMSDOE24": "7790c3b3038e3fb34f2fe844e10d187a02fa3ab4",
    "GEMSDOE25": "af2b6f2543e5422a7e917638b70e038e6fd91cad",
    "GEMSDOE27": "bef7ae8e8f63b69d299c9214c75988c8f5055f9c",
    "GEMSDOE28": "2c839d10f57ec9b074829e93c84bc39935f52896",
    "GEMSDOE30": "9c0d637c0171407196b61b780444bc772ce75438",
    "GEMSDOE31": "eeb7da54ca4a8ae056f45e5b23eeef586ad79bf2",
    "GEMSDOE32": "07806249f4ed3efe70b4fbf866183c32392b7853",
    "GEMSDOE33": "08380a2e6f2a76d733ee6144d6de33e2907c13b8",
    "GEMSDOE36": "32c2660001d98f6fa9084a0971b3a9d5062d49b9",
}

# Historical maxima are preserved owner claims, not authenticated receipts. The
# exact filenames and pairwise audit values are from GEMSDOE36's pinned current
# README forensic table. They are never used as prediction inputs.
SITES = [
    ("GEMSDOE24", "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477, "68d0e2e4fcc5", 1.0000, "fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1"),
    ("GEMSDOE25", "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600, "91eae1ca42ec", 1.0000, "e40b9b5e3871cb34d138f586bde97f5099658d01"),
    ("GEMSDOE27", "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449, "33003374335d", 0.9802, "927322eadbde56be42ae129ccdfb9b37540d8e60"),
    ("GEMSDOE28", "gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710, "5556aa1438fd", 1.0000, "e6321461066f89080e3b1bb670d3951ab20d3638"),
    ("GEMSDOE30", "gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", 0.2600, "8cf893ead566", 1.0000, "760af3005dd40b9f36d8fef97d6dc384fd9f2a2f"),
    ("GEMSDOE31", "gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", 0.2708, "07b6db440535", 1.0000, "597b04cd1afb65d1ebbe3e9417fd952be48e3d74"),
    ("GEMSDOE32", "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", 0.2778, "c55bafc47005", 1.0000, "5fc7792c5887735ecd3aa9a612787da588a7bf2c"),
    ("GEMSDOE33", "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", 0.2632, "87f857d505e2", 0.9971, "f618cc54773bd9b4d6c2b3ebf78103a05cc10cb6"),
    ("GEMSDOE36", "gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", 0.2750, "e15891020b9c", 0.9758, "c5a8ae7da3bd2fcff5aa5855afd44c7a3346c16"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    tip = json.loads(TIP_CARD.read_text())
    h33 = json.loads(H33.read_text())
    rows = []
    for site, filename, score, sha12, overlap, artifact_ref in SITES:
        repo = f"buffedlizard55-lab/{site}"
        rows.append(
            {
                "site": site,
                "historical_best_file": filename,
                "artifact_url": f"https://github.com/{repo}/blob/{artifact_ref}/docs/downloads/{filename}",
                "sha256_prefix": sha12,
                "reported_value": score,
                "score_evidence_label": "OWNER-REPORTED / UNVERIFIED",
                "organizer_receipt_present": False,
                "maximum_3px_overlap_vs_other_eight_historical_masks": overlap,
                "unique_under_70_percent_rule": bool(overlap <= 0.70),
                "recommendation": "DO NOT SUBMIT",
                "reason": "Historical/already-used reference and fails the cross-site 70% uniqueness rule.",
                "current_readme_ref": READ_ME_REFS[site],
                "current_readme_url": f"https://github.com/{repo}/blob/{READ_ME_REFS[site]}/README.md",
            }
        )

    final_rows = tip["correlation_overlap_vs_registry"]["final_dots"]["rows"]
    lattice = next(row for row in final_rows if row["registry_id"] == "registry-001")
    competing = [row for row in final_rows if row["registry_id"] != "registry-001"]
    strongest_competing = max(
        competing, key=lambda row: row["candidate_dot_overlap_within_3px"]
    )
    report = {
        "schema": "gemsdoe1-nine-site-executive-v1",
        "generated_utc": tip["generated_utc"],
        "score_governance": (
            "No artifact-linked DrivenData receipt was found. All nine historical values, "
            "including H33-B2 0.2778 and conflicting leaderboard claims 0.3195/0.4413, "
            "remain OWNER-REPORTED / UNVERIFIED. Local numbers are labeled HOLDOUT-DTI."
        ),
        "historical_source": {
            "url": "https://github.com/buffedlizard55-lab/GEMSDOE36/blob/32c2660001d98f6fa9084a0971b3a9d5062d49b9/README.md",
            "scope": "Pinned historical file table and literal pairwise uniqueness audit",
        },
        "sites": rows,
        "h33_b2_explanation": h33,
        "new_scientifically_distinct_candidate": {
            "method": "TIP1 orientation-following fault-tip coherence gradient",
            "file": tip["submission_name"],
            "sha256": tip["raster_sha256"],
            "scientifically_distinct": True,
            "difference_from_h33_b2": (
                "TIP1 derives a directional LiDAR coherence derivative without catalogue "
                "tips or prior predictions; B2 is a deletion-only subset of D2.8."
            ),
            "holdout": tip["arms"]["B"]["holdout"],
            "surface_max_abs_registry_rank_correlation": tip[
                "correlation_overlap_vs_registry"
            ]["surface_before_placement"]["B"]["max_abs_rank_correlation"],
            "maximum_competing_method_3px_overlap": strongest_competing[
                "candidate_dot_overlap_within_3px"
            ],
            "maximum_competing_method_file": strongest_competing["file"],
            "retained_lattice_3px_overlap": lattice[
                "candidate_dot_overlap_within_3px"
            ],
            "strict_format_valid": tip["validator_output"]["format_valid"],
            "verdict": "negative",
            "recommendation": "DOWNLOAD FOR AUDIT: YES / SUBMIT: NO",
            "can_exceed_owner_reported_0_2778": (
                "UNPROVEN. TIP1 scored HOLDOUT-DTI 0.082434 on the named local evaluator, "
                "far below the 0.166060 local promotion benchmark; local holdout and the "
                "unverified organizer claim are not directly comparable. No score projection is made."
            ),
        },
        "leaderboard_claim_irregularity": {
            "claims_seen": [0.3195, 0.4413],
            "status": "UNVERIFIED-OWNER-REPORT",
            "receipt_present": False,
        },
        "recommendation": (
            "Do not resubmit any historical best and do not spend a slot on TIP1. "
            "TIP1 is format-valid and uniquely named, but misses the efficacy gate and "
            "fails the retained literal lattice overlap gate."
        ),
        "inputs": {
            str(TIP_CARD.relative_to(ROOT)): sha256(TIP_CARD),
            str(H33.relative_to(ROOT)): sha256(H33),
        },
    }
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    OUTPUT.write_text(text)
    DOCS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUTPUT.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
