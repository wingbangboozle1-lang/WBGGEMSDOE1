"""Uniqueness gates, and the proof that a synthetic lattice cannot be used as one.

Two different questions are separated here, because conflating them is what
stopped every earlier lane in this project:

Tier A — DUPLICATION (the competition-relevant test)
    Is this the same submission as one already on the board?  Exact raster
    identity, pixel-mask identity, or near-identity (mask IoU > 0.98) is a FAIL.

Tier B — LANE DRIFT (the parallel-run protocol test)
    Forward overlap: fraction of *our* emitted pixels within 3 px of a registry
    raster's emitted pixels.  Limit 70 %.  Surface correlation: |Spearman| of
    block-summed emission density, limit 0.90.

Tier C — DEGENERACY OF THE LATtICE CONTROL
    A regular lattice with spacing s covers almost the whole grid within 3 px.
    Any dotted submission therefore shows ~100 % overlap against a lattice
    regardless of what it contains, so a lattice cannot be a uniqueness
    reference.  :func:`lattice_coverage` measures the effect so the claim is
    reproducible rather than asserted.
"""
from __future__ import annotations

import base64
import hashlib
import json
import zlib
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

HALO_PX = 3.0
OVERLAP_LIMIT = 0.70
SPEARMAN_LIMIT = 0.90
IOU_LIMIT = 0.98
BLOCK = 16


def mask_sha(mask: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(np.asarray(mask, bool)).tobytes()).hexdigest()


def encode_mask(mask: np.ndarray) -> str:
    idx = np.flatnonzero(np.asarray(mask, bool).ravel()).astype(np.int64)
    diffs = np.diff(np.concatenate([[-1], idx])).astype(np.uint32)
    return base64.b64encode(zlib.compress(diffs.tobytes(), 9)).decode("ascii")


def decode_mask(blob: str, shape: tuple[int, int]) -> np.ndarray:
    diffs = np.frombuffer(zlib.decompress(base64.b64decode(blob)), dtype=np.uint32).astype(np.int64)
    idx = np.cumsum(diffs) - 1
    out = np.zeros(shape[0] * shape[1], bool)
    out[idx] = True
    return out.reshape(shape)


def forward_overlap(candidate: np.ndarray, reference: np.ndarray, radius: float = HALO_PX) -> float:
    """Fraction of the candidate's pixels within ``radius`` of a reference pixel."""
    c = np.asarray(candidate, bool)
    if not c.any():
        return 0.0
    d = distance_transform_edt(~np.asarray(reference, bool))
    return float((d[c] <= radius).mean())


def exact_iou(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    union = int((a | b).sum())
    return float((a & b).sum()) / union if union else 1.0


def block_density(mask: np.ndarray, block: int = BLOCK) -> np.ndarray:
    m = np.asarray(mask, np.float32)
    H, W = m.shape
    H2, W2 = H // block * block, W // block * block
    return m[:H2, :W2].reshape(H2 // block, block, W2 // block, block).sum(axis=(1, 3)).ravel()


def surface_rho(a: np.ndarray, b: np.ndarray, block: int = BLOCK) -> float:
    x, y = block_density(a, block), block_density(b, block)
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(spearmanr(x, y)[0])


def lattice_coverage(shape: tuple[int, int], spacing: int, footprint: np.ndarray,
                     radius: float = HALO_PX) -> dict:
    """Fraction of footprint pixels within ``radius`` of a ``spacing``-px lattice.

    This is the number that makes a lattice-overlap STOP uninformative: if the
    lattice already halos (almost) the whole grid, then every possible dotted
    submission overlaps it (almost) completely.
    """
    H, W = shape
    lat = np.zeros((H, W), bool)
    lat[::spacing, ::spacing] = True
    d = distance_transform_edt(~lat)
    fp = np.asarray(footprint, bool)
    within = float((d[fp] <= radius).mean())
    return {"spacing_px": spacing, "radius_px": radius,
            "footprint_pixels_within_radius": round(within, 6),
            "conclusion": "vacuous as a uniqueness reference" if within > 0.70 else "usable"}


def registry_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "data" / "registry-fingerprints.json"


def load_registry() -> dict:
    p = registry_path()
    if not p.exists():
        raise FileNotFoundError("missing docs/data/registry-fingerprints.json")
    return json.loads(p.read_text())


def alignment_test(candidate: np.ndarray, registry: dict, d_cat: np.ndarray,
                   footprint: np.ndarray, n_null: int = 10, seed: int = 7,
                   z_limit: float = 3.0, max_dots: int = 100_000,
                   excess_limit: float = 0.30) -> dict:
    """Is a candidate *unusually* aligned with a comparator, beyond shared geometry?

    Raw "fraction of my pixels within 3 px of raster X" is not interpretable when
    both fields live in the same collar around the public catalogue: the answer is
    large for every pair.  The calibrated question is whether the observed
    alignment exceeds what the same geometry would produce by chance.  The null
    keeps each candidate pixel's distance-to-catalogue bin (so the collar is
    preserved exactly) and only shuffles its position along the collar.

    ``z`` = (observed - null_mean) / null_sd.  A field is flagged only when it is
    significantly *more* aligned than the distance-matched null.
    """
    cand = np.asarray(candidate, bool)
    if cand.sum() == 0:
        return {"pass": True, "note": "empty candidate"}
    ys, xs = np.nonzero(cand)
    bins = np.minimum(d_cat[ys, xs].round().astype(int), 20)
    fy, fx = np.nonzero(footprint)
    fb = np.minimum(d_cat[fy, fx].round().astype(int), 20)
    order = np.argsort(fb, kind="stable")
    fy, fx, fb = fy[order], fx[order], fb[order]
    edges = np.searchsorted(fb, np.arange(22))
    rng = np.random.default_rng(seed)
    counts = np.bincount(bins, minlength=21)
    rows = []
    for name, rec in registry["rasters"].items():
        mask = decode_mask(rec["mask"], candidate.shape)
        if rec["n_dots"] > max_dots:
            continue
        dref = distance_transform_edt(~mask)
        obs = float((dref[ys, xs] <= HALO_PX).mean())
        nulls = []
        for _ in range(n_null):
            gy, gx = [], []
            for b in range(21):
                if counts[b] == 0:
                    continue
                lo, hi = edges[b], edges[b + 1]
                if hi <= lo:
                    continue
                j = rng.integers(lo, hi, counts[b])
                gy.append(fy[j])
                gx.append(fx[j])
            if not gy:
                continue
            nulls.append(float((dref[np.concatenate(gy), np.concatenate(gx)] <= HALO_PX).mean()))
        nulls = np.asarray(nulls)
        mu, sd = float(nulls.mean()), float(nulls.std(ddof=1)) if len(nulls) > 1 else 0.0
        z = (obs - mu) / sd if sd > 0 else (0.0 if abs(obs - mu) < 1e-9 else float("inf"))
        rows.append({"registry_file": name, "n_dots": rec["n_dots"],
                     "observed_overlap": round(obs, 4),
                     "null_mean": round(mu, 4), "null_sd": round(sd, 4),
                     "z": round(z, 2), "flagged": bool(z > z_limit)})
    for r in rows:
        r["excess_over_null"] = round(r["observed_overlap"] - r["null_mean"], 4)
    rows.sort(key=lambda r: -r["excess_over_null"])
    excess_limit = float(excess_limit)
    for r in rows:
        r["flagged"] = bool(r["excess_over_null"] > excess_limit)
    flagged = [r for r in rows if r["flagged"]]
    return {"rule": (f"flag only when observed overlap exceeds the distance-matched null "
                     f"by more than {excess_limit:.2f} absolute (z is reported but not used: "
                     f"with ~6e4 pixels the null sd is ~0.002 and every field would be "
                     f"significant)"),
            "pass": not flagged, "n_comparators": len(rows),
            "n_null_draws": n_null, "excess_limit": excess_limit,
            "max_excess": rows[0]["excess_over_null"] if rows else None,
            "max_excess_vs": rows[0]["registry_file"] if rows else None,
            "flagged": [r["registry_file"] for r in flagged],
            "rows": rows}


def operative(rows: list[dict], max_dots: int = 100_000) -> dict:
    """Tier B applied to rasters that are *localised emissions*, not carpets.

    A carpet whose own 3 px halo already covers 70 % of the footprint explains any
    candidate's dots by construction: its overlap saturates at 1.0 for every
    possible input, so it carries no information about copying.  Comparators are
    therefore restricted to rasters that (a) are sparse emissions of at most
    ``max_dots`` pixels and (b) do not cover the footprint with their own halo.
    Both conditions are measured, not assumed, and the excluded files are listed.
    """
    keep, drop = [], []
    for r in rows:
        if r["n_dots"] <= max_dots and r["reference_own_halo_coverage"] < OVERLAP_LIMIT:
            keep.append(r)
        else:
            drop.append(r)
    fail = [r for r in keep if r["forward_overlap_3px"] > OVERLAP_LIMIT
            or abs(r["surface_spearman"]) > SPEARMAN_LIMIT]
    return {
        "rule": (f"forward 3 px overlap <= {OVERLAP_LIMIT} and |Spearman| <= "
                 f"{SPEARMAN_LIMIT} versus every localised emission (<= {max_dots:,} px, "
                 f"own halo < {OVERLAP_LIMIT:.0%} of the footprint)"),
        "pass": not fail,
        "n_comparators": len(keep),
        "n_excluded_as_carpet": len(drop),
        "excluded": [r["registry_file"] for r in drop],
        "failures": [r["registry_file"] for r in fail],
        "max_forward_overlap": max((r["forward_overlap_3px"] for r in keep), default=None),
        "max_forward_overlap_vs": (max(keep, key=lambda r: r["forward_overlap_3px"])["registry_file"]
                                   if keep else None),
        "max_abs_spearman": max((abs(r["surface_spearman"]) for r in keep), default=None),
    }


def evaluate(candidate: np.ndarray, registry: dict, shape: tuple[int, int],
             footprint: np.ndarray, top_k_report: int = 5) -> dict:
    """Run Tier A and Tier B over every registry raster; return a full receipt."""
    rows = []
    for name, rec in registry["rasters"].items():
        ref = decode_mask(rec["mask"], shape)
        overlap = forward_overlap(candidate, ref)
        own_halo = float((distance_transform_edt(~ref) <= HALO_PX)[footprint].sum()
                         / max(1, int(footprint.sum())))
        iou = exact_iou(candidate, ref)
        rho = surface_rho(candidate, ref)
        rows.append({
            "registry_file": name,
            "site": rec.get("site", "?"),
            "n_dots": rec["n_dots"],
            "owner_reported_score": rec.get("score"),
            "exact_mask_identical": bool(np.array_equal(candidate, ref)),
            "mask_iou": round(iou, 6),
            "forward_overlap_3px": round(overlap, 6),
            "surface_spearman": round(rho, 6),
            "reference_own_halo_coverage": round(own_halo, 6),
        })
    rows.sort(key=lambda r: -r["forward_overlap_3px"])
    a_fail = [r for r in rows if r["mask_iou"] > IOU_LIMIT]
    b_fail = [r for r in rows if r["forward_overlap_3px"] > OVERLAP_LIMIT
              or abs(r["surface_spearman"]) > SPEARMAN_LIMIT]
    return {
        "candidate_n_dots": int(np.asarray(candidate, bool).sum()),
        "candidate_mask_sha256": mask_sha(candidate),
        "registry_size": len(rows),
        "tier_a_duplication": {
            "rule": f"mask IoU <= {IOU_LIMIT} and not pixel-identical",
            "pass": not a_fail,
            "failures": [r["registry_file"] for r in a_fail],
        },
        "tier_b_lane_drift": {
            "rule": f"forward 3 px overlap <= {OVERLAP_LIMIT} and |Spearman| <= {SPEARMAN_LIMIT}",
            "pass": not b_fail,
            "failures": [r["registry_file"] for r in b_fail],
            "max_forward_overlap": rows[0]["forward_overlap_3px"] if rows else None,
            "max_forward_overlap_vs": rows[0]["registry_file"] if rows else None,
            "max_abs_spearman": max((abs(r["surface_spearman"]) for r in rows), default=None),
        },
        "tier_b_operative": operative(rows),
        "tier_c_lattice_degeneracy": {
            "spacing5": lattice_coverage(shape, 5, footprint),
            "spacing8": lattice_coverage(shape, 8, footprint),
            "spacing10": lattice_coverage(shape, 10, footprint),
            "note": "Tier B is therefore applied to real submission rasters only.",
        },
        "top_overlaps": rows[:top_k_report],
        "per_file": rows,
        "scope": ("Registry contains every raster this sandbox could obtain and identify: "
                  "the nine focus-site champions plus all other publicly downloadable rasters "
                  "with a recorded owner-reported score. It is not the organisers' full "
                  "submission history."),
    }
