#!/usr/bin/env python3
"""Reopen all four frozen research releases; never train, tune or approve a slot.

Historical holdout/novelty measurements are attributed to their source cards.
Only artifact integrity/format/ZIP checks are recomputed by this review.
"""
from __future__ import annotations

import hashlib
from html import escape
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.validate import validate  # noqa: E402

REVIEW_DATE = "2026-10-27"


def load(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def specifications():
    c = load("registry/run_card.json")
    t = load("evidence/tip1_run_card_20261026.json")
    mpath = "evidence/run_card_wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros.json"
    m = load(mpath)
    d = load("evidence/wbg_h1/run_card.json")
    th = t["arms"]["B"]["holdout"]
    return [
        dict(id="WBG-C1", source="registry/run_card.json", artifact=c["artifact"],
             expected_sha256=c["raster_sha256"], name=c["submission_name"], note=c["submission_note"],
             hypothesis=c["hypothesis"], mechanism=c["mechanism"], mimic=c["non_fault_mimic"],
             holdout=c["holdout"], registry=c["registry"],
             blocker="Surface duplicate STOP; paired efficacy CI includes zero. No final dots generated."),
        dict(id="TIP1", source="evidence/tip1_run_card_20261026.json",
             artifact="docs/downloads/" + t["submission_name"], expected_sha256=t["raster_sha256"],
             name=t["submission_name"], note=t["submission_note"], hypothesis=t["hypothesis"],
             mechanism=t["mechanism"], mimic=t["named_non_fault_mimic"],
             holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=th["evaluator_version"],
                          dti=th["dti"], ci95=th["ci95"]["interval"], withheld_positive_pixels=th["n_withheld_positive_pixels"]),
             registry=t["correlation_overlap_vs_registry"]["final_dots"],
             blocker="Final-dot literal overlap exceeds 70%; independent paired current-best replay unavailable."),
        dict(id="MVGZ", source=mpath, artifact=m["tif"], expected_sha256=m["raster_sha256"],
             name=m["submission_name"], note=m["submission_note"], hypothesis=m["hypothesis"],
             mechanism=m["mechanism"], mimic=m["named_non_fault_process_that_could_mimic_it"],
             holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=m["holdout_dti"]["evaluator_version"],
                          dti=m["holdout_dti"]["pooled_dti"], ci95=m["holdout_dti"]["ci95"],
                          withheld_positive_pixels=m["holdout_dti"]["n_withheld_positives"]),
             registry=m["correlation_overlap_vs_registry"],
             blocker="Negative efficacy; only 37 registry rasters checked in frozen card, not complete current portfolio."),
        dict(id="WBG-H1 / DPGF-1", source="evidence/wbg_h1/run_card.json",
             artifact=d["raster_sha256"]["tif_file"], expected_sha256=d["raster_sha256"]["tif_sha256"],
             name=d["submission_name"], note=d["submission_note"], hypothesis=d["hypothesis"],
             mechanism=d["mechanism"], mimic=d["mimic"],
             holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=d["holdout_dti"]["evaluator_version"],
                          dti=d["holdout_dti"]["dti"], ci95=d["holdout_dti"]["ci95"],
                          withheld_positive_pixels=d["holdout_dti"]["n_withheld_positives"]),
             registry=d["registry_correlation_and_overlap"],
             blocker="Literal lattice overlap 99.8035% and slab overlap 88.32% exceed 70%; sparse/symmetric exemptions unauthorized. No current-best promotion."),
    ]


def validate_artifact(spec, template):
    """Call the pinned shared validator, then verify identity and ZIP bytes."""
    path = ROOT / spec["artifact"]
    report = validate(path)
    with rasterio.open(template) as ref, rasterio.open(path) as ds:
        a = ds.read(1)
        checks = dict(sha256_matches_card=sha(path) == spec["expected_sha256"],
                      shared_validator_passed=report["all_checks_passed"],
                      crs_shape_transform_match=(ds.crs, ds.shape, ds.transform) == (ref.crs, ref.shape, ref.transform),
                      all_finite=bool(np.isfinite(a).all()),
                      whole_array_in_0_1=bool(((a >= 0) & (a <= 1)).all()),
                      note_at_most_140_chars=0 < len(spec["note"]) <= 140)
        decoded_sha = hashlib.sha256(a.astype("<f4").tobytes()).hexdigest()
    zpath = path.with_suffix(".zip")
    zip_report = {"present": zpath.exists(), "exact_single_tiff": None}
    if zpath.exists():
        with zipfile.ZipFile(zpath) as archive:
            members = archive.infolist()
            exact = len(members) == 1 and members[0].filename == path.name and archive.read(members[0]) == path.read_bytes()
        checks["zip_exact_single_tiff"] = exact
        zip_report = dict(present=True, exact_single_tiff=exact, sha256=sha(zpath))
    return dict(checks=checks, passed=all(checks.values()), sha256=sha(path),
                decoded_sha256=decoded_sha, zip=zip_report, shared_validator=report)


def build_review():
    rows = []
    manifest = load("registry/data_manifest.json")
    sample_pin = next(r["sha256"] for r in manifest["files"] if r["dest"] == "sample_submission.tif")
    if sha(ROOT / "data/bridge/sample_submission.tif") != sample_pin:
        raise ValueError("Pinned reference template hash mismatch")
    for spec in specifications():
        row = {**spec, "source_card_sha256": sha(ROOT / spec["source"]),
               "validation": validate_artifact(spec, ROOT / "data/bridge/sample_submission.tif"),
               "verdict": "negative", "ok_to_submit": False,
               "leaderboard_estimate": None, "organizer_confirmed_score": None,
               "measurement_status": "Frozen HOLDOUT-DTI and registry evidence, not rerun or revalidated scientifically in this review"}
        rows.append(row)
    pixel_ids = [r["validation"]["decoded_sha256"] for r in rows]
    for row in rows:
        row["decoded_distinct_among_four_releases"] = pixel_ids.count(row["validation"]["decoded_sha256"]) == 1
    return dict(schema="wbg-portfolio-review-v1", review_date_utc=REVIEW_DATE,
                scope="Four local frozen releases; no fresh full-registry clearance, no new geological experiment",
                experiments_started=0, submission_slots_used=0,
                format_integrity_passed=all(r["validation"]["passed"] for r in rows),
                verdict="negative", ok_to_submit=False, rows=rows,
                corrections=[
                    "Inherited WBG-H1 projections used owner/user-reported values, not submission-page receipts. No ORGANIZER-CONFIRMED project score or calibrated forecast is established.",
                    "A mean lattice-kernel assumption cannot identify hidden fault count or weighted recall from one rounded reported score. Private-count inversion is not verified evidence.",
                    "Sparse-only or symmetric overlap does not satisfy the literal one-way all-registry threshold; no density exemption is authorized.",
                    "Mirrored data integrity is not independent organizer provenance. Core data and all nineteen shared cache bands were restored and hash-checked in this follow-up; that still does not authorize resuming a stopped lane.",
                    "The official leaderboard cannot be refreshed on this sandbox's outbound allowlist. Retain the dated observation; do not label it current.",
                ])


def render(review):
    rows = []
    for r in review["rows"]:
        h = r["holdout"]
        href = r["artifact"].removeprefix("docs/")
        rows.append(f'''<tr><td>{escape(r['id'])}</td><td><a href="{escape(href)}" download>{escape(Path(href).name)}</a></td>
<td>HOLDOUT-DTI {h['dti']:.6f}<br>95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]<br>{escape(h['evaluator_version'])}<br>{h['withheld_positive_pixels']:,} withheld positives; frozen</td>
<td>{'PASS' if r['validation']['passed'] else 'FAIL'} local format/integrity</td><td>{escape(r['blocker'])}<br><strong>DO NOT SUBMIT</strong></td><td>Unavailable</td></tr>''')
    issues = "".join(f"<li>{escape(c)}</li>" for c in review["corrections"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>All-release review · WBG GEMS</title><link rel="stylesheet" href="assets/style.css"></head>
<body><header class="wrap"><nav><a href="index.html">Research desk</a> · <a href="executive-summary.html">Nine-site summary</a> · <a href="how-to-submit.html">Submission guide</a></nav></header>
<main class="wrap" id="main"><h1>All-release review — {REVIEW_DATE}</h1><p class="alert"><strong>DOWNLOAD: YES (research only). SUBMIT: NO. No eligible submission.</strong></p>
<p>All four local TIFFs are research downloads, not recommended uploads. Different evaluators, splits and prediction representations cannot be ranked as one leaderboard. Estimated leaderboard results and organizer-confirmed file scores are unavailable.</p>
<div class="table-wrap"><table><thead><tr><th>Method</th><th>Exact research file</th><th>Recorded local evidence</th><th>Reopened bytes</th><th>Uniqueness / promotion blocker</th><th>Leaderboard estimate</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Trust corrections</h2><ul>{issues}</ul><p>The original cards remain unchanged as historical records. This review overrides unsupported interpretations, not their frozen measurements. No training, tuning, final-dot placement, new raster, or submission slot was used.</p>
<p>The highest supplied historical nine-site claim remains GEMSDOE32 B2 at USER-REPORTED 0.2778, not an organizer receipt. Pruning catalogue-near redundant dots is a plausible metric explanation, not proof of hidden-label locations.</p>
<h2>Next steps in order</h2><ol><li>Resolve the missing lane assignment and literal registry saturation conflict centrally. Do not exempt dense priors privately or move dots around registry holes.</li><li>Restore the pinned feature cache, verify band semantics/provenance, and lock an untouched same-instrument current-best comparator.</li><li>Preregister an authorized method, run each feature canary and buffered segment holdout, then both literal novelty gates and exact saved-file validation.</li><li>Only a separate selector may approve a weekly slot after all gates pass; current account allowance and receipts remain unavailable.</li></ol>
<p><a href="data/portfolio-review.json">Full machine-readable review, hashes, validators and registry measurements</a> · <a href="data/followup-run-card.json">Follow-up run card</a> · <a href="standing-prompt.md">Standing brief</a></p></main></body></html>'''


def main():
    review = build_review()
    text = json.dumps(review, indent=2, allow_nan=False) + "\n"
    for path in (ROOT / "evidence/portfolio_review_20261027.json", ROOT / "docs/data/portfolio-review.json"):
        path.write_text(text)
    (ROOT / "docs/portfolio-review.html").write_text(render(review))
    print(json.dumps({k: review[k] for k in ("format_integrity_passed", "experiments_started", "submission_slots_used", "ok_to_submit")}))
    return 0 if review["format_integrity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
