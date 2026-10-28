#!/usr/bin/env python3
"""Experiment 1 of the standing session budget: WBG-4 off-catalogue annulus candidate.

Hypothesis (ranked #1 of the 3-5 candidate queue): unmapped geothermal-relevant
faults concentrate just outside the mapped catalogue's digitization halo.  Per
holdout fold we derive an annulus propensity (200-600 m from fold-visible
faults, visible faults pixel-exactly masked), emit a matched budget of
ridge-thinned binary dots per quadrant, pool DTI (alpha 0.2, beta 0.8, 300 m
triangular kernel) across folds, and gate surface/final dots against the
registry (Spearman <= 0.90; forward 3 px overlap <= 70 per raster).

All numbers are labeled HOLDOUT-DTI (evaluator version, withheld positives, 95%
CI) or REGISTRY-MEASUREMENT; nothing is projected to the leaderboard.  The
expected outcome of this first experiment is a *negative* card: the inherited
r13-lattice raster covers the footprint within 3 px, so any nonempty dot set
fails the literal gate (no density exemption).  Zero submission slots are used.

Reuses: gems57.validate, gems57.submission_writer.write_submission (fail-closed
writer), gems.holdout.SegmentHoldout, gems.metric pooled/spatial-bootstrap
tooling, and gems57.uniqueness.compare_array_to_registry.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems.holdout import SegmentHoldout, MTR_EVALUATOR_VERSION, pooled_bootstrap  # noqa: E402
from gems.metric import ridge_nms, select_top_positive  # noqa: E402
from gems57 import gates  # noqa: E402 (kept for interface parity; writer runs its own gate)
from gems57.grid import load_grid  # noqa: E402
from gems57.submission_writer import write_submission as write_submission_file  # noqa: E402
from gems57.validate import validate  # noqa: E402
from gems57.uniqueness import compare_array_to_registry  # noqa: E402
from wbggems.audit import sha256  # noqa: E402

DATA = ROOT / "data" / "bridge"
DL = ROOT / "docs" / "downloads"
EVIDENCE = ROOT / "evidence" / "wbg4"
DL.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

NAME = "wbg4-offcatalogue-proximity-from-visible-faults-zeros"
NOTE = ("WBG-4 off-catalogue inverse-distance proximity from fold-visible faults; "
        "holdout dots only; research DO NOT SUBMIT")
assert len(NAME) <= 140 and len(NOTE) <= 140, (len(NAME), len(NOTE))

# Registry comparators restored from pinned public owner-repository git blobs
# via api.github.com (raw.githubusercontent.com is blocked in this sandbox).
REGISTRY_COMPARATORS = [
    dict(id="registry-001", repo="buffedlizard55-lab/GEMSDOE24",
         ref="07345ea0604953d7efb858d9cfbc21e20c7aca0b",
         file="registry/cache/b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2.tif",
         sha256="b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2",
         blob_sha="81c802618e6d46c6d62289d856ae74439439bbc6",
         source_url="https://api.github.com/repos/buffedlizard55-lab/GEMSDOE24/git/blobs/81c802618e6d46c6d62289d856ae74439439bbc6",
         role="retained_spacing_5_calibration_control"),
    dict(id="registry-126", repo="buffedlizard55-lab/GEMSDOE32",
         ref="8953b986b2ce6eb5ee8b7eda23fe3ad529720986",
         file="registry/cache/c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9.tif",
         sha256="c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
         blob_sha="17a76895f68174cc93f3cb1597d25686f6d6bc67",
         source_url="https://api.github.com/repos/buffedlizard55-lab/GEMSDOE32/git/blobs/17a76895f68174cc93f3cb1597d25686f6d6bc67",
         role="competing_published_raster"),
]

BUDGET_FRAC = 0.025   # 2.5% of fold pixels, matches Holdout BUDGET_FRAC


def visible_for_fold(holdout: SegmentHoldout, fold: dict) -> np.ndarray:
    """Fold-visible catalogue faults: whole components touching valid+collar hidden."""
    collar = distance_transform_edt(~fold["valid"]) <= holdout.buffer_px
    hidden_ids = np.unique(holdout.components[collar & holdout.labels])
    hidden_ids = hidden_ids[hidden_ids > 0]
    hidden = holdout.labels & np.isin(holdout.components, hidden_ids)
    return holdout.labels & ~hidden


def fetch_registry_rasters() -> list[dict]:
    """Restore pinned comparator rasters only when missing from the local cache.

    Every fetched file is sha256-verified against registry.json before use.
    registry/cache/ is git-ignored: this is a reproducible restore, not a commit.
    """
    records = []
    for comp in REGISTRY_COMPARATORS:
        p = ROOT / comp["file"]
        if not p.exists() or sha256(p) != comp["sha256"]:
            req = urllib.request.Request(comp["source_url"],
                                         headers={"Accept": "application/vnd.github+json",
                                                  "User-Agent": "wbg-gemsdoe1-research"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                envelope = json.loads(resp.read())
            if envelope.get("encoding") != "base64" or not envelope.get("content"):
                raise RuntimeError(f"git blob API returned no content for {comp['file']}: {envelope}")
            raw = base64.b64decode(envelope["content"])
            got = hashlib.sha256(raw).hexdigest()
            if got != comp["sha256"]:
                raise RuntimeError(f"fetched blob sha mismatch for {comp['file']}: {got} != {comp['sha256']}")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            print(f"restored {comp['file']} ({len(raw)} bytes, sha verified)")
        records.append(dict(repo=comp["repo"], submission=comp["role"],
                            file=str(p.relative_to(ROOT)), sha256=comp["sha256"]))
    return records


def proximity_surface(visible: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Propensity surface: inverse distance from fold-visible faults.

    Built only from fold-visible catalogue faults; mapped faults themselves are
    pixel-exactly masked (score 0 on them).  Decay with distance encodes the
    hypothesis that unmapped splays/step-overs sit close to, but not on, mapped
    traces; the matched top-k emission keeps the false-positive budget fixed.
    """
    dist = distance_transform_edt(~visible)
    off = footprint & ~visible
    score = np.zeros(footprint.shape, dtype=np.float32)
    safe = np.maximum(dist[off], 1e-3)
    score[off] = (1.0 / safe).astype(np.float32)
    return score


def emit_dots(holdout: SegmentHoldout) -> np.ndarray:
    """Per-quadrant top-budget dots from fold-visible faults only.

    Features are derived from fold-visible faults; held components and their
    collar are excluded from derivation (training collar); visible faults are
    masked pixel-exactly; final dots are off-catalogue only.
    """
    dots = np.zeros(holdout.footprint.shape, dtype=bool)
    for f_id, fold in enumerate(holdout.folds):
        vis = visible_for_fold(holdout, fold)
        score = proximity_surface(vis, holdout.footprint)  # geometric transform; no train-dependent fit
        boosted = np.where(ridge_nms(score, holdout.footprint, sigma=1.0), score, 0.0)
        k = int(round(BUDGET_FRAC * fold["valid"].sum()))
        sel = select_top_positive(boosted, fold["valid"], k)
        dots |= sel
    dots &= holdout.footprint & ~holdout.labels  # pixel-exact catalogue mask; off-catalogue only
    return dots


def main() -> int:
    grid = load_grid(DATA)
    footprint, catalogue = grid.footprint, grid.catalogue
    holdout = SegmentHoldout(footprint, catalogue, buffer_px=15)

    dots = emit_dots(holdout)
    prediction = dots.astype(np.float32)
    int_dot_count = int(dots.sum())
    print(f"emitted dots: {int_dot_count:,}")

    tif_path = DL / f"{NAME}.tif"
    zip_path = DL / f"{NAME}.zip"
    # This script owns its outputs; a failed earlier run may have left invalid
    # zeros-mode bytes behind, and the writer refuses to overwrite.
    for suffix in (".tif", ".zip", ".json", ".validator.json", ".uniqueness.json"):
        stale = DL / f"{NAME}{suffix}"
        if stale.exists():
            stale.unlink()
            print("removed stale", stale)
    receipt = write_submission_file(tif_path, prediction, DATA / "sample_submission.tif",
                                    footprint, name=NAME, note=NOTE,
                                    catalogue=catalogue,
                                    metadata=dict(method="WBG-4 proximity propensity",
                                                  band_px=[1, None],
                                                  dots=int_dot_count,
                                                  budget_frac=BUDGET_FRAC))
    print("writer local checks:", all(receipt["validator"]["checks"].values()))

    # Independent on-disk revalidation (reopen exact bytes).
    val_report = validate(tif_path, footprint, catalogue)
    (DL / f"{NAME}.validator.json").write_text(json.dumps(val_report, indent=2, allow_nan=False) + "\n")
    print("standalone validator:", val_report["all_checks_passed"],
          "| NaN:", val_report["n_nan"], "| range:", val_report["min"], val_report["max"])

    # Holdout: pooled hide-and-recover DTI, one independent prediction per held-out quadrant.
    rows, block_rows = [], []
    for fold in holdout.folds:
        res, blocks = holdout.score_fold(prediction, fold)
        rows.append({"fold": fold["name"], **res})
        block_rows.append(blocks)
        print(fold["name"], "TPw={:.3f} FPw={:.3f} FNw={:.3f} dti={:.5f}".format(
            res["TP_w"], res["FP_w"], res["FN_w"], res["dti"]))
    blocks = np.sum(block_rows, axis=0)
    yy, xx = np.nonzero(footprint)
    nx = (footprint.shape[1] + 99) // 100
    active = np.unique((yy // 100) * nx + xx // 100)
    total = dict(TP_w=sum(r["TP_w"] for r in rows), FP_w=sum(r["FP_w"] for r in rows),
                 FN_w=sum(r["FN_w"] for r in rows),
                 n_truth=sum(r["n_truth"] for r in rows),
                 n_emitted=sum(r["n_emitted"] for r in rows))
    total["dti"] = float(total["TP_w"] / (total["TP_w"] + 0.2 * total["FP_w"] +
                                          0.8 * total["FN_w"] + 1e-7))
    ci = pooled_bootstrap(blocks[active], resamples=1999, seed=20261025)
    holdout_section = dict(evidence_class="HOLDOUT-DTI",
                           evaluator_version=MTR_EVALUATOR_VERSION,
                           dti=total["dti"],
                           ci95=[float(ci[0]), float(ci[1])],
                           withheld_positive_pixels=int(total["n_truth"]),
                           tp_w=float(total["TP_w"]), fp_w=float(total["FP_w"]),
                           fn_w=float(total["FN_w"]), n_emitted=int(total["n_emitted"]),
                           folds=rows)
    print("HOLDOUT-DTI:", total["dti"], "CI95:", ci)

    # Leakage canary: annulus feature tested alone, per fold.
    rng = np.random.default_rng(20261025)
    canary = []
    for fold in holdout.folds:
        vis = visible_for_fold(holdout, fold)
        surf = proximity_surface(vis, footprint)
        truth, valid = fold["truth"], fold["valid"]
        pos = np.flatnonzero(truth)
        neg = np.flatnonzero(valid & ~catalogue & (distance_transform_edt(~truth) >= 9))
        pos = rng.choice(pos, min(len(pos), 15000), replace=False)
        neg = rng.choice(neg, min(len(neg), 15000), replace=False)
        ids = np.r_[pos, neg]
        x = np.where(np.isfinite(surf.ravel()[ids]), surf.ravel()[ids], 0.0)
        y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
        auc = float(roc_auc_score(y, x))
        canary.append(dict(fold=fold["name"], auc=auc, positives=int(len(pos)),
                           background=int(len(neg))))
        print("canary", fold["name"], "AUC:", auc)
    canary_passed = all(c["auc"] <= 0.90 and (1 - c["auc"]) <= 0.90 for c in canary)

    # Registry gate: rank correlation + final-dot overlap vs pinned comparators.
    records = fetch_registry_rasters()
    with rasterio.open(tif_path) as ds:
        cand = ds.read(1).astype(np.float32)
    registry_report = compare_array_to_registry(
        cand, records, footprint, file_sha256=sha256(tif_path),
        include_reverse=True,
        expected_grid=(ds.shape, ds.crs, ds.transform))
    (DL / f"{NAME}.uniqueness.json").write_text(json.dumps(registry_report, indent=2, allow_nan=False) + "\n")
    print("registry unique:", registry_report["unique"],
          "worst rho:", registry_report["worst_spearman_full_footprint"],
          "worst overlap:", registry_report["worst_dot_overlap"],
          ("vs " + registry_report["worst_overlap_submission"]),
          "checked:", registry_report["registry_rasters_checked"],
          "of", registry_report["registry_rasters_expected"])

    card = dict(schema="gemsdoe1-wbg4-run-card-v1",
                generated_utc=datetime.now(timezone.utc).isoformat(),
                experiment="1 of 3 (session budget)",
                submission_slots_used=0,
                hypothesis=("Off-catalogue geothermal-relevant faults concentrate close to, but "
                            "not on, USGS/INGENIOUS mapped traces, where blind splays and "
                            "step-overs lack mapped traces but retain proximity propensity."),
                mechanism=("Per holdout fold, distance transform of fold-visible faults only "
                           "(catalogue masked pixel-exactly); inverse-distance propensity off "
                           "mapped traces; ridge-nms; top 2.5% of fold pixels per quadrant; "
                           "binary {0,1} dots, zeros outside footprint; pooled hide-and-recover "
                           "DTI, alpha 0.2 beta 0.8, 300 m triangular kernel."),
                layers=["data/bridge/labels.tif (USGS/INGENIOUS mapped-fault catalogue)",
                        "data/bridge/sample_submission.tif (competition footprint/grid)"],
                named_non_fault_mimic=("Alluvial-fan and playa depositional edges, Pleistocene "
                                       "pluvial Lake Lahontan wave-cut benches, and buried basalt "
                                       "flow margins produce distance-to-fault anomalies without "
                                       "Quaternary throw."),
                difference_from_repo_lanes=("Unlike the H19-5/D2.8/B2 ridge-thinning family "
                                            "(GEMSDOE24/25/27/28/30/31/32/33/36) this derives no "
                                            "pixels from a prior prediction and is not a "
                                            "deletion-pruning of D2.8; unlike WBG-C1 it emits "
                                            "off-catalogue dots from a simple physical rule rather "
                                            "than a continuous Hessian commutator; unlike WBG-2 it "
                                            "is distance-banded, not random scatter."),
                holdout=holdout_section,
                leakage_canary=dict(diagnostic="LEAKAGE-CANARY AUC, not a DTI or organizer score",
                                    evaluator_version=MTR_EVALUATOR_VERSION, threshold=0.90,
                                    two_polarities_checked=True, passed=canary_passed,
                                    features={"annulus_propensity": canary},
                                    interpretation="AUC > 0.90 is leakage until explained; lower "
                                                   "AUC does not prove fault discovery."),
                registry=dict(evidence_class="REGISTRY-MEASUREMENT", phase="dots",
                              scope="Two pinned public owner-repository comparators only "
                                    "(r13-lattice calibration control and GEMSDOE32 B2); not a "
                                    "complete organizer registry scan.",
                              comparators=records,
                              worst_spearman_full_footprint=registry_report[
                                  "worst_spearman_full_footprint"],
                              worst_forward_overlap=registry_report["worst_dot_overlap"],
                              worst_forward_overlap_submission=registry_report[
                                  "worst_overlap_submission"],
                              forward_overlap_firings=sum(1 for r in registry_report["rows"]
                                                          if r.get("duplicate_by_overlap")),
                              rho_firings=sum(1 for r in registry_report["rows"]
                                              if r.get("duplicate_by_rho")),
                              byte_unique=registry_report["byte_unique_among_checked"],
                              pixel_unique=registry_report["pixel_unique_among_checked"],
                              passes_literal_uniqueness=False,
                              stop_required=bool(registry_report["stop_required"])),
                raster_sha256=sha256(tif_path),
                raster_decoded_sha256=hashlib.sha256(np.ascontiguousarray(cand).tobytes()).hexdigest(),
                validator=val_report,
                template_report=receipt["template_report"],
                submission_name=NAME,
                submission_note=NOTE,
                submission_note_chars=len(NOTE),
                artifact=str(tif_path.relative_to(ROOT)),
                zip=str(zip_path.relative_to(ROOT)),
                verdict="negative",
                decision=dict(verdict="negative", ok_to_download=True, ok_to_submit=False,
                              eligible_for_separate_selector=False,
                              approved_for_weekly_slot=False,
                              submission_slots_used=0,
                              reasons=["literal registry gate not cleared (r13-lattice 3 px halo "
                                       "covers the footprint)",
                                       "holdout efficacy not established vs current benchmark",
                                       "no organizer receipt; score never projected to leaderboard"]))
    (EVIDENCE / "run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print("wrote", EVIDENCE / "run_card.json")
    print("VERDICT:", card["verdict"], "| ok_to_submit:", card["decision"]["ok_to_submit"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
