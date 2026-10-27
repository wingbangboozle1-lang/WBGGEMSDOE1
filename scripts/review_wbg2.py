#!/usr/bin/env python3
"""Recheck the stopped WBG-2 raster using the shared validator and literal gate.

This is a forensic recheck of existing bytes, NOT an experiment, model run,
placement, selector, upload or authorization. The GEMSDOE24 lattice is an
immutable, hash-pinned audit witness; only the cache copy is downloaded.

    python scripts/review_wbg2.py --write   # refresh the recorded audit
    python scripts/review_wbg2.py --check   # remeasure, fail on any drift

The GitHub API is used solely when the ignored witness cache is absent. No
credentials are requested; an existing GITHUB_TOKEN may increase rate limits.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]
import numpy as np
import rasterio
from scipy import ndimage
from gems57 import uniqueness
from validate_submission import check_tiff

TIF = ROOT / "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif"
ZIP = TIF.with_suffix(".zip")
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
LATTICE = ROOT / ".cache/wbg2_review/focus24-lattice.tif"
C1 = ROOT / "docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif"
CARD = ROOT / "evidence/wbg2/run_card.json"
MIRROR = ROOT / "docs/data/wbg2-review.json"
TIF_SHA = "f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3"
LATTICE_SHA = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
C1_SHA = "8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875"
LATTICE_BLOB = "81c802618e6d46c6d62289d856ae74439439bbc6"
LATTICE_SOURCE = ("https://github.com/buffedlizard55-lab/GEMSDOE24/blob/"
                  "7ab1c8f77f0b4b8644e3929403a0dab65838b008/inputs/calibration/"
                  "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif")
NOTE = "WBG-2 density-prior research; literal registry overlap failed. DO NOT SUBMIT."


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def restore_witness() -> None:
    if LATTICE.is_file() and sha(LATTICE) == LATTICE_SHA:
        return
    url = f"https://api.github.com/repos/buffedlizard55-lab/GEMSDOE24/git/blobs/{LATTICE_BLOB}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "WBGGEMSDOE1-audit"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
        payload = json.load(response)
    if payload.get("sha") != LATTICE_BLOB or payload.get("encoding") != "base64":
        raise ValueError("unexpected GitHub lattice blob response")
    data = base64.b64decode(payload["content"], validate=False)
    if len(data) != 1_706_456 or hashlib.sha256(data).hexdigest() != LATTICE_SHA:
        raise ValueError("lattice witness failed pinned length or SHA-256 check")
    LATTICE.parent.mkdir(parents=True, exist_ok=True)
    temporary = LATTICE.with_suffix(".partial")
    temporary.write_bytes(data)
    temporary.replace(LATTICE)


def audit() -> dict:
    restore_witness()
    if sha(TIF) != TIF_SHA:
        raise ValueError("WBG-2 TIFF does not match its pinned SHA-256")
    report = check_tiff(TIF)  # shared validator; reference pins checked internally
    if not report.get("mirrored_reference_available") or not report.get("catalogue_reference_available"):
        raise ValueError("pinned reference or catalogue missing")
    with rasterio.open(TEMPLATE) as src:
        footprint = np.isfinite(src.read(1))
        grid = (src.shape, src.crs, src.transform)
    with rasterio.open(LABELS) as src:
        if (src.shape, src.crs, src.transform) != grid:
            raise ValueError("catalogue grid differs from template")
        catalogue = src.read(1) > 0
    with rasterio.open(TIF) as src:
        if (src.shape, src.crs, src.transform) != grid:
            raise ValueError("candidate grid differs from template")
        dots = src.read(1) > 0
    with zipfile.ZipFile(ZIP) as archive:
        names = archive.namelist()
        zip_ok = names == [TIF.name] and archive.read(names[0]) == TIF.read_bytes()
    records = [
        {"file": str(LATTICE), "sha256": LATTICE_SHA, "repo": "GEMSDOE24",
         "submission": "GEMSDOE24 registered spacing-5 lattice"},
        {"file": str(C1), "sha256": C1_SHA, "repo": "WBGGEMSDOE1",
         "submission": "WBG-C1 registered continuous research surface"},
    ]
    # List input intentionally does not certify a complete registry. Even one
    # failing witness is enough to STOP; it cannot establish global uniqueness.
    results = uniqueness.compare_to_registry(TIF, records, footprint,
                                              expected_grid=grid, include_reverse=False)
    rows = []
    for row in results["rows"]:
        if "error" in row:
            raise ValueError(f"registry witness error: {row['error']}")
        rows.append({"submission": row["submission"], "repo": row["repo"],
                     "sha256": row["sha256"], "their_positive_pixels": row["their_dots"],
                     "forward_overlap_within_3px": row["my_dots_within_3px_of_theirs"],
                     "spearman_full_footprint": row["spearman_full_footprint"],
                     "identical_bytes": row["identical_bytes"],
                     "identical_decoded_predictions": row["identical_decoded_predictions"],
                     "duplicate_by_overlap": row["duplicate_by_overlap"],
                     "duplicate_by_rho": row["duplicate_by_rho"]})
    dist = ndimage.distance_transform_edt(~catalogue)[dots]
    checks = report["checks"]
    return {
        "schema": "wbg2-corrected-forensic-review-v2",
        "reviewed_utc_date": "2026-10-27",
        "hypothesis": "WBG-2: off-catalogue mapped-fault density prior",
        "mechanism": "A Gaussian mapped-fault density prior drives scattered binary dots, with a four-step Manhattan catalogue exclusion. The rendered TIFF was generated in a previous session.",
        "named_non_fault_mimic": "Range-front alluvial fans and basin margins can follow mapped-fault density without being faults.",
        "lane": "No single-method paragraph was supplied; this stopped lane is not restarted.",
        "holdout": {"evidence_class": "HOLDOUT-DTI", "value": None, "ci95": None,
                    "evaluator_version": None, "withheld_positive_pixels": None,
                    "status": "No valid visible-only, buffered same-instrument result found for this artifact. Full-catalogue proxy DTI is not a holdout."},
        "leakage_canary": {"all_features_tested_alone": False,
                           "status": "Not established for the WBG-2 density prior on the required holdout."},
        "registry": {"evidence_class": "REGISTRY-MEASUREMENT", "phase": "final dots, forensic recheck",
                     "surface_before_placement": "No qualifying pre-placement registry audit was found.",
                     "witnesses_checked": len(rows), "scope": "Two SHA-verified witnesses; a failure is decisive, not a complete registry scan.",
                     "rho_limit_signed": uniqueness.RHO_LIMIT, "forward_overlap_limit": uniqueness.OVERLAP_LIMIT,
                     "rows": rows, "lattice_immutable_source": LATTICE_SOURCE,
                     "passes_literal_uniqueness": False,
                     "decision": "DUPLICATE - STOP under the stated literal >70% forward-overlap rule; no density or chance exemption."},
        "catalogue_exclusion_check": {"evidence_class": "RASTER-MEASUREMENT", "distance": "Euclidean pixels to nearest mapped-fault cell",
                                      "minimum_px": float(dist.min()), "candidate_pixels_below_4px": int((dist < 4).sum()),
                                      "note": "Four iterations of a four-connected dilation exclude a Manhattan diamond, not the full 400 m Euclidean disk."},
        "raster_sha256": TIF_SHA,
        "artifact": str(TIF.relative_to(ROOT)),
        "validator_output": {"evidence_class": "LOCAL-FORMAT-VALIDATION", "all_checks_passed": report["all_checks_passed"],
                             "checks": checks, "meta": report["meta"], "n_nan": report["n_nan"],
                             "n_infinite": report["n_infinite"], "min": report["min"], "max": report["max"],
                             "positive_pixels": report["emitted_positive_pixels"], "reference_origin_authenticated": False,
                             "zip_exact_single_identical_tiff": zip_ok, "zip_sha256": sha(ZIP),
                             "limitation": "A local pass is not organizer acceptance. The official text requests null/NaN beyond bounds; this all-finite exterior is a conservative local response to a reported range rejection."},
        "submission_name": TIF.stem, "submission_note": NOTE,
        "leaderboard_estimate": None, "organizer_confirmed_score": None,
        "estimate_reason": "No credible estimate. The retired in-sample regression used unconfirmed values, duplicate entries, correlated predictors and extrapolation; its residual interval is not a 95% prediction interval.",
        "artifact_role": "Existing research artifact only; not an approved submission.",
        "verdict": "negative", "ok_to_download": bool(report["all_checks_passed"] and zip_ok),
        "ok_to_submit": False, "new_experiments": 0, "new_rasters_generated": 0, "submission_slots_used": 0,
        "supersedes": "research/history/wbg2_20261027/run_card_SUPERSEDED.json",
    }


def compare_documents(stored, measured, path="card"):
    """Fail on any drift; tolerate only platform-scale float reduction noise."""
    if isinstance(measured, dict):
        if not isinstance(stored, dict) or stored.keys() != measured.keys():
            raise ValueError(f"audit structure drift at {path}")
        for key, value in measured.items():
            compare_documents(stored[key], value, f"{path}.{key}")
    elif isinstance(measured, list):
        if not isinstance(stored, list) or len(stored) != len(measured):
            raise ValueError(f"audit list drift at {path}")
        for index, (left, right) in enumerate(zip(stored, measured, strict=True)):
            compare_documents(left, right, f"{path}[{index}]")
    elif isinstance(measured, float):
        if isinstance(stored, bool) or not isinstance(stored, (int, float)) or not np.isclose(stored, measured, rtol=1e-8, atol=1e-10):
            raise ValueError(f"audit floating-point drift at {path}")
    elif type(stored) is not type(measured) or stored != measured:
        raise ValueError(f"audit value drift at {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = audit()
    if not result["validator_output"]["all_checks_passed"] or not result["validator_output"]["zip_exact_single_identical_tiff"]:
        raise ValueError("exact TIFF/ZIP local format or identity check failed")
    if not all(r["duplicate_by_overlap"] for r in result["registry"]["rows"]):
        raise ValueError("recorded duplicate witnesses did not reproduce")
    if len(NOTE) > 140:
        raise ValueError("note exceeds 140 characters")
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.write:
        CARD.write_text(text)
        MIRROR.write_text(text)
    else:
        # Full evidence and public mirror must agree; do not check just a few
        # approval fields while allowing stale or contradictory details through.
        stored = json.loads(CARD.read_text())
        if MIRROR.read_bytes() != CARD.read_bytes():
            raise ValueError("published WBG-2 review differs from canonical card")
        compare_documents(stored, result)
    print(json.dumps({"format_valid": result["validator_output"]["all_checks_passed"],
                      "lattice_overlap": result["registry"]["rows"][0]["forward_overlap_within_3px"],
                      "literal_gate_pass": False, "holdout_available": False,
                      "ok_to_submit": False, "verdict": "negative"}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, rasterio.errors.RasterioError) as error:
        print(f"WBG-2 audit failed closed: {error}", file=sys.stderr)
        raise SystemExit(1)
