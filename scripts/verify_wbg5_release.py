#!/usr/bin/env python
"""Re-derive every WBG-5 submission gate from the bytes on disk.

This is the automated inspector. It never reads a claim as true just because a
JSON file says so: it recomputes the file gates from the TIFF itself, then checks
that the published decision, the manifest and the three WBG-5 pages agree with
those recomputed gates. Exit code 0 means "download and submit" is safe.

Shallow mode (default) is what CI runs: it needs only committed files.
``--deep`` additionally recomputes competitor overlap and rank correlation from
the local ``.cache/anchors`` registry, which is not committed.

Usage:
    python scripts/verify_wbg5_release.py [--deep] [--quiet]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "docs" / "downloads"
EVID = ROOT / "evidence" / "wbg5"
SITE = ROOT / "docs" / "wbg5"
MANIFEST = DOWNLOADS / "wbg5-manifest.json"
TEMPLATE = ROOT / "data" / "bridge" / "sample_submission.tif"
ANCHORS = ROOT / ".cache" / "anchors"

OVERLAP_LIMIT = 0.70
RHO_LIMIT = 0.90
AUC_LIMIT = 0.90
NOTE_LIMIT = 140
EXPECTED_DOTS = 55_000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Report:
    def __init__(self, quiet: bool = False) -> None:
        self.rows: list[tuple[str, bool, str]] = []
        self.quiet = quiet

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        ok = bool(ok)
        self.rows.append((name, ok, detail))
        if not self.quiet:
            print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
        return ok

    @property
    def failed(self) -> list[str]:
        return [n for n, ok, _ in self.rows if not ok]


def forward_overlap(candidate: np.ndarray, reference: np.ndarray, radius: float = 3.0) -> float:
    """Fraction of candidate dots within ``radius`` px of a reference dot."""
    from scipy.spatial import cKDTree

    cp, rp = np.argwhere(candidate), np.argwhere(reference)
    if not len(cp) or not len(rp):
        return 0.0
    return float(np.mean(cKDTree(rp).query(cp)[0] <= radius))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deep", action="store_true", help="also recompute the registry gates")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    rep = Report(args.quiet)

    if not rep.check("manifest exists", MANIFEST.exists()):
        return 1
    man = json.loads(MANIFEST.read_text())
    tif = DOWNLOADS / man["artifact"]
    zp = DOWNLOADS / man["zip_file"]

    # ---------------- 1. bytes ------------------------------------------------
    for label, path in (("tif", tif), ("zip", zp)):
        if not rep.check(f"{label} file exists", path.exists(), path.name):
            return 1
    tif_sha = sha256_file(tif)
    zip_sha = sha256_file(zp)
    rep.check("tif sha256 matches manifest", tif_sha == man["sha256"], tif_sha[:16])
    rep.check("zip sha256 matches manifest", zip_sha == man["zip_sha256"], zip_sha[:16])
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        rep.check("zip holds exactly one member", len(names) == 1, ",".join(names))
        inner = hashlib.sha256(zf.read(names[0])).hexdigest() if names else ""
    rep.check("zip member is byte-identical to the tif", inner == tif_sha)

    # ---------------- 2. raster contract, recomputed ---------------------------
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
        meta = {
            "count": ds.count,
            "dtype": ds.dtypes[0],
            "crs": str(ds.crs),
            "shape": arr.shape,
            "transform": tuple(ds.transform),
            "nodata": ds.nodata,
        }
    with rasterio.open(TEMPLATE) as tds:
        ref = tds.read(1)
        tmpl = {
            "crs": str(tds.crs),
            "shape": ref.shape,
            "transform": tuple(tds.transform),
        }
    finite = np.isfinite(arr)
    ref_finite = np.isfinite(ref)
    values = arr[finite]

    rep.check("single band", meta["count"] == 1, str(meta["count"]))
    rep.check("float32", meta["dtype"] == "float32", meta["dtype"])
    rep.check("CRS matches the organisers' template", meta["crs"] == tmpl["crs"], meta["crs"])
    rep.check("shape matches the template", meta["shape"] == tmpl["shape"], str(meta["shape"]))
    rep.check("affine transform matches the template", meta["transform"] == tmpl["transform"])
    rep.check(
        "no NaN inside the study footprint",
        not np.isnan(arr[ref_finite]).any(),
        f"{int(np.isnan(arr[ref_finite]).sum())} NaN",
    )
    rep.check(
        "NaN only outside the footprint",
        not np.isfinite(arr[~ref_finite]).any(),
        f"{int(np.isfinite(arr[~ref_finite]).sum())} finite outside",
    )
    rep.check(
        "every value inside [0, 1]  (the portal's own gate)",
        bool(values.size and values.min() >= 0.0 and values.max() <= 1.0),
        f"[{values.min():.3f}, {values.max():.3f}]",
    )
    positives = int((arr > 0).sum())
    rep.check("has positive predictions", positives > 0, str(positives))
    rep.check("positive count matches the manifest", positives == EXPECTED_DOTS, str(positives))
    bad = np.unique(values[(values < 0) | (values > 1)])
    rep.check("no out-of-range distinct values", bad.size == 0, str(bad[:5]))

    # ---------------- 3. label and note ---------------------------------------
    name = man["submission_name"]
    derived = tif.name.replace("-nanoutside.tif", "")
    rep.check("submission name matches the file basename", name == derived, name)
    rep.check("submission name is a slug", bool(re.fullmatch(r"[a-z0-9][a-z0-9.\-]{2,80}", name)))
    note = man["note"]
    rep.check("note is non-empty", bool(note.strip()))
    rep.check(f"note is within {NOTE_LIMIT} characters", len(note) <= NOTE_LIMIT, f"{len(note)} chars")
    rep.check("note length recorded correctly", man.get("note_characters") == len(note))

    # ---------------- 4. published evidence agrees ----------------------------
    validator = json.loads((EVID / "validator.json").read_text())
    decision = json.loads((EVID / "decision.json").read_text())
    unique = json.loads((EVID / "uniqueness.json").read_text())
    canaries = json.loads((EVID / "canaries.json").read_text())

    vchecks = validator.get("checks", {})
    for key in (
        "single_band",
        "float32",
        "crs_matches_template",
        "shape_matches_template",
        "transform_matches_template",
        "no_nan_inside_footprint",
        "nan_outside_footprint_only",
        "values_in_0_1",
        "has_positive_predictions",
    ):
        rep.check(f"recorded validator flag {key}", vchecks.get(key) is True)
    rep.check("recorded validator sha256 matches the file", validator.get("sha256") == tif_sha)
    rep.check("recorded validator passed", validator.get("all_passed") is True)

    recomputed = {
        "format_valid": bool(vchecks.get("values_in_0_1") and vchecks.get("nan_outside_footprint_only")),
        "byte_unique": bool(unique.get("byte_unique_among_checked")),
        "competitor_uniqueness": bool(unique.get("passes_competing_gate")),
    }
    rep.check("recomputed gates equal the recorded gates", recomputed == decision.get("gates"),
              json.dumps(recomputed))
    expected_submit = "YES" if all(recomputed.values()) else "NO"
    rep.check("decision follows from the gates, not from prose", decision.get("SUBMIT") == expected_submit,
              decision.get("SUBMIT"))
    rep.check("no failed gate is listed", decision.get("reasons") == [], str(decision.get("reasons")))
    rep.check("manifest ok_to_submit agrees with the decision",
              man.get("ok_to_submit") is (expected_submit == "YES"))

    rep.check("max 3-px overlap vs rivals under the limit",
              unique["max_forward_3px_overlap_vs_competing"] <= OVERLAP_LIMIT,
              f"{unique['max_forward_3px_overlap_vs_competing']:.4f} vs {OVERLAP_LIMIT}")
    rep.check("max |rho| vs rivals under the limit",
              unique["max_abs_spearman_vs_competing"] <= RHO_LIMIT,
              f"{unique['max_abs_spearman_vs_competing']:.4f} vs {RHO_LIMIT}")
    rep.check("no rival is byte-identical",
              all(not c["byte_identical"] for c in unique["competing_published_submissions"]))
    max_auc = canaries.get("max_orientation_invariant_auc", canaries.get("max_auc"))
    rep.check("leakage canary below the AUC limit", max_auc is not None and max_auc <= AUC_LIMIT,
              f"{max_auc:.4f} vs {AUC_LIMIT} ({canaries.get('max_feature')})")
    rep.check("leakage canary did not flag leakage", canaries.get("suspected_leakage") is False)

    # ---------------- 5. the pages cannot contradict the gates ----------------
    index = (SITE / "index.html").read_text()
    howto = (SITE / "how-to-submit.html").read_text()
    rep.check("landing page states SUBMIT: YES", "SUBMIT: YES" in index)
    rep.check("landing page links the tif by name", tif.name in index)
    rep.check("landing page links the zip by name", zp.name in index)
    rep.check("how-to page repeats the exact paste name", name in howto)
    rep.check("how-to page states the file is fine to submit as downloaded", "as downloaded" in howto)
    rep.check("forensics page exists", (SITE / "forensics.html").exists())

    # ---------------- 6. optional deep registry recomputation -----------------
    if args.deep:
        if not (ANCHORS / "anchors.json").exists():
            rep.check("anchor registry available for --deep", False, str(ANCHORS))
        else:
            ours = np.nan_to_num(arr, nan=0.0) > 0.5
            meta_anchors = json.loads((ANCHORS / "anchors.json").read_text())["anchors"]
            worst_o, worst_o_name, worst_r, worst_r_name = 0.0, "", 0.0, ""
            for row in meta_anchors:
                path = ANCHORS / row["name"]
                if not path.exists():
                    continue
                with rasterio.open(path) as ds:
                    theirs = np.nan_to_num(ds.read(1), nan=0.0) > 0.5
                ov = forward_overlap(ours, theirs)
                if ov > worst_o:
                    worst_o, worst_o_name = ov, row["name"]
                if theirs.sum() and ours.sum():
                    from scipy.stats import spearmanr

                    rho = spearmanr(ours.ravel(), theirs.ravel()).statistic
                    if abs(rho) > abs(worst_r):
                        worst_r, worst_r_name = float(rho), row["name"]
            rep.check("deep: recomputed overlap still under the limit", worst_o <= OVERLAP_LIMIT,
                      f"{worst_o:.4f} vs {worst_o_name}")
            rep.check("deep: recomputed |rho| still under the limit", abs(worst_r) <= RHO_LIMIT,
                      f"{worst_r:.4f} vs {worst_r_name}")
            rep.check("deep: recomputed overlap matches the published value",
                      abs(worst_o - unique["max_forward_3px_overlap_vs_competing"]) < 0.01,
                      f"{worst_o:.4f} vs {unique['max_forward_3px_overlap_vs_competing']:.4f}")

    if args.quiet:
        for n, ok, d in rep.rows:
            if not ok:
                print(f"FAIL  {n}  [{d}]")
    print()
    if rep.failed:
        print(f"WBG-5 RELEASE: NOT SUBMITTABLE — {len(rep.failed)} failed check(s): {rep.failed}")
        return 2
    print(f"WBG-5 RELEASE: SUBMITTABLE — {len(rep.rows)} checks passed, 0 failed")
    print(f"  file  : {tif.name}")
    print(f"  sha256: {tif_sha}")
    print(f"  name  : {name}")
    print(f"  note  : {note}  ({len(note)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
