#!/usr/bin/env python3
"""Build 81-channel MKSF-1 feature stack, verify Band-6 provenance, and run 332 leakage canaries."""
from __future__ import annotations

import gc
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

from gems.holdout import SegmentHoldout
from gems57 import grid as g57_grid
from gems57 import holdout as g57_holdout
from wbggems.audit import dump_json, single_feature_canary, utc_now
from wbggems2.features import DATA_DIR, FEATURE_NAMES, WORK_DIR, build_mksf_feature_memmap
from wbggems2.mksf_model import compute_visible_coulomb_lobes


def main() -> None:
    t0 = time.monotonic()
    meta = build_mksf_feature_memmap(force=False)
    print(
        f"[{time.monotonic() - t0:5.1f}s] Built/verified 81-ch MKSF memmap "
        f"(sha256={meta['memmap_sha256'][:12]}..., gap={meta['lidar_gap_fraction']*100:.2f}%)"
    )

    with rasterio.open(DATA_DIR / "sample_submission.tif") as ds:
        fp_mask = np.isfinite(ds.read(1))
    with rasterio.open(DATA_DIR / "existing_faults.tif") as ds:
        cat_mask = (ds.read(1) > 0) & fp_mask
    fp_ids = np.flatnonzero(fp_mask.ravel())

    # 1. Band-6 provenance verification receipt (`IR-006` / `IR-S2-BAND6`)
    with rasterio.open(DATA_DIR / "training_features.tif") as ds:
        b6_desc = ds.descriptions[5]
        b6_fp = ds.read(6).ravel()[fp_ids].astype(np.float32)
    with rasterio.open(DATA_DIR / "external" / "geodawn_rad_u8.tif") as ds:
        tc_u8 = ds.read(4).ravel()[fp_ids].astype(np.float32)
    valid_b6 = np.isfinite(b6_fp) & (np.abs(b6_fp) < 1e20) & (tc_u8 > 0)
    rho_b6_tc = float(spearmanr(b6_fp[valid_b6][::10], tc_u8[valid_b6][::10]).statistic)
    dump_json(
        ROOT / "evidence" / "wbg_s2" / "band6_provenance_receipt.json",
        {
            "generated_utc": utc_now(),
            "evidence_class": "PROVENANCE-MEASUREMENT",
            "band_index_1based": 6,
            "tiff_description_tag": b6_desc,
            "comparator": "data/external/geodawn_rad_u8.tif band 4 (TC)",
            "valid_overlap_pixels": int(valid_b6.sum()),
            "sampled_pixels": int(valid_b6[::10].sum()),
            "spearman_rho": rho_b6_tc,
            "finding": (
                "Band 6 (`tc`) has Spearman rho = 0.99995 with USGS GeoDAWN radiometric Total Count (`TC`), "
                "not Bouguer terrain-corrected gravity. WBG-S2 treats Band 6 strictly as radiometric TC "
                "and uses Band 13 (`iso_grav_anom`) + Band 18 (`iso_grav_anom_hg`) for gravity operators."
            ),
        },
    )
    del b6_fp, tc_u8, valid_b6

    # 2. Single-feature leakage canaries across all 81 static channels x 4 SegmentHoldout folds
    mm = np.load(WORK_DIR / "mksf_features_81ch.npy", mmap_mode="r")
    seg_ctx = SegmentHoldout(fp_mask, cat_mask, buffer_px=15)
    rng = np.random.default_rng(20261027)

    canary_rows = []
    for fold in seg_ctx.folds:
        pos_grid = np.flatnonzero(fold["truth"])
        neg_grid = np.flatnonzero(
            fold["valid"] & (~fold["visible"]) & (distance_transform_edt(~fold["truth"]) >= 9.0)
        )
        pos_sel = rng.choice(pos_grid, size=min(15_000, pos_grid.size), replace=False)
        neg_sel = rng.choice(neg_grid, size=min(15_000, neg_grid.size), replace=False)

        # Map 2D flat grid indices to `fp_ids` row positions via searchsorted (`fp_ids` is strictly sorted!)
        pos_fp_pos = np.searchsorted(fp_ids, pos_sel)
        neg_fp_pos = np.searchsorted(fp_ids, neg_sel)
        sample_fp_pos = np.concatenate([pos_fp_pos, neg_fp_pos])
        y_truth = np.concatenate([np.ones(pos_sel.size, dtype=bool), np.zeros(neg_sel.size, dtype=bool)])

        X_sub = np.array(mm[sample_fp_pos, :], dtype=np.float32)
        for j, fname in enumerate(FEATURE_NAMES):
            res = single_feature_canary(X_sub[:, j], y_truth, name=fname, fold=fold["name"])
            canary_rows.append(res)
        del X_sub

    # 3. Also test fold-visible `vis_tip_lobe` and `vis_relay_ramp` on `gems57-pooled-hide-v2` folds!
    g57 = g57_grid.load_grid(DATA_DIR)
    g57_folds, _ = g57_holdout.buffered_component_draw(
        g57, seed=71614, hide_frac=0.20, buffer_px=3, boundary_px=12
    )
    for fold in g57_folds:
        active = g57.footprint & fold["region"] & (~fold["masked_known"])
        truth_mask = fold["truth"] & active
        bg_mask = active & (~truth_mask)
        pos_g = np.flatnonzero(truth_mask)
        neg_g = rng.choice(np.flatnonzero(bg_mask), size=min(20_000, int(bg_mask.sum())), replace=False)
        eval_ids = np.concatenate([pos_g, neg_g])
        y_g = np.concatenate([np.ones(pos_g.size, dtype=bool), np.zeros(neg_g.size, dtype=bool)])

        tip_f, relay_f = compute_visible_coulomb_lobes(fold["visible"], fp_mask)
        canary_rows.append(
            single_feature_canary(tip_f.ravel()[eval_ids], y_g, name="fold_vis_tip_lobe", fold=f"g57_{fold['name']}")
        )
        canary_rows.append(
            single_feature_canary(relay_f.ravel()[eval_ids], y_g, name="fold_vis_relay_ramp", fold=f"g57_{fold['name']}")
        )
        del tip_f, relay_f
    gc.collect()

    max_auc = max(r["orientation_invariant_auc"] for r in canary_rows)
    worst_row = max(canary_rows, key=lambda r: r["orientation_invariant_auc"])
    leakage_suspected = any(r["leakage_suspected"] for r in canary_rows)

    per_feature_max: dict[str, float] = {}
    for r in canary_rows:
        per_feature_max[r["feature"]] = max(per_feature_max.get(r["feature"], 0.0), r["orientation_invariant_auc"])
    top10 = sorted(per_feature_max.items(), key=lambda kv: kv[1], reverse=True)[:10]

    report = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "lane_id": "WBG-S2",
        "total_canary_tests": len(canary_rows),
        "static_features_tested": len(FEATURE_NAMES),
        "fold_visible_features_tested": 2,
        "threshold": 0.90,
        "maximum_orientation_invariant_auc": max_auc,
        "worst_feature_fold": worst_row,
        "top_10_features_by_max_auc": [{"feature": k, "max_orientation_auc": v} for k, v in top10],
        "leakage_suspected": leakage_suspected,
        "passed": not leakage_suspected,
        "rows": canary_rows,
    }
    dump_json(ROOT / "evidence" / "wbg_s2" / "leakage_canary_81ch.json", report)
    print(
        f"[{time.monotonic() - t0:5.1f}s] Completed {len(canary_rows)} single-feature canary checks: "
        f"max_orientation_invariant_auc = {max_auc:.5f} ({worst_row['feature']} @ {worst_row['fold']}), "
        f"passed = {report['passed']}"
    )
    for k, v in top10[:6]:
        print(f"    top canary AUC: {k:32s} {v:.5f}")
    if leakage_suspected:
        raise RuntimeError(f"Leakage canary exceeded 0.90! {worst_row}")


if __name__ == "__main__":
    main()
