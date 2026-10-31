#!/usr/bin/env python3
"""Build the 31 Oct 2026 research candidate: catalogue-distal magnetic horizontal-gradient ridges.

Physical signature
  Blakely & Simpson (1986) horizontal-gradient maxima of the reduced-to-pole magnetic
  anomaly ('rtp' band of the 19-band training stack). A pixel is a ridge when its horizontal
  gradient magnitude exceeds both neighbours along at least one of four directions.
  Magnetic-contact ridges mark lateral changes in magnetisation, often where faults offset
  rock units.

Why catalogue-distal
  Only ridges more than 4 px (400 m) from the mapped USGS/INGENIOUS catalogue are eligible,
  so the file targets lineaments the mapped catalogue does not already contain.

Emission
  Top-N eligible ridges by gradient magnitude, greedy spacing >= 3 px (no two dots closer than
  3 px). Binary dots, float32 values {0,1} inside the footprint, zeros outside (shared policy:
  all-finite zeros export, see vendor/gems57/grid.py).

Honesty notes (written into the run card)
  * The full catalogue is used for eligibility, so a direct holdout reading of this file is
    NOT valid (per-fold regeneration not implemented here). HOLDOUT-DTI is recorded as NOT
    MEASURED.
  * A leakage canary tests each feature alone on the holdout (see run card).
  * Nothing here is an organizer score; the file is not cleared for submission.

Usage: .venv/bin/python scripts/build_candidate_20261031.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_erosion, distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import build_holdout  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402

NAME = "wbggemsdoe1-rtp-hgm-distal-37k-20261031"
NOTE = "Research only, NOT cleared: RTP gradient ridges >=400 m from mapped faults, 37k dots, 3px spacing."
N_DOTS = 37_000
CATALOGUE_CLEARANCE_PX = 4.0
SPACING_PX = 3.0
EDGE_MARGIN_PX = 2
OUT_DIR = ROOT / "docs/downloads"
EVID = ROOT / "evidence/session_20261031"


def load_rtp(grid) -> np.ndarray:
    with rasterio.open(ROOT / "data/official/training_features.tif") as src:
        names = [str(d).split(" - ")[0].strip() for d in src.descriptions]
        idx = names.index("rtp") + 1
        band = src.read(idx, masked=True).filled(np.nan).astype(np.float64)
    band[~np.isfinite(band) | (np.abs(band) > 1e30)] = np.nan
    return band


def horizontal_gradient_magnitude(rtp: np.ndarray, valid: np.ndarray, cell_m: float = 100.0) -> np.ndarray:
    z = np.where(valid, rtp, 0.0)
    gy, gx = np.gradient(z, cell_m)
    hgm = np.sqrt(gx * gx + gy * gy)
    hgm[~valid] = 0.0
    return hgm


def blakely_simpson_maxima(h: np.ndarray) -> np.ndarray:
    """Maximum in at least one of four directions versus its two neighbours (Blakely & Simpson 1986)."""
    pad = np.pad(h, 1, mode="constant", constant_values=0.0)
    c = pad[1:-1, 1:-1]
    pairs = [((0, -1), (0, 1)), ((-1, 0), (1, 0)), ((-1, 1), (1, -1)), ((-1, -1), (1, 1))]
    is_max = np.zeros(h.shape, bool)
    for (dy1, dx1), (dy2, dx2) in pairs:
        n1 = pad[1 + dy1:pad.shape[0] - 1 + dy1, 1 + dx1:pad.shape[1] - 1 + dx1]
        n2 = pad[1 + dy2:pad.shape[0] - 1 + dy2, 1 + dx2:pad.shape[1] - 1 + dx2]
        is_max |= (c > n1) & (c > n2)
    return is_max


def greedy_spacing(order_y: np.ndarray, order_x: np.ndarray, shape: tuple[int, int],
                   n_target: int, spacing: float) -> tuple[np.ndarray, int]:
    """Take candidates in the given (descending score) order, rejecting any within `spacing` px."""
    r = int(math.ceil(spacing))
    offsets = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
               if 0 < dy * dy + dx * dx < spacing * spacing]
    blocked = np.zeros(shape, bool)
    selected = np.zeros(shape, bool)
    count = 0
    h, w = shape
    for y, x in zip(order_y.tolist(), order_x.tolist()):
        if blocked[y, x]:
            continue
        selected[y, x] = True
        blocked[y, x] = True
        for dy, dx in offsets:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True
        count += 1
        if count >= n_target:
            break
    return selected, count


def canary_auc(ctx, rtp_hgm_full: np.ndarray, catalogue: np.ndarray) -> dict:
    """Each feature alone, scored on the shared holdout truth (AUC; >0.90 = leakage until proven otherwise)."""
    s_hgm, y_all, s_dist = [], [], []
    rng = np.random.default_rng(31)
    for cell in ctx.cells:
        sl = cell.bbox
        active = cell.active
        truth = np.zeros(active.shape, bool)
        truth[cell.truth_yx] = True
        hgm = rtp_hgm_full[sl]
        cat_crop = catalogue[sl]
        visible_cat = cat_crop & ~truth          # catalogue the method was allowed to see
        dist = distance_transform_edt(~visible_cat)
        idx = np.flatnonzero(active)
        keep = rng.choice(idx, size=min(idx.size, 60000), replace=False)
        yy, xx = np.unravel_index(keep, active.shape)
        s_hgm.append(hgm[yy, xx])
        s_dist.append(-dist[yy, xx])          # closer to visible catalogue => higher score
        y_all.append(truth[yy, xx].astype(int))
    y = np.concatenate(y_all)
    out = dict(n_pixels=int(y.size), n_positive=int(y.sum()), evaluator="gems57.holdout build_holdout (seeds 20,21; mode all)")
    if y.sum() == 0 or y.sum() == y.size:
        return out | dict(error="degenerate labels")
    out["auc_hgm_alone"] = float(roc_auc_score(y, np.concatenate(s_hgm)))
    out["auc_neg_distance_to_visible_catalogue_alone"] = float(roc_auc_score(y, np.concatenate(s_dist)))
    out["leakage_rule"] = "AUC > 0.90 = leakage until proven otherwise"
    out["passes_0_90_rule"] = bool(max(out["auc_hgm_alone"], out["auc_neg_distance_to_visible_catalogue_alone"]) <= 0.90)
    return out


def main() -> int:
    grid = load_grid(ROOT / "data/bridge")
    rtp = load_rtp(grid)
    valid = grid.footprint & np.isfinite(rtp)
    # Keep 2 px away from the footprint edge and from NaN cells so gradients are not edge artefacts.
    interior = binary_erosion(valid, iterations=EDGE_MARGIN_PX, border_value=0)
    hgm = horizontal_gradient_magnitude(rtp, valid)
    maxima = blakely_simpson_maxima(hgm)
    dist_cat = distance_transform_edt(~grid.catalogue)
    eligible = interior & maxima & (dist_cat > CATALOGUE_CLEARANCE_PX)
    ys, xs = np.nonzero(eligible)
    scores = hgm[ys, xs]
    order = np.argsort(-scores, kind="stable")
    selected, n_sel = greedy_spacing(ys[order], xs[order], grid.shape, N_DOTS, SPACING_PX)
    pred = np.where(selected & grid.footprint, 1.0, 0.0).astype(np.float32)

    assert not np.any((pred > 0) & grid.catalogue), "dot on mapped catalogue"
    assert not np.any((pred > 0) & ~grid.footprint), "dot outside footprint"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EVID.mkdir(parents=True, exist_ok=True)
    tif = OUT_DIR / f"{NAME}-zeros.tif"
    receipt = write_submission(
        tif, pred, ROOT / "data/bridge/sample_submission.tif", grid.footprint,
        note=NOTE, name=NAME, catalogue=grid.catalogue,
        metadata=dict(method="RTP Blakely-Simpson horizontal-gradient maxima, catalogue-distal",
                      source="data/official/training_features.tif band 'rtp' (owner mirror, hash-verified)"),
    )

    # The shared writer creates files with mkstemp mode 0600; make the deliverable downloadable.
    # (Done here, not by editing the pinned shared writer.)
    tif.chmod(0o644)

    # Distance profile of the emitted dots to the mapped catalogue (for the review table).
    d_out = dist_cat[selected & grid.footprint]
    profile = dict(min_px=float(d_out.min()), median_px=float(np.median(d_out)),
                   share_within_300m=float((d_out <= 3.0).mean()), share_over_400m=float((d_out > 4.0).mean()))

    # Canary: each feature alone on the shared holdout (per-fold visible catalogue).
    ctx = build_holdout(grid, seeds=(20, 21), modes=("all",))
    canary = canary_auc(ctx, hgm, grid.catalogue)

    tif_sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    card = dict(
        schema="gemsdoe1-run-card-v1",
        date="2026-10-31",
        candidate=NAME,
        hypothesis=("Magnetic horizontal-gradient ridges of the RTP anomaly that lie at least 400 m from every "
                    "mapped fault mark unmapped, fault-controlled magnetic contacts."),
        mechanism=("Lateral magnetisation contrasts along faults produce gradient maxima; excluding catalogue-adjacent "
                   "ridges targets faults that the catalogue does not contain."),
        named_nonfault_mimic=("Lithologic magnetic contacts (intrusive or sedimentary boundaries) and flight-line or "
                              "levelling artefacts both produce RTP gradient ridges that are not faults."),
        holdout_dti="NOT MEASURED - eligibility uses the full catalogue, so a direct holdout reading is invalid; "
                    "per-fold regeneration not implemented in this session.",
        leakage_canary=canary,
        catalogue_distance_profile_px=profile,
        registry_overlap="see evidence/session_20261031/candidate_overlap.json",
        raster_sha256=tif_sha,
        n_dots=int((pred > 0).sum()),
        selection=dict(eligible_maxima=int(eligible.sum()), dots_requested=N_DOTS, dots_selected=int(n_sel),
                       clearance_px=CATALOGUE_CLEARANCE_PX, spacing_px=SPACING_PX, edge_margin_px=EDGE_MARGIN_PX),
        validator=dict(sha256=receipt["sha256"], bytes=receipt["bytes"], validator=receipt["validator"]),
        submission_name=NAME,
        submission_note=NOTE,
        note_chars=len(NOTE),
        verdict=("NEGATIVE-FOR-SUBMISSION (research download only): unvalidated, no holdout reading, "
                 "literal overlap gate fails (see overlap file)."),
        organizer_confirmed="NONE",
        sources=dict(
            competition="https://www.drivendata.org/competitions/306/competition-doe-gems/",
            problem="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
            rules="https://docs.nlr.gov/docs/fy26osti/96647.pdf",
            leaderboard="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
            method="Blakely, R.J. & Simpson, R.W. (1986) Approximating edges of source bodies from magnetic or gravity anomalies, Geophysics 51(7):1494-1498; https://www.sciencedirect.com/science/article/abs/pii/S0926985117307176",
            data_mirror="https://github.com/buffedlizard55-lab/GEMSDOE (commit c0c06ac82178f26b94fce3397036ef8f12a2f3a0, data/bridge)",
        ),
    )
    (EVID / "candidate_run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(tif=str(tif.relative_to(ROOT)), sha256=tif_sha, n_dots=card["n_dots"],
                          profile=profile, canary=canary), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
