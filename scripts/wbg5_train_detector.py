#!/usr/bin/env python3
"""EXP-A: can the official 19-band stack find faults the training fold never saw?

Runs a 4-fold geographically-blocked cross-validation over the catalogue, writes
out-of-fold probabilities, and evaluates emissions on each held-out strip with the
official metric.  Nothing about catalogue geometry reaches the model: no
coordinates, no distance-to-fault feature, no neighbour labels.

    python scripts/wbg5_train_detector.py --folds 4
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
import numpy as np
from wbg5 import detect, features, grid

TMP = Path("/tmp/lab")
CHAMP = ROOT / "docs" / "audit" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=4)
    ap.add_argument("--neg", type=int, default=260_000)
    ap.add_argument("--out", default="docs/data/detector_cv.json")
    ap.add_argument("--sweep", default="2000,4000,6000,8000,12000,16000,24000,36000")
    ap.add_argument("--only-fold", type=int, default=-1)
    args = ap.parse_args()
    TMP.mkdir(exist_ok=True)
    features.set_root(ROOT)

    cat = grid.load_catalogue()
    fp = grid.load_footprint()
    H = grid.HEIGHT
    strip = [(i * H // args.folds, (i + 1) * H // args.folds) for i in range(args.folds)]
    rho = [float(v) for v in args.sweep.split(",")]
    rng = np.random.default_rng(0)
    ns = features.names()

    prob = np.full((H, grid.WIDTH), np.nan, np.float32)
    report = {"schema": "wbg5-detector-cv-v1", "folds": [], "n_features": len(ns), "features": ns,
              "protocol": ("contiguous N-S strips; the evaluated strip is never seen in "
                           "training; inputs are 19 official bands + 4 derivative channels "
                           "on 14 of them; no coordinates, no catalogue distance, no "
                           "neighbour labels")}
    t0 = time.time()
    for f, (r0, r1) in enumerate(strip):
        if args.only_fold >= 0 and f != args.only_fold:
            continue
        train_px = sum((b1 - b0) * grid.WIDTH for b0, b1 in strip if b0 != r0)
        keep = min(1.0, args.neg / max(1.0, train_px * 0.4))
        Xs, ys = [], []
        for (b0, b1) in strip:
            if b0 == r0:
                continue
            for X, valid, rr in features.iter_blocks(b0, b1):
                lab = cat[rr:rr + X.shape[1]]
                m = valid > 0
                pos = np.flatnonzero((lab & m).ravel())
                neg = np.flatnonzero((~lab & m).ravel())
                if pos.size == 0:
                    continue
                neg = neg[rng.random(neg.size) < keep]
                idx = np.concatenate([pos, neg])
                Xs.append(X.reshape(X.shape[0], -1)[:, idx].T.astype(np.float32))
                ys.append(lab.ravel()[idx].astype(np.int8))
        X = np.concatenate(Xs)
        y = np.concatenate(ys)
        del Xs, ys
        clf = detect.fit_fold(X, y)
        print(f"fold {f} rows {r0}-{r1}: train {X.shape[0]:,} px, pos {int(y.sum()):,}"
              f"  ({time.time()-t0:.0f}s)", flush=True)
        del X, y

        ys_all, ps_all, fcols, flabs = [], [], [], []
        for X, valid, rr in features.iter_blocks(r0, r1):
            F = X.reshape(X.shape[0], -1).T
            p = clf.predict_proba(F)[:, 1].astype(np.float32).reshape(X.shape[1], X.shape[2])
            n = p.shape[0]
            prob[rr:rr + n] = np.where(valid > 0, p, np.nan)
            m = (valid > 0) & fp[rr:rr + n]
            ys_all.append(cat[rr:rr + n][m].astype(np.int8))
            ps_all.append(p[m])
            flat = np.flatnonzero(m.ravel())
            if flat.size > 3000:
                flat = rng.choice(flat, 3000, replace=False)
            fcols.append(F[flat])
            flabs.append(cat[rr:rr + n].ravel()[flat].astype(np.int8))
        yh, ph = np.concatenate(ys_all), np.concatenate(ps_all)
        Fc, yc = np.concatenate(fcols), np.concatenate(flabs)
        del ys_all, ps_all, fcols, flabs

        canary = {nm: round(detect.auc(yc, Fc[:, i]), 4) for i, nm in enumerate(ns)}
        canary = dict(sorted(canary.items(), key=lambda kv: -(kv[1] if kv[1] == kv[1] else 0))[:6])

        strip_valid = fp[r0:r1]
        n_valid = int(strip_valid.sum())
        truth = cat[r0:r1]
        sweep = {}
        for density in rho:
            n = int(density * n_valid / 1e6)
            mask = detect.emit_from_prob(prob[r0:r1], strip_valid,
                                         np.ones(truth.shape, bool), n)
            sweep[f"dots_{density:.0f}"] = {"n_dots": int(mask.sum()),
                                            **detect.score_emission(mask.astype(np.float32),
                                                                    truth, strip_valid, None, False)}
        sweep["prob_continuous"] = detect.score_emission(
            np.where(np.isfinite(prob[r0:r1]), prob[r0:r1], 0.0), truth, strip_valid, None, False)
        if CHAMP.exists():
            import rasterio
            with rasterio.open(CHAMP) as ds:
                c = ds.read(1)[r0:r1]
            sweep["champion_control"] = detect.score_emission(
                np.where(np.isfinite(c), c, 0.0), truth, strip_valid, None, False)

        rec = {"fold": f, "rows": [r0, r1],
               "auc": round(detect.auc(yh, ph), 4),
               "average_precision": round(detect.average_precision(yh, ph), 4),
               "pos_rate": round(float(yh.mean()), 5),
               "leakage_canary_top_single_features": canary,
               "canary_max": max(v for v in canary.values() if v == v),
               "sweep": sweep}
        report["folds"].append(rec)
        print(f"   AUC {rec['auc']:.4f}  AP {rec['average_precision']:.4f}"
              f"  canary max {rec['canary_max']:.3f}", flush=True)
        for k, v in sweep.items():
            print(f"   {k:>17s} dti={v['dti']:.4f} cov={v['coverage']:.4f}"
                  f" nodots={int(v.get('n_dots', 0))}", flush=True)
        del yh, ph, Fc, yc

    np.save(TMP / "prob_oof.npy", prob)
    agg: dict[str, list] = {}
    for fr in report["folds"]:
        for k, v in fr["sweep"].items():
            agg.setdefault(k, []).append(v["dti"])
    report["mean_dti_by_emission"] = {k: round(float(np.mean(v)), 5) for k, v in agg.items()}
    out = ROOT / args.out
    if args.only_fold < 0:
        out.write_text(json.dumps(report, indent=1) + "\n")
    print("\nmean DTI by emission:")
    for k, v in sorted(report["mean_dti_by_emission"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:>17s} {v:.5f}")
    print(f"\n{time.time()-t0:.0f}s; prob_oof -> {TMP/'prob_oof.npy'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
