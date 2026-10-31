#!/usr/bin/env python3
"""Generate the 31 Oct 2026 research GeoTIFF from the E2 method (fold-safe lane).

Method (identical to the holdout experiment E2, applied to the FULL visible catalogue):
  1. Features: the 19 cached training bands (footprint only, NaN -> median, z-scored).
  2. Model: HistGradientBoostingClassifier, positives = mapped catalogue pixels,
     negatives = footprint pixels > 3 px from any mapped pixel (200k sample).
  3. Allowed cells: footprint minus mapped catalogue (no dot on a known trace).
  4. Budget: K = 0.2 x mapped-catalogue pixels (= 12,198). Holdout-consistent (the protocol hides
     20 % of the catalogue) and within 2 % of the repo's previously measured hidden size (12,395).
     K is an ASSUMPTION carried from the protocol, not an organizer value.
  5. Emission: shared exact-marginal greedy allocator (vendor/gems57/emit.py).
  6. Write through the shared fail-closed writer (vendor/gems57/submission_writer.py):
     float32, EPSG:32611, 3730x3292, transform pinned, zeros outside footprint, values in {0,1}.
  7. Gates: template format check, shared local validator, shared registry uniqueness
     (118 owner-reported GitHub rasters, literal Spearman > 0.90 and 3-px overlap > 0.70).

Nothing here uploads anything. Verdicts are written by the run card, not by this script.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import emit as EM  # noqa: E402
from gems57 import grid as GR  # noqa: E402
from gems57 import gates as GT  # noqa: E402
from gems57 import uniqueness as UQ  # noqa: E402
from gems57 import submission_writer as SW  # noqa: E402
from gems57.validate import validate  # noqa: E402

from fold_safe_lane_20261031 import calibrate_to_budget, load_grid_and_bands  # noqa: E402

NAME = "wbggemsdoe1-fs-hgbvisible-greedy-k12198-20261031"
NOTE = "RESEARCH ONLY, do not submit. Fold-safe HGB + greedy dots; holdout DTI 0.0536 < uniform null 0.0646."
OUT_TIF = ROOT / "docs/downloads" / f"{NAME}.tif"
RUN_CARD = ROOT / "evidence/fold_safe_20261031/final_run_card_20261031.json"
INDEX = ROOT / "evidence/uniqueness/registry_index_20261031.json"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    t0 = time.time()
    grid, names, fp_idx, X = load_grid_and_bands()
    fp, cat = grid.footprint, grid.catalogue
    rng = np.random.default_rng(20261031)
    dil = ndi.binary_dilation(cat, iterations=3)
    pos = np.flatnonzero(cat[fp])
    neg_pool = np.flatnonzero(~dil[fp])
    neg = rng.choice(neg_pool, size=min(200_000, neg_pool.size), replace=False)
    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, max_leaf_nodes=31,
                                           l2_regularization=1.0, random_state=0)
    model.fit(X[idx], y)
    prob_fp = model.predict_proba(X)[:, 1].astype(np.float32)
    prob = np.zeros(fp.shape, np.float32)
    prob[fp] = prob_fp
    allowed = fp & ~cat
    k_truth = 0.2 * float(cat.sum())
    pc = calibrate_to_budget(prob, allowed, k_truth)
    alloc = EM.greedy_allocate(pc, allowed, k_truth=k_truth)
    emitted = np.asarray(alloc.emitted, bool) & allowed
    pred = emitted.astype(np.float32)
    print(f"[alloc] dots={int(emitted.sum())} K={k_truth:.1f} on_catalogue={int((emitted & cat).sum())} "
          f"elapsed={time.time()-t0:.0f}s", flush=True)

    OUT_TIF.parent.mkdir(parents=True, exist_ok=True)
    receipt = SW.write_submission(
        OUT_TIF, pred, SAMPLE, fp, note=NOTE, name=NAME, catalogue=cat,
        metadata=dict(method="E2 fold-safe HGB (19 bands) + greedy exact-marginal allocation",
                      k_truth_assumed=k_truth, dots=int(emitted.sum()),
                      holdout_receipt="evidence/fold_safe_20261031/E2-hgb-visible-only.json"))
    tif_sha = sha256(OUT_TIF)
    with rasterio.open(OUT_TIF) as ds:
        grid_ok = (ds.count, ds.dtypes[0], ds.height, ds.width, str(ds.crs), tuple(ds.transform)[:6])
    fmt = GT.format_report(OUT_TIF, SAMPLE, footprint=fp)
    local = validate(OUT_TIF, fp, cat)

    index = json.loads(INDEX.read_text())
    uq = UQ.compare_to_registry(OUT_TIF, index, fp,
                                expected_grid=(fp.shape, grid.crs, grid.transform))
    rows = [r for r in uq.get("rows", []) if "error" not in r] if isinstance(uq, dict) else []
    worst_rho = max((r["spearman_full_footprint"] for r in rows if r.get("spearman_full_footprint") is not None), default=None)
    worst_ov = max((r["my_dots_within_3px_of_theirs"] for r in rows), default=None)
    worst_row = max(rows, key=lambda r: r["my_dots_within_3px_of_theirs"]) if rows else {}
    run_card = dict(
        schema="unique-candidate-run-card-v2",
        name=NAME,
        note=NOTE,
        note_chars=len(NOTE),
        hypothesis=("Mapped faults are a sample of a larger fault population; a gradient-boosted "
                    "classifier on the 19 measured geophysical bands, trained only on mapped faults "
                    "(never on hidden or own predictions), ranks off-catalogue cells where unmapped "
                    "fault-like signatures occur."),
        mechanism=("Band-space similarity to mapped-fault pixels, greedy exact-marginal dot emission "
                   "under the DTI bar with K = 0.2 x mapped pixels."),
        named_non_fault_mimic=("Lithologic contacts, dike margins, and alluvial-fan edges with magnetic or "
                               "gravity contrasts parallel to mapped traces; survey-line artefacts."),
        holdout=dict(
            evidence_class="HOLDOUT-DTI",
            evaluator_version="gems57-pooled-hide-v2",
            experiment="E2-hgb-visible-only",
            dti=0.053605608273793175, ci95=[0.04586326736637219, 0.06144478396769219],
            withheld_positive_pixels=22893,
            uniform_null_dti=0.0645836331358035, uniform_null_ci95=[0.056569198223278036, 0.07238565503364346],
            proximity_null_dti=0.04886389958804631,
            verdict_vs_uniform_null="FAILS: candidate below matched-budget uniform null (paired delta -0.0110, CI [-0.0182, -0.0035])",
            benchmark_to_beat="HOLDOUT-DTI 0.166060 (GEMSDOE24 S3DEP1, from docs/wbg5 record; not re-measured here)"),
        leakage_canary=dict(evidence_class="LEAKAGE-CANARY", threshold=0.90,
                            max_direction_free_auc=0.799, top_feature="dist_to_visible_catalogue",
                            pass_=True, source="evidence/fold_safe_20261031/E2-hgb-visible-only.json"),
        registry_comparison=dict(
            registry_rasters_expected=index["n_entries"],
            registry_rasters_checked=len(rows),
            complete_accessible_scan=bool(uq.get("complete_accessible_scan")) if isinstance(uq, dict) else None,
            worst_spearman_full_footprint=worst_rho,
            worst_forward_3px_overlap=worst_ov,
            worst_overlap_vs=worst_row.get("submission"),
            byte_identical_any=any(r.get("identical_bytes") for r in rows),
            decoded_identical_any=any(r.get("identical_decoded_predictions") for r in rows),
            literal_gate_rho_limit=0.90, literal_gate_overlap_limit=0.70,
            summary={k: v for k, v in uq.items() if k != "rows"} if isinstance(uq, dict) else None,
        ),
        raster=dict(path=str(OUT_TIF.relative_to(ROOT)), sha256=tif_sha, bytes=OUT_TIF.stat().st_size,
                    dots=int(emitted.sum()), values="{0,1} float32, zeros outside footprint",
                    crs_shape_transform=grid_ok),
        validator=dict(template_format_ok=bool(fmt.get("ok")), template_problems=fmt.get("problems"),
                       local_all_checks_passed=bool(local["all_checks_passed"]),
                       local_checks=local["checks"], min=local["min"], max=local["max"],
                       n_nan=local["n_nan"], n_infinite=local["n_infinite"],
                       on_catalogue_positive_pixels=local.get("on_catalogue_positive_pixels")),
        organizer_confirmed_score=None,
        leaderboard_estimate="UNAVAILABLE: no organizer receipt; holdout does not rank registry files",
        gates=dict(
            G1_format=bool(fmt.get("ok")) and bool(local["all_checks_passed"]),
            G2_exact_copy_free=not any(r.get("identical_bytes") or r.get("identical_decoded_predictions") for r in rows),
            G3_rank_correlation_lt_0p90=(worst_rho is not None and worst_rho <= 0.90),
            G4_literal_overlap_lt_0p70=(worst_ov is not None and worst_ov <= 0.70),
            G5_leakage_canary_le_0p90=True,
            G6_holdout_beats_uniform_null=False),
        ok_to_download=True,
        ok_to_submit=False,
        verdict="DOWNLOAD: YES (research/learning only) - SUBMIT: NO",
        status_reason=("Fails G4 (literal 70% overlap) and G6 (holdout below matched uniform null). "
                       "Local format is valid. No slot used."),
        submission_slots_used=0,
        elapsed_s=round(time.time() - t0, 1),
        writer_receipt_sha256=sha256(OUT_TIF.with_suffix(".json")) if OUT_TIF.with_suffix(".json").exists() else None,
        writer_status=receipt.get("status"),
    )
    RUN_CARD.parent.mkdir(parents=True, exist_ok=True)
    RUN_CARD.write_text(json.dumps(run_card, indent=2, allow_nan=False, default=str) + "\n")
    print(json.dumps(dict(tif=str(OUT_TIF.relative_to(ROOT)), sha256=tif_sha, dots=int(emitted.sum()),
                          format_ok=run_card["gates"]["G1_format"], worst_rho=worst_rho,
                          worst_overlap=worst_ov, worst_overlap_vs=worst_row.get("submission"),
                          gates=run_card["gates"]), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
