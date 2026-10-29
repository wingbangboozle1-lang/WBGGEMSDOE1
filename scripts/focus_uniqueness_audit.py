#!/usr/bin/env python3
"""Pool audit: format facts, decoded duplicates, and all-pairs uniqueness for the focus-site rasters.

Pool = every sha256-verified raster from ``scripts/fetch_focus_rasters.py`` (the nine focus sites
GEMSDOE24/25/27/28/30/31/32/33/36 plus the 118 owner-reported scored rasters) and the
WBGGEMSDOE1 rasters already committed under ``docs/downloads/``.

Gates reuse the repo's own definitions (no private fork):
  * ``gems1.uniqueness.overlap_within`` / ``spearman_surface`` (3 px inclusive radius,
    Spearman on a fixed 250k-pixel footprint sample, seed 32);
  * ``gems.novelty.is_duplicate`` (|rho| > 0.90 or overlap > 0.70);
  * space-filling rasters (>= 70% of footprint positive) are reported but excluded from the
    overlap gate, as in ``gems1.uniqueness.audit``.

Outputs:
  * ``.cache/focus_pool.npz``  - positive indices + rank sample per raster (git-ignored, rebuildable)
  * ``evidence/focus_uniqueness/pool_audit.json`` - committed summary (no large arrays)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


FETCH = ROOT / "registry/focus_raster_fetch.json"
OWN_DOWNLOADS = sorted((ROOT / "docs/downloads").glob("*.tif"))
FOOTPRINT_REF = ROOT / "data/bridge/sample_submission.tif"
EXPECTED_FOOTPRINT_PX = 5167373  # gems.submission.EXPECTED (official sample finite mask)
CACHE = ROOT / ".cache/focus_pool.npz"
OUT = ROOT / "evidence/focus_uniqueness/pool_audit.json"
RADIUS = 3.0
SAMPLE_N = 250_000
TARGETS = {
    "GEMSDOE24": "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
    "GEMSDOE25": "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
    "GEMSDOE27": "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif",
    "GEMSDOE28": "gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif",
    "GEMSDOE30": "gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
    "GEMSDOE31": "gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif",
    "GEMSDOE32": "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
    "GEMSDOE33": "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
    "GEMSDOE36": "gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
}


def sha256_bytes(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pool_entries() -> list[dict]:
    """Unique-by-sha256 pool: focus/scored fetch manifest plus own committed downloads."""
    seen: dict[str, dict] = {}
    for e in json.loads(FETCH.read_text())["entries"]:
        if e.get("status") not in ("cached", "downloaded"):
            continue
        p = ROOT / e["local"]
        sha = sha256_bytes(p)
        if sha != e["sha256"]:
            raise RuntimeError(f"pool sha mismatch {p}")
        seen.setdefault(sha, {"name": p.name, "repo": e["repo"], "path": e["path"],
                              "source": e["source"], "sha256": sha, "file": str(p.relative_to(ROOT))})
    for p in OWN_DOWNLOADS:
        sha = sha256_bytes(p)
        seen.setdefault(sha, {"name": p.name, "repo": "WBGGEMSDOE1", "path": str(p.relative_to(ROOT)),
                              "source": "own_docs_downloads", "sha256": sha,
                              "file": str(p.relative_to(ROOT))})
    return sorted(seen.values(), key=lambda d: (d["repo"], d["name"]))


def coverage_mode() -> int:
    """Add footprint 3-px coverage per pool file (repo definition: gems.novelty.classify_space_filling_control)."""
    with rasterio.open(FOOTPRINT_REF) as f:
        footprint = np.isfinite(f.read(1))
    prev = json.loads(OUT.read_text())
    n_fp = int(footprint.sum())
    for rec in prev["files"]:
        with rasterio.open(ROOT / next(p["file"] for p in pool_entries() if p["sha256"] == rec["sha256"])) as ds:
            arr = ds.read(1)
        ref = np.isfinite(arr) & (arr > 0) & footprint
        if not ref.any():
            rec["coverage3px"] = 0.0
            continue
        d = distance_transform_edt(~ref)
        rec["coverage3px"] = float(((d <= RADIUS) & footprint).sum() / n_fp)
        rec["is_space_filling_control"] = bool(rec["coverage3px"] >= 0.70)
    prev["coverage_note"] = ("coverage3px = fraction of the footprint within 3 px of the file's own positive cells; "
                             ">= 0.70 marks a blind space-filling control whose literal dot-overlap is degenerate.")
    OUT.write_text(json.dumps(prev, indent=1, allow_nan=False) + "\n")
    print("coverage written for", len(prev["files"]), file=sys.stderr)
    return 0


def main() -> int:
    if "--coverage" in sys.argv:
        return coverage_mode()
    if "--reuse" in sys.argv:
        return reuse_matrices()
    with rasterio.open(FOOTPRINT_REF) as f:
        footprint = np.isfinite(f.read(1))
    if int(footprint.sum()) != EXPECTED_FOOTPRINT_PX:
        raise RuntimeError("footprint does not match the official sample finite mask")
    fp_flat = np.flatnonzero(footprint.ravel())
    rng = np.random.default_rng(32)
    sample_idx = np.sort(rng.choice(fp_flat.size, size=SAMPLE_N, replace=False))
    sample_cells = fp_flat[sample_idx]

    pool = pool_entries()
    n = len(pool)
    pos_idx: list[np.ndarray] = []
    ranks = np.zeros((n, SAMPLE_N), dtype=np.float32)
    facts = []
    for i, rec in enumerate(pool):
        with rasterio.open(ROOT / rec["file"]) as ds:
            arr = ds.read(1)
            crs_epsg = ds.crs.to_epsg() if ds.crs else None
            shape = ds.shape
            tr = tuple(round(float(x), 6) for x in ds.transform)[:6]
            dtype = ds.dtypes[0]
            count = ds.count
            nodata = ds.nodata
        fin = np.isfinite(arr)
        fp_vals = arr[footprint]
        out_vals = arr[~footprint]
        in_fin = np.isfinite(fp_vals)
        pos = np.flatnonzero((arr > 0) & footprint & fin).astype(np.int64)
        pos_idx.append(pos.astype(np.int32))
        v = np.where(footprint, arr, 0.0).ravel()[sample_cells].astype(np.float64)
        ranks[i] = rankdata(v).astype(np.float32)
        facts.append({
            "name": rec["name"], "repo": rec["repo"], "sha256": rec["sha256"],
            "count": count, "dtype": dtype, "shape": list(shape), "crs_epsg": crs_epsg,
            "transform_matches_official": bool(tr == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)),
            "nodata": None if nodata is None else (None if np.isnan(nodata) else float(nodata)),
            "nodata_is_nan": bool(nodata is not None and np.isnan(nodata)),
            "nan_inside_footprint": int((~in_fin).sum()),
            "outside_nonzero_or_nan": int(((out_vals != 0) | ~np.isfinite(out_vals)).sum()),
            "outside_is_nan": bool(np.isnan(out_vals).all()),
            "all_finite_in_0_1": bool(np.isfinite(arr).all() and (arr >= 0).all() and (arr <= 1).all()),
            "footprint_in_0_1": bool(in_fin.all() and (fp_vals[in_fin] >= 0).all() and (fp_vals[in_fin] <= 1).all()),
            "positive_in_footprint": int(pos.size),
            "positive_fraction_footprint": float(pos.size / footprint.sum()),
            "space_filling": bool(pos.size >= 0.70 * footprint.sum()),
            "decoded_positive_sha256": hashlib.sha256(pos.astype("<i8").tobytes()).hexdigest(),
            "min": float(np.nanmin(fp_vals)) if in_fin.any() else None,
            "max": float(np.nanmax(fp_vals)) if in_fin.any() else None,
            "source": rec["source"], "score": None,
        })
        if (i + 1) % 50 == 0:
            print(f"[{i+1}/{n}] read", file=sys.stderr)

    # Owner-reported scores, attached by filename match against the scored registry.
    scored = json.loads((ROOT / "registry/wbg_h1/scored_registry.json").read_text())["entries"]
    by_path = {(e["repo"], e["path"]): e for e in scored}
    for f_ in facts:
        for (repo, path), e in by_path.items():
            if repo == f_["repo"] and Path(path).name == f_["name"]:
                f_["score"] = e.get("score")
                f_["score_label"] = "OWNER-REPORTED"
                break

    # all-pairs directional overlap: row = candidate i (its dots), column = reference j (its 3 px zone)
    overlap = np.full((n, n), np.nan, dtype=np.float32)
    shape = footprint.shape
    for j in range(n):
        ref = np.zeros(shape, dtype=bool)
        pj = pos_idx[j]
        if pj.size:
            ref.ravel()[pj] = True
        d = distance_transform_edt(~ref).ravel() if pj.size else None
        if d is None:
            continue
        for i in range(n):
            pi = pos_idx[i]
            if pi.size == 0:
                continue
            overlap[i, j] = float((d[pi] <= RADIUS).mean())
        if (j + 1) % 50 == 0:
            print(f"[{j+1}/{n}] overlap columns", file=sys.stderr)

    # Spearman on the fixed sample for every pair
    z = ranks - ranks.mean(axis=1, keepdims=True)
    z /= np.linalg.norm(z, axis=1, keepdims=True) + 1e-12
    rho = (z @ z.T).astype(np.float32)

    return write_summary(facts, overlap, rho, n)


def reuse_matrices() -> int:
    """Recompute the summary from the saved matrices (no TIFF re-read, ~seconds)."""
    prev = json.loads(OUT.read_text())
    facts = prev["files"]
    m = np.load(CACHE)
    overlap, rho = m["overlap"], m["rho"]
    return write_summary(facts, overlap, rho, len(facts))


def attach_user_scores(facts: list[dict]) -> list[dict]:
    """Attach USER-REPORTED scores. Matching is by key substring of the registry filename within the same
    repo (the user-report keys are filename tokens), then recorded on the matched file's sha256.
    One key can hit several files (ambiguous; see irregularity IR-042). Conflicts are recorded, not resolved.
    Never ORGANIZER-CONFIRMED."""
    fetch = json.loads(FETCH.read_text())["entries"]
    user = json.loads((ROOT / "registry/focus_user_reported_scores.json").read_text())["entries"]
    by_sha = {f_["sha256"]: f_ for f_ in facts}
    conflicts = []
    unmatched = []
    for u in user:
        hits = [e for e in fetch if e["repo"] == u["site"] and u["key"].lower() in Path(e["path"]).name.lower()]
        if not hits:
            unmatched.append({"site": u["site"], "key": u["key"], "score": u["score"]})
            continue
        for h in hits:
            f_ = by_sha.get(h["sha256"])
            if f_ is None:
                continue
            prev = f_.get("user_score")
            if prev is not None and abs(prev - u["score"]) > 1e-9:
                conflicts.append({"sha256": h["sha256"], "file": f_["name"], "scores": [prev, u["score"]]})
            f_["user_score"] = u["score"]
            f_["user_score_key"] = u["key"]
            f_["score_label"] = "USER-REPORTED"
    return unmatched, conflicts


def resolve_target_shas() -> dict[str, str]:
    """Registry sha256 for each target file (by repo + filename), independent of pool naming."""
    out: dict[str, str] = {}
    for e in json.loads(FETCH.read_text())["entries"]:
        lab = e["repo"]
        if lab in TARGETS and Path(e["path"]).name == TARGETS[lab]:
            out[lab] = e["sha256"]
    return out


def write_summary(facts: list[dict], overlap: np.ndarray, rho: np.ndarray, n: int) -> int:
    """Per-target gate split into three classes (never mixed):

    * SAME-CONTENT: decoded positive set identical to the target (format twins, e.g. -nan/-zeros);
    * DEGENERATE: reference 3-px coverage >= 0.70 (lattice / space-filling; literal overlap is
      uninformative, per gems.novelty.classify_space_filling_control);
    * DISTINCT: everything else. Literal gate = overlap > 0.70 or |rho| > 0.90 vs a DISTINCT ref.
    """
    sha_list = [f_["sha256"] for f_ in facts]
    target_rows = {}
    unmatched_user, score_conflicts = attach_user_scores(facts)
    tgt_sha = resolve_target_shas()
    for lab, fname in TARGETS.items():
        if lab not in tgt_sha:
            target_rows[lab] = {"error": f"target not found in registry: {fname}"}
            continue
        idx = [k for k, f_ in enumerate(facts) if f_["sha256"] == tgt_sha[lab]]
        if len(idx) != 1:
            target_rows[lab] = {"error": f"target sha not uniquely in pool: {fname} ({len(idx)})"}
            continue
        i = idx[0]
        t_dec = facts[i]["decoded_positive_sha256"]
        rows = []
        for j in range(n):
            if j == i:
                continue
            rows.append({
                "ref_name": facts[j]["name"], "ref_repo": facts[j]["repo"], "ref_sha256": sha_list[j],
                "same_content": facts[j]["decoded_positive_sha256"] == t_dec,
                "degenerate_coverage": bool(facts[j].get("coverage3px", 0) >= 0.70),
                "ref_positive": facts[j]["positive_in_footprint"], "ref_coverage3px": facts[j].get("coverage3px"),
                "rho": float(rho[i, j]), "overlap": float(overlap[i, j]), "ref_score": facts[j].get("score"),
            })
        same = [r for r in rows if r["same_content"]]
        degen = [r for r in rows if r["degenerate_coverage"] and not r["same_content"]]
        distinct = [r for r in rows if not r["same_content"] and not r["degenerate_coverage"]]
        ov_d = max(distinct, key=lambda r: r["overlap"])
        rho_d = max(distinct, key=lambda r: abs(r["rho"]))
        dup_flag = any((r["overlap"] > 0.70) or (abs(r["rho"]) > 0.90) for r in distinct)
        target_rows[lab] = {
            "name": fname,
            "sha256": sha_list[i],
            "decoded_positive_sha256": t_dec,
            "user_reported_score": facts[i].get("user_score"),
            "user_reported_key": facts[i].get("user_score_key"),
            "positive_in_footprint": facts[i]["positive_in_footprint"],
            "coverage3px": facts[i].get("coverage3px"),
            "same_content_files": [r["ref_name"] for r in same],
            "degenerate_refs_excluded": len(degen),
            "distinct_refs_checked": len(distinct),
            "max_overlap_distinct": ov_d["overlap"], "max_overlap_ref": {"name": ov_d["ref_name"], "repo": ov_d["ref_repo"]},
            "max_abs_rho_distinct": abs(rho_d["rho"]), "max_abs_rho_ref": {"name": rho_d["ref_name"], "repo": rho_d["ref_repo"]},
            "literal_gate_duplicate_vs_distinct_ref": bool(dup_flag),
            "top_closest_distinct_refs": sorted(distinct, key=lambda r: -max(abs(r["rho"]), r["overlap"]))[:6],
        }
    # Pairwise among the nine focus top files (format twins collapsed by content identity)
    tgt_idx = {}
    for lab in TARGETS:
        ks = [k for k, f_ in enumerate(facts) if lab in tgt_sha and f_["sha256"] == tgt_sha[lab]]
        if len(ks) == 1:
            tgt_idx[lab] = ks[0]
    pair = {}
    for a, ia in tgt_idx.items():
        pair[a] = {b: (None if ia == ib else round(float(overlap[ia, ib]), 4)) for b, ib in tgt_idx.items()}
    target_rows["_pairwise_overlap_among_nine_top_files"] = pair

    # Groups of decoded-identical predictions (exact duplicates by decoded positives)
    groups: dict[str, list[str]] = {}
    for f_ in facts:
        groups.setdefault(f_["decoded_positive_sha256"], []).append(f"{f_['repo']}:{f_['name']}")
    dup_groups = [sorted(v) for v in groups.values() if len(v) > 1]

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    if not CACHE.exists() or "--reuse" not in sys.argv:
        np.savez_compressed(CACHE, overlap=overlap, rho=rho, names=np.array([f_["name"] for f_ in facts]),
                            shas=np.array(sha_list))
    summary = {
        "schema": "gemsdoe1-focus-pool-audit-v1",
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "pool_size": n,
        "footprint_pixels": EXPECTED_FOOTPRINT_PX,
        "rho_threshold": 0.90, "overlap_threshold": 0.70, "radius_px": RADIUS,
        "sample_pixels_for_rho": SAMPLE_N, "sample_seed": 32,
        "exact_decoded_duplicate_groups": dup_groups,
        "format_failures": [f_["name"] for f_ in facts if not (
            f_["crs_epsg"] == 32611 and f_["count"] == 1 and f_["dtype"] == "float32"
            and f_["shape"] == [3730, 3292] and f_["transform_matches_official"]
            and f_["nan_inside_footprint"] == 0 and f_["footprint_in_0_1"])],
        "label_note": "User-reported scores are USER-REPORTED (no organizer receipt). Gates are measured, not estimated.",
        "user_score_unmatched": unmatched_user,
        "user_score_conflicts_by_sha": score_conflicts,
        "targets": target_rows,
        "files": facts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=1, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k in ("pool_size", "exact_decoded_duplicate_groups")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
