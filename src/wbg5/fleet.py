"""Fleet-wide score model: predict a live DTI from measurable raster geometry.

Every quantity here is computed from a submission raster plus the public catalogue.
Nothing looks at a peer repository's source, method name, or claimed score, so the
model is a *geometry → score* estimator that can be applied to a raster nobody has
ever submitted.

Calibration set: 121 (raster, live score) pairs recovered from the nine-site score
ledgers in the sibling repositories (``docs/score-ledger.csv``), spanning
0.0286–0.2778.  The targets are owner-reported DrivenData evaluations, not
organizer receipts; :func:`fit` reports leave-one-out error so the size of that
caveat is visible in the residuals.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label, uniform_filter

RING_EDGES = (3, 5, 8, 15, 30, 60)
FEATURES = (
    "log_dots",
    "frac_le3", "frac_le5", "frac_le8", "frac_le15", "frac_le30", "frac_le60",
    "cov3", "cov8", "cov15",
    "clump_frac", "nn_mean", "nn_p90",
    "line_coherence", "annulus_occupancy", "mass_frac",
)


def _nn_stats(mask: np.ndarray) -> tuple[float, float, float]:
    """Nearest-neighbour distance statistics and bearing coherence of the dots."""
    ys, xs = np.nonzero(mask)
    if len(ys) < 10:
        return 0.0, 0.0, 0.0
    from scipy.spatial import cKDTree
    pts = np.column_stack([ys, xs]).astype(np.float32)
    tree = cKDTree(pts)
    d, idx = tree.query(pts, k=2)
    nn = d[:, 1]
    # bearing coherence: are the dots organised into lines rather than a blob?
    vec = pts[idx[:, 1]] - pts
    ang = np.arctan2(vec[:, 0], vec[:, 1]) % np.pi
    c = np.cos(2 * ang).mean()
    s = np.sin(2 * ang).mean()
    return float(nn.mean()), float(np.percentile(nn, 90)), float(np.hypot(c, s))


def geometry(mask: np.ndarray, d_cat: np.ndarray, cat: np.ndarray, n_cat: int) -> dict:
    """All 16 features for one binary emission."""
    n = int(mask.sum())
    if n == 0:
        return {k: 0.0 for k in FEATURES}
    d = d_cat[mask]
    out = {"log_dots": float(np.log10(n))}
    for e in RING_EDGES:
        out[f"frac_le{e}"] = float((d <= e).mean())
    dt = distance_transform_edt(~mask)
    for e in (3, 8, 15):
        out[f"cov{e}"] = float(((dt <= e) & (cat > 0)).sum() / max(1, n_cat))
    dens = uniform_filter(mask.astype(np.float32), size=7) * 49.0
    out["clump_frac"] = float((dens[mask] > 1.5).mean())
    nn_mean, nn_p90, coh = _nn_stats(mask)
    out["nn_mean"], out["nn_p90"], out["line_coherence"] = nn_mean, nn_p90, coh
    ann = (d_cat >= 4) & (d_cat <= 40)
    out["annulus_occupancy"] = float(n / max(1, ann.sum()))
    out["mass_frac"] = float(n / mask.size)
    return out


def to_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[r[f] for f in FEATURES] for r in rows], dtype=np.float64)


def fit(X: np.ndarray, y: np.ndarray, seed: int = 0) -> dict:
    """Leave-one-out comparison of three estimators; the best one is returned."""
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import RidgeCV
    from sklearn.model_selection import LeaveOneOut, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    models = {
        "ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 12))),
        "rf": RandomForestRegressor(n_estimators=600, min_samples_leaf=3, random_state=seed,
                                    n_jobs=-1),
        "hgb": HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                             max_leaf_nodes=15, min_samples_leaf=8,
                                             l2_regularization=1.0, random_state=seed),
    }
    loo = LeaveOneOut()
    table, best = {}, None
    for name, m in models.items():
        pred = cross_val_predict(m, X, y, cv=loo)
        rmse = float(np.sqrt(((pred - y) ** 2).mean()))
        ss = float(1 - ((pred - y) ** 2).sum() / ((y - y.mean()) ** 2).sum())
        rho = float(np.corrcoef(pred, y)[0, 1])
        table[name] = {"loo_rmse": round(rmse, 4), "loo_r2": round(ss, 4),
                       "loo_pearson": round(rho, 4)}
        if best is None or rmse < best[1]:
            best = (name, rmse, m)
    name, rmse, m = best
    m.fit(X, y)
    return {"model": m, "name": name, "loo_rmse": rmse, "table": table,
            "residual_sd": rmse, "n": int(len(y))}


def predict(model_pack: dict, feats: dict, z: float = 1.96) -> dict:
    x = np.array([[feats[f] for f in FEATURES]])
    mu = float(model_pack["model"].predict(x)[0])
    sd = model_pack["residual_sd"]
    return {"estimate": round(mu, 4),
            "interval_95": [round(max(0.0, mu - z * sd), 4), round(mu + z * sd, 4)],
            "loo_rmse": round(sd, 4), "model": model_pack["name"],
            "label": "FLEET-GEOMETRY-ESTIMATE on owner-reported scores"}
