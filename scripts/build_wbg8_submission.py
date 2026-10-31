#!/usr/bin/env python3
"""Build WBG-8: a unique, portal-safe GeoTIFF candidate for the GEMS prize.

Hypothesis (registered 2026-10-31, lane WBG-8):
  The focus-site champion family (D2.8 -> B1 -> B2, 0.2600 -> 0.2778
  USER-REPORTED) shows that the winning *geometry* is a ~37,654-dot
  off-catalogue (>=3 px) Poisson-300 m dot field, and that successive
  exclusion of catalogue-adjacent dots raised the score.  WBG-8 keeps that
  geometry but replaces the h19-5 placement surface with an independently
  implemented multi-layer BLIND geophysical ridge composite (RTP Hessian
  ridge energy, geodetic strain-rate magnitude, isostatic-gravity edge
  energy, basement-depth steps, detrended-topographic fronts) blended with
  catalogue-derived structural priors (distance rings 3-8 px, trace-tip
  lobes, relay-corridor fill) computed from the *visible* catalogue per
  fold during holdout and from the full catalogue for final placement.

Mechanism:
  Blind faults sit on linear geophysical/topographic contrasts that the
  public catalogue did not map; 300 m-spaced dots inside a 300 m triangular
  kernel buy distinct credit; excluding d<3 px removes dots that can only
  be false positives against hidden new-fault truth.

Non-fault mimic (named):
  Lithologic contacts and intrusive boundaries produce the same magnetic/
  gravity ridge signatures without being faults; basin-range pediment
  scarps (non-fault) mimic detrended-elevation fronts.

Protocol:
  * Efficacy = per-fold hide-and-recover: catalogue priors derived from
    fold['visible'] ONLY; dots selected inside fold['valid']; pooled DTI
    (gems-segment-pooled-v1, alpha .2, beta .8, 300 m kernel) + spatial CI.
  * Leakage canary: every blind layer and every visible-only prior tested
    alone vs withheld truth; AUC > 0.90 = leakage until proven otherwise.
  * Uniqueness: all 118 owner-reported scored registry rasters re-fetched
    and hash-pinned; rank-correlation and both-direction 3 px overlaps
    measured; the degenerate dense-lattice rule is reported separately.
  * Portal safety: written with the shared strict writer, outside=zeros
    (all-finite), values strictly in [0,1] - this is the format that fixes
    the portal error "Predicted values must be in range [0, 1]".
  * Score projection: the family-grouped geometry score model
    (MODEL-ESTIMATE, grouped RMSE 0.113) is applied and labelled; it is
    never written as an organizer score.

Outputs:
  docs/downloads/<NAME>.tif .zip .validator.json
  evidence/wbg8_mridge/run_card.json  evidence/wbg8_mridge/holdout.json
  evidence/wbg8_mridge/uniqueness.json  evidence/wbg8_mridge/score_estimate.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import holdout, submission  # noqa: E402

SEED = 20261031
N_DOTS = 37654          # champion-family dot budget (B2 = 37,654)
MIN_SEP_PX = 3.0        # Poisson 300 m kernel-disjoint spacing
OFFCAT_MIN_PX = 3.0     # B2-cleanest exclusion: no dot within 3 px of catalogue
DOWNLOADS = ROOT / "docs" / "downloads"
EVIDENCE = ROOT / "evidence" / "wbg8"
SCORE_MODEL = ROOT / "evidence" / "wbg6_score_model.json"
SCORED_FETCH = ROOT / "evidence" / "scored_raster_fetch.json"
LATTICE_DOT_FLOOR = 100000  # registry rasters this dense make the literal gate degenerate


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Blind geophysical layers (catalogue-free; identical across holdout folds)
# --------------------------------------------------------------------------

def hessian_ridge(band: np.ndarray, valid: np.ndarray,
                  scales=(1.5, 3.0, 6.0), beta: float = 0.5) -> np.ndarray:
    """Frangi-style ridge (lineament) energy, max over Gaussian scales.

    Ridge = same-sign Hessian eigenvalues with a dominant direction
    (|lambda_minor| << |lambda_major|).  Captures linear magnetic highs AND
    lows (dikes, contacts, faulted lithologic edges) without polarity bias.
    """
    out = np.zeros(band.shape, np.float32)
    filled = np.where(np.isfinite(band), band, 0).astype(np.float32)
    for s in scales:
        g = ndi.gaussian_filter(filled, s)
        gy, gx = np.gradient(g)
        fyy = np.gradient(gy, axis=0)
        fxx = np.gradient(gx, axis=1)
        fxy = np.gradient(gx, axis=0)
        tr = fxx + fyy
        det = fxx * fyy - fxy * fxy
        disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
        l1 = tr / 2.0 - disc
        l2 = tr / 2.0 + disc
        amin = np.minimum(np.abs(l1), np.abs(l2))
        amax = np.maximum(np.abs(l1), np.abs(l2))
        same = (l1 * l2) > 0
        rb = np.divide(amin, amax, out=np.zeros_like(amin), where=amax > 0)
        c = float(np.percentile(amax[valid], 90)) * 0.5
        c = max(c, 1e-9)
        s2 = amin * amin + amax * amax
        v = np.exp(-(rb * rb) / (2 * beta * beta)) * (1.0 - np.exp(-s2 / (2 * c * c)))
        v = np.where(same & valid, v, 0.0)
        np.maximum(out, v.astype(np.float32), out=out)
    return out


def grad_energy(band: np.ndarray, valid: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    """Gradient-magnitude edge energy on a smoothed band."""
    filled = np.where(np.isfinite(band), band, 0).astype(np.float32)
    g = ndi.gaussian_filter(filled, sigma)
    gy, gx = np.gradient(g)
    e = np.sqrt(gx * gx + gy * gy).astype(np.float32)
    e[~valid] = 0
    return e


def rank01(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Robust [0,1] rank transform inside the valid mask (ties -> mean rank)."""
    v = x[valid]
    if v.size == 0 or not np.isfinite(v).any():
        return np.zeros_like(x, np.float32)
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(v.size, np.float64)
    ranks[order] = np.arange(1, v.size + 1)
    # average ties
    sv = v[order]
    sr = ranks[order]
    i = 0
    while i < sv.size:
        j = i
        while j + 1 < sv.size and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            sr[i:j + 1] = sr[i:j + 1].mean()
        i = j + 1
    out = np.zeros_like(x, np.float32)
    out[valid] = ((ranks - 1) / max(v.size - 1, 1)).astype(np.float32)
    return out


def build_blind_layers(stack_path: Path, footprint: np.ndarray) -> dict:
    """Five catalogue-free propensity layers from the 19-band feature stack."""
    names = {b: i for i, b in enumerate([
        "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope",
        "tc", "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15",
        "iso_grav_anom_vg", "det_elev", "iso_grav_anom", "tmi",
        "depth_to_base_surf", "ieq_n100a15", "cond_surf", "iso_grav_anom_hg",
        "det_elev_slope"], 1)}
    layers: dict[str, np.ndarray] = {}
    with rasterio.open(stack_path) as ds:
        def read(band_name):
            a = ds.read(names[band_name]).astype(np.float32)
            nd = ds.nodata
            if nd is not None and np.isfinite(nd):
                a[a == np.float32(nd)] = np.nan
            a[~footprint] = np.nan
            return a

        t0 = time.time()
        rtp, valid = read("rtp"), footprint
        layers["ridge_rtp"] = hessian_ridge(rtp, valid)
        tc = read("tc")
        layers["ridge_tc"] = hessian_ridge(tc, valid)
        print(f"  [blind] magnetic ridges {time.time()-t0:.1f}s", flush=True)

        t0 = time.time()
        shear = np.abs(read("geod_shearrate"))
        inv2 = np.abs(read("geod_2ndinv"))
        strain = np.nan_to_num(shear, nan=0) + np.nan_to_num(inv2, nan=0)
        strain[~valid] = 0
        layers["strain"] = strain.astype(np.float32)
        print(f"  [blind] strain {time.time()-t0:.1f}s", flush=True)

        t0 = time.time()
        hx = read("iso_grav_anom_hg")
        vg = read("iso_grav_anom_vg")
        grav = np.sqrt(np.nan_to_num(hx, nan=0) ** 2 + np.nan_to_num(vg, nan=0) ** 2)
        grav[~valid] = 0
        layers["grav_edge"] = grav.astype(np.float32)
        print(f"  [blind] gravity edge {time.time()-t0:.1f}s", flush=True)

        t0 = time.time()
        layers["basement_step"] = grad_energy(read("depth_to_base_surf"), valid)
        print(f"  [blind] basement step {time.time()-t0:.1f}s", flush=True)

        t0 = time.time()
        slope = read("det_elev_slope")
        topo = grad_energy(slope, valid)
        layers["topo_front"] = topo
        print(f"  [blind] topo front {time.time()-t0:.1f}s", flush=True)

    return {k: rank01(v, footprint) for k, v in layers.items()}


# --------------------------------------------------------------------------
# Catalogue-derived structural priors (visible-only per fold; full for final)
# --------------------------------------------------------------------------

def ring_weight(d_cat: np.ndarray) -> np.ndarray:
    """Off-catalogue propensity by distance: zero at d<3, peak 3-6, zero >12."""
    w = np.zeros_like(d_cat, dtype=np.float32)
    m1 = (d_cat >= 3.0) & (d_cat <= 6.0)
    m2 = (d_cat > 6.0) & (d_cat < 12.0)
    w[m1] = 1.0
    w[m2] = (12.0 - d_cat[m2]) / 6.0
    return w


def tip_and_relay_surface(cat: np.ndarray, footprint: np.ndarray,
                          lobe_len_px: int = 8) -> np.ndarray:
    """Trace-tip continuation lobes + relay-corridor fill (axial stepovers)."""
    from skimage.morphology import skeletonize

    skel = skeletonize(cat)
    kern = np.ones((3, 3), int)
    kern[1, 1] = 0
    nbr = ndi.convolve(skel.astype(np.int64), kern, mode="constant", cval=0)
    tips = skel & (nbr == 1)
    sy, sx = np.nonzero(tips)
    surface = np.zeros(cat.shape, np.float32)
    tip_dirs: list[tuple[float, float, int, int]] = []
    for y, x in zip(sy, sx):
        body = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                if (dy or dx) and 0 <= y + dy < cat.shape[0]
                and 0 <= x + dx < cat.shape[1] and skel[y + dy, x + dx]]
        if not body:
            continue
        dy, dx = body[0]
        sdy, sdx = -dy, -dx  # outward along strike
        tip_dirs.append((float(sdy), float(sdx), int(y), int(x)))
        pdy, pdx = -sdx, sdy
        for lateral in (-1, 0, 1):
            for length in range(1, lobe_len_px + 1):
                wy = int(round(y + sdy * length + lateral * pdy * 0.5))
                wx = int(round(x + sdx * length + lateral * pdx * 0.5))
                if 0 <= wy < cat.shape[0] and 0 <= wx < cat.shape[1]:
                    w = 1.0 - 0.10 * (length - 1) - 0.30 * abs(lateral)
                    if w > surface[wy, wx]:
                        surface[wy, wx] = max(w, 0.0)
    # relay corridors: pairs of tips facing each other (anti-parallel outward
    # directions), 4-20 px apart with small lateral offset -> pull-apart fill
    for i, (udy1, vdx1, y1, x1) in enumerate(tip_dirs):
        for udy2, vdx2, y2, x2 in tip_dirs[i + 1:]:
            dy, dx = y2 - y1, x2 - x1
            dist = math.hypot(dy, dx)
            if not (4.0 <= dist <= 20.0):
                continue
            ndy, ndx = dy / dist, dx / dist
            # facing: each tip's outward direction aligned with the connecting line
            if not (udy1 * ndy + vdx1 * ndx > 0.5 and udy2 * (-ndy) + vdx2 * (-ndx) > 0.5):
                continue
            lateral = abs(udy1 * (-ndx) + vdx1 * ndy)  # 0 = perfectly axial
            if lateral > 0.5:
                continue
            steps = int(math.ceil(dist))
            for t in range(1, steps):
                wy = int(round(y1 + dy * t / steps))
                wx = int(round(x1 + dx * t / steps))
                w = 0.9 - 0.3 * (dist - 4.0) / 16.0
                if w > surface[wy, wx]:
                    surface[wy, wx] = max(w, 0.0)
    surface = np.where(footprint & ~cat, surface, 0.0)
    mx = float(surface.max())
    if mx > 0:
        surface = surface / mx
    return surface.astype(np.float32)


def build_prior(cat_visible: np.ndarray, footprint: np.ndarray,
                d_cat: np.ndarray) -> np.ndarray:
    """Mean of normalised distance rings, tip/relay surface (visible-only)."""
    rings = ring_weight(d_cat)
    rings = np.where(footprint & ~cat_visible, rings, 0.0).astype(np.float32)
    mx = float(rings.max())
    if mx > 0:
        rings = rings / mx
    tips = tip_and_relay_surface(cat_visible, footprint)
    prior = 0.5 * rings + 0.5 * tips
    prior[~footprint] = 0.0
    return prior.astype(np.float32)


# --------------------------------------------------------------------------
# Greedy Poisson (kernel-disjoint) dot selection
# --------------------------------------------------------------------------

def _greedy_pass(surface: np.ndarray, mask: np.ndarray, n_dots: int,
                 min_sep_px: float, seed: int, out: np.ndarray,
                 blocked: np.ndarray) -> int:
    """One greedy Poisson pass filling up to n_dots *new* dots into `out`."""
    h, w = surface.shape
    elig = mask & (surface > 0) & ~out
    idx = np.flatnonzero(elig.ravel())
    if idx.size == 0:
        return 0
    vals = surface.ravel()[idx]
    rng = np.random.default_rng(seed)
    order = np.lexsort((idx, -(vals + rng.uniform(0, 1e-9, idx.size))))
    r = int(math.ceil(min_sep_px))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = yy * yy + xx * xx <= min_sep_px * min_sep_px
    placed = 0
    for flat in idx[order]:
        if placed >= n_dots:
            break
        y, x = divmod(int(flat), w)
        if blocked[y, x]:
            continue
        out[y, x] = True
        placed += 1
        y0, y1 = max(0, y - r), min(h, y + r + 1)
        x0, x1 = max(0, x - r), min(w, x + r + 1)
        sub = disk[y0 - (y - r): y0 - (y - r) + (y1 - y0),
                   x0 - (x - r): x0 - (x - r) + (x1 - x0)]
        blocked[y0:y1, x0:x1] |= sub
    return placed


def select_dots(surface: np.ndarray, eligible: np.ndarray, n_dots: int,
                min_sep_px: float, seed: int) -> np.ndarray:
    """Coverage-stratified two-pass Poisson selection.

    Pass A (champion-family coverage): one dot in each viable 61-px (~6 km)
    block, blocks ranked by their best surface value -> footprint coverage
    like the 0.2778 champion (0.92 of 6-km blocks).
    Pass B: the remaining budget by global surface value, same Poisson disk.
    """
    h, w = surface.shape
    mask = eligible & (surface > 0)
    if not mask.any():
        raise ValueError("no eligible pixels for dot selection")
    out = np.zeros((h, w), bool)
    blocked = np.zeros((h, w), bool)
    # --- pass A: block quota ------------------------------------------------
    bs = 61
    by, bx = np.mgrid[0:h:bs, 0:w:bs]
    block_scores = []
    for y0 in range(0, h, bs):
        for x0 in range(0, w, bs):
            sl = (slice(y0, min(y0 + bs, h)), slice(x0, min(x0 + bs, w)))
            sub = mask[sl]
            if not sub.any():
                continue
            m = float(np.max(surface[sl][sub]))
            block_scores.append((m, y0, x0))
    block_scores.sort(key=lambda t: -t[0])
    n_blocks = 0
    for m, y0, x0 in block_scores:
        sl = (slice(y0, min(y0 + bs, h)), slice(x0, min(x0 + bs, w)))
        # best eligible pixel in the block (surface-ordered)
        sub_mask = mask[sl] & ~blocked[sl]
        if not sub_mask.any():
            continue
        sub_surf = np.where(sub_mask, surface[sl], -1.0)
        flat = int(np.argmax(sub_surf))
        if sub_surf.ravel()[flat] <= 0:
            continue
        ly, lx = divmod(flat, sl[1].stop - sl[1].start)
        y, x = y0 + ly, x0 + lx
        if blocked[y, x] or out[y, x]:
            continue
        r = int(math.ceil(min_sep_px))
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        disk = yy * yy + xx * xx <= min_sep_px * min_sep_px
        out[y, x] = True
        n_blocks += 1
        y0b, y1b = max(0, y - r), min(h, y + r + 1)
        x0b, x1b = max(0, x - r), min(w, x + r + 1)
        sub = disk[y0b - (y - r): y0b - (y - r) + (y1b - y0b),
                   x0b - (x - r): x0b - (x - r) + (x1b - x0b)]
        blocked[y0b:y1b, x0b:x1b] |= sub
    # --- pass B: global propensity fill ------------------------------------
    remaining = n_dots - int(out.sum())
    placed_b = _greedy_pass(surface, mask, remaining, min_sep_px,
                            seed + 7, out, blocked)
    total = int(out.sum())
    if total < n_dots:
        raise ValueError(f"only {total} dots placed of {n_dots} requested "
                         f"(blocks={n_blocks}, passB={placed_b})")
    return out


# --------------------------------------------------------------------------
# Registry uniqueness (118 hash-pinned scored rasters)
# --------------------------------------------------------------------------

def registry_uniqueness(tif: Path, footprint: np.ndarray,
                        catalogue: np.ndarray, eligible: np.ndarray) -> dict:
    from scipy.stats import spearmanr

    fetch = json.loads(SCORED_FETCH.read_text())
    with rasterio.open(tif) as s:
        mine = s.read(1)
    mine_dots = np.isfinite(mine) & (mine > 0) & footprint
    my_d = ndi.distance_transform_edt(~mine_dots)
    yy, xx = np.nonzero(footprint)
    rng = np.random.default_rng(SEED)
    sample = rng.choice(yy.size, size=min(600_000, yy.size), replace=False)
    sy, sx = yy[sample], xx[sample]
    rows = []
    n_checked = 0
    for rec in fetch["entries"]:
        if rec.get("status") not in {"downloaded", "cached"}:
            continue
        path = ROOT / rec["local"]
        if not path.exists():
            continue
        with rasterio.open(path) as ds:
            a = ds.read(1)
        other = np.isfinite(a) & (a > 0) & footprint
        n_other = int(other.sum())
        n_mine = int(mine_dots.sum())
        if n_other == 0 or n_mine == 0:
            continue
        n_checked += 1
        other_d = ndi.distance_transform_edt(~other)
        ov_mine_on_other = float((my_d[other] <= 3.0).sum()) / n_other
        ov_other_on_mine = float((other_d[mine_dots] <= 3.0).sum()) / n_mine
        rho = float(spearmanr(mine[sy, sx].astype(np.float64),
                              a[sy, sx].astype(np.float64)).statistic)
        # density-matched expectation: fraction of MY eligible pixels that fall
        # within 3 px of this raster's dots by pure coverage geometry (lift
        # ~1.0 = mechanical overlap from THEIR dot density, not duplication).
        near_dilated = other_d <= 3.0
        expected = float(near_dilated[eligible].sum()) / max(int(eligible.sum()), 1)
        obs = ov_other_on_mine
        rows.append({
            "repo": rec["repo"], "name": rec["name"],
            "owner_reported_score": rec["score"],
            "n_dots": n_other,
            "abs_spearman_surface": abs(rho),
            "overlap_3px_their_dots_on_mine": round(ov_mine_on_other, 4),
            "overlap_3px_my_dots_on_theirs": round(obs, 4),
            "density_matched_expected_my_dots": round(expected, 4),
            "overlap_lift": round(obs / expected, 3) if expected > 0 else None,
            "same_budget_class": n_other <= 45000,
            "dense_lattice_degenerate": n_other >= LATTICE_DOT_FLOOR,
        })
    sparse = [r for r in rows if not r["dense_lattice_degenerate"]]
    budget_class = [r for r in rows if r["same_budget_class"]]
    dense = [r for r in rows if r["dense_lattice_degenerate"]]
    max_rho_row = max(rows, key=lambda r: r["abs_spearman_surface"])
    # THE literal protocol gate, one direction only: MY dots within 3 px of
    # ONE registry raster's dots, over non-degenerate (non-lattice) rasters.
    max_lit = max(sparse, key=lambda r: r["overlap_3px_my_dots_on_theirs"])
    max_literal_overlap = max_lit["overlap_3px_my_dots_on_theirs"]
    max_lit_budget = max(budget_class, key=lambda r: r["overlap_3px_my_dots_on_theirs"])
    max_literal_budget = max_lit_budget["overlap_3px_my_dots_on_theirs"]
    # Conservative reverse check within the same budget class: their dots on
    # mine (family members exceed 0.86 in this direction; ours must not).
    max_rev_budget = max(budget_class, key=lambda r: r["overlap_3px_their_dots_on_mine"])
    max_reverse_budget = max_rev_budget["overlap_3px_their_dots_on_mine"]
    # Material-lift diagnostic: lift only matters where absolute overlap is
    # material (>=0.30); small-denominator lifts on trivial overlap are noise.
    lift_rows = [r for r in sparse
                 if r["overlap_lift"] is not None
                 and r["overlap_3px_my_dots_on_theirs"] >= 0.30]
    max_lift_row = (max(lift_rows, key=lambda r: r["overlap_lift"])
                    if lift_rows else None)
    return {
        "n_registry_rasters_checked": n_checked,
        "max_abs_spearman": max_rho_row["abs_spearman_surface"],
        "max_abs_spearman_vs": max_rho_row["name"],
        "passes_spearman_gate": bool(max_rho_row["abs_spearman_surface"] <= 0.90),
        "max_literal_mine_on_theirs": round(max_literal_overlap, 4),
        "max_literal_mine_on_theirs_vs": max_lit["name"],
        "passes_literal_nonlattice_gate": bool(max_literal_overlap <= 0.70),
        "max_literal_same_budget": round(max_literal_budget, 4),
        "max_literal_same_budget_vs": max_lit_budget["name"],
        "max_reverse_same_budget": round(max_reverse_budget, 4),
        "max_reverse_same_budget_vs": max_rev_budget["name"],
        "passes_same_budget_gate": bool(max_literal_budget <= 0.70
                                        and max_reverse_budget <= 0.70),
        "max_material_lift": (max_lift_row["overlap_lift"]
                              if max_lift_row else None),
        "max_material_lift_vs": (max_lift_row["name"] if max_lift_row else None),
        "max_material_lift_overlap": (max_lift_row["overlap_3px_my_dots_on_theirs"]
                                      if max_lift_row else None),
        "dense_lattice_rasters_excluded": [r["name"] for r in dense],
        "literal_gate_note": (
            "The literal '>70% of my dots within 3 px of ONE registry raster' "
            "rule is DEGENERATE against dense rasters: fields with 103k-517k "
            "dots (and the 206,895-dot r13 lattice) capture 0.68-0.99 of ANY "
            "37k-dot field by pigeonhole, so the gate is evaluated over "
            "non-degenerate rasters (n<100k) and separately over the "
            "same-budget class (n<=45k); dense-field results are still listed "
            "in rows_top10_by_overlap. This implements AGENTS.md defect (ii)."),
        "rows_top10_by_overlap": sorted(
            rows, key=lambda r: -r["overlap_3px_my_dots_on_theirs"])[:10],
    }


# --------------------------------------------------------------------------
# MODEL-ESTIMATE score projection (never an organizer score)
# --------------------------------------------------------------------------

def score_estimate(dots: np.ndarray, footprint: np.ndarray,
                   catalogue: np.ndarray, cat_density: np.ndarray) -> dict:
    model = json.loads(SCORE_MODEL.read_text())
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    n = int(dots.sum())
    y, x = np.nonzero(dots)
    dc = d_cat[y, x]
    r = 3
    dens = ndi.uniform_filter(dots.astype(np.float32), size=2 * r + 1)
    near = dens[dots]
    blocks = ndi.uniform_filter(dots.astype(np.float32), size=61)
    feats = [float(np.log(max(n, 1))), float((blocks > 0).sum() / footprint.sum()),
             float(np.log1p(np.quantile(dc, 0.9))),
             float(np.log1p(near.mean() * 100.0)),
             float((dc <= 3).mean()), float(cat_density[dots].mean())]
    mu = np.array(model["feature_mean"])
    sd = np.array(model["feature_sd"])
    beta = np.array(model["coefficients_standardised"])
    z = np.r_[1.0, (np.array(feats) - mu) / sd]
    pred = float(z @ beta)
    rmse = model["rmse_grouped"]
    # Family-parity reference: the 0.2778 champion's OWN model estimate, so the
    # projection is read within-model (the model under-predicts this family).
    b2_ref = None
    try:
        desc = {r["name"]: r for r in json.loads(
            (ROOT / "evidence/portfolio_descriptors.json").read_text())["rows"]}
        b2 = desc["h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"]
        b2_feats = [float(np.log(max(b2["n"], 1))),
                    float(b2["roi_coverage_frac"]),
                    float(np.log1p(b2["dist_p90_px"])),
                    float(np.log1p(b2["mean_neighbour_dots"] * 100.0)),
                    float(b2["frac_within_3px"]),
                    float(b2["mean_local_cat_density"])]
        b2_pred = float(np.r_[1.0, (np.array(b2_feats) - mu) / sd] @ beta)
        b2_ref = {"name": "h33-h33-2-b2 (owner-reported 0.2778)",
                  "model_estimate": round(b2_pred, 4),
                  "feature_values": dict(zip(model["terms"], b2_feats))}
    except (OSError, KeyError, ValueError) as exc:  # pragma: no cover
        b2_ref = {"error": str(exc)}
    return {
        "evidence_class": "MODEL-ESTIMATE",
        "model": "wbg6-score-model-v2 (family-grouped OLS on owner-reported scores)",
        "terms": model["terms"],
        "feature_values": dict(zip(model["terms"], feats)),
        "estimate": round(pred, 4),
        "family_parity_reference": b2_ref,
        "within_model_gap_vs_b2_geometry": (round(pred - b2_ref["model_estimate"], 4)
                                            if b2_ref and "model_estimate" in b2_ref
                                            else None),
        "interval_68_model": [round(pred - rmse, 4), round(pred + rmse, 4)],
        "interval_95_model": [round(pred - 1.96 * rmse, 4), round(pred + 1.96 * rmse, 4)],
        "model_grouped_rmse": rmse,
        "model_grouped_spearman": model["spearman_grouped"],
        "caveat": ("Projection from geometry-descriptor regression on USER-REPORTED "
                   "scores; grouped CV is weak (Spearman "
                   f"{model['spearman_grouped']:.2f}), and the model UNDER-predicts "
                   "the 0.24-0.28 champion family (B2's own model estimate is far "
                   "below its reported 0.2778). Read estimates within-model via the "
                   "family-parity reference. NOT a HOLDOUT-DTI and NOT "
                   "ORGANIZER-CONFIRMED."),
    }


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dots", type=int, default=N_DOTS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out-dir", type=Path, default=DOWNLOADS)
    args = ap.parse_args()

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(ROOT / "data/bridge/labels.tif") as src:
        cat = src.read(1) > 0
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
    if not (cat <= footprint).all():
        raise ValueError("catalogue outside footprint")

    print("[1/6] blind geophysical layers", flush=True)
    layers = build_blind_layers(ROOT / "data/official/training_features.tif", footprint)
    blind = np.mean(np.stack(list(layers.values())), axis=0)
    blind[~footprint] = 0.0
    print(f"  composite mean rank computed; layers={list(layers)}", flush=True)

    print("[2/6] leakage canary (blind layers alone)", flush=True)
    seg = holdout.SegmentHoldout(footprint, cat, buffer_px=15)
    canary_blind = seg.canary(layers, max_per_class=8000)

    print("[3/6] per-fold hide-and-recover holdout (visible-only priors)", flush=True)
    ref_rows, block_rows, fold_rows = [], [], []
    for fold in seg.folds:
        t0 = time.time()
        d_vis = ndi.distance_transform_edt(~fold["visible"]).astype(np.float32)
        prior = build_prior(fold["visible"], footprint, d_vis)
        surf = 0.70 * blind + 0.30 * rank01(prior, footprint)
        surf[~footprint] = 0.0
        eligible = fold["valid"] & ~fold["visible"] & (d_vis >= OFFCAT_MIN_PX)
        n_fold = max(int(args.dots * eligible.sum() / footprint.sum()), 200)
        dots_fold = select_dots(surf, eligible, n_fold, MIN_SEP_PX,
                                args.seed + fold["id"])
        ref, blocks = seg.score_fold(dots_fold, fold)
        ref_rows.append(ref)
        block_rows.append(blocks)
        fold_rows.append({"fold": fold["name"], "dots": int(dots_fold.sum()),
                          "dti": ref["dti"], "n_truth": ref["n_truth"]})
        print(f"  fold {fold['name']}: dots={dots_fold.sum()} dti={ref['dti']:.4f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    total = holdout.pooled_components(ref_rows)
    blocks_sum = np.sum(block_rows, axis=0)
    yy, xx = np.nonzero(footprint)
    nx = (footprint.shape[1] + 99) // 100
    active = np.unique((yy // 100) * nx + xx // 100)
    ci = holdout.spatial_bootstrap_ci(blocks_sum[active], draws=1999)

    # prior canary: per-fold visible-only prior AUCs (same protocol as seg.canary)
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(args.seed)
    prior_auc_folds = []
    for fold in seg.folds:
        d_vis = ndi.distance_transform_edt(~fold["visible"]).astype(np.float32)
        prior = build_prior(fold["visible"], footprint, d_vis)
        pos = np.flatnonzero(fold["truth"])
        neg = np.flatnonzero(fold["valid"] & ~fold["visible"]
                             & (ndi.distance_transform_edt(~fold["truth"]) >= 9))
        pos = rng.choice(pos, min(len(pos), 8000), replace=False)
        neg = rng.choice(neg, min(len(neg), 8000), replace=False)
        y_true = np.r_[np.ones(pos.size), np.zeros(neg.size)]
        x = np.r_[prior.ravel()[pos], prior.ravel()[neg]]
        auc = float(roc_auc_score(y_true, x))
        prior_auc_folds.append({"fold": fold["name"], "auc": auc})
    pooled_prior_auc = float(np.mean([r["auc"] for r in prior_auc_folds]))
    prior_suspicious = any(max(r["auc"], 1 - r["auc"]) > 0.90 for r in prior_auc_folds)

    print("[4/6] final global placement (full-catalogue priors, fresh seed)", flush=True)
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    prior_full = build_prior(cat, footprint, d_cat)
    surf = 0.70 * blind + 0.30 * rank01(prior_full, footprint)
    surf[~footprint] = 0.0
    eligible = footprint & ~cat & (d_cat >= OFFCAT_MIN_PX)
    dots = select_dots(surf, eligible, args.dots, MIN_SEP_PX, args.seed)
    values = dots.astype(np.float32)
    print(f"  placed {int(dots.sum())} dots", flush=True)

    stamp = hashlib.sha256(dots.tobytes()).hexdigest()[:8]
    name = (f"wbg8-mridge-pois300-offcat3-{int(dots.sum())}-"
            f"20261031-{stamp}-zeros")
    tif = args.out_dir / f"{name}.tif"

    print("[5/6] write + strict validation (portal-safe zeros exterior)", flush=True)
    submission.write_submission(values, ROOT / "data/bridge/sample_submission.tif",
                                tif, outside="zero")
    zp = submission.zip_single(tif)
    receipt = submission.check_variants(tif, ROOT / "data/bridge/sample_submission.tif")
    (args.out_dir / f"{name}.validator.json").write_text(
        json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    print("[6/6] registry uniqueness (118 scored rasters)", flush=True)
    uniqueness = registry_uniqueness(tif, footprint, cat, eligible)

    cat_density = ndi.uniform_filter(cat.astype(np.float32), size=21)
    estimate = score_estimate(dots, footprint, cat, cat_density)

    hard_ok = receipt["format_valid"] and all(
        c["pass"] for c in receipt["checks"].values() if c["hard_requirement"])
    canary_ok = canary_blind["passed"] and not prior_suspicious
    unique_ok = (uniqueness["passes_spearman_gate"]
                 and uniqueness["passes_literal_nonlattice_gate"]
                 and uniqueness["passes_same_budget_gate"])
    # Family band context: owner-reported focus-site bests
    family_band = [0.2449, 0.2477, 0.2600, 0.2632, 0.2649, 0.2707, 0.2708,
                   0.2710, 0.2750, 0.2778]
    decision = {
        "verdict": "promote" if (hard_ok and canary_ok and unique_ok) else "negative",
        "download_ok": bool(hard_ok),
        "portal_safe_zeros_exterior": True,
        "values_strictly_in_0_1": bool(receipt["checks"]["footprint_range_0_1"]["pass"]),
        "eligible_for_separate_selector": bool(hard_ok and canary_ok and unique_ok),
        "ok_to_submit": bool(hard_ok and canary_ok and unique_ok),
        "approved_for_weekly_slot": bool(hard_ok and canary_ok and unique_ok),
        "gates": {
            "format_hard": bool(hard_ok),
            "leakage_canary": bool(canary_ok),
            "registry_uniqueness_sparse_gate": bool(unique_ok),
        },
        "user_decision_required": (
            "Score for this file is a MODEL-ESTIMATE, never organizer-confirmed. "
            "Spending a weekly DrivenData slot is the owner's call; the file is "
            "pre-cleared for format, range, canary and uniqueness so a submit "
            "attempt cannot fail on the '[0,1]' portal error. approved_for_weekly_slot "
            "marks readiness for the selector step within the weekly cap shown on "
            "the submission page; this repository never uploads anything itself."),
    }

    card = {
        "schema": "wbg8-run-card-v1",
        "generated_utc": "2026-10-31T00:00:00+00:00",
        "lane": "WBG-8 blind multi-layer ridge + structural priors, champion-family geometry",
        "hypothesis": ("Multi-layer blind geophysical ridge energy blended with "
                       "visible-catalogue structural priors places off-catalogue "
                       "Poisson-300 m dots where unmapped faults continue, beating "
                       "the single-surface champion family geometry."),
        "mechanism": ("RTP/TC Hessian ridge energy + geodetic strain magnitude + "
                      "gravity-edge energy + basement-depth steps + detrended-topo "
                      "fronts, ranked, blended 0.70/0.30 with distance-ring/ tip-lobe/"
                      "relay-corridor priors; coverage-stratified two-pass greedy "
                      "kernel-disjoint selection (61 px block quota then global "
                      "propensity), d_cat >= 3 px, 37,654 dots, seed "
                      f"{args.seed}."),
        "non_fault_mimic": ("Lithologic contacts and intrusive contacts produce the "
                            "same magnetic/gravity ridge signatures; pediment scarps "
                            "mimic topo fronts; neither is a fault."),
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
            "dti": total["dti"],
            "ci95": ci["interval"],
            "withheld_positive_pixels": int(total["n_truth"]),
            "n_emitted_per_fold": [r["dots"] for r in fold_rows],
            "folds": fold_rows,
            "protocol": {"aggregation": "pooled TPw/FPw/FNw",
                         "buffer_m": seg.buffer_px * 100,
                         "visible_fault_mask": "pixel-exact before credit",
                         "alpha": 0.2, "beta": 0.8, "kernel_radius_m": 300,
                         "placement": "per-fold visible-only catalogue priors",
                         "blind_layers": "catalogue-free, fold-invariant"},
            "limitation": ("Catalogue-proxy hide-and-recover. Instrument defect (i): "
                           "this evaluator does NOT rank real submissions "
                           "(Spearman 0.144, p=0.12, n=118). It is an efficacy "
                           "diagnostic, never a leaderboard forecast."),
        },
        "leakage_canary": {
            "threshold": 0.90,
            "blind_layers": canary_blind,
            "prior_visible_only_folds": prior_auc_folds,
            "prior_mean_auc": pooled_prior_auc,
            "passed": bool(canary_ok),
        },
        "correlation_overlap_vs_registry": uniqueness,
        "registry": {
            "passes_literal_uniqueness": bool(unique_ok),
            "evaluation": ("non-degenerate rasters (n<100k) literal direction + "
                           "same-budget class (n<=45k) both directions + "
                           "|Spearman|<=0.90; dense-field forced overlap reported "
                           "separately per AGENTS.md defect ii"),
            "max_literal_mine_on_theirs_nonlattice": uniqueness["max_literal_mine_on_theirs"],
            "max_literal_same_budget": uniqueness["max_literal_same_budget"],
            "max_reverse_same_budget": uniqueness["max_reverse_same_budget"],
            "max_abs_spearman": uniqueness["max_abs_spearman"],
        },
        "score_estimate": estimate,
        "family_band_owner_reported": family_band,
        "validator": {
            "file": receipt["file"],
            "bytes": receipt["bytes"],
            "sha256": receipt["sha256"],
            "format_valid": receipt["format_valid"],
            "all_hard_checks_passed": bool(hard_ok),
            "no_nan_inside_footprint": receipt["checks"]["footprint_all_finite"]["pass"],
            "values_in_0_1": receipt["checks"]["footprint_range_0_1"]["pass"],
            "crs_shape_transform_match": bool(
                receipt["checks"]["crs_epsg_32611"]["pass"]
                and receipt["checks"]["shape_matches_template"]["pass"]
                and receipt["checks"]["geotransform_matches_template"]["pass"]),
            "n_positive": receipt["in_footprint_positive_pixels"],
            "range_min": 0.0, "range_max": 1.0,
            "exterior": "zeros (all-finite; fixes the portal [0,1] NaN error)",
        },
        "artifact": {
            "tif": str(tif.relative_to(ROOT)),
            "zip": str(zp.relative_to(ROOT)),
            "tif_sha256": sha256(tif),
            "zip_sha256": sha256(zp),
            "positive_set_sha256": hashlib.sha256(
                np.flatnonzero(dots.ravel()).tobytes()).hexdigest(),
        },
        "submission_name": name,
        "note": ("WBG-8 blind multilayer ridge priors offcat3 poisson300 "
                 f"{int(dots.sum())} dots seed {args.seed}; unique; portal-safe"),
        "verdict": "promote" if (hard_ok and canary_ok and unique_ok) else "negative",
        "decision": decision,
        "slots_used": 0,
        "leaderboard_claim": ("No organizer receipt exists for this file. Expected "
                              "score band is the MODEL-ESTIMATE above plus the "
                              "family context 0.24-0.28; beating 0.2778 is a "
                              "hypothesis, not a claim."),
    }
    card["note"] = card["note"][:140]
    (EVIDENCE / "run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    (EVIDENCE / "holdout.json").write_text(json.dumps(card["holdout"], indent=2, allow_nan=False) + "\n")
    (EVIDENCE / "uniqueness.json").write_text(json.dumps(uniqueness, indent=2, allow_nan=False) + "\n")
    (EVIDENCE / "score_estimate.json").write_text(json.dumps(estimate, indent=2, allow_nan=False) + "\n")

    print(json.dumps({
        "name": name, "sha256": card["artifact"]["tif_sha256"],
        "dots": int(dots.sum()), "format_valid": receipt["format_valid"],
        "holdout_dti": round(total["dti"], 5), "ci95": ci["interval"],
        "canary_passed": bool(canary_ok),
        "max_literal_overlap_nonlattice": uniqueness["max_literal_mine_on_theirs"],
        "max_literal_overlap_same_budget": uniqueness["max_literal_same_budget"],
        "max_abs_spearman": uniqueness["max_abs_spearman"],
        "score_estimate": estimate["estimate"],
        "estimate_95": estimate["interval_95_model"],
        "verdict": card["verdict"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
