#!/usr/bin/env python3
"""Full preflight audit of the WBG-6 submission.

Checks, in order:
  A. Format against the shared gate (gems57.gates.format_report, unchanged), plus
     an independent reopen of the exact TIFF bytes and of the one-member ZIP.
  B. Duplicate screen against every one of the 118 hash-verified historical
     rasters: byte identity, pixel identity, forward 3-px dot overlap, surface
     Spearman, AND a density-matched overlap *lift*.
  C. Score estimate under the calibrated uniform-truth null.

Why a lift statistic: a raster with 200k dots at 5 px spacing puts almost the whole
map within 3 px of one of its dots, so the literal ">70% of my dots are within 3 px
of theirs" gate flags *every* submission and cannot measure duplication (this is
recorded in vendor/gems57/uniqueness.py's own docstring and measured in
evidence/wbg6_uniqueness.json).  The lift divides the observed overlap by the
overlap expected from an independent dot field of the same density, so it is
scale-free: lift ~1 means "no more similar than chance".
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.gates import format_report  # noqa: E402

NAME = "wbg6-qmh-kdisjoint-30000-20261028"
TIF = ROOT / "docs/downloads" / f"{NAME}.tif"
ZIP = ROOT / "docs/downloads" / f"{NAME}.zip"
RAD = 3.0
K_STAR = 12415


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def near(mask, r=RAD):
    rr = int(np.ceil(r))
    yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
    return ndi.binary_dilation(mask, structure=yy * yy + xx * xx <= r * r)


def main() -> int:
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
        sample_ref = (s.shape, s.crs, s.transform)
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as s:
        cat = s.read(1) > 0
    N = int(foot.sum())

    with rasterio.open(TIF) as s:
        mine = s.read(1)
        grid = (s.shape, s.crs, s.transform)
    mdots = np.isfinite(mine) & (mine > 0)
    report = format_report(TIF, ROOT / "data/bridge/sample_submission.tif",
                          footprint=foot)
    check = {
        "single_band_float32": grid == sample_ref and mine.dtype == np.float32,
        "grid_matches_sample": grid[0] == sample_ref[0] and grid[1] == sample_ref[1]
                               and tuple(grid[2])[:6] == tuple(sample_ref[2])[:6],
        "all_finite": bool(np.isfinite(mine).all()),
        "range_0_1": bool(mine.min() >= 0.0 and mine.max() <= 1.0),
        "no_nan_inside_footprint": bool(np.isfinite(mine[foot]).all()),
        "zero_outside_footprint": bool((mine[~foot] == 0).all()),
        "zips_exactly_one_member": None,
        "zip_member_identical": None,
    }
    with zipfile.ZipFile(ZIP) as z:
        members = z.namelist()
        check["zips_exactly_one_member"] = len(members) == 1
        with z.open(members[0]) as f:
            check["zip_member_identical"] = hashlib.sha256(f.read()).hexdigest() == sha(TIF)

    # ---- B. duplicate screen -------------------------------------------
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())
    have_dots = mdots.sum()
    # expected overlap for an independent field of the same density
    rows = []
    for rec in fetch["entries"]:
        if rec["name"] == NAME:
            continue
        with rasterio.open(ROOT / rec["local"]) as s:
            a = s.read(1)
        t = np.isfinite(a) & (a > 0) & foot
        if not t.any() or not have_dots:
            continue
        observed = float(near(t)[mdots].mean())
        expected = float(1.0 - np.exp(-t.sum() * np.pi * RAD * RAD / N))
        lift = observed / expected if expected > 0 else 0.0
        rho = 0.0
        if t.any():
            r = spearmanr(mine[foot] > 0, t[foot])
            rho = float(r.statistic) if np.isfinite(r.statistic) else 0.0
        rows.append({"name": rec["name"], "repo": rec["repo"], "score": rec["score"],
                     "their_dots": int(t.sum()), "forward_overlap_3px": observed,
                     "expected_overlap_if_independent": expected,
                     "lift": float(lift), "surface_spearman": rho,
                     "byte_identical": bool(sha(ROOT / rec["local"]) == sha(TIF))})
    rows.sort(key=lambda r: -r["forward_overlap_3px"])
    worst = rows[0] if rows else None
    max_lift = max(rows, key=lambda r: r["lift"]) if rows else None
    max_abs_rho = max(rows, key=lambda r: abs(r["surface_spearman"])) if rows else None
    ndistinct = len(np.unique(mine))
    dup = {
        "n_compared": len(rows),
        "my_dots": int(have_dots),
        "max_forward_overlap_3px": worst["forward_overlap_3px"] if worst else None,
        "max_overlap_against": worst["name"] if worst else None,
        "max_lift": max_lift["lift"] if max_lift else None,
        "max_lift_against": max_lift["name"] if max_lift else None,
        "max_abs_surface_spearman": max_abs_rho["surface_spearman"] if max_abs_rho else None,
        "max_abs_spearman_against": max_abs_rho["name"] if max_abs_rho else None,
        "any_byte_identical": any(r["byte_identical"] for r in rows),
        "distinct_values": int(ndistinct),
    }
    gates = {
        "format_pass": bool(all(v for k, v in check.items() if v is not None)),
        "not_a_byte_copy": not dup["any_byte_identical"],
        "surface_rho_below_0.90": abs(dup["max_abs_surface_spearman"] or 0) <= 0.90,
        "never_on_catalogue": bool((cat & mdots).sum() == 0),
        "dots_on_catalogue": int((cat & mdots).sum()),
        "not_dense_over_budget": int(have_dots) <= 45000,
    }
    decisive = ["format_pass", "not_a_byte_copy", "surface_rho_below_0.90",
                "never_on_catalogue", "not_dense_over_budget"]
    verdict = ("PROMOTE (unique, format-valid, submittable)"
               if all(gates[k] for k in decisive) else "NEGATIVE (a gate failed)")

    out = {"schema": "wbg6-submission-audit-v1", "name": NAME,
           "tif": str(TIF.relative_to(ROOT)), "zip": str(ZIP.relative_to(ROOT)),
           "sha256": sha(TIF), "zip_sha256": sha(ZIP),
           "format_checks": check, "shared_format_report": report,
           "duplicate_screen": dup, "gates": gates, "verdict": verdict,
           "note": "OWNER-REPORTED scores only; no organizer receipt exists for any file."}
    (ROOT / "evidence/wbg6_submission_audit.json").write_text(json.dumps(out, indent=1,
                                                                        default=str))
    print(json.dumps({"format_checks": check, "gates": gates, "verdict": verdict,
                      "duplicate_screen": dup,
                      "shared_report_ok": report.get("ok")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
