"""Registry uniqueness gates.

Two separate gates, per the standing protocol:

1. SURFACE gate (before placement) -- we never copy another project's surface,
   a provenance statement is NOT a measured surface-gate pass.
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
            if src.count != 1 or src.crs != crs or src.transform != transform:
                return None
            a = src.read(1).astype(np.float32)
    except Exception:
        return None
    return a


def compare(ours: np.ndarray, theirs: np.ndarray, evaluated: np.ndarray | None = None) -> dict:
    """Diagnostic overlap and correlation; enrichment NEVER exempts a STOP.

    Forward distance uses Euclidean pixel distance. Undefined correlation is
    recorded as null; it cannot certify uniqueness. This legacy diagnostic is
    not a replacement for the pinned shared registry tool.
    """
    if ours.shape != theirs.shape or not np.isfinite(ours).all() or not np.isfinite(theirs).all():
        raise ValueError("Registry comparison needs aligned finite arrays")
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
    t_dil = ndi.distance_transform_edt(~t) <= THREE_PX
    n_eval = max(1, int(evaluated.sum()))
    fwd = float((o & t_dil).sum()) / max(1, int(o.sum()))
    chance = float((t_dil & evaluated).sum()) / n_eval
    enrichment = fwd / chance if chance > 0 else 0.0
    # Spearman on a subsample for tractability, deterministic
    rng = np.random.default_rng(0)
    idx = rng.choice(ours.size, size=min(400_000, ours.size), replace=False)
    rho = float(spearmanr(ours.ravel()[idx], theirs.ravel()[idx]).statistic)
    if not np.isfinite(rho):
        rho = None
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
    worst_rho = max((abs(e["rho"]) for e in entries if e["rho"] is not None), default=0.0)
    return {
        "rasters_compared": len(entries),
        "max_forward_3px_overlap": worst_overlap,
        "max_enrichment_vs_chance": worst_enrich,
        "max_abs_spearman": worst_rho,
        "stop_enrichment_threshold": STOP_ENRICHMENT,
        "stop_overlap_threshold": STOP_OVERLAP,
        "stop_rho_threshold": STOP_RHO,
        "passes_final_dot_gate": bool(
            bool(entries) and all(e["rho"] is not None for e in entries)
            and worst_rho <= STOP_RHO and worst_overlap <= STOP_OVERLAP
        ),
        "gate_rule": "STOP if |rho| > 0.90 OR forward Euclidean 3px overlap > 0.70; no density exemption.",
        "top_matches": entries[:12],
    }
