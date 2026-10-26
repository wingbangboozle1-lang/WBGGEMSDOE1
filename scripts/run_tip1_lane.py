#!/usr/bin/env python3
"""Execute once or verify the preregistered three-arm TIP1 experiment."""

from __future__ import annotations

import argparse
import gc
import json
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import emission, holdout, novelty, submission, tip1  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

PREREG_COMMIT = "99d5d4a38a6a930ceca66f3f75ac64e0a7867e5b"
PREREG_PATH = "research/00_ranked_hypotheses.md"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"
LIDAR_METADATA = ROOT / "data/external/lidar_scarp_features.json"
REGISTRY = ROOT / "registry/registry.json"
REGISTRY_SOURCES = ROOT / "registry/source_registry.json"
BASELINE_CARD = ROOT / "evidence/benchmarks/gemsdoe24_s3dep1_run_card_20261026.json"
RUN_CARD = ROOT / "evidence/tip1_run_card_20261026.json"
DOCS_CARD = ROOT / "docs/data/tip1_run_card.json"
PREVIEW = ROOT / "docs/assets/tip1-preview.png"
DOWNLOADS = ROOT / "docs/downloads"

EXPECTED_INPUTS = {
    "data/bridge/sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "data/bridge/labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "data/external/lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "data/external/lidar_scarp_features.json": "9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41",
}
BASELINE_EXPECTED = {
    "dti": 0.16606013635163805,
    "ci95": [0.15185839118988828, 0.18033886456990444],
    "evaluator_version": "gems-segment-pooled-v1",
    "n_withheld_positive_pixels": 60988,
}
BUDGET_FRACTION = 0.0073
MIN_SPACING_PX = 3.0
MAX_SECONDS = 7200
ARM_ORDER = ("B", "A", "C")


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", checksum)


def write_preview(dots: np.ndarray, footprint: np.ndarray, path: Path, step: int = 6) -> None:
    """Write a deterministic dependency-free downsampled map preview."""
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = footprint.shape
    small_h, small_w = height // step, width // step
    fp_small = footprint[: small_h * step, : small_w * step].reshape(
        small_h, step, small_w, step
    ).any(axis=(1, 3))
    dot_small = dots[: small_h * step, : small_w * step].reshape(
        small_h, step, small_w, step
    ).any(axis=(1, 3))
    rgb = np.full((small_h, small_w, 3), (247, 244, 237), np.uint8)
    rgb[fp_small] = (218, 231, 226)
    rgb[dot_small] = (211, 80, 55)
    raw = b"".join(b"\x00" + rgb[row].tobytes() for row in range(small_h))
    header = struct.pack(">IIBBBBB", small_w, small_h, 8, 2, 0, 0, 0)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def merge_canary(context: holdout.SegmentHoldout, features: dict[str, np.ndarray]) -> dict:
    """Run shared canaries in memory-bounded groups while preserving one sample seed."""
    merged = {}
    metadata = None
    names = list(features)
    for start in range(0, len(names), 6):
        batch = {name: features[name] for name in names[start : start + 6]}
        result = context.canary(batch, seed=20261025, max_per_class=15000)
        merged.update(result["features"])
        metadata = result
    assert metadata is not None
    return {
        "diagnostic": metadata["diagnostic"],
        "evaluator_version": metadata["evaluator_version"],
        "threshold": metadata["threshold"],
        "two_polarities_checked": True,
        "passed": not any(row["leakage_suspected"] for row in merged.values()),
        "n_features_checked": len(merged),
        "features": merged,
        "interpretation": metadata["interpretation"],
    }


def verify_baseline_card() -> dict:
    baseline = json.loads(BASELINE_CARD.read_text())
    recorded = baseline["holdout"]
    observed = {
        "dti": recorded["dti"],
        "ci95": recorded["ci95"]["interval"],
        "evaluator_version": recorded["evaluator_version"],
        "n_withheld_positive_pixels": recorded["n_withheld_positive_pixels"],
    }
    if (
        observed["evaluator_version"] != BASELINE_EXPECTED["evaluator_version"]
        or observed["n_withheld_positive_pixels"]
        != BASELINE_EXPECTED["n_withheld_positive_pixels"]
        or not np.isclose(observed["dti"], BASELINE_EXPECTED["dti"], rtol=0, atol=1e-15)
        or not np.allclose(observed["ci95"], BASELINE_EXPECTED["ci95"], rtol=0, atol=1e-15)
    ):
        raise ValueError("Pinned S3DEP1 benchmark card does not match preregistration")
    return {
        "label": "HOLDOUT-DTI",
        **observed,
        "source": str(BASELINE_CARD.relative_to(ROOT)),
        "source_sha256": sha256_file(BASELINE_CARD),
        "independently_replayed_this_run": False,
        "paired_fold_dot_arrays_available": False,
        "promotion_effect": "fail_closed",
        "reason": (
            "The pinned public receipt contains pooled/fold summaries but no fold-aligned "
            "prediction masks or 10 km block components. Its ignored prepared stacks and "
            "stage arrays are absent, so an independent paired replay is unavailable."
        ),
    }


def verify_registry_manifest() -> dict:
    registry = json.loads(REGISTRY.read_text())
    if (
        registry["rejected_count"] != 0
        or not registry["retained_spacing_5_lattice_present"]
        or registry["source_manifest_sha256"] != sha256_file(REGISTRY_SOURCES)
        or registry["unique_rasters"] != len(registry["entries"])
        or not registry["entries"]
    ):
        raise ValueError("Immutable registry is incomplete")
    for row in registry["entries"]:
        path = ROOT / row["comparison_cache_path"]
        if sha256_file(path) != row["comparison_cache_sha256"]:
            raise ValueError(f"Registry comparison blob mismatch: {row['id']}")
    return registry


def pooled_receipt_check(result: dict) -> None:
    pooled = holdout.pooled_components(result["folds"])
    for key in ("dti", "TP_w", "FP_w", "FN_w", "n_truth", "n_emitted"):
        if not np.isclose(result[key], pooled[key], rtol=1e-12, atol=1e-9):
            raise ValueError(f"Pooled holdout mismatch for {key}")


def verify_recorded() -> dict:
    card = json.loads(RUN_CARD.read_text())
    if json.loads(DOCS_CARD.read_text()) != card:
        raise ValueError("Evidence and site run cards disagree")
    if card["verdict"] != "negative" or card["promote"] or card["ok_to_submit"]:
        raise ValueError("TIP1 fail-closed decision changed")
    if card["experiments_run"] > 3 or card["submission_slots_used"] != 0:
        raise ValueError("Experiment or slot budget violated")
    if card["benchmark"]["independently_replayed_this_run"]:
        raise ValueError("Recorded replay status unexpectedly changed")
    for result in card["arms"].values():
        pooled_receipt_check(result["holdout"])
    name = card["submission_name"]
    artifact = DOWNLOADS / name
    if Path(name).name != name or not name.endswith(".tif"):
        raise ValueError("Unsafe artifact name")
    if sha256_file(artifact) != card["raster_sha256"]:
        raise ValueError("TIP1 raster checksum mismatch")
    checks = submission.check_variants(artifact, TEMPLATE)
    if checks != card["validator_output"] or not checks["format_valid"]:
        raise ValueError("TIP1 exact-file validation changed")
    if not checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]:
        raise ValueError("TIP1 strict whole-array [0,1] validation failed")
    if not (1 <= len(card["submission_note"]) <= 140):
        raise ValueError("Submission note length invalid")
    if "DO NOT SUBMIT" not in card["submission_note"]:
        raise ValueError("Negative artifact note lost its warning")
    if sha256_file(REGISTRY) != card["inputs"]["registry/registry.json"]:
        raise ValueError("Registry receipt changed")
    return card


def execute() -> dict:
    if RUN_CARD.exists() or DOCS_CARD.exists():
        raise SystemExit("Frozen TIP1 receipt exists; use --verify-recorded. No reruns or tuning.")
    started = time.monotonic()
    for relative, expected_sha in EXPECTED_INPUTS.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_sha:
            raise ValueError(f"Missing or altered pinned input: {relative}")
    registry = verify_registry_manifest()
    benchmark = verify_baseline_card()

    with rasterio.open(TEMPLATE) as dataset:
        footprint = np.isfinite(dataset.read(1))
        grid = (dataset.shape, dataset.crs, dataset.transform)
    with rasterio.open(LABELS) as dataset:
        if (dataset.shape, dataset.crs, dataset.transform) != grid:
            raise ValueError("Catalogue grid mismatch")
        labels = footprint & (dataset.read(1) > 0)
    with rasterio.open(LIDAR) as dataset:
        if (dataset.shape, dataset.crs, dataset.transform) != grid:
            raise ValueError("LiDAR grid mismatch")
        encoded = {name: dataset.read(spec[0]) for name, spec in tip1.BANDS.items()}

    context = holdout.SegmentHoldout(footprint, labels, buffer_px=15)
    support = tip1.fixed_support(encoded, footprint)
    decoded = {
        name: tip1.decode(encoded[name], maximum, encoding)
        for name, (_band, maximum, encoding) in tip1.BANDS.items()
    }
    delta2 = tip1.axial_delta(decoded["coh100"], decoded["strike"], support, 2)
    delta4 = tip1.axial_delta(decoded["coh100"], decoded["strike"], support, 4)
    balance = tip1.curvature_balance(decoded["lapneg_max"], decoded["lappos_max"])
    root_step = np.sqrt(decoded["step_max"]).astype(np.float32)
    veto = tip1.channel_bank_veto(
        decoded["cross_max"], decoded["upface_max"], decoded["downface_max"]
    )
    surfaces = tip1.arm_surfaces(
        decoded["coh100"], delta2, delta4, balance, root_step, veto, support
    )
    transformed = {
        "support": support.astype(np.float32),
        "delta2": delta2,
        "delta4": delta4,
        "curvature_balance": balance,
        "root_step": root_step,
        "channel_bank_veto": veto,
        "max_delta": np.maximum(delta2, delta4),
        "scale_persistence": np.sqrt(delta2 * delta4),
        "arm_A_surface": surfaces["A"],
        "arm_B_surface": surfaces["B"],
        "arm_C_surface": surfaces["C"],
    }
    canary_features = {f"raw_{name}": value for name, value in encoded.items()}
    canary_features.update({f"decoded_{name}": value for name, value in decoded.items()})
    canary_features.update(transformed)
    canary = merge_canary(context, canary_features)

    base_card = {
        "schema": "gemsdoe1-tip1-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "TIP1: orientation-following fault-tip damage gradient",
        "mechanism": (
            "Maximum |coh100(+2)-coh100(-2)| or |coh100(+4)-coh100(-4)| "
            "along local axial strike, multiplied by balanced crest/base curvature, "
            "sqrt(step amplitude), complete valid support and a channel-bank veto."
        ),
        "named_non_fault_mimic": "Road-cut terminus and fan-channel avulsion-lobe edge",
        "preregistration": PREREG_PATH,
        "preregistration_commit": PREREG_COMMIT,
        "prediction_uses_catalogue": False,
        "prediction_uses_registry_rasters": False,
        "experiment_limit": 3,
        "time_limit_seconds": MAX_SECONDS,
        "experiments_run": 0,
        "submission_slots_used": 0,
        "benchmark": benchmark,
        "leakage_canary": canary,
        "supported_pixels": int(support.sum()),
        "arms": {},
        "correlation_overlap_vs_registry": {},
        "raster_sha256": None,
        "validator_output": None,
        "submission_name": None,
        "submission_note": "TIP1 research artifact | DO NOT SUBMIT",
        "promote": False,
        "verdict": "negative",
        "ok_to_download": False,
        "ok_to_submit": False,
        "submission_authorized": False,
        "organizer_confirmed_score": None,
        "inputs": {
            **{relative: sha256_file(ROOT / relative) for relative in EXPECTED_INPUTS},
            "registry/source_registry.json": sha256_file(REGISTRY_SOURCES),
            "registry/registry.json": sha256_file(REGISTRY),
            str(BASELINE_CARD.relative_to(ROOT)): sha256_file(BASELINE_CARD),
        },
        "code_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (
                Path(__file__),
                ROOT / "src/gems/tip1.py",
                ROOT / "src/gems/holdout.py",
                ROOT / "src/gems/metric.py",
                ROOT / "src/gems/emission.py",
                ROOT / "src/gems/novelty.py",
                ROOT / "src/gems/submission.py",
            )
        },
        "registry_scope": registry["scope"],
        "registry_unique_rasters": registry["unique_rasters"],
        "stopped_reason": None,
    }

    def freeze(reason: str) -> dict:
        base_card["stopped_reason"] = reason
        base_card["elapsed_seconds"] = time.monotonic() - started
        save_json(RUN_CARD, base_card)
        save_json(DOCS_CARD, base_card)
        print(json.dumps(base_card, indent=2, allow_nan=False), flush=True)
        return base_card

    if not canary["passed"]:
        return freeze("leakage canary exceeded |AUC| polarity threshold; stopped before scoring")
    if time.monotonic() - started >= MAX_SECONDS:
        return freeze("two-hour limit reached before novelty checks")

    # All three preregistered surfaces are checked in one immutable-registry pass.
    surface_novelty = novelty.compare_registry_surfaces(
        surfaces, footprint, registry["entries"], ROOT
    )
    base_card["correlation_overlap_vs_registry"]["surface_before_placement"] = surface_novelty
    if not all(report["passed"] for report in surface_novelty.values()):
        return freeze("duplicate surface; stopped before holdout placement")
    if time.monotonic() - started >= MAX_SECONDS:
        return freeze("two-hour limit reached before holdout")

    # Fixed order begins with the preregistered primary; A and C cannot replace B.
    for arm in ARM_ORDER:
        predictions = [
            emission.priority_poisson(
                surfaces[arm],
                fold["valid"] & ~fold["visible"] & (surfaces[arm] > 0),
                round(BUDGET_FRACTION * int(fold["valid"].sum())),
                min_dist=MIN_SPACING_PX,
            )
            for fold in context.folds
        ]
        result = context.summarize(predictions)
        pooled_receipt_check(result)
        base_card["arms"][arm] = {
            "name": tip1.ARM_NAMES[arm],
            "fixed_role": (
                "primary; only arm eligible for promotion"
                if arm == "B"
                else "mechanism control; cannot replace Arm B"
            ),
            "holdout": result,
        }
        base_card["experiments_run"] += 1
        del predictions
        gc.collect()
        if time.monotonic() - started >= MAX_SECONDS:
            return freeze("two-hour limit reached during fixed three-arm holdout")

    primary = base_card["arms"]["B"]["holdout"]
    base_card["promotion_gate"] = {
        "arm_B_point_exceeds_current_best": bool(primary["dti"] > benchmark["dti"]),
        "current_best_independently_replayed": False,
        "paired_delta_dti": None,
        "paired_delta_ci95": None,
        "paired_ci95_strictly_positive": False,
        "passed": False,
        "reason": "Fail closed: current-best fold predictions cannot be replayed for paired bootstrap.",
    }

    final = emission.priority_poisson(
        surfaces["B"],
        footprint & ~labels & (surfaces["B"] > 0),
        round(BUDGET_FRACTION * int(footprint.sum())),
        min_dist=MIN_SPACING_PX,
    )
    content_id = submission.scored_content_id(final, footprint, labels)
    name = f"gemsdoe1-tip1-directional-tip-gradient-20261026-{content_id}-zeros.tif"
    artifact = DOWNLOADS / name
    submission.write_submission(final, TEMPLATE, artifact, outside="zero")
    checks = submission.check_variants(artifact, TEMPLATE)
    note = (
        f"TIP1 directional LiDAR coherence-tip gradient | format-valid research; "
        f"DO NOT SUBMIT | id {content_id}"
    )
    if len(note) > 140:
        raise AssertionError("Submission note exceeds 140 characters")
    base_card.update(
        raster_sha256=sha256_file(artifact),
        validator_output=checks,
        submission_name=name,
        submission_note=note,
        ok_to_download=bool(checks["format_valid"]),
        final_dot_count=int(final.sum()),
        final_budget=int(round(BUDGET_FRACTION * int(footprint.sum()))),
        content_id=content_id,
    )
    if not checks["format_valid"] or not checks["checks"][
        "variant_strict_whole_array_no_nan_allowed"
    ]["pass"]:
        return freeze("exact-file format validation failed")
    write_preview(final, footprint, PREVIEW)

    final_novelty = novelty.compare_registry(
        final.astype(np.float32),
        footprint,
        registry["entries"],
        ROOT,
        dots=final,
    )
    base_card["correlation_overlap_vs_registry"]["final_dots"] = final_novelty
    duplicate_rows = [row for row in final_novelty["rows"] if row["duplicate"]]
    base_card["literal_duplicate_rows"] = duplicate_rows
    if not final_novelty["passed"]:
        return freeze(
            "duplicate final dots under literal all-entry gate; no relocation, retuning, selector promotion or slot use"
        )

    return freeze(
        "negative: baseline replay/paired-CI gate unavailable; artifact retained for audit only"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    args = parser.parse_args()
    card = verify_recorded() if args.verify_recorded else execute()
    if args.verify_recorded:
        print(json.dumps(card, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
