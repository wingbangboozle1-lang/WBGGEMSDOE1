"""Submission-format validator for the DOE GEMS Prize.

Checks the contract stated by the organizers on
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/

    * EPSG:32611 (UTM 11N)
    * 100 m posting
    * the same bounds as the training data
    * a single float32 band with values in [0, 1]
    * cells outside the study footprint null or nan

and the two additional constraints this project imposes after the portal
rejected a NaN file with "Predicted values must be in range [0, 1]":

    * "zeros" mode: no NaN anywhere in the file, 0.0 outside the footprint
    * an optional ZIP must contain exactly one TIFF, byte-identical to the input
"""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import asdict, dataclass, field

import numpy as np
import rasterio

EXPECTED_CRS_EPSG = 32611
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_PIXEL = (100.0, 100.0)


@dataclass
class Report:
    path: str = ""
    sha256: str = ""
    shape: list = field(default_factory=list)
    dtype: str = ""
    band_count: int = 0
    crs: str = ""
    pixel_size: list = field(default_factory=list)
    origin: list = field(default_factory=list)
    nodata: object = None
    mode: str = "unknown"
    in_footprint_pixels: int = 0
    positive_pixels: int = 0
    value_min: float = 0.0
    value_max: float = 0.0
    checks: dict = field(default_factory=dict)
    all_checks_passed: bool = False
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_tif(path: str, footprint: np.ndarray | None = None) -> Report:
    rep = Report(path=path, sha256=_sha256(path))
    with rasterio.open(path) as src:
        rep.shape = [int(src.height), int(src.width)]
        rep.dtype = src.dtypes[0]
        rep.band_count = int(src.count)
        rep.crs = str(src.crs)
        tr = src.transform
        rep.pixel_size = [float(tr.a), float(abs(tr.e))]
        rep.origin = [float(tr.c), float(tr.f)]
        rep.nodata = None if src.nodata is None else float(src.nodata)
        arr = src.read(1)

    nan_anywhere = bool(np.isnan(arr).any()) if arr.dtype.kind == "f" else False
    rep.mode = "nan" if nan_anywhere else "zeros"

    if footprint is None:
        finite = np.isfinite(arr)
        footprint = finite
    footprint = np.asarray(footprint, dtype=bool)

    inside = arr[footprint]
    inside_finite = np.isfinite(inside)
    rep.in_footprint_pixels = int(footprint.sum())
    rep.positive_pixels = int(np.count_nonzero(np.nan_to_num(inside) > 0))

    finite_inside = inside[inside_finite]
    if finite_inside.size:
        rep.value_min = float(finite_inside.min())
        rep.value_max = float(finite_inside.max())

    outside = arr[~footprint]
    outside_ok = bool(np.all(np.nan_to_num(outside, nan=0.0) == 0.0))

    checks = {
        "single_band": rep.band_count == 1,
        "dtype_float32": rep.dtype == "float32",
        "shape_matches": tuple(rep.shape) == EXPECTED_SHAPE,
        "crs_epsg_32611": rep.crs.upper().endswith("32611"),
        "pixel_size_100m": all(abs(p - 100.0) < 1e-6 for p in rep.pixel_size),
        "in_footprint_all_finite": bool(inside_finite.all()),
        "values_in_0_1": bool(
            rep.value_min >= 0.0 and rep.value_max <= 1.0 and finite_inside.size > 0
        ),
        "outside_footprint_zero": outside_ok,
        "has_predictions": rep.positive_pixels > 0,
    }
    if rep.mode == "zeros":
        checks["no_nan_anywhere"] = True
    rep.checks = checks
    rep.all_checks_passed = all(checks.values())
    rep.errors = [k for k, v in checks.items() if not v]
    return rep


def validate_zip(zip_path: str, tif_path: str) -> dict:
    """A submission ZIP must hold exactly one TIFF, identical to `tif_path`."""
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        tifs = [n for n in names if n.lower().endswith((".tif", ".tiff"))]
        out = {
            "zip": zip_path,
            "members": names,
            "tif_members": tifs,
            "exactly_one_tif": len(tifs) == 1 and len(names) == 1,
        }
        if len(tifs) == 1:
            inner = z.read(tifs[0])
            outer = open(tif_path, "rb").read()
            out["byte_identical"] = hashlib.sha256(inner).hexdigest() == hashlib.sha256(outer).hexdigest()
        else:
            out["byte_identical"] = False
    out["all_checks_passed"] = bool(out["exactly_one_tif"] and out["byte_identical"])
    return out
