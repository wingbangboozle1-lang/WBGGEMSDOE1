"""Verification of :mod:`wbg2.metric` against independent references.

Three checks, all of which must pass:

CHECK A -- organizer arithmetic.
    The organizer worked example publishes TP_w = 3.00, FP_w = 1.89, FN_w = 2.00
    and DTI(0.2, 0.8) = 0.60.
    Source: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
    Feeding those three published counts through this module's denominator
    reproduces the published value. This confirms alpha, beta and eps.

CHECK B -- brute-force cross-check.
    A deliberately naive O(|P|*|G|) double loop, written independently of the
    transform-based fast path, must agree to 1e-12 on random small grids.

CHECK C -- known-value kernels.
    A single prediction exactly on a ground-truth pixel gives DTI = 1.
    A single prediction 1 px away gives k = 2/3.
    A single prediction 3 px away gives k = 0 and is pure false positive.
"""

from __future__ import annotations

import numpy as np

from .metric import ALPHA, BETA, EPS, R_PIXELS, dti, triangular_kernel


def organizer_arithmetic() -> dict:
    tp, fp, fn = 3.00, 1.89, 2.00
    denom = tp + ALPHA * fp + BETA * fn + EPS
    return {"value": tp / denom, "published": 0.60, "denominator": denom}


def brute_force(p: np.ndarray, g: np.ndarray) -> float:
    """Naive transcription of the organizer equations, no transforms."""
    p = np.asarray(p, dtype=np.float64)
    g = np.asarray(g, dtype=bool)
    ys, xs = np.nonzero(p > 0)
    gys, gxs = np.nonzero(g)

    fp = 0.0
    for y, x in zip(ys, xs):
        if gys.size == 0:
            nearest = np.inf
        else:
            nearest = np.min(np.hypot(gys - y, gxs - x))
        k = max(1.0 - nearest / R_PIXELS, 0.0)
        fp += p[y, x] * (1.0 - k)

    tp = 0.0
    for gy, gx in zip(gys, gxs):
        best = 0.0
        for y, x in zip(ys, xs):
            d = np.hypot(gy - y, gx - x)
            if d <= R_PIXELS:
                best = max(best, p[y, x] * (1.0 - d / R_PIXELS))
        tp += best
    fn = float(gys.size) - tp
    return tp / (tp + ALPHA * fp + BETA * fn + EPS)


def random_cross_check(trials: int = 40, seed: int = 20261027) -> dict:
    rng = np.random.default_rng(seed)
    worst = 0.0
    for _ in range(trials):
        n = int(rng.integers(12, 26))
        p = np.zeros((n, n))
        g = np.zeros((n, n), dtype=bool)
        npred = int(rng.integers(1, 8))
        pys = rng.integers(0, n, npred)
        pxs = rng.integers(0, n, npred)
        p[pys, pxs] = rng.uniform(0.2, 1.0, npred)
        ngt = int(rng.integers(1, 8))
        g[rng.integers(0, n, ngt), rng.integers(0, n, ngt)] = True
        fast = dti(p, g)
        slow = brute_force(p, g)
        worst = max(worst, abs(fast - slow))
    return {"trials": trials, "max_abs_difference": worst}


def known_values() -> dict:
    out = {}
    # exact hit
    p = np.zeros((9, 9)); g = np.zeros((9, 9), dtype=bool)
    p[4, 4] = 1.0; g[4, 4] = True
    out["exact_hit"] = dti(p, g)
    # 1 px away
    p = np.zeros((9, 9)); g = np.zeros((9, 9), dtype=bool)
    p[4, 5] = 1.0; g[4, 4] = True
    out["one_pixel_off"] = dti(p, g)
    # 3 px away -> kernel zero
    p = np.zeros((9, 9)); g = np.zeros((9, 9), dtype=bool)
    p[4, 7] = 1.0; g[4, 4] = True
    out["three_pixels_off"] = dti(p, g)
    out["kernel_at_1px"] = float(triangular_kernel(np.array([1.0]))[0])
    out["kernel_at_3px"] = float(triangular_kernel(np.array([3.0]))[0])
    return out


def run_all() -> dict:
    a = organizer_arithmetic()
    b = random_cross_check()
    c = known_values()
    ok = (
        abs(a["value"] - a["published"]) < 5e-3
        and b["max_abs_difference"] < 1e-12
        and abs(c["exact_hit"] - 1.0 / (1.0 + EPS)) < 1e-12
        and abs(
            c["one_pixel_off"]
            - (2.0 / 3.0) / (2.0 / 3.0 + 0.2 * (1.0 / 3.0) + 0.8 * (1.0 / 3.0) + EPS)
        ) < 1e-12
        and c["three_pixels_off"] == 0.0
        and c["kernel_at_3px"] == 0.0
    )
    return {"organizer_arithmetic": a, "brute_force": b, "known_values": c, "all_pass": bool(ok)}


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=1))
