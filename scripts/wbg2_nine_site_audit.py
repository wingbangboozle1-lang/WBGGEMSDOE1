#!/usr/bin/env python
"""Scoped pairwise diagnostic against the nine named focus-site artifacts.

This script does not clear a lane or establish complete-registry uniqueness.
It uses the shared template overlap implementation; chance enrichment is
reported only as a diagnostic and never waives a literal STOP. It must not be
run for a new candidate without an assigned lane and a surface-before-placement
check.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "vendor")]

from wbg2 import uniqueness as U  # noqa: E402

OURS = os.path.join(ROOT, "docs", "downloads", "wbg2-offcatalogue-density-36k-20261027.tif")
LABELS = os.path.join(ROOT, "data", "bridge", "labels.tif")
OUT = os.path.join(ROOT, "evidence", "wbg2", "nine_site_uniqueness.json")

#: Highest supplied historical artifact per site and USER-REPORTED value.
#: These values are not submission-page receipts or organizer-confirmed scores.
TOP = {
    "GEMSDOE24": ("/tmp/GEMSDOE24", "h25-1-dotted-h19-5-d1-5", 0.2477),
    "GEMSDOE25": ("/tmp/GEMSDOE25", "dotted-h19-5-d2-8", 0.2600),
    "GEMSDOE27": ("/tmp/GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5", 0.2449),
    "GEMSDOE28": ("/tmp/GEMSDOE28", "h36-1-rung30-blind-r1", 0.2710),
    "GEMSDOE30": ("/tmp/GEMSDOE30", "d28-poisson300m-offcat-44090", 0.2600),
    "GEMSDOE31": ("/tmp/GEMSDOE31", "h27-4-solo-d28", 0.2708),
    "GEMSDOE32": ("/tmp/g32", "h33-h33-2-b2", 0.2778),
    "GEMSDOE33": ("/tmp/GEMSDOE33", "h33d-analog-tip-stepover-r30", 0.2632),
    "GEMSDOE36": ("/tmp/GEMSDOE36", "anderson-geothermal-pinn-38854", 0.2750),
}


def find_artifact(root: str, key: str) -> str | None:
    best = None
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            if key not in filename or not filename.lower().endswith(".tif"):
                continue
            score = 0
            if "zeros" in filename:
                score += 2
            if "allfinite" in filename or "nanoutside" in filename:
                score += 1
            if "nan" in filename:
                score -= 1
            if best is None or score > best[0]:
                best = (score, os.path.join(dirpath, filename))
    return best[1] if best else None


def _disk(radius: float) -> np.ndarray:
    r = int(np.ceil(radius))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return yy * yy + xx * xx <= radius * radius


def main() -> int:
    with rasterio.open(LABELS) as source:
        labels = source.read(1)
        transform, crs = source.transform, source.crs
    footprint = labels != -1
    catalogue = labels == 1
    catalogue_near3 = ndi.binary_dilation(catalogue, structure=_disk(3.0))

    with rasterio.open(OURS) as source:
        ours = source.read(1).astype(np.float32)
    ours = np.where(np.isfinite(ours), ours, 0.0)

    rows = []
    for site, (clone_root, key, user_reported) in TOP.items():
        path = find_artifact(clone_root, key) if os.path.isdir(clone_root) else None
        row = {
            "site": site,
            "user_reported_score": user_reported,
            "score_evidence_class": "USER-REPORTED / NOT ORGANIZER-CONFIRMED",
            "expected_artifact": key,
            "audited": path is not None,
        }
        if path is None:
            row["status"] = "NOT AUDITED — source clone missing"
            rows.append(row)
            print(f"{site:10s} NOT AUDITED (clone missing)")
            continue
        theirs = U.load_aligned(path, labels.shape, transform, crs)
        if theirs is None:
            row["status"] = "NOT AUDITED — exact grid mismatch or unreadable raster"
            rows.append(row)
            print(f"{site:10s} NOT AUDITED (grid mismatch / unreadable)")
            continue
        comparison = U.compare(ours, theirs, evaluated=footprint)
        their_support = np.isfinite(theirs) & (theirs > 0) & footprint
        row.update({
            "artifact": os.path.basename(path),
            "their_positive_pixels": int(their_support.sum()),
            "their_fraction_within_3px_of_catalogue": float(
                (their_support & catalogue_near3).sum()
            ) / max(1, int(their_support.sum())),
            "their_fraction_on_catalogue": float(
                (their_support & catalogue).sum()
            ) / max(1, int(their_support.sum())),
            "forward_3px_overlap": comparison["forward_overlap"],
            "sampled_spearman_rho_diagnostic_only": comparison["rho_sampled_diagnostic_only"],
            "chance_overlap_diagnostic_only": comparison["chance_overlap_diagnostic_only"],
            "enrichment_diagnostic_only": comparison["enrichment_diagnostic_only"],
            "literal_pairwise_stop": comparison["literal_pairwise_stop"],
            "status": "audited",
        })
        rows.append(row)
        print(
            f"{site:10s} USER-REPORTED={user_reported:.4f}  "
            f"overlap={comparison['forward_overlap']:.3f}  "
            f"rho_diagnostic={comparison['rho_sampled_diagnostic_only']:+.3f}  "
            f"literal_STOP={comparison['literal_pairwise_stop']}"
        )

    audited = [row for row in rows if row.get("status") == "audited"]
    complete_focus_nine = len(audited) == len(TOP) and not any(
        row.get("status") != "audited" for row in rows
    )
    summary = {
        "schema": "wbg2-nine-site-pairwise-diagnostic-v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence_class": "REGISTRY-MEASUREMENT (scoped pairwise comparison; not submit approval)",
        "ours": os.path.relpath(OURS, ROOT),
        "n_audited": len(audited),
        "n_sites": len(rows),
        "sites_not_audited": [row["site"] for row in rows if row.get("status") != "audited"],
        "max_enrichment_diagnostic_only": max(
            (row["enrichment_diagnostic_only"] for row in audited), default=None
        ),
        "max_forward_overlap": max(
            (row["forward_3px_overlap"] for row in audited), default=None
        ),
        "max_abs_sampled_spearman_diagnostic_only": max(
            (abs(row["sampled_spearman_rho_diagnostic_only"]) for row in audited), default=None
        ),
        "literal_pairwise_stop_observed": any(
            row["literal_pairwise_stop"] for row in audited
        ),
        "surface_before_placement_checked": False,
        "global_registry_clearance": False,
        "scope": "Exact nine focus-site artifacts only; not the complete registry and not a pre-placement surface check.",
        "verdict": (
            "PASS_FOCUS9_PAIRWISE_ONLY_NOT_GLOBAL_REGISTRY_CLEARANCE"
            if complete_focus_nine and not any(row["literal_pairwise_stop"] for row in audited)
            else "STOP_OR_INCOMPLETE_FOCUS9_AUDIT_NOT_GLOBAL_CLEARANCE"
        ),
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as output:
        json.dump(summary, output, indent=2, allow_nan=False)
        output.write("\n")
    print("\nscoped verdict:", summary["verdict"])
    print("Global registry clearance: NO; surface-before-placement check: NOT DONE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
