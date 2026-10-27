"""DTI identities against the published equations (page 967)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems1.metric import dti_binary, dti_bruteforce, dti_exact


def test_official_numeric_example_identity():
    # Published worked example (page 967): TPw=3.00, FPw=1.89, FNw=2.00, DTI printed as 0.60.
    # Exact identity is 3 / (3 + 0.2*1.89 + 0.8*2) = 3/4.978 ≈ 0.60265; 0.60 is rounding.
    tp, fp, fn = 3.00, 1.89, 2.00
    dti = tp / (tp + 0.2 * fp + 0.8 * fn)
    assert abs(dti - 3.0 / 4.978) < 1e-12
    assert round(dti, 2) == 0.60


def test_binary_matches_bruteforce():
    rng = np.random.default_rng(0)
    pred = rng.random((12, 12)) > 0.92
    truth = np.zeros((12, 12), bool)
    truth[3, 3:8] = True
    a = dti_binary(pred, truth)
    b = dti_bruteforce(pred.astype(float), truth)
    assert abs(a["tp"] - b["tp"]) < 1e-9
    assert abs(a["fp"] - b["fp"]) < 1e-9
    assert abs(a["dti"] - b["dti"]) < 1e-9


def test_soft_matches_binary_on_01():
    pred = np.zeros((10, 10), np.float32)
    pred[2, 2] = 1.0
    pred[5, 5] = 1.0
    truth = np.zeros((10, 10), bool)
    truth[2, 3] = True
    truth[5, 5] = True
    a = dti_exact(pred, truth)
    b = dti_binary(pred > 0, truth)
    assert abs(a["dti"] - b["dti"]) < 1e-9


def test_range_guard():
    pred = np.zeros((4, 4), np.float32)
    pred[1, 1] = 1.2
    truth = np.zeros((4, 4), bool)
    truth[1, 1] = True
    try:
        dti_exact(pred, truth)
        raise AssertionError("should have rejected out-of-range")
    except ValueError:
        pass


if __name__ == "__main__":
    test_official_numeric_example_identity()
    test_binary_matches_bruteforce()
    test_soft_matches_binary_on_01()
    test_range_guard()
    print("test_metric.py PASS")
