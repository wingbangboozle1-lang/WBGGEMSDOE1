"""Full-Footprint (`5,167,373` px) Pre-Placement & Final-Dot Uniqueness Auditor for `WBG-4`.

Directly reuses `vendor/gems57/uniqueness.py` (`compare_array_to_registry` and `two_phase_summary`)
with ZERO private fork, scanning the deduplicated union of:
  1. All 360 frozen focus-site rasters (`registry/focus_inventory.json`: `GEMSDOE24..36`),
  2. All 15 peer rasters in `data/wbg_s2_peers/` (`2026-10-27` focus updates + `KANLERGEMSDOE2`),
  3. All accessible sister-repository `.tif` rasters in `data/wbg4_sister_peers/`
     (`WBGGEMSDOE2`, `WBGGEMSDOE3`, `KANLERGEMSDOE1/2/3`, `GEMSDOEkarage1/2/3`,
      `ApartGEMSDOE1/2/3`, `GEMSDOESASS1/2/3`),
  4. All prior local `WBGGEMSDOE1` `.tif` artifacts in `docs/downloads/` (excluding `candidate_path` itself).

Enforces `|Spearman| <= 0.90` on BOTH pre-placement continuous surface and final dots across all
rasters on all `5,167,373` footprint pixels, reports `two_phase_summary` verbatim (including literal
`r13-lattice-s5` and continuous-surface `WBG-C1` firings with zero private exemption), and checks
competing non-lattice sparse submissions (`forward_3px_overlap <= 0.70`).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57.grid import TRANSFORM  # noqa: E402
from gems57.uniqueness import compare_array_to_registry, two_phase_summary  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_aligned_single_band_tif(path: Path, shape: tuple[int, int]) -> bool:
    try:
        with rasterio.open(path) as ds:
            if ds.count != 1 or ds.shape != shape:
                return False
            if ds.crs is None or ds.crs.to_epsg() != 32611 or ds.transform != TRANSFORM:
                return False
        return True
    except Exception:
        return False


def build_combined_registry_index(
    *,
    exclude_paths: set[Path] | None = None,
    shape: tuple[int, int] = (3730, 3292),
) -> tuple[dict[str, Any], dict[str, int]]:
    """Build a SHA-256-deduplicated full inventory across focus, peer, sister, and local rasters."""
    excl = {p.resolve() for p in (exclude_paths or set())}
    by_sha: dict[str, dict[str, Any]] = {}
    counts = {
        "focus_inventory_360": 0,
        "wbg_s2_peers": 0,
        "wbg4_sister_peers": 0,
        "wbggemsdoe1_local": 0,
        "skipped_non_aligned_tifs": 0,
    }

    def _add(repo: str, source_label: str, path: Path, bucket: str, known_sha: str | None = None) -> None:
        rp = path.resolve()
        if rp in excl or not rp.exists():
            return
        if bucket != "focus_inventory_360" and not _is_aligned_single_band_tif(rp, shape):
            counts["skipped_non_aligned_tifs"] += 1
            return
        digest = known_sha or _sha256(rp)
        counts[bucket] += 1
        rel = str(rp.relative_to(ROOT)) if rp.is_relative_to(ROOT) else str(rp)
        if digest not in by_sha:
            by_sha[digest] = {
                "repo_first": repo,
                "sha256": digest,
                "cache_file": rel,
                "sources": [source_label],
            }
        else:
            if source_label not in by_sha[digest]["sources"]:
                by_sha[digest]["sources"].append(source_label)

    # 1. Frozen 9-site focus inventory (360 unique hashes)
    focus_inv = json.loads((ROOT / "registry" / "focus_inventory.json").read_text())
    for r in focus_inv["rasters"]:
        _add(
            r["repo_first"],
            r["sources"][0],
            ROOT / r["cache_file"],
            "focus_inventory_360",
            known_sha=r["sha256"],
        )

    # 2. Latest 2026-10-27 focus + KANLERGEMSDOE2 rasters
    for p in sorted((ROOT / "data" / "wbg_s2_peers").glob("*.tif")):
        repo_guess = p.name.split("_")[0]
        _add(repo_guess, f"wbg_s2_peers:{p.name}", p, "wbg_s2_peers")

    # 3. Sister GEMSDOE repositories restored by `scripts/wbg4_restore_data.py`
    sister_dir = ROOT / "data" / "wbg4_sister_peers"
    if sister_dir.exists():
        for p in sorted(sister_dir.glob("*.tif")):
            repo_guess = p.name.split("__")[0]
            _add(repo_guess, f"sister:{p.name}", p, "wbg4_sister_peers")

    # 4. Prior local WBGGEMSDOE1 artifacts
    for p in sorted((ROOT / "docs" / "downloads").glob("*.tif")):
        _add("WBGGEMSDOE1", f"WBGGEMSDOE1:docs/downloads/{p.name}", p, "wbggemsdoe1_local")

    rasters = sorted(by_sha.values(), key=lambda d: (d["repo_first"], d["sources"][0], d["sha256"]))
    index = {
        "complete_accessible_scan": True,
        "errors": [],
        "n_unique_file_hashes": len(rasters),
        "rasters": rasters,
    }
    counts["deduplicated_unique_rasters"] = len(rasters)
    return index, counts


def run_full_wbg4_uniqueness_audit(
    *,
    pre_surface_2d: np.ndarray,
    final_dots_2d: np.ndarray,
    footprint: np.ndarray,
    candidate_tif_path: Path | None = None,
) -> dict[str, Any]:
    """Audit both pre-placement surface and final dots across all 450+ deduplicated rasters."""
    excl = {candidate_tif_path.resolve()} if candidate_tif_path is not None and candidate_tif_path.exists() else set()
    reg_index, source_counts = build_combined_registry_index(exclude_paths=excl, shape=footprint.shape)

    # Normalize pre-placement surface strictly into [0, 1] inside footprint, 0 outside
    surf = np.where(footprint & np.isfinite(pre_surface_2d), pre_surface_2d, 0.0).astype(np.float32)
    s_max = float(surf[footprint].max()) if np.any(footprint) else 1.0
    s_min = float(surf[footprint].min()) if np.any(footprint) else 0.0
    if s_max > s_min:
        surf_01 = np.where(footprint, (surf - s_min) / (s_max - s_min), 0.0).astype(np.float32)
    else:
        surf_01 = np.zeros_like(surf)

    # Exact full-footprint (`5,167,373` px) Spearman of pre-placement surface against all registry rasters
    # (uses identical rankdata algebra to `vendor/gems57/uniqueness.py` without redundant 3-px dilation on surface)
    from scipy.stats import rankdata

    s_vals = surf_01[footprint]
    s_ranks = rankdata(s_vals).astype(np.float64)
    s_ranks -= s_ranks.mean()
    s_norm = float(np.linalg.norm(s_ranks))
    pre_rows: list[dict[str, Any]] = []
    for rec in reg_index["rasters"]:
        p = ROOT / rec["cache_file"]
        with rasterio.open(p) as src:
            theirs = src.read(1).astype(np.float32)
        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        tv = theirs[footprint]
        if s_norm == 0.0 or np.ptp(tv) == 0.0:
            continue
        if np.all((tv == 0.0) | (tv == 1.0)):
            tb = tv > 0.0
            nt = int(tb.sum())
            n = int(tv.size)
            rho = float(s_ranks[tb].sum() / (s_norm * np.sqrt(nt * (n - nt) / n)))
        else:
            tr = rankdata(tv).astype(np.float64)
            tr -= tr.mean()
            rho = float(np.dot(s_ranks, tr) / (s_norm * np.linalg.norm(tr)))
        pre_rows.append({"submission": rec["sources"][0], "spearman_full_footprint": rho})
    worst_pre_abs = max(pre_rows, key=lambda r: abs(r["spearman_full_footprint"]))

    file_sha = _sha256(candidate_tif_path) if candidate_tif_path is not None and candidate_tif_path.exists() else None
    dot_cmp = compare_array_to_registry(
        final_dots_2d.astype(np.float32),
        reg_index,
        footprint,
        file_sha256=file_sha,
        include_reverse=True,
    )
    if candidate_tif_path is not None:
        dot_cmp["my_file"] = str(candidate_tif_path.relative_to(ROOT))

    n_fp = int(footprint.sum())
    two_phase = two_phase_summary(
        dot_cmp["rows"],
        n_fp,
        expected_rasters=len(reg_index["rasters"]),
    )

    checked_rows = [r for r in dot_cmp["rows"] if "error" not in r]
    worst_dot_abs_rho = max(
        (r for r in checked_rows if r.get("spearman_full_footprint") is not None),
        key=lambda r: abs(r["spearman_full_footprint"]),
    )

    # Separate competing non-lattice sparse submissions (`0 < their_dots <= 0.20 * n_fp` and not `r13-lattice-s5`)
    # strictly as a transparent diagnostic alongside the unmodified literal reading!
    competing_sparse = [
        r
        for r in checked_rows
        if 0 < int(r["their_dots"]) <= int(0.20 * n_fp)
        and "r13-lattice-s5" not in r["submission"]
    ]
    worst_comp_fwd = max(competing_sparse, key=lambda r: r["my_dots_within_3px_of_theirs"])
    worst_comp_rev = max(competing_sparse, key=lambda r: r["their_dots_within_3px_of_mine"])
    worst_comp_rho = max(
        (r for r in competing_sparse if r.get("spearman_full_footprint") is not None),
        key=lambda r: abs(r["spearman_full_footprint"]),
    )

    # Extract explicit per-site summary across Focus-9 + Local WBGGEMSDOE1 + Sister GEMSDOE repos
    by_repo_best: dict[str, dict[str, Any]] = {}
    for r in competing_sparse:
        repo = str(r.get("repo") or "unknown")
        prev = by_repo_best.get(repo)
        if prev is None or r["my_dots_within_3px_of_theirs"] > prev["forward_3px_overlap"]:
            by_repo_best[repo] = {
                "repo": repo,
                "submission": r["submission"],
                "their_dots": int(r["their_dots"]),
                "forward_3px_overlap": round(float(r["my_dots_within_3px_of_theirs"]), 6),
                "reverse_3px_overlap": round(float(r["their_dots_within_3px_of_mine"]), 6),
                "spearman_full_footprint": round(float(r["spearman_full_footprint"]), 6)
                if r.get("spearman_full_footprint") is not None
                else None,
                "jaccard_dot_sets": round(float(r["jaccard_dot_sets"]), 6),
            }

    pre_abs_rho_val = abs(float(worst_pre_abs["spearman_full_footprint"]))
    dot_abs_rho_val = abs(float(worst_dot_abs_rho["spearman_full_footprint"]))
    comp_fwd_val = float(worst_comp_fwd["my_dots_within_3px_of_theirs"])

    competing_sparse_pass = (
        pre_abs_rho_val <= 0.90
        and dot_abs_rho_val <= 0.90
        and comp_fwd_val <= 0.70
        and bool(dot_cmp["byte_unique_among_checked"])
        and bool(dot_cmp["pixel_unique_among_checked"])
    )

    return {
        "schema_version": 1,
        "lane_id": "WBG-4",
        "method_code": "CSJF-1",
        "footprint_pixels": n_fp,
        "full_footprint_exact_spearman_no_subsampling": True,
        "source_counts": source_counts,
        "pre_placement_surface_gate": {
            "rasters_checked": len(pre_rows),
            "max_abs_spearman_full_footprint": round(pre_abs_rho_val, 6),
            "max_signed_spearman_full_footprint": round(float(worst_pre_abs["spearman_full_footprint"]), 6),
            "worst_comparator": worst_pre_abs["submission"],
            "limit": 0.90,
            "pass": pre_abs_rho_val <= 0.90,
        },
        "final_dots_competing_sparse_diagnostic": {
            "competing_sparse_rasters_checked": len(competing_sparse),
            "max_forward_3px_overlap": round(comp_fwd_val, 6),
            "worst_forward_comparator": worst_comp_fwd["submission"],
            "max_reverse_3px_overlap": round(float(worst_comp_rev["their_dots_within_3px_of_mine"]), 6),
            "worst_reverse_comparator": worst_comp_rev["submission"],
            "max_abs_spearman_full_footprint": round(abs(float(worst_comp_rho["spearman_full_footprint"])), 6),
            "worst_spearman_comparator": worst_comp_rho["submission"],
            "byte_unique": bool(dot_cmp["byte_unique_among_checked"]),
            "pixel_unique": bool(dot_cmp["pixel_unique_among_checked"]),
            "competing_sparse_pass": competing_sparse_pass,
            "top_15_by_forward_overlap": [
                {
                    "repo": r["repo"],
                    "submission": r["submission"],
                    "their_dots": int(r["their_dots"]),
                    "forward_3px_overlap": round(float(r["my_dots_within_3px_of_theirs"]), 6),
                    "reverse_3px_overlap": round(float(r["their_dots_within_3px_of_mine"]), 6),
                    "spearman_full_footprint": round(float(r["spearman_full_footprint"]), 6)
                    if r.get("spearman_full_footprint") is not None
                    else None,
                    "jaccard_dot_sets": round(float(r["jaccard_dot_sets"]), 6),
                }
                for r in sorted(competing_sparse, key=lambda x: -x["my_dots_within_3px_of_theirs"])[:15]
            ],
            "worst_per_repo": dict(sorted(by_repo_best.items())),
        },
        "two_phase_summary": two_phase,
        "literal_all_entry_gate": {
            "complete_accessible_scan": bool(dot_cmp["complete_accessible_scan"]),
            "rasters_checked": int(dot_cmp["registry_rasters_checked"]),
            "max_abs_spearman_full_footprint": round(dot_abs_rho_val, 6),
            "worst_spearman_comparator": worst_dot_abs_rho["submission"],
            "worst_forward_3px_overlap": round(float(dot_cmp["worst_dot_overlap"]), 6),
            "worst_overlap_comparator": dot_cmp["worst_overlap_submission"],
            "duplicate_firings_count": int(dot_cmp["duplicate_count"]),
            "literal_pass": bool(dot_cmp["unique"]) and dot_abs_rho_val <= 0.90,
            "governance_note": (
                "Fail-closed under AGENTS.md: literal all-entry registry includes continuous research "
                "surfaces (e.g. WBG-C1, 17GEMSDOE E-proba-multiscale) and 5-px calibration grid "
                "13gems_20261001_r13-lattice-s5 (covering 99.8713% of footprint within 3 px). "
                "No private exemption is claimed; verdict stays 'negative' / SUBMIT: NO pending "
                "explicit human selector protocol reconciliation."
            ),
        },
    }
