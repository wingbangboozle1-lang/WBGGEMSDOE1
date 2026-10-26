#!/usr/bin/env python3
"""Lane TSML — at most 3 experiments. Writes evidence JSON, GeoTIFF, run card."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems1 import canary, detector, grid, holdout, uniqueness, validate  # noqa: E402

UTC = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
EVID = ROOT / "evidence"
DOWN = ROOT / "docs" / "downloads"
REG = ROOT / "data" / "registry"
NINE = REG / "ninesite"
EVID.mkdir(parents=True, exist_ok=True)
DOWN.mkdir(parents=True, exist_ok=True)


def dump(name: str, obj) -> Path:
    p = EVID / name
    p.write_text(json.dumps(obj, indent=2, default=str))
    print(f"wrote {p}")
    return p


def load_binary(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0) & foot


def registry_paths() -> list[Path]:
    out = []
    for folder in (REG, NINE):
        if folder.exists():
            out.extend(sorted(folder.glob("*.tif")))
    # unique by name
    seen = set()
    uniq = []
    for p in out:
        if p.name in seen:
            continue
        seen.add(p.name)
        uniq.append(p)
    return uniq


def main() -> int:
    print("=== WBGGEMSDOE1 experiments", UTC, "===")
    # pin check
    pins = {}
    ddir = grid.data_dir()
    for name, pin in grid.SHA256_PINS.items():
        got = grid.sha256_file(ddir / name)
        pins[name] = {"pin": pin, "got": got, "ok": got == pin}
        print(f"pin {name}: {'OK' if got == pin else 'FAIL'}")
        if got != pin:
            raise SystemExit(f"SHA-256 mismatch for {name}")
    dump("data_pins.json", pins)

    _, foot, _ = grid.read_template()
    labels = grid.read_labels()
    print(f"footprint {int(foot.sum())} catalogue {int(labels.sum())}")
    ctx = holdout.build_context(foot, labels)
    n_hid = sum(f.n_hidden for f in ctx.folds)
    print(f"holdout withheld positives (sum folds): {n_hid}")
    dump(
        "holdout_context.json",
        {
            "evaluator_version": ctx.evaluator_version,
            "collar_px": holdout.COLLAR_PX,
            "n_withheld_sum_folds": n_hid,
            "per_fold": {f.name: f.n_hidden for f in ctx.folds},
        },
    )

    champ_path = NINE / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
    if not champ_path.exists():
        champ_path = REG / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
    champ = load_binary(champ_path, foot)
    print(f"champion dots {int(champ.sum())} on-cat {int((champ & labels).sum())}")

    # ------------------------------------------------------------------ E1 leakage canary
    print("\n--- E1 leakage canaries ---")
    feat = ddir / "gems-geodawn-numerical-features.tif"
    auc_rows = {}
    leaking = []

    def _one(name, field):
        rec = canary.canary_aucs({name: field}, ctx)
        auc = rec["auc"][name]
        auc_rows[name] = auc
        if auc is not None and auc > 0.90:
            leaking.append(name)
        print(f"  AUC {name:32s} {auc}")
        return rec

    d_cat = distance_transform_edt(~labels).astype(np.float32)
    _one("neg_dist_full_catalogue", -d_cat)
    del d_cat
    _one("neg_dist_visible_NW", -ctx.folds[0].d_visible.astype(np.float32))
    for b, bname in grid.BAND_NAMES.items():
        raw, valid = grid.read_band(feat, b)
        filled = grid.fill_nearest(raw, valid & foot)
        _one(f"band{b:02d}_{bname}", filled)
        del raw, filled
    can = {
        "auc": auc_rows,
        "leaking_auc_gt_0.90": leaking,
        "pass_no_detector_leak": all(not x.startswith("band") for x in leaking),
    }
    dump("e1_leakage_canary.json", can)
    print("canary leaking:", can["leaking_auc_gt_0.90"])
    detector_leak = [x for x in leaking if x.startswith("band")]
    e1_pass = "neg_dist_full_catalogue" in leaking and len(detector_leak) == 0
    print("E1 pass (catalogue distance leaks; no band AUC>0.90):", e1_pass)

    # ------------------------------------------------------------------ E2 TSML
    print("\n--- E2 TSML ---")
    tsml = detector.tsml_field(feat, foot)
    d_vis_full = distance_transform_edt(~labels)
    mask_tsml = detector.emit_from_field(
        tsml, foot, labels, d_vis_full, min_dist=3.2, n_max=38000, support_q=0.014, b_px=2.0
    )
    print(f"TSML dots {int(mask_tsml.sum())} on-cat {int((mask_tsml & labels).sum())}")
    # canary on TSML score
    tsml_can = canary.canary_aucs({"tsml_score": tsml["score"]}, ctx)
    print("TSML score holdout AUC", tsml_can["auc"])
    hr_tsml = holdout.evaluate_mask(mask_tsml, ctx, b_visible_px=2.0, name="TSML")
    hr_champ = holdout.evaluate_mask(champ, ctx, b_visible_px=2.0, name="champion_h33_2_b2")
    # random control at matched mass
    rng = np.random.default_rng(20261026)
    cand = foot & ~labels & (d_vis_full > 2.0)
    ys, xs = np.nonzero(cand)
    n_rand = int(mask_tsml.sum())
    pick = rng.choice(ys.size, size=min(n_rand, ys.size), replace=False)
    rand = np.zeros_like(foot)
    rand[ys[pick], xs[pick]] = True
    hr_rand = holdout.evaluate_mask(rand, ctx, b_visible_px=2.0, name="random_matched")
    delta = holdout.paired_delta(hr_tsml, hr_champ, "TSML-minus-champion")
    e2 = {
        "hypothesis": "TSML",
        "dots": int(mask_tsml.sum()),
        "on_catalogue": int((mask_tsml & labels).sum()),
        "canary": tsml_can,
        "holdout_tsml": hr_tsml,
        "holdout_champion": hr_champ,
        "holdout_random": hr_rand,
        "delta_vs_champion": delta,
        "beats_champion_point": hr_tsml["pooled_dti"] > hr_champ["pooled_dti"],
    }
    dump("e2_tsml.json", e2)
    print(
        f"HOLDOUT-DTI TSML {hr_tsml['pooled_dti']:.4f} {hr_tsml['ci95']} "
        f"n={hr_tsml['n_withheld_positives']}"
    )
    print(
        f"HOLDOUT-DTI champion {hr_champ['pooled_dti']:.4f} {hr_champ['ci95']} "
        f"n={hr_champ['n_withheld_positives']}"
    )
    print(f"HOLDOUT-DTI random {hr_rand['pooled_dti']:.4f}")

    # uniqueness of TSML (surface = score, dots = mask)
    uniq_tsml = uniqueness.audit(mask_tsml, tsml["score"], foot, registry_paths())
    dump("e2_uniqueness.json", uniq_tsml)
    print(
        "TSML unique",
        uniq_tsml["unique"],
        "max|rho|",
        uniq_tsml["max_abs_spearman"],
        "max overlap",
        uniq_tsml["max_overlap_non_spacefill"],
        "drifted",
        uniq_tsml["drifted_reason"],
    )
    if uniq_tsml["drifted"]:
        dump(
            "duplicate_stop.json",
            {"verdict": "duplicate", "reason": uniq_tsml["drifted_reason"]},
        )
        print("LANE DRIFT — logging duplicate and stopping per protocol.")
        # still write a run card
        _write_runcard(
            UTC,
            "TSML",
            mask_tsml,
            tsml["score"],
            hr_tsml,
            hr_champ,
            uniq_tsml,
            None,
            "negative",
            foot,
            labels,
            "duplicate/lane-drift; not a submission",
        )
        return 0

    # ------------------------------------------------------------------ E3 MVGZ (only if TSML did not beat champion; still unique)
    print("\n--- E3 MVGZ ---")
    mvgz = detector.mvgz_field(feat, foot)
    mask_mvgz = detector.emit_from_field(
        mvgz, foot, labels, d_vis_full, min_dist=3.0, n_max=38000, support_q=0.020, b_px=2.0
    )
    print(f"MVGZ dots {int(mask_mvgz.sum())} on-cat {int((mask_mvgz & labels).sum())}")
    mvgz_can = canary.canary_aucs({"mvgz_score": mvgz["score"]}, ctx)
    hr_mvgz = holdout.evaluate_mask(mask_mvgz, ctx, b_visible_px=2.0, name="MVGZ")
    uniq_mvgz = uniqueness.audit(mask_mvgz, mvgz["score"], foot, registry_paths())
    e3 = {
        "hypothesis": "MVGZ",
        "dots": int(mask_mvgz.sum()),
        "on_catalogue": int((mask_mvgz & labels).sum()),
        "canary": mvgz_can,
        "holdout_mvgz": hr_mvgz,
        "delta_vs_champion": holdout.paired_delta(hr_mvgz, hr_champ, "MVGZ-minus-champion"),
        "uniqueness": {
            "unique": uniq_mvgz["unique"],
            "max_abs_spearman": uniq_mvgz["max_abs_spearman"],
            "max_overlap_non_spacefill": uniq_mvgz["max_overlap_non_spacefill"],
            "drifted_reason": uniq_mvgz["drifted_reason"],
            "top": uniq_mvgz["top"],
        },
        "beats_champion_point": hr_mvgz["pooled_dti"] > hr_champ["pooled_dti"],
    }
    dump("e3_mvgz.json", e3)
    print(
        f"HOLDOUT-DTI MVGZ {hr_mvgz['pooled_dti']:.4f} {hr_mvgz['ci95']} unique={uniq_mvgz['unique']}"
    )

    # pick the unique arm with higher holdout DTI
    cand_name, cand_mask, cand_score, cand_hr, cand_uniq, cand_can = (
        "TSML",
        mask_tsml,
        tsml["score"],
        hr_tsml,
        uniq_tsml,
        tsml_can,
    )
    if uniq_mvgz["unique"] and (not uniq_tsml["unique"] or hr_mvgz["pooled_dti"] > hr_tsml["pooled_dti"]):
        cand_name, cand_mask, cand_score, cand_hr, cand_uniq, cand_can = (
            "MVGZ",
            mask_mvgz,
            mvgz["score"],
            hr_mvgz,
            uniq_mvgz,
            mvgz_can,
        )

    beats = cand_hr["pooled_dti"] > hr_champ["pooled_dti"]
    canary_ok = not cand_can.get("leaking_auc_gt_0.90")
    # promote only if unique AND holdout point-win AND canary clean
    verdict = "promote" if (cand_uniq["unique"] and beats and canary_ok) else "negative"
    note = (
        f"{cand_name} unique holdout-win vs champion proxy"
        if verdict == "promote"
        else f"{cand_name} unique but HOLDOUT-DTI {cand_hr['pooled_dti']:.4f} vs champ {hr_champ['pooled_dti']:.4f}; DO NOT SUBMIT"
    )
    tif_path = _write_runcard(
        UTC,
        cand_name,
        cand_mask,
        cand_score,
        cand_hr,
        hr_champ,
        cand_uniq,
        cand_can,
        verdict,
        foot,
        labels,
        note,
    )
    print("PRIMARY TIF", tif_path, "verdict", verdict)
    return 0


def _write_runcard(
    utc,
    name,
    mask,
    score,
    hr,
    hr_champ,
    uniq,
    can,
    verdict,
    foot,
    labels,
    note,
):
    from gems1.grid import write_geotiff

    content = np.array(np.nonzero(mask)).tobytes()
    import hashlib

    cid = hashlib.sha256(content).hexdigest()[:8]
    stem = f"wbggemsdoe1-h1-{name.lower()}-{utc}-{cid}-zeros"
    tif = DOWN / f"{stem}.tif"
    write_geotiff(mask.astype(np.float32), tif, footprint=foot, outside="zeros")
    rec = validate.validate_submission(tif, footprint=foot, labels=labels, require_all_finite=True)
    dump(f"validator_{stem}.json", rec)

    # zip
    import zipfile

    zpath = DOWN / f"{stem}.zip"
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, arcname=tif.name)

    sub_name = f"WBGGEMSDOE1-H1-{name}-{cid.upper()}"
    sub_note = note[:140]
    runcard = {
        "hypothesis": (
            "Transtensional strain-gated magnetic-contact lineaments (TSML)"
            if name == "TSML"
            else "Magnetic vertical-gradient zero-crossing contacts (MVGZ)"
        ),
        "mechanism": (
            "Hessian ridges of TMI horizontal-gradient magnitude, corroborated by "
            "isostatic-gravity slope and basement-depth gradient, gated to extensional "
            "high 2nd-invariant corridors (dilatation>0)."
            if name == "TSML"
            else "Zero crossings of TMI vertical gradient weighted by TMI horizontal gradient "
            "(Blakely contact mapping), off-catalogue B=2."
        ),
        "named_non_fault_process_that_could_mimic_it": (
            "Lithologic magnetic contacts (dikes, volcanic flow edges, pluton margins) and "
            "Basin-Range flexure without discrete fault displacement."
            if name == "TSML"
            else "Magnetic lithologic contacts and cultural EM noise along linear infrastructure."
        ),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": hr["evaluator_version"],
            "pooled_dti": hr["pooled_dti"],
            "ci95": hr["ci95"],
            "n_withheld_positives": hr["n_withheld_positives"],
        },
        "holdout_dti_champion_proxy": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": hr_champ["evaluator_version"],
            "pooled_dti": hr_champ["pooled_dti"],
            "ci95": hr_champ["ci95"],
            "n_withheld_positives": hr_champ["n_withheld_positives"],
            "file": "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
            "live_score_label": "OWNER-REPORT 0.2778 (no organizer receipt in this repo)",
        },
        "correlation_overlap_vs_registry": {
            "n_registry": uniq["n_registry"],
            "max_abs_spearman": uniq["max_abs_spearman"],
            "max_overlap_non_spacefill": uniq["max_overlap_non_spacefill"],
            "max_overlap_literal": uniq["max_overlap_literal"],
            "unique": uniq["unique"],
            "drifted_reason": uniq["drifted_reason"],
            "top": uniq["top"],
        },
        "raster_sha256": rec["sha256"],
        "validator": rec,
        "submission_name": sub_name,
        "submission_note": sub_note,
        "verdict": verdict,
        "dots": int(mask.sum()),
        "tif": str(tif.relative_to(ROOT)),
        "zip": str(zpath.relative_to(ROOT)),
        "canary": can,
        "utc": utc,
    }
    dump("run_card.json", runcard)
    dump(f"run_card_{stem}.json", runcard)
    print("RUN CARD verdict", verdict, "sha", rec["sha256"][:16], "dots", int(mask.sum()))
    return tif


if __name__ == "__main__":
    raise SystemExit(main())
