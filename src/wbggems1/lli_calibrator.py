"""Empirical Live-Ledger Inversion (LLI) Calibrator over all 118 ORGANIZER-CONFIRMED rasters.

Protocol Rule 3 Compliance:
Every output of this module is strictly labeled `LLI-PROJECTION (empirical LOO-calibrated
projection on n=118 ORGANIZER-CONFIRMED rasters, NOT an organizer-confirmed score)`.
It is NEVER used to alter model training or override `SegmentHoldout` (`HOLDOUT-DTI`);
it serves solely as a forensic diagnostic explaining why sparse, collar-clean ridges
survived DrivenData's global `FP_w` denominator while dense continuous surfaces collapsed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

from wbggems1.paths import raw_data_dir, registry_cache_dir, repo_root


@dataclass
class LLICalibrator:
    feature_names: list[str]
    mean: np.ndarray
    std: np.ndarray
    coef: np.ndarray
    intercept: float
    loo_mae: float
    loo_rmse: float
    loo_spearman: float
    n_scored: int

    def extract_descriptor(
        self,
        arr: np.ndarray,
        fp_mask: np.ndarray,
        d_cat: np.ndarray,
        has_lidar_grid: np.ndarray,
        slope_grid: np.ndarray,
        ref_3px_near: np.ndarray,
    ) -> np.ndarray:
        vals = np.where(fp_mask & np.isfinite(arr), np.clip(arr, 0.0, 1.0), 0.0).astype(np.float32)
        pos = vals > 0.0
        n_pos = int(np.count_nonzero(pos))
        total_mass = float(vals.sum())
        n_fp = float(np.count_nonzero(fp_mask))

        frac_active = n_pos / n_fp
        mass_frac = total_mass / n_fp
        is_binary = float(np.count_nonzero((vals > 0.0) & (vals < 0.999)) / max(n_pos, 1) < 0.05)
        collar_waste_frac = float(vals[fp_mask & (d_cat <= 2.0)].sum() / max(total_mass, 1e-6))
        mid_band_frac = float(vals[fp_mask & (d_cat > 2.0) & (d_cat <= 12.0)].sum() / max(total_mass, 1e-6))
        far_band_frac = float(vals[fp_mask & (d_cat > 12.0)].sum() / max(total_mass, 1e-6))
        lidar_share = float(vals[fp_mask & has_lidar_grid].sum() / max(total_mass, 1e-6))
        mean_slope = float((vals[fp_mask] * slope_grid[fp_mask]).sum() / max(total_mass, 1e-6))
        ref_overlap = float(vals[fp_mask & ref_3px_near].sum() / max(total_mass, 1e-6))

        # Sweet-spot dot-mass bell around ~38k dots (log-ratio distance)
        log_mass = float(np.log1p(total_mass))
        mass_sweet = float(np.exp(-0.5 * ((log_mass - np.log1p(37654.0)) / 0.85) ** 2))

        return np.array(
            [
                log_mass,
                frac_active,
                mass_frac,
                is_binary,
                collar_waste_frac,
                mid_band_frac,
                far_band_frac,
                lidar_share,
                mean_slope,
                ref_overlap,
                mass_sweet,
                mass_sweet * (1.0 - collar_waste_frac),
            ],
            dtype=np.float64,
        )

    def project(
        self,
        arr: np.ndarray,
        fp_mask: np.ndarray,
        d_cat: np.ndarray,
        has_lidar_grid: np.ndarray,
        slope_grid: np.ndarray,
        ref_3px_near: np.ndarray,
    ) -> dict[str, Any]:
        x = self.extract_descriptor(arr, fp_mask, d_cat, has_lidar_grid, slope_grid, ref_3px_near)
        xz = (x - self.mean) / self.std
        pred = float(np.clip(xz @ self.coef + self.intercept, 0.0, 1.0))
        return {
            "label": (
                f"LLI-PROJECTION (empirical Ridge on n={self.n_scored} ORGANIZER-CONFIRMED rasters; "
                f"LOO MAE={self.loo_mae:.4f}, LOO Spearman={self.loo_spearman:.3f}; NOT an organizer score)"
            ),
            "projected_value": round(pred, 4),
            "loo_mae": round(self.loo_mae, 4),
            "approx_interval_pm_1mae": [round(max(0.0, pred - self.loo_mae), 4), round(pred + self.loo_mae, 4)],
            "descriptors": {k: round(float(v), 5) for k, v in zip(self.feature_names, x)},
        }


def fit_lli_calibrator() -> tuple[LLICalibrator, dict[str, Any]]:
    rdir = raw_data_dir()
    rcache = registry_cache_dir()
    root = repo_root()

    with rasterio.open(rdir / "sample_submission.tif") as ds:
        fp_mask = np.isfinite(ds.read(1))
    with rasterio.open(rdir / "existing_faults.tif") as ds:
        cat_mask = (ds.read(1) > 0) & fp_mask
    d_cat = distance_transform_edt(~cat_mask).astype(np.float32)

    with rasterio.open(rdir / "training_features.tif") as ds:
        slope_raw = ds.read(19).astype(np.float32)
        slope_grid = np.where((np.abs(slope_raw) < 1e30) & np.isfinite(slope_raw) & fp_mask, slope_raw, 0.0)

    with rasterio.open(rdir / "external" / "lidar_scarp_features_u8.tif") as ds:
        has_lidar_grid = (ds.read(12) > 0) & fp_mask

    # Reference structural ridge anchor: H23-B pure 3DEP scarp ridge (non-H19 independent topological prior)
    h23_path = (
        rcache
        / "data/registry/scored/GEMSDOE22__gems22-h23-b-dti-optimal-emission-10pct-20261002-86176698-nan.tif"
    )
    if not h23_path.exists():
        h23_path = (
            rcache
            / "data/registry/scored/GEMSDOE32__gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
        )
    with rasterio.open(h23_path) as ds:
        h23_pos = (np.nan_to_num(ds.read(1), nan=0.0) > 0.0) & fp_mask
    ref_3px_near = distance_transform_edt(~h23_pos) <= 3.0

    scored_reg = json.loads((root / "registry" / "wbg_h1" / "scored_registry.json").read_text())
    entries = scored_reg["entries"] if isinstance(scored_reg, dict) and "entries" in scored_reg else scored_reg

    fnames = [
        "log_mass",
        "frac_active",
        "mass_frac",
        "is_binary",
        "collar_waste_frac",
        "mid_band_frac",
        "far_band_frac",
        "lidar_share",
        "mean_slope",
        "h23_scarp_3px_share",
        "mass_sweet_bell",
        "clean_sweet_bell",
    ]
    dummy = LLICalibrator(fnames, np.zeros(12), np.ones(12), np.zeros(12), 0.0, 0.0, 0.0, 0.0, 0)

    X_rows: list[np.ndarray] = []
    y_vals: list[float] = []
    row_meta: list[dict[str, Any]] = []

    for e in entries:
        rel = e.get("local") or e.get("cache_file") or e.get("filename")
        score = e.get("score") if "score" in e else e.get("live_dti")
        if rel is None or score is None:
            continue
        p = rcache / rel
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            arr = ds.read(1)
        desc = dummy.extract_descriptor(arr, fp_mask, d_cat, has_lidar_grid, slope_grid, ref_3px_near)
        X_rows.append(desc)
        y_vals.append(float(score))
        row_meta.append(
            {
                "id": e.get("name", rel),
                "site": e.get("repo") or e.get("site", ""),
                "live_dti": float(score),
                "log_mass": round(float(desc[0]), 4),
                "collar_waste_frac": round(float(desc[4]), 4),
            }
        )

    X = np.vstack(X_rows)
    y = np.array(y_vals, dtype=np.float64)
    n = len(y)

    # Exact Leave-One-Out CV
    loo_preds = np.zeros(n, dtype=np.float64)
    for i in range(n):
        m_tr = np.ones(n, dtype=bool)
        m_tr[i] = False
        mu = X[m_tr].mean(axis=0)
        sd = np.maximum(X[m_tr].std(axis=0), 1e-8)
        reg = Ridge(alpha=6.0)
        reg.fit((X[m_tr] - mu) / sd, y[m_tr])
        loo_preds[i] = float(np.clip(((X[i] - mu) / sd) @ reg.coef_ + reg.intercept_, 0.0, 1.0))

    loo_mae = float(np.mean(np.abs(y - loo_preds)))
    loo_rmse = float(np.sqrt(np.mean((y - loo_preds) ** 2)))
    loo_rho = float(spearmanr(y, loo_preds).statistic)

    mu_all = X.mean(axis=0)
    sd_all = np.maximum(X.std(axis=0), 1e-8)
    reg_all = Ridge(alpha=6.0)
    reg_all.fit((X - mu_all) / sd_all, y)

    cal = LLICalibrator(
        feature_names=fnames,
        mean=mu_all,
        std=sd_all,
        coef=reg_all.coef_,
        intercept=float(reg_all.intercept_),
        loo_mae=loo_mae,
        loo_rmse=loo_rmse,
        loo_spearman=loo_rho,
        n_scored=n,
    )
    report = {
        "n_organizer_scored_rasters": n,
        "loo_mae": round(loo_mae, 5),
        "loo_rmse": round(loo_rmse, 5),
        "loo_spearman_rho": round(loo_rho, 5),
        "standardized_weights": {k: round(float(w), 5) for k, w in zip(fnames, reg_all.coef_)},
        "intercept": round(float(reg_all.intercept_), 5),
    }
    return cal, report
