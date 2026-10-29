#!/usr/bin/env python3
"""Emit one full-catalogue candidate from a holdout-tested arm, then run every local gate.

This script never uploads anything and never marks a file as submit-cleared on its own.
A file gets ``ok_to_submit = true`` only if every gate in ``docs/owner-brief-20261029.md`` §4
passes; the leakage canary decides that gate from the detached-mode holdout receipt.

Outputs (docs/downloads/ and evidence/candidates/)
---------------------------------------------------
  <name>.tif                      float32, EPSG:32611, 3730 x 3292, 100 m, values {0,1} (zeros elsewhere)
  <name>.zip                      one-member archive of the TIFF
  <name>.validator.json           shared gems57.validate receipt
  <name>.uniqueness.json          shared gems57.uniqueness literal + rank comparison vs 118 registry rasters
  <name>.run_card.json            the one JSON run card required by PROMPT.md §5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57.emit import greedy_allocate  # noqa: E402
from gems57.grid import load_grid, write_submission  # noqa: E402
from gems57.uniqueness import compare_array_to_registry  # noqa: E402
from gems57.validate import validate as validate_shared  # noqa: E402
from unique_candidate_lane import ARMS, K_STAR_FINAL, scale_to_budget  # noqa: E402

REG = ROOT / "registry/wbg_h1/scored_registry.json"
FETCH = ROOT / "evidence/scored_raster_fetch.json"
HOLDOUT_ALL = ROOT / "evidence/unique_candidate_lane.json"
HOLDOUT_DET = ROOT / "evidence/unique_candidate_lane_detached.json"
DOWNLOADS = ROOT / "docs/downloads"
CARDS = ROOT / "evidence/candidates"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def registry_inventory() -> dict:
    """Full inventory of the 118 owner-reported rasters fetched and SHA-verified by fetch_scored_rasters.py."""
    n_reg = len(json.loads(REG.read_text())["entries"])
    fetch = json.loads(FETCH.read_text())["entries"]
    ok = [e for e in fetch if e.get("status") in ("downloaded", "cached")]
    rasters = [dict(repo_first=e["repo"], sources=[e["name"]], cache_file=str(ROOT / e["local"]),
                    sha256=e["registry_sha256"], owner_reported_score=e["score"]) for e in ok]
    return dict(rasters=rasters, complete_accessible_scan=(len(ok) == n_reg), errors=[])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--param", required=True, type=float, help="arm parameter in metres")
    ap.add_argument("--name", required=True)
    ap.add_argument("--note", required=True)
    args = ap.parse_args()
    if len(args.note) > 140:
        raise SystemExit(f"note is {len(args.note)} characters; limit is 140")

    grid = load_grid()
    fp, cat = grid.footprint, grid.catalogue
    field_fn, _ = ARMS[args.arm]
    allowed = fp & ~cat                              # never place a dot on the public catalogue
    p = field_fn(cat, fp, args.param) * fp
    p = scale_to_budget(p, allowed, K_STAR_FINAL)
    alloc = greedy_allocate(p, allowed, K_STAR_FINAL)
    dots = alloc.emitted & allowed
    values = np.where(dots, 1.0, 0.0).astype(np.float32)

    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    CARDS.mkdir(parents=True, exist_ok=True)
    tif = DOWNLOADS / f"{args.name}.tif"
    write_submission(tif, values, mode="zeros")
    zpath = DOWNLOADS / f"{args.name}.zip"
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(tif, arcname=tif.name)

    receipt = validate_shared(tif, footprint=fp, catalogue=cat)
    (CARDS / f"{args.name}.validator.json").write_text(json.dumps(receipt, indent=1, allow_nan=False, default=str) + "\n")
    format_ok = bool(receipt["all_checks_passed"])

    with rasterio.open(tif) as ds:
        mine = ds.read(1)
    uniq = compare_array_to_registry(mine, registry_inventory(), fp, file_sha256=sha256_file(tif))
    (CARDS / f"{args.name}.uniqueness.json").write_text(json.dumps(uniq, indent=1, allow_nan=False, default=str) + "\n")

    holdout_all = json.loads(HOLDOUT_ALL.read_text())["arms"]
    holdout_det = json.loads(HOLDOUT_DET.read_text())["arms"] if HOLDOUT_DET.exists() else {}
    key = f"{args.arm}@{int(args.param)}m"
    det = holdout_det.get(key, {})
    canary_det = det.get("canary_auc_max")
    canary_pass = canary_det is not None and canary_det <= 0.90

    card = dict(
        schema="unique-candidate-run-card-v1",
        name=args.name,
        note=args.note,
        note_chars=len(args.note),
        hypothesis=("Hidden new faults lie within a short, fixed kernel of visible catalogue traces; "
                    "placing dots where the expected kernel credit is highest maximises the shared DTI."
                    if args.arm == "A_decay" else
                    "Hidden new faults are continuations of visible catalogue fault tips; decay from visible endpoints only."),
        mechanism=("Greedy exact-marginal emission (gems57.emit.greedy_allocate) on a probability field scaled to "
                   f"K*={K_STAR_FINAL} hidden truth cells; field = {args.arm} at {int(args.param)} m from the full public catalogue."),
        named_non_fault_mimic=("Lithologic contacts and dike margins parallel to mapped faults; alluvial fan edges "
                               "adjacent to mapped scarps; survey-line artefacts along catalogue traces."),
        holdout=dict(
            evidence_class="HOLDOUT-DTI", evaluator_version=det.get("evaluator_version", "gems57-pooled-hide-v2"),
            withholding_mode="detached", draw_reported=21,
            dti=det.get("draw21", {}).get("dti"), ci95=det.get("draw21", {}).get("ci95"),
            withheld_positive_pixels=det.get("draw21", {}).get("withheld_positive_pixels"),
            null_matched_budget_dti=det.get("draw21_null", {}).get("dti"),
            paired_delta_vs_null=det.get("draw21_paired_vs_null"),
            all_mode_reference=holdout_all.get(key, {}).get("draw21", {}),
        ),
        leakage_canary=dict(threshold=0.90, detached_max_auc=canary_det, pass_=canary_pass,
                            all_mode_max_auc=holdout_all.get(key, {}).get("canary_auc_max")),
        registry_comparison=dict(
            expected=uniq["registry_rasters_expected"], checked=uniq["registry_rasters_checked"],
            complete_accessible_scan=uniq["complete_accessible_scan"], duplicate_count=uniq["duplicate_count"],
            worst_spearman_full_footprint=uniq["worst_spearman_full_footprint"],
            worst_dot_overlap=uniq["worst_dot_overlap"], worst_overlap_submission=uniq["worst_overlap_submission"],
            byte_unique=uniq["byte_unique_among_checked"], pixel_unique=uniq["pixel_unique_among_checked"],
            unique=uniq["unique"], verdict=uniq["verdict"],
        ),
        raster=dict(path=str(tif.relative_to(ROOT)), sha256=sha256_file(tif), zip=str(zpath.relative_to(ROOT)),
                    zip_sha256=sha256_file(zpath), dots=int(dots.sum()), format_valid=format_ok),
        organizer_confirmed_score=None,
        leaderboard_estimate="unavailable: no organizer receipt and holdout does not rank registry files",
    )
    # verdict logic: a file may be SUBMIT-OK only when every gate passes
    gates = {
        "G1_format": format_ok,
        "G2_uniqueness_vs_118_registry": bool(uniq["unique"]),
        "G3_leakage_canary_detached": canary_pass,
    }
    card["gates"] = gates
    # Repo convention for research surfaces (see docs/downloads/manifest.json): download is allowed for a
    # format-valid, non-copy file; submission needs every gate, including the uniqueness rule.
    card["ok_to_download"] = bool(format_ok and uniq["byte_unique_among_checked"] and uniq["pixel_unique_among_checked"])
    card["ok_to_submit"] = bool(all(gates.values()))
    card["verdict"] = "promote" if card["ok_to_submit"] else "negative"
    (CARDS / f"{args.name}.run_card.json").write_text(json.dumps(card, indent=1, allow_nan=False, default=str) + "\n")
    print(json.dumps(dict(name=args.name, dots=card["raster"]["dots"], format_valid=format_ok,
                          canary_detached=canary_det, gates=gates, ok_to_submit=card["ok_to_submit"]), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
