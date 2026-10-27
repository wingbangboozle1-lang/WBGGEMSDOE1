#!/usr/bin/env python3
"""One preregistered TASC lane: three arms, shared holdout, one unique TIFF.

The lane and every constant are frozen in ``registry/preregistration_tasc_20261027.json``
and ``research/03_ranked_hypotheses_2026-10-27.md``.  No leaderboard score,
organizer receipt or weekly submission slot is created here.

Modes:
  --build-features  Build the frozen physical/tip surfaces and run the shared canary.
  --execute         Reuse those surfaces, score all three arms, check novelty, write
                    the format-validated research TIFF and the JSON run card.

All catalogue-derived channels use ``fold.visible`` only.  No registry raster, prior
prediction pixel, hidden component or sample-submission value is an input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("WBG_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data" / "raw"))

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from gems import emission, holdout, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402
from prepare_data import prepare  # noqa: E402

PREREG = ROOT / "registry/preregistration_tasc_20261027.json"
DOC = ROOT / "research/03_ranked_hypotheses_2026-10-27.md"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
REGISTRY = ROOT / "registry/registry.json"
CACHE = ROOT / ".cache/tasc"
EVIDENCE = ROOT / "evidence"
DOWNLOADS = ROOT / "docs/downloads"
DOCS_DATA = ROOT / "docs/data"
LEDGER = ROOT / "registry/experiment_ledger_tasc_20261027.json"
RUN_CARD = EVIDENCE / "tasc_run_card_20261027.json"
DOCS_CARD = DOCS_DATA / "run-card-tasc-20261027.json"
FEATURE_RECEIPT = EVIDENCE / "tasc_features_20261027.json"
CANARY_RECEIPT = EVIDENCE / "tasc_canary_20261027.json"
EXPERIMENT_RECEIPT = EVIDENCE / "tasc_experiment_20261027.json"

EXPECTED_INPUTS = {
    "data/bridge/sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "data/bridge/labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
}


def save(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False, default=float) + "\n")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_inputs(prereg: dict) -> dict:
    for rel, digest in EXPECTED_INPUTS.items():
        p = ROOT / rel
        if not p.is_file() or sha256_file(p) != digest:
            raise ValueError(f"pinned input missing or altered: {rel}")
    pins = json.loads((ROOT / "registry/template_pins.json").read_text())[
        "cached_feature_stack_reference"
    ]["expected_band_sha256"]
    receipt = prepare()
    if [b["sha256"] for b in receipt["bands"]] != pins:
        raise ValueError("19-band shared cache does not match template pins")
    registry = json.loads(REGISTRY.read_text())
    if registry["rejected_count"] != 0 or registry["unique_rasters"] != len(registry["entries"]):
        raise ValueError("novelty registry is incomplete")
    for row in registry["entries"]:
        p = ROOT / row["comparison_cache_path"]
        if not p.is_file() or sha256_file(p) != row["comparison_cache_sha256"]:
            raise ValueError(f"registry comparator hash mismatch: {row['id']}")
    return {"shared_cache_bands": 19, "registry_unique_rasters": registry["unique_rasters"],
            "registry_rejected": registry["rejected_count"]}


def load_grid(prereg: dict):
    with rasterio.open(TEMPLATE) as ds:
        footprint = np.isfinite(ds.read(1))
        meta = (ds.shape, ds.crs, ds.transform)
    with rasterio.open(LABELS) as ds:
        if (ds.shape, ds.crs, ds.transform) != meta:
            raise ValueError("catalogue grid mismatch")
        catalogue = footprint & (ds.read(1) > 0)
    return footprint, catalogue


def load_band(number: int, cache_receipt: dict, footprint: np.ndarray) -> np.ndarray:
    row = cache_receipt["bands"][number - 1]
    path = ROOT / "data/template57" / row["cache_file"]
    a = np.asarray(np.load(path, mmap_mode="r"), dtype=np.float32).copy()
    valid = footprint & np.isfinite(a)
    med = float(np.median(a[valid])) if valid.any() else 0.0
    a[~valid] = med
    return a


def robust_pos(a: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    vals = a[footprint]
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25.0, 75.0])
    scale = max(float(q75 - q25) / 1.349, 1e-6)
    z = (a - med) / scale
    return np.clip(z, 0.0, 6.0).astype(np.float32)


def grad_mag(a: np.ndarray, sigma: float) -> np.ndarray:
    sm = ndi.gaussian_filter(a, sigma, mode="nearest")
    gy, gx = np.gradient(sm)
    return np.hypot(gx, gy).astype(np.float32)


def tip_corridor(visible: np.ndarray, hidden: np.ndarray, footprint: np.ndarray,
                 prereg: dict) -> tuple[np.ndarray, dict]:
    """Skeletonize visible faults only; return fold-local forward tip corridors."""
    c = prereg["fixed_constants"]
    skel = skeletonize(visible & footprint)
    if np.any(skel & ~visible) or np.any(skel & hidden):
        raise ValueError("skeletonization leaked non-visible or hidden catalogue pixels")
    neighbours = ndi.convolve(skel.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - skel
    endpoints = skel & (neighbours == 1)
    ys, xs = np.nonzero(endpoints)
    H, W = footprint.shape
    s_vals = np.arange(c["corridor_s_range_px"][0], c["corridor_s_range_px"][1] + 1, dtype=np.float64)
    t_vals = np.arange(-c["corridor_t_abs_max_px"], c["corridor_t_abs_max_px"] + 1, dtype=np.float64)
    S, T = np.meshgrid(s_vals, t_vals, indexing="ij")
    weights = np.exp(-((S - c["corridor_s_peak_px"]) / c["corridor_s_sigma_px"]) ** 2
                     - (T / c["corridor_t_sigma_px"]) ** 2).astype(np.float32)
    corridor = np.zeros(footprint.shape, np.float32)
    used = 0
    for y, x in zip(ys, xs):
        r = 12
        y0, y1 = max(0, y - r), min(H, y + r + 1)
        x0, x1 = max(0, x - r), min(W, x + r + 1)
        ly, lx = np.nonzero(skel[y0:y1, x0:x1])
        if len(ly) < 2:
            continue
        pts = np.column_stack((ly + y0, lx + x0)).astype(np.float64)
        centre = pts.mean(axis=0)
        cov = np.cov((pts - centre).T)
        vals, vecs = np.linalg.eigh(cov)
        u = vecs[:, int(np.argmax(vals))]
        outward = np.array([y, x], np.float64) - centre
        if np.dot(u, outward) < 0:
            u = -u
        norm = np.linalg.norm(u)
        if norm < 1e-9:
            continue
        u /= norm
        v = np.array([-u[1], u[0]], np.float64)
        yy = np.rint(y + S * u[0] + T * v[0]).astype(np.int64)
        xx = np.rint(x + S * u[1] + T * v[1]).astype(np.int64)
        yyc = np.clip(yy, 0, H - 1)
        xxc = np.clip(xx, 0, W - 1)
        ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W) & footprint[yyc, xxc]
        np.maximum.at(corridor, (yyc[ok], xxc[ok]), weights[ok])
        used += 1
    corridor[visible] = 0.0
    corridor[~footprint] = 0.0
    stats = {"visible_pixels": int(visible.sum()), "skeleton_pixels": int(skel.sum()),
             "endpoints": int(len(ys)), "endpoints_with_tangent": int(used),
             "corridor_positive_pixels": int((corridor > 0).sum()),
             "skeleton_subset_of_visible": True}
    return corridor, stats


def annulus(visible: np.ndarray, footprint: np.ndarray, prereg: dict) -> np.ndarray:
    c = prereg["fixed_constants"]
    d = ndi.distance_transform_edt(~visible).astype(np.float32)
    out = np.exp(-((d - 8.0) / 10.0) ** 2).astype(np.float32)
    out[(d < c["annulus_px"][0]) | (d > c["annulus_px"][1])] = 0.0
    out[visible] = 0.0
    out[~footprint] = 0.0
    return out


def build_features(prereg: dict) -> dict:
    started = time.monotonic()
    CACHE.mkdir(parents=True, exist_ok=True)
    inputs = verify_inputs(prereg)
    footprint, catalogue = load_grid(prereg)
    cache_receipt = json.loads((EVIDENCE / "shared_feature_cache.json").read_text())
    b = prereg["fixed_constants"]["band_indices_1_based"]
    sigma = prereg["fixed_constants"]["response_gaussian_sigma_px"]

    raw = {}
    for key, idx in b.items():
        raw[key] = load_band(idx, cache_receipt, footprint)
    shear_g = robust_pos(grad_mag(raw["geod_shearrate"], sigma), footprint)
    dilat = robust_pos(raw["geod_dilaterate"], footprint)
    grav_g = robust_pos(grad_mag(raw["iso_grav_anom"], sigma), footprint)
    mag_g = robust_pos(grad_mag(raw["tmi"], sigma), footprint)
    depth_g = robust_pos(grad_mag(raw["depth_to_base_surf"], sigma), footprint)
    R = (0.30 * shear_g + 0.20 * dilat + 0.20 * grav_g + 0.15 * mag_g + 0.15 * depth_g).astype(np.float32)
    R[~footprint] = 0.0
    del shear_g, dilat, grav_g, mag_g, depth_g
    for key in list(raw):
        raw[key][~footprint] = 0.0

    ctx = holdout.SegmentHoldout(footprint, catalogue,
                                 buffer_px=prereg["fixed_constants"]["holdout_buffer_px"])
    C = np.zeros(footprint.shape, np.float32)
    D = np.zeros(footprint.shape, np.float32)
    fold_receipts = []
    for fold in ctx.folds:
        hidden = catalogue & ~fold["visible"]
        corridor, stats = tip_corridor(fold["visible"], hidden, footprint, prereg)
        dist = annulus(fold["visible"], footprint, prereg)
        # Corridor support may overlap hidden truth pixels (that is the target), but the
        # skeleton assertion proves it was derived from visible faults only.
        C[fold["valid"]] = corridor[fold["valid"]]
        D[fold["valid"]] = dist[fold["valid"]]
        fold_receipts.append({"fold": fold["name"], **stats,
                              "withheld_positive_pixels": int(fold["truth"].sum()),
                              "visible_fault_pixels": int(fold["visible"].sum()),
                              "hidden_component_pixels": int(hidden.sum()),
                              "catalogue_derived_from_visible_only": True,
                              "skeleton_intersects_hidden_components": False})
        del corridor, dist

    arm_A = R.copy()
    arm_B = (C * (0.5 + R)).astype(np.float32)
    arm_C = (D * (0.5 + R)).astype(np.float32)
    for name, arr in (("R", R), ("C", C), ("D", D), ("A", arm_A), ("B", arm_B), ("C_arm", arm_C)):
        arr[~footprint] = 0.0
        np.save(CACHE / f"{name}.npy", arr)

    canary_features = {f"raw_{k}": v for k, v in raw.items()}
    canary_features.update({"response_R": R, "tip_corridor_C": C, "annulus_D": D,
                            "arm_A": arm_A, "arm_B": arm_B, "arm_C": arm_C})
    canary = ctx.canary(canary_features, seed=20261027, max_per_class=15000)
    receipt = {
        "schema": "gemsdoe1-tasc-features-v1",
        "generated_utc": utc(),
        "preregistration_sha256": sha256_file(PREREG),
        "hypothesis_document_sha256": sha256_file(DOC),
        "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
        "inputs": inputs,
        "fold_receipts": fold_receipts,
        "feature_arrays": {name: {"path": str((CACHE / f"{name}.npy").relative_to(ROOT)),
                                  "sha256": sha256_file(CACHE / f"{name}.npy")}
                           for name in ("R", "C", "D", "A", "B", "C_arm")},
        "canary": canary,
        "elapsed_seconds": time.monotonic() - started,
    }
    save(FEATURE_RECEIPT, receipt)
    save(CANARY_RECEIPT, canary)
    print(json.dumps({"canary_passed": canary["passed"],
                      "max_orientation_invariant_auc": max(
                          max(r["auc"], 1 - r["auc"]) for v in canary["features"].values()
                          for r in v["folds"]),
                      "n_features_checked": len(canary["features"]),
                      "elapsed_seconds": receipt["elapsed_seconds"]}, indent=2))
    return receipt


def load_features(prereg: dict) -> dict[str, np.ndarray]:
    receipt = json.loads(FEATURE_RECEIPT.read_text())
    if receipt["preregistration_sha256"] != sha256_file(PREREG):
        raise ValueError("preregistration changed after feature build")
    out = {}
    for name, row in receipt["feature_arrays"].items():
        p = ROOT / row["path"]
        if sha256_file(p) != row["sha256"]:
            raise ValueError(f"cached feature altered: {name}")
        out[name] = np.load(p, mmap_mode="r")
    return out


def lli_projection(tif: Path, footprint: np.ndarray, catalogue: np.ndarray) -> dict:
    """Empirical projection on 118 USER-REPORTED historical values; never a score."""
    from wbggems1.lli_calibrator import fit_lli_calibrator

    cal, report = fit_lli_calibrator()
    rdir = ROOT / "data/raw"
    with rasterio.open(rdir / "external/lidar_scarp_features_u8.tif") as ds:
        has_lidar = (ds.read(12) > 0) & footprint
    with rasterio.open(rdir / "training_features.tif") as ds:
        slope_raw = ds.read(19).astype(np.float32)
    slope = np.where((np.abs(slope_raw) < 1e30) & np.isfinite(slope_raw) & footprint, slope_raw, 0.0)
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    h23 = (rdir / "registry_cache/data/registry/scored/"
           "GEMSDOE22__gems22-h23-b-dti-optimal-emission-10pct-20261002-86176698-nan.tif")
    if not h23.exists():
        h23 = (rdir / "registry_cache/data/registry/scored/"
               "GEMSDOE32__gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    with rasterio.open(h23) as ds:
        ref_pos = (np.nan_to_num(ds.read(1), nan=0.0) > 0) & footprint
    ref_near = ndi.distance_transform_edt(~ref_pos) <= 3.0
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
    projected = cal.project(arr, footprint, d_cat, has_lidar, slope, ref_near)
    projected["label"] = (
        f"LLI-PROJECTION (empirical Ridge on n={report['n_organizer_scored_rasters']} "
        "USER-REPORTED / NOT ORGANIZER-CONFIRMED historical rasters; "
        f"LOO MAE={report['loo_mae']:.4f}, LOO Spearman={report['loo_spearman_rho']:.3f}; "
        "NOT an organizer score, NOT a leaderboard measurement)"
    )
    projected["n_historical_values"] = report["n_organizer_scored_rasters"]
    projected["historical_value_evidence_class"] = "USER-REPORTED; NOT ORGANIZER-CONFIRMED"
    return projected


def execute(prereg: dict) -> dict:
    started = time.monotonic()
    if sha256_file(PREREG) != prereg["_frozen_sha256"]:
        raise ValueError("preregistration changed during execution")
    inputs = verify_inputs(prereg)
    footprint, catalogue = load_grid(prereg)
    F = load_features(prereg)
    R, C, D = np.asarray(F["R"]), np.asarray(F["C"]), np.asarray(F["D"])
    arm_A, arm_B, arm_C = np.asarray(F["A"]), np.asarray(F["B"]), np.asarray(F["C_arm"])
    canary = json.loads(CANARY_RECEIPT.read_text())
    if not canary["passed"]:
        raise RuntimeError("leakage canary failed; no holdout scoring or TIFF packaging")

    ctx = holdout.SegmentHoldout(footprint, catalogue,
                                 buffer_px=prereg["fixed_constants"]["holdout_buffer_px"])
    budget_frac = prereg["fixed_constants"]["dot_budget_fraction"]
    spacing = prereg["fixed_constants"]["min_dot_spacing_px"]
    arms = {"A": arm_A, "B": arm_B, "C": arm_C}
    predictions = {}
    holdout_summary = {}
    for name, surface in arms.items():
        preds = []
        for fold in ctx.folds:
            eligible = fold["valid"] & ~fold["visible"] & (surface > 0)
            k = round(budget_frac * int(fold["valid"].sum()))
            preds.append(emission.priority_poisson(surface, eligible, int(k), min_dist=spacing))
        predictions[name] = preds
        holdout_summary[name] = ctx.summarize(preds, ci_draws=prereg["fixed_constants"]["bootstrap_draws"])
        print(f"Arm {name}: HOLDOUT-DTI={holdout_summary[name]['dti']:.6f} "
              f"CI={holdout_summary[name]['ci95']['interval']}", flush=True)

    paired = ctx.compare_paired(predictions["B"], predictions["A"],
                                ci_draws=prereg["fixed_constants"]["bootstrap_draws"],
                                seed=20261027)
    baseline = prereg["gates"]["baseline_holdout_dti_point"]
    primary = holdout_summary["B"]
    efficacy = {
        "baseline_point_dti": baseline,
        "baseline_evaluator": prereg["gates"]["baseline_evaluator"],
        "baseline_withheld_positives": prereg["gates"]["baseline_withheld_positives"],
        "baseline_fold_predictions_available_for_paired_replay": False,
        "candidate_ci_lower_bound_exceeds_baseline_point": bool(primary["ci95"]["interval"][0] > baseline),
        "paired_vs_arm_A": paired,
        "passed": bool(primary["ci95"]["interval"][0] > baseline and paired["ci95_strictly_positive"]),
    }

    registry = json.loads(REGISTRY.read_text())
    entries = registry["entries"]
    surface_novelty = novelty.compare_registry_surfaces(
        {"A": arm_A, "B": arm_B, "C": arm_C}, footprint, entries, ROOT
    )
    save(EVIDENCE / "tasc_surface_novelty_20261027.json", surface_novelty)
    if not surface_novelty["B"]["passed"]:
        raise RuntimeError("surface duplicate STOP before final dot placement")
    print("Surface registry rank gate passed for Arm B", flush=True)

    final = emission.priority_poisson(
        arm_B, footprint & ~catalogue & (arm_B > 0),
        round(budget_frac * int(footprint.sum())), min_dist=spacing
    )
    content_id = submission.scored_content_id(final.astype(np.float32), footprint, catalogue)
    name = f"wbggemsdoe1-tasc-tip-strain-corridor-20261027-{content_id}-zeros.tif"
    artifact = DOWNLOADS / name
    submission.write_submission(final.astype(np.float32), TEMPLATE, artifact, outside="zero")
    zip_path = submission.zip_single(artifact)
    checks = submission.check_variants(artifact, TEMPLATE)
    strict_key = "variant_strict_whole_array_no_nan_allowed"
    if not checks["format_valid"] or not checks["checks"][strict_key]["pass"]:
        raise RuntimeError("exact-file format validation failed")
    note = (f"TASC tip-aligned strain corridor | unique research TIFF | "
            f"DO NOT SUBMIT | id {content_id}")
    if len(note) > 140:
        raise ValueError("submission note exceeds 140 characters")

    final_novelty = novelty.compare_registry(
        final.astype(np.float32), footprint, entries, ROOT, dots=final,
        separate_calibration_controls=True,
    )
    save(EVIDENCE / "tasc_final_novelty_20261027.json", final_novelty)
    literal_rows = final_novelty["rows"]
    literal_pass = bool(literal_rows) and not any(r["literal_duplicate"] for r in literal_rows)
    registry_summary = {
        "surface": {k: {"passed": v["passed"],
                        "max_abs_rank_correlation": v["max_abs_rank_correlation"]}
                    for k, v in surface_novelty.items()},
        "final_dots_literal_unseparated_passed": literal_pass,
        "final_dots_competing_method_passed": final_novelty["competing_method_passed"],
        "competing_method_rasters": final_novelty["competing_method_rasters"],
        "calibration_control_rasters": final_novelty["calibration_control_rasters"],
        "max_abs_rank_correlation": final_novelty["max_abs_rank_correlation"],
        "max_literal_dot_overlap_within_3px": final_novelty["max_dot_overlap"],
        "max_competing_dot_overlap_within_3px": final_novelty["max_competing_dot_overlap"],
        "calibration_control_summary": final_novelty["calibration_control_summary"],
        "rank_limit": 0.90,
        "overlap_limit": 0.70,
        "scope": registry["scope"],
        "decoded_pixel_sha256_unique_among_checked": None,
    }
    decoded = hashlib.sha256(np.ascontiguousarray(
        np.asarray(final[footprint], dtype="<f4")).tobytes()).hexdigest()
    registry_summary["decoded_pixel_sha256_unique_among_checked"] = bool(
        decoded not in {r["footprint_sha256"] for r in entries}
    )
    registry_summary["decoded_pixel_sha256"] = decoded

    projected = lli_projection(artifact, footprint, catalogue)
    verdict = "negative"
    reasons = []
    if not efficacy["passed"]:
        reasons.append("candidate did not beat the frozen current-best holdout benchmark with a 95% CI lower bound above it and a positive paired CI")
    if not literal_pass:
        reasons.append("literal all-entry 3 px overlap gate fails against the retained spacing-5 calibration lattice")
    if not registry_summary["final_dots_competing_method_passed"]:
        reasons.append("competing-method 3 px overlap gate failed")
    reasons.extend(["no assigned method lane was supplied",
                    "no authenticated current weekly allowance or organizer receipt exists",
                    "promotion to a real slot is a separate selector step"])

    run_card = {
        "schema": "gemsdoe1-tasc-run-card-v1",
        "generated_utc": utc(),
        "hypothesis": "TASC: visible-fault-tip-aligned strain-transfer corridors identify concealed continuations absent from the public catalogue.",
        "mechanism": ("Fold-local visible-tip tangent corridor (0-3 km forward, +/-1 km across) multiplied by a "
                      "300 m Gaussian gradient response of geodetic shear/dilatation, gravity, magnetic and "
                      "basement-depth fields; no hidden component, prior prediction or registry raster is an input."),
        "named_non_fault_mimic": "Alluvial-fan channel avulsion lobe, road/rail cut-and-fill, pluvial shoreline bench, intrusive/lithologic contact.",
        "lane": "provisional research only; no assigned single-method paragraph supplied",
        "preregistration": str(PREREG.relative_to(ROOT)),
        "preregistration_sha256": prereg["_frozen_sha256"],
        "hypothesis_document": str(DOC.relative_to(ROOT)),
        "inputs": inputs,
        "input_hashes": {rel: sha256_file(ROOT / rel) for rel in EXPECTED_INPUTS},
        "code_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in (
            Path(__file__), ROOT / "src/gems/holdout.py", ROOT / "src/gems/metric.py",
            ROOT / "src/gems/emission.py", ROOT / "src/gems/novelty.py",
            ROOT / "src/gems/submission.py", PREREG)},
        "leakage_canary": canary,
        "holdout": {name: {"label": "HOLDOUT-DTI", "evaluator_version": s["evaluator_version"],
                           "dti": s["dti"], "ci95": s["ci95"]["interval"],
                           "withheld_positive_pixels": s["n_withheld_positive_pixels"],
                           "representation": "binary 0/1 dots, 3 px minimum spacing, 0.73% fold budget",
                           "tpw": s["TP_w"], "fpw": s["FP_w"], "fnw": s["FN_w"]}
                    for name, s in holdout_summary.items()},
        "efficacy_gate": efficacy,
        "correlation_overlap_vs_registry": registry_summary,
        "leaderboard_estimate": {
            "label": projected["label"],
            "projected_value": projected["projected_value"],
            "approx_interval_pm_1mae": projected["approx_interval_pm_1mae"],
            "evidence_class": "LLI-PROJECTION; USER-REPORTED calibration; NOT an organizer score",
            "organizer_confirmed_submission_score": None,
        },
        "raster_sha256": sha256_file(artifact),
        "zip_sha256": sha256_file(zip_path),
        "decoded_pixel_sha256": decoded,
        "validator_output": checks,
        "submission_name": name,
        "submission_note": note,
        "submission_note_characters": len(note),
        "final_dot_count": int(final.sum()),
        "final_budget": int(round(budget_frac * int(footprint.sum()))),
        "artifact": str(artifact.relative_to(ROOT)),
        "zip_artifact": str(zip_path.relative_to(ROOT)),
        "artifact_role": "newly generated, format-validated, scientifically distinct research TIFF; not a promoted competition submission",
        "decision": {
            "verdict": verdict,
            "ok_to_download": True,
            "ok_to_submit": False,
            "eligible_for_separate_selector": False,
            "approved_for_weekly_slot": False,
            "submission_slots_used": 0,
            "reasons": reasons,
        },
        "verdict": verdict,
        "experiments_completed": 3,
        "submission_slots_used": 0,
        "elapsed_seconds": time.monotonic() - started,
        "next_action": ("Retain the negative result. A future authorized lane needs an independently replayed "
                        "current-best comparator, a resolved registry policy for space-filling calibration "
                        "controls, and untouched confirmation before a separate selector considers a slot."),
    }
    save(RUN_CARD, run_card)
    save(DOCS_CARD, run_card)
    save(EXPERIMENT_RECEIPT, {"generated_utc": utc(), "arms": holdout_summary,
                              "paired": paired, "efficacy": efficacy,
                              "surface_novelty": surface_novelty,
                              "final_novelty": final_novelty,
                              "run_card": str(RUN_CARD.relative_to(ROOT))})
    print(json.dumps({"submission_name": name, "holdout_B": run_card["holdout"]["B"],
                      "literal_pass": literal_pass,
                      "competing_pass": registry_summary["final_dots_competing_method_passed"],
                      "lli_projection": projected["projected_value"],
                      "ok_to_submit": False, "verdict": verdict}, indent=2))
    return run_card


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-features", action="store_true")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    if args.build_features == args.execute:
        ap.error("choose exactly one of --build-features or --execute")
    prereg = json.loads(PREREG.read_text())
    prereg["_frozen_sha256"] = sha256_file(PREREG)
    if args.build_features:
        if FEATURE_RECEIPT.exists():
            raise SystemExit("TASC features already frozen; no retuning or rebuild")
        build_features(prereg)
        return 0
    if RUN_CARD.exists():
        raise SystemExit("TASC run card already frozen; no rerun")
    ledger = {"started_utc": utc(), "hypothesis_id": "TASC", "experiments_started": 3,
              "maximum_experiments": 3, "maximum_wall_hours": 2,
              "preregistration_sha256": prereg["_frozen_sha256"], "status": "running",
              "submission_slots_used": 0}
    save(LEDGER, ledger)
    try:
        card = execute(prereg)
        ledger.update(status="negative_stopped", finished_utc=utc(),
                      experiments_completed=3, elapsed_seconds=card["elapsed_seconds"],
                      raster_sha256=card["raster_sha256"], verdict=card["verdict"])
        save(LEDGER, ledger)
    except Exception as exc:
        ledger.update(status="failed_closed", finished_utc=utc(), error=str(exc))
        save(LEDGER, ledger)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
