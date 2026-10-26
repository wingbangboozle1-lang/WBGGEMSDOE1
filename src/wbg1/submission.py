"""Submission writer: zeros/nan GeoTIFF pair + audit JSON + zip.

Grid is copied EXACTLY from the template (sample_submission.tif):
same CRS, shape, transform, single-band float32. Inside footprint values are
{0,1}; zeros-variant writes 0.0 outside, nan-variant writes NaN outside.
"""
from __future__ import annotations

import hashlib
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def utc_tag() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def write_submission_pair(
    mask: np.ndarray,
    foot: np.ndarray,
    template_tif: Path,
    out_dir: Path,
    slug: str,
    timestamp_tag: str,
    candidate_meta: dict,
) -> dict:
    mask = np.asarray(mask, dtype=bool) & np.asarray(foot, dtype=bool)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_tif) as tpl:
        shape, crs, transform = tuple(tpl.shape), tpl.crs, tpl.transform
    assert mask.shape == shape, (mask.shape, shape)

    zeros = np.zeros(shape, dtype=np.float32)
    zeros[mask] = 1.0
    nan = np.full(shape, np.nan, dtype=np.float32)
    nan[foot] = 0.0
    nan[mask] = 1.0

    digest_src = mask.tobytes()
    content8 = hashlib.sha256(digest_src).hexdigest()[:8]
    base = f"wbg1-{slug}-{timestamp_tag}-{content8}"
    zeros_name, nan_name = f"{base}-zeros.tif", f"{base}-nan.tif"
    audit_name = f"{base}-audit.json"

    def _write(path: Path, arr: np.ndarray, nodata):
        with rasterio.open(
            path, "w", driver="GTiff", height=shape[0], width=shape[1],
            count=1, dtype="float32", crs=crs, transform=transform,
            nodata=nodata, compress="deflate",
        ) as ds:
            ds.write(arr, 1)

    zp, np_ = out_dir / zeros_name, out_dir / nan_name
    _write(zp, zeros, nodata=None)
    _write(np_, nan, nodata=float("nan"))
    zip_name = base + "-zeros.zip"
    with zipfile.ZipFile(out_dir / zip_name, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(zp, arcname=zeros_name)

    audit = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "slug": slug,
        "timestamp_tag": timestamp_tag,
        "content_digest8": content8,
        "grid": {"shape": list(shape), "crs": str(crs), "transform": list(transform)},
        "positive_px": int(mask.sum()),
        "zeros_tif": {"filename": zeros_name, "sha256": sha256_file(zp),
                      "bytes": zp.stat().st_size},
        "nan_tif": {"filename": nan_name, "sha256": sha256_file(np_),
                    "bytes": np_.stat().st_size},
        "zip": {"filename": zip_name, "sha256": sha256_file(out_dir / zip_name),
                "bytes": (out_dir / zip_name).stat().st_size},
        "candidate": candidate_meta,
    }
    (out_dir / audit_name).write_text(json.dumps(audit, indent=2))
    audit["audit_json"] = audit_name
    return audit
