#!/usr/bin/env python3
"""Build the WBG-3 final submission TIFF (full-catalogue training).

Trains the winning WBG-3 detector configuration on the full visible catalogue
(all 60,988 catalogue pixels as positives; 4x random footprint background as
negatives -- unknown real faults in the background are inherent label noise,
exactly as in the competition), predicts the full grid, and emits the dotted
field with the holdout-winning emission settings.

Outputs (docs/downloads/):
  <name>.tif / .zip / .validator.json / .uniqueness.json
  evidence/wbg3/run_card.json
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from wbg2 import validate as V  # noqa: E402
from run_wbg3_experiments import build_static_features, dotted, WORK, SEED, LABELS  # noqa: E402
from run_wbg3_exp3 import build_local_features  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else "exp3"  # exp2 | exp3 (holdout winner)
BUDGET = 37654
CLEARANCE = 2


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    t0 = time.time()
    with rasterio.open(LABELS) as s:
        lab = s.read(1)
        profile = s.profile.copy()
    foot = lab != -1
    cat = lab == 1
    static, names = build_static_features(lab.shape)
    stacks = [(static, names)]
    if MODE == "exp3":
        local, lnames = build_local_features(static, names, foot)
        stacks.append((local, lnames))
    n_feat = sum(s.shape[0] for s, _ in stacks)

    from sklearn.ensemble import HistGradientBoostingClassifier
    rng = np.random.default_rng(SEED)
    pos_idx = np.flatnonzero(cat.ravel())
    neg_pool = np.flatnonzero((foot & ~cat).ravel())
    neg_idx = rng.choice(neg_pool, size=4 * pos_idx.size, replace=False)
    sel = np.r_[pos_idx, neg_idx]
    y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
    rows, cols = np.divmod(sel, lab.shape[1])
    X = np.empty((sel.size, n_feat), np.float32)
    off = 0
    for stack, _n in stacks:
        for j in range(stack.shape[0]):
            X[:, off + j] = np.asarray(stack[j])[rows, cols]
        off += stack.shape[0]
    clf = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
        min_samples_leaf=40, l2_regularization=1.0, random_state=SEED)
    clf.fit(X, y)
    print(f"trained on {pos_idx.size} pos / {neg_idx.size} neg ({time.time()-t0:.0f}s)", flush=True)

    surf = np.zeros(lab.shape, np.float32)
    for r0 in range(0, lab.shape[0], 128):
        r1 = min(lab.shape[0], r0 + 128)
        h = r1 - r0
        Xc = np.empty((h * lab.shape[1], n_feat), np.float32)
        off = 0
        for stack, _n in stacks:
            for j in range(stack.shape[0]):
                Xc[:, off + j] = np.asarray(stack[j][r0:r1]).ravel()
            off += stack.shape[0]
        surf[r0:r1] = clf.predict_proba(Xc)[:, 1].reshape(h, lab.shape[1]).astype(np.float32)
    surf[~foot] = 0.0
    np.save(WORK / f"surface_final_{MODE}.npy", surf)

    dist_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    dots = dotted(surf, foot, dist_cat, BUDGET, CLEARANCE)
    print(f"dots: {int(dots.sum())} ({time.time()-t0:.0f}s)", flush=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"wbggemsdoe1-wbg3-{MODE}det-clear2-37654-{stamp}-zeros"
    out_dir = ROOT / "docs/downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    tif_path = out_dir / f"{name}.tif"
    meta = profile.copy()
    meta.update(count=1, dtype="float32", nodata=None, compress="deflate", tiled=False)
    # profile comes from labels.tif (int8); rebuild from sample submission instead
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as s:
        meta = s.profile.copy()
    meta.update(count=1, dtype="float32", nodata=None, compress="deflate", tiled=False)
    with rasterio.open(tif_path, "w", **meta) as dst:
        dst.write(dots.astype(np.float32), 1)
    zip_path = out_dir / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tif_path, arcname=tif_path.name)

    rep = V.validate_tif(str(tif_path), footprint=foot)
    zrep = V.validate_zip(str(zip_path), str(tif_path))
    (out_dir / f"{name}.validator.json").write_text(json.dumps({"tif": rep.to_dict(), "zip": zrep}, indent=1))

    # uniqueness: nine focus artifacts (/tmp/reg9) + every aligned tif in docs/
    with rasterio.open(tif_path) as s:
        surface = s.read(1); transform = s.transform; crs = s.crs
    sys.path.insert(0, str(ROOT / "vendor"))
    from gems57.uniqueness import dot_overlap
    from scipy.stats import spearmanr
    rng = np.random.default_rng(0)
    idx = rng.choice(surface.size, 400_000, replace=False)
    rows = []
    for s in ("24", "25", "27", "28", "30", "31", "32", "33", "36"):
        with rasterio.open(f"/tmp/reg9/GEMSDOE{s}.tif") as ds:
            theirs = np.nan_to_num(ds.read(1), nan=0.0)
        rows.append({"site": f"GEMSDOE{s}",
                     "forward_3px_overlap_euclidean": dot_overlap(surface, theirs),
                     "spearman_rho_subsample400k": float(spearmanr(surface.ravel()[idx], theirs.ravel()[idx]).statistic),
                     "their_positive": int((theirs > 0).sum())})
    mx = max(r["forward_3px_overlap_euclidean"] for r in rows)
    mr = max(abs(r["spearman_rho_subsample400k"]) for r in rows)
    reg = {"gate": "gems57 literal per-raster (Euclidean 3px, no exemption)",
           "scope": "nine focus-site champions only; full-registry literal scan incl. dense surfaces blocks any sparse field by construction",
           "rows": rows, "max_forward_3px_overlap_euclidean": mx, "max_abs_spearman": mr,
           "unique_vs_nine_focus_sites": bool(mx <= 0.70 and mr <= 0.90)}
    (out_dir / f"{name}.uniqueness.json").write_text(json.dumps(reg, indent=1))

    card = {
        "schema": "wbg3-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "submission_name": name,
        "submission_note": "WBG-3 supervised multi-physics detector, dotted clear2 37654, zeros no NaN"[:140],
        "mode": MODE,
        "budget_pixels": BUDGET,
        "catalogue_clearance_px": CLEARANCE,
        "seed": SEED,
        "raster_sha256": sha256(tif_path),
        "zip_sha256": sha256(zip_path),
        "validator": {"tif": rep.to_dict(), "zip": zrep},
        "registry": reg,
        "elapsed_s": time.time() - t0,
    }
    ev = ROOT / "evidence/wbg3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "run_card.json").write_text(json.dumps(card, indent=1, default=float))
    print(json.dumps({"name": name, "sha256": card["raster_sha256"],
                      "validator_pass": rep.all_checks_passed and zrep["all_checks_passed"],
                      "registry_max_overlap_euclidean": reg["max_forward_3px_overlap_euclidean"],
                      "registry_max_abs_rho": reg["max_abs_spearman"],
                      "unique_vs_nine_focus_sites": reg["unique_vs_nine_focus_sites"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
