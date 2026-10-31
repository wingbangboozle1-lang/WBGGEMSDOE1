"""WBG31-E1: multi-structural-index Euler solution density (catalogue-free).

Thompson (1982) and Reid et al. (1990) show that the Euler homogeneity equation,

    (x - x0) Tx + (y - y0) Ty + (z - z0) Tz = N (B - T),

can be solved in each moving window by linear least squares once N is fixed.
Here Tx and Ty come from Gaussian derivatives of the field, Tz is the supplied
vertical-derivative band, and the four unknowns are (x0, y0, z0, B). Solutions
are accepted only when they lie inside their own window and have a depth
between 50 m and 3000 m. Accepted solutions are binned to cells and summed
with a Gaussian of sigma 3 cells, which is then scaled so one isolated
solution peaks at 1.

Only the potential-field bands 9, 11, 13 and 14 are read, so the channels are
catalogue-free. The unit of the vertical-derivative bands is unverified, so the
depth scale is a stated limitation. Positions use metres (100 m cells). The
sign of Tz only flips the sign of z0, so the depth magnitude is used.

Local sums use uniform filters on row chunks with a halo, so memory stays
bounded on the 12.4 M-cell grid.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

CELL_M = 100.0
WINDOW = 7
SIGMA_CELLS = 3.0
DEPTH_MIN_M = 50.0
DEPTH_MAX_M = 3000.0
CHUNK_ROWS = 512
HALO = 12  # window half-width plus derivative margin, rows

CHANNELS = (
    "euler_mag_N0_density",
    "euler_mag_N1_density",
    "euler_grav_N0_density",
    "euler_grav_N1_density",
)
# (band number, vertical-derivative band number, structural indices, name prefix)
SOURCES = (
    (14, 9, (0, 1), "euler_mag"),       # total magnetic intensity; tmi_vg
    (13, 11, (0, 1), "euler_grav"),     # isostatic gravity anomaly; iso_grav_anom_vg
)


def _derivatives(field, valid):
    """Gaussian x and y derivatives in units per metre; zero outside valid."""
    f0 = np.where(valid, field, 0.0).astype(np.float64)
    d_col = ndi.gaussian_filter(f0, sigma=1.0, order=(0, 1), mode="constant") / CELL_M
    d_row = ndi.gaussian_filter(f0, sigma=1.0, order=(1, 0), mode="constant") / CELL_M
    return f0, d_col, -d_row  # x east (column), y north (negative row)


def euler_solution_density(field, vertical, footprint, structural_index, *, window=WINDOW,
                           sigma_cells=SIGMA_CELLS, return_receipt=False):
    """Return a float32 Euler solution-density grid for one field and one N.

    ``field`` and ``vertical`` are 2D arrays with NaN or non-finite values allowed
    outside valid data. ``vertical`` is the vertical derivative of ``field``.
    ``footprint`` is the boolean study area. The output is zero outside it.
    """
    field = np.asarray(field)
    vertical = np.asarray(vertical)
    footprint = np.asarray(footprint, bool)
    if field.shape != vertical.shape or field.shape != footprint.shape:
        raise ValueError("field, vertical and footprint must share one shape")
    if window % 2 == 0 or window < 3:
        raise ValueError("window must be an odd integer >= 3")
    N = float(structural_index)
    valid = footprint & np.isfinite(field) & np.isfinite(vertical)
    # Keep windows whose support is valid: window half-width 3 + derivative support 4 + 1.
    interior = ndi.binary_erosion(valid, iterations=window // 2 + 5, border_value=0)
    f0, tx, ty = _derivatives(field, valid)
    tz = np.where(valid, vertical, 0.0).astype(np.float64)
    height, width = f0.shape
    counts = np.zeros(height * width, np.float64)
    accepted = 0
    attempted = 0
    depths = []
    half_m = (window // 2) * CELL_M
    box = lambda a: ndi.uniform_filter(a, size=window, mode="constant", cval=0.0)  # noqa: E731
    for r0 in range(0, height, CHUNK_ROWS):
        r1 = min(height, r0 + CHUNK_ROWS)
        p0 = max(0, r0 - HALO)
        p1 = min(height, r1 + HALO)
        sl = slice(p0, p1)
        keep = slice(r0 - p0, r0 - p0 + (r1 - r0))
        rows = np.arange(p0, p1, dtype=np.float64)[:, None]
        cols = np.arange(width, dtype=np.float64)[None, :]
        x = np.broadcast_to(cols * CELL_M, f0[sl].shape)
        y = np.broadcast_to(-rows * CELL_M, f0[sl].shape)
        Tx, Ty, Tz, T = tx[sl], ty[sl], tz[sl], f0[sl]
        # Local coordinates: subtract the window centre, which is exact here
        # because box(x*f) - xc*box(f) = box((x-xc)*f).
        xc, yc = x, y
        bx = lambda f: box(x * f) - xc * box(f)  # noqa: E731
        by = lambda f: box(y * f) - yc * box(f)  # noqa: E731
        m11 = box(Tx * Tx)
        m12 = box(Tx * Ty)
        m13 = box(Tx * Tz)
        m22 = box(Ty * Ty)
        m23 = box(Ty * Tz)
        m33 = box(Tz * Tz)
        mx = box(Tx)
        my = box(Ty)
        mz = box(Tz)
        mt = box(T)
        v1 = bx(Tx * Tx) + by(Tx * Ty) + N * box(Tx * T)
        v2 = bx(Tx * Ty) + by(Ty * Ty) + N * box(Ty * T)
        v3 = bx(Tx * Tz) + by(Ty * Tz) + N * box(Tz * T)
        v4 = N * (bx(Tx) + by(Ty) + N * mt)
        M = np.empty(Tx.shape + (4, 4))
        M[..., 0, 0], M[..., 0, 1], M[..., 0, 2], M[..., 0, 3] = m11, m12, m13, N * mx
        M[..., 1, 0], M[..., 1, 1], M[..., 1, 2], M[..., 1, 3] = m12, m22, m23, N * my
        M[..., 2, 0], M[..., 2, 1], M[..., 2, 2], M[..., 2, 3] = m13, m23, m33, N * mz
        M[..., 3, 0], M[..., 3, 1], M[..., 3, 2], M[..., 3, 3] = N * mx, N * my, N * mz, N * N
        V = np.stack([v1, v2, v3, v4], axis=-1)
        # Keep only interior centres in the kept rows.
        centre_rows = np.arange(p0, p1)
        mask = (centre_rows >= r0) & (centre_rows < r1)
        mask_full = mask[:, None] & interior[sl]
        if not mask_full.any():
            continue
        Mm = M[mask_full]
        Vv = V[mask_full]
        if N == 0.0:
            # Contact (N=0): the base-level column and row vanish, so B is not
            # identifiable. Solve the 3x3 system for (x0, y0, z0) only.
            Mm = Mm[:, :3, :3]
            Vv = Vv[:, :3]
        det = np.linalg.det(Mm)
        good = np.abs(det) > 1e-300
        if not good.any():
            continue
        sol = np.linalg.solve(Mm[good], Vv[good][..., None])[..., 0]
        finite = np.isfinite(sol).all(axis=1)
        sol = sol[finite]
        if N == 0.0:
            sol = np.column_stack([sol, np.zeros(len(sol))])  # placeholder B, unused
        rr_idx, cc_idx = np.nonzero(mask_full)
        rr_idx = rr_idx[good][finite] + p0
        cc_idx = cc_idx[good][finite]
        attempted += len(sol)
        dx0 = sol[:, 0]
        dy0 = sol[:, 1]
        z0 = np.abs(sol[:, 2])
        inside = (np.abs(dx0) <= half_m) & (np.abs(dy0) <= half_m)
        depth_ok = (z0 >= DEPTH_MIN_M) & (z0 <= DEPTH_MAX_M)
        ok = inside & depth_ok
        accepted += int(ok.sum())
        depths.append(z0[ok])
        tcol = cc_idx[ok] + np.rint(dx0[ok] / CELL_M).astype(int)
        trow = rr_idx[ok] - np.rint(dy0[ok] / CELL_M).astype(int)
        inbounds = (tcol >= 0) & (tcol < width) & (trow >= 0) & (trow < height)
        tcol, trow = tcol[inbounds], trow[inbounds]
        in_fp = footprint[trow, tcol]
        flat = trow[in_fp] * width + tcol[in_fp]
        counts += np.bincount(flat, minlength=counts.size)
    density = ndi.gaussian_filter(counts.reshape(height, width), sigma_cells, mode="constant")
    density *= 2.0 * np.pi * sigma_cells * sigma_cells
    density = np.where(footprint, density, 0.0).astype(np.float32)
    if not return_receipt:
        return density
    all_depths = np.concatenate(depths) if depths else np.zeros(0)
    receipt = dict(structural_index=N, window_cells=window, attempted_solutions=int(attempted),
                   accepted_solutions=int(accepted),
                   acceptance_fraction=float(accepted / attempted) if attempted else 0.0,
                   depth_median_m=float(np.median(all_depths)) if all_depths.size else None,
                   depth_p10_m=float(np.percentile(all_depths, 10)) if all_depths.size else None,
                   depth_p90_m=float(np.percentile(all_depths, 90)) if all_depths.size else None,
                   finite_inside_footprint=bool(np.isfinite(density[footprint]).all()),
                   max_value=float(density.max()), depth_window_m=[DEPTH_MIN_M, DEPTH_MAX_M],
                   interior_fraction_of_footprint=float(interior.sum() / max(1, footprint.sum())))
    return density, receipt


def euler_channels(bands, footprint, *, return_receipt=True):
    """Compute the four catalogue-free channels in the order of ``CHANNELS``.

    ``bands`` maps a 1-based band number to a 2D array. It must contain bands
    9, 11, 13 and 14 from the shared 19-band stack.
    """
    out, receipts = {}, []
    for band, vband, indices, prefix in SOURCES:
        field = np.asarray(bands[band])
        vertical = np.asarray(bands[vband])
        valid_fp = footprint & np.isfinite(field) & np.isfinite(vertical)
        for n in indices:
            density, rec = euler_solution_density(field, vertical, footprint, n, return_receipt=True)
            name = f"{prefix}_N{n}_density"
            out[name] = density
            rec["channel"] = name
            rec["source_band"] = band
            rec["vertical_band"] = vband
            rec["valid_footprint_cells"] = int(valid_fp.sum())
            receipts.append(rec)
    stack = np.stack([out[c] for c in CHANNELS], axis=0)
    if not return_receipt:
        return stack
    return stack, dict(channels=list(CHANNELS), receipts=receipts,
                       cell_m=CELL_M, window_cells=WINDOW, sigma_cells=SIGMA_CELLS,
                       depth_window_m=[DEPTH_MIN_M, DEPTH_MAX_M],
                       catalogue_read=False, vertical_unit_verified=False)
