#!/usr/bin/env python3
"""Audit nine frozen owner repositories; never copy their predictions into a model.

Snapshots are restored by scripts/fetch_repositories.py. Historical scores are
explicitly unverified USER-REPORTED claims, not computed or organizer-confirmed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
import numpy as np
import rasterio
from scipy import ndimage as ndi
from gems57 import uniqueness
from wbggems.audit import dump_json, sha256, utc_now

SITE_FILES = {
    "GEMSDOE24": ("gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", .2477),
    "GEMSDOE25": ("gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", .2600),
    "GEMSDOE27": ("gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", .2449),
    "GEMSDOE28": ("gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", .2710),
    "GEMSDOE30": ("gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", .2600),
    "GEMSDOE31": ("gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", .2708),
    "GEMSDOE32": ("gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", .2778),
    "GEMSDOE33": ("GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", .2632),
    "GEMSDOE36": ("gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", .2750),
}


def read_aligned(path, ref):
    with rasterio.open(path) as src:
        if src.count != 1 or (src.shape, src.crs, src.transform) != ref:
            raise ValueError(f"not an aligned single-band prediction: {path}")
        a = src.read(1).astype(np.float32)
    return a


def main():
    cache = ROOT / ".cache/research"
    with rasterio.open(ROOT / "data/sample_submission.tif") as src:
        ref = (src.shape, src.crs, src.transform)
        fp = np.isfinite(src.read(1))
    with rasterio.open(ROOT / "data/labels.tif") as src:
        cat = src.read(1) > 0
    snapshots, inventory, rows, masks = {}, [], [], {}
    seen_files = {}
    for repo, (file, claimed_score) in SITE_FILES.items():
        tree = json.loads((cache / f"{repo}-tree.json").read_text())
        if tree.get("truncated"):
            raise ValueError(f"truncated Git tree for {repo}; cannot certify inventory")
        # A git-tree SHA is not a commit SHA. Use the explicitly resolved
        # immutable commit pin, never infer it from the tree endpoint's `sha`.
        commit = tree.get("commit_sha")
        if not commit:
            pins = json.loads((ROOT / "registry/repository_snapshots.json").read_text())["repositories"]
            commit = next(p["ref"] for p in pins if p["repo"] == f"buffedlizard55-lab/{repo}")
        snapshots[repo] = commit
        snapshot_url = f"https://github.com/buffedlizard55-lab/{repo}/tree/{commit}"
        path = cache / repo / "docs/downloads" / file
        a = read_aligned(path, ref)
        values = np.where(np.isfinite(a) & fp, a, 0).astype(np.float32)
        masks[repo] = values > 0
        decoded_hash = hashlib.sha256(values.tobytes()).hexdigest()
        rows.append({"site": repo, "snapshot_sha": commit, "snapshot_url": snapshot_url,
                     "file": file, "download_url": f"https://buffedlizard55-lab.github.io/{repo}/docs/downloads/{file}",
                     "immutable_file_url": f"https://github.com/buffedlizard55-lab/{repo}/blob/{commit}/docs/downloads/{file}",
                     "reported_historical_value": claimed_score,
                     "historical_value_evidence_class": "USER-REPORTED; NOT ORGANIZER-CONFIRMED",
                     "organizer_submission_receipt": None, "leaderboard_estimate": None,
                     "sha256": sha256(path), "decoded_in_footprint_sha256": decoded_hash,
                     "dots": int(masks[repo].sum()), "known_fault_positive_pixels": int((masks[repo] & cat).sum()),
                     "already_historical_submission": True, "recommended_new_submission": False,
                     "raw_score_source": "User prompt supplied in this session; owner repo repeats the claim but supplies no independently authenticated portal receipt."})
        for blob in tree["tree"]:
            relative = blob["path"]
            if blob["type"] != "blob" or not relative.lower().endswith((".tif", ".tiff")):
                continue
            # Training/official/external layers are not a prior prediction registry.
            if relative.startswith(("data/", "vendor/")):
                continue
            p = cache / repo / relative
            try:
                with rasterio.open(p) as ds:
                    aligned = ds.count == 1 and (ds.shape, ds.crs, ds.transform) == ref
                if not aligned:
                    continue
                content = p.read_bytes()
                blob_digest = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
                if blob_digest != blob["sha"]:
                    raise ValueError("cached file does not match the pinned Git blob identity")
                digest = hashlib.sha256(content).hexdigest()
                del content
                source = {"repo": repo, "ref": commit, "path": relative,
                          "git_blob_identity_verified": True,
                          "git_blob_sha": blob["sha"], "bytes": p.stat().st_size,
                          "sha256": digest, "immutable_url": f"https://github.com/buffedlizard55-lab/{repo}/blob/{commit}/{relative}"}
                inventory.append(source)
                if digest not in seen_files:
                    seen_files[digest] = {"repo_first": repo, "sha256": digest,
                        "cache_file": str(p.relative_to(ROOT)), "sources": [f"{repo}:{relative}"]}
                else:
                    seen_files[digest]["sources"].append(f"{repo}:{relative}")
            except (OSError, ValueError, rasterio.errors.RasterioError) as e:
                inventory.append({"repo": repo, "ref": commit, "path": relative, "error": str(e)})
    # Dilation uses the unchanged shared gate. Cache one support halo per site,
    # not a private alternative novelty metric.
    near = {repo: uniqueness._near(mask) for repo, mask in masks.items()}
    comparisons = []
    for row in rows:
        mine = masks[row["site"]]
        others = []
        for other in rows:
            if row["site"] == other["site"]:
                continue
            theirs = masks[other["site"]]
            overlap = float(near[other["site"]][mine].mean())
            same = bool(np.array_equal(mine, theirs))
            others.append({"site": other["site"], "same_decoded_predictions": row["decoded_in_footprint_sha256"] == other["decoded_in_footprint_sha256"],
                           "same_dot_set": same, "forward_3px_overlap": overlap,
                           "intersection_dots": int((mine & theirs).sum()),
                           "jaccard": float((mine & theirs).sum() / (mine | theirs).sum())})
        row["exact_dot_duplicates_at_other_focus_champions"] = [r["site"] for r in others if r["same_dot_set"]]
        row["pixel_distinct_among_other_focus_champions"] = not row["exact_dot_duplicates_at_other_focus_champions"]
        row["maximum_forward_3px_overlap_vs_other_focus_champions"] = max(r["forward_3px_overlap"] for r in others)
        row["passes_literal_overlap_among_focus_champions"] = all(r["forward_3px_overlap"] <= .7 for r in others)
        comparisons.append({"site": row["site"], "comparisons": others})
    distances = ndi.distance_transform_edt(~cat)
    d28, b1, b2, anderson = (masks[k] for k in ("GEMSDOE25", "GEMSDOE31", "GEMSDOE32", "GEMSDOE36"))
    lineage = {
        "evidence_class": "RASTER-MEASUREMENT", "not_a_holdout_or_leaderboard_score": True,
        "d28_dots": int(d28.sum()), "b1_dots": int(b1.sum()), "b2_dots": int(b2.sum()),
        "d28_equals_gems30": bool(np.array_equal(d28, masks["GEMSDOE30"])),
        "b1_equals_d28_pruned_at_distance_le_1px": bool(np.array_equal(b1, d28 & (distances > 1))),
        "b2_equals_b1_pruned_at_distance_le_2px": bool(np.array_equal(b2, b1 & (distances > 2))),
        "b2_equals_d28_pruned_at_distance_le_2px": bool(np.array_equal(b2, d28 & (distances > 2))),
        "b0_to_b1_removed": int((d28 & ~b1).sum()), "b1_to_b2_removed": int((b1 & ~b2).sum()),
        "anderson_contains_every_b2_dot": bool(not (b2 & ~anderson).any()),
        "anderson_added_dots_to_b2": int((anderson & ~b2).sum()),
        "caution": "Subset identities are measured. No hidden labels are available to prove why removed dots changed a historical score. A 200 m exclusion is not an organizer rule or universal geological principle."
    }
    errors = [r for r in inventory if "error" in r]
    index = {"generated_utc": utc_now(), "evidence_class": "REGISTRY-MEASUREMENT", "snapshots": snapshots,
             "scope": "All tracked aligned single-band TIFFs outside data/ and vendor/ in nine frozen owner snapshots. Includes archives, research artifacts and calibration priors. Not all 92 user-listed sites, hidden/private rasters, releases or later commits.",
             "complete_accessible_scan": not errors, "errors": errors, "files_indexed": len(inventory),
             "n_unique_file_hashes": len(seen_files), "rasters": list(seen_files.values())}
    dump_json(ROOT / "registry/focus_inventory.json", index)
    dump_json(ROOT / "registry/focus_files.json", {"generated_utc": utc_now(), "snapshots": snapshots, "files": inventory})
    dump_json(ROOT / "registry/repository_snapshots.json", {"generated_utc": utc_now(), "repositories": [
        {"repo": f"buffedlizard55-lab/{r}", "ref": s, "tarball_url": f"https://codeload.github.com/buffedlizard55-lab/{r}/tar.gz/{s}"}
        for r, s in snapshots.items()]})
    summary = {"generated_utc": utc_now(), "evidence_class": "USER-REPORTED-HISTORICAL-CLAIMS + RASTER-MEASUREMENTS",
               "score_warning": "Historical values are not organizer-confirmed and not HOLDOUT-DTI. No estimated leaderboard score is available.",
               "rows": sorted(rows, key=lambda r: (-r["reported_historical_value"], r["site"])),
               "lineage": lineage, "pairwise_champion_comparisons": comparisons,
               "inventory": {"files_indexed": len(inventory), "unique_file_hashes": len(seen_files), "errors": errors},
               "promotion_recommendation": "No historical file should be copied and presented as a new unique submission."}
    dump_json(ROOT / "evidence/nine_site_audit.json", summary)
    print(json.dumps(lineage, indent=2))
    print(f"Indexed {len(inventory)} source paths / {len(seen_files)} unique file hashes")


if __name__ == "__main__":
    main()
