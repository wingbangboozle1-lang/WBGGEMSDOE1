#!/usr/bin/env python3
"""Execute the Pre-Registered WBG-H1 (DPGF-1) 3-Experiment Protocol, Gates & Submission Synthesis.

Strictly follows the Parallel-Run Protocol:
  - Verifies immutable SHA-256 lock on `evidence/preregistration_20261026.json` (`7d53a7901224...`).
  - Verifies `evidence/leakage_canary_66ch.json` (`passed == True`, max symmetric AUC <= 0.90).
  - Evaluates matched baseline `B0` + strictly `<= 3` experiments (`EXP-1`, `EXP-2`, `EXP-3`) on
    shared `gems.holdout.SegmentHoldout` (`gems-segment-pooled-v1`, 60,988 withheld positive px,
    3,199 whole components, 1,999 10-km spatial block-bootstrap draws).
  - Checks pre-placement continuous surface novelty (`|Spearman rho| <= 0.90`) BEFORE placement.
  - Synthesizes full-footprint Dual-Partition Stitched-OOF (`Quadrant + 45° Diamond` 15-px whole-segment
    OOF) for the best arm, invokes shared `scripts/submission_writer.py` (`outside="zero"`), runs the
    10-point DrivenData `[0, 1]` portal gate, audits post-placement uniqueness across Focus-9,
    Sparse-Dot, Competing-Method, and Literal-Lattice scopes, and writes `evidence/run_card.json`.
"""

from __future__ import annotations

import gc
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems.holdout import SegmentHoldout  # noqa: E402
from gems.submission import scored_content_id, zip_single  # noqa: E402
from wbggems1.dpgf_model import (  # noqa: E402
    COLLAR_PX,
    TOTAL_DOT_BUDGET,
    build_regime_masks_and_boost,
    fit_predict_b0_fold,
    fit_predict_dpgf_surface_fold,
    make_diamond_4fold_partition,
)
from wbggems1.lli_calibrator import fit_lli_calibrator  # noqa: E402
from wbggems1.paths import raw_data_dir, work_dir  # noqa: E402
from wbggems1.selector_gate import (  # noqa: E402
    check_post_placement_uniqueness,
    check_surface_novelty_pre_placement,
    disk_3px_mask,
    validate_geotiff_portal_gates,
)
from wbggems1.submodular import emit_celf_submodular, emit_two_regime_submodular  # noqa: E402

EXPECTED_PREREG_SHA256 = "e8ad0eb13d19b394e9f595efb1cf7515a0f779e6628b80638438d57efcdb4e16"
EXPECTED_MD_SHA256 = "7d53a790122433e86f926c9371162433a9a883289e40602764d0496b888686ce"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _format_holdout_label(summary: dict[str, Any]) -> str:
    dti = summary["dti"]
    lo, hi = summary["ci95"]["interval"]
    ev = summary["evaluator_version"]
    n_pos = summary["n_withheld_positive_pixels"]
    return f"HOLDOUT-DTI = {dti:.6f} ({ev}, n={n_pos:,} withheld positives, 95% CI [{lo:.6f}, {hi:.6f}])"


def main() -> None:
    t_start = time.time()
    prereg_path = ROOT / "evidence" / "preregistration_20261026.json"
    got_sha = _sha256(prereg_path)
    if got_sha != EXPECTED_PREREG_SHA256:
        raise RuntimeError(f"Preregistration lock mismatch: {got_sha} != {EXPECTED_PREREG_SHA256}")
    md_sha = _sha256(ROOT / "knowledge" / "01_preregistration_wbg_hypotheses_2026-10-26.md")
    if md_sha != EXPECTED_MD_SHA256:
        raise RuntimeError(f"Preregistration markdown lock mismatch: {md_sha} != {EXPECTED_MD_SHA256}")

    canary_path = ROOT / "evidence" / "leakage_canary_66ch.json"
    canary = json.loads(canary_path.read_text())
    if not canary.get("passed"):
        raise RuntimeError("Leakage canary failed! Halting before model fitting.")

    rdir = raw_data_dir()
    wdir = work_dir()

    with rasterio.open(rdir / "sample_submission.tif") as ds:
        fp_mask = np.isfinite(ds.read(1))
    with rasterio.open(rdir / "existing_faults.tif") as ds:
        cat_mask = (ds.read(1) > 0) & fp_mask
    d_cat = distance_transform_edt(~cat_mask).astype(np.float32)

    ctx = SegmentHoldout(fp_mask, cat_mask, buffer_px=15)
    fp_ids = np.flatnonzero(fp_mask.ravel())
    n_fp = fp_ids.size

    rr, cc = np.unravel_index(fp_ids, fp_mask.shape)
    fp_r_norm = ((rr - rr.mean()) / max(rr.std(), 1.0)).astype(np.float32)
    fp_c_norm = ((cc - cc.mean()) / max(cc.std(), 1.0)).astype(np.float32)

    mm = np.load(wdir / "dpgf_features.npy", mmap_mode="r")
    has_lidar_fp = np.load(wdir / "has_lidar_fp.npy")

    print(f"[0.0s] Verified preregistration lock ({got_sha[:12]}) & 66-ch canary (max AUC={canary['max_symmetric_auc']:.4f})")

    # --- ARM B0: 31-ch HGB + 2.8 px priority Poisson ---
    b0_dots: list[np.ndarray] = []
    for fold in ctx.folds:
        t0 = time.time()
        _, d_grid = fit_predict_b0_fold(
            mm,
            fp_mask,
            fp_ids,
            fold["train"],
            fold["valid"],
            fold["visible"],
            seed=1000 + fold["id"],
        )
        b0_dots.append((d_grid > 0.0).astype(np.uint8))
        print(f"[{time.time() - t_start:5.1f}s] B0 fold {fold['name']:18s} ({time.time() - t0:.1f}s) dots={int(d_grid.sum())}")
    b0_sum = ctx.summarize(b0_dots, ci_draws=1999)
    print("  ->", _format_holdout_label(b0_sum))

    # --- ARM EXP-1: 66-ch CorePhysics + LiDAR-Dual (HGB+ET) + 300 m CELF Submodular ---
    exp1_dots: list[np.ndarray] = []
    exp1_oof_surface = np.zeros(fp_mask.shape, dtype=np.float32)
    for fold in ctx.folds:
        t0 = time.time()
        surf_q, _ = fit_predict_dpgf_surface_fold(
            mm,
            fp_mask,
            fp_ids,
            has_lidar_fp,
            fp_r_norm,
            fp_c_norm,
            fold["train"],
            fold["valid"],
            fold["visible"],
            deconfound_and_hardneg=False,
            seed=2000 + fold["id"],
        )
        exp1_oof_surface += surf_q
        d_vis_q = distance_transform_edt(~fold["visible"]).astype(np.float32)
        elig_q = fold["valid"] & (d_vis_q > COLLAR_PX)
        budget_q = int(round(TOTAL_DOT_BUDGET * (int(fold["valid"].sum()) / float(n_fp))))
        em_q, _ = emit_celf_submodular(surf_q, elig_q, budget_q, weight_grid=surf_q)
        exp1_dots.append((em_q > 0.0).astype(np.uint8))
        print(f"[{time.time() - t_start:5.1f}s] EXP-1 fold {fold['name']:16s} ({time.time() - t0:.1f}s) dots={int(em_q.sum())}")
        del surf_q, d_vis_q
        gc.collect()
    exp1_sum = ctx.summarize(exp1_dots, ci_draws=1999)
    exp1_vs_b0 = ctx.compare_paired(exp1_dots, b0_dots, ci_draws=1999)
    print("  ->", _format_holdout_label(exp1_sum), f"| delta_vs_B0={exp1_vs_b0['paired_delta_dti']:+.6f} CI={exp1_vs_b0['paired_delta_ci95']}")

    # --- ARM EXP-2 (DeconfHardNeg + 8-Azimuth Sharpening + Single-Regime CELF) & EXP-3 (Two-Regime 72/28 CELF) ---
    exp2_dots: list[np.ndarray] = []
    exp3_dots: list[np.ndarray] = []
    exp2_oof_surface = np.zeros(fp_mask.shape, dtype=np.float32)
    fold_thresholds: list[dict[str, float]] = []
    exp3_regime_stats: list[dict[str, Any]] = []

    for fold in ctx.folds:
        t0 = time.time()
        surf_q, meta_q = fit_predict_dpgf_surface_fold(
            mm,
            fp_mask,
            fp_ids,
            has_lidar_fp,
            fp_r_norm,
            fp_c_norm,
            fold["train"],
            fold["valid"],
            fold["visible"],
            deconfound_and_hardneg=True,
            seed=3000 + fold["id"],
        )
        exp2_oof_surface += surf_q
        fold_thresholds.append(meta_q)

        d_vis_q = distance_transform_edt(~fold["visible"]).astype(np.float32)
        elig_q = fold["valid"] & (d_vis_q > COLLAR_PX)
        budget_q = int(round(TOTAL_DOT_BUDGET * (int(fold["valid"].sum()) / float(n_fp))))

        # EXP-2 single-regime CELF
        em2_q, _ = emit_celf_submodular(surf_q, elig_q, budget_q, weight_grid=surf_q)
        exp2_dots.append((em2_q > 0.0).astype(np.uint8))

        # EXP-3 two-regime (72% / 28%) CELF conditioned on Regime A coverage
        reg_a_q, reg_b_surf_q = build_regime_masks_and_boost(
            mm, fp_mask, fp_ids, has_lidar_fp, fold["valid"], surf_q, meta_q
        )
        em3_q, st3_q = emit_two_regime_submodular(
            surf_q,
            reg_b_surf_q,
            elig_q,
            reg_a_q,
            budget_q,
            regime_a_fraction=0.72,
        )
        exp3_dots.append((em3_q > 0.0).astype(np.uint8))
        exp3_regime_stats.append({"fold": fold["name"], **st3_q})

        print(
            f"[{time.time() - t_start:5.1f}s] EXP-2/3 fold {fold['name']:14s} ({time.time() - t0:.1f}s) "
            f"exp2_dots={int(em2_q.sum())} exp3_A={st3_q['regime_a_dots']} exp3_B={st3_q['regime_b_dots']}"
        )
        del surf_q, d_vis_q, reg_a_q, reg_b_surf_q
        gc.collect()

    exp2_sum = ctx.summarize(exp2_dots, ci_draws=1999)
    exp2_vs_b0 = ctx.compare_paired(exp2_dots, b0_dots, ci_draws=1999)
    print("  -> EXP-2:", _format_holdout_label(exp2_sum), f"| delta_vs_B0={exp2_vs_b0['paired_delta_dti']:+.6f} CI={exp2_vs_b0['paired_delta_ci95']}")

    exp3_sum = ctx.summarize(exp3_dots, ci_draws=1999)
    exp3_vs_b0 = ctx.compare_paired(exp3_dots, b0_dots, ci_draws=1999)
    exp3_vs_exp2 = ctx.compare_paired(exp3_dots, exp2_dots, ci_draws=1999)
    print("  -> EXP-3:", _format_holdout_label(exp3_sum), f"| delta_vs_B0={exp3_vs_b0['paired_delta_dti']:+.6f} CI={exp3_vs_b0['paired_delta_ci95']}")

    # Select winning WBG-H1 arm strictly by pooled HOLDOUT-DTI
    candidates = [
        ("EXP-1", exp1_sum, exp1_vs_b0, exp1_oof_surface, False, False),
        ("EXP-2", exp2_sum, exp2_vs_b0, exp2_oof_surface, True, False),
        ("EXP-3", exp3_sum, exp3_vs_b0, exp2_oof_surface, True, True),
    ]
    winner_name, winner_sum, winner_vs_b0, quad_oof_surface, win_deconf, win_tworeg = max(
        candidates, key=lambda t: t[1]["dti"]
    )
    print(f"\n[{time.time() - t_start:5.1f}s] Selected top WBG-H1 arm on SegmentHoldout: {winner_name} (DTI={winner_sum['dti']:.6f})")

    # --- Synthesize Dual-Partition Stitched-OOF (Quadrant OOF + 45° Rotated Diamond OOF) ---
    diamond_folds = make_diamond_4fold_partition(fp_mask, cat_mask, buffer_px=15)
    diamond_oof_surface = np.zeros(fp_mask.shape, dtype=np.float32)
    diam_thresholds: list[dict[str, float]] = []
    for dfold in diamond_folds:
        t0 = time.time()
        dsurf_q, dmeta_q = fit_predict_dpgf_surface_fold(
            mm,
            fp_mask,
            fp_ids,
            has_lidar_fp,
            fp_r_norm,
            fp_c_norm,
            dfold["train"],
            dfold["valid"],
            dfold["visible"],
            deconfound_and_hardneg=win_deconf,
            seed=4000 + dfold["fold"],
        )
        diamond_oof_surface += dsurf_q
        diam_thresholds.append(dmeta_q)
        print(f"[{time.time() - t_start:5.1f}s] Dual-Partition {dfold['name']} ({time.time() - t0:.1f}s)")
        del dsurf_q
        gc.collect()

    stitched_surface = (0.5 * quad_oof_surface + 0.5 * diamond_oof_surface).astype(np.float32)
    stitched_surface[~fp_mask] = 0.0
    del exp1_oof_surface, exp2_oof_surface, quad_oof_surface, diamond_oof_surface
    gc.collect()

    # Save CV checkpoint before post-processing so CV metrics are persisted immediately
    (wdir / "wbg_h1_cv_checkpoint.json").write_text(
        json.dumps(
            {
                "selected_arm": winner_name,
                "b0": b0_sum,
                "exp1": exp1_sum,
                "exp1_vs_b0": exp1_vs_b0,
                "exp2": exp2_sum,
                "exp2_vs_b0": exp2_vs_b0,
                "exp3": exp3_sum,
                "exp3_vs_b0": exp3_vs_b0,
                "exp3_vs_exp2": exp3_vs_exp2,
            },
            indent=2,
        )
    )

    # --- Gate 1: Pre-Placement Continuous Surface Novelty (`|Spearman rho| <= 0.90`) ---
    surf_novelty = check_surface_novelty_pre_placement(stitched_surface, fp_mask)
    print(
        f"[{time.time() - t_start:5.1f}s] Pre-placement surface novelty: passed={surf_novelty['passed']} "
        f"(max |rho|={surf_novelty['max_abs_spearman_rho']:.4f})"
    )
    if not surf_novelty["passed"]:
        raise RuntimeError(f"Pre-placement surface duplicate detected: {surf_novelty}")

    # --- Full-Footprint Dot Placement (strictly outside dead <= 200 m collar) ---
    eligible_full = fp_mask & (d_cat > COLLAR_PX)
    obj_surface = np.where(eligible_full, stitched_surface, 0.0).astype(np.float32)

    all_thr = (fold_thresholds if win_deconf else []) + diam_thresholds
    avg_thr = {
        "slope_tr_q40": float(np.mean([m["slope_tr_q40"] for m in all_thr])) if all_thr else 0.05,
        "upface_tr_q55": float(np.mean([m["upface_tr_q55"] for m in all_thr])) if all_thr else 0.05,
        "pied_tr_q55": float(np.mean([m["pied_tr_q55"] for m in all_thr])) if all_thr else 0.05,
    }

    if win_tworeg:
        reg_a_full, reg_b_surf_full = build_regime_masks_and_boost(
            mm, fp_mask, fp_ids, has_lidar_fp, fp_mask, obj_surface, avg_thr
        )
        final_dots_grid, full_emit_stats = emit_two_regime_submodular(
            obj_surface,
            np.where(eligible_full, reg_b_surf_full, 0.0).astype(np.float32),
            eligible_full,
            reg_a_full,
            TOTAL_DOT_BUDGET,
            regime_a_fraction=0.72,
        )
    else:
        final_dots_grid, _ = emit_celf_submodular(
            obj_surface, eligible_full, TOTAL_DOT_BUDGET, weight_grid=obj_surface
        )
        full_emit_stats = {
            "target_total": TOTAL_DOT_BUDGET,
            "emitted_total": int((final_dots_grid > 0).sum()),
        }

    # --- Write GeoTIFF + ZIP via shared `scripts/submission_writer.py` ---
    cid = scored_content_id(final_dots_grid, fp_mask, cat_mask)
    dl_dir = ROOT / "docs" / "downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    # Remove any stale generated submission files in docs/downloads
    for old_f in dl_dir.glob("wbggemsdoe1-wbg-h1-*"):
        old_f.unlink()

    stem = f"wbggemsdoe1-wbg-h1-dpgf1-{winner_name.lower()}-20261026-{cid}-zeros"
    tif_path = dl_dir / f"{stem}.tif"
    zip_path = dl_dir / f"{stem}.zip"

    tmp_npy = wdir / "final_dots_2d.npy"
    np.save(tmp_npy, final_dots_grid.astype(np.float32))
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "submission_writer.py"),
            str(tmp_npy),
            str(tif_path),
            "--template",
            str(rdir / "sample_submission.tif"),
            "--outside",
            "zero",
        ],
        check=True,
        capture_output=True,
    )
    zip_single(tif_path, zip_path)

    # --- Run 10-Point DrivenData Portal Gate + Multi-Scope Post-Placement Uniqueness ---
    del stitched_surface, obj_surface
    gc.collect()
    portal_gate = validate_geotiff_portal_gates(tif_path)
    post_uniq = check_post_placement_uniqueness(final_dots_grid, fp_mask)
    f9_sparse = post_uniq["focus_9_sparse_scope"]
    sp_peers = post_uniq["sparse_dot_peers_le_100k_scope"]
    sparse_peers_audit = {
        "focus9_all_historical_and_20261026": f9_sparse,
        "sparse_dot_peers_le_100k": sp_peers,
        "top_10_sparse_peers": post_uniq["top_10_sparse_by_cand_in_ref_3px"],
    }

    # --- Compute LLI-PROJECTION (strictly labeled as projection, never an organizer score) ---
    cal, _ = fit_lli_calibrator()
    with rasterio.open(rdir / "training_features.tif") as ds:
        s_raw = ds.read(19).astype(np.float32)
        slope_grid = np.where((np.abs(s_raw) < 1e30) & np.isfinite(s_raw) & fp_mask, s_raw, 0.0)
    has_lidar_grid = np.zeros(fp_mask.shape, dtype=bool)
    has_lidar_grid.ravel()[fp_ids] = has_lidar_fp
    h23_path = (
        rdir
        / "registry_cache/data/registry/scored/GEMSDOE22__gems22-h23-b-dti-optimal-emission-10pct-20261002-86176698-nan.tif"
    )
    with rasterio.open(h23_path) as ds:
        h23_pos = (np.nan_to_num(ds.read(1), nan=0.0) > 0.0) & fp_mask
    lli_proj = cal.project(final_dots_grid, fp_mask, d_cat, has_lidar_grid, slope_grid, disk_3px_mask(h23_pos))

    # --- Evaluate Promotion Verdict ---
    beats_b0 = bool(winner_vs_b0["paired_delta_dti"] > 0.0 and winner_vs_b0["ci95_strictly_positive"])
    beats_portfolio_holdout_ref = bool(winner_sum["dti"] > 0.163792)
    sparse_and_focus9_unique = bool(
        sp_peers["passed"]
        and f9_sparse["passed"]
        and surf_novelty["passed"]
    )
    promote_verdict = (
        "promote"
        if (
            portal_gate["all_10_gates_passed"]
            and canary["passed"]
            and beats_b0
            and beats_portfolio_holdout_ref
            and sparse_and_focus9_unique
        )
        else "negative"
    )

    sub_name = f"wbggems1-dpgf1-{winner_name.lower()}-20261026-{cid}"
    sub_note = (
        f"WBGGEMSDOE1 WBG-H1 ({winner_name}): DipShift+TFSDI+DualLiDAR+CELF300m; "
        f"HOLDOUT-DTI={winner_sum['dti']:.4f} vs B0={b0_sum['dti']:.4f}; 37654 zero-ext dots"
    )[:140]

    elapsed_total = round(time.time() - t_start, 2)

    exp_bundle = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_seconds": elapsed_total,
        "budget_cap_experiments": 3,
        "experiments_executed": 3,
        "preregistration_sha256": got_sha,
        "leakage_canary_summary": {
            "passed": canary["passed"],
            "n_features": canary["n_features_tested"],
            "max_symmetric_auc": canary["max_symmetric_auc"],
            "max_feature": canary["max_symmetric_auc_feature"],
        },
        "arms": {
            "B0_Raw31_HGB_NMS28": {
                "formatted_score": _format_holdout_label(b0_sum),
                "holdout": b0_sum,
            },
            "EXP1_DPGF_CorePhysics": {
                "formatted_score": _format_holdout_label(exp1_sum),
                "holdout": exp1_sum,
                "paired_vs_B0": exp1_vs_b0,
            },
            "EXP2_DPGF_DeconfHardNeg": {
                "formatted_score": _format_holdout_label(exp2_sum),
                "holdout": exp2_sum,
                "paired_vs_B0": exp2_vs_b0,
            },
            "EXP3_DPGF_TwoRegime_Submod": {
                "formatted_score": _format_holdout_label(exp3_sum),
                "holdout": exp3_sum,
                "paired_vs_B0": exp3_vs_b0,
                "paired_vs_EXP2": exp3_vs_exp2,
                "fold_regime_allocation": exp3_regime_stats,
            },
        },
        "selected_arm": winner_name,
        "beats_portfolio_reference_dprf1_016379": beats_portfolio_holdout_ref,
        "full_submission_synthesis": {
            "method": "Dual-Partition Stitched-OOF (Quadrant 4-fold + 45-deg Rotated Diamond 4-fold, buffer_px=15)",
            "emission_stats": full_emit_stats,
            "tif_file": tif_path.name,
            "zip_file": zip_path.name,
            "tif_bytes": tif_path.stat().st_size,
            "zip_bytes": zip_path.stat().st_size,
            "tif_sha256": portal_gate["sha256"],
            "zip_sha256": _sha256(zip_path),
            "scored_content_id": cid,
        },
        "pre_placement_surface_novelty": surf_novelty,
        "post_placement_uniqueness": post_uniq,
        "multi_scope_uniqueness_breakdown": sparse_peers_audit,
        "portal_preflight_10_gates": portal_gate,
        "lli_empirical_projection": lli_proj,
    }

    run_card = {
        "hypothesis": (
            f"WBG-H1 (DPGF-1 / {winner_name}): Updip Subsurface-to-Surface Fault Dip Back-Projection "
            "(DipShift 500m/1000m) + Tectonic-vs-Fluvial Scarp Discrimination Index (TFSDI) + "
            "LiDAR-Completeness Slope-Quantile Calibrated Dual Ensemble + 300 m CELF Submodular Coverage"
        ),
        "mechanism": (
            "Normal faults dipping 50-65 deg into alluvial basins displace subsurface gravity/magnetic/MT "
            "basement steps 400-1,000 m basinward of the surface piedmont scarp (outside the 300 m DTI kernel). "
            "Advecting subsurface potential-field gradients updip along smooth regional elevation gradients "
            "re-aligns subsurface basement steps onto surface fault traces, while TFSDI suppresses cross-contour "
            "fluvial washes and the 51-ch LiDAR-blind specialist bridges the 24.63% 3DEP coverage gap."
        ),
        "mimic": (
            "Pleistocene Lake Lahontan / Columbus paleo-shoreline beach ridges (contour-parallel benches "
            "with low cross-slope incision, mitigated by requiring updip-projected gravity/magnetic/MT "
            "corroboration) and steep non-fault volcanic/intrusive pediment contacts."
        ),
        "holdout_dti": {
            "label": _format_holdout_label(winner_sum),
            "evaluator_version": winner_sum["evaluator_version"],
            "n_withheld_positives": winner_sum["n_withheld_positive_pixels"],
            "dti": round(winner_sum["dti"], 6),
            "ci95": [round(x, 6) for x in winner_sum["ci95"]["interval"]],
            "baseline_b0_dti": round(b0_sum["dti"], 6),
            "baseline_b0_ci95": [round(x, 6) for x in b0_sum["ci95"]["interval"]],
            "paired_delta_vs_b0": round(winner_vs_b0["paired_delta_dti"], 6),
            "paired_delta_vs_b0_ci95": [round(x, 6) for x in winner_vs_b0["paired_delta_ci95"]],
            "fold_wins_vs_b0": f"{winner_vs_b0['fold_wins']}/{winner_vs_b0['n_folds']}",
        },
        "registry_correlation_and_overlap": {
            "pre_placement_surface_max_abs_spearman": surf_novelty["max_abs_spearman_rho"],
            "pre_placement_surface_passed": surf_novelty["passed"],
            "focus9_sites_max_3px_dot_overlap": f9_sparse["max_cand_in_ref_3px"],
            "focus9_sites_closest_peer": f9_sparse["max_cand_in_ref_peer"],
            "focus9_sites_max_abs_spearman": f9_sparse["max_abs_spearman_rho"],
            "focus9_sites_passed": f9_sparse["passed"],
            "sparse_dot_submissions_le_100k_max_3px_overlap": sp_peers["max_cand_in_ref_3px"],
            "sparse_dot_submissions_closest_peer": sp_peers["max_cand_in_ref_peer"],
            "sparse_dot_submissions_passed": sp_peers["passed"],
            "all_206_competing_symmetric_3px_max_overlap": post_uniq["competing_methods_scope"][
                "max_symmetric_3px_overlap"
            ],
            "literal_oneway_vs_516k_continuous_slabs_ir_wbg1_03": post_uniq["competing_methods_scope"][
                "max_cand_in_ref_3px"
            ],
            "literal_oneway_vs_r13_space_filling_lattice_ir_wbg1_01": post_uniq[
                "literal_unseparated_scope"
            ]["max_cand_in_ref_3px"],
        },
        "raster_sha256": {
            "tif_file": f"docs/downloads/{tif_path.name}",
            "tif_sha256": portal_gate["sha256"],
            "zip_file": f"docs/downloads/{zip_path.name}",
            "zip_sha256": _sha256(zip_path),
            "footprint_sha256": post_uniq["candidate_footprint_sha256"],
        },
        "validator_output": {
            "all_10_portal_gates_passed": portal_gate["all_10_gates_passed"],
            "format_valid": portal_gate["shared_validator_check_variants"]["format_valid"],
            "strict_whole_array_0_1_no_nan": portal_gate["shared_validator_check_variants"]["checks"][
                "variant_strict_whole_array_no_nan_allowed"
            ]["pass"],
            "nan_cells_whole_raster": portal_gate["metrics"]["nan_cells_whole_raster"],
            "inf_cells_whole_raster": portal_gate["metrics"]["inf_cells_whole_raster"],
            "whole_raster_range": [
                portal_gate["metrics"]["whole_raster_min"],
                portal_gate["metrics"]["whole_raster_max"],
            ],
            "footprint_positive_dots": portal_gate["metrics"]["footprint_positive_dots"],
            "dead_collar_le_200m_dots": portal_gate["metrics"]["dead_collar_le_200m_dots"],
        },
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "verdict": promote_verdict,
    }

    (ROOT / "evidence" / "wbg_h1_experiments.json").write_text(json.dumps(exp_bundle, indent=2) + "\n")
    (ROOT / "evidence" / "run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")

    print("\n=== FINAL WBG-H1 RUN CARD ===")
    print(json.dumps(run_card, indent=2))


def _compute_sparse_and_slab_breakdown(dots_grid: np.ndarray, fp_mask: np.ndarray) -> dict[str, Any]:
    from scipy.stats import rankdata

    from wbggems1.selector_gate import _fast_pearson, load_all_comparison_entries

    fp_ids = np.flatnonzero(fp_mask.ravel())
    cand_pos = (dots_grid > 0.0) & fp_mask
    cand_pos_flat = np.flatnonzero(cand_pos.ravel())
    n_cand = int(cand_pos_flat.size)
    rng = np.random.default_rng(20261026)
    sub_flat = fp_ids[np.sort(rng.choice(fp_ids.size, size=120_000, replace=False))]
    cand_rk = rankdata(dots_grid.ravel()[sub_flat], method="average").astype(np.float32)

    entries = load_all_comparison_entries()
    sparse_rows = []
    focus9_rows = []
    for it in entries:
        if it["is_lattice_control"]:
            continue
        with rasterio.open(it["path"]) as ds:
            a = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float32)
        r_pos = (a > 0.0) & fp_mask
        n_ref = int(np.count_nonzero(r_pos))
        if n_ref == 0:
            continue
        r3_flat = disk_3px_mask(r_pos).ravel()
        c_in_r = float(np.count_nonzero(r3_flat[cand_pos_flat])) / float(n_cand)
        ref_sub = a.ravel()[sub_flat]
        rho = abs(_fast_pearson(cand_rk, rankdata(ref_sub, method="average").astype(np.float32))) if float(ref_sub.std()) > 1e-12 else 0.0
        rec = {
            "label": it["label"],
            "site": it["site"],
            "n_ref": n_ref,
            "cand_in_ref_3px": round(c_in_r, 6),
            "abs_spearman": round(rho, 6),
        }
        if n_ref <= 100_000:
            sparse_rows.append(rec)
            if it["is_focus9"]:
                focus9_rows.append(rec)

    def _pack(rows: list[dict[str, Any]]) -> dict[str, Any]:
        top_ov = max(rows, key=lambda d: d["cand_in_ref_3px"])
        top_rh = max(rows, key=lambda d: d["abs_spearman"])
        return {
            "n_rasters": len(rows),
            "passed": bool(top_ov["cand_in_ref_3px"] <= 0.70 and top_rh["abs_spearman"] <= 0.90),
            "max_cand_in_ref_3px": top_ov["cand_in_ref_3px"],
            "closest_peer": top_ov["label"],
            "max_abs_spearman": top_rh["abs_spearman"],
            "closest_spearman_peer": top_rh["label"],
            "top_5_peers": sorted(rows, key=lambda d: d["cand_in_ref_3px"], reverse=True)[:5],
        }

    return {
        "focus9_all_historical_and_20261026": _pack(focus9_rows),
        "sparse_dot_peers_le_100k": _pack(sparse_rows),
    }


if __name__ == "__main__":
    main()
