"""Feature block algebra over the official 19-band competition stack.

The stack is the organiser product ``training_features.tif`` (sha256
``4371c82e…23bc5``, EPSG:32611, 3 730 x 3 292, 100 m, nodata -3.4e38).  It is
mirrored in this repository's bridge directory; :func:`stack_path` refuses to run
unless the grid matches :mod:`wbg5.grid`, so a silently mis-registered mirror
cannot enter a model.

Everything here is *band-local and block-local*: no function reads a label.  The
only label consumer in the lane is :mod:`wbg5.detect`, which takes an explicit
boolean mask.  All work is windowed, so peak memory is one 128-row block
(``75 x 128 x 3292 x 4 B`` = 126 MB) rather than the whole 3.7 GB cube.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, sobel

from . import grid

BANDS = (
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
    "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15",
    "cond_surf", "iso_grav_anom_hg", "det_elev_slope",
)
TEXTURE_BANDS = ("rtp", "tmi", "tmi_hg", "tmi_vg", "tc", "mag_anom", "iso_grav_anom",
                 "iso_grav_anom_hg", "iso_grav_anom_vg", "iso_grav_anom_slope",
                 "det_elev", "det_elev_slope", "cond_surf", "depth_to_base_surf")
SCALES = (2.0, 6.0)
PAD = 12
BLOCK = 128
STACK_SHA256 = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"


def stack_path(root: Path) -> Path:
    import os
    env = os.environ.get("WBG5_FEATURES")
    cands = [Path(env)] if env else []
    cands += [root / "data" / "bridge" / "training_features.tif",
              root / "data" / "bridge" / "gems-geodawn-numerical-features.tif",
              Path("/tmp/lab/training_features.tif")]
    for cand in cands:
        if cand.exists():
            return cand
    raise FileNotFoundError(
        "official feature stack missing: expected data/bridge/training_features.tif "
        f"(sha256 {STACK_SHA256}). See data/bridge/README.md for the reassembly recipe.")


@lru_cache(maxsize=1)
def _open(path: str):
    ds = rasterio.open(path)
    if (ds.height, ds.width, ds.count) != (grid.HEIGHT, grid.WIDTH, 19):
        raise ValueError(f"feature stack grid {(ds.height, ds.width, ds.count)} "
                         f"!= {(grid.HEIGHT, grid.WIDTH, 19)}")
    if tuple(ds.transform)[:6] != tuple(grid.TRANSFORM)[:6] or ds.crs != grid.CRS:
        raise ValueError("feature stack georeference does not match wbg5.grid")
    return ds


def names() -> list[str]:
    out = list(BANDS)
    for b in TEXTURE_BANDS:
        out += [f"{b}__std{SCALES[0]:.0f}", f"{b}__grad{SCALES[0]:.0f}",
                f"{b}__std{SCALES[1]:.0f}", f"{b}__grad{SCALES[1]:.0f}"]
    return out


def _read(rows: slice) -> tuple[np.ndarray, np.ndarray]:
    ds = _open(str(stack_path(_ROOT[0])))
    a = ds.read(window=rasterio.windows.Window(0, rows.start, grid.WIDTH,
                                               rows.stop - rows.start)).astype(np.float32)
    bad = ~np.isfinite(a) | (a < -1e30)
    valid = ~bad.any(0)
    a[bad] = np.nan
    return a, valid


_ROOT: list[Path] = [Path(".")]


def set_root(root: Path) -> None:
    _ROOT[0] = Path(root)


def _texture(a: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    med = np.nanmedian(a)
    filled = np.where(np.isfinite(a), a, med)
    mu = gaussian_filter(filled, sigma, mode="nearest")
    sd = np.sqrt(np.maximum(gaussian_filter((filled - mu) ** 2, sigma, mode="nearest"), 0))
    grad = np.hypot(sobel(filled, 0), sobel(filled, 1)) / 8.0
    return sd, grad


def block(r0: int, r1: int, robust: bool = True) -> tuple[np.ndarray, np.ndarray, int]:
    """Features for rows ``[r0, r1)``; returns ``(X[F, n, W], valid[n, W], r0)``."""
    p0, p1 = max(0, r0 - PAD), min(grid.HEIGHT, r1 + PAD)
    a, valid = _read(slice(p0, p1))
    valid = valid.astype(np.float32)
    feats = []
    for i in range(19):
        b = a[i]
        if robust:
            v = b[valid > 0]
            lo, hi = (np.percentile(v, [1, 99]) if v.size else (0.0, 1.0))
            b = np.clip((b - lo) / (hi - lo if hi > lo else 1.0), 0, 1)
        feats.append(np.nan_to_num(b, nan=0.0).astype(np.float32))
    for nm in TEXTURE_BANDS:
        base = a[BANDS.index(nm)]
        for s in SCALES:
            sd, gd = _texture(base, s)
            for ch in (sd, gd):
                v = ch[valid > 0]
                lo, hi = (np.percentile(v, [1, 99]) if v.size else (0.0, 1.0))
                feats.append(np.nan_to_num(np.clip((ch - lo) / (hi - lo if hi > lo else 1.0), 0, 1),
                                           nan=0.0).astype(np.float32))
    X = np.stack(feats)[:, r0 - p0:r1 - p0, :]
    return X, valid[r0 - p0:r1 - p0], r0


def iter_blocks(r0: int = 0, r1: int | None = None, size: int = BLOCK):
    r1 = grid.HEIGHT if r1 is None else r1
    for s in range(r0, r1, size):
        yield block(s, min(s + size, r1))


def sample(X_by_col, valid, labels, n_max: int, rng):
    """Sub-sample valid pixels of a block stack into a flat training matrix."""
    idx = np.flatnonzero(valid.ravel())
    if idx.size > n_max:
        idx = rng.choice(idx, n_max, replace=False)
    return X_by_col[:, idx].T, labels[idx]
