#!/usr/bin/env python3
"""Finalize the WBG-5 submission: blend75 emission, validate, uniqueness, run card."""
from __future__ import annotations
import hashlib, json, sys, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path("/home/user/WBGGEMSDOE1")
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "vendor"))
from gems57.emit import greedy_allocate
from gems57.uniqueness import dot_overlap
from gems import submission

WORK = Path("/tmp/wbg5")
LABELS = ROOT / "data/bridge/labels.tif"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"
W_DCOC = 0.75
K_TRUTH = 12366.0


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def norm01(a, foot):
    a = np.where(foot, a, 0.0)
    mx = np.nanmax(a[foot]) if foot.any() else 1.0
    return (a / mx).astype(np.float32) if mx > 0 else a.astype(np.float32)


t0 = time.time()
with rasterio.open(LABELS) as s:
    lab = s.read(1)
foot = lab != -1
cat = lab == 1
allowed = foot & ~cat

surf = np.load(WORK / "surface_wbg5.npy")
feats = np.lib.format.open_memmap(WORK / "wbg5_features.npy", mode="r", dtype="float32",
                                  shape=(46, lab.shape[0], lab.shape[1]))
dcoc = np.asarray(feats[41]).copy()
surf_n = norm01(surf, foot)
dcoc_n = norm01(dcoc, foot)
emit_surf = ((1 - W_DCOC) * surf_n + W_DCOC * dcoc_n).astype(np.float32)

a = greedy_allocate(emit_surf, allowed, K_TRUTH, floor=0.02, max_dots=60000)
dots = a.emitted.astype(np.float32)
print(f"greedy dots {int(dots.sum())} surrogate DTI {a.surrogate_dti:.4f} ({time.time()-t0:.0f}s)", flush=True)

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
name = f"wbggemsdoe1-wbg5-dcoc-blend75-submod-{stamp}-zeros"
note = "WBG-5 DCOC dip-offset cross-gradient coherence blend75 submodular zeros no NaN"
assert len(note) <= 140, len(note)
out_dir = ROOT / "docs/downloads"
tif = out_dir / f"{name}.tif"
with rasterio.open(SAMPLE) as s:
    meta = s.profile.copy()
meta.update(count=1, dtype="float32", nodata=None, compress="deflate", tiled=False)
with rasterio.open(tif, "w", **meta) as dst:
    dst.write(dots.astype(np.float32), 1)
zp = out_dir / f"{name}.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(tif, arcname=tif.name)
print(f"wrote {name} sha256 {sha256(tif)} dots {int(dots.sum())}", flush=True)

receipt = submission.check_variants(str(tif), str(SAMPLE))
validator = {"format_valid": bool(receipt.get("format_valid")),
             "portal_safe_local_policy": bool(receipt.get("format_valid") and
                 receipt["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]),
             "checks": receipt.get("checks", {})}
(out_dir / f"{name}.validator.json").write_text(json.dumps(validator, indent=1))

# uniqueness: nine peer champions + this repo's prior lanes + local audit raster
comps = []
for s in ("24", "25", "27", "28", "30", "31", "32", "33", "36"):
    p = Path(f"/tmp/reg9/GEMSDOE{s}.tif")
    if p.exists():
        comps.append((f"GEMSDOE{s}", p))
for lp in [ROOT / "docs/downloads/wbggemsdoe1-wbg3-exp3det-clear2-37654-20261027T200705Z-zeros.tif",
           ROOT / "docs/downloads/wbggemsdoe1-wbg4-csjf1-edti-35135-20261027-b3dacd59-zeros.tif",
           ROOT / "docs/downloads/wbggemsdoe1-wbg3-spipmr-wcs-36800-20261027-1458d60c-zeros.tif",
           ROOT / "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif",
           ROOT / "docs/downloads/wbggemsdoe1-wbg-s2-exp3-mksf-vierbeincoulomb-20261027-e9b4a3c09065-zeros.tif",
           ROOT / "docs/downloads/wbggemsdoe1-wbg-h1-dpgf1-exp-3-20261026-0749b3c8195f-zeros.tif",
           ROOT / "docs/audit/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"]:
    if lp.exists():
        comps.append((lp.stem[:34], lp))
rng = np.random.default_rng(0)
idx = rng.choice(dots.size, 400_000, replace=False)
mine = dots.ravel()
rows = []
for label, p in comps:
    with rasterio.open(p) as ds:
        theirs = np.nan_to_num(ds.read(1), nan=0.0)
    ov = dot_overlap(dots, theirs)
    rho = float(spearmanr(mine[idx], theirs.ravel()[idx]).statistic) if np.ptp(theirs) else float("nan")
    rows.append({"submission": label, "forward_3px_overlap": ov, "spearman_subsample": rho,
                 "their_dots": int((theirs > 0).sum())})
peer_rows = [r for r in rows if r["submission"].startswith("GEMSDOE")]
peer_max = max(r["forward_3px_overlap"] for r in peer_rows)
all_max = max(r["forward_3px_overlap"] for r in rows)
rho_max = max(abs(r["spearman_subsample"]) for r in rows if np.isfinite(r["spearman_subsample"]))
reg = {"gate": "gems57 literal per-raster (Euclidean 3px); rho<=0.90; overlap<=0.70",
       "n_comparators": len(rows), "rows": rows,
       "peer_champion_max_overlap": peer_max,
       "all_comparator_max_overlap": all_max,
       "max_abs_spearman": rho_max,
       "unique_vs_peer_champions": bool(peer_max <= 0.70 and rho_max <= 0.90),
       "unique_vs_all_checked": bool(all_max <= 0.70 and rho_max <= 0.90)}
(out_dir / f"{name}.uniqueness.json").write_text(json.dumps(reg, indent=1))

card = {"schema": "wbg5-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lane_id": "WBG-5", "method_code": "DCOC-BLEND75",
        "hypothesis": "Dip-offset cross-gradient coherence: blind normal-fault traces are where the conductivity-surface gradient is co-linear with the potential-field gradient at the dip-projected offset.",
        "mechanism": "Max over (dy,dx) in [-4..4]^2 of the gradient dot product between cond_surf and (rtp+iso_grav_anom_hg), plus multi-scale conductivity-edge persistence; supervised HGB on 46 channels; emission surface = 0.25*HGB + 0.75*DCOC; shared submodular greedy_allocate.",
        "named_non_fault_mimic": "Buried Tertiary dike swarms, lithologic contacts, survey seams, ephemeral fluvial incision (scale-persistence de-contends the last).",
        "submission_name": name, "submission_note": note,
        "raster_sha256": sha256(tif), "zip_sha256": sha256(zp),
        "dots": int(dots.sum()),
        "validator": validator, "registry": reg,
        "k_truth_estimate": K_TRUTH, "k_truth_label": "INFERRED private-truth size; not a measured fact",
        "wbg4_benchmark_holdout_dti": 0.165424,
        "elapsed_s": time.time() - t0}
ev = ROOT / "evidence/wbg5"; ev.mkdir(parents=True, exist_ok=True)
(ev / "run_card.json").write_text(json.dumps(card, indent=1, default=float))
print(json.dumps({"name": name, "sha256": card["raster_sha256"], "dots": int(dots.sum()),
                  "validator_pass": validator["portal_safe_local_policy"],
                  "peer_max": peer_max, "all_max": all_max, "rho_max": rho_max,
                  "unique_peer": reg["unique_vs_peer_champions"],
                  "unique_all": reg["unique_vs_all_checked"]}, indent=1))
