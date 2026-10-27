#!/usr/bin/env python3
"""WBG-3 experiments: learned multi-physics fault detector + dotted emission.

Lane (single method): train a HistGradientBoosting detector on the official
19-band GeoDAWN stack + USGS 3DEP LiDAR scarp stack + GeoDAWN radiometrics,
using ONLY the visible catalogue of each SegmentHoldout fold as positives;
emit a budget-matched dotted field with a catalogue clearance and a minimum
dot spacing; score with the shared pooled DTI evaluator
(gems-segment-pooled-v1, alpha=0.2, beta=0.8, R=300 m, whole fault components
hidden with a 1.5 km buffer, visible faults masked pixel-exactly).

Arms (budget: 3 experiments):
  E1 control   clearance >0 px (pixel-exact visible mask only), budget 37654
  E2 candidate clearance >2 px, budget 37654
  E3 candidate clearance >2 px, budget 22000 (precision / smaller budget)

No registry raster is read as a prediction input. Registry rasters are used
only afterwards, for the uniqueness gate.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems.holdout import SegmentHoldout  # noqa: E402
from wbg2.features import decode_lidar  # noqa: E402

WORK = Path("/tmp/wbg3")
WORK.mkdir(parents=True, exist_ok=True)
SEED = 20261027

OFFICIAL = ROOT / "data/training_features.tif"
LIDAR = ROOT / "data/lidar_scarp_features_u8.tif"
RAD = ROOT / "data/geodawn_rad_u8.tif"
EXT = ROOT / "data/geodawn_extensions_u8.tif"
LABELS = ROOT / "data/bridge/labels.tif"

LIDAR_USE = ["step_max", "ex_max", "lapneg_max", "lappos_max", "upface_max",
             "downface_max", "cross_max", "coh100", "relief"]
LIDAR_ALL = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
             "downface_max", "upface_max", "cross_max", "relief", "coh100",
             "strike", "valid"]


def build_static_features(shape) -> tuple[np.lib.format.memmap, list[str]]:
    cache = WORK / "static_features.npy"
    names_path = WORK / "static_feature_names.json"
    H, W = shape
    names: list[str] = []
    # count first
    with rasterio.open(OFFICIAL) as s:
        n_off = s.count
        off_names = [f"official:{d.split(' - ')[0]}" for d in s.descriptions]
    n_feat = n_off + len(LIDAR_USE) + 1 + 4 + 4 + 5
    if cache.exists() and names_path.exists():
        arr = np.lib.format.open_memmap(cache, mode="r", dtype="float32", shape=(n_feat, H, W))
        return arr, json.loads(names_path.read_text())
    arr = np.lib.format.open_memmap(cache, mode="w+", dtype="float32", shape=(n_feat, H, W))
    i = 0
    with rasterio.open(OFFICIAL) as s:
        for b in range(1, n_off + 1):
            a = s.read(b).astype(np.float32)
            a[a < -1e30] = np.nan
            arr[i] = a
            names.append(off_names[b - 1]); i += 1
            del a
    with rasterio.open(LIDAR) as s:
        raw = s.read()
    for nm in LIDAR_USE:
        arr[i] = decode_lidar(raw[LIDAR_ALL.index(nm)], nm); names.append(f"lidar:{nm}"); i += 1
    arr[i] = (raw[LIDAR_ALL.index("valid")] > 0).astype(np.float32); names.append("lidar:valid"); i += 1
    del raw
    for path, tag in ((RAD, "rad"), (EXT, "ext")):
        with rasterio.open(path) as s:
            for b in range(1, 5):
                arr[i] = s.read(b).astype(np.float32); names.append(f"{tag}:{s.descriptions[b-1]}"); i += 1
    # gradient magnitudes (sigma=1.5) of five official bands, NaN filled by footprint mean
    with rasterio.open(LABELS) as s:
        lab = s.read(1)
    foot = lab != -1
    with rasterio.open(OFFICIAL) as s:
        for b, nm in ((15, "depth_to_base_surf"), (17, "cond_surf"), (12, "det_elev"),
                      (13, "iso_grav_anom"), (2, "rtp")):
            a = s.read(b).astype(np.float64)
            a[a < -1e30] = np.nan
            m = np.isfinite(a) & foot
            fill = float(np.nanmean(a[m])) if m.any() else 0.0
            af = np.where(m, a, fill)
            gy, gx = np.gradient(ndi.gaussian_filter(af, 1.5))
            g = np.hypot(gx, gy)
            arr[i] = np.where(foot, g, 0.0).astype(np.float32); names.append(f"gradmag:{nm}"); i += 1
            del a, af, gy, gx, g
    arr.flush()
    names_path.write_text(json.dumps(names))
    return np.lib.format.open_memmap(cache, mode="r", dtype="float32", shape=(n_feat, H, W)), names


def fold_catalogue_features(visible: np.ndarray, sigma=15.0):
    dist = ndi.distance_transform_edt(~visible).astype(np.float32)
    kde = ndi.gaussian_filter(visible.astype(np.float32), sigma)
    if kde.max() > 0:
        kde = (kde / kde.max()).astype(np.float32)
    return dist, kde


def dotted(surface, valid, dist_visible, budget, clearance_px, block_radius=2):
    """Greedy dotted emission: descending surface, Chebyshev spacing block."""
    admissible = valid & (dist_visible > clearance_px) & np.isfinite(surface) & (surface > 0)
    ys, xs = np.nonzero(admissible)
    if ys.size == 0:
        return np.zeros(surface.shape, np.uint8)
    vals = surface[ys, xs]
    # cap candidate pool for speed; budget is << pool in practice
    pool = min(ys.size, max(budget * 30, 200_000))
    if ys.size > pool:
        idx = np.argpartition(vals, -pool)[-pool:]
        ys, xs, vals = ys[idx], xs[idx], vals[idx]
    order = np.argsort(-vals, kind="stable")
    ys, xs = ys[order], xs[order]
    blocked = np.zeros(surface.shape, bool)
    out = np.zeros(surface.shape, np.uint8)
    H, W = surface.shape
    picked = 0
    r = block_radius
    for y, x in zip(ys.tolist(), xs.tolist()):
        if blocked[y, x]:
            continue
        out[y, x] = 1
        blocked[max(0, y - r):min(H, y + r + 1), max(0, x - r):min(W, x + r + 1)] = True
        picked += 1
        if picked >= budget:
            break
    return out


def main() -> int:
    t0 = time.time()
    with rasterio.open(LABELS) as s:
        lab = s.read(1)
    foot = lab != -1
    cat = lab == 1
    feats, names = build_static_features(lab.shape)
    print(f"static features: {feats.shape[0]} in {time.time()-t0:.0f}s", flush=True)
    print(names, flush=True)

    ho = SegmentHoldout(foot, cat)

    # ---- leakage canary: every static feature alone (two polarities) ----
    canary_features = {n: np.asarray(feats[i]) for i, n in enumerate(names)}
    canary = ho.canary(canary_features, max_per_class=8000)
    (WORK / "canary.json").write_text(json.dumps(canary, indent=1))
    print("canary passed:", canary["passed"], "max sym AUC:",
          max(max(v["pooled_auc"], 1 - v["pooled_auc"]) for v in canary["features"].values()), flush=True)

    from sklearn.ensemble import HistGradientBoostingClassifier

    total_foot = int(foot.sum())
    surfaces, fold_data = [], []
    for fold in ho.folds:
        tf = time.time()
        dist_v, kde_v = fold_catalogue_features(fold["visible"])
        train = fold["train"]
        pos_mask = fold["visible"] & train
        neg_pool = train & ~pos_mask
        # IR-WBG3-01 fix: v1 sampled negatives >=9 px from the full catalogue
        # and fed log-distance/KDE-to-visible as features. Positives all sit at
        # distance 0 to the visible set (itself), so those features separated
        # the training classes perfectly and the surface degenerated to a
        # constant off-catalogue (fold AUC 0.500). Catalogue-distance features
        # are therefore dropped from the detector entirely; negatives are now
        # every non-positive train pixel (train is already purged >1.5 km from
        # hidden components, so no hidden fault can be sampled as a negative).
        rng = np.random.default_rng(SEED + fold["id"])
        pos_idx = np.flatnonzero(pos_mask.ravel())
        neg_idx = np.flatnonzero(neg_pool.ravel())
        neg_idx = rng.choice(neg_idx, size=min(neg_idx.size, 4 * pos_idx.size), replace=False)
        sel = np.r_[pos_idx, neg_idx]
        y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
        X = np.empty((sel.size, feats.shape[0]), np.float32)
        rows, cols = np.divmod(sel, lab.shape[1])
        for j in range(feats.shape[0]):
            X[:, j] = np.asarray(feats[j])[rows, cols]
        clf = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
            min_samples_leaf=40, l2_regularization=1.0, random_state=SEED)
        clf.fit(X, y)
        # predict in row chunks
        surf = np.zeros(lab.shape, np.float32)
        F = feats.shape[0]
        for r0 in range(0, lab.shape[0], 128):
            r1 = min(lab.shape[0], r0 + 128)
            h = r1 - r0
            Xc = np.empty((h * lab.shape[1], F), np.float32)
            for j in range(F):
                Xc[:, j] = np.asarray(feats[j][r0:r1]).ravel()
            surf[r0:r1] = clf.predict_proba(Xc)[:, 1].reshape(h, lab.shape[1]).astype(np.float32)
        surf[~foot] = 0.0
        np.save(WORK / f"surface_fold{fold['id']}.npy", surf)
        surfaces.append(surf)
        fold_data.append((fold, dist_v))
        print(f"fold {fold['name']}: train pos {pos_idx.size} neg {neg_idx.size} "
              f"surface done {time.time()-tf:.0f}s", flush=True)

    arms = {
        "E1_control_clear0_budget37654": dict(clearance_px=0, budget=37654),
        "E2_candidate_clear2_budget37654": dict(clearance_px=2, budget=37654),
        "E3_candidate_clear2_budget22000": dict(clearance_px=2, budget=22000),
    }
    results = {}
    arm_preds = {}
    for arm, cfg in arms.items():
        preds = []
        for fold, dist_v in fold_data:
            b = int(round(cfg["budget"] * int((fold["valid"] & foot).sum()) / total_foot))
            p = dotted(surfaces[fold["id"]], fold["valid"] & foot, dist_v, b, cfg["clearance_px"])
            preds.append(p)
        arm_preds[arm] = preds
        res = ho.summarize(preds, ci_draws=999)
        results[arm] = res
        print(arm, "HOLDOUT-DTI", res["dti"], res["ci95"]["interval"], flush=True)

    paired = ho.compare_paired(arm_preds["E2_candidate_clear2_budget37654"],
                               arm_preds["E1_control_clear0_budget37654"],
                               ci_draws=999)
    out = {"evaluator_version": "gems-segment-pooled-v1", "canary_passed": canary["passed"],
           "feature_names": names, "dropped_features_ir_wbg3_01": ["cat:log1p_dist_visible", "cat:kde_visible_sigma15"],
           "arms": results, "paired_E2_vs_E1": paired,
           "elapsed_s": time.time() - t0}
    (WORK / "experiments.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"paired_E2_vs_E1": paired}, indent=1, default=float))
    print(f"DONE {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
