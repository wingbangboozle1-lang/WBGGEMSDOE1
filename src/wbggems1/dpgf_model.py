"""WBG-H1 (DPGF-1) Pre-Registered Models, Fold-Safe Residualization & Dual-Partition OOF Synthesis.

Strictly implements the frozen 4-arm protocol locked in:
  - knowledge/01_preregistration_wbg_hypotheses_2026-10-26.md
  - evidence/preregistration_20261026.json (SHA-256: 7d53a7901224...)

Arms evaluated on shared `gems.holdout.SegmentHoldout` (`gems-segment-pooled-v1`):
  - B0   : 31-ch (19 organizer + 12 3DEP lidar) HistGradientBoosting + 2.8-px NMS thinning
  - EXP-1: 66-ch WBG-H1 CorePhysics + LiDAR-Completeness Dual Ensemble (HGB+ET) + 300 m CELF Submodular
  - EXP-2: EXP-1 + Fold-Safe Regional Nuisance Residualization + Stratified Hard-Negative Sampling + 8-Azimuth Strike Sharpening
  - EXP-3: EXP-2 + Two-Regime (72% Dip-Coupled Scarp/Piedmont / 28% Concealed Basin + LiDAR-Gap + Hydrothermal) 300 m CELF Submodular
"""

from __future__ import annotations

import gc
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, label, shift
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import Ridge

from gems.emission import priority_poisson
from wbggems1.features import FEATURE_NAMES

TOTAL_DOT_BUDGET = 37_654
COLLAR_PX = 2.0
PREDICT_CHUNK = 250_000

IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}

# Exact feature index sets
B0_COLS = list(range(31))
FULL_66_COLS = list(range(len(FEATURE_NAMES)))
LIDAR_DEPENDENT_INDICES = set(range(19, 31)) | {
    IDX["dpgf_dip_surface_coupling"],
    IDX["dpgf_tfsdi_scarp"],
    IDX["dpgf_graben_crest_base"],
}
NONLIDAR_51_COLS = [i for i in range(len(FEATURE_NAMES)) if i not in LIDAR_DEPENDENT_INDICES]

REGIONAL_SCALAR_COLS = [
    IDX["org_mag_anom"],
    IDX["org_iso_grav_anom"],
    IDX["org_tmi"],
    IDX["org_rtp"],
    IDX["org_depth_to_base_surf"],
    IDX["org_cond_surf"],
    IDX["org_geod_2ndinv"],
    IDX["org_geod_dilaterate"],
    IDX["org_geod_shearrate"],
    IDX["gd_TMI_up150"],
    IDX["gd_K"],
    IDX["gd_Th"],
    IDX["gd_U"],
    IDX["gd_TC"],
]


@dataclass
class RegionalResidualizer:
    """Fold-safe spatial + elevation regional baseline residualizer fit ONLY on train background."""

    col_indices: list[int]
    coef: np.ndarray  # (8, n_cols)
    intercept: np.ndarray  # (n_cols,)
    res_std: np.ndarray  # (n_cols,)
    col_medians: np.ndarray  # (n_cols,)

    @staticmethod
    def _design(r_norm: np.ndarray, c_norm: np.ndarray, det_elev: np.ndarray) -> np.ndarray:
        de = np.nan_to_num(det_elev, nan=0.0).astype(np.float32) * 1e-3
        return np.column_stack(
            [
                r_norm,
                c_norm,
                r_norm * r_norm,
                c_norm * c_norm,
                r_norm * c_norm,
                de,
                de * de,
            ]
        ).astype(np.float32)

    @classmethod
    def fit(
        cls,
        mm: np.ndarray,
        bg_fp_indices: np.ndarray,
        fp_r_norm: np.ndarray,
        fp_c_norm: np.ndarray,
        seed: int = 42,
    ) -> "RegionalResidualizer":
        rng = np.random.default_rng(seed)
        if bg_fp_indices.size > 120_000:
            sub = np.sort(rng.choice(bg_fp_indices, size=120_000, replace=False))
        else:
            sub = bg_fp_indices

        Y = np.array(mm[sub][:, REGIONAL_SCALAR_COLS], dtype=np.float32, copy=True)
        col_medians = np.nanmedian(Y, axis=0).astype(np.float32)
        col_medians = np.where(np.isfinite(col_medians), col_medians, 0.0).astype(np.float32)
        for j in range(Y.shape[1]):
            bad = ~np.isfinite(Y[:, j])
            if np.any(bad):
                Y[bad, j] = col_medians[j]

        det_el = np.array(mm[sub, IDX["org_det_elev"]], dtype=np.float32)
        B = cls._design(fp_r_norm[sub], fp_c_norm[sub], det_el)
        reg = Ridge(alpha=250.0, random_state=seed)
        reg.fit(B, Y)
        pred = reg.predict(B)
        res = Y - pred
        res_std = np.maximum(np.std(res, axis=0), 1e-4).astype(np.float32)
        return cls(
            col_indices=list(REGIONAL_SCALAR_COLS),
            coef=reg.coef_.T.astype(np.float32),  # (7, n_cols)
            intercept=reg.intercept_.astype(np.float32),
            res_std=res_std,
            col_medians=col_medians,
        )

    def transform_inplace(
        self,
        X_full_or_sub: np.ndarray,
        col_map: dict[int, int],
        r_norm: np.ndarray,
        c_norm: np.ndarray,
        det_elev: np.ndarray,
    ) -> None:
        """Replace mapped regional scalar columns with fold-standardized local residuals."""
        B = self._design(r_norm, c_norm, det_elev)
        trend = B @ self.coef + self.intercept[None, :]
        for k, orig_col in enumerate(self.col_indices):
            if orig_col in col_map:
                j = col_map[orig_col]
                vals = X_full_or_sub[:, j]
                bad = ~np.isfinite(vals)
                if np.any(bad):
                    vals = vals.copy()
                    vals[bad] = self.col_medians[k]
                X_full_or_sub[:, j] = ((vals - trend[:, k]) / self.res_std[k]).astype(np.float32)


def directional_strike_sharpen(prob_grid: np.ndarray, footprint_mask: np.ndarray) -> np.ndarray:
    """8-azimuth fault-strike continuity enhancer suppressing circular/speckle mimics."""
    p = np.where(footprint_mask & np.isfinite(prob_grid), np.maximum(prob_grid, 0.0), 0.0).astype(
        np.float32
    )
    # Isotropic fine pre-smoothing for subpixel shift stability
    p_base = gaussian_filter(p, sigma=0.65).astype(np.float32)
    best_ridge = np.zeros_like(p, dtype=np.float32)

    for k in range(8):
        theta = k * (np.pi / 8.0)
        ux = float(np.cos(theta))
        uy = float(np.sin(theta))
        nx = -uy
        ny = ux

        # 5-tap Gaussian along-strike integral (-3, -1.5, 0, +1.5, +3 px -> ~600 m strike window)
        along = 0.28 * p_base
        for s_px, wt in ((1.5, 0.22), (3.0, 0.14)):
            along += wt * shift(p_base, (s_px * uy, s_px * ux), order=1, mode="nearest")
            along += wt * shift(p_base, (-s_px * uy, -s_px * ux), order=1, mode="nearest")

        # Cross-strike flank at +-2.5 px (250 m perpendicular to strike)
        flank = 0.5 * (
            shift(p_base, (2.5 * ny, 2.5 * nx), order=1, mode="nearest")
            + shift(p_base, (-2.5 * ny, -2.5 * nx), order=1, mode="nearest")
        )
        ridge_k = np.maximum(0.0, along - 0.30 * flank)
        np.maximum(best_ridge, ridge_k, out=best_ridge)

    sharpened = (0.55 * p + 0.45 * best_ridge).astype(np.float32)
    sharpened[~footprint_mask] = 0.0
    return sharpened


def _fit_hgb_et_pair(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    sample_weight: np.ndarray | None,
    seed: int,
) -> tuple[HistGradientBoostingClassifier, ExtraTreesClassifier, np.ndarray]:
    """Fit paired HistGradientBoosting + median-imputed ExtraTrees specialist."""
    hgb = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=220,
        max_leaf_nodes=63,
        min_samples_leaf=75,
        l2_regularization=2.0,
        early_stopping=False,
        random_state=seed,
    )
    hgb.fit(X_tr, y_tr, sample_weight=sample_weight)

    medians = np.nanmedian(X_tr, axis=0).astype(np.float32)
    medians = np.where(np.isfinite(medians), medians, 0.0).astype(np.float32)
    X_imp = X_tr.copy()
    for j in range(X_imp.shape[1]):
        bad = ~np.isfinite(X_imp[:, j])
        if np.any(bad):
            X_imp[bad, j] = medians[j]

    et = ExtraTreesClassifier(
        n_estimators=96,
        max_depth=18,
        min_samples_leaf=20,
        max_features="sqrt",
        n_jobs=-1,
        random_state=seed + 17,
    )
    et.fit(X_imp, y_tr, sample_weight=sample_weight)
    del X_imp
    return hgb, et, medians


def _predict_hgb_et_pair(
    hgb: HistGradientBoostingClassifier,
    et: ExtraTreesClassifier,
    medians: np.ndarray,
    mm: np.ndarray,
    fp_indices: np.ndarray,
    cols: list[int],
    residualizer: RegionalResidualizer | None,
    fp_r_norm: np.ndarray,
    fp_c_norm: np.ndarray,
    hgb_weight: float = 0.68,
) -> np.ndarray:
    """Chunked memory-safe prediction on selected footprint indices."""
    n = fp_indices.size
    out = np.zeros(n, dtype=np.float32)
    if n == 0:
        return out
    col_map = {orig_c: j for j, orig_c in enumerate(cols)}
    for s in range(0, n, PREDICT_CHUNK):
        idx = fp_indices[s : s + PREDICT_CHUNK]
        Xc = np.array(mm[idx][:, cols], dtype=np.float32, copy=True)
        if residualizer is not None:
            det_el = np.array(mm[idx, IDX["org_det_elev"]], dtype=np.float32)
            residualizer.transform_inplace(Xc, col_map, fp_r_norm[idx], fp_c_norm[idx], det_el)
        p_hgb = hgb.predict_proba(Xc)[:, 1].astype(np.float32)
        for j in range(Xc.shape[1]):
            bad = ~np.isfinite(Xc[:, j])
            if np.any(bad):
                Xc[bad, j] = medians[j]
        p_et = et.predict_proba(Xc)[:, 1].astype(np.float32)
        out[s : s + PREDICT_CHUNK] = hgb_weight * p_hgb + (1.0 - hgb_weight) * p_et
        del Xc, p_hgb, p_et
    return out


def _slope_stratified_quantile_calibrate(
    src_cal: np.ndarray,
    ref_cal: np.ndarray,
    slope_src_cal: np.ndarray,
    slope_ref_cal: np.ndarray,
    src_target: np.ndarray,
    slope_target: np.ndarray,
) -> np.ndarray:
    """Map LiDAR-Blind probabilities onto the Full-Sensor probability scale within 4 slope quartiles."""
    if src_target.size == 0 or src_cal.size < 200 or ref_cal.size < 200:
        return src_target.astype(np.float32)

    q_edges = np.nanquantile(slope_ref_cal, [0.25, 0.50, 0.75])
    q_grid = np.linspace(0.0, 1.0, 501)
    calibrated = np.empty_like(src_target, dtype=np.float32)

    b_src_cal = np.digitize(np.nan_to_num(slope_src_cal, nan=0.0), q_edges)
    b_ref_cal = np.digitize(np.nan_to_num(slope_ref_cal, nan=0.0), q_edges)
    b_tgt = np.digitize(np.nan_to_num(slope_target, nan=0.0), q_edges)

    global_src_q = np.quantile(src_cal, q_grid)
    global_ref_q = np.quantile(ref_cal, q_grid)

    for b in range(4):
        m_tgt = b_tgt == b
        if not np.any(m_tgt):
            continue
        s_sub = src_cal[b_src_cal == b]
        r_sub = ref_cal[b_ref_cal == b]
        if s_sub.size >= 100 and r_sub.size >= 100:
            sq = np.quantile(s_sub, q_grid)
            rq = np.quantile(r_sub, q_grid)
        else:
            sq, rq = global_src_q, global_ref_q
        # Ensure strict monotonicity for np.interp
        sq_u, u_idx = np.unique(sq, return_index=True)
        rq_u = rq[u_idx]
        calibrated[m_tgt] = np.interp(src_target[m_tgt], sq_u, rq_u).astype(np.float32)

    return calibrated


def _sample_standard_train(
    train_fp_mask: np.ndarray,
    vis_fp: np.ndarray,
    d_vis_fp: np.ndarray,
    rng: np.random.Generator,
    n_neg: int = 180_000,
) -> tuple[np.ndarray, np.ndarray, None]:
    """Standard B0 / EXP-1 sampling: all visible train positives + random d_vis >= 9 px negatives."""
    pos_idx = np.flatnonzero(train_fp_mask & vis_fp)
    neg_pool = np.flatnonzero(train_fp_mask & (~vis_fp) & (d_vis_fp >= 9.0))
    if neg_pool.size > n_neg:
        neg_idx = np.sort(rng.choice(neg_pool, size=n_neg, replace=False))
    else:
        neg_idx = neg_pool
    idx = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate(
        [np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)]
    )
    return idx, y, None


def _sample_hardneg_train(
    train_fp_mask: np.ndarray,
    vis_fp: np.ndarray,
    d_vis_fp: np.ndarray,
    slope_fp: np.ndarray,
    rng: np.random.Generator,
    n_near: int = 70_000,
    n_steep_far: int = 65_000,
    n_flat_far: int = 65_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """EXP-2 / EXP-3 stratified near-piedmont + high-slope mimic + basin background sampling.

    Tempered Horvitz-Thompson stratum weights teach tree splits to reject 300-1200 m
    range-front piedmont aprons and steep incised desert washes while preserving
    spatial prior calibration between ranges and basins.
    """
    pos_idx = np.flatnonzero(train_fp_mask & vis_fp)
    slope_clean = np.nan_to_num(slope_fp, nan=0.0)
    slope_p70 = float(np.quantile(slope_clean[train_fp_mask], 0.70))

    near_pool = np.flatnonzero(train_fp_mask & (~vis_fp) & (d_vis_fp >= 3.0) & (d_vis_fp < 12.0))
    steep_pool = np.flatnonzero(
        train_fp_mask & (~vis_fp) & (d_vis_fp >= 12.0) & (slope_clean >= slope_p70)
    )
    flat_pool = np.flatnonzero(
        train_fp_mask & (~vis_fp) & (d_vis_fp >= 12.0) & (slope_clean < slope_p70)
    )

    def _draw(pool: np.ndarray, k: int) -> tuple[np.ndarray, float]:
        if pool.size == 0:
            return pool, 1.0
        if pool.size <= k:
            return pool, 1.0
        chosen = np.sort(rng.choice(pool, size=k, replace=False))
        # Square-root tempered Horvitz-Thompson weight avoids extreme variance while preserving rank calibration
        ht = float(np.sqrt(pool.size / float(k)))
        return chosen, ht

    near_idx, w_near = _draw(near_pool, n_near)
    steep_idx, w_steep = _draw(steep_pool, n_steep_far)
    flat_idx, w_flat = _draw(flat_pool, n_flat_far)

    idx = np.concatenate([pos_idx, near_idx, steep_idx, flat_idx])
    y = np.concatenate(
        [
            np.ones(pos_idx.size, dtype=np.int8),
            np.zeros(near_idx.size + steep_idx.size + flat_idx.size, dtype=np.int8),
        ]
    )
    # Normalize negative mean weight to 1.0 so positive-to-negative balance stays comparable to EXP-1
    neg_w = np.concatenate(
        [
            np.full(near_idx.size, w_near, dtype=np.float32),
            np.full(steep_idx.size, w_steep, dtype=np.float32),
            np.full(flat_idx.size, w_flat, dtype=np.float32),
        ]
    )
    neg_w /= max(float(np.mean(neg_w)), 1e-6)
    sw = np.concatenate([np.ones(pos_idx.size, dtype=np.float32), neg_w])
    return idx, y, sw


def fit_predict_b0_fold(
    mm: np.ndarray,
    fp_mask: np.ndarray,
    fp_ids: np.ndarray,
    train_grid: np.ndarray,
    valid_grid: np.ndarray,
    visible_grid: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Run B0 (31-ch HGB + 2.8 px priority NMS) for one fold; returns (continuous_valid, dots_valid)."""
    rng = np.random.default_rng(seed)
    d_vis_grid = distance_transform_edt(~visible_grid).astype(np.float32)

    fp_flat = fp_ids
    train_fp = train_grid.ravel()[fp_flat]
    valid_fp = valid_grid.ravel()[fp_flat]
    vis_fp = visible_grid.ravel()[fp_flat]
    d_vis_fp = d_vis_grid.ravel()[fp_flat]

    tr_idx, y_tr, _ = _sample_standard_train(train_fp, vis_fp, d_vis_fp, rng, n_neg=180_000)
    X_tr = np.array(mm[tr_idx][:, B0_COLS], dtype=np.float32, copy=True)

    hgb = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=220,
        max_leaf_nodes=63,
        min_samples_leaf=75,
        l2_regularization=2.0,
        early_stopping=False,
        random_state=seed,
    )
    hgb.fit(X_tr, y_tr)
    del X_tr

    val_fp_indices = np.flatnonzero(valid_fp)
    p_val = np.zeros(val_fp_indices.size, dtype=np.float32)
    for s in range(0, val_fp_indices.size, PREDICT_CHUNK):
        sub = val_fp_indices[s : s + PREDICT_CHUNK]
        Xc = np.array(mm[sub][:, B0_COLS], dtype=np.float32)
        p_val[s : s + PREDICT_CHUNK] = hgb.predict_proba(Xc)[:, 1].astype(np.float32)
        del Xc

    cont_grid = np.zeros(fp_mask.shape, dtype=np.float32)
    cont_grid.ravel()[fp_flat[val_fp_indices]] = p_val

    budget_q = int(round(TOTAL_DOT_BUDGET * (val_fp_indices.size / float(fp_flat.size))))
    dots_grid = priority_poisson(
        cont_grid,
        valid_grid & (d_vis_grid > COLLAR_PX),
        budget_q,
        min_dist=2.8,
    ).astype(np.float32)
    gc.collect()
    return cont_grid, dots_grid


def fit_predict_dpgf_surface_fold(
    mm: np.ndarray,
    fp_mask: np.ndarray,
    fp_ids: np.ndarray,
    has_lidar_fp: np.ndarray,
    fp_r_norm: np.ndarray,
    fp_c_norm: np.ndarray,
    train_grid: np.ndarray,
    valid_grid: np.ndarray,
    visible_grid: np.ndarray,
    *,
    deconfound_and_hardneg: bool,
    seed: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit WBG-H1 LiDAR-Completeness Dual Ensemble on one fold and return continuous valid surface.

    When `deconfound_and_hardneg=False` -> EXP-1 continuous surface.
    When `deconfound_and_hardneg=True`  -> EXP-2 / EXP-3 continuous surface (reused by EXP-2 & EXP-3!).
    """
    rng = np.random.default_rng(seed)
    d_vis_grid = distance_transform_edt(~visible_grid).astype(np.float32)

    train_fp = train_grid.ravel()[fp_ids]
    valid_fp = valid_grid.ravel()[fp_ids]
    vis_fp = visible_grid.ravel()[fp_ids]
    d_vis_fp = d_vis_grid.ravel()[fp_ids]
    slope_fp = np.array(mm[:, IDX["org_det_elev_slope"]], dtype=np.float32)

    # Hold out a 12% segment-grouped inner calibration slice of `train` solely for slope-stratified
    # LiDAR-gap quantile alignment (so quantile curves are 100% out-of-bag!).
    vis_train_grid = visible_grid & train_grid
    comp_lbl, n_comp = label(vis_train_grid, structure=np.ones((3, 3), dtype=int))
    cal_seg_ids = set(
        rng.choice(np.arange(1, n_comp + 1), size=max(1, int(0.12 * n_comp)), replace=False).tolist()
    )
    cal_pos_grid = np.isin(comp_lbl, list(cal_seg_ids))
    # Spatial box slice in train for background calibration pixels
    cal_bg_fp = train_fp & (~vis_fp) & (d_vis_fp >= 9.0) & (rng.random(fp_ids.size) < 0.08)
    cal_fp_mask = (cal_pos_grid.ravel()[fp_ids] | cal_bg_fp) & train_fp
    fit_train_fp = train_fp & (~cal_pos_grid.ravel()[fp_ids]) & (~cal_bg_fp)

    residualizer: RegionalResidualizer | None = None
    if deconfound_and_hardneg:
        bg_idx = np.flatnonzero(fit_train_fp & (~vis_fp) & (d_vis_fp >= 15.0))
        residualizer = RegionalResidualizer.fit(mm, bg_idx, fp_r_norm, fp_c_norm, seed=seed)

    # 1. Fit LiDAR-Blind 51-channel specialist across ALL fit_train_fp (maximum structural sample!)
    if deconfound_and_hardneg:
        tr_all_idx, y_all, sw_all = _sample_hardneg_train(
            fit_train_fp, vis_fp, d_vis_fp, slope_fp, rng
        )
    else:
        tr_all_idx, y_all, sw_all = _sample_standard_train(
            fit_train_fp, vis_fp, d_vis_fp, rng, n_neg=180_000
        )

    X_blind = np.array(mm[tr_all_idx][:, NONLIDAR_51_COLS], dtype=np.float32, copy=True)
    if residualizer is not None:
        col_map_51 = {c: j for j, c in enumerate(NONLIDAR_51_COLS)}
        det_el = np.array(mm[tr_all_idx, IDX["org_det_elev"]], dtype=np.float32)
        residualizer.transform_inplace(
            X_blind, col_map_51, fp_r_norm[tr_all_idx], fp_c_norm[tr_all_idx], det_el
        )
    blind_hgb, blind_et, blind_med = _fit_hgb_et_pair(X_blind, y_all, sw_all, seed=seed + 100)
    del X_blind
    gc.collect()

    # 2. Fit Full-Sensor 66-channel specialist on fit_train_fp & has_lidar_fp
    fit_lidar_fp = fit_train_fp & has_lidar_fp
    if deconfound_and_hardneg:
        tr_lid_idx, y_lid, sw_lid = _sample_hardneg_train(
            fit_lidar_fp, vis_fp, d_vis_fp, slope_fp, rng
        )
    else:
        tr_lid_idx, y_lid, sw_lid = _sample_standard_train(
            fit_lidar_fp, vis_fp, d_vis_fp, rng, n_neg=160_000
        )

    X_full = np.array(mm[tr_lid_idx][:, FULL_66_COLS], dtype=np.float32, copy=True)
    if residualizer is not None:
        col_map_66 = {c: j for j, c in enumerate(FULL_66_COLS)}
        det_el_l = np.array(mm[tr_lid_idx, IDX["org_det_elev"]], dtype=np.float32)
        residualizer.transform_inplace(
            X_full, col_map_66, fp_r_norm[tr_lid_idx], fp_c_norm[tr_lid_idx], det_el_l
        )
    full_hgb, full_et, full_med = _fit_hgb_et_pair(X_full, y_lid, sw_lid, seed=seed + 200)
    del X_full
    gc.collect()

    # 3. Compute out-of-bag inner calibration distributions on cal_fp_mask
    cal_lid_idx = np.flatnonzero(cal_fp_mask & has_lidar_fp)
    cal_all_idx = np.flatnonzero(cal_fp_mask)
    p_cal_blind_all = _predict_hgb_et_pair(
        blind_hgb, blind_et, blind_med, mm, cal_all_idx, NONLIDAR_51_COLS, residualizer, fp_r_norm, fp_c_norm
    )
    p_cal_blind_lid = _predict_hgb_et_pair(
        blind_hgb, blind_et, blind_med, mm, cal_lid_idx, NONLIDAR_51_COLS, residualizer, fp_r_norm, fp_c_norm
    )
    p_cal_full_lid = _predict_hgb_et_pair(
        full_hgb, full_et, full_med, mm, cal_lid_idx, FULL_66_COLS, residualizer, fp_r_norm, fp_c_norm
    )
    ref_cal_fused = 0.72 * p_cal_full_lid + 0.28 * p_cal_blind_lid

    # 4. Predict on valid_fp (`valid & has_lidar` gets fused 66+51; `valid & ~has_lidar` gets slope-quantile calibrated 51)
    val_lid_idx = np.flatnonzero(valid_fp & has_lidar_fp)
    val_gap_idx = np.flatnonzero(valid_fp & (~has_lidar_fp))

    p_val_lid_full = _predict_hgb_et_pair(
        full_hgb, full_et, full_med, mm, val_lid_idx, FULL_66_COLS, residualizer, fp_r_norm, fp_c_norm
    )
    p_val_lid_blind = _predict_hgb_et_pair(
        blind_hgb, blind_et, blind_med, mm, val_lid_idx, NONLIDAR_51_COLS, residualizer, fp_r_norm, fp_c_norm
    )
    p_val_lid = 0.72 * p_val_lid_full + 0.28 * p_val_lid_blind

    p_val_gap_raw = _predict_hgb_et_pair(
        blind_hgb, blind_et, blind_med, mm, val_gap_idx, NONLIDAR_51_COLS, residualizer, fp_r_norm, fp_c_norm
    )
    p_val_gap = _slope_stratified_quantile_calibrate(
        src_cal=p_cal_blind_all,
        ref_cal=ref_cal_fused,
        slope_src_cal=slope_fp[cal_all_idx],
        slope_ref_cal=slope_fp[cal_lid_idx],
        src_target=p_val_gap_raw,
        slope_target=slope_fp[val_gap_idx],
    )

    raw_surface = np.zeros(fp_mask.shape, dtype=np.float32)
    raw_surface.ravel()[fp_ids[val_lid_idx]] = p_val_lid
    raw_surface.ravel()[fp_ids[val_gap_idx]] = p_val_gap

    if deconfound_and_hardneg:
        out_surface = directional_strike_sharpen(raw_surface, valid_grid)
    else:
        out_surface = raw_surface

    # Fold-only thresholds for Two-Regime classification (zero valid peek!)
    slope_tr_med = float(np.nanquantile(slope_fp[fit_lidar_fp], 0.40))
    upface_fp = np.array(mm[fit_lidar_fp, IDX["lid_upface_max"]], dtype=np.float32)
    upface_tr_p55 = float(np.nanquantile(upface_fp, 0.55))
    pied_fp = np.array(mm[fit_lidar_fp, IDX["ms_piedmont_inflection"]], dtype=np.float32)
    pied_tr_p55 = float(np.nanquantile(pied_fp, 0.55))

    meta = {
        "slope_tr_q40": slope_tr_med,
        "upface_tr_q55": upface_tr_p55,
        "pied_tr_q55": pied_tr_p55,
        "val_lidar_px": int(val_lid_idx.size),
        "val_gap_px": int(val_gap_idx.size),
    }
    del full_hgb, full_et, blind_hgb, blind_et
    gc.collect()
    return out_surface, meta


def build_regime_masks_and_boost(
    mm: np.ndarray,
    fp_mask: np.ndarray,
    fp_ids: np.ndarray,
    has_lidar_fp: np.ndarray,
    domain_mask: np.ndarray,
    surface_grid: np.ndarray,
    thresholds: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Construct Regime A mask (dip-coupled scarp/piedmont) and Regime B geophysical-boosted surface."""
    dom_fp = domain_mask.ravel()[fp_ids]
    dom_indices = np.flatnonzero(dom_fp)

    slope_v = np.nan_to_num(np.array(mm[dom_indices, IDX["org_det_elev_slope"]], dtype=np.float32), nan=0.0)
    upface_v = np.nan_to_num(np.array(mm[dom_indices, IDX["lid_upface_max"]], dtype=np.float32), nan=0.0)
    pied_v = np.nan_to_num(np.array(mm[dom_indices, IDX["ms_piedmont_inflection"]], dtype=np.float32), nan=0.0)
    has_lid_v = has_lidar_fp[dom_indices]

    reg_a_v = has_lid_v & (
        (slope_v >= thresholds["slope_tr_q40"])
        | (upface_v >= thresholds["upface_tr_q55"])
        | (pied_v >= thresholds["pied_tr_q55"])
    )
    regime_a_mask = np.zeros(fp_mask.shape, dtype=bool)
    regime_a_mask.ravel()[fp_ids[dom_indices]] = reg_a_v

    # Concealed-basin / gap geophysical corroboration boost on Regime B
    updip_g = np.nan_to_num(np.array(mm[dom_indices, IDX["dpgf_grav_updip_1000m"]], dtype=np.float32), nan=0.0)
    updip_mt = np.nan_to_num(np.array(mm[dom_indices, IDX["dpgf_mt_updip_600m"]], dtype=np.float32), nan=0.0)
    hyd_c = np.nan_to_num(np.array(mm[dom_indices, IDX["hyd_conduit_subsurf_x"]], dtype=np.float32), nan=0.0)
    mt_grad = np.nan_to_num(np.array(mm[dom_indices, IDX["ms_mt_claycap_perim"]], dtype=np.float32), nan=0.0)

    def _pos_z(arr: np.ndarray) -> np.ndarray:
        med = float(np.median(arr))
        iqr = max(float(np.percentile(arr, 75) - np.percentile(arr, 25)), 1e-5)
        return np.clip((arr - med) / iqr, 0.0, 3.0).astype(np.float32)

    boost_v = 1.0 + 0.14 * _pos_z(updip_g) + 0.10 * _pos_z(updip_mt) + 0.12 * _pos_z(hyd_c) + 0.08 * _pos_z(mt_grad)
    boost_grid = np.ones(fp_mask.shape, dtype=np.float32)
    boost_grid.ravel()[fp_ids[dom_indices]] = boost_v

    regime_b_surface = (surface_grid * boost_grid).astype(np.float32)
    return regime_a_mask, regime_b_surface


def make_diamond_4fold_partition(
    footprint: np.ndarray,
    catalogue: np.ndarray,
    buffer_px: int = 15,
) -> list[dict[str, Any]]:
    """Complementary 45-degree rotated / radial-diamond 4-fold whole-segment holdout partition.

    Used ONLY when synthesizing the full-footprint submission surface of a promoted arm so
    averaging Quadrant OOF + Diamond OOF eliminates orthogonal fold-boundary seams while
    keeping 100% of predictions genuinely out-of-fold with whole-segment 15-px buffering.
    """
    rows, cols = np.nonzero(footprint)
    r_mid = 0.5 * float(rows.min() + rows.max())
    c_mid = 0.5 * float(cols.min() + cols.max())
    r_span = max(0.5 * float(rows.max() - rows.min()), 1.0)
    c_span = max(0.5 * float(cols.max() - cols.min()), 1.0)

    rr, cc = np.indices(footprint.shape, dtype=np.float32)
    u = (rr - r_mid) / r_span + (cc - c_mid) / c_span
    v = (rr - r_mid) / r_span - (cc - c_mid) / c_span

    raw_zones = [
        (u < 0.0) & (v < 0.0) & footprint,   # North diamond
        (u >= 0.0) & (v < 0.0) & footprint,  # East diamond
        (u < 0.0) & (v >= 0.0) & footprint,  # West diamond
        (u >= 0.0) & (v >= 0.0) & footprint, # South diamond
    ]
    comp_lbl, _ = label(catalogue & footprint, structure=np.ones((3, 3), dtype=int))
    folds: list[dict[str, Any]] = []
    for k, valid in enumerate(raw_zones):
        dist_to_valid = distance_transform_edt(~valid)
        val_plus_buf = dist_to_valid <= buffer_px
        hidden_ids = set(np.unique(comp_lbl[val_plus_buf]).tolist()) - {0}
        hidden_mask = np.isin(comp_lbl, list(hidden_ids))
        visible = (catalogue & footprint) & (~hidden_mask)
        train = footprint & (~val_plus_buf)
        folds.append(
            {
                "fold": k,
                "name": f"Diamond_{k}",
                "valid": valid,
                "train": train,
                "visible": visible,
            }
        )
    return folds
