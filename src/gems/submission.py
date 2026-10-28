"""Build, verify and label DrivenData GEMS submission GeoTIFFs."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .validator import sha256_file

EXPECTED = {
    "crs": "EPSG:32611",
    "shape": (3730, 3292),
    "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
    "dtype": "float32",
    "bounds": (243350.0, 4135550.0, 572550.0, 4508550.0),
    "footprint_pixels": 5167373,
    "outside_pixels": 7111787,
}


def sanitize(pred: np.ndarray) -> np.ndarray:
    """NaN/Inf-safe float32 in [0, 1]. NaN -> 0 (no evidence), +Inf -> 1, -Inf -> 0, then clip."""
    a = np.nan_to_num(np.asarray(pred, dtype=np.float64), nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def raster_mask_report(dataset: Any, footprint: np.ndarray) -> dict[str, Any]:
    """Inspect GDAL's effective band mask and external sidecars without modifying data.

    Range-checking ``read(1)`` alone misses finite pixels marked nodata by metadata
    or a GDAL mask. A single-file submission must not depend on an adjacent .msk,
    .aux.xml, or other sidecar. The footprint comes from a separately checked grid.
    """
    fp = np.asarray(footprint, dtype=bool)
    if fp.shape != dataset.shape or not fp.any():
        raise ValueError("a nonempty, grid-aligned footprint is required for mask validation")
    mask = dataset.read_masks(1)
    masked_inside = int(np.count_nonzero(fp & (mask == 0)))
    primary = Path(dataset.name).resolve()
    extra_files = sorted(Path(name).name for name in dataset.files
                         if Path(name).resolve() != primary)
    return {
        "masked_inside_footprint": masked_inside,
        "inside_all_valid": masked_inside == 0,
        "self_contained": not extra_files,
        "external_dependency_names": extra_files,
    }


def matches_frozen_validation(current: dict[str, Any], frozen: dict[str, Any]) -> bool:
    """Compare a historical receipt without weakening the newer mask guards.

    The frozen TIP1 card predates these two mandatory checks. Require both
    current checks to pass, then compare every previously recorded field exactly.
    The historical card itself remains unchanged.
    """
    names = ("footprint_gdal_mask_valid", "single_file_self_contained")
    checks = current.get("checks", {})
    if not current.get("format_valid") or any(checks.get(name, {}).get("pass") is not True for name in names):
        return False
    comparable = {**current, "checks": {key: value for key, value in checks.items() if key not in names}}
    return comparable == frozen


def write_submission(
    pred_2d: np.ndarray,
    template_path: Path | str,
    out_path: Path | str,
    *,
    outside: str = "zero",
) -> Path:
    """Write ``pred_2d`` using the template profile and a local finite policy.

    The default is an all-finite ``0.0`` exterior for strict local range checks.
    Official instructions instead describe null/NaN outside the footprint; the
    cause of the reported portal error and actual portal acceptance are unknown.
    The NaN compatibility twin fails this project's strict all-finite policy.
    Neither option authorizes a competition submission.
    """
    if outside not in ("nan", "zero"):
        raise ValueError("outside must be 'nan' or 'zero'")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_path) as t:
        profile = t.profile.copy()
        footprint = np.isfinite(t.read(1))
    if not footprint.any():
        raise ValueError("template contains no finite prediction footprint")
    if np.shape(pred_2d) != footprint.shape:
        raise ValueError(f"prediction shape {np.shape(pred_2d)} != template {footprint.shape}")
    if np.ma.isMaskedArray(pred_2d) and np.ma.getmaskarray(pred_2d)[footprint].any():
        raise ValueError("Prediction has masked pixels inside the footprint; no silent mask removal")
    pred_2d = np.asarray(pred_2d)
    values = pred_2d[footprint]
    if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError(
            "Predictions inside the footprint must be finite and in [0,1]; sanitize explicitly if intended"
        )
    arr = pred_2d.astype(np.float32, copy=True)
    arr = np.where(
        footprint, arr, np.float32(np.nan) if outside == "nan" else np.float32(0.0)
    ).astype(np.float32)
    profile.update(
        driver="GTiff", dtype="float32", count=1, nodata=(np.nan if outside == "nan" else None)
    )
    # A stale sidecar from an earlier file could otherwise override the new TIFF's
    # nodata/mask metadata, even though only the TIFF is ultimately uploaded.
    if any(Path(str(out_path) + suffix).exists() for suffix in (".msk", ".aux.xml")):
        raise ValueError("Output path has existing raster sidecars; refusing an ambiguous overwrite")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(AREA_OR_POINT="Area")
    with rasterio.open(out_path) as written:
        mask_report = raster_mask_report(written, footprint)
    if not mask_report["inside_all_valid"] or not mask_report["self_contained"]:
        raise ValueError("Written raster is masked inside the footprint or depends on sidecar files")
    return out_path


def zip_single(tif_path: Path | str, zip_path: Path | str | None = None) -> Path:
    tif_path = Path(tif_path)
    zip_path = Path(zip_path) if zip_path else tif_path.with_suffix(".zip")
    if tif_path.suffix.lower() != ".tif" or not tif_path.is_file():
        raise ValueError("ZIP input must be an existing .tif")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    info = zipfile.ZipInfo(tif_path.name, date_time=(2026, 10, 2, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(info, tif_path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if (
            names != [tif_path.name]
            or hashlib.sha256(z.read(tif_path.name)).digest()
            != hashlib.sha256(tif_path.read_bytes()).digest()
        ):
            raise ValueError("ZIP contents do not exactly match the single GeoTIFF")
    return zip_path


def check_variants(path: Path | str, template_path: Path | str) -> dict[str, Any]:
    path = Path(path)
    with rasterio.open(template_path) as t:
        t_arr = t.read(1)
        t_prof = t.profile
        footprint = np.isfinite(t_arr)
        t_crs, t_tr, t_shape = t.crs, t.transform, t.shape
    with rasterio.open(path) as s:
        arr = s.read(1)
        masked = s.read(1, masked=True)
        prof = s.profile
        crs, tr, shape, count, dtypes, nodata = (
            s.crs,
            s.transform,
            s.shape,
            s.count,
            s.dtypes,
            s.nodata,
        )
        mask_report = raster_mask_report(s, footprint) if s.shape == footprint.shape and footprint.any() else None
    shape_ok = arr.shape == footprint.shape
    if shape_ok:
        inside, outside = arr[footprint], arr[~footprint]
    else:
        inside = outside = np.array([], dtype=np.float32)
    fin_in = np.isfinite(inside)

    def rng_ok(v: np.ndarray) -> bool:
        return bool(
            v.size
            and np.isfinite(v).any()
            and not np.isinf(v).any()
            and np.nanmin(v) >= 0.0
            and np.nanmax(v) <= 1.0
        )

    checks: dict[str, dict[str, Any]] = {}

    def add(name: str, ok: bool, detail: str, *, hard: bool = True) -> None:
        checks[name] = {"pass": bool(ok), "detail": detail, "hard_requirement": hard}

    expected_template = (
        t_crs is not None
        and t_crs.to_epsg() == 32611
        and t_shape == EXPECTED["shape"]
        and tuple(t_tr)[:6] == EXPECTED["transform"]
        and int(footprint.sum()) == EXPECTED["footprint_pixels"]
    )
    add(
        "official_template_grid_and_footprint",
        expected_template,
        "Template must be the pinned organizer grid, not just a self-consistent arbitrary raster",
    )
    add("single_band", count == 1, f"count={count}")
    add("footprint_gdal_mask_valid", bool(mask_report and mask_report["inside_all_valid"]),
        f"GDAL validity mask within footprint: {mask_report}")
    add("single_file_self_contained", bool(mask_report and mask_report["self_contained"]),
        f"External raster dependencies: {mask_report}")
    add("dtype_float32", dtypes == ("float32",), f"dtypes={dtypes}")
    add("crs_epsg_32611", crs is not None and crs.to_epsg() == 32611 and crs == t_crs, f"{crs}")
    add("shape_matches_template", shape == t_shape, f"{shape} vs {t_shape}")
    add("geotransform_matches_template", tr == t_tr, f"{tuple(tr)[:6]}")
    if shape_ok:
        add(
            "footprint_all_finite",
            bool(fin_in.all()),
            f"{int((~fin_in).sum())} NaN/Inf inside the {int(footprint.sum()):,}-pixel footprint",
        )
        add(
            "footprint_range_0_1",
            rng_ok(inside),
            f"finite={int(fin_in.sum())}/{inside.size}; range={float(inside[fin_in].min()) if fin_in.any() else None} to {float(inside[fin_in].max()) if fin_in.any() else None}",
        )
        add(
            "outside_is_nan_official_text",
            bool(np.isnan(outside).all()),
            f"{int(np.isnan(outside).sum()):,} of {outside.size:,} outside pixels are NaN",
            hard=False,
        )
    else:
        for name in ("footprint_all_finite", "footprint_range_0_1"):
            add(name, False, "not evaluated: the raster does not have the template's shape")
        add(
            "outside_is_nan_official_text",
            False,
            "not evaluated: the raster does not have the template's shape",
            hard=False,
        )
    add(
        "nodata_tag_is_nan", nodata is not None and np.isnan(nodata), f"nodata={nodata}", hard=False
    )
    add("variant_nan_aware_whole_array", rng_ok(arr), "np.nanmin/np.nanmax over the whole array")
    add(
        "variant_masked_read",
        rng_ok(masked.compressed()),
        "rasterio read(masked=True).compressed()",
    )
    add(
        "variant_strict_whole_array_no_nan_allowed",
        bool(((arr >= 0) & (arr <= 1)).all()),
        "((a>=0)&(a<=1)).all() over the whole array - fails for ANY NaN, including the official sample's NaN outside",
        hard=False,
    )

    def _same(a, b) -> bool:
        if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
            return True
        return a == b

    same_profile = all(
        _same(prof.get(k), t_prof.get(k))
        for k in ("driver", "dtype", "nodata", "width", "height", "crs", "transform")
    )
    add(
        "profile_matches_official_sample",
        bool(same_profile),
        f"driver/dtype/nodata/size/crs/transform equal to template; compress={prof.get('compress')} (template {t_prof.get('compress')})",
        hard=False,
    )
    hard_fail = [k for k, v in checks.items() if v["hard_requirement"] and not v["pass"]]
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "format_valid": not hard_fail,
        # Deprecated legacy alias: a format-only check cannot authorize a slot.
        "ok_to_upload": False,
        "upload_authorization": "not evaluated by a format validator; separate scientific selector required",
        "format_acceptable": not hard_fail,
        "submission_authorized": False,
        "scope": "Format only; this does not certify bias audit, holdout promotion or weekly-slot eligibility",
        "hard_failures": hard_fail,
        "official_format_compliant": checks["outside_is_nan_official_text"]["pass"]
        and not hard_fail,
        "in_footprint_positive_pixels": int((inside > 0).sum()),
        "in_footprint_mass": round(float(np.nansum(inside, dtype=np.float64)), 2)
        if inside.size
        else 0.0,
        "checks": checks,
    }


def scored_content_id(pred_2d: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray) -> str:
    pred_2d, footprint, catalogue = (
        np.asarray(pred_2d),
        np.asarray(footprint, bool),
        np.asarray(catalogue, bool),
    )
    if pred_2d.shape != footprint.shape or catalogue.shape != footprint.shape:
        raise ValueError("Content-ID grids must match")
    v = np.asarray(pred_2d[footprint & ~catalogue], dtype="<f4").copy()
    if not np.isfinite(v).all() or np.any((v < 0) | (v > 1)):
        raise ValueError("Content ID requires valid scored probabilities")
    v[v == 0] = 0  # Canonicalize negative zero, but preserve all soft-score values.
    return hashlib.sha256(v.tobytes()).hexdigest()[:12]


def make_filename(
    family: str, hypothesis: str, date: str, content_id: str, outside: str = "nan"
) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in hypothesis.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return f"{family}-{slug}-{date}-{content_id}-{outside}.tif"


def make_note(
    hypothesis_id: str,
    summary: str,
    content_id: str,
    family: str = "24GEMSDOE",
    *,
    reference: bool = False,
) -> str:
    prefix = f"{family} {hypothesis_id} | "
    suffix = f" | id {content_id} | " + (
        "reference, no new score" if reference else "not yet live-scored"
    )
    max_sum = 140 - len(prefix) - len(suffix)
    if max_sum < 1:
        raise ValueError("Hypothesis/content identifiers are too long for the 140-character note")
    return f"{prefix}{summary[:max_sum]}{suffix}"


def dump_json(obj: Any, path: Path | str) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, default=float) + "\n")
