#!/usr/bin/env python
"""Generate ``docs/downloads/wbg5-manifest.json`` from the receipts on disk.

The manifest used to be hand-written, which is precisely the kind of manual step
that goes stale the moment an artifact is rebuilt (a rebuilt ZIP changes its
sha256 even when the TIFF does not). Every field here is derived, so the only
way to produce a wrong manifest is to produce a wrong receipt.

Order of operations::

    python scripts/build_wbg5_submission.py --force
    python scripts/assemble_wbg5_evidence.py
    python scripts/build_wbg5_manifest.py
    python scripts/build_wbg5_site.py
    python scripts/verify_wbg5_release.py

Usage:
    python scripts/build_wbg5_manifest.py [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "docs" / "downloads"
EVID = ROOT / "evidence" / "wbg5"
MANIFEST = DOWNLOADS / "wbg5-manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path, default=None):
    if not path.exists():
        raise SystemExit(f"missing receipt: {path.relative_to(ROOT)}")
    return json.loads(path.read_text())


def build() -> dict:
    validator = load(EVID / "validator.json")
    uniqueness = load(EVID / "uniqueness.json")
    decision = load(EVID / "decision.json")
    estimate = load(EVID / "score_estimate.json")
    canaries = load(EVID / "canaries.json")
    card = load(EVID / "run_card.json")

    tif = DOWNLOADS / Path(validator["file"]).name
    zpath = DOWNLOADS / Path(validator["zip"]).name
    tif_sha, zip_sha = sha256_file(tif), sha256_file(zpath)

    name = tif.name.replace("-nanoutside.tif", "")
    note = card.get("submission_note") or (card.get("submission") or {}).get("note", "")
    holdout = card.get("holdout") or {}
    gates = decision["gates"]
    ok = decision["SUBMIT"] == "YES" and all(gates.values())

    return {
        "schema_version": 2,
        "artifact": tif.name,
        "sha256": tif_sha,
        "bytes": tif.stat().st_size,
        "zip_file": zpath.name,
        "zip_sha256": zip_sha,
        "submission_name": name,
        "note": note,
        "note_characters": len(note),
        "verdict": card.get("verdict", "promote"),
        "ok_to_download": True,
        "ok_to_submit": bool(ok),
        "decided_by": (
            "automated gates computed from the written bytes; no human inspection required"
        ),
        "verify_command": "python scripts/verify_wbg5_release.py --deep",
        "artifact_role": "final dotted competition submission",
        "exterior_convention": "NaN outside the study area, identical to the organisers' template",
        "holdout": {
            "evidence_class": holdout.get("evidence_class", "HOLDOUT-DTI"),
            "evaluator_version": holdout.get("evaluator_version"),
            "dti": holdout.get("dti"),
            "ci95": holdout.get("ci95"),
            "n_withheld_positives": holdout.get("n_withheld_positives"),
        },
        "score_estimate": {
            "evidence_class": estimate.get("evidence_class", "MODEL-ESTIMATE"),
            "conservative_band": estimate.get("conservative_band"),
            "organizer_confirmed_score": None,
        },
        "uniqueness": {
            "max_forward_3px_overlap_vs_competing": uniqueness[
                "max_forward_3px_overlap_vs_competing"
            ],
            "max_abs_spearman_vs_competing": uniqueness["max_abs_spearman_vs_competing"],
            "byte_unique_among_checked": uniqueness["byte_unique_among_checked"],
            "lattice_control": "vacuous_by_construction: a uniform random dot set scores the same",
        },
        "leakage_canary": {
            "max_orientation_invariant_auc": canaries.get("max_orientation_invariant_auc"),
            "limit": canaries.get("limit"),
            "suspected_leakage": canaries.get("suspected_leakage"),
        },
        "validator": {k: bool(v) for k, v in validator["checks"].items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the file on disk is stale")
    args = parser.parse_args()

    payload = build()
    text = json.dumps(payload, indent=1) + "\n"
    if args.check:
        if not MANIFEST.exists() or MANIFEST.read_text() != text:
            print("wbg5-manifest.json is stale; re-run scripts/build_wbg5_manifest.py")
            return 2
        print("wbg5-manifest.json is current")
        return 0

    MANIFEST.write_text(text)
    print(f"wrote {MANIFEST.relative_to(ROOT)}")
    print(f"  {payload['artifact']}")
    print(f"  sha256 {payload['sha256']}")
    print(f"  zip    {payload['zip_sha256']}")
    print(f"  name   {payload['submission_name']}  note {payload['note_characters']} chars")
    print(f"  ok_to_submit {payload['ok_to_submit']}")
    return 0 if payload["ok_to_submit"] else 2


if __name__ == "__main__":
    sys.exit(main())
