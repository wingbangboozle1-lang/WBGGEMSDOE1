#!/usr/bin/env python3
"""E3: build the unique final TIF + gates + run card.

Selection (pre-committed, P(win)-grounded):
  1. Dedupe lattice twins (S2.35 == S2.8 on-grid) by mask hash.
  2. Gate set: unique cells (corr < 0.90 AND 3px-overlap < 70% vs every
     focus-9 raster) with SGMC point estimate above the champion bar.
  3. Ship (rule v2, amended after v1 shipped a paired-marginal cell — see
     code history): among unique bar-beaters with PAIRED-DELTA CI > 0 vs the
     bar raster (same-blocks paired block bootstrap), ship max transfer-ratio
     R = (A_sgmc/N) / (0.8 + 0.2*N/G), G = 12226 (sibling lattice calibration
     of hidden-truth mass; sensitivity over {12226, 20000, 62122} reported).
     Rationale: live truth is sparse (~12k) vs SGMC truth (62k); under
     proportional credit transfer (factor cancels in ratios), R ranks live
     DTI via the naive closure. Pure max-SGMC would overspend N. Fallback if
     no cell is paired-confident: max-R point-beater, flagged MARGINAL.
     The v1 ship (s_topo-B30000-S2.0, paired p=0.36) is preserved in git
     history, not in downloads/.
  4. Paired block-bootstrap DELTA (ship vs bar raster, same blocks) for the
     win claim; univariate OLS live~SGMC projection reported WITH an
     out-of-range credibility flag (our SGMC exceeds all champions, and the
     champion cloud is inverse in N — the OLS point is NOT credible).
  5. Verdict promote iff unique AND format-pass AND point-bar-beaten.
     ok_to_submit stays False: promotion is a separate selector step.

Writes docs/downloads pair + audit JSON + evidence/e3_run_card.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg1 import emission, holdout, submission, validate  # noqa: E402
from wbg1 import metric as M  # noqa: E402
from wbg1.paths import (data_dir, downloads_dir, evidence_dir, registry_dir,  # noqa: E402
                        registry_raster_dir, work_dir)

OWNER_REPORTED = {
    "G24-d1.5": 0.2477, "G25-d2.8": 0.2600, "G27-gap": 0.2449,
    "G28-rung30": 0.2710, "G30-poisson": 0.2600, "G31-h274solo": 0.2708,
    "G32-h33": 0.2778, "G33-analog": 0.2632, "G36-pinn": 0.2750,
}
SURF_IDX = {"s_geo": 0, "s_cond": 1, "s_mag": 2, "s_topo": 3, "s_grav": 4,
            "h1": 6}
H1W_W = np.array([0.1, 0.1, 0.2, 0.5, 0.1])
G_CALIB = 12226
G_SENS = [12226, 20000, 62122]


def transfer_R(a_sgmc: float, n: int, g: float = G_CALIB) -> float:
    return float((a_sgmc / max(1, n)) / (0.8 + 0.2 * n / g))


def fit_projection(e2: dict, our_sgmc: float, our_n: int) -> dict:
    xs, ys, ns = [], [], []
    for k, v in e2["champions"].items():
        if k in OWNER_REPORTED:
            xs.append(v["sgmc_DTI"])
            ys.append(OWNER_REPORTED[k])
            ns.append(v["dots"])
    xs, ys, ns = map(np.array, (xs, ys, ns))
    # Univariate live ~ SGMC: REJECTED (N-confounded, wrong sign).
    A = np.vstack([xs, np.ones_like(xs)]).T
    slope, intercept = np.linalg.lstsq(A, ys, rcond=None)[0]
    # Headline: bivariate live ~ SGMC + N (structural form matches DTI algebra:
    # +credit, -denominator). n=9; our SGMC is above range (extrapolation).
    B = np.vstack([xs, ns, np.ones_like(xs)]).T
    bb, *_ = np.linalg.lstsq(B, ys, rcond=None)
    pred = float(bb[0] * our_sgmc + bb[1] * our_n + bb[2])
    resid = ys - (B @ bb)
    rmse = float(np.sqrt((resid ** 2).mean()))
    ss = float(((ys - ys.mean()) ** 2).sum())
    r2 = float(1 - (resid ** 2).sum() / ss) if ss > 0 else 0.0
    # leave-one-out RMSE for an honest interval
    loo_errs = []
    for i in range(len(xs)):
        m = np.ones(len(xs), dtype=bool)
        m[i] = False
        bi, *_ = np.linalg.lstsq(B[m], ys[m], rcond=None)
        loo_errs.append(ys[i] - (B[i] @ bi))
    loo_rmse = float(np.sqrt(np.mean(np.array(loo_errs) ** 2)))
    in_range = bool(xs.min() <= our_sgmc <= xs.max())
    return {
        "method": ("OLS live(owner-reported) ~ SGMC + N over 9 champions "
                   "(structural DTI form: +credit, -denominator)"),
        "coef_sgmc": float(bb[0]), "coef_N": float(bb[1]),
        "intercept": float(bb[2]), "r2": r2, "rmse": rmse,
        "loo_rmse": loo_rmse, "n": len(xs),
        "champion_sgmc_range": [float(xs.min()), float(xs.max())],
        "champion_N_range": [int(ns.min()), int(ns.max())],
        "our_sgmc": float(our_sgmc), "our_N": int(our_n),
        "in_calibration_range": in_range,
        "PROJECTION": pred,
        "PROJECTION_interval": [pred - 1.96 * loo_rmse, pred + 1.96 * loo_rmse],
        "caveats": ["our SGMC above champion range (extrapolation)",
                    "n=9 incl. byte-duplicate champion rows, owner-reported live inputs (not receipts)",
                    "SGMC->live transfer assumed",
                    "interval is fit-noise-only; true uncertainty is "
                    "extrapolation-dominated and UNQUANTIFIED — directional, not precise"],
        "univariate_rejected": {
            "slope": float(slope), "intercept": float(intercept),
            "reason": "N-confounded (negative slope); our-x out of range"},
        "label": "PROJECTION (model extrapolation, NOT a score)",
    }


def parse_key(key: str) -> tuple[str, int, float]:
    sname, btok, stok = key.rsplit("-", 2)
    return sname, int(btok[1:]), float(stok[1:])


def surface_for(sname: str, stack, ctx) -> np.ndarray:
    if sname == "h1w":
        from wbg1 import features as _F
        parts = np.asarray(stack[0:5]).astype(np.float64)
        surf = _F.rank_norm((parts * H1W_W[:, None, None]).sum(axis=0)
                            * np.asarray(stack[5]), ctx.foot)
        del parts
        return surf
    return np.asarray(stack[SURF_IDX[sname]])


def paired_delta(mask_a: np.ndarray, mask_b: np.ndarray, ctx,
                 n_rep: int = 5000, seed: int = 0) -> dict:
    """Paired block-bootstrap CI on (DTI_a - DTI_b), SGMC instrument."""
    truth = ctx.sgmc_offcat
    pa = np.asarray(mask_a, dtype=bool) & ctx.foot & ~ctx.labels
    pb = np.asarray(mask_b, dtype=bool) & ctx.foot & ~ctx.labels
    ka_t = M.kernel_from_mask(truth)
    ka_p = M.kernel_from_mask(pa)
    kb_p = M.kernel_from_mask(pb)
    bids = M.block_ids(ctx.foot.shape, 16)
    nb = 256
    acc = {}
    for tag, pm, kp in (("a", pa, ka_p), ("b", pb, kb_p)):
        ab = np.zeros(nb)
        fb = np.zeros(nb)
        yy, xx = np.nonzero(pm)
        if len(yy):
            bb = bids[yy, xx]
            kv = ka_t[yy, xx].astype(np.float64)
            np.add.at(ab, bb, kv)
            np.add.at(fb, bb, 1.0 - kv)
        acc[tag] = (ab, fb)
    # FNw blocks depend on pred kernel: per-truth-pixel contributions per mask
    ty, tx = np.nonzero(truth)
    tb = bids[ty, tx]
    fna = np.zeros(nb)
    fnb = np.zeros(nb)
    np.add.at(fna, tb, 1.0 - ka_p[ty, tx].astype(np.float64))
    np.add.at(fnb, tb, 1.0 - kb_p[ty, tx].astype(np.float64))
    aa, fpa = acc["a"]
    ab, fpb = acc["b"]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nb, size=(n_rep, nb))
    da = aa[idx].sum(1) / (aa[idx].sum(1) + 0.2 * fpa[idx].sum(1) + 0.8 * fna[idx].sum(1))
    db = ab[idx].sum(1) / (ab[idx].sum(1) + 0.2 * fpb[idx].sum(1) + 0.8 * fnb[idx].sum(1))
    d = da - db
    return {"delta_point": float(M.dti_from_terms(aa.sum(), fpa.sum(), fna.sum())
                                 - M.dti_from_terms(ab.sum(), fpb.sum(), fnb.sum())),
            "delta_mean": float(d.mean()),
            "delta_ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "p_one_sided_gt0": float((d <= 0).mean()),
            "n_rep": n_rep, "seed": seed}


def main() -> int:
    t0 = time.time()
    e2 = json.loads((evidence_dir() / "e2_sweep.json").read_text())
    ctx = holdout.load_holdout_context(data_dir())
    stack = np.lib.format.open_memmap(work_dir() / "h1_stack.npy", mode="r")
    reg = validate.load_registry_list(registry_dir() / "focus9.json",
                                      registry_raster_dir())
    rdir = registry_raster_dir()
    allowed = emission.flank_allowed(ctx.foot, ctx.labels, 2.0)

    bar_id = max(e2["champions"], key=lambda k: e2["champions"][k]["sgmc_DTI"])
    bar = e2["champions"][bar_id]["sgmc_DTI"]
    bar_ci = e2["champions"][bar_id]["sgmc_ci95"]
    focus = json.loads((registry_dir() / "focus9.json").read_text())
    bar_file = next(r["file"] for r in focus["rasters"] if r["id"] == bar_id)
    bar_mask = holdout.read_binary_tif(rdir / bar_file)
    print(f"[E3] champion SGMC bar: {bar_id} = {bar:.5f} [{bar_ci[0]:.5f},{bar_ci[1]:.5f}]",
          flush=True)

    ranked = sorted(e2["h1_grid"], key=lambda k: e2["h1_grid"][k]["sgmc_DTI"],
                    reverse=True)
    shortlist, seen = [], {}
    for key in ranked:
        if len([r for r in shortlist if not r.get("skipped")]) >= 8:
            break
        sname, b, s = parse_key(key)
        m = emission.poisson_disk_thin_priority(surface_for(sname, stack, ctx),
                                               allowed, s, b, seed=1)
        h = hashlib.sha256(m.tobytes()).hexdigest()
        if h in seen:
            shortlist.append({"key": key, "twin_of": seen[h], "skipped": True,
                              "sgmc_DTI": e2["h1_grid"][key]["sgmc_DTI"]})
            continue
        seen[h] = key
        uq = validate.uniqueness_vs_registry(m, ctx.foot, reg)
        sg = holdout.evaluate_sgmc(m, ctx)
        pd = paired_delta(m, bar_mask, ctx)
        n = int(m.sum())
        a_val = sg["pooled"]["A"]
        row = {"key": key, "sgmc_DTI": sg["pooled"]["DTI"],
               "sgmc_ci95": sg["ci"]["ci95"], "A_sgmc": a_val, "N": n,
               "R": {str(g): transfer_R(a_val, n, g) for g in G_SENS},
               "unique": uq["unique"], "worst_corr": uq["worst_corr"],
               "worst_overlap": uq["worst_overlap"],
               "beats_bar_point": bool(sg["pooled"]["DTI"] > bar),
               "paired_delta": pd["delta_point"],
               "paired_ci95": pd["delta_ci95"],
               "paired_confident": bool(pd["delta_ci95"][0] > 0)}
        shortlist.append(row)
        wc, wo = uq["worst_corr"], uq["worst_overlap"]
        print(f"[E3] {key}: SGMC={sg['pooled']['DTI']:.5f} R={row['R'][str(G_CALIB)]:.6f} "
              f"unique={uq['unique']} corr={wc['id']}:{wc['corr']:.3f} "
              f"ov={wo['id']}:{wo['overlap_3px']:.3f} "
              f"d={pd['delta_point']:.5f} CI=[{pd['delta_ci95'][0]:.5f},{pd['delta_ci95'][1]:.5f}]",
              flush=True)

    confident = [r for r in shortlist
                 if not r.get("skipped") and r["unique"] and r["beats_bar_point"]
                 and r["paired_confident"]]
    if confident:
        confident.sort(key=lambda r: r["R"][str(G_CALIB)], reverse=True)
        ship, marginal = confident[0], False
        cands = confident
    else:
        cands = [r for r in shortlist
                 if not r.get("skipped") and r["unique"] and r["beats_bar_point"]]
        if cands:
            cands.sort(key=lambda r: r["R"][str(G_CALIB)], reverse=True)
            ship, marginal = cands[0], True
        else:
            ship, marginal = None, False
    if ship is not None:
        sens_ok = all(max(cands, key=lambda r: r["R"][str(g)])["key"] == ship["key"]
                      for g in G_SENS)
    else:
        sens_ok = False
    if ship is None:
        best = next(r for r in shortlist if not r.get("skipped"))
        ship_key = best["key"]
        print(f"[E3] NO UNIQUE BAR-BEATER; research-only ship {ship_key} (negative)",
              flush=True)
    else:
        ship_key = ship["key"]
        print(f"[E3] shipping {ship_key} R={ship['R'][str(G_CALIB)]:.6f} "
              f"sens_stable={sens_ok} marginal={marginal}", flush=True)
    sname, b, s = parse_key(ship_key)
    mask = emission.poisson_disk_thin_priority(surface_for(sname, stack, ctx),
                                              allowed, s, b, seed=1)

    hr = holdout.evaluate_hide_and_recover(mask, ctx, flank_exclude_px=2.0)
    sg = holdout.evaluate_sgmc(mask, ctx)
    uniq = validate.uniqueness_vs_registry(mask, ctx.foot, reg)
    pd = paired_delta(mask, bar_mask, ctx)
    print(f"[E3] paired Δ vs {bar_id}: {pd['delta_point']:.5f} "
          f"CI=[{pd['delta_ci95'][0]:.5f},{pd['delta_ci95'][1]:.5f}] "
          f"p(Δ≤0)={pd['p_one_sided_gt0']:.4f}", flush=True)

    proj = fit_projection(e2, sg["pooled"]["DTI"], int(mask.sum()))
    beats_bar = bool(sg["pooled"]["DTI"] > bar)
    ts = submission.utc_tag()
    slug = f"{sname}-blind-{b}d-s{str(s).replace('.', 'p')}"
    note_core = (f"WBG1 {sname} {b}d SGMC {sg['pooled']['DTI']:.4f} "
                 f"vs bar {bar:.4f} d={pd['delta_point']:.4f}"
                 + (" MARGINAL" if (ship is not None and marginal) else ""))
    candidate_meta = {
        "candidate_id": f"WBG1-{sname}-{b}",
        "surface": sname, "grid_key": ship_key,
        "description": ("H1-lane blind fault emission; best transfer-ratio-R "
                        "among unique SGMC-bar-beaters; priority Poisson-disk, "
                        "B=2 flank exclusion"),
        "HOLDOUT-DTI_sgmc": sg["pooled"]["DTI"], "sgmc_ci95": sg["ci"]["ci95"],
        "sgmc_evaluator": sg["evaluator"], "sgmc_n_truth": sg["n_truth"],
        "HOLDOUT-DTI_hide": hr["pooled"]["DTI"], "hide_ci95": hr["ci"]["ci95"],
        "hide_evaluator": hr["evaluator"],
        "n_withheld_total": hr["n_withheld_total"],
        "champion_sgmc_bar": {"id": bar_id, "dti": bar, "ci95": bar_ci},
        "paired_delta_vs_bar": pd,
        "R_transfer": {str(g): transfer_R(sg["pooled"]["A"], int(mask.sum()), g)
                       for g in G_SENS},
        "R_sensitivity_stable": sens_ok if ship else False,
        "beats_champion_bar": beats_bar,
        "projection": proj,
        "uniqueness_shortlist": shortlist,
        "submission_note": note_core[:140],
    }
    audit = submission.write_submission_pair(
        mask, ctx.foot, Path(ctx.template_path), downloads_dir(), slug, ts,
        candidate_meta)
    fmt_z = validate.validate_format(
        downloads_dir() / audit["zeros_tif"]["filename"], Path(ctx.template_path),
        strict_finite=True)
    fmt_n = validate.validate_format(
        downloads_dir() / audit["nan_tif"]["filename"], Path(ctx.template_path),
        strict_finite=False)
    print(f"[E3] wrote {audit['zeros_tif']['filename']} "
          f"zeros_pass={fmt_z['pass']} nan_pass={fmt_n['pass']}", flush=True)

    promoted = bool(fmt_z["pass"] and uniq["unique"] and beats_bar
                      and ship is not None and not marginal)
    verdict = "promote" if promoted else "negative"
    run_card = {
        "hypothesis": ("H1-lane: blind faults missing from USGS/INGENIOUS "
                       "catalogue are ranked by label-free lineament transforms "
                       "(winner: LiDAR-scarp/curvature surface); emission at the "
                       "transfer-ratio-optimal operating point."),
        "mechanism": ("rank lineament surface, soft Andersonian gate (h1/h1w) "
                      "or pure scarp rank (s_topo), priority Poisson-disk, B=2 "
                      "flank exclusion; budget/spacing by SGMC holdout + "
                      "transfer-ratio R for sparse live truth."),
        "non_fault_mimic": ("Pleistocene Lake Lahontan shorelines/terraces and "
                            "basalt flow margins: identical short-wavelength "
                            "curvature + conductivity steps; dominant expected FP."),
        "primary_instrument": sg["evaluator"],
        "sgmc_dti": sg["pooled"]["DTI"], "sgmc_ci95": sg["ci"]["ci95"],
        "sgmc_n_truth": sg["n_truth"],
        "holdout_dti_hide": hr["pooled"]["DTI"],
        "holdout_ci95_hide": hr["ci"]["ci95"],
        "hide_evaluator": hr["evaluator"], "n_withheld": hr["n_withheld_total"],
        "champion_sgmc_bar": {"id": bar_id, "dti": bar, "ci95": bar_ci},
        "paired_delta_vs_bar": pd,
        "beats_champion_holdout_bar": beats_bar,
        "selection_rule": ("v2: max-R among unique bar-beaters with paired-delta "
                           "CI>0 vs bar; fallback (marginal) max-R point-beater"),
        "marginal_selection": bool(ship is not None and marginal),
        "R_transfer": candidate_meta["R_transfer"],
        "correlation_overlap_vs_registry": {
            "worst_corr": uniq["worst_corr"],
            "worst_overlap": uniq["worst_overlap"]},
        "unique": uniq["unique"],
        "uniqueness_shortlist": shortlist,
        "raster_sha256": audit["zeros_tif"]["sha256"],
        "validator": {"zeros": fmt_z, "nan": fmt_n},
        "submission_name": audit["zeros_tif"]["filename"],
        "submission_note": note_core[:140],
        "projection": proj,
        "verdict": verdict, "ok_to_submit": False,
        "ok_to_submit_note": "selector step separate (weekly cap)",
        "elapsed_s": round(time.time() - t0, 1),
    }
    (evidence_dir() / "e3_run_card.json").write_text(json.dumps(run_card, indent=2))
    ap = downloads_dir() / audit["audit_json"]
    ja = json.loads(ap.read_text())
    ja["run_card"] = {k: v for k, v in run_card.items() if k != "validator"}
    ja["format_validation"] = {"zeros": fmt_z, "nan": fmt_n}
    ap.write_text(json.dumps(ja, indent=2))
    print(f"[E3] verdict={verdict} ok_to_submit=False (selector separate)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
