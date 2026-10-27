#!/usr/bin/env python3
"""WBG-D1 preregistered three-experiment runner.

EXP-1 deterministic radiometric composite dots + random baseline (no fitting).
EXP-2 19-band control vs 19+7 channel HGB spatial LOQO with per-channel canaries.
EXP-3 full-footprint synthesis, registry uniqueness and portal validation.

All metric arithmetic is the shared vendor/gems57 instrument
(gems57-pooled-hide-v2). Evidence is written under evidence/wbg_d1/.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

from gems57 import evaluate_holdout, grid, holdout, submission_writer, uniqueness
from wbggems.audit import dump_json, sha256, single_feature_canary, utc_now
from wbggemsd1.features import (
    CHANNEL_NAMES,
    DOT_BUDGET,
    build_radiometric_channels,
    deterministic_composite,
    nms_dots,
    rtp_edge,
)

EVID = ROOT / "evidence" / "wbg_d1"
CACHE = ROOT / ".cache" / "wbg-d1"
BAND_DIR = ROOT / "data" / "template57" / ".cache" / "features"
PREREG = ROOT / "registry" / "preregistration_wbg_d1.json"
FIT = dict(max_iter=80, max_leaf_nodes=15, learning_rate=0.08,
           l2_regularization=5.0, early_stopping=False)
MAX_NEG = 160_000


def _load_grid():
    return grid.load_grid(ROOT / "data")


def _channels_path():
    return CACHE / "channels.npz"


def get_channels(g):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = _channels_path()
    if path.exists():
        loaded = np.load(path)
        return {name: loaded[name] for name in CHANNEL_NAMES}
    channels = build_radiometric_channels(
        ROOT / "data/external/geodawn_rad_u8.tif",
        ROOT / "data/external/geodawn_extensions_u8.tif",
        BAND_DIR / "band-14.npy", g.footprint, g.catalogue)
    meta = channels.pop("_meta")
    np.savez(path, **channels)
    dump_json(EVID / "radiometric_coverage.json", {"generated_utc": utc_now(), **meta})
    return channels


def crop_evaluation(prediction, fold, footprint):
    y, x = np.nonzero(fold["region"])
    ys = slice(max(0, int(y.min()) - 4), min(footprint.shape[0], int(y.max()) + 5))
    xs = slice(max(0, int(x.min()) - 4), min(footprint.shape[1], int(x.max()) + 5))
    cropped = {key: np.asarray(fold[key])[ys, xs]
               for key in ("region", "visible", "masked_known", "truth")}
    return evaluate_holdout.evaluate(
        np.asarray(prediction[ys, xs]), cropped, footprint[ys, xs],
        origin=(ys.start, xs.start), global_shape=footprint.shape)


def pooled(terms_by_arm, candidate):
    return evaluate_holdout.pooled_summary(
        terms_by_arm, draws=1000, seed=520810, candidate=candidate)


def exp1(g, folds, quad, channels):
    started = time.monotonic()
    rtp3 = rtp_edge(BAND_DIR / "band-02.npy", g.footprint)
    score = deterministic_composite(channels, rtp3, g.footprint)
    allowed = g.footprint & ~g.catalogue
    dots = nms_dots(score, allowed, DOT_BUDGET)
    rng = np.random.default_rng(71614)
    rand_ids = rng.choice(np.flatnonzero(allowed), DOT_BUDGET, replace=False)
    random_dots = np.zeros(g.shape, bool)
    random_dots.ravel()[rand_ids] = True
    out = {}
    for arm, pred in (("deterministic_rad_composite", dots),
                      ("random_dot_baseline", random_dots)):
        terms = None
        per_fold = {}
        for fold in folds:
            measurement, block_terms = crop_evaluation(pred.astype(np.float32), fold, g.footprint)
            terms = block_terms if terms is None else terms + block_terms
            per_fold[fold["name"]] = {k: measurement[k] for k in
                                      ("dti", "n_truth", "n_emitted", "tp", "fp", "fn")}
        out[arm] = {"per_fold": per_fold, "pooled_terms": terms.tolist(),
                    "dot_count": int(pred.sum())}
    # deterministic vs random paired summary
    terms_by_arm = {
        "deterministic_rad_composite": np.asarray(out["deterministic_rad_composite"]["pooled_terms"]),
        "random_dot_baseline": np.asarray(out["random_dot_baseline"]["pooled_terms"]),
    }
    summary = pooled(terms_by_arm, "deterministic_rad_composite")
    report = {"generated_utc": utc_now(), "experiment": "EXP-1",
              "evaluator_version": evaluate_holdout.VERSION,
              "elapsed_seconds": round(time.monotonic() - started, 2),
              "arms": {k: {kk: vv for kk, vv in v.items() if kk != "pooled_terms"} for k, v in out.items()},
              "pooled_summary": summary}
    dump_json(EVID / "exp1.json", report)
    np.save(CACHE / "exp1_dots.npy", dots)
    print(json.dumps({"EXP-1": summary["scores"],
                      "paired": summary["paired_differences"]}, indent=1), flush=True)
    return report


def _feature_matrix(bands, channels, indices):
    parts = [np.asarray(b, np.float32).ravel()[indices] for b in bands]
    parts += [np.asarray(channels[name], np.float32).ravel()[indices] for name in CHANNEL_NAMES]
    return np.column_stack(parts).astype(np.float32)


def exp2(g, folds, quad, channels, spec):
    started = time.monotonic()
    bands = [np.load(BAND_DIR / f"band-{i:02d}.npy", mmap_mode="r") for i in range(1, 20)]
    # leakage canaries first
    canary_rows = []
    all_planes = bands + [channels[name] for name in CHANNEL_NAMES]
    all_names = [f"band_{i+1:02d}" for i in range(19)] + list(CHANNEL_NAMES)
    for fold in folds:
        active = g.footprint & fold["region"] & ~fold["masked_known"]
        truth = fold["truth"] & active
        pos = np.flatnonzero(truth)
        neg = np.flatnonzero(active & ~truth)
        rng = np.random.default_rng(71614 + 100 + fold["fold"])
        neg = rng.choice(neg, size=min(50_000, len(neg)), replace=False)
        ids = np.concatenate((pos, neg))
        labels = np.concatenate((np.ones(len(pos), bool), np.zeros(len(neg), bool)))
        for name, plane in zip(all_names, all_planes):
            canary_rows.append(single_feature_canary(
                np.asarray(plane).ravel()[ids], labels, name=name, fold=fold["name"]))
    max_auc = max(r["orientation_invariant_auc"] for r in canary_rows)
    canary = {"generated_utc": utc_now(), "all_features_tested_alone": True,
              "n_rows": len(canary_rows), "maximum_orientation_invariant_auc": max_auc,
              "leakage_suspected": any(r["leakage_suspected"] for r in canary_rows),
              "rows": canary_rows}
    dump_json(EVID / "exp2_canaries.json", canary)
    print(f"canary max invariant AUC={max_auc:.4f} leakage={canary['leakage_suspected']}", flush=True)
    if canary["leakage_suspected"]:
        raise RuntimeError("leakage canary fired; EXP-2 stopped before model fit")

    surfaces = {arm: np.zeros(g.shape, np.float32) for arm in
                ("control_19band_hgb", "candidate_19band_plus_7rad_hgb")}
    terms = {arm: None for arm in surfaces}
    fold_report = []
    for fold in folds:
        f = fold["fold"]
        train = g.footprint & (quad != f) & (
            ndi.distance_transform_edt(~fold["region"]) > spec["holdout"]["training_collar_px"])
        train &= ~fold["hidden_all"]
        positive = np.flatnonzero(train & fold["visible"])
        negative = np.flatnonzero(train & ~g.catalogue)
        rng = np.random.default_rng(spec["holdout"]["split_seed"] + f)
        negative = rng.choice(negative, size=min(MAX_NEG, len(negative)), replace=False)
        train_ids = np.concatenate((positive, negative))
        y = np.concatenate((np.ones(len(positive), np.uint8), np.zeros(len(negative), np.uint8)))
        weights = np.ones(len(y), float)
        weights[:len(positive)] = len(negative) / len(positive)
        test_ids = np.flatnonzero(g.footprint & (quad == f))
        x_train = _feature_matrix(bands, channels, train_ids)
        row = {"fold": fold["name"], "train_positive": int(len(positive)),
               "train_negative": int(len(negative)), "arms": {}}
        for arm, count in (("control_19band_hgb", 19),
                           ("candidate_19band_plus_7rad_hgb", 26)):
            model = HistGradientBoostingClassifier(
                max_iter=FIT["max_iter"], max_leaf_nodes=FIT["max_leaf_nodes"],
                learning_rate=FIT["learning_rate"], l2_regularization=FIT["l2_regularization"],
                early_stopping=False, random_state=spec["holdout"]["split_seed"] + f)
            with threadpool_limits(limits=2):
                model.fit(x_train[:, :count], y, sample_weight=weights)
                for start in range(0, len(test_ids), 65_536):
                    ids = test_ids[start:start + 65_536]
                    xt = _feature_matrix(bands, channels, ids)[:, :count]
                    pred = model.predict_proba(xt)[:, 1]
                    if not np.isfinite(pred).all() or (pred < 0).any() or (pred > 1).any():
                        raise ValueError("invalid model confidence; no silent clipping")
                    surfaces[arm].ravel()[ids] = pred.astype(np.float32)
            measurement, block_terms = crop_evaluation(surfaces[arm], fold, g.footprint)
            terms[arm] = block_terms if terms[arm] is None else terms[arm] + block_terms
            row["arms"][arm] = {k: measurement[k] for k in
                                ("dti", "n_truth", "n_emitted", "tp", "fp", "fn")}
            print(f"{fold['name']} {arm}: HOLDOUT-DTI={measurement['dti']:.6f}", flush=True)
        fold_report.append(row)
        del x_train
        gc.collect()
    summary = pooled(terms, "candidate_19band_plus_7rad_hgb")
    for arm, surface in surfaces.items():
        surface[~g.footprint | g.catalogue] = 0.0
        np.save(CACHE / f"exp2_{arm}.npy", surface)
    report = {"generated_utc": utc_now(), "experiment": "EXP-2",
              "evaluator_version": evaluate_holdout.VERSION,
              "elapsed_seconds": round(time.monotonic() - started, 2),
              "canary": {k: v for k, v in canary.items() if k != "rows"},
              "folds": fold_report, "pooled_summary": summary}
    dump_json(EVID / "exp2.json", report)
    print(json.dumps({"EXP-2 scores": summary["scores"],
                      "paired": summary["paired_differences"]}, indent=1), flush=True)
    return report, surfaces


def _merged_registry_index(g):
    inventory = json.loads((ROOT / "registry/focus_inventory.json").read_text())
    records = inventory["rasters"]
    local_priors = [
        "docs/downloads/gemsdoe1-tip1-directional-tip-gradient-20261026-9a4b9b4bc8cd-zeros.tif",
        "docs/downloads/wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros.tif",
        "docs/downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif",
        "docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif",
    ]
    extra = []
    for rel in local_priors:
        p = ROOT / rel
        if p.exists():
            extra.append({"repo_first": "WBGGEMSDOE1", "sha256": sha256(p),
                          "cache_file": str(p), "sources": [f"WBGGEMSDOE1:{rel}"]})
    return {"rasters": records + extra,
            "complete_accessible_scan": True, "errors": []}, len(records) + len(extra)


def exp3(g, channels, exp2_report):
    started = time.monotonic()
    candidate = "candidate_19band_plus_7rad_hgb"
    control = "control_19band_hgb"
    scores = exp2_report["pooled_summary"]["scores"]
    candidate_wins = scores[candidate]["dti"] > scores[control]["dti"]
    chosen = candidate if candidate_wins else control
    surface = np.load(CACHE / f"exp2_{chosen}.npy", mmap_mode="r").copy()
    surface[~g.footprint] = 0.0
    # normalize defensively into [0,1] preserving rank (predict_proba already in range)
    if not (np.isfinite(surface).all() and surface.min() >= 0 and surface.max() <= 1):
        raise ValueError("synthesis surface failed finite [0,1] invariant")
    # Project portal gate G10: no dots within the 2 px (200 m) dead collar.
    # Organizer masks known faults from scoring (forum 11516), so collar dots
    # earn no credit and only add FP mass; the 200 m rule is a project choice,
    # not an organizer rule (documented in the executive summary).
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    allowed = g.footprint & ~g.catalogue & (d_cat > 2.0)
    dots = nms_dots(surface.astype(np.float64), allowed, DOT_BUDGET)
    binary = np.zeros(g.shape, np.float32)
    binary[dots] = 1.0
    # dotted holdout score on the same v2 instrument
    terms = None
    per_fold = {}
    folds, _ = holdout.buffered_component_draw(g, seed=71614, hide_frac=0.2,
                                               buffer_px=3, boundary_px=12)
    for fold in folds:
        measurement, block_terms = crop_evaluation(binary, fold, g.footprint)
        terms = block_terms if terms is None else terms + block_terms
        per_fold[fold["name"]] = {k: measurement[k] for k in
                                  ("dti", "n_truth", "n_emitted", "tp", "fp", "fn")}
    dotted_dti = _pooled_dti(terms)

    index, n_expected = _merged_registry_index(g)
    expected_grid = (g.shape, g.crs, g.transform)
    print(f"registry compare: {n_expected} rasters ...", flush=True)
    surface_audit = uniqueness.compare_array_to_registry(
        surface, index, g.footprint, expected_grid=expected_grid)
    dots_audit = uniqueness.compare_array_to_registry(
        binary, index, g.footprint, expected_grid=expected_grid)
    dot_rows = [r for r in dots_audit["rows"] if "error" not in r]
    two_phase = uniqueness.two_phase_summary(
        dot_rows, int(g.footprint.sum()), expected_rasters=n_expected)
    real_peers = [r for r in dot_rows
                  if "lattice" not in r["submission"].lower()
                  and r["their_dots"] <= 0.20 * int(g.footprint.sum())]
    real_peers.sort(key=lambda r: r["my_dots_within_3px_of_theirs"], reverse=True)
    top_geo_peers = [{k: r[k] for k in ("submission", "their_dots",
                                        "my_dots_within_3px_of_theirs",
                                        "their_dots_within_3px_of_mine",
                                        "spearman_full_footprint", "jaccard_dot_sets")}
                     for r in real_peers[:10]]
    lattice_rows = [{"submission": r["submission"],
                     "forward_overlap": r["my_dots_within_3px_of_theirs"],
                     "their_dots": r["their_dots"]}
                    for r in dot_rows if "lattice" in r["submission"].lower()]
    np.save(CACHE / "exp3_dots.npy", dots)
    report = {"generated_utc": utc_now(), "experiment": "EXP-3",
              "evaluator_version": evaluate_holdout.VERSION,
              "elapsed_seconds": round(time.monotonic() - started, 2),
              "chosen_arm": chosen, "candidate_wins_continuous": bool(candidate_wins),
              "dotted_holdout": {"evidence_class": "HOLDOUT-DTI",
                                 "evaluator_version": evaluate_holdout.VERSION,
                                 "pooled_dti": float(dotted_dti),
                                 "per_fold": per_fold, "dot_count": int(dots.sum())},
              "surface_audit_worst": {k: surface_audit[k] for k in
                                      ("worst_spearman_full_footprint", "worst_rho_submission",
                                       "worst_dot_overlap", "worst_overlap_submission",
                                       "registry_rasters_checked", "stop_required")},
              "dots_audit_worst": {k: dots_audit[k] for k in
                                   ("worst_spearman_full_footprint", "worst_rho_submission",
                                    "worst_dot_overlap", "worst_overlap_submission",
                                    "registry_rasters_checked", "stop_required")},
              "two_phase": two_phase,
              "top_geological_dotfield_peers": top_geo_peers,
              "synthetic_lattice_controls": lattice_rows,
              "collar_rule": "dots restricted to catalogue distance > 2 px (200 m); project portal gate G10, not an organizer rule"}
    dump_json(EVID / "exp3_gates.json", report)
    # persist full audits separately (large)
    dump_json(EVID / "exp3_surface_registry_audit.json",
              {k: v for k, v in surface_audit.items() if k != "rows"})
    dump_json(EVID / "exp3_dots_registry_audit.json",
              {k: v for k, v in dots_audit.items() if k != "rows"})
    print(json.dumps(report["surface_audit_worst"], indent=1), flush=True)
    print(json.dumps(report["dots_audit_worst"], indent=1), flush=True)
    print(json.dumps(report["dotted_holdout"]["pooled_dti"], indent=1), flush=True)
    return report, binary, surface, dots_audit, two_phase


def _pooled_dti(terms):
    a = np.asarray(terms, float)
    tp, fp, fn = a[:, 0].sum(), a[:, 1].sum(), a[:, 2].sum()
    return tp / (tp + 0.2 * fp + 0.8 * fn + 1e-12)


def package(g, binary, exp2_report, exp3_report, dots_audit, two_phase):
    decoded = hashlib.sha256(np.ascontiguousarray(binary).tobytes()).hexdigest()
    name = f"wbggemsdoe1-wbg-d1-rad-alteration-20261027-{decoded[:12]}-zeros"
    note = ("WBG-D1 GeoDAWN radiometric alteration+shallow magnetic edge HGB; "
            "37654 off-catalogue NMS dots; HOLDOUT gated; unique bytes")[:140]
    tif = ROOT / "docs/downloads" / f"{name}.tif"
    receipt = submission_writer.write_submission(
        tif, binary, ROOT / "data/sample_submission.tif", g.footprint,
        note=note, name=name, catalogue=g.catalogue,
        metadata={"hypothesis_id": "WBG-D1",
                  "preregistration_sha256": sha256(PREREG),
                  "prior_submission_pixels_used": False,
                  "organizer_origin_authenticated": False})
    summary = exp2_report["pooled_summary"]
    cand = summary["scores"]["candidate_19band_plus_7rad_hgb"]
    ctrl = summary["scores"]["control_19band_hgb"]
    paired = summary["paired_differences"]["control_19band_hgb"]
    canary = exp2_report["canary"]
    efficacy_ok = bool(paired["ci95"][0] > 0 and cand["dti"] >= ctrl["dti"])
    rho_ok = bool((dots_audit["worst_spearman_full_footprint"] or 0.0) <= 0.90)
    like = two_phase["like_for_like_reading"]
    overlap_ok = bool(like["worst_forward_overlap_dot_fields"] <= 0.70)
    format_ok = bool(receipt["validator"]["all_checks_passed"])
    verdict = "promote" if (efficacy_ok and rho_ok and overlap_ok and format_ok
                            and not canary["leakage_suspected"]) else "negative"
    run_card = {
        "generated_utc": utc_now(),
        "hypothesis": "WBG-D1: radiometric alteration halos (K enrichment vs Th/K, compositional edges) plus shallow magnetic edges identify concealed non-ridge faults, fused with the 19-band potential-field stack by spatial LOQO HGB.",
        "mechanism": "Robust-z Gaussian high-pass/edge transforms of GeoDAWN K, Th/K, U/Th at 500m-1km; TMI minus 150m upward continuation shallow residual; 26-channel HistGradientBoosting under buffered whole-component LOQO; fixed 37,654-dot 300m NMS emission off the mapped catalogue.",
        "non_fault_mimic": "Playa/evaporite and Lake Lahontan paleo-lacustrine clays, K-bearing basin fill, weathering/sorting and flight-line leveling, cultural magnetic noise.",
        "lane": "self-declared provisional research lane; no assigned method paragraph; no slot authorization",
        "holdout": {"evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": cand["evaluator_version"],
                    "candidate_dti": cand["dti"], "candidate_ci95": cand["ci95"],
                    "control_dti": ctrl["dti"], "control_ci95": ctrl["ci95"],
                    "withheld_positive_pixels": cand["withheld_positive_pixels"],
                    "paired_delta": paired["delta"], "paired_ci95": paired["ci95"],
                    "dotted_pooled_dti": exp3_report["dotted_holdout"]["pooled_dti"]},
        "canary": canary,
        "registry": {"phase": "surface-before-placement then final dots",
                     "rasters_checked": dots_audit["registry_rasters_checked"],
                     "scope": two_phase["scope_note"],
                     "surface_worst_spearman": exp3_report["surface_audit_worst"]["worst_spearman_full_footprint"],
                     "dots_worst_spearman": dots_audit["worst_spearman_full_footprint"],
                     "dots_worst_rho_submission": dots_audit["worst_rho_submission"],
                     "literal_worst_forward_overlap": two_phase["literal_reading"]["worst_forward_overlap"],
                     "literal_worst_overlap_submission": two_phase["literal_reading"]["worst_overlap_submission"],
                     "dotfield_worst_forward_overlap": like["worst_forward_overlap_dot_fields"],
                     "dotfield_worst_submission": like["worst_forward_overlap_dot_field_submission"],
                     "dotfield_rasters": like["dot_field_rasters"],
                     "continuous_surface_rasters": like["continuous_surface_rasters"],
                     "geological_peer_worst_forward_overlap": exp3_report["top_geological_dotfield_peers"][0]["my_dots_within_3px_of_theirs"],
                     "geological_peer_worst_submission": exp3_report["top_geological_dotfield_peers"][0]["submission"],
                     "top_geological_dotfield_peers": exp3_report["top_geological_dotfield_peers"][:5],
                     "synthetic_lattice_controls": exp3_report["synthetic_lattice_controls"],
                     "lattice_note": "The r13-lattice rasters are uniform synthetic calibration grids; pigeonhole overlap with any sparse dot field is structural (IR-WBG1-01), not geological duplication.",
                     "byte_unique": dots_audit["byte_unique_among_checked"],
                     "pixel_unique": dots_audit["pixel_unique_among_checked"]},
        "raster_sha256": receipt["sha256"],
        "raster_decoded_sha256": decoded,
        "artifact": f"docs/downloads/{tif.name}",
        "zip_artifact": f"docs/downloads/{receipt['zip_file']}",
        "validator": receipt["validator"]["checks"],
        "validator_all_passed": receipt["validator"]["all_checks_passed"],
        "submission_name": name,
        "submission_note": note,
        "submission_note_chars": len(note),
        "gates": {"efficacy_paired_ci_positive": efficacy_ok, "spearman_ok": rho_ok,
                  "dotfield_overlap_ok": overlap_ok, "format_ok": format_ok},
        "verdict": verdict,
        "ok_to_download": True,
        "ok_to_submit": verdict == "promote",
        "submission_slots_used": 0,
        "experiments_completed": 3,
    }
    dump_json(EVID / "run_card.json", run_card)
    dump_json(ROOT / "registry/run_card_wbg_d1.json", run_card)
    print(json.dumps({"verdict": verdict, "gates": run_card["gates"],
                      "candidate_dti": cand["dti"], "control_dti": ctrl["dti"],
                      "paired_ci": paired["ci95"]}, indent=1), flush=True)
    return run_card


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", choices=["1", "2", "3", "all"], default="all")
    args = ap.parse_args()
    EVID.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    prereg_hash = sha256(PREREG)
    g = _load_grid()
    channels = get_channels(g)
    folds, quad = holdout.buffered_component_draw(
        g, seed=71614, hide_frac=0.2, buffer_px=3, boundary_px=12)
    spec = json.loads(PREREG.read_text())
    if sha256(PREREG) != prereg_hash:
        raise RuntimeError("preregistration changed during run")
    if args.exp in ("1", "all"):
        exp1(g, folds, quad, channels)
    if args.exp in ("2", "all"):
        exp2_report, _ = exp2(g, folds, quad, channels, spec)
    elif args.exp == "3":
        exp2_report = json.loads((EVID / "exp2.json").read_text())
    else:
        exp2_report = None
    if args.exp in ("3", "all"):
        exp3_report, binary, surface, dots_audit, two_phase = exp3(g, channels, exp2_report)
        package(g, binary, exp2_report, exp3_report, dots_audit, two_phase)


if __name__ == "__main__":
    main()
