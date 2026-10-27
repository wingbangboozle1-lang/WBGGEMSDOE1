import hashlib

import numpy as np
import pytest
from scipy.stats import spearmanr

from gems import novelty


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_compact_binary_registry_matches_exact_spearman_and_dot_overlap(tmp_path):
    footprint = np.ones((5, 6), dtype=bool)
    values = np.zeros(footprint.sum(), dtype="<f4")
    positive = np.array([2, 9, 18, 27], dtype=np.uint32)
    values[positive] = 1
    cache = tmp_path / "positions.npy"
    np.save(cache, positive, allow_pickle=False)
    entry = {
        "id": "registry-001",
        "file": "reference.tif",
        "footprint_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
        "comparison_cache_path": cache.name,
        "comparison_cache_sha256": _sha(cache),
        "comparison_encoding": "uint32_footprint_positive_positions",
    }
    surface = np.arange(30, dtype=np.float32).reshape(5, 6)
    report = novelty.compare_registry_surfaces(
        {"A": surface, "B": surface[::-1].copy()},
        footprint,
        [entry],
        tmp_path,
        sample_size=30,
    )
    expected = spearmanr(surface.ravel(), values).statistic
    assert report["A"]["rows"][0]["raw_spearman"] == pytest.approx(expected)
    assert report["A"]["raw_rank_pixels"] == 30
    assert report["B"]["registry_unique_rasters"] == 1

    dots = np.zeros_like(footprint)
    dots.ravel()[positive] = True
    final = novelty.compare_registry(
        dots.astype(np.float32), footprint, [entry], tmp_path, dots=dots, sample_size=30
    )
    assert final["max_dot_overlap"] == 1.0
    assert final["passed"] is False


def test_compact_value_registry_verifies_footprint_content(tmp_path):
    footprint = np.ones((3, 3), bool)
    values = np.linspace(0, 1, 9, dtype="<f4")
    cache = tmp_path / "values.npy"
    np.save(cache, values, allow_pickle=False)
    entry = {
        "id": "registry-001",
        "file": "graded.tif",
        "footprint_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
        "comparison_cache_path": cache.name,
        "comparison_cache_sha256": _sha(cache),
        "comparison_encoding": "float32_footprint_values",
    }
    surface = values.reshape(3, 3)
    report = novelty.compare_registry_surfaces(
        {"B": surface}, footprint, [entry], tmp_path, sample_size=9
    )["B"]
    assert report["max_abs_rank_correlation"] == 1.0
    assert report["passed"] is False
