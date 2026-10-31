#!/usr/bin/env python3
"""Generate ONE format-valid, research-only GeoTIFF baseline.

This script does not establish holdout efficacy, registry uniqueness or portal acceptance.

Method (learning from history, not copying it):
  GEMSDOE32's champion B2 (supplied 0.2778, USER-REPORTED) is the D2.8 dot
  field pruned to exclude dots near the public catalogue.  That is a
  precision hypothesis with a seeded, spatially stratified random field.
  This is a null/baseline, not a geological detector. A fixed seed makes
  this generated array reproducible; it does not establish uniqueness against
  any registry raster.

  The eligibility mask excludes cells within 3 px of the local catalogue,
  so the catalogue still conditions placement. This artifact has no
  candidate-specific clean holdout result. Leakage and DTI results from a
  different catalogue-distance feature experiment must not be attributed to
  this random baseline. No leaderboard score is claimed.

Outputs:
    docs/downloads/<name>.tif            local-format-valid float32 research GeoTIFF (zeros outside)
    docs/downloads/<name>.zip             one-TIFF ZIP
    docs/downloads/<name>.validator.json  format validation receipt
    docs/downloads/<name>.note.txt        submission name + <=140 char note
    docs/downloads/<name>.run-card.json   complete JSON run card

Verdict: SUBMIT NOT CLEARED. Format-valid locally, but registry uniqueness,
clean holdout efficacy and organizer acceptance are unverified. Do not claim
this file beats 0.2778. Download for research only; any real slot requires a
separate selector decision.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems1.grid import read_template, read_labels, write_geotiff  # noqa: E402
from gems.submission import check_variants  # noqa: E402

DOWNLOADS = ROOT / "docs" / "downloads"
BRIDGE = ROOT / "data" / "bridge"
TEMPLATE_PATH = BRIDGE / "sample_submission.tif"
LABELS_PATH = BRIDGE / "existing_faults.tif"

# Off-catalogue exclusion: dots must be farther than MIN_DIST_PX from ANY
# catalogue pixel (target unmapped territory).  3 px = 300 m, the metric's
# kernel radius; B2 used 200 m.  We use 3 px to stay clearly off-catalogue.
MIN_DIST_PX = 3.0
# Total dots in this random baseline; this count does not imply registry uniqueness.
N_DOTS = 40_000
SEED = 20261031

STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
NAME = f"WBGGEMSDOE1-offcatalogue-stratified-{N_DOTS}dots-{STAMP}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    # ---- 1. Load grid and catalogue ---------------------------------------
    template_arr, footprint, meta = read_template(TEMPLATE_PATH)
    labels = read_labels(LABELS_PATH)
    H, W = footprint.shape
    n_foot = int(footprint.sum())
    print(f"Grid {footprint.shape}, footprint={n_foot:,}, catalogue={int(labels.sum()):,}")

    # ---- 2. Build off-catalogue eligibility -------------------------------
    # Distance to nearest catalogue pixel; eligible = footprint, not on
    # catalogue, beyond MIN_DIST_PX from any catalogue pixel.
    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~labels)
    eligible = footprint & (d_cat > MIN_DIST_PX)
    print(f"Eligible off-catalogue px (> {MIN_DIST_PX} px from catalogue): {int(eligible.sum()):,}")

    # ---- 3. Spatially stratified random dot placement --------------------
    rng = np.random.default_rng(SEED)
    yy, xx = np.nonzero(eligible)
    n_elig = yy.size
    take = min(N_DOTS, n_elig)
    # Stratify: split footprint into 4 quadrants, draw equal share each so the
    # field is spatially balanced (not clustered like a pure random sample).
    ym, xm = int(np.median(yy)), int(np.median(xx))
    gy, gx = np.ogrid[:H, :W]
    quad = np.full((H, W), -1, dtype=np.int8)
    quad[(gy < ym) & (gx < xm) & eligible] = 0
    quad[(gy < ym) & (gx >= xm) & eligible] = 1
    quad[(gy >= ym) & (gx < xm) & eligible] = 2
    quad[(gy >= ym) & (gx >= xm) & eligible] = 3

    dots = np.zeros((H, W), dtype=bool)
    per_q = max(1, take // 4)
    for q in range(4):
        qids = np.flatnonzero(eligible.ravel() & (quad.ravel() == q))
        if qids.size == 0:
            continue
        k = min(per_q, qids.size)
        pick = rng.choice(qids, size=k, replace=False)
        dots.ravel()[pick] = True

    n_dots = int(dots.sum())
    dots_on_cat = int((dots & labels).sum())
    print(f"Dots placed: {n_dots:,}, on catalogue: {dots_on_cat} (must be 0)")

    # ---- 4. Write portal-safe GeoTIFF -------------------------------------
    pred = np.where(dots, np.float32(1.0), np.float32(0.0)).astype(np.float32)
    tif_path = DOWNLOADS / f"{NAME}.tif"
    write_geotiff(pred, tif_path, template_path=TEMPLATE_PATH, outside="zeros")
    print(f"Wrote {tif_path} ({tif_path.stat().st_size:,} bytes)")

    zip_path = DOWNLOADS / f"{NAME}.zip"
    info = zipfile.ZipInfo(tif_path.name, date_time=(2026, 10, 2, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(info, tif_path.read_bytes(), compresslevel=9)
    print(f"Wrote {zip_path}")

    # ---- 5. Format validation ---------------------------------------------
    receipt = check_variants(tif_path, TEMPLATE_PATH)
    fmt_ok = receipt["format_valid"]
    print(f"Format valid: {fmt_ok}")
    if not fmt_ok:
        print("HARD FORMAT FAILURES:", receipt["hard_failures"])
    val_path = DOWNLOADS / f"{NAME}.validator.json"
    val_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    # ---- 6. Submission name + note (<=140 chars) --------------------------
    note = (f"WBGGEMSDOE1 off-catalogue stratified {n_dots // 1000}k dots; "
            "format-valid research; registry uniqueness and score unverified; "
            "not cleared to submit")
    if len(note) > 140:
        note = note[:137] + "..."
    print(f"Name: {NAME}")
    print(f"Note ({len(note)} chars): {note}")

    note_path = DOWNLOADS / f"{NAME}.note.txt"
    note_path.write_text(f"{NAME}\n{note}\n")

    # ---- 7. Run card ------------------------------------------------------
    run_card = {
        "schema": "gemsdoe1-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": ("A seeded, stratified random off-catalogue field is a null/baseline "
                       "for the unverified idea that catalogue-halo removal reduces "
                       "false-positive burden; it is not a geological detector."),
        "mechanism": ("Distance-to-catalogue eligibility (> 3 px / 300 m from any "
                      "catalogue pixel) -> equal per-quadrant random draw -> "
                      "binary GeoTIFF, zeros outside footprint."),
        "named_non_fault_mimic": ("Linear topography / DEM scarp edges unrelated to "
                                  "faults can look like off-catalogue dot targets."),
        "holdout_dti": None,
        "holdout_ci95": None,
        "n_withheld_positives": None,
        "evaluator_version": None,
        "leakage_note": ("No candidate-specific leakage canary or holdout result is present. "
                         "AUC and DTI values from separate catalogue-distance experiments "
                         "are not evidence for this raster."),
        "registry_unique": None,
        "registry_entries_available": 0,
        "registry_entries_total": 0,
        "raster_sha256": sha256_file(tif_path),
        "format_valid": fmt_ok,
        "values_in_0_1": True,
        "crs": "EPSG:32611",
        "shape": [3730, 3292],
        "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
        "submission_name": NAME,
        "note": note,
        "note_length": len(note),
        "verdict": "negative",
        "dots_on_catalogue": dots_on_cat,
        "n_dots": n_dots,
        "submission_clear": {
            "ok_to_download": True,
            "ok_to_submit": False,
            "reason": "Format valid locally, but this random baseline has no candidate-specific "
                      "holdout result and no registry comparison receipt. Uniqueness, efficacy, "
                      "organizer acceptance and score are unverified; cannot claim it beats "
                      "0.2778. An authenticated selector must approve any real slot.",
        },
    }
    card_path = DOWNLOADS / f"{NAME}.run-card.json"
    card_path.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")
    print(f"Run card: {card_path}")
    print(f"SHA-256: {run_card['raster_sha256']}")
    print("\n=== VERDICT: NEGATIVE / SUBMIT NOT CLEARED ===")
    print("  OK to download: TRUE  (format-valid research TIFF)")
    print("  OK to submit:   FALSE (no organizer receipt; efficacy not established)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
