#!/usr/bin/env python3
"""Patch the nine-site executive summary with the WBG-5 result and this project's row."""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAD = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()

SUMMARY = ROOT / "docs/data/nine_site_executive_summary.json"
CARD = json.loads((ROOT / "evidence/wbg5/run_card.json").read_text())

NINE = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28",
        "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}

# overlap of our artifact against exactly the nine historical masks
top = CARD["registry_uniqueness"]["top"]
vs_nine = [r for r in top if Path(r["name"]).stem in NINE]
max_vs_nine = max((r["overlap_frac"] for r in vs_nine), default=None)
max_vs_nine_name = max(vs_nine, key=lambda r: r["overlap_frac"])["name"] if vs_nine else None

d = json.loads(SUMMARY.read_text())

d["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
d["score_governance"] = (
    "No artifact-linked DrivenData receipt was found. All nine historical values, including "
    "H33-B2 0.2778 and conflicting leaderboard claims 0.3195/0.4413, remain OWNER-REPORTED / "
    "UNVERIFIED. Local numbers are labeled HOLDOUT-DTI. WBG-5/MTA-1 is additionally a NULL "
    "result: its paired holdout CI includes zero, so it is DO NOT SUBMIT."
)

d["new_scientifically_distinct_candidate"] = {
    "method": "WBG-5 / MTA-1: scale-persistent magnetic-texture anisotropy of the "
              "reduced-to-pole field relative to local depth-to-base structural contours",
    "file": CARD["artifact"]["tif"],
    "sha256": CARD["artifact"]["tif_sha256"],
    "scientifically_distinct": True,
    "difference_from_h33_b2": "MTA-1 adds directional RTP-texture-energy channels at sigma 3/8 px "
                              "relative to band-15 contours to the official 19-band stack; "
                              "H33-B2 is a deletion-only subset of an earlier dotted field.",
    "holdout": {
        **CARD["holdout_dti"],
        "control_arm": "A1_ctrl_no_mta (19-band stack minus the MTA channels)",
        "paired_fold_wins": "2 of 4",
    },
    "canary": CARD["canary"],
    "verdict": CARD["verdict"],
    "uniqueness": {
        "competing_submission_gate": CARD["registry_uniqueness"]["passes_sparse_gate"],
        "maximum_3px_overlap_vs_nine_historical_masks": max_vs_nine,
        "maximum_overlap_vs_nine_historical": max_vs_nine_name,
        "literal_all_entry_gate": CARD["registry_uniqueness"]["literal_all_entry_pass"],
        "literal_gate_note": "Fails only against WBGGEMSDOE1's own continuous wbg-c1 research "
                             "surface, which overlaps every budget-matched dotted field by "
                             "construction and is therefore reported, never gating.",
    },
}

d["recommendation"] = (
    "Do not resubmit any historical best and do not spend a slot on WBG-5/MTA-1. WBG-5 is "
    "format-valid and passes the competing-submission uniqueness gate, but its paired holdout "
    "CI includes zero (MTA-1 adds no recoverable signal over the 19-band control)."
)

d["wbg5_mta1_null_result"] = {
    "schema": "gemsdoe1-wbg5-mta1-forensics-v1",
    "canary_passed": CARD["canary"]["all_features_passed"],
    "canary_max_sym_auc": CARD["canary"]["max_sym_auc"],
    "canary_note": "AUC > 0.90 in any fold is treated as leakage; none was found. The earlier "
                   "canary false-positive was a holdout-misalignment artifact (catalogue excluded "
                   "from the footprint) and is resolved.",
    "arms": {
        "A2_mta1_dti": CARD["holdout_dti"]["dti"],
        "A1_control_dti": CARD["holdout_dti"]["control_arm_A1_dti"],
    },
    "paired_delta": CARD["holdout_dti"]["paired_delta"],
    "paired_ci95": CARD["holdout_dti"]["paired_delta_ci95"],
    "conclusion": "MTA-1 is not supported by the segment-pooled holdout.",
}

# add this project as a tenth row in the per-site table
ours = {
    "site": "WBGGEMSDOE1",
    "historical_best_file": Path(CARD["artifact"]["tif"]).name,
    "artifact_url": f"https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/{HEAD}/{CARD['artifact']['tif']}",
    "sha256_prefix": CARD["artifact"]["tif_sha256"][:12],
    "reported_value": None,
    "reported_value_label": "HOLDOUT-DTI 0.1316 (no public score)",
    "score_evidence_label": "HOLDOUT-DTI / null",
    "organizer_receipt_present": False,
    "maximum_3px_overlap_vs_other_eight_historical_masks": max_vs_nine,
    "maximum_overlap_vs_nine_historical_mask": max_vs_nine_name,
    "unique_under_70_percent_rule": bool(max_vs_nine is not None and max_vs_nine <= 0.70),
    "recommendation": "DO NOT SUBMIT",
    "reason": "Scientifically distinct and competing-submission-unique, but the paired holdout "
              "CI includes zero: MTA-1 adds no signal over the 19-band control.",
    "evidence_card": "evidence/wbg5/run_card.json",
}
if not any(s["site"] == "WBGGEMSDOE1" for s in d["sites"]):
    d["sites"].append(ours)

d["inputs"]["evidence/wbg5/run_card.json"] = hashlib.sha256(
    (ROOT / "evidence/wbg5/run_card.json").read_bytes()).hexdigest()
d["inputs"]["scripts/build_wbg5_submission.py"] = hashlib.sha256(
    (ROOT / "scripts/build_wbg5_submission.py").read_bytes()).hexdigest()

SUMMARY.write_text(json.dumps(d, indent=2) + "\n")
print("patched", SUMMARY)
print("max overlap vs nine:", max_vs_nine, max_vs_nine_name)
print("verdict:", d["new_scientifically_distinct_candidate"]["verdict"])
