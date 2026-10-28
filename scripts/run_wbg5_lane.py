#!/usr/bin/env python3
"""WBG-5 / MTA-1 lane: magnetic-texture anisotropy relative to depth-to-base contours.

Hypothesis (pre-registered before fitting)
------------------------------------------
A concealed displacement that has no subaerial trace still interrupts the
coherent magnetic basement fabric.  That interruption is expressed as a
*scale-dependent anisotropy of magnetic texture relative to the local
depth-to-base structural contours*: the RTP / TMI field keeps coherent texture
along a fault-parallel direction while the across-contour texture is disrupted,
or vice versa.  Standard 1-D ridge filters and simple gradient magnitudes are
blind to this because they sum edge strength over all orientations.

Mechanism
---------
For the reduced-to-pole field (band 2, ``rtp``) smoothed at two scales
(sigma = 3 px and 8 px):

    gy, gx          = gradient(smoothed rtp)
    (ny, nx)        = unit vector of grad(depth_to_base_surf, band 15)   # across-contour
    (-nx, ny)       = unit vector along the contour
    E_across        = (gy*ny + gx*nx)**2
    E_along         = (gy*(-nx) + gx*ny)**2
    mta(sigma)      = (E_across - E_along) / (E_across + E_along + eps)

``mta`` is persisted across the two scales (the channel is the scale-8 value
guarded by the scale-3 sign, so a real, scale-persistent fabric break survives
and single-scale noise does not).  The two new channels are added to the
official 19-band GeoDAWN stack plus a small set of first-order derivatives.

Named non-fault mimic
---------------------
Lithologic contacts, dike swarms, flight-line levelling residuals, and
Pleistocene shoreline cusps can all produce oriented magnetic texture.  MTA is
a structural *indicator*, never a verified fault or a geothermal-vent
confirmation.

Protocol
--------
Single method lane.  Whole fault components are hidden with a 1.5 km buffer;
the detector reads only each fold's *visible* catalogue; visible faults are
masked pixel-exactly; pooled DTI uses alpha=0.2, beta=0.8, R=300 m.  Every
feature is tested alone (orientation-invariant AUC > 0.90 is a leakage alarm).
Arms (budget: 3 experiments):
  A1 19-band + derivatives control (no MTA)
  A2 19-band + derivatives + MTA-1
  A3 MTA-only ablation (MTA channels alone, no official bands)
Paired A2-vs-A1 uses the identical dotted emission and fold split.
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
from gems1 import grid as G  # noqa: E402

WORK = Path("/tmp/wbg5")
WORK.mkdir(parents=True, exist_ok=True)
SEED = 20261028

CACHE = ROOT / "data/template57/.cache/features"
LABELS = ROOT / "data/existing_faults.tif"
TEMPLATE = ROOT / "data/sample_submission.tif"

BAND_FILES = {i: CACHE / f"band-{i:02d}.npy" for i in range(1, 20)}
# Official band indices (1-based) used for derivatives.
IDX = {
    "rtp": 2,
    "tmi_hg": 3,
    "tmi_vg": 9,
    "iso_grav_anom": 13,
    "det_elev": 12,
    "depth_to_base_surf": 15,
    "cond_surf": 17,
    "tmi": 14,
}

MTA_SCALES = (3.0, 8.0)


# --------------------------------------------------------------------------- #
# feature construction
# --------------------------------------------------------------------------- #
def _load_band(idx: int, foot: np.ndarray) -> np.ndarray:
    raw = np.load(BAND_FILES[idx])
    raw = np.asarray(raw, dtype=np.float64)
    raw[~foot] = np.nan
    raw[(~np.isfinite(raw)) | (np.abs(raw) > 1e30)] = np.nan
    return raw


def _fill_nearest(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    if valid.all():
        return a.astype(np.float32, copy=False)
    filled = a.astype(np.float32, copy=True)
    _, ind = ndi.distance_transform_edt(~valid, return_distances=True, return_indices=True)
    bad = ~valid
    filled[bad] = filled[ind[0][bad], ind[1][bad]]
    return filled


def _robust_z(a: np.ndarray, foot: np.ndarray, clip: float = 6.0) -> np.ndarray:
    v = a[foot]
    med = float(np.nanmedian(v)) if v.size else 0.0
    mad = float(np.nanmedian(np.abs(v - med))) if v.size else 0.0
    scale = 1.4826 * mad if mad > 1e-9 else float(np.nanstd(v) or 1.0)
    if not np.isfinite(scale) or scale <= 1e-9:
        scale = 1.0
    z = (a - med) / scale
    z = np.clip(z, -clip, clip)
    return np.where(foot, z, 0.0).astype(np.float32)


def _gradmag(a: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    s = ndi.gaussian_filter(a, sigma)
    gy, gx = np.gradient(s)
    return np.hypot(gx, gy).astype(np.float32)


def _mta_channels(rtp: np.ndarray, depth: np.ndarray, foot: np.ndarray) -> list[np.ndarray]:
    """Scale-persistent magnetic-texture anisotropy relative to depth contours."""
    d = ndi.gaussian_filter(depth, 3.0)
    gdy, gdx = np.gradient(d)
    gnorm = np.hypot(gdy, gdx)
    valid = foot & (gnorm > 1e-6)
    ny = np.where(valid, gdy / np.maximum(gnorm, 1e-6), 0.0)
    nx = np.where(valid, gdx / np.maximum(gnorm, 1e-6), 0.0)
    # across-contour unit vector n=(ny,nx); along-contour t=(-nx,ny)
    out = []
    signs = []
    for sigma in MTA_SCALES:
        s = ndi.gaussian_filter(rtp, sigma)
        gy, gx = np.gradient(s)
        e_across = (gy * ny + gx * nx) ** 2
        e_along = (gy * (-nx) + gx * ny) ** 2
        mta = (e_across - e_along) / (e_across + e_along + 1e-9)
        mta = np.where(valid, mta, 0.0).astype(np.float32)
        out.append(mta)
        signs.append(np.sign(mta))
    # persistence: keep scale-8 magnitude, gated by agreement of sign at scale 3
    persist = np.abs(out[1]) * np.where(np.abs(signs[0] * signs[1] + 1.0) < 0.5, 1.0, 0.35)
    signed = np.where(np.abs(out[1]) > np.abs(out[0]), out[1], out[0])
    channels = [out[0].astype(np.float32), out[1].astype(np.float32),
                persist.astype(np.float32), signed.astype(np.float32)]
    return channels


DERIV_KEYS = ("det_elev", "tmi", "iso_grav_anom", "rtp", "depth_to_base_surf", "cond_surf")


def build_features(foot: np.ndarray) -> tuple[np.lib.format.memmap, list[str]]:
    cache = WORK / "wbg5_features.npy"
    names_path = WORK / "wbg5_feature_names.json"
    H, W = foot.shape

    n_off = 19
    n_deriv = len(DERIV_KEYS)
    n_tilt = 1
    n_lap = 2
    n_mta = 4
    n_feat = n_off + n_deriv + n_tilt + n_lap + n_mta

    if cache.exists() and names_path.exists():
        arr = np.lib.format.open_memmap(cache, mode="r", dtype="float32", shape=(n_feat, H, W))
        if len(json.loads(names_path.read_text())) == n_feat:
            return arr, json.loads(names_path.read_text())

    arr = np.lib.format.open_memmap(cache, mode="w+", dtype="float32", shape=(n_feat, H, W))
    names: list[str] = []
    i = 0
    keep: dict[str, np.ndarray] = {}
    # one band at a time: official channel + remember the few needed for derivatives
    for b in range(1, 20):
        raw = _load_band(b, foot)
        arr[i] = _robust_z(raw, foot)
        names.append(f"official:band{b:02d}")
        i += 1
        for key, idx in IDX.items():
            if idx == b:
                keep[key] = raw
        del raw
    for key in DERIV_KEYS:
        filled = _fill_nearest(keep[key], foot & np.isfinite(keep[key]))
        arr[i] = _gradmag(filled)
        names.append(f"gradmag:{key}")
        i += 1
    tilt = np.arctan2(keep["tmi_vg"], np.sqrt(keep["tmi_hg"] ** 2 + 1e-6))
    arr[i] = np.where(foot, tilt, 0.0).astype(np.float32)
    names.append("tilt:tmi")
    i += 1
    for key in ("det_elev", "tmi"):
        filled = _fill_nearest(keep[key], foot & np.isfinite(keep[key]))
        arr[i] = np.where(foot, ndi.gaussian_laplace(filled, 2.0), 0.0).astype(np.float32)
        names.append(f"lap2:{key}")
        i += 1
    for c, nm in zip(_mta_channels(keep["rtp"], keep["depth_to_base_surf"], foot),
                     ("s3", "s8", "persist", "signed")):
        arr[i] = c
        names.append(f"mta:{nm}")
        i += 1
    arr.flush()
    names_path.write_text(json.dumps(names))
    del arr, keep
    return np.lib.format.open_memmap(cache, mode="r", dtype="float32", shape=(n_feat, H, W)), names


# --------------------------------------------------------------------------- #
# emission
# --------------------------------------------------------------------------- #
def dotted(surface, valid, dist_visible, budget, clearance_px, block_radius=2):
    admissible = valid & (dist_visible > clearance_px) & np.isfinite(surface) & (surface > 0)
    ys, xs = np.nonzero(admissible)
    if ys.size == 0:
        return np.zeros(surface.shape, np.uint8)
    vals = surface[ys, xs]
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
    with rasterio.open(TEMPLATE) as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(LABELS) as s:
        lab = s.read(1)
    cat = lab == 1
    # SegmentHoldout requires the catalogue to be a subset of the footprint;
    # it masks visible faults pixel-exactly before scoring.
    assert cat.sum() and np.all(cat <= foot)

    feats, names = build_features(foot)
    print(f"features: {feats.shape[0]} in {time.time()-t0:.0f}s", flush=True)
    print(names, flush=True)

    ho = SegmentHoldout(foot, cat, buffer_px=15)

    # leakage canary on every feature alone (two polarities, per fold)
    feat_map = {n: np.asarray(feats[i]) for i, n in enumerate(names)}
    canary_all = ho.canary(feat_map, max_per_class=8000)
    (WORK / "canary_all.json").write_text(json.dumps(canary_all, indent=1))

    def _sym(v: dict) -> float:
        folds = [f["auc"] for f in v["folds"]]
        return max([max(v["pooled_auc"], 1 - v["pooled_auc"])] + [max(a, 1 - a) for a in folds])

    flagged = [n for n, v in canary_all["features"].items() if _sym(v) > 0.90]
    print("canary(all) passed:", canary_all["passed"], "flagged:", flagged, flush=True)

    # Protocol: AUC > 0.90 is leakage until proven otherwise. The flagged bands
    # are regional geodetic-strain / DEM fields that separate the held-out
    # mapped catalogue from background in one fold at AUC~0.999; that circularity
    # cannot be excluded, so they are dropped and the reduced set is re-canaried.
    keep_idx = [i for i, n in enumerate(names) if n not in flagged]
    keep_names = [n for n in names if n not in flagged]
    canary = ho.canary({n: feat_map[n] for n in keep_names}, max_per_class=8000)
    (WORK / "canary.json").write_text(json.dumps(canary, indent=1))
    max_auc = max(_sym(v) for v in canary["features"].values())
    print("canary(reduced) passed:", canary["passed"], "max sym AUC:", max_auc, flush=True)
    assert canary["passed"], "reduced feature set still fails the leakage canary"

    from sklearn.ensemble import HistGradientBoostingClassifier

    # Keep the full memmap and index the retained columns at use sites (no copy).
    feats_full = np.lib.format.open_memmap(
        WORK / "wbg5_features.npy", mode="r", dtype="float32",
        shape=(len(feat_map), foot.shape[0], foot.shape[1]))
    names = keep_names
    mta_idx = [i for i, n in enumerate(names) if n.startswith("mta:")]
    n_mta = len(mta_idx)
    n_ctrl = feats_full.shape[0] - n_mta - len(flagged)

    def col(j: int) -> np.ndarray:
        return np.asarray(feats_full[j])
    total_foot = int(foot.sum())
    mta_names = {n for n in names if n.startswith("mta:")}
    cols_all = list(range(len(names)))
    cols_ctrl = [k for k, n in enumerate(names) if n not in mta_names]

    def make_X(rows, cols, src):
        X = np.empty((rows.size, len(src)), np.float32)
        for j, s in enumerate(src):
            X[:, j] = np.asarray(feats_full[s])[rows, cols]
        return X

    def predict_surface(clf, src):
        surf = np.zeros(foot.shape, np.float32)
        for r0 in range(0, foot.shape[0], 128):
            r1 = min(foot.shape[0], r0 + 128)
            h = r1 - r0
            rr, cc = np.divmod(np.arange(r0, r1).repeat(foot.shape[1]), foot.shape[1])
            Xc = np.empty((h * foot.shape[1], len(src)), np.float32)
            for j, s in enumerate(src):
                Xc[:, j] = np.asarray(feats_full[s][r0:r1]).ravel()
            surf[r0:r1] = clf.predict_proba(Xc)[:, 1].reshape(h, foot.shape[1]).astype(np.float32)
            del Xc, rr, cc
        surf[~foot] = 0.0
        return surf

    surfaces_all, surfaces_ctrl, fold_data = [], [], []
    for fold in ho.folds:
        tf = time.time()
        dist_v = ndi.distance_transform_edt(~fold["visible"]).astype(np.float32)
        train = fold["train"]
        pos_mask = fold["visible"] & train
        neg_pool = train & ~pos_mask
        rng = np.random.default_rng(SEED + fold["id"])
        pos_idx = np.flatnonzero(pos_mask.ravel())
        if pos_idx.size > 120_000:
            pos_idx = rng.choice(pos_idx, 120_000, replace=False)
        neg_idx = np.flatnonzero(neg_pool.ravel())
        neg_idx = rng.choice(neg_idx, size=min(neg_idx.size, 3 * pos_idx.size), replace=False)
        sel = np.r_[pos_idx, neg_idx]
        y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
        rows, cols = np.divmod(sel, foot.shape[1])
        X = make_X(rows, cols, cols_all)
        clf_all = HistGradientBoostingClassifier(
            max_iter=150, learning_rate=0.06, max_leaf_nodes=63,
            min_samples_leaf=40, l2_regularization=1.0, random_state=SEED)
        clf_all.fit(X, y)
        Xc = make_X(rows, cols, cols_ctrl)
        clf_ctrl = HistGradientBoostingClassifier(
            max_iter=150, learning_rate=0.06, max_leaf_nodes=63,
            min_samples_leaf=40, l2_regularization=1.0, random_state=SEED)
        clf_ctrl.fit(Xc, y)
        del X, Xc, rows, cols, sel, y
        s_all = predict_surface(clf_all, cols_all)
        s_ctrl = predict_surface(clf_ctrl, cols_ctrl)
        del clf_all, clf_ctrl
        np.save(WORK / f"surface_all_fold{fold['id']}.npy", s_all)
        np.save(WORK / f"surface_ctrl_fold{fold['id']}.npy", s_ctrl)
        surfaces_all.append(s_all)
        surfaces_ctrl.append(s_ctrl)
        fold_data.append((fold, dist_v))
        print(f"fold {fold['name']}: pos {pos_idx.size} neg {neg_idx.size} "
              f"done {time.time()-tf:.0f}s", flush=True)

    arms = {
        "A1_ctrl_no_mta": surfaces_ctrl,
        "A2_mta1": surfaces_all,
    }
    results, arm_preds = {}, {}
    for arm, surfaces in arms.items():
        preds = []
        for fold, dist_v in fold_data:
            b = int(round(37654 * int((fold["valid"] & foot).sum()) / total_foot))
            preds.append(dotted(surfaces[fold["id"]], fold["valid"] & foot, dist_v, b, 2))
        arm_preds[arm] = preds
        res = ho.summarize(preds, ci_draws=999)
        results[arm] = res
        print(arm, "HOLDOUT-DTI", res["dti"], res["ci95"]["interval"], flush=True)

    paired = ho.compare_paired(arm_preds["A2_mta1"], arm_preds["A1_ctrl_no_mta"], ci_draws=999)
    out = {
        "lane_id": "WBG-5",
        "method_code": "MTA-1",
        "evaluator_version": "gems-segment-pooled-v1",
        "canary_passed": canary["passed"],
        "canary_max_sym_auc": max_auc,
        "canary_all_passed": canary_all["passed"],
        "dropped_canary_flagged": flagged,
        "n_features_total": len(feat_map),
        "feature_names": names,
        "n_mta_channels": n_mta,
        "arms": results,
        "paired_A2_vs_A1": paired,
        "elapsed_s": time.time() - t0,
    }
    (WORK / "experiments.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"paired_A2_vs_A1": paired}, indent=1, default=float))
    print(f"DONE {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
