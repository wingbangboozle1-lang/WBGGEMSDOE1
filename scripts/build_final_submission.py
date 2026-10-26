#!/usr/bin/env python3
"""E3: build the unique final TIF + gates + run card.

Reads evidence/e1_surface.json + evidence/e2_sweep.json, ranks the E2 grid by
the PRIMARY instrument (SGMC off-catalogue pooled DTI; hide-and-recover-vs-
catalogue is diagnostic-only for B-excluded emissions because of the
demonstrated floor effect), ships the best-UNIQUE grid cell among the top 5
(unique = corr < 0.90 AND 3px-overlap < 70% vs every focus-9 raster, checked
on final dots), then:
  * format validator (F1..F6, strict-finite)
  * MODEL projection of live DTI via SGMC-holdout->live linear map fit on the
    9 champions (labelled PROJECTION, never a score)
  * promotion gate: unique AND format-pass AND beats champion SGMC bar
  * writes docs/downloads pair + audit JSON + evidence/e3_run_card.json

Promotion to a real weekly slot is a SEPARATE selector step (weekly cap on the
submission page). This script only writes the automated verdict.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbg1 import emission, holdout, submission, validate  # noqa: E402
from wbg1.paths import (data_dir, downloads_dir, evidence_dir, registry_dir,  # noqa: E402
                        registry_raster_dir, work_dir)

# Owner-reported public scores (task statement / sibling ledgers). NOT organizer
# receipts; used only to fit the labelled PROJECTION map.
OWNER_REPORTED = {
    "G24-d1.5": 0.2477, "G25-d2.8": 0.2600, "G27-gap": 0.2449,
    "G28-rung30": 0.2710, "G30-poisson": 0.2600, "G31-h274solo": 0.2708,
    "G32-h33": 0.2778, "G33-analog": 0.2632, "G36-pinn": 0.2750,
}
SURF_IDX = {"s_geo": 0, "s_cond": 1, "s_mag": 2, "s_topo": 3, "s_grav": 4,
            "h1": 6}
H1W_W = np.array([0.1, 0.1, 0.2, 0.5, 0.1])  # geo cond mag topo grav


def fit_projection(e2: dict, our_sgmc: float) -> dict:
    xs, ys = [], []
    for k, v in e2["champions"].items():
        if k in OWNER_REPORTED:
            xs.append(v["sgmc_DTI"])
            ys.append(OWNER_REPORTED[k])
    xs = np.array(xs)
    ys = np.array(ys)
    A = np.vstack([xs, np.ones_like(xs)]).T
    slope, intercept = np.linalg.lstsq(A, ys, rcond=None)[0]
    pred = slope * our_sgmc + intercept
    resid = ys - (slope * xs + intercept)
    rmse = float(np.sqrt((resid ** 2).mean()))
    ss = float(((ys - ys.mean()) ** 2).sum())
    r2 = float(1 - (resid ** 2).sum() / ss) if ss > 0 else 0.0
    return {
        "method": ("ordinary least squares live(owner-reported) ~ SGMC-HOLDOUT-DTI "
                   "over 9 champions (hide-vs-catalogue is floored, cannot map)"),
        "slope": float(slope), "intercept": float(intercept), "r2": r2,
        "rmse": rmse, "n": len(xs),
        "PROJECTION": float(pred),
        "PROJECTION_interval": [float(pred - 1.96 * rmse), float(pred + 1.96 * rmse)],
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


def main() -> int:
    t0 = time.time()
    e2 = json.loads((evidence_dir() / "e2_sweep.json").read_text())
    ctx = holdout.load_holdout_context(data_dir())
    stack = np.lib.format.open_memmap(work_dir() / "h1_stack.npy", mode="r")
    reg = validate.load_registry_list(registry_dir() / "focus9.json",
                                      registry_raster_dir())
    allowed = emission.flank_allowed(ctx.foot, ctx.labels, 2.0)

    ranked = sorted(e2["h1_grid"], key=lambda k: e2["h1_grid"][k]["sgmc_DTI"],
                    reverse=True)
    print(f"[E3] unconstrained best: {ranked[0]} "
          f"SGMC={e2['h1_grid'][ranked[0]]['sgmc_DTI']:.5f}", flush=True)
    shortlist = []
    ship_key, mask = None, None
    for key in ranked[:5]:
        sname, b, s = parse_key(key)
        m = emission.poisson_disk_thin_priority(surface_for(sname, stack, ctx),
                                               allowed, s, b, seed=1)
        uq = validate.uniqueness_vs_registry(m, ctx.foot, reg)
        wc, wo = uq["worst_corr"], uq["worst_overlap"]
        shortlist.append({"key": key, "sgmc_DTI": e2["h1_grid"][key]["sgmc_DTI"],
                          "unique": uq["unique"], "worst_corr": wc,
                          "worst_overlap": wo})
        print(f"[E3] {key}: unique={uq['unique']} "
              f"worst_corr={wc['id']}:{wc['corr']:.4f} "
              f"worst_ov={wo['id']}:{wo['overlap_3px']:.4f}", flush=True)
        if uq["unique"] and ship_key is None:
            ship_key, mask = key, m
    if ship_key is None:  # fail closed: research-only artifact, negative verdict
        ship_key = ranked[0]
        sname, b, s = parse_key(ship_key)
        mask = emission.poisson_disk_thin_priority(surface_for(sname, stack, ctx),
                                                  allowed, s, b, seed=1)
        print(f"[E3] NO UNIQUE CANDIDATE in top-5; shipping {ship_key} as "
              f"research-only (verdict will be negative)", flush=True)
    sname, b, s = parse_key(ship_key)
    print(f"[E3] shipping: {ship_key} dots={int(mask.sum())} "
          f"on_catalogue={int((mask & ctx.labels).sum())}", flush=True)

    hr = holdout.evaluate_hide_and_recover(mask, ctx, flank_exclude_px=2.0)
    sg = holdout.evaluate_sgmc(mask, ctx)

    uniq = validate.uniqueness_vs_registry(mask, ctx.foot, reg)
    ts = submission.utc_tag()
    slug = f"{sname}-blind-{b}d-s{str(s).replace('.', 'p')}"
    proj = fit_projection(e2, sg["pooled"]["DTI"])
    champ_bar = max(v["sgmc_DTI"] for v in e2["champions"].values())
    beats_bar = bool(sg["pooled"]["DTI"] > champ_bar)

    note_core = (f"WBG1 {sname} {b}d SGMC {sg['pooled']['DTI']:.4f} "
                 f"vs champ {champ_bar:.4f} PROJ~{proj['PROJECTION']:.3f}")
    candidate_meta = {
        "candidate_id": f"WBG1-{sname}-{b}",
        "surface": sname,
        "grid_key": ship_key,
        "description": ("H1-lane blind fault emission (label-free lineament "
                        "transforms, Andersonian gate, priority Poisson-disk, "
                        "B=2 flank exclusion); best-unique E2 grid cell"),
        "HOLDOUT-DTI_sgmc": sg["pooled"]["DTI"],
        "sgmc_ci95": sg["ci"]["ci95"],
        "sgmc_evaluator": sg["evaluator"],
        "sgmc_n_truth": sg["n_truth"],
        "HOLDOUT-DTI_hide": hr["pooled"]["DTI"],
        "hide_ci95": hr["ci"]["ci95"],
        "hide_evaluator": hr["evaluator"],
        "n_withheld_total": hr["n_withheld_total"],
        "champion_sgmc_bar": champ_bar,
        "beats_champion_bar": beats_bar,
        "projection": proj,
        "uniqueness_shortlist_top5": shortlist,
        "submission_note": note_core[:140],
    }
    audit = submission.write_submission_pair(
        mask, ctx.foot, Path(ctx.template_path), downloads_dir(), slug, ts,
        candidate_meta)
    print(f"[E3] wrote {audit['zeros_tif']['filename']}", flush=True)

    fmt_z = validate.validate_format(
        downloads_dir() / audit["zeros_tif"]["filename"],
        Path(ctx.template_path), strict_finite=True)
    fmt_n = validate.validate_format(
        downloads_dir() / audit["nan_tif"]["filename"],
        Path(ctx.template_path), strict_finite=False)
    print(f"[E3] format zeros_pass={fmt_z['pass']} nan_pass={fmt_n['pass']}",
          flush=True)

    promoted = bool(fmt_z["pass"] and uniq["unique"] and beats_bar)
    verdict = "promote" if promoted else "negative"
    run_card = {
        "hypothesis": ("H1-lane: blind faults missing from USGS/INGENIOUS "
                       "catalogue are ranked by label-free lineament transforms "
                       "(topo/mag/cond/grav + geothermal discharge coincidence, "
                       "Andersonian strike gate); emission at the SGMC-validated "
                       "operating point."),
        "mechanism": ("rank-consensus lineament surface, soft Andersonian strike "
                      "gate, break-even-budgeted priority Poisson emission with "
                      "B=2 catalogue-flank exclusion; surface+budget+spacing chosen "
                      "on WBG1-SGMC-CAL-v1.0."),
        "non_fault_mimic": ("Pleistocene Lake Lahontan shorelines/terraces and "
                            "basalt flow margins: identical short-wavelength "
                            "curvature + conductivity steps; dominant expected FP."),
        "primary_instrument": sg["evaluator"],
        "sgmc_dti": sg["pooled"]["DTI"],
        "sgmc_ci95": sg["ci"]["ci95"],
        "sgmc_n_truth": sg["n_truth"],
        "holdout_dti_hide": hr["pooled"]["DTI"],
        "holdout_ci95_hide": hr["ci"]["ci95"],
        "hide_evaluator": hr["evaluator"],
        "n_withheld": hr["n_withheld_total"],
        "champion_sgmc_bar": champ_bar,
        "beats_champion_holdout_bar": beats_bar,
        "correlation_overlap_vs_registry": {
            "worst_corr": uniq["worst_corr"],
            "worst_overlap": uniq["worst_overlap"]},
        "unique": uniq["unique"],
        "uniqueness_shortlist_top5": shortlist,
        "raster_sha256": audit["zeros_tif"]["sha256"],
        "validator": {"zeros": fmt_z, "nan": fmt_n},
        "submission_name": audit["zeros_tif"]["filename"],
        "submission_note": note_core[:140],
        "projection": proj,
        "verdict": verdict,
        "ok_to_submit": False,
        "ok_to_submit_note": ("selector step is separate (weekly cap); site shows "
                              "SUBMIT: YES only on promote + selector approval"),
        "elapsed_s": round(time.time() - t0, 1),
    }
    (evidence_dir() / "e3_run_card.json").write_text(json.dumps(run_card, indent=2))
    audit_path = downloads_dir() / audit["audit_json"]
    ja = json.loads(audit_path.read_text())
    ja["run_card"] = {k: v for k, v in run_card.items() if k != "validator"}
    ja["format_validation"] = {"zeros": fmt_z, "nan": fmt_n}
    audit_path.write_text(json.dumps(ja, indent=2))
    print(f"[E3] verdict={verdict} ok_to_submit=False (selector step separate)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
