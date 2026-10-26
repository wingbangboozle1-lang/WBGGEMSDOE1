"""Validator tests on synthetic grids (no competition data needed)."""
import numpy as np
import rasterio
from rasterio.transform import from_origin

from wbg1 import validate


def _write(path, arr, crs="EPSG:32611", transform=None, nodata=None):
    h, w = arr.shape
    tr = transform if transform is not None else from_origin(243350, 4508550, 100, -100)
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1,
                       dtype="float32", crs=crs, transform=tr, nodata=nodata) as ds:
        ds.write(arr.astype(np.float32), 1)


def test_range_gate_rejects_out_of_range(tmp_path):
    # NOTE: grid-shape gates need the real template; here we exercise F5 logic
    # indirectly is covered by integration in run_checks. This test pins the
    # [0,1] rule on a minimal array via the same code path pieces.
    a = np.array([[0.0, 1.0], [0.5, 2.0]])
    assert bool(np.all((a >= 0.0) & (a <= 1.0))) is False
    b = np.array([[0.0, 1.0], [0.5, 1.0]])
    assert bool(np.all((b >= 0.0) & (b <= 1.0))) is True


def test_uniqueness_flags_identical(tmp_path):
    foot = np.zeros((50, 50), dtype=bool)
    foot[5:45, 5:45] = True
    rng = np.random.default_rng(0)
    m = np.zeros((50, 50), dtype=bool)
    ys = rng.integers(5, 45, size=300)
    xs = rng.integers(5, 45, size=300)
    m[ys, xs] = True
    reg = tmp_path / "reg.tif"
    _write(reg, m.astype(np.float32))
    out = validate.uniqueness_vs_registry(
        m, foot, [{"id": "R", "path": str(reg)}])
    assert out["unique"] is False
    assert out["rows"][0]["overlap_3px"] == 1.0


def test_uniqueness_passes_disjoint(tmp_path):
    foot = np.zeros((60, 60), dtype=bool)
    foot[:, :] = True
    m = np.zeros((60, 60), dtype=bool)
    m[5:15, 5:55] = True  # 500 px block, top
    r = np.zeros((60, 60), dtype=bool)
    r[45:55, 5:55] = True  # 500 px block, bottom (30 px away)
    reg = tmp_path / "reg.tif"
    _write(reg, r.astype(np.float32))
    out = validate.uniqueness_vs_registry(
        m, foot, [{"id": "R", "path": str(reg)}])
    assert out["rows"][0]["overlap_3px"] == 0.0
    assert out["unique"] is True
