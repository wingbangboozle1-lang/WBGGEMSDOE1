#!/usr/bin/env python3
"""Reopen WBG-2 bytes and fail closed on the known negative decision.

Default exits 2 (NOT submit-ready). ``--expect-negative`` is for CI and exits 0
only when the negative decision and integrity evidence are internally consistent.
``--deep --fetch`` additionally recomputes the pinned shared-gate diagnostics.
No option uploads, trains, places dots, or approves a real slot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor'), str(ROOT / 'scripts')]
from audit_wbg2_safety import EXPECTED, OUT, TIF, ZIP, WITNESS_SHA, audit  # noqa: E402
from validate_submission import check_tiff  # noqa: E402


def compare_audit(actual, expected):
    """Exact structures/identity plus very small cross-platform float tolerance.

    Raster hashes, verdicts, counts, source URLs, booleans and all other values
    remain exact. Numeric tolerance only accommodates platform reduction noise;
    it is far smaller than a pixel fraction or any protocol threshold.
    """
    differences = []

    def walk(a, b, path):
        if isinstance(b, dict):
            if not isinstance(a, dict) or set(a) != set(b):
                differences.append(f"{path}: object keys or type changed")
                return
            for key in b:
                walk(a[key], b[key], f"{path}.{key}")
        elif isinstance(b, list):
            if not isinstance(a, list) or len(a) != len(b):
                differences.append(f"{path}: list length or type changed")
                return
            for index, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{path}[{index}]")
        elif isinstance(b, float):
            if (isinstance(a, bool) or not isinstance(a, (float, int))
                    or not math.isfinite(a) or not math.isfinite(b)
                    or not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14)):
                differences.append(f"{path}: {a!r} vs {b!r}")
        elif type(a) is not type(b) or a != b:
            differences.append(f"{path}: {a!r} vs {b!r}")

    walk(actual, expected, "audit")
    return differences


def verify(deep=False, fetch=False):
    card = json.loads((ROOT / 'evidence/wbg2/run_card.json').read_text())
    evidence = json.loads(OUT.read_text())
    report = check_tiff(TIF)
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        zip_ok = names == [TIF.name] and hashlib.sha256(z.read(names[0])).hexdigest() == EXPECTED
    witness = evidence['already_placed_final_dots_witness']
    surface = evidence['surface_witness']
    checks = {
        'exact_tiff_hash': report['sha256'] == EXPECTED == card['raster_sha256'],
        'shared_local_format': report['all_checks_passed'],
        'single_identical_tiff_in_zip': zip_ok,
        'reference_witness_hash': witness['sha256'] == surface['sha256'] == WITNESS_SHA,
        'final_overlap_stop': witness['duplicate_by_overlap'] and witness['my_dots_within_3px_of_theirs'] > .70,
        'surface_overlap_stop_retrospective': surface['duplicate_by_overlap'] and surface['my_dots_within_3px_of_theirs'] > .70,
        'card_negative_and_not_submit': card['verdict'] == 'negative' and card['decision']['ok_to_submit'] is False,
        'no_fabricated_score': card['score_estimate']['value'] is None and card['holdout']['pooled_dti'] is None,
        'note_within_140': 0 < len(card['submission_note']) <= 140,
        'no_slot_approval': card['decision']['approved_for_weekly_slot'] is False,
    }
    differences = []
    if deep:
        fresh = audit(do_fetch=fetch)
        differences = compare_audit(fresh, evidence)
        checks['deep_audit_matches_record_with_float_tolerance'] = not differences
    return {'checks': checks, 'negative_decision_integrity_passed': all(checks.values()),
            'local_format_passed': report['all_checks_passed'], 'ok_to_submit': False,
            'sha256': report['sha256'], 'verdict': 'negative',
            'deep_comparison': {'performed': deep, 'float_rtol': 1e-12, 'float_atol': 1e-14,
                                'difference_count': len(differences), 'first_differences': differences[:10]},
            'warning': 'DO NOT SUBMIT; diagnostic integrity is not submission approval.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--expect-negative', action='store_true')
    ap.add_argument('--deep', action='store_true')
    ap.add_argument('--fetch', action='store_true')
    args = ap.parse_args()
    result = verify(deep=args.deep, fetch=args.fetch)
    print(json.dumps(result, indent=2, allow_nan=False))
    if not result['negative_decision_integrity_passed']:
        return 1
    return 0 if args.expect_negative else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(json.dumps({'ok_to_submit': False, 'error': str(error)}), file=sys.stderr)
        raise SystemExit(1)
