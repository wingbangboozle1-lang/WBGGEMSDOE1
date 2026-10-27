"""Strict GeoTIFF submission validator. No human inspection.

Fixes the DrivenData portal error "Predicted values must be in range [0, 1]"
by requiring every cell of the zeros-mode raster to be finite and in [0, 1].
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from . import grid


def validate_submission(
    path: Path,
    template_path: Path | None = None,
    footprint: np.ndarray | None = None,
    labels: np.ndarray | None = None,
    require_all_finite: bool = True,
) -> dict:
    path = Path(path)
    _, foot, meta = grid.read_template(template_path)
    if footprint is not None:
        foot = np.asarray(footprint, bool)
    with rasterio.open(path) as src:
        arr = src.read(1)
        crs_ok = str(src.crs) in ("EPSG:32611", "epsg:32611") or (
            src.crs is not None and src.crs.to_epsg() == 32611
        )
        shape_ok = src.shape == (meta["height"], meta["width"])
        tr = tuple(float(x) for x in src.transform)[:6]
        exp = tuple(float(x) for x in meta["transform"])[:6]
        transform_ok = all(abs(a - b) < 1e-6 for a, b in zip(tr, exp))
        dtype_ok = src.dtypes[0] == "float32"
        count_ok = src.count == 1

    checks = {
        "file_exists": path.is_file() and path.stat().st_size > 0,
        "crs_epsg_32611": bool(crs_ok),
        "shape_3730x3292": bool(shape_ok),
        "transform_match": bool(transform_ok),
        "dtype_float32": bool(dtype_ok),
        "single_band": bool(count_ok),
    }
    if arr.shape != foot.shape:
        checks["shape_matches_footprint"] = False
        return {"pass": False, "checks": checks, "error": "array/footprint shape mismatch"}

    finite_all = bool(np.isfinite(arr).all())
    in01_all = bool(np.isfinite(arr).all() and (arr >= 0).all() and (arr <= 1).all())
    finite_in = bool(np.isfinite(arr[foot]).all())
    in01_in = bool(finite_in and (arr[foot] >= 0).all() and (arr[foot] <= 1).all())
    nan_in = int(np.isnan(arr[foot]).sum())
    dots = int(((arr > 0) & foot).sum())
    on_cat = None
    if labels is not None:
        on_cat = int(((arr > 0) & labels & foot).sum())
        checks["zero_dots_on_catalogue"] = on_cat == 0

    checks["finite_inside_footprint"] = finite_in
    checks["values_in_0_1_inside_footprint"] = in01_in
    checks["no_nan_inside_footprint"] = nan_in == 0
    if require_all_finite:
        checks["all_cells_finite"] = finite_all
        checks["all_cells_in_0_1"] = in01_all

    ok = all(bool(v) for v in checks.values())
    return {
        "pass": ok,
        "checks": checks,
        "n_checks": len(checks),
        "n_pass": int(sum(bool(v) for v in checks.values())),
        "sha256": grid.sha256_file(path),
        "bytes": path.stat().st_size,
        "dots": dots,
        "on_catalogue": on_cat,
        "min": float(np.nanmin(arr)),
        "max": float(np.nanmax(arr)),
        "nan_inside": nan_in,
        "nan_anywhere": int(np.isnan(arr).sum()),
        "path": str(path),
    }
