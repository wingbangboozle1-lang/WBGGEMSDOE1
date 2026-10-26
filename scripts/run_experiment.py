#!/usr/bin/env python3
"""One preregistered WBG-C1 screen; no retuning, dot placement or portal upload.

Reuse shared cache, buffered whole-component split, pooled evaluator and writer.
Research surfaces are retained even if negative. Registry STOP is applied by
scripts/audit_registry.py before any final dot placement (which is not implemented).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

# Avoid thread oversubscription in small CPU-only research sandboxes.
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

from gems57 import grid, holdout, evaluate_holdout, submission_writer
from wbggems import commutator
from wbggems.audit import dump_json, sha256, single_feature_canary, utc_now
from prepare_data import prepare

ARMS = ("control_19band_hgb", "candidate_19band_plus_commutator_hgb")


def matrix(bands, indices):
    return np.column_stack([np.asarray(b).ravel()[indices] for b in bands]).astype(np.float32)


def crop_evaluation(prediction, fold, footprint):
    y, x = np.nonzero(fold["region"])
    if len(y) == 0:
        raise ValueError("empty holdout quadrant")
    ys = slice(max(0, int(y.min()) - 4), min(footprint.shape[0], int(y.max()) + 5))
    xs = slice(max(0, int(x.min()) - 4), min(footprint.shape[1], int(x.max()) + 5))
    cropped = {key: np.asarray(fold[key])[ys, xs]
               for key in ("region", "visible", "masked_known", "truth")}
    return evaluate_holdout.evaluate(np.asarray(prediction[ys, xs]), cropped, footprint[ys, xs],
                                     origin=(ys.start, xs.start), global_shape=footprint.shape)


def main():
    started = time.monotonic()
    out = ROOT / "evidence/experiment.json"
    ledger_path = ROOT / "registry/experiment_ledger.json"
    if out.exists() or ledger_path.exists():
        raise SystemExit("This preregistered screen has already started. Reuse its receipt; do not silently rerun/tune.")
    prereg_path = ROOT / "registry/preregistration.json"
    prereg = json.loads(prereg_path.read_text())
    frozen_hash = sha256(prereg_path)
    ledger = {"started_utc": utc_now(), "hypothesis_id": "WBG-C1", "experiments_started": 1,
              "maximum_experiments": 3, "maximum_wall_hours": 2,
              "preregistration_sha256": frozen_hash, "status": "running", "submission_slots_used": 0}
    dump_json(ledger_path, ledger)
    try:
        cache_receipt = prepare()
        spec = prereg["holdout"]
        g = grid.load_grid(ROOT / "data")
        cache_root = ROOT / "data/template57"
        raw = [np.load(cache_root / row["cache_file"], mmap_mode="r") for row in cache_receipt["bands"]]
        names = [row["description"] or f"band_{row['band']}" for row in cache_receipt["bands"]]
        planes, features_receipt = commutator.features(raw[16], raw[14], raw[7], g.footprint)
        feature_dir = ROOT / ".cache/wbg-c1"
        feature_dir.mkdir(parents=True, exist_ok=True)
        features_receipt["planes"] = []
        for name, plane in zip(commutator.CHANNELS, planes):
            path = feature_dir / f"{name}.npy"
            np.save(path, plane)
            features_receipt["planes"].append({"name": name, "sha256": sha256(path), "path": str(path.relative_to(ROOT))})
        dump_json(ROOT / "evidence/candidate_features.json", features_receipt)
        print("Built four catalogue-blind commutator features", flush=True)
        all_bands = raw + planes
        all_names = names + list(commutator.CHANNELS)
        folds, quad = holdout.buffered_component_draw(
            g, seed=spec["split_seed"], hide_frac=spec["hide_fraction"],
            buffer_px=spec["feature_buffer_px"], boundary_px=spec["quadrant_boundary_erosion_px"])
        # Canary first, before training or trusting a model-level result.
        canaries = []
        for fold in folds:
            active = g.footprint & fold["region"] & ~fold["masked_known"]
            truth = fold["truth"] & active
            pos = np.flatnonzero(truth)
            neg = np.flatnonzero(active & ~truth)
            rng = np.random.default_rng(spec["split_seed"] + 100 + fold["fold"])
            neg = rng.choice(neg, size=min(50000, len(neg)), replace=False)
            ids = np.concatenate((pos, neg))
            labels = np.concatenate((np.ones(len(pos), bool), np.zeros(len(neg), bool)))
            for name, band in zip(all_names, all_bands):
                canaries.append(single_feature_canary(np.asarray(band).ravel()[ids], labels,
                                                      name=name, fold=fold["name"]))
        canary = {"generated_utc": utc_now(), "evaluator_version": evaluate_holdout.VERSION,
                  "rows": canaries, "all_features_tested_alone": True,
                  "maximum_orientation_invariant_auc": max(r["orientation_invariant_auc"] for r in canaries),
                  "leakage_suspected": any(r["leakage_suspected"] for r in canaries),
                  "protocol": "AUC > 0.90 in either orientation or missingness is suspected leakage; sampled negatives only."}
        dump_json(ROOT / "evidence/feature_canaries.json", canary)
        if canary["leakage_suspected"]:
            raise RuntimeError("Single-feature leakage canary fired; screen stopped before model fit.")
        surfaces = {arm: np.lib.format.open_memmap(feature_dir / f"{arm}-oof.npy", mode="w+",
                    dtype="float32", shape=g.shape) for arm in ARMS}
        for surface in surfaces.values():
            surface[:] = 0
        terms = {}
        fold_results = []
        fit_config = spec["fixed_model"]
        for fold in folds:
            if time.monotonic() - started > 7200:
                raise TimeoutError("Two-hour experiment budget exhausted")
            f = fold["fold"]
            # Label-blind held quadrant plus an 8 km training collar. All hidden
            # components are globally absent; context-collar faults are not negatives.
            train = g.footprint & (quad != f) & (ndi.distance_transform_edt(~fold["region"]) > spec["training_collar_px"])
            train &= ~fold["hidden_all"]
            positive = np.flatnonzero(train & fold["visible"])
            negative = np.flatnonzero(train & ~g.catalogue)
            rng = np.random.default_rng(spec["split_seed"] + f)
            negative = rng.choice(negative, size=min(fit_config["max_training_negatives"], len(negative)), replace=False)
            if not len(positive) or not len(negative):
                raise ValueError("empty training class")
            train_ids = np.concatenate((positive, negative))
            y = np.concatenate((np.ones(len(positive), np.uint8), np.zeros(len(negative), np.uint8)))
            weights = np.ones(len(y), float)
            weights[:len(positive)] = len(negative) / len(positive)
            x_all = matrix(all_bands, train_ids)
            test_ids = np.flatnonzero(g.footprint & (quad == f))
            row = {"name": fold["name"], "split_receipt": fold["receipt"],
                   "training_positive_pixels": int(len(positive)), "training_sampled_background_pixels": int(len(negative)),
                   "training_collar_m": spec["training_collar_px"] * 100,
                   "all_hidden_components_excluded_from_training": bool(not fold["hidden_all"].ravel()[train_ids].any()),
                   "training_is_spatially_disjoint": bool(not fold["region"].ravel()[train_ids].any()), "arms": {}}
            for arm, count in zip(ARMS, (19, len(all_bands))):
                model = HistGradientBoostingClassifier(
                    max_iter=fit_config["max_iter"], max_leaf_nodes=fit_config["max_leaf_nodes"],
                    learning_rate=fit_config["learning_rate"], l2_regularization=fit_config["l2_regularization"],
                    early_stopping=False, random_state=spec["split_seed"] + f)
                with threadpool_limits(limits=2):
                    model.fit(x_all[:, :count], y, sample_weight=weights)
                    for start in range(0, len(test_ids), 65536):
                        ids = test_ids[start:start + 65536]
                        pred = model.predict_proba(matrix(all_bands[:count], ids))[:, 1]
                        if not np.isfinite(pred).all() or (pred < 0).any() or (pred > 1).any():
                            raise ValueError("model produced invalid confidence; no silent clipping")
                        surfaces[arm].ravel()[ids] = pred.astype(np.float32)
                measurement, block_terms = crop_evaluation(surfaces[arm], fold, g.footprint)
                row["arms"][arm] = measurement
                terms[arm] = terms.get(arm, np.zeros_like(block_terms)) + block_terms
                print(f"{fold['name']} {arm}: HOLDOUT-DTI={measurement['dti']:.6f}, withheld={measurement['n_truth']}", flush=True)
            fold_results.append(row)
        summary = evaluate_holdout.pooled_summary(terms, draws=spec["bootstrap"]["draws"],
                    seed=spec["bootstrap"]["seed"], candidate=ARMS[1])
        for surface in surfaces.values():
            surface.flush()
        candidate = surfaces[ARMS[1]]
        # Grid metadata and footprint only come from the sample. Its prediction
        # values NEVER enter features, labels or output. Public known faults are
        # removed exactly, not by a truth-shaped halo.
        candidate[~g.footprint | g.catalogue] = 0
        candidate.flush()
        decoded = __import__("hashlib").sha256(np.ascontiguousarray(candidate).tobytes()).hexdigest()
        name = f"wbg-c1-commutator-research-surface-20261026-{decoded[:12]}"
        note = "WBG-C1 curvature non-coaxiality; spatial OOF research surface; no dot placement; NOT approved for submission."
        path = ROOT / "docs/downloads" / (name + ".tif")
        receipt = submission_writer.write_submission(path, candidate, ROOT / "data/sample_submission.tif", g.footprint,
                    note=note, name=name, catalogue=g.catalogue,
                    metadata={"artifact_role": "unplaced research surface, NOT a promoted competition submission",
                              "hypothesis_id": "WBG-C1", "preregistration_sha256": frozen_hash,
                              "prior_submission_pixels_used": False, "organizer_origin_authenticated": False})
        report = {"generated_utc": utc_now(), "hypothesis_id": "WBG-C1", "preregistration_sha256": frozen_hash,
                  "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                  "summary": summary, "folds": fold_results,
                  "withheld_positive_pixels": sum(f["receipt"]["withheld_positive_pixels"] for f in folds),
                  "representation": "continuous OOF confidence surface; no threshold/budget search or final dot placement",
                  "surface_file": str(path.relative_to(ROOT)), "surface_decoded_sha256": decoded,
                  "surface_sha256": receipt["sha256"], "note": note,
                  "limitations": ["Public-catalogue hide-and-recover is not a hidden new-fault leaderboard estimate.",
                    "Background is incompletely labelled; negative sampling is not verified fault absence.",
                    "Positive class weighting produces confidence, not calibrated prevalence-corrected probabilities.",
                    "No identically evaluated cross-repository current-best benchmark or untouched confirmation is claimed.",
                    "No assigned method lane, organizer-authenticated inputs, authenticated remaining slot allowance or portal receipt."],
                  "final_dots_generated": False, "submission_slots_used": 0, "elapsed_seconds": time.monotonic() - started}
        if sha256(prereg_path) != frozen_hash:
            raise RuntimeError("Preregistration changed while screen ran")
        dump_json(out, report)
        for arm, block_terms in terms.items():
            np.save(feature_dir / f"{arm}-block-terms.npy", block_terms)
        dump_json(ROOT / "evidence/block_terms.json", {arm: values.tolist() for arm, values in terms.items()})
        ledger.update(status="screen_complete_pending_registry", finished_utc=utc_now(),
                      elapsed_seconds=report["elapsed_seconds"], experiments_completed=1)
        dump_json(ledger_path, ledger)
        print(json.dumps(summary, indent=2), flush=True)
        print(f"Research surface: {path.relative_to(ROOT)}; no slot authorized", flush=True)
    except Exception as exc:
        ledger.update(status="failed_closed", finished_utc=utc_now(), error=str(exc),
                      elapsed_seconds=time.monotonic() - started)
        dump_json(ledger_path, ledger)
        raise


if __name__ == "__main__":
    main()
