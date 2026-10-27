"""Batched memory-safe execution of shared SegmentHoldout.canary() across all 66 channels."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import rasterio

from gems.holdout import SegmentHoldout
from wbggems1.features import FEATURE_NAMES
from wbggems1.paths import raw_data_dir, repo_root, work_dir


def run_all_feature_canaries(batch_size: int = 6) -> dict[str, Any]:
    rdir = raw_data_dir()
    wdir = work_dir()
    with rasterio.open(rdir / "sample_submission.tif") as tmpl:
        fp = np.isfinite(tmpl.read(1))
    with rasterio.open(rdir / "labels.tif") as lab_ds:
        catalogue = (lab_ds.read(1) > 0) & fp

    ctx = SegmentHoldout(fp, catalogue, buffer_px=15)
    fp_ids = np.flatnonzero(fp.ravel())
    mm = np.load(wdir / "dpgf_features.npy", mmap_mode="r")
    assert mm.shape == (len(fp_ids), len(FEATURE_NAMES))

    all_features: dict[str, Any] = {}
    meta_out: dict[str, Any] = {}
    for start in range(0, len(FEATURE_NAMES), batch_size):
        names_batch = FEATURE_NAMES[start : start + batch_size]
        batch_grids: dict[str, np.ndarray] = {}
        for j, name in enumerate(names_batch, start=start):
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = mm[:, j]
            batch_grids[name] = grid
        res = ctx.canary(batch_grids)
        meta_out = {k: v for k, v in res.items() if k != "features"}
        all_features.update(res["features"])
        del batch_grids

    max_sym_auc = 0.0
    max_feat = None
    for fname, frow in all_features.items():
        p_auc = float(frow["pooled_auc"])
        sym = max(
            [max(p_auc, 1.0 - p_auc)]
            + [max(float(d["auc"]), 1.0 - float(d["auc"])) for d in frow["folds"]]
        )
        if sym > max_sym_auc:
            max_sym_auc = sym
            max_feat = fname

    passed = not any(v["leakage_suspected"] for v in all_features.values())
    out = {
        **meta_out,
        "passed": bool(passed),
        "n_features_tested": len(all_features),
        "max_symmetric_auc": round(max_sym_auc, 6),
        "max_symmetric_auc_feature": max_feat,
        "features": all_features,
    }
    dest = repo_root() / "evidence" / "leakage_canary_66ch.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n")
    return out
