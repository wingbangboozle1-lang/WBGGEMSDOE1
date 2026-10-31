#!/usr/bin/env python3
"""Run the preregistered PFTL-1 research-only spatial holdout screen.

The script consumes the verified shared feature cache, shared GEMS57 holdout,
evaluator, uniqueness comparator, submission writer and local validator. It
never selects a competition slot and never emits final dots.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

import numpy as np
from sklearn.metrics import roc_auc_score

from gems57 import evaluate_holdout as g57_evaluator
from gems57 import grid as g57_grid
from gems57 import holdout as g57_holdout
from gems57 import submission_writer as g57_writer
from gems57 import uniqueness as g57_uniqueness
from gems57 import validate as g57_validate
from wbggems.pfterlag import build_pfterlag_surface

PREREG_PATH = ROOT / "registry" / "pfterlag_preregistration_20261031.json"
FEATURE_CACHE_PATH = ROOT / "evidence" / "shared_feature_cache.json"
RESTORE_PATH = ROOT / "evidence" / "data_restore.json"
REGISTRY_PATH = ROOT / "registry" / "registry.json"
ARTIFACT_PATH = ROOT / "docs" / "downloads" / "wbggemsdoe1-pfterlag-pftl1-surface-20261031.tif"
RUN_CARD_PATH = ROOT / "evidence" / "pfterlag_20261031" / "run_card.json"
HOLDOUT_SEED = 71614
CANARY_SEED = 20261031
BOOTSTRAP_SEED = 20261031


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def load_cached_bands(footprint: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    cache = json.loads(FEATURE_CACHE_PATH.read_text(encoding="utf-8"))
    restore = json.loads(RESTORE_PATH.read_text(encoding="utf-8"))
    if not cache.get("all_19_template_band_hashes_match"):
        raise RuntimeError("shared feature-cache manifest does not certify all 19 band hashes")
    if not restore.get("all_verified") or cache.get("organizer_origin_authenticated") is not False:
        raise RuntimeError("unexpected data-restore provenance state")
    manifest_bands = {int(row["band"]): row for row in cache["bands"]}
    raw: dict[str, np.ndarray] = {}
    checked: dict[str, Any] = {}
    for band, name in ((12, "det_elev"), (13, "iso_grav_anom"), (14, "tmi")):
        row = manifest_bands[band]
        path = ROOT / "data" / "template57" / row["cache_file"]
        digest = sha256_file(path)
        if digest != row["sha256"]:
            raise RuntimeError(f"band {band} cache SHA-256 mismatch: {digest}")
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        if array.shape != footprint.shape or array.dtype != np.float32:
            raise RuntimeError(f"band {band} has unexpected shape/dtype: {array.shape}/{array.dtype}")
        raw[name] = array
        checked[str(band)] = {
            "literal_name": name,
            "cache_path": str(path.relative_to(ROOT)),
            "sha256": digest,
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "hash_verified": True,
        }
    source = ROOT / "data" / "training_features.tif"
    source_digest = sha256_file(source)
    if source_digest != cache["source_sha256"]:
        raise RuntimeError("the original feature-stack SHA-256 differs from the shared cache manifest")
    return raw, {
        "evidence_class": "OWNER-MIRROR-INTEGRITY",
        "source_stack": str(source.relative_to(ROOT)),
        "source_sha256": source_digest,
        "shared_template_repository": cache["shared_template_repository"],
        "shared_template_ref": cache["shared_template_ref"],
        "all_19_band_hashes_match_manifest": bool(cache["all_19_template_band_hashes_match"]),
        "selected_bands": checked,
        "organizer_origin_authenticated": False,
    }


def _two_sided_auc(values: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if np.ptp(values) <= 0.0:
        return 0.5, 0.5
    auc = float(roc_auc_score(y, values))
    return auc, max(auc, 1.0 - auc)


def leakage_canaries(
    features: dict[str, np.ndarray], folds: list[dict[str, Any]], footprint: np.ndarray
) -> dict[str, Any]:
    """Test every preregistered input/intermediate/final feature on each holdout fold."""
    result: dict[str, Any] = {}
    feature_names = list(features)
    for feature_name in feature_names:
        feature = np.asarray(features[feature_name], dtype=np.float32)
        per_fold = []
        pooled_y: list[np.ndarray] = []
        pooled_v: list[np.ndarray] = []
        for fold_index, fold in enumerate(folds):
            active = footprint & np.asarray(fold["region"], bool) & ~np.asarray(fold["masked_known"], bool)
            truth = active & np.asarray(fold["truth"], bool)
            pos = np.flatnonzero(truth)
            neg = np.flatnonzero(active & ~truth)
            if pos.size < 2 or neg.size < 2:
                raise RuntimeError(f"canary fold {fold['name']} lacks positive or negative samples")
            rng = np.random.default_rng(CANARY_SEED + fold_index)
            n_pos = min(int(pos.size), 10_000)
            n_neg = min(int(neg.size), max(20_000, 10 * n_pos))
            chosen_pos = rng.choice(pos, size=n_pos, replace=False)
            chosen_neg = rng.choice(neg, size=n_neg, replace=False)
            indices = np.concatenate([chosen_pos, chosen_neg])
            labels = np.concatenate([np.ones(n_pos, dtype=np.uint8), np.zeros(n_neg, dtype=np.uint8)])
            values = feature.ravel()[indices].astype(np.float64, copy=False)
            values = np.where(np.isfinite(values), values, 0.0)
            auc, two_sided = _two_sided_auc(values, labels)
            per_fold.append({
                "fold": fold["name"],
                "seed": CANARY_SEED + fold_index,
                "positive_count_in_fold": int(pos.size),
                "negative_count_in_fold": int(neg.size),
                "positive_sample_n": int(n_pos),
                "negative_sample_n": int(n_neg),
                "auc": auc,
                "two_sided_auc": two_sided,
            })
            pooled_y.append(labels)
            pooled_v.append(values)
        y_all = np.concatenate(pooled_y)
        v_all = np.concatenate(pooled_v)
        pooled_auc, pooled_two_sided = _two_sided_auc(v_all, y_all)
        result[feature_name] = {
            "pooled_auc": pooled_auc,
            "pooled_two_sided_auc": pooled_two_sided,
            "max_fold_two_sided_auc": max(row["two_sided_auc"] for row in per_fold),
            "folds": per_fold,
        }
    max_auc = max(row["max_fold_two_sided_auc"] for row in result.values())
    max_feature = max(result, key=lambda k: result[k]["max_fold_two_sided_auc"])
    return {
        "evidence_class": "HOLDOUT-LEAKAGE-CANARY",
        "threshold": 0.90,
        "max_two_sided_auc": max_auc,
        "max_feature": max_feature,
        "passed": bool(max_auc <= 0.90),
        "sampling": "per fold, up to 10,000 held-out positives and up to max(20,000, 10x positives) active non-positive cells; deterministic seed",
        "features_tested": result,
    }


def evaluate_surface(
    surface: np.ndarray, folds: list[dict[str, Any]], footprint: np.ndarray
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    terms: dict[str, np.ndarray] = {}
    fold_scores: list[dict[str, Any]] = []
    for fold in folds:
        candidate_score, candidate_terms = g57_evaluator.evaluate(
            surface, fold, footprint, block_side=200
        )
        active = footprint & np.asarray(fold["region"], bool) & ~np.asarray(fold["masked_known"], bool)
        if not active.any():
            raise RuntimeError(f"fold {fold['name']} has an empty active evaluation domain")
        matched_probability = float(surface[active].mean())
        null = np.zeros(surface.shape, dtype=np.float32)
        null[active] = matched_probability
        null_score, null_terms = g57_evaluator.evaluate(
            null, fold, footprint, block_side=200
        )
        terms["PFTL1_surface"] = terms.get("PFTL1_surface", np.zeros_like(candidate_terms)) + candidate_terms
        terms["mass_matched_uniform_null"] = terms.get("mass_matched_uniform_null", np.zeros_like(null_terms)) + null_terms
        fold_scores.append({
            "fold": fold["name"],
            "seed": fold["receipt"]["seed"],
            "withheld_positive_pixels": fold["receipt"]["withheld_positive_pixels"],
            "boundary_buffer_pixels": fold["receipt"]["boundary_buffer_px"],
            "feature_buffer_pixels": fold["receipt"]["feature_buffer_px"],
            "candidate": candidate_score,
            "mass_matched_uniform_null": null_score,
            "matched_mean_probability": matched_probability,
        })
    summary = g57_evaluator.pooled_summary(
        terms, draws=2000, seed=BOOTSTRAP_SEED, candidate="PFTL1_surface"
    )
    return summary, fold_scores


def registry_adapter(registry: dict[str, Any]) -> dict[str, Any]:
    """Map the restored inventory's `entries` keys to the shared comparator schema.

    This is only a shape adapter. It does not alter the shared comparator or
    thresholds, and its scope remains the indexed public-owner inventory.
    """
    entries = registry["entries"]
    complete = bool(
        registry.get("source_rows") == registry.get("restored_rows")
        and registry.get("unique_rasters") == len(entries)
        and registry.get("rejected_count") == 0
    )
    rasters = []
    for row in entries:
        rasters.append({
            "repo_first": row["repo"],
            "sources": [row["file"]],
            "cache_file": row["cache_path"],
            "sha256": row["sha256"],
        })
    return {
        "rasters": rasters,
        "complete_accessible_scan": complete,
        "errors": [],
        "scope": (
            "All unique restored rasters from the 231 indexed immutable public-owner source rows; "
            "not a complete organizer registry and may omit external, private, unlinked, inaccessible, "
            "or later-written submissions."
        ),
        "adapter": "registry/registry.json entries-to-gems57-rasters shape adapter; shared comparison code unchanged",
    }


def main() -> int:
    started = time.monotonic()
    if not PREREG_PATH.is_file():
        raise FileNotFoundError(f"preregistration missing: {PREREG_PATH}")
    if RUN_CARD_PATH.exists() or ARTIFACT_PATH.exists() or ARTIFACT_PATH.with_suffix(".zip").exists():
        raise FileExistsError("refusing to overwrite any PFTL-1 artifact or run card")
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    grid = g57_grid.load_grid()
    raw, data_provenance = load_cached_bands(grid.footprint)
    surface, feature_planes, normalization = build_pfterlag_surface(
        raw["det_elev"], raw["iso_grav_anom"], raw["tmi"], grid.footprint
    )
    del raw

    folds, _quadrants = g57_holdout.buffered_component_draw(
        grid,
        seed=HOLDOUT_SEED,
        hide_frac=0.20,
        buffer_px=3,
        boundary_px=12,
    )
    if len(folds) != 4 or any(not np.asarray(f["truth"], bool).any() for f in folds):
        raise RuntimeError("shared buffered component draw did not produce four nonempty spatial folds")
    if np.any(np.asarray(folds[0]["visible"], bool) & np.asarray(folds[0]["hidden_all"], bool)):
        raise RuntimeError("visible catalogue overlaps withheld components")

    canary = leakage_canaries(feature_planes, folds, grid.footprint)
    holdout, fold_scores = evaluate_surface(surface, folds, grid.footprint)

    research_name = "WBGGEMSDOE1 PFTL-1 research surface"
    note = "Research-only continuous surface; no final dots or slot clearance."
    writer_receipt = g57_writer.write_submission(
        ARTIFACT_PATH,
        surface,
        g57_grid.DATA_DIR / "sample_submission.tif",
        grid.footprint,
        note=note,
        name=research_name,
        catalogue=None,
        metadata={
            "candidate_id": "PFTL-1",
            "artifact_role": "continuous research-only score surface; no final dot placement",
            "preregistration_sha256": sha256_file(PREREG_PATH),
            "competition_slot_used": False,
            "organizer_approval": False,
        },
    )
    local_validation = g57_validate.validate(ARTIFACT_PATH, grid.footprint)
    if not local_validation.get("all_checks_passed"):
        raise RuntimeError("shared local validator did not pass the serialized research surface")

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    adapter = registry_adapter(registry)
    uniqueness = g57_uniqueness.compare_to_registry(
        ARTIFACT_PATH,
        adapter,
        grid.footprint,
        include_reverse=True,
        expected_grid=(grid.shape, grid.crs, grid.transform),
    )
    stop_reasons = []
    if not canary["passed"]:
        stop_reasons.append("at least one feature-only leakage canary exceeded the 0.90 threshold")
    if uniqueness.get("stop_required"):
        stop_reasons.append("pre-placement shared registry screen requires STOP")
    if not uniqueness.get("unique"):
        stop_reasons.append("candidate surface does not clear the literal registry uniqueness gate")

    holdout_candidate = holdout["scores"]["PFTL1_surface"]
    holdout_null = holdout["scores"]["mass_matched_uniform_null"]
    paired_delta = holdout["paired_differences"]["mass_matched_uniform_null"]
    card = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "RESEARCH-ONLY RUN CARD",
        "candidate_id": "PFTL-1",
        "experiment_count": 1,
        "experiment_budget_max": 3,
        "elapsed_seconds": time.monotonic() - started,
        "hypothesis": prereg["hypothesis"],
        "mechanism": prereg["mechanism"],
        "named_non_fault_mimic": prereg["named_non_fault_mimics"],
        "layers": prereg["inputs"],
        "preregistration": {
            "path": str(PREREG_PATH.relative_to(ROOT)),
            "sha256": sha256_file(PREREG_PATH),
            "status": prereg["status"],
            "assigned_method_paragraph_supplied": False,
        },
        "data_readiness": data_provenance,
        "surface_normalization": normalization,
        "leakage_canary": canary,
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": g57_evaluator.VERSION,
            "alpha": 0.2,
            "beta": 0.8,
            "triangular_kernel_radius_m": 300,
            "withheld_positive_count": holdout_candidate["withheld_positive_pixels"],
            "pooled_candidate": holdout_candidate,
            "mass_matched_uniform_null": holdout_null,
            "paired_candidate_minus_null": paired_delta,
            "folds": fold_scores,
            "split": {
                "seed": HOLDOUT_SEED,
                "quadrants": [row["name"] for row in folds],
                "whole_original_components_withheld": True,
                "feature_context_buffer_pixels": 3,
                "quadrant_boundary_erosion_pixels": 12,
                "visible_catalogue_masking": "pixel-exact in the shared evaluator",
                "catalogue_derived_features": "none; all PFTL-1 feature planes are built from bands 12, 13, 14 only",
            },
            "uncertainty": holdout["bootstrap"],
            "interpretation_limit": "Conditional internal holdout DTI only; not an organizer score or leaderboard projection.",
        },
        "preplacement_registry_comparison": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "phase": "continuous surface before any final-dot placement",
            "inventory_scope": uniqueness["scope"],
            "registry_rasters_expected": uniqueness["registry_rasters_expected"],
            "registry_rasters_checked": uniqueness["registry_rasters_checked"],
            "complete_accessible_index_scan": uniqueness["complete_accessible_scan"],
            "shared_comparator": "gems57.uniqueness.compare_to_registry (unchanged)",
            "schema_adapter": adapter["adapter"],
            "rho_limit": uniqueness["rho_limit"],
            "overlap_limit": uniqueness["overlap_limit"],
            "candidate_positive_support": uniqueness["my_dots"],
            "max_signed_spearman_full_footprint": uniqueness["worst_spearman_full_footprint"],
            "spearman_reference": uniqueness["worst_rho_submission"],
            "max_candidate_support_within_3px_of_registry": uniqueness["worst_dot_overlap"],
            "overlap_reference": uniqueness["worst_overlap_submission"],
            "byte_unique_among_checked": uniqueness["byte_unique_among_checked"],
            "pixel_unique_among_checked": uniqueness["pixel_unique_among_checked"],
            "duplicate_count": uniqueness["duplicate_count"],
            "unique_by_literal_rule": uniqueness["unique"],
            "stop_required": uniqueness["stop_required"],
            "rows": uniqueness["rows"],
        },
        "final_dot_comparison": {
            "status": "NOT_RUN — no final dots were emitted because the pre-placement gate failed",
            "rows": None,
        },
        "artifact": {
            "path": str(ARTIFACT_PATH.relative_to(ROOT)),
            "sha256": writer_receipt["sha256"],
            "bytes": writer_receipt["bytes"],
            "role": "new continuous research surface; not a final dotted candidate",
            "download_status": "YES — research only",
            "unique_bytes": uniqueness["byte_unique_among_checked"],
            "spatial_uniqueness_gate": "FAILED; do not submit",
        },
        "validator": {
            "evidence_class": "LOCAL-FORMAT-VALIDATION",
            "shared_writer_receipt": writer_receipt["template_report"],
            "shared_local_validator": writer_receipt["validator"],
            "post_write_revalidation": local_validation,
            "all_format_checks_passed": bool(local_validation["all_checks_passed"]),
            "organizer_acceptance": False,
        },
        "submission_name": research_name,
        "submission_note": note,
        "submission_note_characters": len(note),
        "download_status": "YES — research only",
        "submit_status": "NO — research surface fails the literal pre-placement registry gate; no final dots or selector decision",
        "leaderboard_estimate": None,
        "organizer_receipt": None,
        "competition_slot_used": False,
        "verdict": "negative",
        "stop_reasons": stop_reasons,
        "next_action": "Retain the negative research artifact. Do not place final dots, tune around registry gaps, or select/spend a slot.",
    }
    dump_json(RUN_CARD_PATH, card)
    print(json.dumps({
        "run_card": str(RUN_CARD_PATH.relative_to(ROOT)),
        "artifact": card["artifact"],
        "holdout_dti": {
            "candidate": holdout_candidate,
            "null": holdout_null,
            "paired_delta": paired_delta,
        },
        "leakage_max_two_sided_auc": canary["max_two_sided_auc"],
        "registry": {
            "checked": uniqueness["registry_rasters_checked"],
            "max_rho": uniqueness["worst_spearman_full_footprint"],
            "max_overlap": uniqueness["worst_dot_overlap"],
            "rho_reference": uniqueness["worst_rho_submission"],
            "overlap_reference": uniqueness["worst_overlap_submission"],
            "unique": uniqueness["unique"],
        },
        "elapsed_seconds": card["elapsed_seconds"],
        "slot_used": False,
    }, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
