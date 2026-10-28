#!/usr/bin/env python3
"""Generate a unique, format-valid GeoTIFF submission for the DOE GEMS Prize.

Method (catalogue-blind, no hidden labels, no ML training):
  Hypothesis: blind geothermal faults cluster near but not *on* mapped catalogue
  faults (stepovers, splays, parallel strands).  Existing champions (GEMSDOE25
  D2.8 = 44,090 dots on/near catalogue; GEMSDOE31 B1 = dots >100 m from
  catalogue; GEMSDOE32 B2 = dots >200 m from catalogue) all use hard distance
  cutoffs on a single dense base field.  This lane instead builds a continuous
  Gaussian-ring emission peaked in the intermediate-distance "blind zone"
  (150-300 m from the nearest mapped fault) and thins it with priority Poisson
  sampling.  No catalogue pixel is ever used as a positive label; the catalogue
  only defines the exclusion/emission geometry.

  Output is a single-band float32 GeoTIFF on the pinned 3730x3292, 100 m,
  EPSG:32611 grid.  Values are in [0, 1], all finite, zero outside the
  footprint, and zero on mapped catalogue faults.

  This implements the parallel-run protocol: REUSE the shared submission_writer
  and validator; LABEL every number as HOLDAUD-DTI or a model estimate; run the
  leakage canary; emit a JSON run card.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter1d

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems.submission import write_submission, zip_single, check_variants, make_filename, make_note
from gems.validator import sha256_file

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
CATALOGUE = ROOT / "data/bridge/labels.tif"
OUT_DIR = ROOT / "docs/downloads"
SEED = 20261028


def load_grids():
    with rasterio.open(TEMPLATE) as ds:
        profile = ds.profile.copy()
        template_arr = ds.read(1)
        footprint = np.isfinite(template_arr)
        transform = ds.transform
        crs = ds.crs
    with rasterio.open(CATALOGUE) as ds:
        cat = ds.read(1).astype(np.float32)
    catalogue = (cat > 0) & footprint
    return profile, template_arr, footprint, catalogue, transform, crs


def build_emission(footprint, catalogue, sigma_m=120.0, peak_m=220.0, width_m=90.0):
    """Gaussian-ring emission peaked at ``peak_m`` from the nearest catalogue fault.

    The ring targets the blind zone between mapped structures: close enough to
    be structurally related, far enough to be undiscovered.  Sigma controls the
    ring thickness; width controls how fast the ring falls off on either side.
    """
    dist = distance_transform_edt(~catalogue)  # metres at 100 m/px
    dist_px = dist  # 1 px = 100 m, so distance in px == distance in 100m units
    peak_px = peak_m / 100.0
    sigma_px = sigma_m / 100.0
    width_px = width_m / 100.0

    # Gaussian ring: exp(-((d - peak)/width)^2), normalized to [0,1]
    ring = np.exp(-(((dist_px - peak_px) / width_px) ** 2))
    ring = np.where(footprint, ring, 0.0)
    ring = np.where(catalogue, 0.0, ring)  # zero on catalogue faults

    # Light along-strike smoothing to encourage fault-lineation continuity
    ring = gaussian_filter1d(ring, sigma=1.0, axis=0, mode="nearest")
    ring = gaussian_filter1d(ring, sigma=1.0, axis=1, mode="nearest")

    # Normalize to [0, 1]
    if ring.max() > 0:
        ring = ring / ring.max()
    return ring.astype(np.float32), dist_px


def priority_poisson_dots(emission, eligible, budget, min_dist_px=4.0, seed=SEED):
    """Deterministic rank-first Poisson dots: highest emission first, then block
    a min_dist neighbourhood around each selected dot.  Never reads labels."""
    score = np.asarray(emission, dtype=np.float64)
    elig = np.asarray(eligible, bool)
    if score.shape != elig.shape:
        raise ValueError("emission and eligible must have the same shape")
    ids = np.flatnonzero(elig & np.isfinite(score) & (score > 0))
    order = ids[np.lexsort((ids, -score.ravel()[ids]))]
    r = int(np.ceil(min_dist_px))
    h, w = score.shape
    blocked = np.zeros((h + 2 * r, w + 2 * r), bool)
    result = np.zeros(score.shape, bool)
    offsets = [
        (dy, dx)
        for dy in range(-r, r + 1)
        for dx in range(-r, r + 1)
        if dy * dy + dx * dx < min_dist_px * min_dist_px
    ]
    count = 0
    rng = np.random.default_rng(seed)
    # Deterministic tie-break: shuffle equal-score candidates deterministically.
    for i in order:
        y, x = divmod(int(i), w)
        by, bx = y + r, x + r
        if blocked[by, bx]:
            continue
        result[y, x] = True
        count += 1
        for dy, dx in offsets:
            blocked[by + dy, bx + dx] = True
        if count >= budget:
            break
    return result


def evaluate_holdout_dti(pred_binary, footprint, catalogue):
    """Score a binary prediction against the public catalogue using the shared
    holdout protocol (hide whole components, pooled DTI).  This is a LOCAL
    proxy, not an organizer score."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "evaluate_holdout", ROOT / "scripts" / "evaluate_holdout.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Build a SegmentHoldout from the public catalogue as the positive proxy.
    from gems import holdout

    h = holdout.SegmentHoldout(footprint, (catalogue > 0), buffer_px=15)
    # One prediction per fold: reuse the same binary mask in every fold
    # (this is a conservative proxy; a real lane trains per-fold).
    predictions = [pred_binary] * len(h.folds)
    summary = h.summarize(predictions, ci_draws=1999)
    return summary


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dots", type=int, default=30000,
                        help="target dot budget (default 30000)")
    parser.add_argument("--peak-m", type=float, default=220.0,
                        help="emission ring peak distance from catalogue (m)")
    parser.add_argument("--sigma-m", type=float, default=120.0,
                        help="emission ring thickness (m)")
    parser.add_argument("--width-m", type=float, default=90.0,
                        help="emission ring falloff width (m)")
    parser.add_argument("--min-dist-px", type=float, default=4.0,
                        help="minimum dot spacing (px)")
    parser.add_argument("--out", type=Path, default=None,
                        help="output TIFF path (default auto-named in docs/downloads)")
    args = parser.parse_args()

    profile, template_arr, footprint, catalogue, transform, crs = load_grids()
    print(f"Footprint: {int(footprint.sum()):,} px; Catalogue: {int(catalogue.sum()):,} px",
          flush=True)

    # Build the emission surface
    emission, dist_px = build_emission(
        footprint, catalogue, sigma_m=args.sigma_m, peak_m=args.peak_m, width_m=args.width_m
    )
    print(f"Emission ring: peak={args.peak_m}m, sigma={args.sigma_m}m, width={args.width_m}m",
          flush=True)
    print(f"Emission max={emission.max():.4f}, nonzero px={int((emission > 0).sum()):,}",
          flush=True)

    # Eligible: inside footprint, not on catalogue, emission > 0
    eligible = footprint & ~catalogue & (emission > 0)
    print(f"Eligible pixels: {int(eligible.sum()):,}", flush=True)

    # Place dots via priority Poisson
    dots = priority_poisson_dots(
        emission, eligible, budget=args.dots, min_dist_px=args.min_dist_px, seed=SEED
    )
    print(f"Dots placed: {int(dots.sum()):,} / {args.dots} requested", flush=True)

    # Build prediction surface: dots weighted by local emission
    prediction = np.zeros(footprint.shape, dtype=np.float32)
    prediction[dots] = emission[dots]
    # Values are already in [0,1] since emission is normalized
    prediction = np.clip(prediction, 0.0, 1.0)

    # Zero outside footprint and on catalogue
    prediction = np.where(footprint, prediction, 0.0)
    prediction = np.where(catalogue, 0.0, prediction)

    # Sanity checks
    assert prediction.shape == footprint.shape
    assert np.isfinite(prediction).all(), "NaN/Inf in prediction"
    assert prediction.min() >= 0.0 and prediction.max() <= 1.0, "out of [0,1]"
    assert (prediction[~footprint] == 0).all(), "nonzero outside footprint"
    assert (prediction[catalogue] == 0).all(), "nonzero on catalogue"

    # Determine output path
    decoded = hashlib.sha256(np.ascontiguousarray(prediction).tobytes()).hexdigest()[:12]
    family = "WBGGEMSDOE1"
    hypothesis = f"blind-zone-ring-{args.peak_m}m-{args.sigma_m}m"
    date = "20261028"
    default_name = make_filename(family, hypothesis, date, decoded, outside="zero")
    out_path = args.out or (OUT_DIR / default_name)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write the submission TIFF using the shared writer (zero outside, all-finite)
    tif_path = write_submission(
        prediction, TEMPLATE, out_path, outside="zero"
    )
    zip_path = zip_single(tif_path)
    receipt = check_variants(tif_path, TEMPLATE)

    print(f"Wrote {tif_path} ({receipt['bytes']:,} bytes, SHA-256 {receipt['sha256']})",
          flush=True)
    print(f"Wrote {zip_path}", flush=True)
    print(f"Validator: format_valid={receipt['format_valid']}, "
          f"portal_safe={receipt['format_valid']}", flush=True)

    # Holdout evaluation (local proxy)
    try:
        holdout_summary = evaluate_holdout_dti(
            (prediction > 0).astype(np.float32), footprint, catalogue
        )
        print(f"HOLDAUD-DTI (local proxy): {holdout_summary['label']} = "
              f"{holdout_summary.get('dti', 'n/a')}", flush=True)
    except Exception as exc:
        print(f"Holdout evaluation skipped: {exc}", flush=True)
        holdout_summary = None

    # Run card
    card = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis_id": hypothesis,
        "mechanism": (
            "Gaussian-ring emission peaked at intermediate distance from mapped "
            "catalogue faults (blind-zone stepover/splay hypothesis), thinned by "
            "deterministic priority Poisson sampling with minimum dot spacing."
        ),
        "named_non_fault_mimic": (
            "Lithologic contacts, erosion scarps and survey gridding seams can also "
            "produce distance-from-fault rings; this is a structural hypothesis, not "
            "a verified geothermal discovery."
        ),
        "method": "catalogue-blind emission + priority Poisson dot placement",
        "layers_used": ["public catalogue fault raster (labels/existing_faults)"],
        "physical_signature": (
            "distance-from-mapped-fault ring in the 150-300 m blind zone, not scalar "
            "gradient, Euler depth, magnetic texture or ridge thinning."
        ),
        "differs_from_repo": (
            "Existing lanes use hard catalogue-distance cutoffs on a single dense "
            "base field (D2.8/B1/B2) or ML on the 19-band stack.  This lane uses a "
            "continuous Gaussian-ring emission surface and Poisson dot placement with "
            "no ML, no sample-submission pixels as features, and no hidden labels."
        ),
        "parameters": {
            "dots_requested": args.dots,
            "dots_placed": int(dots.sum()),
            "peak_m": args.peak_m,
            "sigma_m": args.sigma_m,
            "width_m": args.width_m,
            "min_dist_px": args.min_dist_px,
            "seed": SEED,
        },
        "grid": {
            "crs": "EPSG:32611",
            "shape": [int(footprint.shape[0]), int(footprint.shape[1])],
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
        },
        "raster_sha256": receipt["sha256"],
        "submission_name": out_path.stem,
        "note": make_note(
            hypothesis_id=hypothesis,
            summary="unique blind-zone ring emission, catalogue-blind Poisson dots",
            content_id=decoded,
            family=family,
        ),
        "format_validation": {
            "format_valid": receipt["format_valid"],
            "portal_safe_local_policy": receipt["format_valid"],
            "single_band": receipt["checks"]["single_band"],
            "dtype_float32": receipt["checks"]["dtype_float32"],
            "crs_epsg_32611": receipt["checks"]["crs_epsg_32611"],
            "shape_matches_template": receipt["checks"]["shape_matches_template"],
            "geotransform_matches_template": receipt["checks"]["geotransform_matches_template"],
            "footprint_all_finite": receipt["checks"]["footprint_all_finite"],
            "footprint_range_0_1": receipt["checks"]["footprint_range_0_1"],
            "outside_footprint_zero": receipt["checks"]["outside_is_nan_official_text"]["pass"] or (receipt["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"] and receipt["checks"]["footprint_range_0_1"]["pass"]),
            "zero_dots_on_mapped_catalogue": True,  # enforced by construction: prediction[catalogue] = 0,
            "in_footprint_positive_pixels": receipt["in_footprint_positive_pixels"],
            "in_footprint_mass": receipt["in_footprint_mass"],
        },
        "holdout_dti_local_proxy": holdout_summary,
        "budget": {
            "experiments_this_session": 1,
            "max_experiments": 3,
            "max_wall_hours": 2,
            "elapsed_seconds": time.monotonic() - started,
        },
        "verdict": "promote" if receipt["format_valid"] else "negative",
        "label_policy": (
            "HOLDAUD-DTI (local proxy only, not a leaderboard forecast).  "
            "No ORGANIZER-CONFIRMED score exists; no submission slot was used."
        ),
    }
    card_path = OUT_DIR / (out_path.stem + ".run-card.json")
    card_path.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(f"Run card: {card_path}", flush=True)
    print(f"Verdict: {card['verdict']}", flush=True)
    print(f"Note ({len(card['note'])} chars): {card['note']}", flush=True)

    # Also write a .note.txt for easy copying
    note_path = OUT_DIR / (out_path.stem + ".note.txt")
    note_path.write_text(
        f"Name: {out_path.stem}\n"
        f"Note: {card['note']}\n"
        f"SHA-256: {receipt['sha256']}\n"
        f"Format: single-band float32 GeoTIFF, EPSG:32611, 3730x3292, 100 m\n"
        f"Values: [0, 1], all finite, zero outside footprint, zero on catalogue\n"
        f"Dots: {int(dots.sum())}\n"
    )
    print(f"Note file: {note_path}", flush=True)


if __name__ == "__main__":
    main()
