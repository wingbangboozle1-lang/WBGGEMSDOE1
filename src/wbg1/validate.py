"""Format validator + uniqueness-vs-registry audit (no human in the loop).

Format gates (portal-blocking):
  F1 single-band GeoTIFF, float32-able
  F2 CRS == EPSG:32611
  F3 shape == (3730, 3292)
  F4 transform matches template exactly
  F5 every value inside footprint is finite and in [0,1]
     (this is the "Predicted values must be in range [0, 1]" gate)
  F6 zeros-variant: whole array finite (NaN-outside files fail strict mode)

Uniqueness gates (protocol-blocking):
  U1 rank-correlation of the binary field vs every registry raster < 0.90
  U2 directed 3-px dot overlap vs every registry raster < 70%
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

from .metric import GRID_CRS, GRID_SHAPE, GRID_TRANSFORM

CORR_LIMIT = 0.90
OVERLAP_LIMIT = 0.70


def validate_format(path: Path, template_path: Path, strict_finite: bool = True) -> dict:
    path, template_path = Path(path), Path(template_path)
    checks: dict[str, dict] = {}

    def put(k, ok, detail=""):
        checks[k] = {"ok": bool(ok), "detail": str(detail)}

    try:
        with rasterio.open(template_path) as t:
            t_shape = tuple(t.shape)
            t_crs, t_tr = t.crs, tuple(t.transform)
            t_inside = np.isfinite(t.read(1))
        with rasterio.open(path) as s:
            shape = tuple(s.shape)
            put("F1_single_band", s.count == 1, f"count={s.count} dtype={s.dtypes[0]}")
            put("F2_crs", str(s.crs) == GRID_CRS and s.crs == t_crs,
                f"crs={s.crs}")
            put("F3_shape", shape == GRID_SHAPE == t_shape, f"shape={shape}")
            put("F4_transform", tuple(s.transform)[:6] == GRID_TRANSFORM == t_tr[:6],
                f"transform={tuple(s.transform)[:6]}")
            a = s.read(1).astype(np.float64)
    except Exception as e:  # fail closed
        put("read", False, repr(e))
        return {"path": str(path), "pass": False, "checks": checks}

    inside = a[t_inside]
    finite_in = np.isfinite(inside)
    put("F5_finite_inside", bool(finite_in.all()),
        f"nan_inside={int((~finite_in).sum())}")
    in_range = bool(np.all((inside[finite_in] >= 0.0) & (inside[finite_in] <= 1.0))) \
        if finite_in.any() else False
    put("F5_range_01", in_range,
        f"min={float(np.nanmin(inside)):.6f} max={float(np.nanmax(inside)):.6f}")
    if strict_finite:
        put("F6_all_finite", bool(np.isfinite(a).all()),
            f"nan_total={int(np.isnan(a).sum())}")
    dots = int((np.nan_to_num(a, nan=0.0) > 0.5).sum())
    binary = bool(np.all(np.isin(np.nan_to_num(inside, nan=0.0),
                                 [0.0, 1.0])))
    checks["info"] = {"dots": dots, "binary01": binary,
                      "positive_inside": int((inside[finite_in] > 0.5).sum())}
    ok = all(v["ok"] for k, v in checks.items() if k.startswith("F") or k == "read")
    return {"path": str(path), "pass": bool(ok), "checks": checks}


def _binary(path: Path) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float64)
    return np.nan_to_num(a, nan=0.0) > 0.5


def uniqueness_vs_registry(mask: np.ndarray, foot: np.ndarray,
                           registry: list[dict]) -> dict:
    """mask: our boolean dots. registry: [{id, path}]. Returns worst-case stats."""
    mask = np.asarray(mask, dtype=bool) & np.asarray(foot, dtype=bool)
    x = mask[foot].astype(np.float64)
    rows = []
    for reg in registry:
        rp = Path(reg["path"])
        if not rp.exists():
            rows.append({"id": reg["id"], "error": "missing file"})
            continue
        rm = _binary(rp) & foot
        y = rm[foot].astype(np.float64)
        if x.std() == 0 or y.std() == 0:
            corr = 0.0
        else:
            corr = float(np.corrcoef(x, y)[0, 1])
        dil = binary_dilation(rm, iterations=3)
        ov = float((mask & dil).sum() / max(1, int(mask.sum())))
        dil2 = binary_dilation(mask, iterations=3)
        ov_rev = float((rm & dil2).sum() / max(1, int(rm.sum())))
        inter = int((mask & rm).sum())
        rows.append({
            "id": reg["id"], "corr": corr, "overlap_3px": ov,
            "overlap_3px_reverse": ov_rev, "exact_inter": inter,
            "reg_dots": int(rm.sum()),
            "corr_ok": bool(abs(corr) < CORR_LIMIT),
            "overlap_ok": bool(ov < OVERLAP_LIMIT),
        })
    worst_corr = max(rows, key=lambda r: abs(r.get("corr", 0))) if rows else None
    worst_ov = max(rows, key=lambda r: r.get("overlap_3px", 0)) if rows else None
    verdict = all(r.get("corr_ok", False) and r.get("overlap_ok", False) for r in rows)
    return {
        "unique": bool(verdict),
        "n_registry": len(rows),
        "our_dots": int(mask.sum()),
        "worst_corr": worst_corr,
        "worst_overlap": worst_ov,
        "rows": rows,
    }


def load_registry_list(registry_json: Path, raster_dir: Path) -> list[dict]:
    reg = json.loads(Path(registry_json).read_text())
    out = []
    for r in reg.get("rasters", []):
        out.append({"id": r["id"], "path": str(Path(raster_dir) / r["file"])})
    return out
