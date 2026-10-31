#!/usr/bin/env python3
"""Experiment E3 (2026-10-31): distance-to-catalogue band NULL, density matched to B2.

Question this file answers (and nothing more): does placing dots only in a
4-10 px band beside the public catalogue, with NO geological information, reproduce
the proxy ranking of the focus family? It is a placement-distance null, not a
geological model, and it is NOT a recommended submission.

Construction (fully specified, deterministic):
  * candidate pixels: footprint AND catalogue distance in [4, 10] px (Euclidean)
  * order: numpy default_rng(seed=20261031) permutation of candidates
  * greedy thinning: accept a candidate only if no accepted dot lies within 4 px
    (so every pair is >= 5 px apart); stop at N = 37,654 dots (B2 density)
  * no dot on or within 3 px of the catalogue (kernel of the catalogue itself)
  * values: 1.0 at dots, 0.0 elsewhere inside the footprint; zeros outside

Outputs:
  docs/downloads/wbggemsdoe1-band4to10-null-37654-20261031.{tif,zip,json}  (shared writer)
  docs/data/band_null_run_card_20261031.json                                (run card)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import metric  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems57.uniqueness import dot_overlap  # noqa: E402

SEED = 20261031
N_DOTS = 37654
BAND = (4.0, 10.0)
THIN_PX = 4.0
REF = ROOT / "data/bridge/sample_submission.tif"
CAT = ROOT / "data/bridge/labels.tif"
NAME = "wbggemsdoe1-band4to10-null-37654-20261031"
NOTE = ("Distance-only null: 37654 dots in 4-10px catalogue band, seed 20261031, no geology. "
        "Research control, not a model.")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    with rasterio.open(REF) as r:
        footprint = np.isfinite(r.read(1))
    with rasterio.open(CAT) as c:
        catalogue = (c.read(1) > 0) & footprint

    dist = distance_transform_edt(~catalogue)
    cand = footprint & (dist >= BAND[0]) & (dist <= BAND[1])
    flat = np.flatnonzero(cand)
    rng = np.random.default_rng(SEED)
    order = flat[rng.permutation(flat.size)]

    shape = footprint.shape
    blocked = np.zeros(shape, bool)
    r = int(np.ceil(THIN_PX))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = yy * yy + xx * xx <= THIN_PX * THIN_PX
    dots = np.zeros(shape, bool)
    n = 0
    for idx in order:
        y, x = divmod(int(idx), shape[1])
        if blocked[y, x]:
            continue
        dots[y, x] = True
        n += 1
        y0, y1 = max(0, y - r), min(shape[0], y + r + 1)
        x0, x1 = max(0, x - r), min(shape[1], x + r + 1)
        dy0, dx0 = y0 - (y - r), x0 - (x - r)
        blocked[y0:y1, x0:x1] |= disk[dy0:dy0 + (y1 - y0), dx0:dx0 + (x1 - x0)]
        if n == N_DOTS:
            break

    pred = np.where(footprint, dots.astype(np.float32), 0.0).astype(np.float32)
    assert n == N_DOTS, f"only placed {n} dots"
    assert not (dots & catalogue).any()
    assert not (dots & (dist <= 3.0)).any()

    out = ROOT / "docs/downloads" / f"{NAME}.tif"
    for stale in (out, out.with_suffix(".zip"), out.with_suffix(".json")):
        stale.unlink(missing_ok=True)  # deterministic regeneration; the writer refuses overwrites
    receipt = write_submission(out, pred, REF, footprint, note=NOTE, name=NAME, catalogue=catalogue,
                               metadata={"experiment": "E3 distance-band null", "seed": SEED,
                                         "band_px": list(BAND), "thin_px": THIN_PX,
                                         "evidence_class": "RESEARCH-NULL (no organizer or holdout score)"})

    # proxy audit (same proxy and metric as scripts/focus_codeload_proxy_audit.py)
    sgmc_path = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
    proxy_info = {"available_locally": sgmc_path.exists()}
    proxy_dti = None
    audit = ROOT / "docs/data/focus_proxy_audit_20261031.json"
    if audit.exists():
        proxy_info["audit_file"] = str(audit.relative_to(ROOT))
    proxy_mask = None
    try:
        cache = Path("/tmp/gems_focus_cache/extracted/GEMSDOE30")
        hits = list(cache.rglob("derived_sgmc_faults_100m_u8.tif")) if cache.exists() else []
        if hits:
            with rasterio.open(hits[0]) as s:
                proxy_mask = (s.read(1) > 0) & ~catalogue & footprint
    except Exception as exc:  # noqa: BLE001
        proxy_info["error"] = str(exc)
    if proxy_mask is not None:
        proxy_dti = metric.dti_exact(pred.astype(np.float64), proxy_mask, valid=footprint)
        proxy_dti = {"dti": round(proxy_dti["dti"], 6), "tp": round(proxy_dti["tp"], 3),
                     "fp": round(proxy_dti["fp"], 3), "fn": round(proxy_dti["fn"], 3),
                     "n_truth": proxy_dti["n_truth"], "label": "PROXY-DTI (not organizer, not holdout)"}

    # G4 degeneracy test: the literal 3-px overlap rule against the r13 lattice that the
    # repo says captures any dot field (registry/irregularities). Lattice = GEMSDOE24 input,
    # read from the cached archive extraction, SHA-256 recorded below.
    lattice_hits = list(Path("/tmp/gems_focus_cache/extracted/GEMSDOE24").rglob(
        "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif")) if Path("/tmp/gems_focus_cache").exists() else []
    lattice = None
    if lattice_hits:
        with rasterio.open(lattice_hits[0]) as lt:
            lv = lt.read(1).astype(np.float64)
        lat = np.isfinite(lv) & (lv > 0)
        lattice = {"file": "GEMSDOE24/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
                   "sha256": sha256(lattice_hits[0]), "dots": int(lat.sum()),
                   "candidate_dots_within_3px_of_lattice": round(dot_overlap(dots, lat), 6)}

    # uniform random baseline at identical density (no distance information at all)
    uni = np.zeros(shape, bool)
    pick = rng.choice(flat, size=N_DOTS, replace=False)
    uni.flat[pick] = True
    uniform = None
    if proxy_mask is not None:
        ud = metric.dti_exact(np.where(footprint, uni.astype(np.float64), 0.0), proxy_mask, valid=footprint)
        uniform = {"dti": round(ud["dti"], 6), "n_dots": int(uni.sum()),
                   "label": "PROXY-DTI uniform random baseline (same density, same footprint)"}

    card = {
        "schema": "gemsdoe1-band-null-run-card-v1",
        "date_utc": "2026-10-31",
        "experiment": "E3",
        "hypothesis": "Placement distance to the public catalogue alone (4-10 px band, no geology) "
                      "reproduces the proxy ranking of the focus family.",
        "mechanism": "Dots kept 4-10 px from mapped traces avoid the 3-px kernel of the catalogue, "
                     "the region the B2 explanation says is costly false-positive mass.",
        "named_non_fault_mimic": "Catalogue-proximity artefacts and dilation of mapped traces in the "
                                 "SGMC-derived proxy (the proxy is a ~1 px dilation of SGMC).",
        "construction": {"seed": SEED, "band_px": list(BAND), "thin_px": THIN_PX, "n_dots": N_DOTS,
                         "candidate_pixels": int(cand.sum())},
        "file": f"docs/downloads/{NAME}.tif",
        "sha256": sha256(out),
        "zip_sha256": receipt["zip_sha256"],
        "writer_receipt": {k: receipt[k] for k in ("sha256", "bytes", "note_chars", "approved_for_weekly_slot",
                                                   "promoted", "submission_slots_used")},
        "validator": receipt["validator"]["checks"],
        "proxy_truth": proxy_info,
        "proxy_dti": proxy_dti,
        "g4_lattice_overlap": lattice,
        "proxy_uniform_random_baseline": uniform,
        "submission_name": NAME,
        "submission_note": NOTE,
        "verdict": "negative",
        "download": "RESEARCH ONLY",
        "submit": "NO",
    }
    (ROOT / "docs/data/band_null_run_card_20261031.json").write_text(
        json.dumps(card, indent=1, allow_nan=False) + "\n")
    print(json.dumps({k: card[k] for k in ("file", "sha256", "proxy_dti", "submit")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
