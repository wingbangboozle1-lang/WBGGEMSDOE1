#!/usr/bin/env python3
"""One preregistered WBG31-E1 screen: Euler solution-density channels.

Reuses the shared template cache, the buffered whole-component holdout, the
pooled evaluator, the single-feature canary and the writer exactly as the
WBG-C1 runner does (scripts/run_experiment.py). The only difference is the
candidate channels, which come from src/wbg31/euler.py.

Two representations are scored with the same instrument:
  * primary_dotted: top-37000 local maxima of each arm's OOF surface, after
    removing visible catalogue cells (masked_known) before selection;
  * secondary_continuous: the unplaced OOF probability surface (WBG-C1 form).

The control arm must reproduce the recorded WBG-C1 control (evidence/experiment.json)
because the feature stack, folds and model settings are identical.

No upload, no slot, no retuning. Refuses to re-run once its ledger exists.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from gems57 import evaluate_holdout, grid, holdout, submission_writer  # noqa: E402
from wbggems.audit import dump_json, sha256, single_feature_canary, utc_now  # noqa: E402
from wbg31 import euler  # noqa: E402
from prepare_data import prepare  # noqa: E402

ARMS = ("control_19band_hgb", "candidate_19band_plus_euler4_hgb")
N_DOTS = 37000
NMS_CELLS = 7
PREREG = ROOT / "registry/wbg31_e1_preregistration.json"
LEDGER = ROOT / "registry/experiment_ledger_wbg31_e1.json"
OUT = ROOT / "evidence/wbg31/e1_experiment.json"
FEATURE_DIR = ROOT / ".cache/wbg31"
WBG_C1_RECORD = ROOT / "evidence/experiment.json"


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
    return evaluate_holdout.evaluate(np.asarray(prediction[ys, xs], dtype=np.float32), cropped,
                                     footprint[ys, xs], origin=(ys.start, xs.start),
                                     global_shape=footprint.shape)


def dotted(surface, excluded, n_dots=N_DOTS, nms=NMS_CELLS):
    """Top-N local maxima after removing excluded (visible-catalogue) cells."""
    s = np.array(surface, dtype=np.float32, copy=True)
    s[excluded] = 0.0
    peaks = (s == ndi.maximum_filter(s, size=nms)) & (s > 0)
    idx = np.flatnonzero(peaks)
    order = idx[np.argsort(-s.ravel()[idx], kind="stable")][:n_dots]
    out = np.zeros(s.shape, np.float32)
    out.ravel()[order] = 1.0
    return out, dict(peaks_available=int(idx.size), dots_selected=int(order.size))


def main():
    started = time.monotonic()
    if OUT.exists() or LEDGER.exists():
        raise SystemExit("WBG31-E1 has already started. Reuse its receipt; do not silently rerun or tune.")
    prereg_hash = sha256(PREREG)
    prereg = json.loads(PREREG.read_text())
    spec = prereg["holdout"]
    fixed = prereg["fixed_model"]
    ledger = {"started_utc": utc_now(), "hypothesis_id": "WBG31-E1", "experiments_started": 1,
              "maximum_experiments": prereg["budget"]["maximum_experiments"],
              "maximum_wall_hours": prereg["budget"]["maximum_wall_hours"],
              "preregistration_sha256": prereg_hash, "status": "running", "submission_slots_used": 0}
    dump_json(LEDGER, ledger)
    try:
        cache_receipt = prepare()
        g = grid.load_grid(ROOT / "data")
        cache_root = ROOT / "data/template57"
        raw = [np.load(cache_root / row["cache_file"], mmap_mode="r") for row in cache_receipt["bands"]]
        assert len(raw) == 19, "expected the 19-band shared cache"
        seed = int(spec["split_seed"])
        # Euler channels, computed once from bands 9, 11, 13, 14 (no catalogue read).
        bands_for_euler = {b: np.asarray(raw[b - 1], dtype=np.float32) for b in (9, 11, 13, 14)}
        channels, euler_receipt = euler.euler_channels(bands_for_euler, g.footprint)
        FEATURE_DIR.mkdir(parents=True, exist_ok=True)
        chan_path = FEATURE_DIR / "euler_channels.npy"
        np.save(chan_path, channels)
        euler_receipt["channel_file"] = str(chan_path.relative_to(ROOT))
        euler_receipt["channel_sha256"] = sha256(chan_path)
        dump_json(ROOT / "evidence/wbg31/euler_features.json", euler_receipt)
        print("Built four Euler channels", flush=True)
        extra = [channels[i] for i in range(channels.shape[0])]
        all_bands = list(raw) + extra
        all_names = [row["description"] or f"band_{row['band']}" for row in cache_receipt["bands"]] + list(euler.CHANNELS)

        folds, quad = holdout.buffered_component_draw(
            g, seed=seed, hide_frac=spec["hide_fraction"],
            buffer_px=spec["feature_buffer_px"], boundary_px=spec["quadrant_boundary_erosion_px"])
        # Canary first, before any model is fit.
        canaries = []
        for fold in folds:
            active = g.footprint & fold["region"] & ~fold["masked_known"]
            truth = fold["truth"] & active
            pos = np.flatnonzero(truth)
            neg = np.flatnonzero(active & ~truth)
            rng = np.random.default_rng(seed + 100 + fold["fold"])
            neg = rng.choice(neg, size=min(50000, len(neg)), replace=False)
            ids = np.concatenate((pos, neg))
            labels = np.concatenate((np.ones(len(pos), bool), np.zeros(len(neg), bool)))
            for name, band in zip(all_names, all_bands):
                canaries.append(single_feature_canary(np.asarray(band, dtype=np.float32).ravel()[ids], labels,
                                                      name=name, fold=fold["name"]))
        canary = {"generated_utc": utc_now(), "evaluator_version": evaluate_holdout.VERSION,
                  "rows": canaries, "features_tested_alone": len(all_names),
                  "maximum_orientation_invariant_auc": max(r["orientation_invariant_auc"] for r in canaries),
                  "leakage_suspected": any(r["leakage_suspected"] for r in canaries),
                  "protocol": "AUC > 0.90 in either orientation or missingness is suspected leakage; sampled negatives only."}
        dump_json(ROOT / "evidence/wbg31/feature_canaries.json", canary)
        if canary["leakage_suspected"]:
            raise RuntimeError("Single-feature leakage canary fired; screen stopped before model fit.")
        surfaces = {arm: np.lib.format.open_memmap(FEATURE_DIR / f"{arm}-oof.npy", mode="w+",
                    dtype="float32", shape=g.shape) for arm in ARMS}
        for surface in surfaces.values():
            surface[:] = 0
        terms_cont, terms_dot = {}, {}
        fold_results = []
        fit_config = fixed
        for fold in folds:
            if time.monotonic() - started > 7200:
                raise TimeoutError("Two-hour experiment budget exhausted")
            f = fold["fold"]
            train = g.footprint & (quad != f) & (ndi.distance_transform_edt(~fold["region"]) > spec["training_collar_px"])
            train &= ~fold["hidden_all"]
            positive = np.flatnonzero(train & fold["visible"])
            negative = np.flatnonzero(train & ~g.catalogue)
            rng = np.random.default_rng(seed + f)
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
                   "training_positive_pixels": int(len(positive)),
                   "training_sampled_background_pixels": int(len(negative)),
                   "all_hidden_components_excluded_from_training": bool(not fold["hidden_all"].ravel()[train_ids].any()),
                   "training_is_spatially_disjoint": bool(not fold["region"].ravel()[train_ids].any()), "arms": {}}
            for arm, count in zip(ARMS, (19, len(all_bands))):
                model = HistGradientBoostingClassifier(
                    max_iter=fit_config["max_iter"], max_leaf_nodes=fit_config["max_leaf_nodes"],
                    learning_rate=fit_config["learning_rate"], l2_regularization=fit_config["l2_regularization"],
                    early_stopping=False, random_state=seed + f)
                with threadpool_limits(limits=2):
                    model.fit(x_all[:, :count], y, sample_weight=weights)
                    for start in range(0, len(test_ids), 65536):
                        ids = test_ids[start:start + 65536]
                        pred = model.predict_proba(matrix(all_bands[:count], ids))[:, 1]
                        if not np.isfinite(pred).all() or (pred < 0).any() or (pred > 1).any():
                            raise ValueError("model produced invalid confidence; no silent clipping")
                        surfaces[arm].ravel()[ids] = pred.astype(np.float32)
                measurement, block_terms = crop_evaluation(surfaces[arm], fold, g.footprint)
                row["arms"].setdefault(arm, {})["continuous"] = measurement
                terms_cont[arm] = terms_cont.get(arm, np.zeros_like(block_terms)) + block_terms
                print(f"{fold['name']} {arm} continuous: HOLDOUT-DTI={measurement['dti']:.6f}, withheld={measurement['n_truth']}", flush=True)
            fold_results.append(row)
        # Dotted representation: global selection after visible-catalogue exclusion.
        excluded = folds[0]["masked_known"] | ~g.footprint
        dot_fields = {}
        for arm in ARMS:
            surfaces[arm].flush()
            dots, sel = dotted(surfaces[arm], excluded)
            dot_fields[arm] = dots
            for fold, row in zip(folds, fold_results):
                measurement, block_terms = crop_evaluation(dots, fold, g.footprint)
                row["arms"][arm]["dotted"] = measurement
                row["arms"][arm]["dot_selection"] = sel
                terms_dot[arm] = terms_dot.get(arm, np.zeros_like(block_terms)) + block_terms
        summary_cont = evaluate_holdout.pooled_summary(terms_cont, draws=spec["bootstrap"]["draws"],
                                                       seed=spec["bootstrap"]["seed"], candidate=ARMS[1])
        summary_dot = evaluate_holdout.pooled_summary(terms_dot, draws=spec["bootstrap"]["draws"],
                                                      seed=spec["bootstrap"]["seed"], candidate=ARMS[1])
        # Reproduction check against the recorded WBG-C1 control (identical stack, folds and model).
        reproduction = None
        if WBG_C1_RECORD.exists():
            rec = json.loads(WBG_C1_RECORD.read_text())
            recorded = rec["summary"]["scores"]["control_19band_hgb"]["dti"]
            ours = summary_cont["scores"]["control_19band_hgb"]["dti"]
            reproduction = dict(recorded_wbg_c1_control_dti=recorded, this_run_control_dti=ours,
                                absolute_difference=abs(recorded - ours),
                                reproduced_within_1e_minus_6=bool(abs(recorded - ours) < 1e-6))
        # Research file: the candidate's dotted field, zeroed on the full catalogue and off-footprint.
        cand_dots = dot_fields[ARMS[1]].copy()
        cand_dots[~g.footprint | g.catalogue] = 0
        decoded = hashlib.sha256(np.ascontiguousarray(cand_dots).tobytes()).hexdigest()
        name = f"wbg31-e1-euler4-dots37k-20261031-{decoded[:10]}"
        note = "WBG31-E1 Euler SI-density + 19-band HGB; 37k OOF dots; research only, NOT approved for submission."
        path = ROOT / "docs/downloads" / (name + ".tif")
        receipt = submission_writer.write_submission(
            path, cand_dots, ROOT / "data/sample_submission.tif", g.footprint, note=note, name=name,
            catalogue=g.catalogue,
            metadata={"artifact_role": "research dot field, NOT a promoted competition submission",
                      "hypothesis_id": "WBG31-E1", "preregistration_sha256": prereg_hash,
                      "organizer_origin_authenticated": False, "submission_slots_used": 0})
        report = {"generated_utc": utc_now(), "hypothesis_id": "WBG31-E1", "preregistration_sha256": prereg_hash,
                  "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                  "primary_dotted": {"summary": summary_dot, "dots_per_arm": N_DOTS,
                                     "withheld_positive_pixels": sum(f["receipt"]["withheld_positive_pixels"] for f in folds)},
                  "secondary_continuous": {"summary": summary_cont},
                  "reproduction_check_vs_wbg_c1": reproduction,
                  "folds": fold_results, "candidate_file": str(path.relative_to(ROOT)),
                  "candidate_dotted_decoded_sha256": decoded, "candidate_file_sha256": receipt["sha256"],
                  "note": note, "final_dots_generated": True, "submission_slots_used": 0,
                  "limitations": [
                      "Public-catalogue hide-and-recover is not a hidden new-fault leaderboard estimate.",
                      "The OOF surface uses fold-visible catalogue only for training; the file applies the full catalogue exclusion, which is a research convention, not a production model.",
                      "Vertical-derivative units of bands 9 and 11 are unverified; depth acceptance is a stated assumption.",
                      "Holdout evaluator gems57-pooled-hide-v2 is a different instrument from the 0.1661 gems-segment-pooled-v1 benchmark; numbers are not comparable across evaluators.",
                      "No organizer-authenticated inputs, no portal receipt, no authorized slot."],
                  "elapsed_seconds": time.monotonic() - started}
        if sha256(PREREG) != prereg_hash:
            raise RuntimeError("Preregistration changed while the screen ran")
        dump_json(OUT, report)
        ledger.update(status="screen_complete_pending_registry", finished_utc=utc_now(),
                      elapsed_seconds=report["elapsed_seconds"], experiments_completed=1)
        dump_json(LEDGER, ledger)
        print(json.dumps({"dotted": summary_dot["paired_differences"], "continuous": summary_cont["paired_differences"],
                          "reproduction": reproduction}, indent=2, default=str), flush=True)
        print(f"Research dot field: {path.relative_to(ROOT)}; no slot authorised", flush=True)
    except Exception as exc:
        ledger.update(status="failed_closed", finished_utc=utc_now(), error=str(exc),
                      elapsed_seconds=time.monotonic() - started)
        dump_json(LEDGER, ledger)
        raise


if __name__ == "__main__":
    main()
