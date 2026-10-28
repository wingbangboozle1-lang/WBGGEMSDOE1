"""FSM-1: fleet score model — a calibrated estimator of a public DTI from emission geometry.

The model is fitted to every raster in this sandbox for which a public score is
recorded *and* whose pixels are obtainable (60 unique rasters, scores 0.0009 to
0.2778, all OWNER-REPORTED — no organizer receipt binds a score to bytes).
Its inputs are seven numbers that can be measured from any submission raster:
number of emitted pixels, the fraction within 3 px / 15 px of the mapped
catalogue, the fraction of the catalogue covered within 3 px, the 50th and 90th
percentile catalogue distance, and the number of connected components.

Honest limits
-------------
* The training scores are owner-reported, not organizer-confirmed.
* Exact-duplicate rasters inside the training set always carry the same score,
  so the labels are internally consistent, but 100 % of them come from a single
  family of dense-dot submissions.
* Leave-one-out RMSE is reported next to every prediction.  A prediction
  interval of roughly +/- 2 x LOO-RMSE is the only defensible reading.
* The model is *correlational*: it says "submissions that look like this scored
  like that", never "this submission will score this".
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

FEATURES = ("n_dots", "frac_le3", "frac_le15", "cat_cov3", "dist_p50", "dist_p90", "n_comp")


def training_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    p = root / "docs" / "data" / "fsm1-training.json"
    if not p.exists():
        raise FileNotFoundError("missing docs/data/fsm1-training.json")
    return p


def load_training() -> tuple[np.ndarray, np.ndarray, list[dict]]:
    blob = json.loads(training_path().read_text())
    rows = blob["rows"]
    X = np.array([[r[f] for f in FEATURES] for r in rows], float)
    y = np.array([r["score"] for r in rows], float)
    return X, y, rows


def _design(X: np.ndarray) -> np.ndarray:
    """Log-transform the two strongly skewed count features."""
    X = np.asarray(X, float)
    return np.column_stack([np.log10(X[:, 0]), X[:, 1], X[:, 2], X[:, 3], X[:, 4], X[:, 5],
                            np.log10(X[:, 6])])


def fit_and_validate(n_estimators: int = 400, seed: int = 0) -> dict:
    """Fit the model and report leave-one-out performance (the honesty check)."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import LeaveOneOut, cross_val_predict

    X, y, rows = load_training()
    Z = _design(X)
    est = RandomForestRegressor(n_estimators=n_estimators, min_samples_leaf=3,
                                random_state=seed, n_jobs=1)
    loo = cross_val_predict(est, Z, y, cv=LeaveOneOut())
    rmse = float(np.sqrt(np.mean((loo - y) ** 2)))
    q2 = float(1 - np.sum((loo - y) ** 2) / np.sum((y - y.mean()) ** 2))
    from scipy.stats import spearmanr
    rho = float(spearmanr(loo, y)[0])
    est.fit(Z, y)
    return dict(model=est, n=int(len(y)), loo=loo, y=y, rows=rows,
                loo_rmse=rmse, loo_q2=q2, loo_rho=rho,
                y_min=float(y.min()), y_max=float(y.max()))


def predict(feats: dict, fit: dict) -> dict:
    """Point estimate plus the LOO-derived prediction interval."""
    Z = _design(np.array([[feats[f] for f in FEATURES]], float))
    point = float(fit["model"].predict(Z)[0])
    point = float(np.clip(point, 0.0, max(fit["y_max"], 0.3)))
    half = 1.96 * fit["loo_rmse"]
    return {
        "estimate": round(point, 4),
        "interval_95": [round(max(0.0, point - half), 4), round(point + half, 4)],
        "loo_rmse": round(fit["loo_rmse"], 4),
        "loo_q2": round(fit["loo_q2"], 4),
        "loo_rho": round(fit["loo_rho"], 4),
        "n_training": fit["n"],
        "training_score_range": [fit["y_min"], fit["y_max"]],
        "label": "MODEL-ESTIMATE (owner-reported training labels; not organizer-confirmed)",
        "features": {k: (round(float(feats[k]), 4) if not isinstance(feats[k], int) else feats[k])
                     for k in FEATURES},
    }


def family_reference(fit: dict, k: int = 5) -> dict:
    """Mean score of the k highest-scoring training rasters: the incumbent band."""
    order = np.argsort(-fit["y"])[:k]
    return {"k": k, "mean_score": float(fit["y"][order].mean()),
            "members": [fit["rows"][i]["stem"] for i in order]}
