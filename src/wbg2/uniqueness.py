"""Retired WBG-2 pairwise diagnostic; never an approval or clearance gate.

Authoritative parallel-lane registry checks must use the pinned shared
``gems57.uniqueness`` implementation with its hash-verified inventory. This
module exists only to preserve diagnostics for the archived WBG-2 research
artifact. A directory scan here is necessarily partial and can NEVER return a
positive clearance. In particular, chance enrichment is diagnostic only and
must not waive the literal overlap STOP.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import rasterio
from scipy.stats import spearmanr
from gems57.uniqueness import OVERLAP_LIMIT, RHO_LIMIT, dot_overlap

THREE_PX = 3.0


def load_aligned(path: str, shape, transform, crs):
    """Read band 1 only when the full grid identity matches exactly."""
    try:
        with rasterio.open(path) as src:
            if (src.height, src.width) != tuple(shape):
                return None
            if src.transform != transform or src.crs != crs:
                return None
            a = src.read(1).astype(np.float32)
    except Exception:
        return None
    return np.where(np.isfinite(a), a, 0.0)


def compare(ours: np.ndarray, theirs: np.ndarray, evaluated: np.ndarray | None = None) -> dict:
    """Return non-authoritative diagnostics; never use these to promote a file.

    ``forward_overlap`` calls the pinned shared template's positive-support,
    Euclidean three-pixel overlap function. Chance enrichment and sampled rho
    are retained only to explain historical WBG-2 measurements; they cannot
    exempt overlap above the standing limit.
    """
    ours = np.asarray(ours)
    theirs = np.asarray(theirs)
    if ours.shape != theirs.shape:
        raise ValueError("candidate and comparison raster grids differ")
    if evaluated is None:
        evaluated = np.ones(ours.shape, dtype=bool)
    evaluated = np.asarray(evaluated, dtype=bool)
    if evaluated.shape != ours.shape:
        raise ValueError("evaluation mask grid differs")
    mine = np.isfinite(ours) & (ours > 0) & evaluated
    their_support = np.isfinite(theirs) & (theirs > 0) & evaluated
    masked_ours = np.where(evaluated, ours, 0.0)
    masked_theirs = np.where(evaluated, theirs, 0.0)
    overlap = dot_overlap(masked_ours, masked_theirs, radius_px=THREE_PX)
    if not their_support.any():
        return {
            "forward_overlap": overlap,
            "rho_sampled_diagnostic_only": 0.0,
            "chance_overlap_diagnostic_only": 0.0,
            "enrichment_diagnostic_only": 0.0,
            "their_positive": 0,
            "ours_positive": int(mine.sum()),
            "literal_pairwise_stop": overlap > OVERLAP_LIMIT,
            "diagnostic_only": True,
        }
    # Deterministic subset for a historical diagnostic only. The pinned shared
    # evaluator, not this sample, governs any authorized promotion decision.
    rng = np.random.default_rng(0)
    idx = rng.choice(ours.size, size=min(400_000, ours.size), replace=False)
    sample_ours, sample_theirs = ours.ravel()[idx], theirs.ravel()[idx]
    if np.ptp(sample_ours) == 0 or np.ptp(sample_theirs) == 0:
        rho = 0.0
    else:
        rho = float(spearmanr(sample_ours, sample_theirs).statistic)
        if not np.isfinite(rho):
            rho = 0.0
    # Report chance coverage only as context. It is never part of STOP logic.
    from scipy import ndimage as ndi

    r = int(np.ceil(THREE_PX))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = yy * yy + xx * xx <= THREE_PX * THREE_PX
    near = ndi.binary_dilation(their_support, structure=disk)
    n_eval = max(1, int(evaluated.sum()))
    chance = float((near & evaluated).sum()) / n_eval
    enrichment = overlap / chance if chance > 0 else 0.0
    return {
        "forward_overlap": overlap,
        "rho_sampled_diagnostic_only": rho,
        "chance_overlap_diagnostic_only": chance,
        "enrichment_diagnostic_only": enrichment,
        "their_positive": int(their_support.sum()),
        "ours_positive": int(mine.sum()),
        "literal_pairwise_stop": bool(overlap > OVERLAP_LIMIT or abs(rho) > RHO_LIMIT),
        "diagnostic_only": True,
    }


def scan_registry(ours: np.ndarray, shape, transform, crs, roots: list[str],
                  exclude: set[str] | None = None, extra_paths: list[str] | None = None) -> dict:
    """Scan paths for forensic context, but fail closed on clearance every time."""
    entries = []
    seen = set(exclude or set())
    for root in roots:
        for path in sorted(glob.glob(os.path.join(root, "**", "*.tif"), recursive=True)):
            absolute = os.path.abspath(path)
            if absolute in seen:
                continue
            seen.add(absolute)
            theirs = load_aligned(path, shape, transform, crs)
            if theirs is None:
                continue
            row = compare(ours, theirs)
            row["path"] = os.path.relpath(path)
            entries.append(row)
    for path in extra_paths or []:
        theirs = load_aligned(path, shape, transform, crs)
        if theirs is None:
            continue
        row = compare(ours, theirs)
        row["path"] = path
        entries.append(row)

    entries.sort(key=lambda row: -row["forward_overlap"])
    worst_overlap = max((row["forward_overlap"] for row in entries), default=None)
    worst_rho = max((abs(row["rho_sampled_diagnostic_only"]) for row in entries), default=None)
    worst_enrichment = max((row["enrichment_diagnostic_only"] for row in entries), default=None)
    return {
        "rasters_compared": len(entries),
        "inventory_complete": False,
        "max_forward_3px_overlap": worst_overlap,
        "max_enrichment_diagnostic_only": worst_enrichment,
        "max_abs_sampled_spearman_diagnostic_only": worst_rho,
        "overlap_stop_threshold_from_shared_template": OVERLAP_LIMIT,
        "rho_stop_threshold_from_shared_template": RHO_LIMIT,
        "literal_stop_observed": any(row["literal_pairwise_stop"] for row in entries),
        "passes_final_dot_gate": False,
        "clearance": "NOT ESTABLISHED — partial directory diagnostics cannot clear the pinned shared registry gate",
        "gate_rule": "The pinned shared template uses literal positive-support overlap and correlation thresholds. Chance enrichment is diagnostic only; no density exemption is permitted.",
        "top_matches": entries[:12],
    }
