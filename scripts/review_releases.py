#!/usr/bin/env python3
"""Revalidate frozen downloads, without training, placement, selection or upload.

This is a reporting layer over the unchanged shared validator, NOT a private
metric, novelty evaluator or selector. Recorded scientific results stay frozen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import rasterio

from validate_submission import check_tiff

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence/release_review_20261027.json"


def load(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def specifications():
    c = load("registry/run_card.json")
    t = load("evidence/tip1_run_card_20261026.json")
    m = load("evidence/run_card.json")
    h = load("evidence/wbg_h1/run_card.json")
    th = t["arms"]["B"]["holdout"]
    return [
        ("WBG-C1", "registry/run_card.json", c["artifact"], c["raster_sha256"], c["holdout"],
         c["registry"]["max_forward_3px_overlap"], "surface-before-placement; 360 frozen file hashes",
         "Negative paired efficacy; literal surface duplicate STOP; final dots not generated."),
        ("TIP1", "evidence/tip1_run_card_20261026.json", "docs/downloads/" + t["validator_output"]["file"], t["raster_sha256"],
         {"dti": th["dti"], "ci95": th["ci95"]["interval"], "evaluator_version": th["evaluator_version"],
          "withheld_positive_pixels": th["n_withheld_positive_pixels"]},
         max(r["candidate_dot_overlap_within_3px"] for r in t["literal_duplicate_rows"]), "final dots; recorded 179-raster audit",
         "Literal final-dot duplicate STOP; current-best paired replay unavailable."),
        ("MVGZ", "evidence/run_card.json", m["tif"], m["raster_sha256"],
         {"dti": m["holdout_dti"]["pooled_dti"], "ci95": m["holdout_dti"]["ci95"],
          "evaluator_version": m["holdout_dti"]["evaluator_version"],
          "withheld_positive_pixels": m["holdout_dti"]["n_withheld_positives"]},
         m["correlation_overlap_vs_registry"]["max_overlap_literal"], "only 37 registry entries; not the complete 360-file scope",
         "Negative recorded efficacy; limited registry scope is not global uniqueness clearance."),
        ("WBG-H1", "evidence/wbg_h1/run_card.json", h["raster_sha256"]["tif_file"], h["raster_sha256"]["tif_sha256"],
         {"dti": h["holdout_dti"]["dti"], "ci95": h["holdout_dti"]["ci95"],
          "evaluator_version": h["holdout_dti"]["evaluator_version"],
          "withheld_positive_pixels": h["holdout_dti"]["n_withheld_positives"]},
         h["registry_correlation_and_overlap"]["literal_oneway_vs_r13_space_filling_lattice_ir_wbg1_01"],
         "recorded lattice witness; filtered sparse/symmetric results do not override literal gate",
         "Literal overlap exceeds 70%; inherited negative verdict. No optional benchmark upload authorized."),
    ]


def review():
    rows = []
    for lane, card, artifact, expected, holdout, overlap, scope, reason in specifications():
        path = ROOT / artifact
        # A missing/corrupt artifact is a hard failure, not a retained green badge.
        try:
            report = check_tiff(path)
            identity = report["sha256"] == expected
            # Portable serialization only; do not change validator decisions/pixels.
            report["file"] = artifact
            if "template_report" in report:
                report["template_report"]["path"] = artifact
            error = None
        except (OSError, ValueError, RuntimeError, rasterio.errors.RasterioError) as exc:
            report, identity, error = {"all_checks_passed": False}, False, str(exc)
        passed = (identity and report["all_checks_passed"]
                  and report.get("mirrored_reference_available") is True
                  and report.get("catalogue_reference_available") is True)
        rows.append({
            "lane": lane, "artifact": artifact, "source_card": card,
            "source_card_sha256": digest(ROOT / card), "expected_raster_sha256": expected,
            "exact_identity_matches": identity, "validator": report, "error": error,
            "holdout": {"evidence_class": "HOLDOUT-DTI", **holdout,
                        "status": "recorded prior measurement; NOT rerun in this review"},
            "recorded_forward_3px_overlap": overlap, "registry_scope": scope,
            "literal_overlap_exceeds_limit": overlap > 0.70,
            "uniqueness_cleared": False, "leaderboard_estimate": None,
            "organizer_confirmed_score": None, "ok_to_download": bool(passed),
            "ok_to_submit": False, "verdict": "negative", "reason": reason,
        })
    return {
        "schema_version": 1, "review_date_utc": "2026-10-27",
        "scope": "Four local frozen research TIFFs; not a new scientific experiment or current external registry audit.",
        "shared_validator": "vendor/gems57/validate.py; unchanged pinned owner template",
        "all_exact_artifacts_format_valid": all(r["ok_to_download"] for r in rows),
        "any_ok_to_submit": False, "new_experiments": 0, "submission_slots_used": 0,
        "rows": rows,
        "reporting_corrections": [
            "Historical 0.2778 and other supplied artifact values lack submission-page receipts: USER-REPORTED, not ORGANIZER-CONFIRMED.",
            "Literal overlap has no authorized lattice/density exclusion. A sparse or symmetric PASS cannot replace it.",
            "Private fault count, private recall, exact portal implementation and score-gain causes are not established by these files.",
            "For binary dots DTI = T / [0.2*(T+N-M) + 0.8*K], where T sums coverage over truth and M over dots. T and M are distinct unknowns.",
            "A lattice-wide mean kernel value need not equal the unknown truth-conditioned mean. Score inversion and LLI forecasts are not validated evidence.",
            "Different evaluators/splits/representations are not a common ranking or a leaderboard forecast.",
        ],
        "next_actions": [
            "Do not restart WBG-C1, TIP1 or another stopped lane, move dots into registry holes, or relax thresholds.",
            "Obtain an assigned distinct method lane, authenticated layer metadata, and a clean paired same-instrument benchmark before new promotion research.",
            "Any future independently authorized lane must pass canaries, buffered holdout improvement, untouched confirmation, literal surface/final-dot gates and exact-file validation.",
            "A separate selector needs authenticated current weekly allowance; this repository has no uploader.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare with committed receipt instead of writing it")
    args = parser.parse_args()
    result = review()
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.check:
        published = ROOT / "docs/data/release-review.json"
        if (not OUTPUT.exists() or OUTPUT.read_text() != text
                or not published.exists() or published.read_text() != text):
            raise SystemExit("Release review differs; inspect exact artifact/evidence changes before rebuilding.")
    else:
        OUTPUT.write_text(text)
        (ROOT / "docs/data/release-review.json").write_text(text)
    print(json.dumps({"all_exact_artifacts_format_valid": result["all_exact_artifacts_format_valid"],
                      "any_ok_to_submit": False, "new_experiments": 0}))
    return 0 if result["all_exact_artifacts_format_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
