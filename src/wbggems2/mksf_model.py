"""Multi-Resolution Kernel-Credit Scarp-Flexure (`MKSF-1`) & Coulomb-Relay Model (`WBG-S2`).

Implements:
  - `B0_19ch_CELF28`: Same-instrument 19-band competition control + `d >= 2.8 px` 300 m CELF.
  - `EXP1_MKSF_Core`: 81-ch Multi-Resolution + Dual-Specialist (`Full-81ch` + `Seamless-69ch`
    10m-3DEP unstarved specialist) + Dual-Target (`HGB_Crest` + `HGB_Kernel` expected 300 m
    triangular-kernel credit regressor + `ET_Crest`) + 8-azimuth ridge/halo crest sharpener
    + Two-Regime (`76%` scarp-flexure / `24%` concealed basin-conduit) `d >= 2.8 px` CELF.
  - `EXP2_MKSF_SGMCDualPop`: Adds held-in training-fold pre-2022 USGS SGMC bedrock-fault
    reactivation auxiliary head (`zero` SGMC features at inference).
  - `EXP3_MKSF_VierbeinCoulomb`: Adds strictly fold-visible (`fold_visible`) Mode-II/III
    crack-tip & inter-component en-echelon relay-ramp stress corroboration.
"""
from __future__ import annotations

import gc
import math
from typing import Any

import numpy as np
from scipy.ndimage import (
    convolve,
    distance_transform_edt,
    gaussian_filter,
    label,
    shift,
)
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)

from wbggems1.submodular import emit_celf_submodular
from wbggems2.features import FEATURE_NAMES, IDX, LIDAR_13_NAMES, ORG_19_NAMES

TOTAL_DOT_BUDGET = 37_654
COLLAR_PX = 2.0
MIN_SEP_PX = 2.8
KERNEL_GAMMA = 1.65
REGIME_A_FRAC = 0.76
PREDICT_CHUNK = 300_000

B0_19_COLS: list[int] = [IDX[c] for c in ORG_19_NAMES]
FULL_81_COLS: list[int] = list(range(len(FEATURE_NAMES)))
# Seamless 69-ch stack excludes the 12 NaN-capable 1m LiDAR value bands (`lid_valid` also excluded
# so the 10 m 3DEP + geophysics specialist is 100% invariant to 1 m LiDAR survey boundaries!)
SEAMLESS_68_COLS: list[int] = [
    i for i, c in enumerate(FEATURE_NAMES) if c not in set(LIDAR_13_NAMES)
]


def crest_sharpen_and_dehalo(raw_prob: np.ndarray, fp_mask: np.ndarray) -> np.ndarray:
    """Concentrate diffuse 2D slope aprons onto 1D local fault-strike crests."""
    p = np.where(fp_mask & np.isfinite(raw_prob), np.clip(raw_prob, 0.0, 1.0), 0.0).astype(np.float32)
    # 1. Subtract broad 700 m isotropic mountain-block halo while preserving narrow 1D strands
    halo = gaussian_filter(p, sigma=7.0).astype(np.float32)
    dehalo = np.maximum(0.0, p - np.float32(0.30) * halo)

    # 2. 8-azimuth along-strike 600 m support minus +-250 m cross-strike flanks
    p_sm = gaussian_filter(dehalo, sigma=0.60).astype(np.float32)
    best_ridge = np.zeros_like(p, dtype=np.float32)
    best_nms = np.zeros_like(p, dtype=np.float32)

    for k in range(8):
        theta = k * (math.pi / 8.0)
        ux = float(math.cos(theta))
        uy = float(math.sin(theta))
        nx, ny = -uy, ux

        along = 0.30 * p_sm
        for s_px, wt in ((1.5, 0.21), (3.0, 0.14)):
            along += wt * shift(p_sm, (s_px * uy, s_px * ux), order=1, mode="nearest")
            along += wt * shift(p_sm, (-s_px * uy, -s_px * ux), order=1, mode="nearest")

        f_pos = shift(p_sm, (2.2 * ny, 2.2 * nx), order=1, mode="nearest")
        f_neg = shift(p_sm, (-2.2 * ny, -2.2 * nx), order=1, mode="nearest")
        flank_mean = 0.5 * (f_pos + f_neg)
        flank_max = np.maximum(f_pos, f_neg)

        ridge_k = np.maximum(0.0, along - np.float32(0.36) * flank_mean)
        nms_k = np.clip(p_sm / (flank_max + np.float32(1e-5)), 0.0, 1.15)
        cond = ridge_k > best_ridge
        best_ridge = np.where(cond, ridge_k, best_ridge)
        best_nms = np.where(cond, nms_k, best_nms)

    out = (0.48 * dehalo + 0.52 * best_ridge) * (0.45 + 0.55 * np.minimum(best_nms, 1.0))
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    out[~fp_mask] = 0.0
    return out


def _sample_purged_crest_train(
    mm: np.ndarray,
    train_fp: np.ndarray,
    vis_fp: np.ndarray,
    d_vis_fp: np.ndarray,
    rng: np.random.Generator,
    n_uniform_neg: int = 125_000,
    n_hard_neg: int = 65_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample visible positives + purged-collar (`d_vis >= 3.2 px`) uniform & near-flank negatives."""
    pos_idx = np.flatnonzero(train_fp & vis_fp)
    # Purge 0 < d_vis < 3.2 px so 300 m kernel-credit pixels are NEVER mislabeled as y=0!
    neg_base_mask = train_fp & (~vis_fp) & (d_vis_fp >= 3.2)

    slope10 = np.asarray(mm[:, IDX["dem10_slope_max"]], dtype=np.float32)
    sl_q55 = float(np.quantile(slope10[train_fp], 0.55))

    hard_mask = neg_base_mask & ((d_vis_fp <= 14.0) | (slope10 >= sl_q55))
    uni_mask = neg_base_mask & (~hard_mask)

    uni_pool = np.flatnonzero(uni_mask)
    hard_pool = np.flatnonzero(hard_mask)

    uni_sel = (
        np.sort(rng.choice(uni_pool, size=n_uniform_neg, replace=False))
        if uni_pool.size > n_uniform_neg
        else uni_pool
    )
    hard_sel = (
        np.sort(rng.choice(hard_pool, size=n_hard_neg, replace=False))
        if hard_pool.size > n_hard_neg
        else hard_pool
    )

    idx = np.concatenate([pos_idx, uni_sel, hard_sel])
    y = np.concatenate(
        [
            np.ones(pos_idx.size, dtype=np.int8),
            np.zeros(uni_sel.size + hard_sel.size, dtype=np.int8),
        ]
    )
    sw = np.concatenate(
        [
            np.ones(pos_idx.size, dtype=np.float32),
            np.ones(uni_sel.size, dtype=np.float32),
            np.full(hard_sel.size, 0.58, dtype=np.float32),
        ]
    )
    return idx, y, sw


def _sample_kernel_credit_train(
    mm: np.ndarray,
    train_fp: np.ndarray,
    vis_fp: np.ndarray,
    d_vis_fp: np.ndarray,
    rng: np.random.Generator,
    n_flank: int = 45_000,
    n_zero: int = 155_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample continuous 300 m triangular-kernel expected credit target `y_kern = max(0, 1 - d/3)`."""
    pos_idx = np.flatnonzero(train_fp & vis_fp)
    flank_pool = np.flatnonzero(train_fp & (~vis_fp) & (d_vis_fp > 0.0) & (d_vis_fp < 3.0))
    zero_pool = np.flatnonzero(train_fp & (~vis_fp) & (d_vis_fp >= 3.2))

    flank_sel = (
        np.sort(rng.choice(flank_pool, size=n_flank, replace=False))
        if flank_pool.size > n_flank
        else flank_pool
    )
    zero_sel = (
        np.sort(rng.choice(zero_pool, size=n_zero, replace=False))
        if zero_pool.size > n_zero
        else zero_pool
    )

    idx = np.concatenate([pos_idx, flank_sel, zero_sel])
    y_kern = np.maximum(0.0, 1.0 - d_vis_fp[idx] / 3.0).astype(np.float32)
    return idx, y_kern


def _quantile_align(src_cal: np.ndarray, ref_cal: np.ndarray, src_eval: np.ndarray) -> np.ndarray:
    if src_eval.size == 0 or src_cal.size < 200 or ref_cal.size < 200:
        return src_eval.astype(np.float32)
    q = np.linspace(0.0, 1.0, 501)
    sq = np.quantile(src_cal, q)
    rq = np.quantile(ref_cal, q)
    sq_u, u_idx = np.unique(sq, return_index=True)
    return np.interp(src_eval, sq_u, rq[u_idx]).astype(np.float32)


def fit_predict_b0_celf28_fold(
    mm: np.ndarray,
    fp_mask: np.ndarray,
    fp_ids: np.ndarray,
    train_grid: np.ndarray,
    valid_grid: np.ndarray,
    visible_grid: np.ndarray,
    *,
    budget_dots: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Refitted 19-band competition control using identical `min_sep=2.8` 300 m CELF emitter."""
    rng = np.random.default_rng(seed)
    d_vis_grid = distance_transform_edt(~(visible_grid & train_grid)).astype(np.float32)
    d_vis_all = distance_transform_edt(~visible_grid).astype(np.float32)

    train_fp = train_grid.ravel()[fp_ids]
    valid_fp = valid_grid.ravel()[fp_ids]
    vis_fp = (visible_grid & train_grid).ravel()[fp_ids]
    d_vis_fp = d_vis_grid.ravel()[fp_ids]

    pos_idx = np.flatnonzero(train_fp & vis_fp)
    neg_pool = np.flatnonzero(train_fp & (~vis_fp) & (d_vis_fp >= 3.2))
    neg_sel = (
        np.sort(rng.choice(neg_pool, size=min(180_000, neg_pool.size), replace=False))
        if neg_pool.size > 180_000
        else neg_pool
    )
    tr_idx = np.concatenate([pos_idx, neg_sel])
    y_tr = np.concatenate([np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_sel.size, dtype=np.int8)])

    X_tr = np.array(mm[tr_idx][:, B0_19_COLS], dtype=np.float32, copy=True)
    hgb = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=220,
        max_leaf_nodes=63,
        min_samples_leaf=75,
        l2_regularization=2.5,
        early_stopping=False,
        random_state=seed,
    )
    hgb.fit(X_tr, y_tr)
    del X_tr

    val_idx = np.flatnonzero(valid_fp)
    p_val = np.zeros(val_idx.size, dtype=np.float32)
    for s in range(0, val_idx.size, PREDICT_CHUNK):
        sub = val_idx[s : s + PREDICT_CHUNK]
        Xc = np.array(mm[sub][:, B0_19_COLS], dtype=np.float32)
        p_val[s : s + PREDICT_CHUNK] = hgb.predict_proba(Xc)[:, 1].astype(np.float32)
        del Xc

    surf = np.zeros(fp_mask.shape, dtype=np.float32)
    surf.ravel()[fp_ids[val_idx]] = p_val
    elig = valid_grid & fp_mask & (d_vis_all > COLLAR_PX)
    w_grid = np.where(elig, np.power(np.clip(surf, 0.0, 1.0), KERNEL_GAMMA), 0.0).astype(np.float32)
    dots, _ = emit_celf_submodular(
        surf,
        elig,
        budget_dots,
        weight_grid=w_grid,
        min_separation_px=MIN_SEP_PX,
        candidate_oversample=16,
    )
    del hgb
    gc.collect()
    return surf, (dots > 0.0).astype(np.uint8)


def fit_predict_mksf_dual_fold(
    mm: np.ndarray,
    fp_mask: np.ndarray,
    fp_ids: np.ndarray,
    lid_valid_fp: np.ndarray,
    train_grid: np.ndarray,
    valid_grid: np.ndarray,
    visible_grid: np.ndarray,
    sgmc_grid: np.ndarray | None,
    *,
    seed: int,
) -> tuple[np.ndarray, np.ndarray | None, dict[str, Any]]:
    """Fit MKSF-1 (`EXP-1`) and optional SGMC-DualPop (`EXP-2`) on one fold in a single pass.

    Strictly touches ONLY `train_grid` and `visible_grid & train_grid`.
    `EXP-1` never touches `sgmc_grid`. `EXP-2` uses `sgmc_grid & train_grid` strictly as held-in
    auxiliary training positives (`w = 0.32`), NEVER as an input feature at training or inference.
    """
    rng = np.random.default_rng(seed)
    vis_train_grid = visible_grid & train_grid
    d_vis_train_grid = distance_transform_edt(~vis_train_grid).astype(np.float32)

    train_fp = train_grid.ravel()[fp_ids]
    valid_fp = valid_grid.ravel()[fp_ids]
    vis_fp = vis_train_grid.ravel()[fp_ids]
    d_vis_fp = d_vis_train_grid.ravel()[fp_ids]

    # Hold out 10% of training components solely for OOB LiDAR-vs-Seamless quantile alignment
    comp_lbl, n_comp = label(vis_train_grid, structure=np.ones((3, 3), dtype=int))
    cal_ids = set(
        rng.choice(np.arange(1, n_comp + 1), size=max(1, int(0.10 * n_comp)), replace=False).tolist()
    )
    cal_pos_fp = np.isin(comp_lbl, list(cal_ids)).ravel()[fp_ids]
    cal_bg_fp = train_fp & (~vis_fp) & (d_vis_fp >= 4.0) & (rng.random(fp_ids.size) < 0.05)
    cal_fp = (cal_pos_fp | cal_bg_fp) & train_fp
    fit_fp = train_fp & (~cal_fp)

    tr_cls_idx, y_cls, sw_cls = _sample_purged_crest_train(mm, fit_fp, vis_fp, d_vis_fp, rng)
    tr_krn_idx, y_krn = _sample_kernel_credit_train(mm, fit_fp, vis_fp, d_vis_fp, rng)

    # --- Specialist 1: Seamless 68-ch (100% coverage 10m 3DEP + Geophys + Hydro, zero 1m LiDAR) ---
    X_s_cls = np.array(mm[tr_cls_idx][:, SEAMLESS_68_COLS], dtype=np.float32, copy=True)
    hgb_s_cls = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=260,
        max_leaf_nodes=63,
        min_samples_leaf=60,
        l2_regularization=2.5,
        early_stopping=False,
        random_state=seed + 11,
    )
    hgb_s_cls.fit(X_s_cls, y_cls, sample_weight=sw_cls)
    del X_s_cls

    X_s_krn = np.array(mm[tr_krn_idx][:, SEAMLESS_68_COLS], dtype=np.float32, copy=True)
    hgb_s_krn = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_iter=220,
        max_leaf_nodes=63,
        min_samples_leaf=60,
        l2_regularization=3.0,
        early_stopping=False,
        random_state=seed + 23,
    )
    hgb_s_krn.fit(X_s_krn, y_krn)
    del X_s_krn
    gc.collect()

    # --- Specialist 2: Full 81-ch (1m LiDAR + 10m 3DEP + Geophys + Hydro) ---
    X_f_cls = np.array(mm[tr_cls_idx][:, FULL_81_COLS], dtype=np.float32, copy=True)
    hgb_f_cls = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=260,
        max_leaf_nodes=63,
        min_samples_leaf=60,
        l2_regularization=2.5,
        early_stopping=False,
        random_state=seed + 37,
    )
    hgb_f_cls.fit(X_f_cls, y_cls, sample_weight=sw_cls)

    # ExtraTrees diversity partner on median-imputed Full-81ch
    medians_81 = np.nanmedian(X_f_cls, axis=0).astype(np.float32)
    medians_81 = np.where(np.isfinite(medians_81), medians_81, 0.0).astype(np.float32)
    for j in range(X_f_cls.shape[1]):
        bad = ~np.isfinite(X_f_cls[:, j])
        if np.any(bad):
            X_f_cls[bad, j] = medians_81[j]
    et_f_cls = ExtraTreesClassifier(
        n_estimators=80,
        max_depth=18,
        min_samples_leaf=20,
        max_features="sqrt",
        n_jobs=2,
        random_state=seed + 53,
    )
    et_f_cls.fit(X_f_cls, y_cls, sample_weight=sw_cls)
    del X_f_cls

    X_f_krn = np.array(mm[tr_krn_idx][:, FULL_81_COLS], dtype=np.float32, copy=True)
    hgb_f_krn = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_iter=220,
        max_leaf_nodes=63,
        min_samples_leaf=60,
        l2_regularization=3.0,
        early_stopping=False,
        random_state=seed + 71,
    )
    hgb_f_krn.fit(X_f_krn, y_krn)
    del X_f_krn
    gc.collect()

    # EXP-2 auxiliary SGMC bedrock reactivation head (strictly held-in train_fp only!)
    hgb_sgmc: HistGradientBoostingClassifier | None = None
    sgmc_aux_count = 0
    if sgmc_grid is not None:
        sgmc_fp = (sgmc_grid & train_grid).ravel()[fp_ids]
        strain_col = np.asarray(mm[:, IDX["org_geod_shearrate"]], dtype=np.float32)
        strain_q35 = float(np.quantile(strain_col[fit_fp], 0.35))
        hyd_col = np.asarray(mm[:, IDX["cgmd_blind_conduit_index"]], dtype=np.float32)
        sgmc_aux_idx = np.flatnonzero(
            fit_fp & sgmc_fp & (~vis_fp) & (d_vis_fp >= 3.5) & ((strain_col >= strain_q35) | (hyd_col > 0.05))
        )
        sgmc_aux_count = int(sgmc_aux_idx.size)
        keep_neg = ~sgmc_fp[tr_cls_idx] | (y_cls == 1)
        base_idx = tr_cls_idx[keep_neg]
        base_y = y_cls[keep_neg]
        base_sw = sw_cls[keep_neg]

        dual_idx = np.concatenate([base_idx, sgmc_aux_idx])
        dual_y = np.concatenate([base_y, np.ones(sgmc_aux_idx.size, dtype=np.int8)])
        dual_sw = np.concatenate([base_sw, np.full(sgmc_aux_idx.size, 0.32, dtype=np.float32)])

        X_dual = np.array(mm[dual_idx][:, SEAMLESS_68_COLS], dtype=np.float32, copy=True)
        hgb_sgmc = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=220,
            max_leaf_nodes=63,
            min_samples_leaf=70,
            l2_regularization=3.0,
            early_stopping=False,
            random_state=seed + 97,
        )
        hgb_sgmc.fit(X_dual, dual_y, sample_weight=dual_sw)
        del X_dual
        gc.collect()

    def _predict_seamless_pair(indices: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
        n = indices.size
        out1 = np.zeros(n, dtype=np.float32)
        out2 = np.zeros(n, dtype=np.float32) if hgb_sgmc is not None else None
        for s in range(0, n, PREDICT_CHUNK):
            sub = indices[s : s + PREDICT_CHUNK]
            Xs = np.array(mm[sub][:, SEAMLESS_68_COLS], dtype=np.float32)
            p_c = hgb_s_cls.predict_proba(Xs)[:, 1].astype(np.float32)
            p_k = np.clip(hgb_s_krn.predict(Xs), 0.0, 1.0).astype(np.float32)
            score_s = 0.64 * p_c + 0.36 * p_k
            out1[s : s + PREDICT_CHUNK] = score_s
            if hgb_sgmc is not None and out2 is not None:
                p_sg = hgb_sgmc.predict_proba(Xs)[:, 1].astype(np.float32)
                out2[s : s + PREDICT_CHUNK] = 0.80 * score_s + 0.20 * p_sg
            del Xs
        return out1, out2

    def _predict_full(indices: np.ndarray) -> np.ndarray:
        n = indices.size
        out = np.zeros(n, dtype=np.float32)
        for s in range(0, n, PREDICT_CHUNK):
            sub = indices[s : s + PREDICT_CHUNK]
            Xf = np.array(mm[sub][:, FULL_81_COLS], dtype=np.float32, copy=True)
            p_hc = hgb_f_cls.predict_proba(Xf)[:, 1].astype(np.float32)
            p_hk = np.clip(hgb_f_krn.predict(Xf), 0.0, 1.0).astype(np.float32)
            for j in range(Xf.shape[1]):
                bad = ~np.isfinite(Xf[:, j])
                if np.any(bad):
                    Xf[bad, j] = medians_81[j]
            p_et = et_f_cls.predict_proba(Xf)[:, 1].astype(np.float32)
            out[s : s + PREDICT_CHUNK] = 0.48 * p_hc + 0.30 * p_hk + 0.22 * p_et
            del Xf
        return out

    # Calibrate Seamless-68ch onto the fused LiDAR-present distribution using OOB `cal_fp`
    cal_all_idx = np.flatnonzero(cal_fp)
    lid_in_cal = lid_valid_fp[cal_all_idx]
    cal_lid_idx = cal_all_idx[lid_in_cal]
    cal_s1_all, cal_s2_all = _predict_seamless_pair(cal_all_idx)
    cal_s1_lid = cal_s1_all[lid_in_cal]
    cal_f_lid = _predict_full(cal_lid_idx)
    cal_ref1_lid = 0.62 * cal_f_lid + 0.38 * cal_s1_lid

    val_lid_idx = np.flatnonzero(valid_fp & lid_valid_fp)
    val_gap_idx = np.flatnonzero(valid_fp & (~lid_valid_fp))

    val_s1_lid, val_s2_lid = _predict_seamless_pair(val_lid_idx)
    val_f_lid = _predict_full(val_lid_idx)
    p_val1_lid = 0.62 * val_f_lid + 0.38 * val_s1_lid

    val_s1_gap, val_s2_gap = _predict_seamless_pair(val_gap_idx)
    p_val1_gap = _quantile_align(cal_s1_all, cal_ref1_lid, val_s1_gap)

    raw_surf1 = np.zeros(fp_mask.shape, dtype=np.float32)
    raw_surf1.ravel()[fp_ids[val_lid_idx]] = np.clip(p_val1_lid, 0.0, 1.0)
    raw_surf1.ravel()[fp_ids[val_gap_idx]] = np.clip(p_val1_gap, 0.0, 1.0)
    sharp_surf1 = crest_sharpen_and_dehalo(raw_surf1, valid_grid & fp_mask)
    del raw_surf1

    sharp_surf2: np.ndarray | None = None
    if cal_s2_all is not None and val_s2_lid is not None and val_s2_gap is not None:
        cal_s2_lid = cal_s2_all[lid_in_cal]
        cal_ref2_lid = 0.56 * cal_f_lid + 0.44 * cal_s2_lid
        p_val2_lid = 0.56 * val_f_lid + 0.44 * val_s2_lid
        p_val2_gap = _quantile_align(cal_s2_all, cal_ref2_lid, val_s2_gap)
        raw_surf2 = np.zeros(fp_mask.shape, dtype=np.float32)
        raw_surf2.ravel()[fp_ids[val_lid_idx]] = np.clip(p_val2_lid, 0.0, 1.0)
        raw_surf2.ravel()[fp_ids[val_gap_idx]] = np.clip(p_val2_gap, 0.0, 1.0)
        sharp_surf2 = crest_sharpen_and_dehalo(raw_surf2, valid_grid & fp_mask)
        del raw_surf2

    # Fold-only thresholds for Two-Regime emission (computed strictly on fit_fp!)
    sl10_tr = np.asarray(mm[fit_fp, IDX["dem10_slope_max"]], dtype=np.float32)
    mono_tr = np.asarray(mm[fit_fp, IDX["pjmf_mono_flex_10m"]], dtype=np.float32)
    meta = {
        "sl10_q38": float(np.quantile(sl10_tr, 0.38)),
        "mono_q60": float(np.quantile(mono_tr, 0.60)),
        "sgmc_aux_positives": sgmc_aux_count,
        "val_lidar_px": int(val_lid_idx.size),
        "val_gap_px": int(val_gap_idx.size),
    }

    gc.collect()
    return sharp_surf1, sharp_surf2, meta


def compute_visible_coulomb_lobes(visible_grid: np.ndarray, fp_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute strictly fold-visible off-fault crack-tip cones & inter-component relay bridges.

    Touches ONLY `visible_grid` and `fp_mask` (`0` withheld fault pixels ever seen!).
    """
    vis = (visible_grid > 0) & fp_mask
    h, w = vis.shape
    tip_field = np.zeros((h, w), dtype=np.float32)
    relay_field = np.zeros((h, w), dtype=np.float32)
    if not np.any(vis):
        return tip_field, relay_field

    comp, n_comp = label(vis, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)

    # Keep genuine fault strands >= 5 px (500 m) to suppress single-pixel noise spurs
    keep_comp = sizes >= 5
    keep_comp[0] = False
    vis_clean = keep_comp[comp]
    if not np.any(vis_clean):
        return tip_field, relay_field

    # 1. Degree-1 morphological endpoints after 1-iteration spur pruning
    nbr_kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int16)
    deg = convolve(vis_clean.astype(np.int16), nbr_kernel, mode="constant", cval=0)
    # Prune 1-px spurs once
    pruned = vis_clean & ~((deg == 1) & (sizes[comp] > 6))
    if not np.any(pruned):
        pruned = vis_clean
    deg2 = convolve(pruned.astype(np.int16), nbr_kernel, mode="constant", cval=0)
    tips_yx = np.argwhere(pruned & (deg2 <= 1))

    # Local patch offsets [-22..22] (2.2 km forward cone)
    R = 22
    yy_p, xx_p = np.mgrid[-R : R + 1, -R : R + 1].astype(np.float32)
    dist_p = np.hypot(yy_p, xx_p)

    for tr, tc in tips_yx:
        cid = int(comp[tr, tc])
        if cid == 0:
            continue
        # Estimate outward tangent vector from component pixels within 7 px of tip
        r0, r1 = max(0, tr - 7), min(h, tr + 8)
        c0, c1 = max(0, tc - 7), min(w, tc + 8)
        sub_y, sub_x = np.nonzero(comp[r0:r1, c0:c1] == cid)
        if sub_y.size < 3:
            continue
        dy = float(tr - (r0 + sub_y.mean()))
        dx = float(tc - (c0 + sub_x.mean()))
        norm = math.hypot(dy, dx)
        if norm < 0.5:
            continue
        uy, ux = dy / norm, dx / norm

        pr0, pr1 = max(0, tr - R), min(h, tr + R + 1)
        pc0, pc1 = max(0, tc - R), min(w, tc + R + 1)
        sy0, sy1 = pr0 - (tr - R), pr1 - (tr - R)
        sx0, sx1 = pc0 - (tc - R), pc1 - (tc - R)

        d_sub = dist_p[sy0:sy1, sx0:sx1]
        proj_along = yy_p[sy0:sy1, sx0:sx1] * uy + xx_p[sy0:sy1, sx0:sx1] * ux
        cos_ang = proj_along / (d_sub + np.float32(1e-5))
        # Forward Mode-II/III splay & propagation cone (`cos >= 0.78`, `2.5 <= d <= 22 px`)
        cone = np.clip((cos_ang - 0.78) / 0.22, 0.0, 1.0) * (
            (d_sub >= 2.5) & (d_sub <= float(R))
        )
        lobe = (cone / (1.0 + d_sub / 8.0)).astype(np.float32)
        np.maximum(tip_field[pr0:pr1, pc0:pc1], lobe, out=tip_field[pr0:pr1, pc0:pc1])

    # 2. Inter-component en-echelon relay-ramp overlap via 6 deterministic hash partitions
    comp_ids = np.arange(n_comp + 1, dtype=np.int64)
    for b in range(6):
        # Multiplicative hash splits distinct component IDs across 6 draws (1 - 2^-6 = 98.44% pair separation)
        bit_b = (((comp_ids * 2654435761 + b * 1013904223) >> (b + 3)) & 1).astype(bool)
        bit_b[0] = False
        mask_a = keep_comp & bit_b
        mask_b = keep_comp & (~bit_b)
        grid_a = mask_a[comp]
        grid_b = mask_b[comp]
        if not np.any(grid_a) or not np.any(grid_b):
            continue
        da = distance_transform_edt(~grid_a).astype(np.float32)
        db = distance_transform_edt(~grid_b).astype(np.float32)
        in_relay = (da >= 2.2) & (db >= 2.2) & (da <= 16.0) & (db <= 16.0) & ((da + db) <= 24.0)
        bridge = np.where(in_relay, 1.0 / (1.0 + (da + db) / 10.0), 0.0).astype(np.float32)
        np.maximum(relay_field, bridge, out=relay_field)

    tip_field[~fp_mask] = 0.0
    relay_field[~fp_mask] = 0.0
    return tip_field, relay_field


def apply_coulomb_corroboration(
    backbone_surface: np.ndarray,
    visible_grid: np.ndarray,
    fp_mask: np.ndarray,
    domain_mask: np.ndarray,
) -> np.ndarray:
    """Bayes-odds boost of backbone surface where visible tip/relay stress is physically corroborated."""
    tip_f, relay_f = compute_visible_coulomb_lobes(visible_grid, fp_mask)
    dom = domain_mask & fp_mask
    if not np.any(dom):
        return backbone_surface.copy()
    p = np.clip(backbone_surface, 0.0, 0.999).astype(np.float32)
    # Require independent physical backbone support (`p >= q_60`) before Coulomb stress boosts!
    q60 = float(np.quantile(p[dom], 0.60))
    q90 = max(float(np.quantile(p[dom], 0.90)), q60 + 1e-4)
    phys_gate = np.clip((p - q60) / (q90 - q60), 0.0, 1.0).astype(np.float32)

    lr_mult = 1.0 + phys_gate * (2.10 * tip_f + 1.35 * relay_f)
    odds = p / np.maximum(1.0 - p, 1e-4)
    post_odds = odds * lr_mult
    out = (post_odds / (1.0 + post_odds)).astype(np.float32)
    out[~dom] = p[~dom]
    out[~fp_mask] = 0.0
    return out


def emit_two_regime_mksf_dots(
    mm: np.ndarray,
    fp_mask: np.ndarray,
    fp_ids: np.ndarray,
    surface_grid: np.ndarray,
    domain_mask: np.ndarray,
    visible_grid: np.ndarray,
    thresholds: dict[str, float],
    budget_dots: int,
) -> tuple[np.ndarray, dict[str, int]]:
    """Two-Regime (`76%` Scarp-Flexure / `24%` Concealed-Conduit) `min_sep=2.8` 300 m CELF emitter."""
    d_vis = distance_transform_edt(~visible_grid).astype(np.float32)
    elig = domain_mask & fp_mask & (d_vis > COLLAR_PX)
    if budget_dots <= 0 or not np.any(elig):
        return np.zeros(fp_mask.shape, dtype=np.uint8), {"regime_a_dots": 0, "regime_b_dots": 0}

    dom_fp = elig.ravel()[fp_ids]
    dom_idx = np.flatnonzero(dom_fp)

    sl10 = np.asarray(mm[dom_idx, IDX["dem10_slope_max"]], dtype=np.float32)
    mono = np.asarray(mm[dom_idx, IDX["pjmf_mono_flex_10m"]], dtype=np.float32)
    reg_a_fp = (sl10 >= thresholds["sl10_q38"]) | (mono >= thresholds["mono_q60"])

    reg_a_mask = np.zeros(fp_mask.shape, dtype=bool)
    reg_a_mask.ravel()[fp_ids[dom_idx]] = reg_a_fp
    reg_a_elig = elig & reg_a_mask
    reg_b_elig = elig & (~reg_a_mask)

    budget_a = int(round(budget_dots * REGIME_A_FRAC))
    w_a = np.where(elig, np.power(np.clip(surface_grid, 0.0, 1.0), KERNEL_GAMMA), 0.0).astype(np.float32)
    dots_a, cov_a = emit_celf_submodular(
        surface_grid,
        reg_a_elig,
        budget_a,
        weight_grid=w_a,
        min_separation_px=MIN_SEP_PX,
        candidate_oversample=16,
    )
    placed_a = int((dots_a > 0.0).sum())

    # Regime B: concealed basins / hydrothermal & cross-gradient corridors outside Regime A disks
    hyd_b = np.asarray(mm[dom_idx, IDX["cgmd_blind_conduit_index"]], dtype=np.float32)
    xg_b = np.asarray(mm[dom_idx, IDX["cgmd_crossgrad_grav_mag"]], dtype=np.float32)

    def _rz(v: np.ndarray) -> np.ndarray:
        m = float(np.median(v))
        s = max(float(np.percentile(v, 75) - np.percentile(v, 25)), 1e-5)
        return np.clip((v - m) / s, 0.0, 3.0).astype(np.float32)

    boost_vec = 1.0 + 0.18 * _rz(hyd_b) + 0.12 * _rz(xg_b)
    boost_grid = np.ones(fp_mask.shape, dtype=np.float32)
    boost_grid.ravel()[fp_ids[dom_idx]] = boost_vec
    surf_b = np.clip(surface_grid * boost_grid, 0.0, 1.0).astype(np.float32)
    w_b = np.where(elig, np.power(surf_b, KERNEL_GAMMA), 0.0).astype(np.float32)

    rem_budget = budget_dots - placed_a
    # Allow fallback into remaining eligible pixels if strict Regime B pool is smaller than rem_budget
    dots_b, cov_ab = emit_celf_submodular(
        surf_b,
        reg_b_elig,
        rem_budget,
        weight_grid=w_b,
        coverage_init=cov_a,
        min_separation_px=MIN_SEP_PX,
        candidate_oversample=16,
    )
    combined = ((dots_a > 0.0) | (dots_b > 0.0)).astype(np.uint8)

    still_needed = budget_dots - int(combined.sum())
    if still_needed > 0:
        dots_fill, _ = emit_celf_submodular(
            surf_b,
            elig & (combined == 0),
            still_needed,
            weight_grid=w_b,
            coverage_init=cov_ab,
            min_separation_px=MIN_SEP_PX,
            candidate_oversample=16,
        )
        combined = ((combined > 0) | (dots_fill > 0.0)).astype(np.uint8)

    return combined, {"regime_a_dots": placed_a, "regime_b_dots": int(combined.sum()) - placed_a}
