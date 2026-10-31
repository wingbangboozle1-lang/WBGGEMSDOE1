"""Analytic checks for the WBG31-E1 Euler channels (no competition data needed)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg31.euler import CELL_M, euler_solution_density  # noqa: E402


def _point_source(n, depth_m, centre_cells, shape=(90, 90)):
    """Field and vertical derivative of T=(rho^2+z^2)^(-N/2) for a point source."""
    rr, cc = np.indices(shape, dtype=float)
    x = cc * CELL_M
    y = -rr * CELL_M
    x0 = centre_cells[1] * CELL_M
    y0 = -centre_cells[0] * CELL_M
    rho2 = (x - x0) ** 2 + (y - y0) ** 2
    R = rho2 + depth_m ** 2
    T = R ** (-n / 2.0)
    Tz = n * depth_m * R ** (-n / 2.0 - 1.0)  # dT/dz at the surface, source below
    return T, Tz


def test_point_source_solutions_cluster_at_true_position_and_depth():
    depth = 800.0
    centre = (45.3, 44.6)
    T, Tz = _point_source(2, depth, centre)
    footprint = np.ones(T.shape, bool)
    density, rec = euler_solution_density(T, Tz, footprint, 2, return_receipt=True)
    assert rec["accepted_solutions"] > 0
    assert np.isfinite(density).all()
    peak = np.unravel_index(np.argmax(density), density.shape)
    assert abs(peak[0] - centre[0]) <= 1.5 and abs(peak[1] - centre[1]) <= 1.5
    assert rec["depth_median_m"] is not None
    assert abs(rec["depth_median_m"] - depth) / depth < 0.15


def test_wrong_structural_index_does_not_concentrate_solutions():
    T, Tz = _point_source(2, 800.0, (45.3, 44.6))
    footprint = np.ones(T.shape, bool)
    d_true = euler_solution_density(T, Tz, footprint, 2)
    d_wrong = euler_solution_density(T, Tz, footprint, 0)
    # The correct index places more weight in a single cell than the wrong one.
    assert d_true.max() > d_wrong.max()


def test_outside_footprint_is_zero_and_nonfinite_input_is_excluded():
    T, Tz = _point_source(2, 800.0, (45.3, 44.6))
    footprint = np.ones(T.shape, bool)
    footprint[:, :10] = False
    T = T.copy()
    T[5, 5] = np.nan
    density = euler_solution_density(T, Tz, footprint, 2)
    assert (density[~footprint] == 0).all()
    assert np.isfinite(density).all()


def test_rejects_bad_window_and_shape():
    T, Tz = _point_source(2, 800.0, (45.3, 44.6), shape=(20, 20))
    footprint = np.ones(T.shape, bool)
    for bad in (4, 1):
        try:
            euler_solution_density(T, Tz, footprint, 1, window=bad)
        except ValueError:
            continue
        raise AssertionError("window %s should be rejected" % bad)
    try:
        euler_solution_density(T, Tz[:10], footprint, 1)
    except ValueError:
        return
    raise AssertionError("shape mismatch should be rejected")


def _contact(depth_m, centre_cells, shape=(90, 90)):
    """Degree-0 homogeneous field T = atan(z_s / rho) of a buried edge (N=0)."""
    rr, cc = np.indices(shape, dtype=float)
    x = cc * CELL_M
    y = -rr * CELL_M
    x0 = centre_cells[1] * CELL_M
    y0 = -centre_cells[0] * CELL_M
    rho = np.hypot(x - x0, y - y0)
    rho = np.maximum(rho, 1e-6)
    T = np.arctan2(depth_m, rho)
    Tz = -rho / (rho ** 2 + depth_m ** 2)  # dT/dz at the surface
    return T, Tz


def test_contact_n0_recovers_position_and_depth():
    depth = 600.0
    centre = (40.4, 45.7)
    T, Tz = _contact(depth, centre)
    footprint = np.ones(T.shape, bool)
    density, rec = euler_solution_density(T, Tz, footprint, 0, return_receipt=True)
    assert rec["accepted_solutions"] > 0, rec
    peak = np.unravel_index(np.argmax(density), density.shape)
    assert abs(peak[0] - centre[0]) <= 1.5 and abs(peak[1] - centre[1]) <= 1.5
    assert abs(rec["depth_median_m"] - depth) / depth < 0.25
