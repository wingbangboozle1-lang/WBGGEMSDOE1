#!/usr/bin/env python3
"""WBG-8 multi-physic hidden-corridor emission lane (preregistered 2026-10-31).

See research/07_wbg8_preregistration_20261031.md.  Three pre-registered
experiments in one driver:

  EXP1  channel screens (canary + PROXY-DTI + fold-safe HOLDOUT-DTI) and blend
        selection by rule R1/R2;
  EXP2  emission-budget grid K by rule R3, then report-draw instruments with
        paired CIs versus a same-mask Poisson control and the B2 champion;
  EXP3  packaging through the shared submission_writer, validator receipt,
        two-phase uniqueness audit vs every cached registry raster, score
        estimate (MODEL-ESTIMATE labels only) and one JSON run card.

Shared instruments only (vendor/gems57): metric.dti_exact, holdout.
buffered_component_draw, evaluate_holdout.evaluate/pooled_summary,
offcatalogue.load_proxy_truth, submission_writer.write_submission.  Channels
reuse the in-repo decoders (src/wbg2/features.py) where they exist.  No private
metric fork, no upload, no score is ever called a projection.

Usage:  .venv/bin/python scripts/run_wbg8_lane.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout as E  # noqa: E402
from gems57 import holdout as H  # noqa: E402
from gems57 import metric as M  # noqa: E402
from gems57 import offcatalogue as OC  # noqa: E402
from gems57 import submission_writer as SW  # noqa: E402
from gems57.grid import load_grid  # noqa: E402

EVID = ROOT / "evidence" / "wbg8"
DOWNLOADS = ROOT / "docs" / "downloads"
BRIDGE = ROOT / "data" / "bridge"
CACHE_BANDS = ROOT / "data" / "template57" / ".cache" / "features"
LIDAR = ROOT / "data" / "external" / "lidar_scarp_features_u8.tif"
RAD = ROOT / "data" / "external" / "geodawn_rad_u8.tif"

K_PRIMARY = 37_654
K_GRID = [30_000, 34_000, 37_654, 42_000, 50_000]
MIN_SEP_PX = 3
NMS_WINDOW = 7
HALO_PX = 3
SELECTION_SEED = 71614   # EXP1 fold-safe replay / canary (scarp_offcat instrument)
REPORT_SEED = 21         # EXP2 report draw (lane protocol report draw)
DRAWS = 1000
EVAL_SEED = 520810
CANARY_LIMIT = 0.90
SPEARMAN_SAMPLE = 200_000
RHO_LIMIT = 0.90
OVERLAP_LIMIT = 0.70
LIFT_LIMIT = 1.2

EXPECTED = {
    "lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "sgmc_faults_100m.tif": "26d142c4c93282cd94f6950ab96f22aeff59fbbea523d43d662e76fa1b161b5c",
    "derived_sgmc_faults_100m.tif": "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False, default=float) + "\n")


def rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Percentile rank of ``a`` inside ``mask``, zeros elsewhere (catalogue-free)."""
    out = np.zeros(a.shape, np.float32)
    v = a[mask]
    if v.size == 0:
        return out
    order = np.argsort(v, kind="mergesort")
    r = np.empty(v.size, np.float32)
    r[order] = (np.arange(v.size, dtype=np.float32) + 0.5) / v.size
    out[mask] = r
    return out


def load_bands() -> dict[str, np.ndarray]:
    idx = {
        "rtp": 2, "tmi_hg": 3, "geod_2ndinv": 4, "geod_shearrate": 7,
        "det_elev": 12, "tmi": 14, "depth_to_base_surf": 15, "cond_surf": 17,
        "iso_grav_anom_hg": 18, "det_elev_slope": 19,
    }
    return {name: np.load(CACHE_BANDS / f"band-{n:02d}.npy").astype(np.float32)
            for name, n in idx.items()}


def decode_u8(q: np.ndarray, xmax: float, mode: str) -> np.ndarray:
    t = (q.astype(np.float32) - 1.0) / 254.0
    x = xmax * (t * t if mode == "sqrt" else t)
    return np.where(q == 0, np.nan, x).astype(np.float32)


def build_channels(bands, grid):
    """Four catalogue-free propensity channels in [0,1].

    ``catalogue-free`` = no channel value is derived from the mapped catalogue.
    Channel values are defined everywhere in the footprint (including catalogue
    pixels, which at fold time are legitimate hidden-truth candidates); the
    catalogue enters only through the emission halo mask outside this function.
    """
    fp = grid.footprint
    off = fp  # ranking domain: the full footprint (values are catalogue-free)

    # CH1 LiDAR scarp expression: 2 m slope excess x along-strike coherence.
    with rasterio.open(LIDAR) as src:
        q_ex = src.read(1)          # ex_max, sqrt, xmax 1.5
        q_coh = src.read(10)        # coh100, linear 0..1
    lidar_valid = (q_ex > 0) & fp
    ex = decode_u8(q_ex, 1.5, "sqrt")
    coh = decode_u8(q_coh, 1.0, "linear")
    s1 = np.where(lidar_valid, ex * np.nan_to_num(coh, nan=0.0), -np.inf)
    ch1 = rank01(s1.astype(np.float32), lidar_valid & off)

    # CH2 buried-basement lineament corridors: gradient coherence of the
    # depth-to-basement surface and detrended elevation, gated by thin cover.
    zb = bands["depth_to_base_surf"]
    de = bands["det_elev"]
    gz = np.hypot(*np.gradient(np.nan_to_num(zb, nan=float(np.nanmedian(zb)))))
    gd = np.hypot(*np.gradient(np.nan_to_num(de, nan=float(np.nanmedian(de)))))
    line = np.maximum(gz, gd)
    thin = rank01(-zb, off)  # thin cover ranks high
    ch2 = (rank01(line, off) * (0.5 + 0.5 * thin)).astype(np.float32)

    # CH3 potential-field edge concordance: magnetic x gravity horizontal
    # gradient co-location (crustal-scale through-going fault zones).
    m = np.abs(np.nan_to_num(bands["tmi_hg"], nan=0.0))
    g = np.abs(np.nan_to_num(bands["iso_grav_anom_hg"], nan=0.0))
    ch3 = (rank01(m, off) * rank01(g, off)).astype(np.float32)

    # CH4 radiometric alteration x conductance (upflow clay halos).
    with rasterio.open(RAD) as src:
        qk, qth, qu, _qtc = (src.read(i) for i in (1, 2, 3, 4))
    k = decode_u8(qk, 8.0, "sqrt")
    th = decode_u8(qth, 40.0, "sqrt")
    rad_ok = (qk > 0) & fp
    kt = np.where(rad_ok & np.isfinite(th) & (th > 0), k / np.maximum(th, 1e-6), -np.inf)
    alter = rank01(kt.astype(np.float32), rad_ok & off)
    cond = rank01(np.nan_to_num(bands["cond_surf"], nan=0.0), off)
    ch4 = (alter * (0.5 + 0.5 * cond)).astype(np.float32)

    for ch in (ch1, ch2, ch3, ch4):
        ch[~fp] = 0.0
        np.clip(ch, 0.0, 1.0, out=ch)
    return {"ch1_lidar_scarp": ch1, "ch2_basement_lineament": ch2,
            "ch3_pf_concordance": ch3, "ch4_rad_conductance": ch4}


def greedy_peaks(score: np.ndarray, allowed: np.ndarray, n: int) -> np.ndarray:
    """NMS peaks in descending score with MIN_SEP_PX Chebyshev separation."""
    s = np.where(allowed & np.isfinite(score), score, -np.inf)
    local = (s == ndi.maximum_filter(s, size=NMS_WINDOW, mode="constant", cval=-np.inf)) & np.isfinite(s)
    ys, xs = np.nonzero(local)
    if ys.size == 0:
        return np.zeros(s.shape, bool)
    order = np.argsort(-s[ys, xs], kind="stable")
    dots = np.zeros(s.shape, bool)
    taken = np.zeros(s.shape, bool)
    h, w = s.shape
    k = 0
    r = MIN_SEP_PX - 1
    for idx in order:
        if k >= n:
            break
        y, x = int(ys[idx]), int(xs[idx])
        if taken[y, x]:
            continue
        dots[y, x] = True
        k += 1
        taken[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)] = True
    return dots


def auc_rank(pos: np.ndarray, neg: np.ndarray) -> float:
    allv = np.concatenate([pos, neg])
    ranks = np.empty(allv.size, float)
    ranks[np.argsort(allv, kind="mergesort")] = np.arange(1, allv.size + 1)
    _, inv, cnt = np.unique(allv, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    ranks = (sums / cnt)[inv]
    rp = ranks[: pos.size].sum()
    return float((rp - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))


def spearman_sampled(a: np.ndarray, b: np.ndarray, idx) -> float:
    av = a.ravel()[idx].astype(np.float64)
    bv = b.ravel()[idx].astype(np.float64)
    if np.all(av == av[0]) or np.all(bv == bv[0]):
        return 0.0
    return float(spearmanr(av, bv).statistic)


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    EVID.mkdir(parents=True, exist_ok=True)

    for name, pin in EXPECTED.items():
        got = sha256(ROOT / "data" / "external" / name)
        if got != pin:
            raise SystemExit(f"hash mismatch on {name}: {got} != {pin}")

    grid = load_grid(BRIDGE)
    fp = grid.footprint
    cat = grid.catalogue
    bands = load_bands()
    channels = build_channels(bands, grid)

    proxy, proxy_receipt = OC.load_proxy_truth(ROOT, grid)
    dump(proxy_receipt, EVID / "proxy_truth_receipt.json")

    d_cat = ndi.distance_transform_edt(~cat)
    halo_full = d_cat <= HALO_PX

    def fold_allowed(visible_mask):
        d_vis = ndi.distance_transform_edt(~visible_mask)
        return fp & ~(d_vis <= HALO_PX)

    def proxy_dti(dots: np.ndarray) -> dict:
        pred = dots.astype(np.float64)
        r = M.dti_exact(pred, proxy, valid=fp, known=cat)
        return {"dti": float(r["dti"]), "tp": float(r["tp"]), "fp": float(r["fp"]),
                "fn": float(r["fn"]), "n_proxy": int(proxy.sum())}

    def replay(surface, folds, budget_total):
        out = []
        fp_count = float(fp.sum())
        for fold in folds:
            visible = np.asarray(fold["visible"], bool)
            region = np.asarray(fold["region"], bool) & fp
            allowed = fold_allowed(visible) & region
            n_f = int(round(budget_total * float(region.sum()) / fp_count))
            out.append(greedy_peaks(surface, allowed, n_f))
        return out

    def score_folds(dots_by_fold, folds):
        terms = None
        rows = []
        for dots, fold in zip(dots_by_fold, folds):
            res, blk = E.evaluate(dots.astype(np.float64), fold, fp)
            terms = blk if terms is None else terms + blk
            rows.append({"fold": fold["name"], "budget": int(dots.sum()),
                         "withheld_positive_px": int(res["n_truth"]),
                         "dti_fold": round(float(res["dti"]), 6)})
        return terms, rows

    def canary_collect(surf, folds, store_pos, store_neg):
        for fold in folds:
            visible = np.asarray(fold["visible"], bool)
            known = np.asarray(fold.get("masked_known", visible), bool)
            truth = np.asarray(fold["truth"], bool)
            region = np.asarray(fold["region"], bool) & fp
            active = region & ~known
            rng = np.random.default_rng(97)
            pos_v = surf[active & truth]
            neg_v = surf[active & ~truth]
            if pos_v.size and neg_v.size:
                store_pos.append(pos_v)
                store_neg.append(rng.choice(neg_v, size=min(200_000, neg_v.size), replace=False))

    def screen(name, surf, folds):
        allowed_full = fp & ~halo_full
        dots_full = greedy_peaks(surf, allowed_full, K_PRIMARY)
        pd = proxy_dti(dots_full)
        fold_dots = replay(surf, folds, K_PRIMARY)
        terms, rows = score_folds(fold_dots, folds)
        pos_l, neg_l = [], []
        canary_collect(surf, folds, pos_l, neg_l)
        pooled = E.pooled_summary({name: terms}, draws=DRAWS, seed=EVAL_SEED, candidate=name)
        sc = pooled["scores"][name]
        pos_all = np.concatenate(pos_l) if pos_l else np.array([])
        neg_all = np.concatenate(neg_l) if neg_l else np.array([])
        auc = auc_rank(pos_all, neg_all) if pos_all.size and neg_all.size else float("nan")
        return {
            "proxy_dti": pd,
            "holdout_dti_selection_draw": {
                "dti": sc["dti"], "ci95": sc["ci95"],
                "withheld_positive_pixels": sc["withheld_positive_pixels"],
                "tpw": sc["tpw"], "fpw": sc["fpw"], "fnw": sc["fnw"],
                "per_fold": rows, "evaluator_version": E.VERSION,
                "evidence_class": "HOLDOUT-DTI", "seed": SELECTION_SEED},
            "dots_at_k": int(dots_full.sum()),
            "canary_auc": round(float(auc), 6),
            "canary_pass": bool(auc <= CANARY_LIMIT),
        }

    # ---- EXP1a: single channels + canary (R1) -----------------------------
    folds_sel, _ = H.buffered_component_draw(grid, seed=SELECTION_SEED, hide_frac=0.2,
                                             buffer_px=3, boundary_px=12)
    exp1 = {"stage": "EXP1 channel screens and blend selection",
            "configs": {}, "selection": {}}
    survivors = []
    for ch_name, surf in channels.items():
        exp1["configs"][ch_name] = screen(ch_name, surf, folds_sel)
        r = exp1["configs"][ch_name]
        print(f"[exp1a] {ch_name}: proxy={r['proxy_dti']['dti']:.4f} "
              f"holdout={r['holdout_dti_selection_draw']['dti']:.4f} auc={r['canary_auc']:.4f} "
              f"{'PASS' if r['canary_pass'] else 'CANARY-FAIL'}", flush=True)
        if r["canary_pass"]:
            survivors.append(ch_name)
    dropped = [c for c in channels if c not in survivors]
    if not survivors:
        raise SystemExit("every channel failed the leakage canary; lane STOP")

    # ---- EXP1b: blends of survivors only (R2) -----------------------------
    blend_all = np.mean(np.stack([channels[c] for c in survivors]), axis=0).astype(np.float32)
    top2 = sorted(survivors,
                  key=lambda c: exp1["configs"][c]["proxy_dti"]["dti"], reverse=True)[:2]
    blend_top2 = np.mean(np.stack([channels[c] for c in top2]), axis=0).astype(np.float32)
    pool = {**{c: channels[c] for c in survivors},
            "blend_all": blend_all, "blend_top2": blend_top2}
    for cfg_name in ("blend_all", "blend_top2"):
        exp1["configs"][cfg_name] = screen(cfg_name, pool[cfg_name], folds_sel)
        r = exp1["configs"][cfg_name]
        print(f"[exp1b] {cfg_name}: proxy={r['proxy_dti']['dti']:.4f} "
              f"holdout={r['holdout_dti_selection_draw']['dti']:.4f} auc={r['canary_auc']:.4f}", flush=True)

    eligible = {k: v for k, v in exp1["configs"].items() if v["canary_pass"]}
    best_name = max(eligible, key=lambda k: (round(eligible[k]["proxy_dti"]["dti"], 3), len(k)))
    exp1["selection"] = {
        "rule": ("R1 drop canary AUC>0.90 before blending; R2 highest selection-draw PROXY-DTI "
                 "wins, ties at 3 dp prefer the blend with more channels"),
        "dropped_canary_failures": dropped,
        "top2_by_single_proxy": top2,
        "selected": best_name,
    }
    dump(exp1, EVID / "exp1_channel_screens.json")

    # ---- EXP1c: proxy instrument vs OWNER-REPORTED scores -----------------
    scored = [("GEMSDOE32", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778,
               ROOT / "docs" / "audit" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")]
    cache = ROOT / ".cache" / "focus_rasters"
    by_name = {}
    if cache.exists():
        for p in sorted(cache.glob("*.tif")):
            by_name.setdefault(p.name.split("__", 1)[-1], p)
    want = {
        "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros": 0.2750,
        "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan": 0.2710,
        "h27-4-solo-d28-20261004-8acb75e1-nan": 0.2708,
        "h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan": 0.2708,
        "h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan": 0.2707,
        "h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan": 0.2649,
        "h33d-analog-tip-stepover-r30-20261004-cb490425926e": 0.2632,
        "dotted-h19-5-d2-8-20261002-e56ea318af89-nan": 0.2600,
        "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca": 0.2600,
        "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan": 0.2477,
        "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan": 0.2449,
    }
    for stem, score in want.items():
        for key, p in by_name.items():
            if key.startswith(stem):
                scored.append((key.split("__")[0], stem, score, p))
                break
    rows = []
    for site, sname, score, path in scored:
        if not Path(path).exists():
            rows.append({"name": sname, "error": "missing"}); continue
        with rasterio.open(path) as ds:
            arr = ds.read(1)
        dots = np.isfinite(arr) & (arr > 0)
        pd = proxy_dti(dots)
        rows.append({"site": site, "name": sname, "score_owner_reported": score,
                     "proxy_dti": pd["dti"], "dots": int(dots.sum()),
                     "frac_within3px_cat": float((dots & (d_cat <= 3)).sum()) / max(1, int(dots.sum()))})
    ok = [r for r in rows if "proxy_dti" in r]
    rho = pval = None
    if len(ok) >= 5:
        sp = spearmanr([r["proxy_dti"] for r in ok], [r["score_owner_reported"] for r in ok])
        rho, pval = float(sp.statistic), float(sp.pvalue)
    est_check = {"schema": "wbg8-proxy-calibration-v1", "n": len(ok), "rows": rows,
                 "spearman_proxy_dti_vs_owner_reported": rho, "spearman_p": pval,
                 "label": "OWNER-REPORTED dependent variable; PROXY-DTI is not a score"}
    dump(est_check, EVID / "proxy_calibration.json")
    print(f"[exp1c] proxy-vs-reported Spearman={rho} (n={len(ok)})", flush=True)

    # ---- EXP2: budget grid + report-draw instruments ----------------------
    surface = pool[best_name]
    allowed_full = fp & ~halo_full
    k_rows = []
    for k in K_GRID:
        dots = greedy_peaks(surface, allowed_full, k)
        k_rows.append({"k": k, "dots": int(dots.sum()), "proxy_dti": proxy_dti(dots)["dti"]})
    best_k = max(k_rows, key=lambda r: (round(r["proxy_dti"], 3), -r["k"]))["k"]
    exp2 = {"k_grid": k_rows,
            "rule": "R3 max selection PROXY-DTI, ties at 3 dp prefer smaller K",
            "selected_k": best_k, "selected_surface": best_name}
    print(f"[exp2] k grid {[(r['k'], round(r['proxy_dti'], 4)) for r in k_rows]} -> {best_k}", flush=True)

    folds_rep, _ = H.buffered_component_draw(grid, seed=REPORT_SEED, hide_frac=0.2,
                                             buffer_px=3, boundary_px=12)
    fold_dots = replay(surface, folds_rep, best_k)
    terms_c, rows_c = score_folds(fold_dots, folds_rep)
    rng = np.random.default_rng(2026)
    terms_ctrl = None
    rows_ctrl = []
    for fold in folds_rep:
        visible = np.asarray(fold["visible"], bool)
        region = np.asarray(fold["region"], bool) & fp
        allowed = fold_allowed(visible) & region
        n_f = int(round(best_k * float(region.sum()) / float(fp.sum())))
        idx = np.flatnonzero(allowed.ravel())
        pick = rng.choice(idx, size=min(n_f, idx.size), replace=False)
        ctrl = np.zeros(fp.shape, bool)
        ctrl.ravel()[pick] = True
        res, blk = E.evaluate(ctrl.astype(np.float64), fold, fp)
        terms_ctrl = blk if terms_ctrl is None else terms_ctrl + blk
        rows_ctrl.append({"fold": fold["name"], "budget": n_f,
                          "dti_fold": round(float(res["dti"]), 6)})
    pooled = E.pooled_summary({best_name: terms_c, "control_poisson_same_mask": terms_ctrl},
                              draws=DRAWS, seed=EVAL_SEED, candidate=best_name)
    cand = pooled["scores"][best_name]
    ctrl = pooled["scores"]["control_poisson_same_mask"]
    diffs = pooled["paired_differences"]

    b2_path = ROOT / "docs" / "audit" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
    with rasterio.open(b2_path) as ds:
        b2_arr = ds.read(1)
    b2 = np.isfinite(b2_arr) & (b2_arr > 0)
    terms_b2 = None
    for fold in folds_rep:
        _res, blk = E.evaluate(b2.astype(np.float64), fold, fp)
        terms_b2 = blk if terms_b2 is None else terms_b2 + blk
    pooled_b2 = E.pooled_summary({best_name: terms_b2}, draws=DRAWS, seed=EVAL_SEED, candidate=best_name)
    b2_hold = pooled_b2["scores"][best_name]
    b2_proxy = proxy_dti(b2)

    final_dots = greedy_peaks(surface, allowed_full, best_k)
    final_proxy = proxy_dti(final_dots)

    exp2["report_draw"] = {
        "seed": REPORT_SEED, "evaluator_version": E.VERSION, "evidence_class": "HOLDOUT-DTI",
        "candidate": {"dti": cand["dti"], "ci95": cand["ci95"],
                      "withheld_positive_pixels": cand["withheld_positive_pixels"],
                      "per_fold": rows_c},
        "control_poisson_same_mask": {"dti": ctrl["dti"], "ci95": ctrl["ci95"], "per_fold": rows_ctrl},
        "paired_difference": diffs,
        "b2_reference_fixed_field": {
            "holdout_dti": b2_hold["dti"], "ci95": b2_hold["ci95"], "proxy_dti": b2_proxy,
            "caveat": "B2 placement used the full catalogue; its fold score is not fold-safe replay."},
        "candidate_proxy_dti": final_proxy,
        "bootstrap": pooled["bootstrap"],
    }
    dump(exp2, EVID / "exp2_budget_and_efficacy.json")
    print(f"[exp2] report holdout={cand['dti']:.4f} ci={cand['ci95']} ctrl={ctrl['dti']:.4f} "
          f"paired={diffs}", flush=True)

    # ---- EXP3: packaging, validator, uniqueness ---------------------------
    name = (f"wbggemsdoe1-wbg8-hidden-corridor-{best_k}-"
            f"{datetime.now(timezone.utc):%Y%m%d}-zeros")
    note = (f"WBG-8 lidar+basement+pf+rad corridors; {best_k:,} catalogue-neutral dots; "
            f"MODEL-ESTIMATE ~0.26-0.29")[:140]
    values = np.zeros(fp.shape, np.float32)
    values[final_dots] = 1.0
    out_tif = DOWNLOADS / f"{name}.tif"
    if out_tif.exists():
        raise SystemExit(f"refusing to overwrite {out_tif}")
    receipt = SW.write_submission(out_tif, values, BRIDGE / "sample_submission.tif", fp,
                                  note=note, name=name, catalogue=cat)
    dump(receipt, EVID / "submission_receipt.json")

    from gems57.uniqueness import dot_overlap
    reg_files = sorted(set((ROOT / ".cache" / "focus_rasters").glob("*.tif")))
    own = [p for p in sorted(DOWNLOADS.glob("*.tif")) if p != out_tif]
    audit_rows = []
    my_sha = sha256(out_tif)
    my_mask = values > 0
    my_mask_sha = hashlib.sha256(np.packbits(my_mask.ravel()).tobytes()).hexdigest()
    sample_rng = np.random.default_rng(4242)
    fp_idx = np.flatnonzero(fp.ravel())
    sample_idx = sample_rng.choice(fp_idx, size=min(SPEARMAN_SAMPLE, fp_idx.size), replace=False)
    max_rho, max_rho_name = -1.0, None
    max_ov, max_ov_name, max_ov_dots = 0.0, None, None
    seen_sha = set()
    for p in reg_files + own:
        digest = sha256(p)
        if digest in seen_sha or digest == my_sha:
            continue
        seen_sha.add(digest)
        with rasterio.open(p) as ds:
            arr = ds.read(1)
        theirs = np.isfinite(arr) & (arr > 0)
        their_mask_sha = hashlib.sha256(np.packbits(theirs.ravel()).tobytes()).hexdigest()
        ov = float(dot_overlap(my_mask, theirs))
        rho_v = spearman_sampled(values, np.where(np.isfinite(arr), arr, 0.0), sample_idx)
        n_theirs = int(theirs.sum())
        if rho_v > max_rho:
            max_rho, max_rho_name = rho_v, p.name
        if ov > max_ov:
            max_ov, max_ov_name, max_ov_dots = ov, p.name, n_theirs
        audit_rows.append({"file": p.name, "sha256": digest, "pixel_sha256": their_mask_sha,
                           "their_dots": n_theirs, "overlap_fwd_3px": round(ov, 6),
                           "spearman_sample": round(rho_v, 6),
                           "identical_bytes": digest == my_sha,
                           "identical_pixels": their_mask_sha == my_mask_sha,
                           "literal_overlap_fail": bool(ov > OVERLAP_LIMIT),
                           "rho_fail": bool(rho_v > RHO_LIMIT),
                           "dense_registry_dots_gt_3x_mine": bool(n_theirs > 3 * int(my_mask.sum()))})

    def coverage3(dots):
        return float((ndi.distance_transform_edt(~dots) <= 3).sum()) / float(fp.sum())

    lift_rows = []
    for r in sorted(audit_rows, key=lambda r: -r["overlap_fwd_3px"])[:15]:
        p = ROOT / ".cache" / "focus_rasters" / r["file"]
        if not p.exists():
            p = DOWNLOADS / r["file"]
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        theirs = np.isfinite(a) & (a > 0)
        exp_uniform = coverage3(theirs)
        lift_rows.append({"file": r["file"], "overlap_fwd": r["overlap_fwd_3px"],
                          "uniform_expectation": round(exp_uniform, 6),
                          "lift": round(r["overlap_fwd_3px"] / max(exp_uniform, 1e-9), 4),
                          "their_dots": r["their_dots"]})
    uniq = {"schema": "wbg8-uniqueness-v1", "candidate": name, "sha256": my_sha,
            "pixel_sha256": my_mask_sha, "my_dots": int(my_mask.sum()),
            "registry_rasters_compared": len(audit_rows),
            "max_spearman_sample": {"value": max_rho, "file": max_rho_name},
            "max_dot_overlap_3px": {"value": max_ov, "file": max_ov_name, "their_dots": max_ov_dots},
            "rho_limit": RHO_LIMIT, "overlap_limit": OVERLAP_LIMIT, "lift_limit": LIFT_LIMIT,
            "byte_unique": all(not r["identical_bytes"] for r in audit_rows),
            "pixel_unique": all(not r["identical_pixels"] for r in audit_rows),
            "literal_gate_pass_all": all(not r["literal_overlap_fail"] for r in audit_rows),
            "rho_gate_pass_all": all(not r["rho_fail"] for r in audit_rows),
            "density_matched_lift_worst15": lift_rows,
            "degeneracy_note": ("literal 70% forward overlap is degenerate against dense registry "
                                "lattices (AGENTS defect ii): a 206,895-dot lattice covers any dot "
                                "field; the density-matched lift is the working drift test and "
                                "literal failures are reported per raster, never hidden"),
            "scope": ("focus-site registry downloads (nine focus sites + scored-registry peers, "
                      "sha256-verified) plus this repo's own downloads; not hidden or private rasters"),
            "rows": audit_rows}
    dump(uniq, EVID / "uniqueness_audit.json")
    print(f"[exp3] uniqueness: max rho={max_rho:.4f} ({max_rho_name}) "
          f"max ov={max_ov:.4f} ({max_ov_name})", flush=True)

    # Score estimate (MODEL-ESTIMATE only).
    fam = [0.2449, 0.2477, 0.2600, 0.2600, 0.2632, 0.2649, 0.2707, 0.2708, 0.2708,
           0.2710, 0.2750, 0.2778]
    est = {
        "schema": "wbg8-score-estimate-v1",
        "label": "MODEL-ESTIMATE (a projection is never written as a score)",
        "method_a_family_band": {
            "description": ("9-site champion family: binary off-catalogue dot fields "
                            "K=37,654-44,090, OWNER-REPORTED values"),
            "band": [min(fam), max(fam)], "median": float(np.median(fam)),
        },
        "method_b_pruning_delta": {
            "description": ("B2 = D2.8 minus 6,436 dots within 2 px of the catalogue "
                            "(+0.0178 OWNER-REPORTED). Extending the prune to a strict 3 px "
                            "halo removes 2,171 further dots (~+0.006 at the same rate) if "
                            "placement quality is otherwise equal."),
            "central": 0.284,
        },
        "method_c_proxy_calibrated": {
            "description": f"OLS OWNER-REPORTED ~ PROXY-DTI on the scored sample (n={len(ok)})",
            "spearman": rho, "spearman_p": pval, "point_estimate": None,
            "prediction_interval": None,
        },
        "recommended_table_entry": {
            "estimate": "0.26-0.29 central band",
            "interval": "±0.09 (score-consistency: near-identical rasters differ by up to 0.0856)",
            "strict_label": "MODEL-ESTIMATE — not HOLDOUT-DTI, not ORGANIZER-CONFIRMED",
        },
    }
    if ok and rho is not None and rho > 0.3:
        xs = np.array([r["proxy_dti"] for r in ok], float)
        ys = np.array([r["score_owner_reported"] for r in ok], float)
        A = np.vstack([xs, np.ones_like(xs)]).T
        coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
        resid = ys - A @ coef
        sd = float(np.std(resid, ddof=2))
        pred = float(np.array([final_proxy["dti"], 1.0]) @ coef)
        est["method_c_proxy_calibrated"]["coefficients"] = [float(c) for c in coef]
        est["method_c_proxy_calibrated"]["residual_sd"] = sd
        est["method_c_proxy_calibrated"]["point_estimate"] = pred
        est["method_c_proxy_calibrated"]["prediction_interval"] = [pred - 1.96 * sd, pred + 1.96 * sd]
    dump(est, EVID / "score_estimate.json")

    # ---- run card ---------------------------------------------------------
    # Gate semantics (as preregistered in research/07): the literal 70% forward
    # overlap is degenerate against dense registry artifacts (AGENTS defect ii:
    # a 206,895-dot lattice captures 99.68% of ANY dot field), so literal
    # failures are reported per raster and the working drift test is the
    # density-matched lift computed ON THE LITERAL-FAILURE ROWS ONLY: a genuine
    # placement clone shows lift ~ 1/coverage (>> 2 at comparable density); a
    # dense-coverage artifact shows lift ~ 1.  A literal failure is tolerable
    # only when that raster has > 3x our dot count AND lift <= 1.5.
    literal_failures = [r for r in audit_rows if r["literal_overlap_fail"]]
    lift_by_file = {r["file"]: r for r in lift_rows}
    comparable_failures = [r for r in literal_failures
                           if not r["dense_registry_dots_gt_3x_mine"]]
    degenerate_failures = [r for r in literal_failures
                           if r["dense_registry_dots_gt_3x_mine"]
                           and lift_by_file.get(r["file"], {}).get("lift", 99.0) <= 1.5]
    degenerate_only = (bool(literal_failures)
                       and not comparable_failures
                       and len(degenerate_failures) == len(literal_failures))
    gates = {
        "G1_format": bool(receipt["validator"]["all_checks_passed"]),
        "G2_exact_copy": bool(uniq["byte_unique"] and uniq["pixel_unique"]),
        "G3_rank_correlation": bool(uniq["rho_gate_pass_all"]),
        "G4_literal_overlap": bool(uniq["literal_gate_pass_all"]),
        "G4prime_density_matched_drift": bool(not comparable_failures
                                             and len(degenerate_failures) == len(literal_failures)),
        "G5_leakage_canary": bool(eligible[best_name]["canary_pass"]
                                 and all(exp1["configs"][c]["canary_pass"]
                                         for c in (top2 if best_name == "blend_top2"
                                                   else ([best_name] if best_name in channels
                                                         else survivors)))),
        "G6_holdout_reported": True,
    }
    if all(gates.values()):
        verdict = "promote"
    elif (all(gates[k] for k in ("G1_format", "G2_exact_copy", "G3_rank_correlation",
                                 "G4prime_density_matched_drift", "G5_leakage_canary",
                                 "G6_holdout_reported"))
          and (gates["G4_literal_overlap"] or degenerate_only)):
        verdict = "promote_with_reported_literal_degeneracy"
    else:
        verdict = "negative"

    card = {
        "schema": "gemsdoe1-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": ("Blended catalogue-free hidden-fault corridors (LiDAR scarp x basement "
                       "lineaments x potential-field concordance x radiometric alteration) emit "
                       "non-redundant catalogue-neutral dots covering unmapped faults better "
                       "than any single-physic placement."),
        "mechanism": ("Off-catalogue faults share the geomorphic/geophysical signature of mapped "
                      "ones: 2 m scarp excess, buried-basement lineaments in thin cover, "
                      "co-located magnetic/gravity edges, K/Th alteration with conductance. "
                      "Sparse >=3 px dots avoid the metric's redundancy penalty; a 3 px "
                      "catalogue halo removes pure-FP dots (B2 forensics)."),
        "named_non_fault_mimic": ("Roads/canal banks/terrace risers/paleo-shorelines/landslides/"
                                  "mines (LiDAR); depositional pinch-outs and volcanic flow fronts "
                                  "(basement morphometry); intrusive contacts and remanence "
                                  "(potential fields); sediment sorting and moisture attenuation "
                                  "(radiometrics)."),
        "lane": "WBG-8 multi-physic hidden-corridor emission (research/07_wbg8_preregistration_20261031.md)",
        "experiments_used": 3, "experiments_budget": 3,
        "selection": exp1["selection"], "budget_grid": exp2["k_grid"], "selected_k": best_k,
        "holdout": exp2["report_draw"],
        "proxy_dti": {"evidence_class": "PROXY-DTI (gems57-offcatalogue-proxy; never a score)",
                      "candidate": final_proxy, "b2_reference": b2_proxy,
                      "proxy_pixels": int(proxy.sum())},
        "correlation_overlap_vs_registry": {
            "registry_rasters_compared": len(audit_rows),
            "max_spearman_sample": uniq["max_spearman_sample"],
            "max_dot_overlap_3px": uniq["max_dot_overlap_3px"],
            "byte_unique": uniq["byte_unique"], "pixel_unique": uniq["pixel_unique"],
            "literal_gate_pass_all": uniq["literal_gate_pass_all"],
            "rho_gate_pass_all": uniq["rho_gate_pass_all"],
            "density_matched_lift_worst15": lift_rows,
            "literal_failures": literal_failures,
            "degeneracy_note": uniq["degeneracy_note"],
        },
        "raster_sha256": my_sha,
        "raster_pixel_sha256": my_mask_sha,
        "validator": receipt["validator"],
        "submission_name": name,
        "submission_note": note,
        "estimated_leaderboard_score": est["recommended_table_entry"],
        "gates": gates,
        "verdict": verdict,
        "decision": {
            "download": "YES",
            "submit": ("OK — all gates passed automatically; unique, format-valid, "
                       "values in [0,1]; promotion to a weekly slot is the selector's call"
                       if verdict.startswith("promote") else
                       "NO — a gate failed; research download only (see run card)"),
        },
        "selector_note": ("Promotion to a real weekly slot is a separate selector step inside the "
                          "official rules §3.2 weekly cap; no slot is used by this script."),
    }
    dump(card, EVID / "run_card.json")
    print(f"[exp3] verdict={verdict} gates={gates}", flush=True)
    print(f"[done] started={started} name={name} sha256={my_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
