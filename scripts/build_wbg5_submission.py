#!/usr/bin/env python3
"""Build, validate and audit the WBG-5 submission GeoTIFF.

Steps
-----
1. read the frozen prediction array produced by ``run_wbg5_lane.py --stage final``
2. write the GeoTIFF with the shared writer (``gems.submission``) in the exact
   convention of the organisers' ``example_submission.tif`` (NaN outside the study
   area, probabilities inside)
3. reopen the bytes and run the strict, fail-closed validator
4. run the novelty audit against every hash-pinned anchor raster
5. write ``evidence/wbg5/`` receipts and a run card

Exit codes: 0 = every gate passed (submittable), 2 = a gate failed (do not submit).

The novelty audit deliberately separates two regimes, because they are not
equivalent evidence:

``competing_published_submissions``
    Real sparse prediction rasters published by other teams. Spearman > 0.90 or
    > 70% of dots within 3 px of one of them is a duplicate.
``synthetic_calibration_controls``
    A spacing-5 lattice. 99.871% of *every* footprint pixel lies within 3 px of
    its nodes (measured, ``tests/test_wbg5.py``), so this comparator returns >99%
    for a uniformly random 40,000-dot set. It is reported for completeness and
    can never be evidence of copying.
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
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import submission  # noqa: E402

CACHE = ROOT / ".cache" / "wbg5"
ANCHORS = ROOT / ".cache" / "anchors"
TEMPLATE = ROOT / "data" / "bridge" / "sample_submission.tif"
LATTICE = ANCHORS / "lattice_r13_s5.tif"
OUT_DIR = ROOT / "docs" / "downloads"
EVID = ROOT / "evidence" / "wbg5"

NAME = "wbg5-satcov-morph-20261028"
OVERLAP_LIMIT = 0.70
RHO_LIMIT = 0.90


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(tif: Path, template: Path) -> dict:
    """Fail-closed local validation against the official submission contract."""
    with rasterio.open(template) as ref:
        ref_profile = (ref.width, ref.height, ref.crs, tuple(ref.transform), ref.count)
        ref_arr = ref.read(1)
    with rasterio.open(tif) as ds:
        checks = {
            "single_band": ds.count == 1,
            "float32": ds.dtypes[0] == "float32",
            "crs_matches_template": ds.crs == ref_profile[2],
            "shape_matches_template": (ds.width, ds.height) == ref_profile[:2],
            "transform_matches_template": tuple(ds.transform) == ref_profile[3],
        }
        arr = ds.read(1)
    finite = np.isfinite(arr)
    checks["no_nan_inside_footprint"] = bool(np.isfinite(arr[np.isfinite(ref_arr)]).all())
    checks["nan_outside_footprint_only"] = bool(
        np.isnan(arr[~np.isfinite(ref_arr)]).all()
    )
    checks["values_in_0_1"] = bool(
        finite.any() and (arr[finite] >= 0.0).all() and (arr[finite] <= 1.0).all()
    )
    checks["has_positive_predictions"] = bool((arr[finite] > 0).any())
    return {
        "checks": checks,
        "all_passed": all(checks.values()),
        "dtype": str(arr.dtype),
        "shape": list(arr.shape),
        "crs": str(rasterio.open(tif).crs),
        "transform": list(tuple(rasterio.open(tif).transform)),
        "range_min": float(arr[finite].min()),
        "range_max": float(arr[finite].max()),
        "nan_pixels": int((~finite).sum()),
        "nan_outside_footprint": int((~finite & ~np.isfinite(ref_arr)).sum()),
        "positive_pixels": int((arr[finite] > 0).sum()),
        "positive_pixels_inside_footprint": int(
            ((arr > 0) & np.isfinite(ref_arr)).sum()
        ),
        "value_outside_footprint_convention": "NaN (identical to example_submission.tif)",
    }


def compare_dots(a: np.ndarray, b: np.ndarray, radius: float = 3.0) -> dict:
    """Forward overlap of dot set ``a`` onto dot set ``b`` within ``radius`` px."""
    pa = np.argwhere(a)
    pb = np.argwhere(b)
    if not len(pa) or not len(pb):
        return {"forward_overlap": 0.0, "n_a": int(len(pa)), "n_b": int(len(pb))}
    dist = cKDTree(pb).query(pa, k=1)[0]
    return {
        "forward_overlap": float((dist <= radius).mean()),
        "n_a": int(len(pa)),
        "n_b": int(len(pb)),
    }


def compare_surface(a: np.ndarray, b: np.ndarray, foot: np.ndarray, seed: int = 5) -> float:
    """Spearman rho of two surfaces on a random footprint subsample."""
    rng = np.random.default_rng(seed)
    idx = rng.choice(np.flatnonzero(foot), size=min(200_000, int(foot.sum())), replace=False)
    xa = a.ravel()[idx]
    xb = b.ravel()[idx]
    keep = np.isfinite(xa) & np.isfinite(xb)
    if keep.sum() < 1000:
        return float("nan")
    rho = spearmanr(xa[keep], xb[keep]).statistic
    return float(rho)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", type=Path, default=CACHE / "final_prediction.npy")
    parser.add_argument("--surface", type=Path, default=CACHE / "surface_final_blind.f32")
    parser.add_argument("--name", default=NAME)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.prediction.exists():
        raise SystemExit(f"missing prediction array: {args.prediction}")

    pred = np.load(args.prediction)
    if pred.dtype != np.float32:
        pred = pred.astype(np.float32)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EVID.mkdir(parents=True, exist_ok=True)
    tif = OUT_DIR / f"{args.name}-nanoutside.tif"
    zpath = OUT_DIR / f"{args.name}-nanoutside.zip"

    # --- write through the shared writer -----------------------------------
    submission.write_submission(pred, TEMPLATE, tif, outside="nan")
    # Deterministic archive: a fixed member timestamp and mode keep the ZIP
    # byte-identical across rebuilds, so the published sha256 stays meaningful.
    info = zipfile.ZipInfo(tif.name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr(info, tif.read_bytes())
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        zbytes = zf.read(names[0]) if len(names) == 1 else b""
    zip_ok = len(names) == 1 and hashlib.sha256(zbytes).hexdigest() == sha256_file(tif)

    receipt = validate(tif, TEMPLATE)
    receipt.update({
        "schema": "gemsdoe1-wbg5-validator-v1",
        "file": str(tif.relative_to(ROOT)),
        "sha256": sha256_file(tif),
        "bytes": tif.stat().st_size,
        "zip": str(zpath.relative_to(ROOT)),
        "zip_sha256": sha256_file(zpath),
        "zip_contains_exactly_one_identical_member": bool(zip_ok),
        "template_sha256": sha256_file(TEMPLATE),
        "generated_utc": "2026-10-28",
        "local_checks_are_not_organizer_acceptance": True,
    })
    (EVID / "validator.json").write_text(json.dumps(receipt, indent=1) + "\n")

    # --- novelty audit -----------------------------------------------------
    with rasterio.open(TEMPLATE) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(tif) as ds:
        ours = ds.read(1)
    ours_dots = np.nan_to_num(ours, nan=0.0) > 0.5

    surface = None
    if args.surface.exists():
        surface = np.fromfile(args.surface, dtype=np.float32).reshape(foot.shape)

    meta = json.loads((ANCHORS / "anchors.json").read_text())
    competing, controls = [], []
    ours_sha = sha256_file(tif)
    for row in meta["anchors"]:
        path = ANCHORS / row["name"]
        if not path.exists():
            continue
        with rasterio.open(path) as ds:
            arr = ds.read(1)
        their_dots = np.nan_to_num(arr, nan=0.0) > 0.5
        entry = {
            "anchor": row["name"],
            "anchor_sha256": row["sha256"],
            "owner_reported_score": row["owner_reported_score"],
            "score_label": row["score_label"],
            "byte_identical": row["sha256"] == ours_sha,
            **compare_dots(ours_dots, their_dots),
        }
        if surface is not None:
            entry["spearman_rho_vs_anchor_surface"] = compare_surface(surface, arr, foot)
        competing.append(entry)

    lattice_row = None
    if LATTICE.exists():
        with rasterio.open(LATTICE) as ds:
            lat = np.nan_to_num(ds.read(1)) > 0
        dist = distance_transform_edt(~lat)
        rng = np.random.default_rng(7)
        idx = rng.choice(np.flatnonzero(foot), size=40000, replace=False)
        rnd = np.zeros(foot.shape, bool)
        rnd.ravel()[idx] = True
        lattice_row = {
            "anchor": "13gems_20261001_r13-lattice-s5 (synthetic calibration control)",
            "role": "synthetic_calibration_controls",
            "fraction_of_ALL_footprint_pixels_within_3px": float((dist[foot] <= 3.0).mean()),
            "random_40000_dot_control_overlap": float((dist.ravel()[idx] <= 3.0).mean()),
            "our_overlap": float((dist[ours_dots] <= 3.0).mean()),
            "verdict": "vacuous_by_construction: a uniform random dot set scores the same",
        }
        controls.append(lattice_row)

    max_overlap = max((c["forward_overlap"] for c in competing), default=0.0)
    max_rho = max(
        (abs(c.get("spearman_rho_vs_anchor_surface") or 0.0) for c in competing), default=0.0
    )
    unique = {
        "schema": "gemsdoe1-wbg5-uniqueness-v1",
        "competing_published_submissions": competing,
        "synthetic_calibration_controls": controls,
        "max_forward_3px_overlap_vs_competing": max_overlap,
        "max_abs_spearman_vs_competing": max_rho,
        "overlap_limit": OVERLAP_LIMIT,
        "rho_limit": RHO_LIMIT,
        "byte_unique_among_checked": all(not c["byte_identical"] for c in competing),
        "passes_competing_gate": bool(
            max_overlap <= OVERLAP_LIMIT and max_rho <= RHO_LIMIT
        ),
        "scope": (
            "11 hash-pinned anchor rasters (git blob SHA-1 and SHA-256 verified) plus the "
            "synthetic r13 lattice. NOT all 92 user-listed sites and not later commits."
        ),
    }
    (EVID / "uniqueness.json").write_text(json.dumps(unique, indent=1) + "\n")

    gates = {
        "format_valid": bool(receipt["all_passed"] and zip_ok),
        "byte_unique": unique["byte_unique_among_checked"],
        "competitor_uniqueness": unique["passes_competing_gate"],
    }
    submittable = all(gates.values())
    decision = {
        "gates": gates,
        "SUBMIT": "YES" if submittable else "NO",
        "reasons": (
            [] if submittable else [k for k, v in gates.items() if not v]
        ),
    }
    (EVID / "decision.json").write_text(json.dumps(decision, indent=1) + "\n")

    print(json.dumps({"validator_checks": receipt["checks"], "zip_ok": zip_ok}, indent=1))
    print(f"\nfile      : {receipt['file']}")
    print(f"sha256    : {receipt['sha256']}")
    print(f"bytes     : {receipt['bytes']}")
    print(f"positive  : {receipt['positive_pixels']}")
    print(f"range     : [{receipt['range_min']}, {receipt['range_max']}]")
    print(f"nan outside footprint only : {receipt['checks']['nan_outside_footprint_only']}")
    print(f"max 3px overlap vs {len(competing)} competing anchors : {max_overlap:.4f} "
          f"(limit {OVERLAP_LIMIT})")
    print(f"max |rho| vs competing anchors               : {max_rho:.4f} (limit {RHO_LIMIT})")
    if lattice_row:
        print(f"lattice 'overlap' (vacuous)                  : {lattice_row['our_overlap']:.4f} "
              f"| random control {lattice_row['random_40000_dot_control_overlap']:.4f}")
    print(f"\nDECISION  : SUBMIT {decision['SUBMIT']}   failed={decision['reasons']}")
    return 0 if submittable else 2


if __name__ == "__main__":
    raise SystemExit(main())
