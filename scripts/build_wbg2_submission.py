#!/usr/bin/env python
"""Build and validate the WBG-2 research artifact; submission eligibility is fail-closed.

Deterministic: same inputs + same seed -> same bytes.

Run from the repository root:

    PYTHONPATH=src .venv/bin/python scripts/build_wbg2_submission.py

Outputs
-------
docs/downloads/<name>.tif            research-only file; not submission-cleared
docs/downloads/<name>.zip            single-member ZIP of the same bytes
docs/downloads/<name>.validator.json format validator report
docs/downloads/<name>.uniqueness.json registry gate report
evidence/wbg2/run_card.json          the session run card
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone

import numpy as np
import rasterio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wbg2 import prior as P  # noqa: E402
from wbg2 import uniqueness as U  # noqa: E402
from wbg2 import validate as V  # noqa: E402
from wbg2.metric import dti  # noqa: E402
from wbggems1.eligibility import submission_eligibility  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LABELS = os.path.join(ROOT, "data", "bridge", "labels.tif")
SAMPLE = os.path.join(ROOT, "data", "bridge", "sample_submission.tif")
OUT_DIR = os.path.join(ROOT, "docs", "downloads")
EV_DIR = os.path.join(ROOT, "evidence", "wbg2")

SEED = 20261027
BUDGET = P.DEFAULT_BUDGET
NAME = "wbg2-offcatalogue-density-36k-20261027"
NOTE = (
    "WBG-2 unique: off-catalogue (>=400 m) fault-density prior, 36k scattered "
    "dots, zeros-mode, no NaN. Not a copy of GEMSDOE24-36."
)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(EV_DIR, exist_ok=True)

    with rasterio.open(LABELS) as src:
        labels = src.read(1)
        transform = src.transform
        crs = src.crs
        profile = src.profile.copy()

    footprint = labels != -1
    catalogue = labels == 1

    # ---- placement prior -------------------------------------------------
    prior = P.density_prior(catalogue)
    excluded = P.catalogue_buffer(catalogue, P.CATALOGUE_BUFFER_PX)
    admissible = footprint & ~excluded

    cells = P.place(prior, admissible, BUDGET, SEED)
    surface = P.render(labels.shape, cells)

    # prove the exclusion held
    assert not excluded[cells[:, 0], cells[:, 1]].any(), "placement violated catalogue buffer"

    # ---- write the TIFF (zeros mode: NaN-free, 0 outside footprint) -------
    out_tif = os.path.join(OUT_DIR, f"{NAME}.tif")
    meta = profile.copy()
    meta.update(count=1, dtype="float32", nodata=None, compress="deflate", tiled=False)
    with rasterio.open(out_tif, "w", **meta) as dst:
        dst.write(surface.astype("float32"), 1)

    out_zip = os.path.join(OUT_DIR, f"{NAME}.zip")
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(out_tif, arcname=os.path.basename(out_tif))

    # ---- validate --------------------------------------------------------
    rep = V.validate_tif(out_tif, footprint=footprint)
    zrep = V.validate_zip(out_zip, out_tif)
    with open(os.path.join(OUT_DIR, f"{NAME}.validator.json"), "w") as f:
        json.dump({"tif": rep.to_dict(), "zip": zrep}, f, indent=1)

    # ---- registry gates --------------------------------------------------
    roots = [
        os.path.join(ROOT, "docs"),
        os.path.join(ROOT, "registry"),
        os.path.join(ROOT, "evidence"),
    ]
    own = {os.path.abspath(out_tif), os.path.abspath(out_zip)}
    reg = U.scan_registry(surface, labels.shape, transform, crs, roots, exclude=own)
    with open(os.path.join(OUT_DIR, f"{NAME}.uniqueness.json"), "w") as f:
        json.dump(reg, f, indent=1)

    # ---- measured DTI vs the catalogue -----------------------------------
    # Zero by construction: the surface is >= 4 px from every mapped fault while
    # the kernel support is 3 px, so the mapped catalogue can contribute nothing.
    # This is a *check that the exclusion held*, not a score proxy.
    dti_vs_catalogue, comp = dti(
        surface, catalogue, footprint=footprint, profile=True
    )

    # ---- calibrated score estimate --------------------------------------
    calib_path = os.path.join(ROOT, "registry", "wbg2_calibration.json")
    with open(calib_path) as f:
        calib = json.load(f)
    near3 = 0.0  # by construction: nothing within 4 px of the catalogue
    b = calib["coefficients"]
    est = b["intercept"] + b["near3cat"] * near3 + b["log_budget"] * float(np.log(BUDGET))
    half = 1.96 * calib["residual_sd"]

    eligibility_gates = {
        "format_valid": bool(rep.all_checks_passed and zrep["all_checks_passed"]),
        "focus_site_uniqueness_pass": bool(reg["passes_final_dot_gate"]),
        "comparable_holdout_dti_available": False,
        "beats_current_holdout_best": False,
        "authorized_slot_selector_record": False,
    }
    can_submit = submission_eligibility(eligibility_gates)

    run_card = {
        "schema": "wbg2-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": "WBG-2: off-catalogue fault-density-prior dot field",
        "mechanism": (
            "Gaussian KDE (1.5 km) of mapped-fault density supplies a placement "
            "prior; all cells within 400 m of the catalogue are excluded because "
            "the scored target is the faults that are NOT in the catalogue; a "
            "36k-cell scattered field is rendered binary in zeros mode."
        ),
        "named_non_fault_mimic": (
            "Basin-fill depocentres and range-front alluvial aprons concentrate "
            "next to mapped faults, so a density prior partly reproduces the "
            "sedimentary basin geometry rather than faulting. The prior is a "
            "spatial-distribution model, not a detection."
        ),
        "lane": "provisional research; no single-method paragraph supplied",
        "budget_pixels": BUDGET,
        "seed": SEED,
        "catalogue_buffer_px": P.CATALOGUE_BUFFER_PX,
        "kde_sigma_px": P.KDE_SIGMA_PX,
        "measured": {
            "evidence_class": "PROXY-DTI",
            "note": (
                "DTI of this surface against the *mapped* catalogue. It is 0.0 by "
                "construction and serves as proof that the >=400 m catalogue "
                "exclusion held. The scored target is the complement of the "
                "catalogue, so this is NOT a score estimate."
            ),
            "dti_vs_catalogue": dti_vs_catalogue,
            "components": comp,
        },
        "score_estimate": {
            "evidence_class": "MODEL-ESTIMATE",
            "status": "WITHDRAWN-EXPLORATORY-REGRESSION; NOT A SCORE; DO NOT USE FOR SLOT SELECTION",
            "valid_for_submission_decision": False,
            "value": est,
            "ci95": [est - half, est + half],
            "model": calib["model"],
            "fitted_on": calib["fitted_on"],
            "r2": calib["r2"],
            "residual_sd": calib["residual_sd"],
            "caveats": calib["caveats"],
        },
        "registry": reg,
        "raster_sha256": sha256(out_tif),
        "validator": {"tif": rep.to_dict(), "zip": zrep},
        "submission_name": NAME,
        "submission_note": NOTE,
        "note_length": len(NOTE),
        "artifacts": {
            "tif": os.path.relpath(out_tif, ROOT),
            "zip": os.path.relpath(out_zip, ROOT),
        },
        "verdict": "negative",
        "eligibility_gates": eligibility_gates,
        "decision": {
            "ok_to_download": True,
            "ok_to_submit": can_submit,
            "submission_slots_used": 0,
            "reason": (
                "Research download only. Format and the limited nine-site byte/dot audit pass, "
                "but there is no comparable HOLDOUT-DTI result showing a win over the current "
                "best and no separately authorized selector record. The exploratory regression "
                "from unverified owner-reported values is not a score estimate suitable for slot selection."
            ),
        },
    }
    with open(os.path.join(EV_DIR, "run_card.json"), "w") as f:
        json.dump(run_card, f, indent=1)

    print(json.dumps({
        "tif": run_card["artifacts"]["tif"],
        "sha256": run_card["raster_sha256"],
        "positive_pixels": rep.positive_pixels,
        "validator_pass": rep.all_checks_passed,
        "zip_pass": zrep["all_checks_passed"],
        "uniqueness_pass": reg["passes_final_dot_gate"],
        "max_overlap": reg["max_forward_3px_overlap"],
        "max_rho": reg["max_abs_spearman"],
        "rasters_compared": reg["rasters_compared"],
        "dti_vs_catalogue": dti_vs_catalogue,
        "withdrawn_exploratory_model_output_not_score": est,
        "model_interval_not_score_ci": [est - half, est + half],
        "note_len": len(NOTE),
    }, indent=1))
    # Exit 0 reports successful artifact generation/validation, not submission approval.
    return 0 if rep.all_checks_passed and zrep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
