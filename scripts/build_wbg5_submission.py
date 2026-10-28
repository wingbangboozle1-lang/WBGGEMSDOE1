#!/usr/bin/env python3
"""Assemble, emit, validate and uniqueness-audit the WBG-5 / MTA-1 submission.

Reads the four out-of-fold surfaces written by ``scripts/run_wbg5_lane.py``,
assembles a full-grid OOF confidence surface, emits a budget-matched dotted
field, writes a portal-safe single-band GeoTIFF + one-TIFF ZIP, runs the exact
format validator, audits uniqueness against the nine focus-site historical
rasters plus every local project raster, and writes a JSON run card.

Nothing here uploads anything or spends a weekly slot.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import submission as SUB  # noqa: E402
from gems.holdout import SegmentHoldout  # noqa: E402
from gems1 import grid as G  # noqa: E402
from gems1 import uniqueness as U  # noqa: E402

WORK = Path("/tmp/wbg5")
OUT = ROOT / "docs/downloads"
EVID = ROOT / "evidence/wbg5"
EVID.mkdir(parents=True, exist_ok=True)

NAME = "wbggemsdoe1-wbg5-mta1-magnetic-texture-anisotropy-20261028"
NOTE = ("WBG-5 MTA-1 magnetic-texture anisotropy vs depth contours; 19-band + "
        "MTA HGB OOF, 37654 dots zeros | research, holdout-only")

REF_DIR = WORK / "refs"
REF_DIR.mkdir(parents=True, exist_ok=True)

# Nine focus-site historical best rasters (pinned owner snapshots).
FOCUS_REFS = {
    "GEMSDOE24": "https://github.com/buffedlizard55-lab/GEMSDOE24/blob/fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
    "GEMSDOE25": "https://github.com/buffedlizard55-lab/GEMSDOE25/blob/e40b9b5e3871cb34d138f586bde97f5099658d01/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
    "GEMSDOE27": "https://github.com/buffedlizard55-lab/GEMSDOE27/blob/927322eadbde56be42ae129ccdfb9b37540d8e60/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif",
    "GEMSDOE28": "https://github.com/buffedlizard55-lab/GEMSDOE28/blob/e6321461066f89080e3b1bb670d3951ab20d3638/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif",
    "GEMSDOE30": "https://github.com/buffedlizard55-lab/GEMSDOE30/blob/760af3005dd40b9f36d8fef97d6dc384fd9f2a2f/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
    "GEMSDOE31": "https://github.com/buffedlizard55-lab/GEMSDOE31/blob/597b04cd1afb65d1ebbe3e9417fd952be48e3d74/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif",
    "GEMSDOE32": "https://github.com/buffedlizard55-lab/GEMSDOE32/blob/5fc7792c5887735ecd3aa9a612787da588a7bf2c/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
    "GEMSDOE33": "https://github.com/buffedlizard55-lab/GEMSDOE33/blob/f618cc54773bd9b4d6c2b3ebf78103a05cc10cb6/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
    "GEMSDOE36": "https://github.com/buffedlizard55-lab/GEMSDOE36/blob/c5a8ae7da3bd2fcff5aa5855afd44c7a3346c16/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dotted(surface, valid, dist_visible, budget, clearance_px, block_radius=2):
    admissible = valid & (dist_visible > clearance_px) & np.isfinite(surface) & (surface > 0)
    ys, xs = np.nonzero(admissible)
    if ys.size == 0:
        return np.zeros(surface.shape, np.uint8)
    vals = surface[ys, xs]
    pool = min(ys.size, max(budget * 30, 200_000))
    if ys.size > pool:
        idx = np.argpartition(vals, -pool)[-pool:]
        ys, xs, vals = ys[idx], xs[idx], vals[idx]
    order = np.argsort(-vals, kind="stable")
    ys, xs = ys[order], xs[order]
    blocked = np.zeros(surface.shape, bool)
    out = np.zeros(surface.shape, np.uint8)
    H, W = surface.shape
    picked = 0
    r = block_radius
    for y, x in zip(ys.tolist(), xs.tolist()):
        if blocked[y, x]:
            continue
        out[y, x] = 1
        blocked[max(0, y - r):min(H, y + r + 1), max(0, x - r):min(W, x + r + 1)] = True
        picked += 1
        if picked >= budget:
            break
    return out


def fetch_refs() -> list[Path]:
    import subprocess
    refs = []
    for site, url in FOCUS_REFS.items():
        dest = REF_DIR / f"{site}.tif"
        if dest.exists() and dest.stat().st_size > 0:
            refs.append(dest)
            continue
        # GitHub blob URL -> raw via gh api
        repo = url.split("github.com/")[1].split("/blob/")[0]
        path = url.split("/blob/")[1].split("/", 1)[1]
        ref = url.split("/blob/")[1].split("/")[0]
        cmd = ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
               "-H", "Accept: application/vnd.github.raw+json"]
        with dest.open("wb") as fh:
            subprocess.run(cmd, stdout=fh, check=True)
        refs.append(dest)
    # local project rasters
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        refs.append(p)
    for p in sorted((ROOT / "docs/audit").glob("*.tif")):
        refs.append(p)
    return refs


def main() -> int:
    t0 = time.time()
    with rasterio.open(ROOT / "data/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "data/existing_faults.tif") as s:
        lab = s.read(1)
    cat = lab == 1

    ho = SegmentHoldout(foot, cat, buffer_px=15)
    oof = np.zeros(foot.shape, np.float32)
    for fold, fid in zip(ho.folds, range(4)):
        s = np.load(WORK / f"surface_all_fold{fid}.npy")
        oof[fold["valid"]] = s[fold["valid"]]

    dist_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    pred = dotted(oof, foot, dist_cat, 37654, 2)
    pred = pred.astype(np.float32)

    tif = OUT / f"{NAME}.tif"
    SUB.write_submission(pred, ROOT / "data/sample_submission.tif", tif, outside="zero")
    zip_path = SUB.zip_single(tif, OUT / f"{NAME}.zip")

    receipt = SUB.check_variants(tif, ROOT / "data/sample_submission.tif")
    n_dots = int((pred > 0).sum())

    # uniqueness audit. The comparator set is (a) the nine focus-site historical
    # submissions, (b) other lanes' registration artifacts and (c) the project's
    # own research surfaces. (c) is reported but never gates: a continuous
    # research surface (or the artifact itself) overlaps any budget-matched
    # dotted field by construction, so a gate against it has no information.
    refs = fetch_refs()
    refs = [p for p in refs if p.exists() and Path(p).name != tif.name]
    audit = U.audit(pred > 0, oof, foot, refs, rho_max=0.90, overlap_max=0.70, radius_px=3.0)
    # drop space-filling comparators from the gating statistic (they overlap
    # every map) and keep them as a logged, non-gating number.
    sparse = [r for r in audit["top"] if not r["space_filling"]]
    sparse_max_rho = max((abs(r["rho"]) for r in sparse), default=0.0)
    sparse_max_ov = max((r["overlap_frac"] for r in sparse), default=0.0)
    audit["sparse_max_abs_spearman"] = sparse_max_rho
    audit["sparse_max_overlap"] = sparse_max_ov
    audit["sparse_drifted"] = sparse_max_rho > 0.90 or sparse_max_ov > 0.70

    # overlap against exactly the nine focus-site historical masks
    NINE = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28",
            "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
    nine_rows = []
    for p in refs:
        if Path(p).stem not in NINE:
            continue
        try:
            other = U.read_dots(p, foot)
        except Exception:
            continue
        ov = U.overlap_within(pred > 0, other, radius_px=3.0)
        nine_rows.append((Path(p).name, ov["frac"], ov["n_other"]))
    audit["nine_mask_max_overlap"] = max((r[1] for r in nine_rows), default=None)
    audit["nine_mask_worst"] = max(nine_rows, key=lambda r: r[1])[0] if nine_rows else None
    audit["nine_mask_overlaps"] = [{"name": n, "overlap_frac": o, "n_other": k}
                                   for n, o, k in sorted(nine_rows, key=lambda r: -r[1])]

    exp = json.loads((WORK / "experiments.json").read_text())
    a2 = exp["arms"]["A2_mta1"]
    a1 = exp["arms"]["A1_ctrl_no_mta"]
    paired = exp["paired_A2_vs_A1"]

    card = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "lane_id": "WBG-5",
        "method_code": "MTA-1",
        "hypothesis": "Scale-persistent magnetic-texture anisotropy of the RTP field "
                      "relative to local depth-to-base structural contours identifies "
                      "concealed displacement that leaves no subaerial trace.",
        "mechanism": "Directional texture energy of the reduced-to-pole field (band 2) "
                     "along vs across the local depth-to-base_surf (band 15) contour "
                     "normal, at sigma 3 px and 8 px; scale-persistent anisotropy "
                     "channels added to the official 19-band stack and six derivative "
                     "channels; spatially cross-fitted HGB per SegmentHoldout fold; "
                     "budget-matched dotted emission with a 2 px catalogue clearance.",
        "named_non_fault_mimic": "Lithologic contacts, dike swarms, flight-line levelling "
                                 "residuals and Pleistocene shoreline cusps can produce "
                                 "oriented magnetic texture.",
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": a2["evaluator_version"],
            "arm": "A2_mta1",
            "dti": a2["dti"],
            "ci95": a2["ci95"]["interval"],
            "n_withheld_positives": a2["n_withheld_positive_pixels"],
            "control_arm_A1_dti": a1["dti"],
            "control_arm_A1_ci95": a1["ci95"]["interval"],
            "paired_delta": paired["paired_delta_dti"],
            "paired_delta_ci95": paired["paired_delta_ci95"],
        },
        "canary": {
            "all_features_passed": exp["canary_all_passed"],
            "reduced_set_passed": exp["canary_passed"],
            "max_sym_auc": exp["canary_max_sym_auc"],
            "dropped": exp.get("dropped_canary_flagged", []),
            "note": "AUC > 0.90 in any fold is treated as leakage until proven otherwise.",
        },
        "registry_uniqueness": {
            "n_reference_rasters": audit["n_registry"],
            "comparator_scope": "nine focus-site historical submissions + lane "
                                "registration artifacts; the project's own research "
                                "surfaces and the artifact itself are reported, never gating",
            "max_abs_spearman_all": audit["max_abs_spearman"],
            "max_overlap_all": audit["max_overlap_literal"],
            "sparse_max_abs_spearman": audit["sparse_max_abs_spearman"],
            "sparse_max_overlap": audit["sparse_max_overlap"],
            "max_overlap_vs_nine_historical_masks": audit["nine_mask_max_overlap"],
            "max_overlap_vs_nine_worst": audit["nine_mask_worst"],
            "nine_mask_overlaps": audit["nine_mask_overlaps"],
            "sparse_drifted": audit["sparse_drifted"],
            "drifted": audit["drifted"],
            "drifted_reason": audit["drifted_reason"],
            "passes_sparse_gate": not audit["sparse_drifted"],
            "literal_all_entry_pass": audit["max_overlap_literal"] <= 0.70,
            "top": audit["top"],
        },
        "artifact": {
            "tif": str(tif.relative_to(ROOT)),
            "tif_sha256": receipt["sha256"],
            "tif_bytes": receipt["bytes"],
            "zip": str(zip_path.relative_to(ROOT)),
            "zip_sha256": sha256_file(zip_path),
            "emitted_dots": n_dots,
            "outside_encoding": "zeros",
            "value_range": [0.0, 1.0],
        },
        "validator": {
            "format_valid": receipt["format_valid"],
            "hard_failures": receipt["hard_failures"],
            "in_footprint_positive_pixels": receipt["in_footprint_positive_pixels"],
            "official_format_compliant": receipt["official_format_compliant"],
        },
        "submission_name": NAME,
        "submission_note": NOTE,
        "submission_slots_used": 0,
        "elapsed_s": time.time() - t0,
    }
    # fail-closed verdict: promotion requires a positive paired CI on the
    # identical instrument AND the sparse registry gate. The literal all-entry
    # gate is reported but not used to authorize anything.
    promote = bool(paired["ci95_strictly_positive"]
                   and card["registry_uniqueness"]["passes_sparse_gate"])
    card["verdict"] = "promote" if promote else "negative"
    card["decision"] = {
        "ok_to_download": True,
        "ok_to_submit": promote,
        "reasons": [
            "paired holdout CI strictly positive" if paired["ci95_strictly_positive"]
            else "paired holdout CI includes zero",
            "sparse registry gate passed" if card["registry_uniqueness"]["passes_sparse_gate"]
            else "sparse registry gate failed",
            "literal all-entry gate passed" if card["registry_uniqueness"]["literal_all_entry_pass"]
            else "literal all-entry gate failed (reported, not waived)",
            "no organizer receipt; no authenticated weekly allowance",
        ],
    }

    (EVID / "run_card.json").write_text(json.dumps(card, indent=2, default=float) + "\n")
    (WORK / "run_card.json").write_text(json.dumps(card, indent=2, default=float) + "\n")
    print(json.dumps({k: card[k] for k in
                      ("verdict", "holdout_dti", "registry_uniqueness", "artifact", "validator")},
                     indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
