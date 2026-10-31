#!/usr/bin/env python3
"""Audit the eleven named focus-site rasters (nine GEMSDOE sites) on this checkout.

Every number written here carries one of three labels:
  HOLDOUT-DTI   -- gems57.holdout.evaluate (shared hide-and-recover), seeds 20,21, mode "all";
                   n = pooled withheld positives; 95% CI = percentile bootstrap over the
                   fold cells (2 seeds x 4 quadrants). Fold-cell CI, NOT the 20 km block CI.
  OVERLAP       -- literal parallel-run statistic from the protocol (>70% of dots within 3 px of
                   one registry raster's dots = duplicate) and the density-matched lift.
  DATA-CHECK    -- format facts read from the raster bytes.
Nothing here is an organizer score. ORGANIZER-CONFIRMED is only copied from a receipt.

Usage: .venv/bin/python scripts/session_audit_20261031.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import build_holdout, evaluate  # noqa: E402
from gems57.metric import RADIUS_PX  # noqa: E402

OUT = ROOT / "evidence/session_20261031"

# The eleven files named in the 29 Oct executive summary, identified by SHA-256 prefix.
NAMED = {
    "GEMSDOE32 B2 (user-reported 0.2778)": "c55bafc470054e82",
    "GEMSDOE36 pinn (0.2750)": "e15891020b9c5705",
    "GEMSDOE28 rung30 (0.2710)": "5556aa1438fd6737",
    "GEMSDOE28 solo D2.8 (0.2708)": "ab02300152248fdd",
    "GEMSDOE31 solo D28 (0.2708)": "07b6db440535404b",
    "GEMSDOE28 hf-euler (0.2707)": "81d5b87bc8424f16",
    "GEMSDOE33 analog-tip (0.2632)": "87f857d505e23247",
    "GEMSDOE25 D2.8 (0.2600)": "91eae1ca42ec845e",
    "GEMSDOE30 poisson (0.2600)": "8cf893ead5667df2",
    "GEMSDOE27 topo-gap (0.2449)": "33003374335d84bf",
    "GEMSDOE24 H25-1 (0.2477)": "68d0e2e4fcc594f9",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def registry_entries() -> list[dict]:
    manifest = json.loads((ROOT / "registry/focus_raster_fetch.json").read_text())
    rows = [e for e in manifest["entries"] if e.get("local")]
    for e in rows:
        e["path_abs"] = ROOT / e["local"]
    return rows


def format_check(path: Path, grid) -> dict:
    with rasterio.open(path) as src:
        a = src.read(1)
        ok_crs = str(src.crs) == "EPSG:32611"
        ok_shape = (src.height, src.width) == grid.shape
        ok_tf = tuple(src.transform)[:6] == tuple(grid.transform)[:6]
        dtype, count, nodata = src.dtypes[0], src.count, src.nodata
    finite = np.isfinite(a)
    fp = grid.footprint
    inside_ok = bool(finite[fp].all())
    values_in_01 = bool(((a[finite] >= 0) & (a[finite] <= 1)).all())
    return dict(
        dtype=dtype, bands=count, nodata=None if nodata is None else float(nodata),
        crs_ok=ok_crs, shape_ok=ok_shape, transform_ok=ok_tf,
        finite_inside_footprint=inside_ok,
        finite_outside_footprint=int((finite & ~fp).sum()),
        nan_outside_footprint=int((~finite & ~fp).sum()),
        values_in_0_1=values_in_01,
        min=float(np.nanmin(a)), max=float(np.nanmax(a)),
        positive_dots=int((finite & (a > 0)).sum()),
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    grid = load_grid(ROOT / "data/bridge")
    registry = registry_entries()
    print(f"registry rasters with local copies: {len(registry)}", flush=True)

    # Resolve named files by SHA prefix, then verify the bytes again.
    named = {}
    for label, prefix in NAMED.items():
        hits = [e for e in registry if e["sha256"].startswith(prefix)]
        if not hits:
            raise SystemExit(f"missing named file {label} ({prefix})")
        e = hits[0]
        digest = sha256(e["path_abs"])
        if digest != e["sha256"]:
            raise SystemExit(f"hash mismatch {label}")
        named[label] = dict(path=e["path_abs"], sha256=digest, repo=e["repo"], rel=e["path"])

    # Candidate dot sets and format facts.
    dots = {}
    fmt = {}
    for label, rec in named.items():
        with rasterio.open(rec["path"]) as src:
            a = src.read(1)
        dots[label] = np.isfinite(a) & (a > 0) & grid.footprint
        fmt[label] = format_check(rec["path"], grid)
        rec["n_dots"] = int(dots[label].sum())

    # Holdout (shared code, unchanged).
    ctx = build_holdout(grid, seeds=(20, 21), modes=("all",))
    holdout = {}
    for label in named:
        res = evaluate(dots[label], ctx)
        cells = [c for c in res["folds"].values()]
        tp = np.array([c["tp"] for c in cells])
        fp = np.array([c["fp"] for c in cells])
        fn = np.array([c["fn"] for c in cells])
        rng = np.random.default_rng(20261031)
        boots = []
        for _ in range(2000):
            idx = rng.integers(0, len(cells), len(cells))
            t, f, n = tp[idx].sum(), fp[idx].sum(), fn[idx].sum()
            boots.append(t / (t + 0.2 * f + 0.8 * n + 1e-12))
        lo, hi = np.quantile(boots, [0.025, 0.975])
        holdout[label] = dict(
            evidence_class="HOLDOUT-DTI",
            evaluator="gems57.holdout.evaluate (seeds 20,21; mode all; alpha 0.2 beta 0.8; 300 m triangular)",
            evaluator_sha256=hashlib.sha256((ROOT / "vendor/gems57/holdout.py").read_bytes()).hexdigest(),
            pooled_dti=float(res["pooled_dti"]),
            n_withheld_positives=int(res["pooled_n_truth"]),
            ci95_fold_bootstrap=[float(lo), float(hi)],
            fold_cells=len(cells),
            emitted_on_visible_catalogue=int(res["on_visible_catalogue"]),
        )
        print(f"HOLDOUT {label}: {res['pooled_dti']:.4f} CI [{lo:.4f},{hi:.4f}] n={res['pooled_n_truth']}", flush=True)

    # Literal overlap and density-matched lift against every local registry raster.
    overlap = {label: [] for label in named}
    phi = {label: [] for label in named}
    for e in registry:
        with rasterio.open(e["path_abs"]) as src:
            r = src.read(1)
        t = np.isfinite(r) & (r > 0)
        if not t.any():
            continue
        near = distance_transform_edt(~t) <= RADIUS_PX   # disk of radius 3 px
        coverage = float(near[grid.footprint].mean())
        for label in named:
            if e["sha256"] == named[label]["sha256"]:
                continue  # identical file (self-match) is not a registry comparison
            m = dots[label]
            if not m.any():
                continue
            ov = float(near[m].mean())
            overlap[label].append(dict(repo=e["repo"], path=e["path"], overlap=ov,
                                       lift=ov / coverage if coverage else float("nan"),
                                       registry_coverage=coverage,
                                       identical_positive_set=bool(np.array_equal(m, t & grid.footprint))))
            # phi (Pearson on 0/1 indicators) from integer counts over the footprint.
            tf = t & grid.footprint
            n_all = int(grid.footprint.sum())
            n1, n2 = int(m.sum()), int(tf.sum())
            n12 = int(np.count_nonzero(m & tf))
            den = math.sqrt(float(n1) * float(n_all - n1) * float(n2) * float(n_all - n2))
            phi[label].append(float((n_all * n12 - n1 * n2) / den) if den > 0 else 0.0)
    summary = {}
    for label in named:
        rows = overlap[label]
        ovs = np.array([x["overlap"] for x in rows])
        summary[label] = dict(
            evidence_class="OVERLAP",
            registry_rasters_compared=len(rows),
            max_literal_overlap=float(ovs.max()),
            n_rasters_over_70pct_literal=int((ovs > 0.70).sum()),
            median_literal_overlap=float(np.median(ovs)),
            median_density_matched_lift=float(np.median([x["lift"] for x in rows])),
            max_phi_binary_rank_proxy=float(max(phi[label])),
            n_rasters_phi_over_0_90=int(sum(p > 0.90 for p in phi[label])),
            identical_positive_set_registry_matches=[x["repo"] + "/" + x["path"] for x in rows if x["identical_positive_set"]],
            worst_five=sorted(({"repo": x["repo"], "path": x["path"], "overlap": x["overlap"]} for x in rows),
                              key=lambda z: -z["overlap"])[:5],
        )
        print(f"OVERLAP {label}: max {summary[label]['max_literal_overlap']:.4f}, "
              f">70% in {summary[label]['n_rasters_over_70pct_literal']}/{len(rows)}", flush=True)

    result = dict(
        generated_by="scripts/session_audit_20261031.py",
        registry_rasters_scanned=len(registry),
        rule_text="PROMPT.md LANE: >70% of dots within 3 px of one registry raster's dots = duplicate",
        files={label: dict(sha256=named[label]["sha256"], repo=named[label]["repo"], path=named[label]["rel"],
                           n_dots=named[label]["n_dots"], format=fmt[label],
                           holdout=holdout[label], overlap=summary[label])
               for label in named},
        organizer_confirmed="NONE",
    )
    (OUT / "focus_audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"wrote {OUT / 'focus_audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
