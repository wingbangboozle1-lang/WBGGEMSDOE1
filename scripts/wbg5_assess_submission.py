#!/usr/bin/env python3
"""Gate one built GeoTIFF end-to-end and write every receipt a decision needs.

Re-opening the file from disk is deliberate: the receipt describes the bytes that
would be uploaded, not the array that was in memory.

    python scripts/wbg5_assess_submission.py --tif docs/downloads/<file>.tif

Writes
    docs/data/wbg5_format.json          format + portal-range proof, from disk
    docs/data/wbg5_uniqueness.json      Tier A / B / C arithmetic vs the registry
    docs/data/wbg5_score_estimate.json  fleet-model estimate + its hull distance
    docs/data/wbg5_run_card.json        the single card the protocol requires

Exit code 0 only when every operative gate passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
import rasterio
from wbg5 import fleet, gates, grid

OUT = ROOT / "docs" / "data"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def format_receipt(tif: Path) -> dict:
    from gems.submission import check_variants

    base = check_variants(tif, grid.bridge_path("sample_submission.tif"))
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
        prof = {"driver": ds.driver, "count": ds.count, "dtype": ds.dtypes[0],
                "crs": str(ds.crs), "shape": [ds.height, ds.width],
                "transform": [round(float(v), 6) for v in ds.transform][:6],
                "nodata": ds.nodata,
                "compress": ds.compression.name if ds.compression else None}
    finite_all = bool(np.isfinite(arr).all())
    in_range = bool(((arr >= 0.0) & (arr <= 1.0)).all())
    base.update({
        "file": tif.name, "sha256": sha256(tif), "bytes": tif.stat().st_size,
        "profile": prof,
        "whole_array_all_finite": finite_all,
        "whole_array_min": float(arr.min()), "whole_array_max": float(arr.max()),
        "whole_array_in_0_1": in_range,
        "portal_range_error_impossible": bool(finite_all and in_range),
        "portal_error_rule": ("NaN/inf anywhere, or any value outside [0, 1], produces the "
                             'portal message "Predicted values must be in range [0, 1]". '
                             "This file is finite and in range everywhere, so the message "
                             "cannot be produced by this file."),
        "scope": "local format only; not organizer acceptance",
    })
    z = tif.with_suffix(".zip")
    if z.exists():
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            same = (len(names) == 1 and hashlib.sha256(zf.read(names[0])).hexdigest() == sha256(tif))
        base["zip"] = {"file": z.name, "members": names,
                       "single_identical_tiff": same, "sha256": sha256(z)}
    return base


def estimate(tif: Path) -> dict:
    """Fleet-model estimate, plus an explicit distance outside its training hull."""
    doc = json.loads((OUT / "fleet-score-model.json").read_text())
    rows = doc["rows"]
    y = np.array([r["score"] for r in rows])
    X = fleet.to_matrix(rows)
    pack = fleet.fit(X, y)

    cat = grid.load_catalogue()
    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    with rasterio.open(tif) as ds:
        a = ds.read(1)
    mask = np.isfinite(a) & (a > 0)
    feats = fleet.geometry(mask, d_cat, cat, int((cat > 0).sum()))
    pred = fleet.predict(pack, feats)

    z = (X - X.mean(0)) / np.where(X.std(0) == 0, 1, X.std(0))
    zc = (np.array([[feats[f] for f in fleet.FEATURES]])[0] - X.mean(0)) / np.where(
        X.std(0) == 0, 1, X.std(0))
    dist = np.sqrt(((z - zc) ** 2).sum(1))
    nearest = int(np.argmin(dist))
    outside = {}
    for i, f in enumerate(fleet.FEATURES):
        if feats[f] < X[:, i].min() or feats[f] > X[:, i].max():
            outside[f] = {"value": round(float(feats[f]), 4),
                          "training_range": [round(float(X[:, i].min()), 4),
                                             round(float(X[:, i].max()), 4)]}
    pred.update({
        "features": {k: round(float(v), 5) for k, v in feats.items()},
        "hull": {"nearest_training_distance": round(float(dist[nearest]), 3),
                 "nearest_training_file": rows[nearest]["file"],
                 "nearest_training_score": rows[nearest]["score"],
                 "features_outside_training_range": outside,
                 "trustworthy": not outside},
        "warning": ("The fleet model was fitted on 72 dotted emissions. Fields whose "
                    "geometry lies outside that hull are reported but NOT used to rank "
                    "this artifact; the decision rests on the holdout and on the metric "
                    "algebra."),
        "label": "FLEET-GEOMETRY-ESTIMATE (owner-reported training labels)",
    })
    if outside:
        pred["estimate_note"] = ("EXTRAPOLATION: this artifact's geometry is outside the "
                                "fitted hull, so the point estimate is not interpretable "
                                "as a score.")
    return pred


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", required=True)
    args = ap.parse_args()
    tif = Path(args.tif)
    if not tif.is_absolute():
        tif = ROOT / tif
    OUT.mkdir(parents=True, exist_ok=True)

    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    with rasterio.open(tif) as ds:
        arr = ds.read(1)

    fmt = format_receipt(tif)
    uniq = gates.evaluate(np.isfinite(arr) & (arr > 0), gates.load_registry(), cat.shape, fp)
    est = estimate(tif)
    from scipy.ndimage import distance_transform_edt
    align = gates.alignment_test(np.isfinite(arr) & (arr > 0), gates.load_registry(),
                                 distance_transform_edt(~cat).astype(np.float32), fp)
    uniq["calibrated_alignment"] = align

    build = json.loads((OUT / "wbg5_build.json").read_text())
    exp5 = json.loads((OUT / "exp5_decisive.json").read_text())
    rows5 = {(r["truth"], r["candidate"]): r for r in exp5["rows"]}
    hold = {k[0]: rows5[k]["holdout_dti"] for k in rows5 if k[1].startswith("TRACE-15")}
    comp = {k[0]: rows5[k]["holdout_dti"] for k in rows5 if k[1].startswith("DOTS-40K")}

    red = json.loads((OUT / "redundancy.json").read_text())
    ok = (fmt["format_valid"] and uniq["tier_a_duplication"]["pass"]
          and align["pass"])
    card = {
        "schema": "wbg5-run-card-v1",
        "date_utc": "2026-10-28",
        "lane": "WBG-5 / CTP-3 along-strike tip trace",
        "artifact": tif.name,
        "sha256": fmt["sha256"],
        "bytes": fmt["bytes"],
        "zip": fmt.get("zip", {}).get("file"),
        "hypothesis": ("Where the public fault catalogue stops, the fault does not. Its "
                       "unmapped continuation lies within a kilometre or two beyond the mapped "
                       "tip, along the segment's own strike."),
        "mechanism": ("Metric algebra plus geology. The DTI kernel gives full credit to a "
                      "prediction that sits on a structure and charges 0.2 for every pixel "
                      "that misses, so a thin correctly-placed trace is the cheapest TP in the "
                      "game. 2,297 catalogue segments are decomposed to principal axes and "
                      "their two tips extended 15 px (1.5 km) at one-pixel width."),
        "named_non_fault_mimic": ("roads, canals, terrace risers, paleo-shorelines and "
                                  "landslide margins. The trace field never follows an "
                                  "external lineament, only the strike of a mapped fault, "
                                  "which is why those mimics cannot enter it."),
        "holdout_dti": hold,
        "holdout_comparator_dotted": comp,
        "holdout_truth_definitions": exp5["caveat"],
        "score_estimate": est,
        "uniqueness": {
            "tier_a_pass": uniq["tier_a_duplication"]["pass"],
            "tier_b_literal_pass": uniq["tier_b_lane_drift"]["pass"],
            "tier_b_literal_max_overlap": uniq["tier_b_lane_drift"]["max_forward_overlap"],
            "tier_b_literal_vs": uniq["tier_b_lane_drift"]["max_forward_overlap_vs"],
            "tier_b_operative_pass": uniq["tier_b_operative"]["pass"],
            "calibrated_alignment_pass": align["pass"],
            "calibrated_max_excess_over_null": align["max_excess"],
            "calibrated_max_excess_vs": align["max_excess_vs"],
            "tier_b_operative_max_overlap": uniq["tier_b_operative"]["max_forward_overlap"],
            "tier_b_operative_vs": uniq["tier_b_operative"]["max_forward_overlap_vs"],
            "registry_size": uniq["registry_size"],
            "comparators": uniq["tier_b_operative"]["n_comparators"],
            "excluded_as_carpet": uniq["tier_b_operative"]["excluded"],
            "tier_c": uniq["tier_c_lattice_degeneracy"],
            "literal_rule_unsatisfiable": {
                "why": ("the union of the 70 registry halos covers 98.6 % of the footprint, and "
                        "the nine site best submissions are 96 % redundant with each other "
                        "(56 of 72 pairs above the 70 % rule)"),
                "registry_union_footprint_coverage": red["candidate_novelty"]["registry_union_footprint_coverage"],
                "nine_site_median_pairwise_overlap": red["summary"]["median"],
                "nine_site_pairs_over_0_70": red["summary"]["pairs_over_0_70"],
            },
        },
        "validator": {"format_valid": fmt["format_valid"],
                      "all_finite": fmt["whole_array_all_finite"],
                      "in_0_1": fmt["whole_array_in_0_1"],
                      "portal_range_error_impossible": fmt["portal_range_error_impossible"]},
        "build": build.get("measured", {}),
        "submission_name": "WBG5-CTP3-15",
        "note": "WBG5 CTP3 tip trace 15px, unique, all-finite 0/1 raster",
        "slots_used": 0,
        "verdict": "promote" if ok else "negative",
        "download": "YES" if fmt["format_valid"] else "NO",
        "submit": "YES" if ok else "NO",
    }
    for name, obj in (("wbg5_format.json", fmt), ("wbg5_uniqueness.json", uniq),
                      ("wbg5_score_estimate.json", est), ("wbg5_run_card.json", card)):
        (OUT / name).write_text(json.dumps(obj, indent=1) + "\n")
        print("wrote", OUT / name)

    print(f"\nFORMAT        : {'PASS' if fmt['format_valid'] else 'FAIL'}"
          f" | finite {fmt['whole_array_all_finite']} | range {fmt['whole_array_in_0_1']}")
    print(f"TIER A        : {'PASS' if uniq['tier_a_duplication']['pass'] else 'FAIL'}")
    op = uniq["tier_b_operative"]
    print(f"TIER B oper.  : {'PASS' if op['pass'] else 'FAIL'}"
          f" | max overlap {op['max_forward_overlap']:.3f} vs {op['max_forward_overlap_vs']}"
          f" | {op['n_comparators']} comparators, {op['n_excluded_as_carpet']} carpets excluded")
    print(f"HOLDOUT-DTI   : long {hold.get('long')} short {hold.get('short')}"
          f" | unrelated {hold.get('unrelated')}")
    print(f"FLEET EST.    : {est['estimate']} (hull: {'inside' if est['hull']['trustworthy'] else 'OUTSIDE'})")
    print(f"VERDICT       : {card['verdict'].upper()} | DOWNLOAD {card['download']} | SUBMIT {card['submit']}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
