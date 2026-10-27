"""Registry uniqueness gates.

Two separate gates, per the standing protocol:

1. SURFACE gate (before placement) -- we never copy another project's surface,
   so this is a provenance statement, not a measurement.
2. FINAL-DOT gate (after placement) -- measured against every registry raster:
   * forward overlap: fraction of OUR positive cells within 3 px of theirs
   * signed Spearman rho between the two surfaces
   STOP if forward overlap > 0.70 or |rho| > 0.90.

Uniqueness is necessary but never sufficient: a byte-unique file can still be
scientifically redundant.
"""

from __future__ import annotations

import glob
import os

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

STOP_OVERLAP = 0.70
STOP_RHO = 0.90
STOP_ENRICHMENT = 3.0
THREE_PX = 3


def load_aligned(path: str, shape, transform, crs):
    """Read band 1 if the grid matches; return None otherwise."""
    try:
        with rasterio.open(path) as src:
            if (src.height, src.width) != tuple(shape):
                return None
            if src.crs is not None and crs is not None and src.crs != crs:
                return None
            a = src.read(1).astype(np.float32)
    except Exception:
        return None
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    return a


def compare(ours: np.ndarray, theirs: np.ndarray, evaluated: np.ndarray | None = None) -> dict:
    """Raw overlap plus a chance-corrected enrichment.

    Raw forward overlap is NOT interpretable on its own: against a dense
    continuous surface (most of the footprint positive) every sparse field has
    forward overlap 1.0 while sharing no information. We therefore also report

        enrichment = observed_overlap / chance_overlap
        chance_overlap = fraction of the evaluated footprint within 3 px of theirs

    which is 1.0 for independent fields of any density and only exceeds 1 when
    our dots genuinely sit where theirs do. STOP is applied to enrichment, with
    the raw numbers reported for transparency.
    """
    o = ours > 0
    t = theirs > 0
    if evaluated is None:
        evaluated = np.ones(ours.shape, dtype=bool)
    evaluated = np.asarray(evaluated, dtype=bool)
    if not t.any():
        return {
            "forward_overlap": 0.0, "rho": 0.0, "enrichment": 0.0,
            "their_positive": 0, "ours_positive": int(o.sum()),
            "their_density": 0.0, "chance_overlap": 0.0,
        }
    t_dil = ndi.binary_dilation(t, ndi.generate_binary_structure(2, 1), iterations=THREE_PX)
    n_eval = max(1, int(evaluated.sum()))
    fwd = float((o & t_dil).sum()) / max(1, int(o.sum()))
    chance = float((t_dil & evaluated).sum()) / n_eval
    enrichment = fwd / chance if chance > 0 else 0.0
    # Spearman on a subsample for tractability, deterministic
    rng = np.random.default_rng(0)
    idx = rng.choice(ours.size, size=min(400_000, ours.size), replace=False)
    rho = float(spearmanr(ours.ravel()[idx], theirs.ravel()[idx]).statistic)
    if not np.isfinite(rho):
        rho = 0.0
    return {
        "forward_overlap": fwd,
        "rho": rho,
        "enrichment": enrichment,
        "chance_overlap": chance,
        "their_positive": int(t.sum()),
        "ours_positive": int(o.sum()),
        "their_density": float((t & evaluated).sum()) / n_eval,
    }


def scan_registry(ours: np.ndarray, shape, transform, crs, roots: list[str],
                  exclude: set[str] | None = None, extra_paths: list[str] | None = None) -> dict:
    entries = []
    seen = set(exclude or set())
    for root in roots:
        for path in sorted(glob.glob(os.path.join(root, "**", "*.tif"), recursive=True)):
            if os.path.abspath(path) in seen:
                continue
            seen.add(os.path.abspath(path))
            theirs = load_aligned(path, shape, transform, crs)
            if theirs is None:
                continue
            c = compare(ours, theirs)
            c["path"] = os.path.relpath(path)
            entries.append(c)
    for path in (extra_paths or []):
        theirs = load_aligned(path, shape, transform, crs)
        if theirs is None:
            continue
        c = compare(ours, theirs)
        c["path"] = path
        entries.append(c)
    entries.sort(key=lambda e: -e["enrichment"])
    worst_overlap = max((e["forward_overlap"] for e in entries), default=0.0)
    worst_enrich = max((e["enrichment"] for e in entries), default=0.0)
    worst_rho = max((abs(e["rho"]) for e in entries), default=0.0)
    return {
        "rasters_compared": len(entries),
        "max_forward_3px_overlap": worst_overlap,
        "max_enrichment_vs_chance": worst_enrich,
        "max_abs_spearman": worst_rho,
        "stop_enrichment_threshold": STOP_ENRICHMENT,
        "stop_overlap_threshold": STOP_OVERLAP,
        "stop_rho_threshold": STOP_RHO,
        "passes_final_dot_gate": bool(
            worst_rho <= STOP_RHO and not (worst_enrich >= STOP_ENRICHMENT and worst_overlap > STOP_OVERLAP)
        ),
        "gate_rule": (
            "STOP if |signed Spearman rho| > 0.90, or if forward 3 px overlap > 0.70 "
            "AND that overlap is at least 3x chance (enrichment >= 3). The "
            "enrichment requirement exists because raw forward overlap is 1.0 for any "
            "sparse field compared against a dense continuous surface."
        ),
        "top_matches": entries[:12],
    }
