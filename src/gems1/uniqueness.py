"""Lane uniqueness vs a raster registry.

A candidate has drifted into another lane if:
  - Spearman rank-correlation of the (pre-placement) surface with any registry
    raster exceeds 0.90, OR
  - more than 70% of its final dots fall within 3 px of one registry raster's dots.

Space-filling rasters (>= 70% of footprint positive) are reported but excluded
from the 70% gate (they overlap every map). The literal overlap is still logged.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr


def read_dots(path: Path, footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    if a.shape != footprint.shape:
        raise ValueError(f"{path} shape {a.shape} != {footprint.shape}")
    return np.isfinite(a) & (a > 0) & footprint


def spearman_surface(a: np.ndarray, b: np.ndarray, footprint: np.ndarray, max_n: int = 250_000) -> float:
    aa = np.asarray(a, dtype=np.float64)[footprint]
    bb = np.asarray(b, dtype=np.float64)[footprint]
    n = aa.size
    if n == 0:
        return 0.0
    if n > max_n:
        rng = np.random.default_rng(32)
        idx = rng.choice(n, size=max_n, replace=False)
        aa, bb = aa[idx], bb[idx]
    if np.std(aa) < 1e-12 or np.std(bb) < 1e-12:
        return 0.0
    rho, _ = spearmanr(aa, bb)
    if not np.isfinite(rho):
        return 0.0
    return float(rho)


def overlap_within(pred_dots: np.ndarray, other_dots: np.ndarray, radius_px: float = 3.0) -> dict:
    n = int(pred_dots.sum())
    n_other = int(other_dots.sum())
    if n == 0:
        return dict(n=0, n_other=n_other, frac=0.0, space_filling=False)
    space_filling = n_other >= 0.70 * other_dots.size  # vs full raster; refined by caller
    d = distance_transform_edt(~other_dots)
    frac = float((d[pred_dots] <= radius_px).mean())
    return dict(n=n, n_other=n_other, frac=frac, space_filling=space_filling)


def audit(
    pred_dots: np.ndarray,
    surface: np.ndarray,
    footprint: np.ndarray,
    registry_paths: list[Path],
    rho_max: float = 0.90,
    overlap_max: float = 0.70,
    radius_px: float = 3.0,
) -> dict:
    foot_n = int(footprint.sum())
    rows = []
    max_rho = 0.0
    max_ov = 0.0
    max_ov_literal = 0.0
    drifted = False
    drifted_reason = None
    for p in registry_paths:
        p = Path(p)
        try:
            other = read_dots(p, footprint)
        except Exception as e:
            rows.append({"path": str(p), "error": str(e)})
            continue
        rho = abs(spearman_surface(surface, other.astype(np.float32), footprint))
        ov = overlap_within(pred_dots, other, radius_px=radius_px)
        other_frac_fp = ov["n_other"] / max(foot_n, 1)
        space = other_frac_fp >= 0.70
        ov["space_filling"] = space
        max_rho = max(max_rho, abs(rho))
        max_ov_literal = max(max_ov_literal, ov["frac"])
        if not space:
            max_ov = max(max_ov, ov["frac"])
        row = {
            "name": p.name,
            "rho": rho,
            "overlap_frac": ov["frac"],
            "n_other": ov["n_other"],
            "space_filling": space,
        }
        rows.append(row)
        if abs(rho) > rho_max:
            drifted = True
            drifted_reason = f"spearman {rho:.4f} > {rho_max} vs {p.name}"
        if (not space) and ov["frac"] > overlap_max:
            drifted = True
            drifted_reason = drifted_reason or f"overlap {ov['frac']:.4f} > {overlap_max} vs {p.name}"
    rows_sorted = sorted(
        [r for r in rows if "error" not in r],
        key=lambda r: -max(abs(r["rho"]), r["overlap_frac"]),
    )
    return {
        "n_registry": len(registry_paths),
        "max_abs_spearman": max_rho,
        "max_overlap_non_spacefill": max_ov,
        "max_overlap_literal": max_ov_literal,
        "rho_threshold": rho_max,
        "overlap_threshold": overlap_max,
        "drifted": drifted,
        "drifted_reason": drifted_reason,
        "unique": (not drifted) and max_rho <= rho_max and max_ov <= overlap_max,
        "top": rows_sorted[:12],
    }
