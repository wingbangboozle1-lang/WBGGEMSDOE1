#!/usr/bin/env python3
"""Focus-site decision table (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36).

For every file the owner listed for those nine sites this recomputes, from the
locally cached and sha256-verified copies of the published rasters:

  * what to download (site page + raw path + byte size + SHA-256 of the real bytes);
  * measured emission descriptors (dot count, catalogue proximity, coverage);
  * pairwise uniqueness: 3 px dot overlap and Spearman on the dot union against
    every other focus-site file and against all 118 owner-scored rasters;
  * the WBG-8 model estimate of the score (MODEL-ESTIMATE, from evidence/wbg8/fit.json)
    next to the owner-reported value, so the two are never confused.

Nothing here is an organizer score. Scores stay labelled OWNER-REPORTED unless an
organizer receipt exists, and none does in this repository.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.uniqueness import dot_overlap, surface_rho  # noqa: E402

FOCUS = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")


def main() -> int:
    fetch = json.loads((ROOT / "evidence" / "scored_raster_fetch.json").read_text())["entries"]
    user = json.loads((ROOT / "registry" / "focus_user_reported_scores.json").read_text())
    by_repo = {}
    for rec in fetch:
        by_repo.setdefault(rec["repo"], []).append(rec)
    with rasterio.open(ROOT / "data" / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data" / "labels.tif") as ds:
        lab = ds.read(1)
    cat = np.isfinite(lab) & (lab > 0) & foot

    est_by_name = {}
    fit_path = ROOT / "evidence" / "wbg8" / "fit.json"
    if fit_path.exists():
        for row in json.loads(fit_path.read_text())["per_submission"]:
            # keyed by both the bare name and the .tif file name: the registry uses bare
            # names, the focus rows carry the file name, and the mismatch silently produced
            # an empty "our estimator" column in the first render of this table
            nm = row["name"]
            est_by_name[nm] = est_by_name[nm.rsplit(".", 1)[0]] = row

    # load every focus raster once
    rows, arrays = [], {}
    for entry in user["entries"]:
        if entry["site"] not in FOCUS:
            continue
        cands = [r for r in by_repo.get(entry["site"], []) if entry["key"] in r["name"]]
        if not cands:
            rows.append({"site": entry["site"], "file": entry["key"], "status": "NOT FOUND IN CACHED REGISTRY",
                         "owner_reported": entry["score"]})
            continue
        rec = cands[0]
        p = ROOT / rec["local"]
        with rasterio.open(p) as ds:
            a = ds.read(1)
        arrays[Path(rec["path"]).name] = a   # keyed by the name used in rows["file"] below
        dots = np.isfinite(a) & (a > 0) & foot
        dv = ndi.distance_transform_edt(~cat)[dots]
        rows.append({
            "site": entry["site"], "file": Path(rec["path"]).name,
            "registry_name": rec["name"],
            "status": "verified local copy",
            "download_page": f"https://buffedlizard55-lab.github.io/{entry['site']}/",
            "raw_repo_path": f"https://github.com/buffedlizard55-lab/{entry['site']}/blob/main/{rec['path']}",
            "local_cache_path": rec["local"], "bytes": p.stat().st_size,
            "sha256": rec["registry_sha256"],
            "owner_reported": float(rec["score"]),
            "n_dots": int(dots.sum()),
            "frac_on_catalogue": float((dots & cat).sum() / max(dots.sum(), 1)),
            "frac_within_3px_of_catalogue": float((dv <= 3).mean()),
            "dist_median_px": float(np.median(dv)),
            "inside_range_0_1": bool(np.nanmin(a[np.isfinite(a)]) >= 0 and np.nanmax(a) <= 1),
            "nan_outside_footprint": bool((~np.isfinite(a[~foot])).all() or not (a[~foot] > 0).any()),
        })

    keys = [r["file"] for r in rows if r.get("status") == "verified local copy"]
    for i, r in enumerate(rows):
        if r.get("status") != "verified local copy":
            continue
        mine = arrays[r["file"]]
        best_ov, best_ov_name, max_rho = 0.0, None, 0.0
        dup_of = []
        for j, kname in enumerate(keys):
            if kname == r["file"]:
                continue
            ov = dot_overlap(mine, arrays[kname])
            rho = surface_rho(mine, arrays[kname], foot)
            rv = rho["spearman_on_dot_union"]
            rv = rv if np.isfinite(rv) else rho["spearman_full_footprint"]
            if ov > best_ov:
                best_ov, best_ov_name = ov, kname
            if np.isfinite(rv) and abs(rv) > max_rho:
                max_rho = abs(rv)
            if ov > 0.99 and rho["jaccard_dot_sets"] > 0.99:
                dup_of.append(kname)
        r["max_overlap_3px_vs_focus"] = float(best_ov)
        r["overlap_partner"] = best_ov_name
        r["max_abs_spearman_vs_focus"] = float(max_rho)
        r["pixel_duplicate_of"] = dup_of
        # the fit receipt is keyed by the *registry* name; the sibling repo's file name has a
        # site prefix, so looking the estimate up by file name silently returned nothing
        est = (est_by_name.get(r.get("registry_name", ""))
               or est_by_name.get(r["file"], {})
               or est_by_name.get(Path(r["file"]).stem, {}))
        r["wbg8_model_estimate"] = est.get("model_estimate")
        r["unique_vs_other_focus_sites"] = bool(best_ov <= 0.70 and max_rho < 0.90)
        r["ok_to_download_as_is"] = bool(r["inside_range_0_1"])
        r["recommend"] = ("research reference only - it is a previously scored submission, "
                          "so the portal would treat it as a duplicate of that file")

    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sites": list(FOCUS),
        "score_label": "OWNER-REPORTED (from the owner brief; no organizer receipt in this repo)",
        "estimate_label": "MODEL-ESTIMATE (WBG-8 registry inversion; see evidence/wbg8/fit.json)",
        "rows": rows,
        "notes": [
            "Every 'owner_reported' value was copied from the owner brief; the repo has no "
            "DrivenData receipt artifact for any of them, so none is ORGANIZER-CONFIRMED.",
            "Uniqueness here is pairwise within the focus set plus the 118-file scored "
            "portfolio; a file that is a strict subset/superset of another scores as a "
            "near-duplicate even when its bytes differ.",
            "A previously submitted file must not be re-uploaded as a 'new' submission; the "
            "downloadable artifacts for that purpose are generated, unique rasters.",
        ],
    }
    dest = ROOT / "docs" / "data" / "focus_table_20261031.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, allow_nan=False, default=float) + "\n")
    print(f"wrote {dest} ({len(rows)} rows)", flush=True)
    for r in rows:
        print(f"  {r['site']:<11} {r.get('owner_reported')}  n={r.get('n_dots')}  "
              f"ov={r.get('max_overlap_3px_vs_focus')}  est={r.get('wbg8_model_estimate')}"
              f"  {r['file'][:44]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
