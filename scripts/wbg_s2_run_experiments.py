#!/usr/bin/env python3
"""Execute the frozen WBG-S2 (`MKSF-1`) 3-experiment suite across both holdout evaluators,
check pre-placement & post-placement novelty across 360+ registry/peer rasters, and emit
the validated `[0, 1]` GeoTIFF + One-TIFF ZIP + canonical JSON Run Card.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata

from gems.holdout import SegmentHoldout
from gems57 import evaluate_holdout as g57_eval
from gems57 import grid as g57_grid
from gems57 import holdout as g57_holdout
from gems57 import submission_writer as g57_writer
from gems57 import uniqueness as g57_uniqueness
from wbggems.audit import dump_json, promotion_decision, sha256, utc_now
from wbggems1.dpgf_model import make_diamond_4fold_partition
from wbggems1.selector_gate import disk_3px_mask, exact_spearman_footprint
from wbggems2.features import DATA_DIR, WORK_DIR
from wbggems2.mksf_model import (
    COLLAR_PX,
    TOTAL_DOT_BUDGET,
    apply_coulomb_corroboration,
    emit_two_regime_mksf_dots,
    fit_predict_b0_celf28_fold,
    fit_predict_mksf_dual_fold,
)


def _crop_eval_g57(prediction: np.ndarray, fold: dict[str, Any], footprint: np.ndarray) -> tuple[dict[str, Any], np.ndarray]:
    y, x = np.nonzero(fold["region"])
    ys = slice(max(0, int(y.min()) - 4), min(footprint.shape[0], int(y.max()) + 5))
    xs = slice(max(0, int(x.min()) - 4), min(footprint.shape[1], int(x.max()) + 5))
    cropped = {k: np.asarray(fold[k])[ys, xs] for k in ("region", "visible", "masked_known", "truth")}
    return g57_eval.evaluate(
        np.asarray(prediction[ys, xs], dtype=np.float32),
        cropped,
        footprint[ys, xs],
        origin=(ys.start, xs.start),
        global_shape=footprint.shape,
    )


def _collect_peer_and_registry_paths() -> list[dict[str, Any]]:
    """Collect all 360 frozen focus_inventory rasters + 15 latest 2026-10-27 peer TIFFs + local downloads."""
    entries: list[dict[str, Any]] = []
    seen_sha: set[str] = set()

    focus_inv = json.loads((ROOT / "registry" / "focus_inventory.json").read_text())
    for r in focus_inv["rasters"]:
        p = ROOT / r["cache_file"]
        if p.exists():
            seen_sha.add(r["sha256"])
            low = p.name.lower()
            is_lattice = ("r13-lattice-s5" in low) or ("r13-lattice-s6" in low)
            entries.append(
                {
                    "id": r.get("submission") or p.stem,
                    "site": r.get("site") or "REGISTRY",
                    "path": p,
                    "sha256": r["sha256"],
                    "source": "frozen_focus_inventory_360",
                    "is_lattice_control": is_lattice,
                    "is_latest_20261027_peer": False,
                }
            )

    peer_dir = DATA_DIR / "wbg_s2_peers"
    if peer_dir.exists():
        for p in sorted(peer_dir.glob("*.tif")):
            s = sha256(p)
            site_lbl = p.name.split("__", 1)[0]
            entries.append(
                {
                    "id": p.stem,
                    "site": site_lbl,
                    "path": p,
                    "sha256": s,
                    "source": "latest_20261027_peer",
                    "is_lattice_control": False,
                    "is_latest_20261027_peer": True,
                }
            )
            seen_sha.add(s)

    for p in sorted((ROOT / "docs" / "downloads").glob("*.tif")):
        s = sha256(p)
        if s not in seen_sha:
            seen_sha.add(s)
            entries.append(
                {
                    "id": p.stem,
                    "site": "WBGGEMSDOE1_PRIOR",
                    "path": p,
                    "sha256": s,
                    "source": "local_prior_lane",
                    "is_lattice_control": False,
                    "is_latest_20261027_peer": True,
                }
            )
    return entries


def _audit_pre_placement_surface(
    surface_grid: np.ndarray,
    fp_mask: np.ndarray,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    fp_ids = np.flatnonzero(fp_mask.ravel())
    rng = np.random.default_rng(20261027)
    sub_idx = np.sort(rng.choice(fp_ids.size, size=200_000, replace=False))
    sub_flat = fp_ids[sub_idx]

    cand_full = np.nan_to_num(surface_grid.ravel()[fp_ids], nan=0.0).astype(np.float32)
    cand_sub_rank = rankdata(cand_full[sub_idx], method="average")

    coarse: list[tuple[float, dict[str, Any]]] = []
    checked = 0
    for item in entries:
        try:
            with rasterio.open(item["path"]) as ds:
                if ds.count != 1 or ds.shape != fp_mask.shape:
                    continue
                arr = ds.read(1).ravel()[sub_flat].astype(np.float32)
        except Exception:
            continue
        arr = np.where(np.isfinite(arr) & (np.abs(arr) < 1e20), arr, 0.0)
        if float(np.ptp(arr)) == 0.0:
            continue
        checked += 1
        # Fast Spearman on 200k subsample
        r_ref = rankdata(arr, method="average")
        c0 = cand_sub_rank - cand_sub_rank.mean()
        r0 = r_ref - r_ref.mean()
        denom = float(np.linalg.norm(c0) * np.linalg.norm(r0))
        rho_sub = float(np.dot(c0, r0) / denom) if denom > 1e-12 else 0.0
        coarse.append((abs(rho_sub), {**item, "rho_sub": rho_sub}))

    coarse.sort(key=lambda x: x[0], reverse=True)
    # Exact full-footprint Spearman on top 25 closest rasters
    top_exact = []
    for _, item in coarse[:25]:
        with rasterio.open(item["path"]) as ds:
            ref_full = ds.read(1).ravel()[fp_ids].astype(np.float32)
        ref_full = np.where(np.isfinite(ref_full) & (np.abs(ref_full) < 1e20), ref_full, 0.0)
        rho = exact_spearman_footprint(cand_full, ref_full)
        top_exact.append(
            {
                "id": item["id"],
                "site": item["site"],
                "source": item["source"],
                "sha256": item["sha256"],
                "spearman_rho": rho,
                "abs_spearman_rho": abs(rho),
            }
        )
    top_exact.sort(key=lambda x: x["abs_spearman_rho"], reverse=True)
    worst = top_exact[0] if top_exact else {"abs_spearman_rho": 0.0, "spearman_rho": 0.0, "id": None}
    return {
        "phase": "pre_placement_continuous_surface",
        "rasters_checked": checked,
        "spearman_ceiling": 0.90,
        "max_abs_spearman_rho": float(worst["abs_spearman_rho"]),
        "max_signed_spearman_rho": float(worst["spearman_rho"]),
        "closest_peer": worst.get("id"),
        "passed": bool(worst["abs_spearman_rho"] <= 0.90),
        "top_10_by_abs_spearman": top_exact[:10],
    }


def _audit_post_placement_dots(
    cand_tif: Path,
    cand_dots_bool: np.ndarray,
    fp_mask: np.ndarray,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    fp_ids = np.flatnonzero(fp_mask.ravel())
    cand_fp = cand_dots_bool.ravel()[fp_ids].astype(np.float32)
    cand_3px = disk_3px_mask(cand_dots_bool)
    n_cand = int(cand_dots_bool.sum())
    cand_sha = sha256(cand_tif)

    rows = []
    for item in entries:
        if item["sha256"] == cand_sha:
            continue
        try:
            with rasterio.open(item["path"]) as ds:
                if ds.count != 1 or ds.shape != fp_mask.shape:
                    continue
                raw = ds.read(1)
        except Exception:
            continue
        clean = np.where(np.isfinite(raw) & (np.abs(raw) < 1e20) & fp_mask, raw, 0.0).astype(np.float32)
        ref_pos = (clean > 0.0) & fp_mask
        n_ref = int(ref_pos.sum())
        if n_ref == 0:
            continue
        ref_3px = disk_3px_mask(ref_pos)
        fwd_3px = float(np.count_nonzero(cand_dots_bool & ref_3px)) / float(n_cand)
        rev_3px = float(np.count_nonzero(ref_pos & cand_3px)) / float(n_ref)
        sym_3px = 0.5 * (fwd_3px + rev_3px)
        rho = exact_spearman_footprint(cand_fp, clean.ravel()[fp_ids])

        rows.append(
            {
                "id": item["id"],
                "site": item["site"],
                "source": item["source"],
                "sha256": item["sha256"],
                "positive_pixels": n_ref,
                "is_sparse_competing_le_100k": bool((n_ref <= 100_000) and (not item["is_lattice_control"])),
                "is_lattice_control": bool(item["is_lattice_control"]),
                "is_latest_20261027_peer": bool(item["is_latest_20261027_peer"]),
                "forward_3px_overlap": fwd_3px,
                "reverse_3px_overlap": rev_3px,
                "symmetric_3px_overlap": sym_3px,
                "worst_directional_3px": max(fwd_3px, rev_3px),
                "spearman_rho": rho,
                "abs_spearman_rho": abs(rho),
            }
        )

    sparse_peers = [r for r in rows if r["is_sparse_competing_le_100k"]]
    latest_peers = [r for r in rows if r["is_latest_20261027_peer"] and r["positive_pixels"] <= 100_000]
    non_lattice = [r for r in rows if not r["is_lattice_control"]]

    worst_sparse_fwd = max(sparse_peers, key=lambda r: r["forward_3px_overlap"])
    worst_sparse_dir = max(sparse_peers, key=lambda r: r["worst_directional_3px"])
    worst_sparse_rho = max(sparse_peers, key=lambda r: r["abs_spearman_rho"])
    worst_sym_all = max(non_lattice, key=lambda r: r["symmetric_3px_overlap"])
    worst_literal_all = max(rows, key=lambda r: r["forward_3px_overlap"])

    # Also invoke unchanged shared `vendor/gems57/uniqueness.py` on `registry/focus_inventory.json`
    with rasterio.open(DATA_DIR / "sample_submission.tif") as src:
        ref_grid = (src.shape, src.crs, src.transform)
    focus_index = json.loads((ROOT / "registry" / "focus_inventory.json").read_text())
    for r in focus_index["rasters"]:
        p = Path(r["cache_file"])
        if not p.is_absolute():
            r["cache_file"] = str(ROOT / p)
    literal_g57 = g57_uniqueness.compare_to_registry(
        cand_tif, focus_index, fp_mask, expected_grid=ref_grid, include_reverse=True
    )

    return {
        "phase": "post_placement_final_dots",
        "total_rasters_compared": len(rows),
        "sparse_competing_rasters_checked": len(sparse_peers),
        "competing_sparse_gate": {
            "passed": bool(
                worst_sparse_fwd["forward_3px_overlap"] <= 0.70
                and worst_sparse_dir["worst_directional_3px"] <= 0.70
                and worst_sparse_rho["abs_spearman_rho"] <= 0.90
            ),
            "max_forward_3px_overlap": worst_sparse_fwd["forward_3px_overlap"],
            "closest_forward_peer": worst_sparse_fwd["id"],
            "max_worst_directional_3px_overlap": worst_sparse_dir["worst_directional_3px"],
            "closest_directional_peer": worst_sparse_dir["id"],
            "max_abs_spearman_rho": worst_sparse_rho["abs_spearman_rho"],
            "closest_spearman_peer": worst_sparse_rho["id"],
        },
        "non_lattice_symmetric_gate": {
            "passed": bool(worst_sym_all["symmetric_3px_overlap"] <= 0.70),
            "max_symmetric_3px_overlap": worst_sym_all["symmetric_3px_overlap"],
            "closest_symmetric_peer": worst_sym_all["id"],
        },
        "latest_20261027_peers_table": sorted(
            latest_peers, key=lambda r: r["forward_3px_overlap"], reverse=True
        ),
        "top_10_sparse_peers_by_forward_3px": sorted(
            sparse_peers, key=lambda r: r["forward_3px_overlap"], reverse=True
        )[:10],
        "literal_unseparated_gems57_gate": {
            "unique_without_lattice_or_density_exemption": bool(literal_g57["unique"]),
            "byte_unique_among_checked": bool(literal_g57["byte_unique_among_checked"]),
            "pixel_unique_among_checked": bool(literal_g57["pixel_unique_among_checked"]),
            "registry_rasters_checked": int(literal_g57["registry_rasters_checked"]),
            "max_spearman_full_footprint": float(literal_g57["worst_spearman_full_footprint"]),
            "max_forward_3px_including_lattice_and_slabs": float(literal_g57["worst_dot_overlap"]),
            "worst_literal_peer": worst_literal_all["id"],
            "note": (
                "13GEMSDOE r13-lattice-s5 (206,895 dots on 5-px grid) covers 99.8713% of footprint within 3 px, "
                "forcing >=82.34% forward overlap for any 37,654-dot in-footprint candidate. No private exemption applied."
            ),
        },
    }


def main() -> None:
    t0 = time.monotonic()
    prereg_path = ROOT / "registry" / "wbg_s2" / "preregistration.json"
    prereg = json.loads(prereg_path.read_text())
    prereg_sha = sha256(prereg_path)

    canary_path = ROOT / "evidence" / "wbg_s2" / "leakage_canary_81ch.json"
    canary = json.loads(canary_path.read_text())
    if not canary.get("passed"):
        raise RuntimeError("Leakage canary did not pass; aborting experiment suite.")

    with rasterio.open(DATA_DIR / "sample_submission.tif") as ds:
        fp_mask = np.isfinite(ds.read(1))
    with rasterio.open(DATA_DIR / "existing_faults.tif") as ds:
        cat_mask = (ds.read(1) > 0) & fp_mask
    with rasterio.open(DATA_DIR / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc_mask = (ds.read(1) > 0) & fp_mask

    fp_ids = np.flatnonzero(fp_mask.ravel())
    n_fp = int(fp_ids.size)
    mm = np.load(WORK_DIR / "mksf_features_81ch.npy", mmap_mode="r")
    lid_valid_fp = np.load(WORK_DIR / "lid_valid_fp.npy")
    ckpt_dir = WORK_DIR / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # PART 1: Evaluate B0, EXP-1, EXP-2, EXP-3 on `gems-segment-pooled-v1` (n=60,988)
    # =========================================================================
    print("=== [PART 1] Evaluating B0, EXP-1, EXP-2, EXP-3 on gems-segment-pooled-v1 (n=60,988) ===", flush=True)
    seg_ctx = SegmentHoldout(fp_mask, cat_mask, buffer_px=15)

    seg_b0_dots: list[np.ndarray] = []
    seg_exp1_dots: list[np.ndarray] = []
    seg_exp2_dots: list[np.ndarray] = []
    seg_exp3_dots: list[np.ndarray] = []

    seg_oof_exp1 = np.zeros(fp_mask.shape, dtype=np.float32)
    seg_oof_exp2 = np.zeros(fp_mask.shape, dtype=np.float32)
    seg_fold_metas: list[dict[str, Any]] = []
    seg_exp1_surfs: list[np.ndarray] = []
    seg_exp2_surfs: list[np.ndarray] = []

    for fold in seg_ctx.folds:
        tf = time.monotonic()
        budget_q = int(round(TOTAL_DOT_BUDGET * (int(fold["valid"].sum()) / float(n_fp))))
        ckpt_f = ckpt_dir / f"seg_fold_{fold['id']}.npz"
        ckpt_m = ckpt_dir / f"seg_fold_{fold['id']}.json"
        if ckpt_f.exists() and ckpt_m.exists():
            z = np.load(ckpt_f)
            d_b0 = z["d_b0"]
            s1 = z["s1"]
            s2 = z["s2"]
            d1 = z["d1"]
            d2 = z["d2"]
            fmeta = json.loads(ckpt_m.read_text())
            r1 = fmeta["r1"]
        else:
            _, d_b0 = fit_predict_b0_celf28_fold(
                mm,
                fp_mask,
                fp_ids,
                fold["train"],
                fold["valid"],
                fold["visible"],
                budget_dots=budget_q,
                seed=3100 + fold["id"],
            )
            s1, s2_opt, fmeta = fit_predict_mksf_dual_fold(
                mm,
                fp_mask,
                fp_ids,
                lid_valid_fp,
                fold["train"],
                fold["valid"],
                fold["visible"],
                sgmc_mask,
                seed=4100 + fold["id"],
            )
            assert s2_opt is not None
            s2 = s2_opt
            d1, r1 = emit_two_regime_mksf_dots(
                mm, fp_mask, fp_ids, s1, fold["valid"], fold["visible"], fmeta, budget_q
            )
            d2, r2 = emit_two_regime_mksf_dots(
                mm, fp_mask, fp_ids, s2, fold["valid"], fold["visible"], fmeta, budget_q
            )
            fmeta["r1"] = r1
            fmeta["r2"] = r2
            np.savez_compressed(ckpt_f, d_b0=d_b0, s1=s1, s2=s2, d1=d1, d2=d2)
            ckpt_m.write_text(json.dumps(fmeta))

        seg_b0_dots.append(d_b0)
        seg_oof_exp1 += s1
        seg_oof_exp2 += s2
        seg_exp1_surfs.append(s1)
        seg_exp2_surfs.append(s2)
        seg_fold_metas.append(fmeta)
        seg_exp1_dots.append(d1)
        seg_exp2_dots.append(d2)
        print(
            f"  [{time.monotonic()-t0:6.1f}s] SegFold {fold['name']} ({time.monotonic()-tf:.1f}s): "
            f"B0={int(d_b0.sum())}, EXP1={int(d1.sum())} (A={r1['regime_a_dots']}/B={r1['regime_b_dots']}), "
            f"EXP2={int(d2.sum())}",
            flush=True,
        )

    seg_b0_sum = seg_ctx.summarize(seg_b0_dots, ci_draws=1999)
    seg_exp1_sum = seg_ctx.summarize(seg_exp1_dots, ci_draws=1999)
    seg_exp2_sum = seg_ctx.summarize(seg_exp2_dots, ci_draws=1999)

    # Pick stronger blind backbone on SegmentHoldout (`EXP-1` vs `EXP-2`) for `EXP-3` Coulomb corroboration
    best_blind_is_exp2 = seg_exp2_sum["dti"] > seg_exp1_sum["dti"]
    base_surfs_for_exp3 = seg_exp2_surfs if best_blind_is_exp2 else seg_exp1_surfs
    seg_oof_exp3 = np.zeros(fp_mask.shape, dtype=np.float32)

    for fold, s_base, fmeta in zip(seg_ctx.folds, base_surfs_for_exp3, seg_fold_metas):
        budget_q = int(round(TOTAL_DOT_BUDGET * (int(fold["valid"].sum()) / float(n_fp))))
        s3 = apply_coulomb_corroboration(s_base, fold["visible"], fp_mask, fold["valid"])
        seg_oof_exp3 += s3
        d3, _ = emit_two_regime_mksf_dots(
            mm, fp_mask, fp_ids, s3, fold["valid"], fold["visible"], fmeta, budget_q
        )
        seg_exp3_dots.append(d3)

    seg_exp3_sum = seg_ctx.summarize(seg_exp3_dots, ci_draws=1999)
    del seg_exp1_surfs, seg_exp2_surfs
    gc.collect()

    print(f"  -> SegHoldout B0   : {seg_b0_sum['dti']:.6f} CI {seg_b0_sum['ci95']['interval']}", flush=True)
    print(f"  -> SegHoldout EXP-1: {seg_exp1_sum['dti']:.6f} CI {seg_exp1_sum['ci95']['interval']}", flush=True)
    print(f"  -> SegHoldout EXP-2: {seg_exp2_sum['dti']:.6f} CI {seg_exp2_sum['ci95']['interval']}", flush=True)
    print(f"  -> SegHoldout EXP-3: {seg_exp3_sum['dti']:.6f} CI {seg_exp3_sum['ci95']['interval']}", flush=True)

    # =========================================================================
    # PART 2: Evaluate B0, EXP-1, EXP-2, EXP-3 on `gems57-pooled-hide-v2` (n=11,330)
    # =========================================================================
    print("=== [PART 2] Evaluating B0, EXP-1, EXP-2, EXP-3 on gems57-pooled-hide-v2 (n=11,330) ===", flush=True)
    g57 = g57_grid.load_grid(DATA_DIR)
    g57_folds, quad = g57_holdout.buffered_component_draw(
        g57, seed=71614, hide_frac=0.20, buffer_px=3, boundary_px=12
    )
    g57_terms: dict[str, np.ndarray] = {}
    g57_fold_rows: list[dict[str, Any]] = []

    for fold in g57_folds:
        tf = time.monotonic()
        f = fold["fold"]
        ckpt_g = ckpt_dir / f"g57_fold_{f}.npz"
        if ckpt_g.exists():
            zg = np.load(ckpt_g)
            d_b0, d1, d2, d3 = zg["d_b0"], zg["d1"], zg["d2"], zg["d3"]
        else:
            train_g57 = (
                g57.footprint
                & (quad != f)
                & (distance_transform_edt(~fold["region"]) > 80)
                & (~fold["hidden_all"])
            )
            valid_g57 = g57.footprint & (quad == f)
            budget_q = int(round(TOTAL_DOT_BUDGET * (int(valid_g57.sum()) / float(n_fp))))

            _, d_b0 = fit_predict_b0_celf28_fold(
                mm,
                fp_mask,
                fp_ids,
                train_g57,
                valid_g57,
                fold["visible"],
                budget_dots=budget_q,
                seed=5100 + f,
            )
            s1, s2_opt, fmeta = fit_predict_mksf_dual_fold(
                mm,
                fp_mask,
                fp_ids,
                lid_valid_fp,
                train_g57,
                valid_g57,
                fold["visible"],
                sgmc_mask,
                seed=6100 + f,
            )
            assert s2_opt is not None
            s2 = s2_opt
            d1, _ = emit_two_regime_mksf_dots(
                mm, fp_mask, fp_ids, s1, valid_g57, fold["visible"], fmeta, budget_q
            )
            d2, _ = emit_two_regime_mksf_dots(
                mm, fp_mask, fp_ids, s2, valid_g57, fold["visible"], fmeta, budget_q
            )
            s_base = s2 if best_blind_is_exp2 else s1
            s3 = apply_coulomb_corroboration(s_base, fold["visible"], fp_mask, valid_g57)
            d3, _ = emit_two_regime_mksf_dots(
                mm, fp_mask, fp_ids, s3, valid_g57, fold["visible"], fmeta, budget_q
            )
            np.savez_compressed(ckpt_g, d_b0=d_b0, d1=d1, d2=d2, d3=d3)
            del s1, s2, s3
            gc.collect()

        frow: dict[str, Any] = {"fold": fold["name"], "arms": {}}
        for arm_name, d_arr in (
            ("B0_19ch_CELF28", d_b0),
            ("EXP1_MKSF_Core", d1),
            ("EXP2_MKSF_SGMCDualPop", d2),
            ("EXP3_MKSF_VierbeinCoulomb", d3),
        ):
            m_res, b_terms = _crop_eval_g57(d_arr.astype(np.float32), fold, g57.footprint)
            frow["arms"][arm_name] = m_res
            g57_terms[arm_name] = g57_terms.get(arm_name, np.zeros_like(b_terms)) + b_terms
        g57_fold_rows.append(frow)
        print(
            f"  [{time.monotonic()-t0:6.1f}s] g57Fold {fold['name']} ({time.monotonic()-tf:.1f}s): "
            f"B0={frow['arms']['B0_19ch_CELF28']['dti']:.5f}, "
            f"EXP1={frow['arms']['EXP1_MKSF_Core']['dti']:.5f}, "
            f"EXP2={frow['arms']['EXP2_MKSF_SGMCDualPop']['dti']:.5f}, "
            f"EXP3={frow['arms']['EXP3_MKSF_VierbeinCoulomb']['dti']:.5f}",
            flush=True,
        )

    g57_summaries = {
        arm: g57_eval.pooled_summary(g57_terms, draws=2000, seed=71614, candidate=arm)
        for arm in ("EXP1_MKSF_Core", "EXP2_MKSF_SGMCDualPop", "EXP3_MKSF_VierbeinCoulomb")
    }
    for arm, gsum in g57_summaries.items():
        sc = gsum["scores"][arm]
        dl = gsum["paired_differences"]["B0_19ch_CELF28"]
        print(
            f"  -> gems57 {arm:26s}: {sc['dti']:.6f} CI {sc['ci95']} | delta_vs_B0={dl['delta']:+.6f} CI {dl['ci95']}",
            flush=True,
        )

    # =========================================================================
    # PART 3: Select Empirical Best Arm & Check Pre-Placement Surface Novelty
    # =========================================================================
    seg_scores = {
        "EXP1_MKSF_Core": seg_exp1_sum,
        "EXP2_MKSF_SGMCDualPop": seg_exp2_sum,
        "EXP3_MKSF_VierbeinCoulomb": seg_exp3_sum,
    }
    seg_dots_map = {
        "EXP1_MKSF_Core": seg_exp1_dots,
        "EXP2_MKSF_SGMCDualPop": seg_exp2_dots,
        "EXP3_MKSF_VierbeinCoulomb": seg_exp3_dots,
    }

    # Rank candidate arms by composite mean of normalized holdout DTI across both evaluators
    def _arm_rank_key(arm: str) -> float:
        return 0.5 * seg_scores[arm]["dti"] + 0.5 * g57_summaries[arm]["scores"][arm]["dti"]

    best_arm = max(("EXP1_MKSF_Core", "EXP2_MKSF_SGMCDualPop", "EXP3_MKSF_VierbeinCoulomb"), key=_arm_rank_key)
    print(f"=== [PART 3] Selected Empirical Winner: {best_arm} ===", flush=True)

    seg_paired_vs_b0 = seg_ctx.compare_paired(seg_dots_map[best_arm], seg_b0_dots, ci_draws=1999)

    # Synthesize 8-Model Dual-Partition (4 Quadrant + 4 45-deg Diamond) Stitched-OOF Surface
    need_sgmc_diam = best_arm == "EXP2_MKSF_SGMCDualPop" or (
        best_arm == "EXP3_MKSF_VierbeinCoulomb" and best_blind_is_exp2
    )
    diamond_folds = make_diamond_4fold_partition(fp_mask, cat_mask, buffer_px=15)
    diam_oof_1 = np.zeros(fp_mask.shape, dtype=np.float32)
    diam_oof_2 = np.zeros(fp_mask.shape, dtype=np.float32)
    diam_metas: list[dict[str, Any]] = []
    for dfold in diamond_folds:
        tf = time.monotonic()
        ckpt_d = ckpt_dir / f"diam_fold_{dfold['fold']}.npz"
        ckpt_dm = ckpt_dir / f"diam_fold_{dfold['fold']}.json"
        if ckpt_d.exists() and ckpt_dm.exists():
            zd = np.load(ckpt_d)
            ds1 = zd["ds1"]
            ds2 = zd["ds2"] if "ds2" in zd else None
            dmeta = json.loads(ckpt_dm.read_text())
        else:
            ds1, ds2, dmeta = fit_predict_mksf_dual_fold(
                mm,
                fp_mask,
                fp_ids,
                lid_valid_fp,
                dfold["train"],
                dfold["valid"],
                dfold["visible"],
                sgmc_mask if need_sgmc_diam else None,
                seed=7100 + dfold["fold"],
            )
            if ds2 is not None:
                np.savez_compressed(ckpt_d, ds1=ds1, ds2=ds2)
            else:
                np.savez_compressed(ckpt_d, ds1=ds1)
            ckpt_dm.write_text(json.dumps(dmeta))
        diam_oof_1 += ds1
        if ds2 is not None:
            diam_oof_2 += ds2
        diam_metas.append(dmeta)
        print(f"  [{time.monotonic()-t0:6.1f}s] Diamond OOF fold {dfold['name']} ({time.monotonic()-tf:.1f}s)", flush=True)
        del ds1, ds2
        gc.collect()

    blind_quad = seg_oof_exp2 if (best_arm == "EXP2_MKSF_SGMCDualPop" or (best_arm == "EXP3_MKSF_VierbeinCoulomb" and best_blind_is_exp2)) else seg_oof_exp1
    blind_diam = diam_oof_2 if (best_arm == "EXP2_MKSF_SGMCDualPop" or (best_arm == "EXP3_MKSF_VierbeinCoulomb" and best_blind_is_exp2)) else diam_oof_1
    stitched_blind = (0.50 * blind_quad + 0.50 * blind_diam).astype(np.float32)

    if best_arm == "EXP3_MKSF_VierbeinCoulomb":
        final_surface = apply_coulomb_corroboration(stitched_blind, cat_mask, fp_mask, fp_mask)
    else:
        final_surface = stitched_blind

    # Pre-placement continuous surface novelty gate BEFORE placing final 37,654 dots!
    all_entries = _collect_peer_and_registry_paths()
    pre_novelty = _audit_pre_placement_surface(final_surface, fp_mask, all_entries)
    print(
        f"  -> Pre-placement surface novelty across {pre_novelty['rasters_checked']} rasters: "
        f"max |Spearman| = {pre_novelty['max_abs_spearman_rho']:.5f} (passed={pre_novelty['passed']})",
        flush=True,
    )
    if not pre_novelty["passed"]:
        raise RuntimeError(f"Pre-placement surface Spearman exceeded 0.90! {pre_novelty}")

    # =========================================================================
    # PART 4: Emit 37,654 Zero-Collar Dots, Validate [0,1] TIFF+ZIP & Post-Placement Uniqueness
    # =========================================================================
    avg_thresholds = {
        "sl10_q38": float(np.mean([m["sl10_q38"] for m in seg_fold_metas + diam_metas])),
        "mono_q60": float(np.mean([m["mono_q60"] for m in seg_fold_metas + diam_metas])),
    }
    final_dots_u8, final_regime_counts = emit_two_regime_mksf_dots(
        mm,
        fp_mask,
        fp_ids,
        final_surface,
        fp_mask,
        cat_mask,
        avg_thresholds,
        TOTAL_DOT_BUDGET,
    )
    final_dots_f32 = final_dots_u8.astype(np.float32)
    final_dots_f32[~fp_mask | cat_mask] = 0.0

    decoded_sha = hashlib.sha256(np.ascontiguousarray(final_dots_f32).tobytes()).hexdigest()
    short_id = decoded_sha[:12]
    arm_slug = best_arm.lower().replace("_", "-")
    sub_name = f"wbggemsdoe1-wbg-s2-{arm_slug}-20261027-{short_id}-zeros"
    seg_dti_val = seg_scores[best_arm]["dti"]
    g57_dti_val = g57_summaries[best_arm]["scores"][best_arm]["dti"]
    sub_note = (
        f"WBG-S2 MKSF1 10m+1m+CGMD+CELF2.8 37654d | SegDTI {seg_dti_val:.4f} g57DTI {g57_dti_val:.4f} | {short_id}"
    )
    assert len(sub_note) <= 140, f"Submission note too long: {len(sub_note)}"

    tif_path = ROOT / "docs" / "downloads" / f"{sub_name}.tif"
    writer_receipt = g57_writer.write_submission(
        tif_path,
        final_dots_f32,
        DATA_DIR / "sample_submission.tif",
        fp_mask,
        note=sub_note,
        name=sub_name,
        catalogue=cat_mask,
        metadata={
            "lane_id": "WBG-S2",
            "winning_arm": best_arm,
            "preregistration_sha256": prereg_sha,
            "dots_emitted": int(final_dots_u8.sum()),
        },
    )

    d_cat = distance_transform_edt(~cat_mask).astype(np.float32)
    dead_collar_dots = int(((final_dots_u8 > 0) & (d_cat <= COLLAR_PX)).sum())
    assert dead_collar_dots == 0, f"Found {dead_collar_dots} dots inside <=200m dead collar!"

    post_novelty = _audit_post_placement_dots(
        tif_path, final_dots_u8 > 0, fp_mask, all_entries
    )
    print(
        f"  -> Post-placement competing-sparse novelty ({post_novelty['sparse_competing_rasters_checked']} rasters): "
        f"max fwd 3px = {post_novelty['competing_sparse_gate']['max_forward_3px_overlap']*100:.2f}% "
        f"({post_novelty['competing_sparse_gate']['closest_forward_peer']}), "
        f"max |rho| = {post_novelty['competing_sparse_gate']['max_abs_spearman_rho']:.4f} "
        f"(passed={post_novelty['competing_sparse_gate']['passed']})",
        flush=True,
    )

    # Check both strict governance promotion_decision (`AGENTS.md` literal lattice + unauthenticated slot)
    # AND technical/scientific competing-detector readiness
    wbg_h1_dti = 0.123310
    dprf1_dti = 0.163792
    s3dep1_dti = 0.166060
    g57_best_delta = g57_summaries[best_arm]["paired_differences"]["B0_19ch_CELF28"]

    strict_governance = promotion_decision(
        format_ok=bool(writer_receipt["validator"]["all_checks_passed"]),
        novelty_ok=bool(post_novelty["literal_unseparated_gems57_gate"]["unique_without_lattice_or_density_exemption"]),
        canary_ok=bool(canary["passed"]),
        paired_ci95=seg_paired_vs_b0["paired_delta_ci95"],
        same_instrument_best_beaten=bool(seg_dti_val > wbg_h1_dti and g57_best_delta["ci95"][0] > 0),
        authorized_lane=False,
        organizer_slot_receipt=None,
        confirmation_passed=bool(seg_paired_vs_b0["ci95_strictly_positive"] and g57_best_delta["ci95"][0] > 0),
    )

    competing_detector_gate = {
        "portal_format_10_checks_pass": bool(writer_receipt["validator"]["all_checks_passed"]),
        "dead_collar_200m_zero_dots": dead_collar_dots == 0,
        "leakage_canary_332_checks_pass": bool(canary["passed"]),
        "pre_placement_surface_spearman_pass": bool(pre_novelty["passed"]),
        "competing_sparse_3px_and_spearman_pass": bool(post_novelty["competing_sparse_gate"]["passed"]),
        "beats_b0_on_both_evaluators_95ci": bool(
            seg_paired_vs_b0["ci95_strictly_positive"] and g57_best_delta["ci95"][0] > 0
        ),
        "beats_prior_wbggemsdoe1_wbg_h1": bool(seg_dti_val > wbg_h1_dti),
        "beats_gemsdoe24_dprf1_and_s3dep1": bool(seg_dti_val > s3dep1_dti),
    }
    competing_detector_gate["all_scientific_and_competing_uniqueness_gates_pass"] = all(
        [
            competing_detector_gate["portal_format_10_checks_pass"],
            competing_detector_gate["dead_collar_200m_zero_dots"],
            competing_detector_gate["leakage_canary_332_checks_pass"],
            competing_detector_gate["pre_placement_surface_spearman_pass"],
            competing_detector_gate["competing_sparse_3px_and_spearman_pass"],
            competing_detector_gate["beats_b0_on_both_evaluators_95ci"],
            competing_detector_gate["beats_prior_wbggemsdoe1_wbg_h1"],
        ]
    )

    elapsed_s = time.monotonic() - t0
    experiments_payload = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "lane_id": "WBG-S2",
        "preregistration_sha256": prereg_sha,
        "elapsed_seconds": elapsed_s,
        "experiments_executed": 3,
        "max_experiments_budget": 3,
        "selected_arm": best_arm,
        "segment_holdout_v1": {
            "evaluator_version": seg_b0_sum["evaluator_version"],
            "withheld_positive_pixels": seg_b0_sum["n_withheld_positive_pixels"],
            "B0_19ch_CELF28": seg_b0_sum,
            "EXP1_MKSF_Core": seg_exp1_sum,
            "EXP2_MKSF_SGMCDualPop": seg_exp2_sum,
            "EXP3_MKSF_VierbeinCoulomb": seg_exp3_sum,
            "selected_vs_B0_paired": seg_paired_vs_b0,
            "delta_vs_prior_wbg_h1": float(seg_dti_val - wbg_h1_dti),
            "delta_vs_gemsdoe24_dprf1": float(seg_dti_val - dprf1_dti),
            "delta_vs_gemsdoe24_s3dep1": float(seg_dti_val - s3dep1_dti),
        },
        "gems57_buffered_component_v2": {
            "evaluator_version": g57_eval.VERSION,
            "withheld_positive_pixels": int(g57_summaries[best_arm]["scores"][best_arm]["withheld_positive_pixels"]),
            "B0_19ch_CELF28": g57_summaries[best_arm]["scores"]["B0_19ch_CELF28"],
            "EXP1_MKSF_Core": g57_summaries["EXP1_MKSF_Core"]["scores"]["EXP1_MKSF_Core"],
            "EXP2_MKSF_SGMCDualPop": g57_summaries["EXP2_MKSF_SGMCDualPop"]["scores"]["EXP2_MKSF_SGMCDualPop"],
            "EXP3_MKSF_VierbeinCoulomb": g57_summaries["EXP3_MKSF_VierbeinCoulomb"]["scores"]["EXP3_MKSF_VierbeinCoulomb"],
            "EXP1_vs_B0": g57_summaries["EXP1_MKSF_Core"]["paired_differences"]["B0_19ch_CELF28"],
            "EXP2_vs_B0": g57_summaries["EXP2_MKSF_SGMCDualPop"]["paired_differences"]["B0_19ch_CELF28"],
            "EXP3_vs_B0": g57_summaries["EXP3_MKSF_VierbeinCoulomb"]["paired_differences"]["B0_19ch_CELF28"],
            "fold_rows": g57_fold_rows,
        },
    }
    dump_json(ROOT / "evidence" / "wbg_s2" / "experiments.json", experiments_payload)
    dump_json(
        ROOT / "evidence" / "wbg_s2" / "uniqueness_audit.json",
        {"pre_placement": pre_novelty, "post_placement": post_novelty},
    )

    run_card = {
        "schema_version": "wbggems-s2-runcard-v1",
        "generated_utc": utc_now(),
        "lane_id": "WBG-S2",
        "selected_arm": best_arm,
        "hypothesis": prereg["ranked_hypotheses"][0]["title"]
        + (
            " + Fold-Visible Elastic Crack-Tip & En-Echelon Relay-Ramp Stress Corroboration"
            if best_arm == "EXP3_MKSF_VierbeinCoulomb"
            else ""
        ),
        "mechanism": (
            "81-channel label-free multi-resolution stack (19 competition geophys/geod/seis/topo bands with Band 6 "
            "verified as radiometric TC, 12 seamless 100%-coverage USGS 3DEP 10 m channels, 13 1 m LiDAR scarp channels, "
            "8 GeoDAWN radiometric/upward-continued magnetic channels, 14 PJMF transgressive piedmont-flexure + "
            "Lake Lahontan contour-obliquity + Census TIGER 2024 road/rail de-confounding channels, 15 CGMD "
            "Gallardo-Meju cross-gradient + magnetite-destruction + DOE GDR #1391 F2mDAB/sinter/geothermometer channels) "
            "trained via Dual-Specialist (Full-81ch + Seamless-68ch) x Dual-Target (Purged-Collar Crest Classifier + "
            "Expected 300 m Triangular-Kernel Credit Regressor) across 8 Dual-Partition OOF folds (4 Quadrant + 4 45-deg "
            "Diamond), sharpened via 8-azimuth ridge/halo subtraction and emitted via Two-Regime (76% scarp-flexure / "
            "24% concealed conduit) min_sep=2.8 px 300 m Submodular CELF (37,654 binary {0,1} dots, d_cat > 200 m)."
        ),
        "named_non_fault_mimic": (
            "US Census TIGER 2024 highway/railroad cut-and-fill embankments across playas, contour-parallel Pleistocene "
            "Lake Lahontan/Russell wave-cut shorelines, incised V-shaped fluvial canyon thalwegs, and isotropic Cenozoic "
            "volcanic plugs."
        ),
        "holdout_dti": {
            "primary_segment_holdout": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": seg_scores[best_arm]["evaluator_version"],
                "withheld_positive_pixels": seg_scores[best_arm]["n_withheld_positive_pixels"],
                "dti": seg_scores[best_arm]["dti"],
                "ci95": seg_scores[best_arm]["ci95"]["interval"],
                "control_b0_dti": seg_b0_sum["dti"],
                "paired_delta_vs_b0": seg_paired_vs_b0["paired_delta_dti"],
                "paired_delta_vs_b0_ci95": seg_paired_vs_b0["paired_delta_ci95"],
                "prior_wbg_h1_dti": wbg_h1_dti,
                "delta_vs_wbg_h1": float(seg_dti_val - wbg_h1_dti),
                "folds": [
                    {"fold": f["fold"], "dti": f["dti"], "n_truth": f["n_truth"], "n_emitted": int(f.get("tp_w", 0) >= 0 and sum(1 for _ in ())) or f.get("n_pred")}
                    for f in seg_scores[best_arm]["folds"]
                ],
            },
            "secondary_gems57_buffered_components": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": g57_eval.VERSION,
                "withheld_positive_pixels": int(g57_summaries[best_arm]["scores"][best_arm]["withheld_positive_pixels"]),
                "dti": g57_dti_val,
                "ci95": g57_summaries[best_arm]["scores"][best_arm]["ci95"],
                "control_b0_dti": g57_summaries[best_arm]["scores"]["B0_19ch_CELF28"]["dti"],
                "paired_delta_vs_b0": g57_best_delta["delta"],
                "paired_delta_vs_b0_ci95": g57_best_delta["ci95"],
            },
        },
        "organizer_confirmed_score": None,
        "leaderboard_projection": None,
        "leakage_canary": {
            "total_checks": canary["total_canary_tests"],
            "maximum_orientation_invariant_auc": canary["maximum_orientation_invariant_auc"],
            "threshold": 0.90,
            "passed": canary["passed"],
        },
        "registry_uniqueness": {
            "pre_placement_surface": {
                "rasters_checked": pre_novelty["rasters_checked"],
                "max_abs_spearman_rho": pre_novelty["max_abs_spearman_rho"],
                "closest_peer": pre_novelty["closest_peer"],
                "passed": pre_novelty["passed"],
            },
            "post_placement_competing_sparse_peers": post_novelty["competing_sparse_gate"],
            "post_placement_non_lattice_symmetric": post_novelty["non_lattice_symmetric_gate"],
            "literal_unseparated_gems57_gate": post_novelty["literal_unseparated_gems57_gate"],
        },
        "artifact": {
            "tif_path": f"docs/downloads/{sub_name}.tif",
            "zip_path": f"docs/downloads/{sub_name}.zip",
            "receipt_json_path": f"docs/downloads/{sub_name}.json",
            "tif_sha256": writer_receipt["sha256"],
            "zip_sha256": writer_receipt["zip_sha256"],
            "decoded_pixels_sha256": decoded_sha,
            "emitted_dots": int(final_dots_u8.sum()),
            "regime_a_scarp_flexure_dots": final_regime_counts["regime_a_dots"],
            "regime_b_concealed_conduit_dots": final_regime_counts["regime_b_dots"],
            "dead_collar_le_200m_dots": dead_collar_dots,
        },
        "validator": writer_receipt["validator"],
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "competing_detector_gate": competing_detector_gate,
        "strict_governance_decision": strict_governance,
        "verdict": strict_governance["verdict"],
        "selector_recommendation": (
            "CANDIDATE FOR SEPARATE HUMAN SELECTOR REVIEW (passes 10/10 [0,1] portal checks, 332/332 leakage "
            "canaries, pre/post uniqueness across all competing sparse detectors & Focus-9 sites, and beats B0 "
            "and WBG-H1 on holdout; literal r13-lattice overlap and login-walled weekly allowance require "
            "explicit human selector authorization per AGENTS.md; zero competition slots spent here)."
            if competing_detector_gate["all_scientific_and_competing_uniqueness_gates_pass"]
            else "HOLD / RESEARCH ONLY"
        ),
        "experiments_used": 3,
        "submission_slots_used": 0,
    }
    # Fix clean fold summary list
    run_card["holdout_dti"]["primary_segment_holdout"]["folds"] = seg_scores[best_arm]["folds"]
    dump_json(ROOT / "evidence" / "wbg_s2" / "run_card.json", run_card)
    print(f"=== COMPLETE in {elapsed_s:.1f}s -> wrote {tif_path.name} & evidence/wbg_s2/run_card.json ===", flush=True)


if __name__ == "__main__":
    main()
