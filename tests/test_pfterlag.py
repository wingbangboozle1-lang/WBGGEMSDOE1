import numpy as np

from wbggems.pfterlag import build_pfterlag_surface, robust_z


def test_robust_z_zeros_exterior_and_invalid_values():
    rng = np.random.default_rng(18)
    values = rng.normal(size=(32, 40)).astype(np.float32)
    footprint = np.zeros(values.shape, dtype=bool)
    footprint[4:-4, 4:-4] = True
    values[10, 10] = np.nan
    scaled = robust_z(values, footprint)
    assert scaled.shape == values.shape
    assert scaled.dtype == np.float32
    assert np.isfinite(scaled).all()
    assert np.all(scaled[~footprint] == 0.0)
    assert scaled[10, 10] == 0.0
    assert np.max(np.abs(scaled)) <= 10.0


def test_pfterlag_surface_is_finite_bounded_and_detects_synthetic_shift():
    height, width = 112, 128
    rng = np.random.default_rng(20261031)
    yy, xx = np.mgrid[:height, :width]
    terrain = (xx >= 48).astype(np.float32) + rng.normal(0, 0.08, (height, width)).astype(np.float32)
    gravity = (xx >= 51).astype(np.float32) + rng.normal(0, 0.08, (height, width)).astype(np.float32)
    magnetic = (xx >= 51).astype(np.float32) + rng.normal(0, 0.08, (height, width)).astype(np.float32)
    terrain += 0.05 * np.sin(yy / 5.0).astype(np.float32)
    gravity += 0.05 * np.sin(yy / 5.0).astype(np.float32)
    magnetic += 0.05 * np.sin(yy / 5.0).astype(np.float32)
    footprint = np.ones((height, width), dtype=bool)
    footprint[:5, :] = False
    footprint[:, :5] = False

    surface, features, receipt = build_pfterlag_surface(terrain, gravity, magnetic, footprint)
    assert surface.shape == footprint.shape
    assert surface.dtype == np.float32
    assert np.isfinite(surface).all()
    assert surface.min() >= 0.0
    assert surface.max() <= 1.0
    assert np.all(surface[~footprint] == 0.0)
    assert receipt["surface_positive_pixels"] > 0
    assert "PFTL1_final_score" in features
    assert "iso_grav_anom_lag_gain_sigma3" in features
    assert "gravity_magnetic_offset_coherence_sigma8" in features
    assert all(np.isfinite(a).all() for a in features.values())
