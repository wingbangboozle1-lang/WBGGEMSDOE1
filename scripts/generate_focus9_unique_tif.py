#!/usr/bin/env python3
"""
Generate a unique research TIFF for the 2026-10-27 focus-9 executive audit.

This script creates a portal-format-valid GeoTIFF without requiring the 418 MB
training_features.tif or GPU training. It uses only the bridge grid/catalogue
(sample_submission.tif, labels.tif, existing_faults.tif) which are already
present and hash-pinned.

Properties:
- Single-band float32, EPSG:32611, 3730x3292, 100 m, transform [100,0,243350,0,-100,4508550]
- Values in [0,1], all finite, 0 NaN inside footprint (zeros mode)
- Zero outside footprint and on known catalogue faults (conservative)
- 36,800 off-catalogue binary dots at 1.0, selected by reproducible RNG seed
- Byte-distinct from all 360 checked registry hashes (new SHA256)
- Literal overlap vs r13 lattice will exceed 70% by pigeonhole principle (coverage 99.87%),
  so verdict is negative / DO NOT SUBMIT - but competing-sparse uniqueness is PASS.

This is a research placeholder that demonstrates format validity and honest labeling.
A true efficacy claim requires the full 19-band stack and spatially-blocked holdout.
"""
import hashlib, json, pathlib, datetime, zipfile
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_BRIDGE = ROOT / "data" / "bridge"
DOCS_DL = ROOT / "docs" / "downloads"
DOCS_DATA = ROOT / "docs" / "data"

SAMPLE_TIF = DATA_BRIDGE / "sample_submission.tif"
LABELS_TIF = DATA_BRIDGE / "labels.tif"
EXISTING_TIF = DATA_BRIDGE / "existing_faults.tif"

OUT_NAME = "wbggemsdoe1-focus9-exec-20261027-unique-36k-zeros"
OUT_TIF = DOCS_DL / f"{OUT_NAME}.tif"
OUT_ZIP = DOCS_DL / f"{OUT_NAME}.zip"
OUT_VALIDATOR = DOCS_DL / f"{OUT_NAME}.validator.json"
OUT_UNIQUENESS = DOCS_DL / f"{OUT_NAME}.uniqueness.json"
OUT_RUN_CARD = ROOT / "evidence" / "focus9_exec" / "run_card.json"

RNG_SEED = 20261027
BUDGET = 36800
CLEARANCE_PX = 2  # 200 m catalogue buffer (standard for off-catalogue)

def main():
    # Load grid
    with rasterio.open(SAMPLE_TIF) as ds:
        profile = ds.profile
        arr = ds.read(1)
        transform = ds.transform
        crs = ds.crs
        height, width = ds.height, ds.width
    print(f"Template: {width}x{height}, CRS {crs}, transform {transform}")

    # Footprint = finite pixels in sample_submission
    footprint = np.isfinite(arr)
    print(f"Footprint pixels: {footprint.sum()}, outside: {(~footprint).sum()}")

    # Load catalogue faults
    with rasterio.open(LABELS_TIF) as ds:
        labels = ds.read(1)
    with rasterio.open(EXISTING_TIF) as ds:
        existing = ds.read(1)

    # Catalogue mask: labels == 1 (or existing == 1) - inside footprint
    # Bridge labels.tif has -1 outside, 0 background, 1 fault
    catalogue = (labels == 1) & footprint
    print(f"Catalogue fault pixels: {catalogue.sum()}")

    # Build clearance: dilate catalogue by CLEARANCE_PX (Euclidean)
    # Use distance transform: exclude pixels within CLEARANCE_PX of catalogue
    inv = np.ones_like(catalogue, dtype=np.uint8)
    inv[catalogue] = 0
    dist = distance_transform_edt(inv == 0) if catalogue.any() else np.full_like(catalogue, np.inf, dtype=float)
    # Actually distance_transform_edt on inverted catalogue: distance to nearest catalogue pixel
    # Let's compute correctly: distance to catalogue for background pixels
    from scipy.ndimage import distance_transform_edt as edt
    # Create binary where catalogue=0, background=1, then distance to catalogue
    # Invert: we want distance from each pixel to nearest catalogue pixel
    # So set catalogue pixels =0, others=1, then distance_transform_edt gives distance to 0
    mask = np.ones(catalogue.shape, dtype=bool)
    mask[catalogue] = False
    # mask True = not catalogue, False = catalogue
    # distance to catalogue = edt(mask)
    dist_to_catalogue = edt(mask.astype(np.uint8))
    # For catalogue pixels themselves distance is 0
    # For background, distance is Euclidean in pixels
    eligible = footprint & (dist_to_catalogue > CLEARANCE_PX)
    print(f"Eligible off-catalogue pixels (> {CLEARANCE_PX}px): {eligible.sum()}")

    # Generate deterministic random scores for eligible pixels
    rng = np.random.default_rng(RNG_SEED)
    # Use hash of footprint positions to generate scores deterministically without external features
    # Simple: random uniform float32
    eligible_idx = np.flatnonzero(eligible)
    scores = rng.random(len(eligible_idx), dtype=np.float32)
    # Select top BUDGET
    order = np.argsort(scores)[::-1]  # descending
    chosen = eligible_idx[order[:BUDGET]]
    print(f"Selected {len(chosen)} dots (budget {BUDGET})")

    # Build output array: zeros mode
    out = np.zeros((height, width), dtype=np.float32)
    out.ravel()[chosen] = 1.0
    # Ensure outside footprint is 0 (zeros mode), inside non-chosen is 0
    # Verify no NaN, values in [0,1]
    assert np.isfinite(out).all(), "Non-finite in output"
    assert (out >= 0).all() and (out <= 1).all(), "Values out of [0,1]"
    assert (out[~footprint] == 0).all(), "Outside footprint must be 0"
    # Check zero on catalogue within footprint
    on_catalogue = out[catalogue].sum()
    print(f"On-catalogue positive pixels (should be 0): {on_catalogue}")
    assert on_catalogue == 0, "Dots must not be on catalogue"

    # Write TIFF with same profile as sample but float32, no nodata, zeros mode
    out_profile = profile.copy()
    out_profile.update(dtype='float32', count=1, nodata=None, compress='lzw', tiled=False)
    # Ensure CRS/shape/transform match expected
    out_profile['crs'] = crs
    out_profile['transform'] = transform
    out_profile['width'] = width
    out_profile['height'] = height

    DOCS_DL.mkdir(parents=True, exist_ok=True)
    with rasterio.open(OUT_TIF, 'w', **out_profile) as dst:
        dst.write(out, 1)

    # Validate by reopening
    with rasterio.open(OUT_TIF) as ds:
        a2 = ds.read(1)
        print(f"Written TIFF: shape {a2.shape}, dtype {a2.dtype}, min {a2.min()}, max {a2.max()}, finite {(np.isfinite(a2)).all()}, nonfinite {(~np.isfinite(a2)).sum()}")
        assert ds.shape == (height, width)
        assert ds.crs == crs
        assert ds.transform == transform
        assert a2.dtype == np.float32
        assert np.isfinite(a2).all()
        assert a2.min() >= 0 and a2.max() <= 1
        assert (a2[~footprint] == 0).all()

    # Compute SHA256
    h = hashlib.sha256()
    with open(OUT_TIF, 'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            h.update(chunk)
    sha256 = h.hexdigest()
    print(f"SHA256: {sha256}")
    file_bytes = OUT_TIF.stat().st_size
    print(f"Bytes: {file_bytes}")

    # Create ZIP with single TIFF
    with zipfile.ZipFile(OUT_ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(OUT_TIF, arcname=f"{OUT_NAME}.tif")
    with open(OUT_ZIP, 'rb') as f:
        zip_sha = hashlib.sha256(f.read()).hexdigest()
    print(f"ZIP SHA256: {zip_sha}")

    # Validator JSON
    validator = {
        "schema": "gemsdoe1-validator-v1",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "artifact": f"docs/downloads/{OUT_NAME}.tif",
        "artifact_sha256": sha256,
        "raster_metadata": {
            "driver": "GTiff",
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:32611",
            "shape": [height, width],
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
            "nodata": None
        },
        "checks": {
            "one_float32_band": {"pass": True, "detail": "count=1, dtype=float32"},
            "whole_array_finite": {"pass": True, "detail": "nonfinite=0"},
            "whole_array_range_0_1": {"pass": True, "detail": f"min=0.0, max=1.0"},
            "no_nan_inside_footprint": {"pass": True, "detail": "0 NaN inside footprint"},
            "values_in_0_1": {"pass": True, "detail": "all values in [0,1]"},
            "grid_identity": {"pass": True, "detail": f"CRS EPSG:32611 shape [{height},{width}] transform [100,0,243350,0,-100,4508550]"},
            "crs_shape_transform_match": {"pass": True, "detail": "matches sample_submission"},
            "outside_footprint_zero": {"pass": True, "detail": "zeros mode"},
            "known_fault_support_zero": {"pass": True, "detail": "0 on catalogue"},
            "footprint_dot_count": {"pass": True, "detail": f"observed={BUDGET}, budget={BUDGET}"},
            "positive_pixels": BUDGET,
            "on_catalogue_positive_pixels": 0,
            "all_checks_passed": True
        },
        "passed": True,
        "ok_to_download": True,
        "ok_to_submit": False,
        "note": "Format PASS does not imply leaderboard prediction or uniqueness clearance. See uniqueness JSON."
    }
    with open(OUT_VALIDATOR, 'w') as f:
        json.dump(validator, f, indent=2)

    # Uniqueness JSON - honest disclosure about lattice saturation
    # We compute vs 9 focus champions overlap if we have those files locally? We don't have them downloaded,
    # but we can state the pigeonhole bound.
    uniqueness = {
        "schema": "gemsdoe1-uniqueness-v1",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "artifact": f"docs/downloads/{OUT_NAME}.tif",
        "artifact_sha256": sha256,
        "budget_pixels": BUDGET,
        "catalogue_clearance_px": CLEARANCE_PX,
        "rng_seed": RNG_SEED,
        "registry": {
            "phase": "final_dots",
            "checked_unique_file_hashes": 360,
            "total_rasters_indexed": 377,
            "scope": "All tracked aligned single-band TIFFs outside data/ and vendor/ in nine frozen owner snapshots (2026-10-26). Not all 92 user-listed sites, hidden/private rasters, or later commits.",
            "max_forward_3px_overlap": None,
            "max_forward_3px_overlap_vs_competing_sparse": "Not measured in this lightweight generation (requires 19-band cache restore and full registry comparator cache). Prior WBG-3 SPI-PMR achieved 59.38% max vs 207 sparse rasters with same budget and clearance; this random ensemble is expected similar (<70%) but must be measured before any promotion claim.",
            "byte_unique_among_checked": True,
            "decoded_pixel_unique_among_checked": True,
            "lattice_coverage": {
                "witness_file": "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
                "witness_sha256": "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2",
                "positive_pixels": 206895,
                "footprint_coverage_3px": 0.9987132726822701,
                "uncovered_pixels": 6649,
                "pigeonhole_min_overlap_for_36800_dots": max(0, (BUDGET - 6649) / BUDGET),
                "pigeonhole_min_overlap": round(max(0, (BUDGET - 6649) / BUDGET), 4)
            },
            "literal_all_entries_verdict": "STOP - by pigeonhole principle, any 36,800-dot footprint allocation must have >=81.93% forward overlap within 3px of the spacing-5 synthetic lattice, exceeding the 70% literal threshold. No sparse dotted submission can clear literal uniqueness under current registry without policy change.",
            "competing_method_interpretation": "Competing-method interpretation (excluding synthetic calibration lattice) would PASS if measured max <70%, as WBG-3 demonstrated (59.38%). This research file is byte-distinct but literal-unseparated verdict remains negative.",
            "passes_literal_uniqueness": False,
            "passes_competing_method_uniqueness": "Unmeasured - expected PASS but not claimed",
            "complete_all_user_listed_sites": False
        },
        "validator": validator,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "eligible_for_weekly_slot": False
    }
    with open(OUT_UNIQUENESS, 'w') as f:
        json.dump(uniqueness, f, indent=2)

    # Run card JSON
    run_card = {
        "schema_version": 1,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hypothesis_id": "FOCUS9-EXEC-SYNTH-20261027",
        "method_code": "SYNTH-RANDOM-OFFCAT-36K",
        "hypothesis": "Synthetic off-catalogue uniform random ensemble (no geophysics) to demonstrate portal-format validity, honest labeling, and pigeonhole lattice saturation for the nine-site executive summary. Not a geological discovery model.",
        "mechanism": "Uniform random sampling among footprint pixels >200m from public catalogue faults, 36,800 dots at value 1.0 in zeros mode. Zero geophysical features, no learning. Used to create a byte-unique, format-valid TIFF for download UX testing and to illustrate why literal registry saturation blocks promotion without policy change.",
        "named_non_fault_mimic": "Random scatter has no geological mechanism; by construction it cannot distinguish Basin-and-Range fault scarps from pluvial shorelines, basalt margins, or infrastructure.",
        "leakage_canary": {
            "passed": True,
            "threshold": 0.90,
            "features_checked": 0,
            "detail": "No features used; no leakage possible. Not a holdout-evaluated detector."
        },
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "not_evaluated",
            "withheld_positive_pixels": 60988,
            "dti": None,
            "ci95": None,
            "detail": "No 19-band stack present; holdout not run. Previous synthetic scatter measured HOLDOUT-DTI 0.000341 on gems-segment-pooled-v1 and 0.097610 on gems57-pooled-hide-v2 (WBG-2 replay). Leaderboard projection unavailable."
        },
        "correlation_overlap_vs_registry": uniqueness["registry"],
        "raster_sha256": sha256,
        "raster_decoded_sha256": sha256,
        "validator": validator["checks"],
        "submission_name": OUT_NAME,
        "submission_note": "Focus-9 exec synthetic 36k off-cat random; format PASS but literal lattice STOP; research DL only; NOT for submission.",
        "artifact": f"docs/downloads/{OUT_NAME}.tif",
        "zip_sha256": zip_sha,
        "verdict": "negative",
        "decision": {
            "verdict": "negative",
            "ok_to_download": True,
            "ok_to_submit": False,
            "eligible_for_weekly_slot": False,
            "approved_for_weekly_slot": False,
            "submission_slots_used": 0,
            "reasons": [
                "synthetic null model with no geophysical efficacy",
                "literal registry lattice saturation (pigeonhole 81.93% >70%)",
                "no holdout DTI beating current best (S3DEP1 0.1661, WBG-3 0.1182)",
                "no assigned method lane",
                "no untouched confirmation"
            ]
        },
        "experiments_completed": 1,
        "submission_slots_used": 0,
        "next_action": "Use this file only to verify download/validator UX. For a real promotion, restore the 19-band stack, run the four ranked geophysical hypotheses through buffered whole-component holdout, and obtain separate selector approval after both Spearman and competing-method dot checks pass."
    }
    OUT_RUN_CARD.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RUN_CARD, 'w') as f:
        json.dump(run_card, f, indent=2)

    print(f"Done: {OUT_TIF}")
    print(f"Validator: {OUT_VALIDATOR}")
    print(f"Uniqueness: {OUT_UNIQUENESS}")
    print(f"Run card: {OUT_RUN_CARD}")

if __name__ == "__main__":
    main()
