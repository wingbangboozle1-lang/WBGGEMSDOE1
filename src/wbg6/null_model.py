"""Null-truth Monte-Carlo estimator of the DOE GEMS DTI score.

Idea
----
The private truth is a set of expert-labelled faults that are *absent* from the
public catalogue.  We cannot see it, but we know the official metric exactly, so
for any candidate raster and any hypothesised truth set we can compute the exact
score.  Averaging over a whole ensemble of plausible truth sets converts that
into an *expected* score -- an estimator that needs no organizer labels.

Truth ensemble (the explicit assumption): ``K`` fault cells arranged as line
segments whose length distribution is taken from the public catalogue, oriented
uniformly and placed uniformly at random inside the scored footprint, and never
on a mapped-fault cell (the competition defines the truth as faults that are not
in the catalogue).  This is a deliberately structure-free null: it asks "how well
would this raster do if the new faults were distributed like faults, anywhere?".

``K`` itself is calibrated on the one historical submission whose dot layout is
provably spatially uniform (the 5 px lattice ``r13-lattice-s5``, 206,895 dots,
reported 0.0904 -- its distance-to-catalogue quantiles match the footprint's to
within 0.1 px).  Its score therefore depends on nothing but ``K``.

Everything this module returns is a MODEL-ESTIMATE under the stated null.  It is
never an organizer result, and a null that ignores real geological structure will
mis-rank rasters that *do* carry structure.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

RADIUS = 3.0
ALPHA = 0.2
BETA = 0.8


def kernel_field(dist: np.ndarray) -> np.ndarray:
    """Triangular kernel value from a distance (pixels) to the nearest positive."""
    return np.maximum(1.0 - np.asarray(dist, np.float32) / RADIUS, 0.0)


def segments_from_catalogue(cat: np.ndarray, rng: np.random.Generator,
                            n_seg: int) -> list[np.ndarray]:
    """Draw ``n_seg`` random axis-aligned-in-rotation segments.

    Length is drawn (with replacement) from the empirical distribution of mapped
    fault segment lengths, so the truth ensemble has catalogue-like geometry.
    """
    lab, n = ndi.label(cat, structure=np.ones((3, 3), bool))
    if n == 0:
        return []
    sizes = np.bincount(lab.ravel())[1:]
    lengths = sizes[sizes >= 2]
    if lengths.size == 0:
        lengths = np.array([5])
    h, w = cat.shape
    out = []
    for _ in range(n_seg):
        L = int(rng.choice(lengths))
        L = max(2, min(L, 60))
        th = rng.uniform(0, np.pi)
        dy, dx = np.sin(th), np.cos(th)
        y0 = rng.uniform(0, h - 1)
        x0 = rng.uniform(0, w - 1)
        t = np.arange(L)
        ys = np.round(y0 + t * dy).astype(int)
        xs = np.round(x0 + t * dx).astype(int)
        keep = (ys >= 0) & (ys < h) & (xs >= 0) & (xs < w)
        if keep.any():
            out.append(ys[keep] * w + xs[keep])
    return out


def draw_truth(cat: np.ndarray, foot: np.ndarray, K: int,
               rng: np.random.Generator, max_tries: int = 40) -> np.ndarray:
    """One truth draw with approximately ``K`` cells (never on the catalogue)."""
    seg_sizes = []
    lab, n = ndi.label(cat, structure=np.ones((3, 3), bool))
    if n:
        sizes = np.bincount(lab.ravel())[1:]
        seg_sizes = sizes[sizes >= 2]
    mean_len = float(np.mean(seg_sizes)) if len(seg_sizes) else 5.0
    n_seg = max(1, int(round(K / max(mean_len, 2.0))))
    flat_cat = cat.ravel()
    flat_foot = foot.ravel()
    truth = np.zeros(cat.shape, bool)
    flat = truth.ravel()
    for seg in segments_from_catalogue(cat, rng, n_seg):
        ok = flat_foot[seg] & ~flat_cat[seg]
        flat[seg[ok]] = True
    # trim / pad to K
    idx = np.flatnonzero(flat)
    if idx.size > K:
        drop = rng.choice(idx, size=idx.size - K, replace=False)
        flat[drop] = False
    elif idx.size < K:
        need = K - idx.size
        cand = np.flatnonzero(flat_foot & ~flat_cat & ~flat)
        if cand.size:
            add = rng.choice(cand, size=min(need, cand.size), replace=False)
            flat[add] = True
    for _ in range(max_tries):
        break
    return truth


def dti_for(values: np.ndarray, truth: np.ndarray) -> float:
    """Exact official DTI of a [0,1] raster against a binary truth."""
    d_dot = ndi.distance_transform_edt(~(values > 0))
    k_dot = kernel_field(d_dot)
    tp = float(k_dot[truth].sum())
    if tp <= 0.0:
        return 0.0
    d_tr = ndi.distance_transform_edt(~truth)
    k_tr = kernel_field(d_tr)
    fp = float((values * (1.0 - k_tr)).sum())
    fn = float(truth.sum()) - tp
    return tp / (tp + ALPHA * fp + BETA * fn + 1e-12)


def expected_dti(values: np.ndarray, cat: np.ndarray, foot: np.ndarray, K: int,
                 draws: int = 60, seed: int = 11) -> dict:
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(draws):
        t = draw_truth(cat, foot, K, rng)
        scores.append(dti_for(values, t))
    s = np.array(scores)
    return {"mean": float(s.mean()), "sd": float(s.std(ddof=1)) if draws > 1 else 0.0,
            "se": float(s.std(ddof=1) / np.sqrt(draws)) if draws > 1 else 0.0,
            "p05": float(np.quantile(s, 0.05)), "p95": float(np.quantile(s, 0.95)),
            "draws": int(draws), "K": int(K)}
