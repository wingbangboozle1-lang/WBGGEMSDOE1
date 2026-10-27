#!/usr/bin/env python
"""Audit WBG-2 against the nine focus sites' artifacts.

Requires the nine focus-site repositories to be cloned outside the repo, e.g.

    git clone --depth 1 https://github.com/buffedlizard55-lab/GEMSDOE24.git /tmp/GEMSDOE24
    ... GEMSDOE25 GEMSDOE27 GEMSDOE28 GEMSDOE30 GEMSDOE31 GEMSDOE33 GEMSDOE36
    git clone --depth 1 https://github.com/buffedlizard55-lab/GEMSDOE32.git /tmp/g32

Usage:
    PYTHONPATH=src .venv/bin/python scripts/wbg2_nine_site_audit.py

Writes evidence/wbg2/nine_site_uniqueness.json and prints a table.

If a clone is missing the site is recorded as NOT AUDITED -- it is never
silently treated as passing.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import rasterio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wbg2 import uniqueness as U  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = os.path.join(ROOT, "docs", "downloads", "wbg2-offcatalogue-density-36k-20261027.tif")
LABELS = os.path.join(ROOT, "data", "bridge", "labels.tif")
OUT = os.path.join(ROOT, "evidence", "wbg2", "nine_site_uniqueness.json")

#: The highest-scoring artifact at each focus site, with the organizer-reported
#: value supplied in the session brief. These are OWNER/USER-REPORTED values,
#: not submission-page receipts.
TOP = {
    "GEMSDOE24": ("/tmp/GEMSDOE24", "h25-1-dotted-h19-5-d1-5", "0.2477"),
    "GEMSDOE25": ("/tmp/GEMSDOE25", "dotted-h19-5-d2-8", "0.2600"),
    "GEMSDOE27": ("/tmp/GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5", "0.2449"),
    "GEMSDOE28": ("/tmp/GEMSDOE28", "h36-1-rung30-blind-r1", "0.2710"),
    "GEMSDOE30": ("/tmp/GEMSDOE30", "d28-poisson300m-offcat-44090", "0.2600"),
    "GEMSDOE31": ("/tmp/GEMSDOE31", "h27-4-solo-d28", "0.2708"),
    "GEMSDOE32": ("/tmp/g32", "h33-h33-2-b2", "0.2778"),
    "GEMSDOE33": ("/tmp/GEMSDOE33", "h33d-analog-tip-stepover-r30", "0.2632"),
    "GEMSDOE36": ("/tmp/GEMSDOE36", "anderson-geothermal-pinn-38854", "0.2750"),
}


def find_artifact(root: str, key: str) -> str | None:
    best = None
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if key in fn and fn.lower().endswith(".tif"):
                # prefer the upload-ready variant
                score = 0
                if "zeros" in fn:
                    score += 2
                if "allfinite" in fn or "nanoutside" in fn:
                    score += 1
                if "nan" in fn:
                    score -= 1
                if best is None or score > best[0]:
                    best = (score, os.path.join(dirpath, fn))
    return best[1] if best else None


def main() -> int:
    with rasterio.open(LABELS) as src:
        labels = src.read(1)
        transform, crs = src.transform, src.crs
    footprint = labels != -1
    catalogue = labels == 1

    with rasterio.open(OURS) as src:
        ours = src.read(1).astype(np.float32)
    ours = np.nan_to_num(ours)

    rows = []
    for site, (root, key, reported) in TOP.items():
        path = find_artifact(root, key) if os.path.isdir(root) else None
        row = {
            "site": site,
            "owner_reported_score": float(reported),
            "expected_artifact": key,
            "audited": path is not None,
        }
        if path is None:
            row["status"] = "NOT AUDITED - repository clone missing"
            rows.append(row)
            print(f"{site:10s} NOT AUDITED (clone missing)")
            continue
        theirs = U.load_aligned(path, labels.shape, transform, crs)
        if theirs is None:
            row["status"] = "NOT AUDITED - grid mismatch"
            rows.append(row)
            print(f"{site:10s} NOT AUDITED (grid mismatch)")
            continue
        c = U.compare(ours, theirs, evaluated=footprint)
        pos = theirs > 0
        row.update({
            "artifact": os.path.basename(path),
            "their_positive_pixels": int(pos.sum()),
            "their_fraction_within_3px_of_catalogue": float(
                (pos & U.ndi.binary_dilation(catalogue, U.ndi.generate_binary_structure(2, 1), iterations=3)).sum()
            ) / max(1, int(pos.sum())),
            "their_fraction_on_catalogue": float((pos & catalogue).sum()) / max(1, int(pos.sum())),
            "forward_3px_overlap": c["forward_overlap"],
            "chance_overlap": c["chance_overlap"],
            "enrichment_vs_chance": c["enrichment"],
            "spearman_rho": c["rho"],
            "status": "audited",
        })
        rows.append(row)
        print(
            f"{site:10s} score={reported}  their_pos={int(pos.sum()):6d}  "
            f"near3cat={row['their_fraction_within_3px_of_catalogue']:.3f}  "
            f"overlap={c['forward_overlap']:.3f}  chance={c['chance_overlap']:.3f}  "
            f"enrich={c['enrichment']:.2f}  rho={c['rho']:+.3f}"
        )

    audited = [r for r in rows if r.get("status") == "audited"]
    summary = {
        "schema": "wbg2-nine-site-uniqueness-v1",
        "generated_utc": "2026-10-27",
        "ours": os.path.relpath(OURS, ROOT),
        "n_audited": len(audited),
        "n_sites": len(rows),
        "sites_not_audited": [r["site"] for r in rows if r.get("status") != "audited"],
        "max_enrichment_vs_chance": max((r["enrichment_vs_chance"] for r in audited), default=None),
        "max_forward_overlap": max((r["forward_3px_overlap"] for r in audited), default=None),
        "max_abs_spearman": max((abs(r["spearman_rho"]) for r in audited), default=None),
        "verdict": None,
        "rows": rows,
    }
    if audited:
        e = summary["max_enrichment_vs_chance"]
        o = summary["max_forward_overlap"]
        rho = summary["max_abs_spearman"]
        dup = (rho > U.STOP_RHO) or (o > U.STOP_OVERLAP and e >= U.STOP_ENRICHMENT)
        summary["verdict"] = "DUPLICATE - STOP" if dup else "UNIQUE vs all audited focus sites"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(summary, f, indent=1)
    print("\nverdict:", summary["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
