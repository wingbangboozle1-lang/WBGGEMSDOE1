#!/usr/bin/env python3
"""Shared exact-file format check, distinct from scientific submission approval.

Default exits nonzero for the stopped lane. --format-only can pass without
claiming holdout efficacy, lane uniqueness or slot authorization.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_submission import check_tiff

CARD = ROOT / 'evidence/wbg2/run_card.json'


def review():
    card = json.loads(CARD.read_text())
    tif = ROOT / card['artifacts']['tif']
    archive = ROOT / card['artifacts']['zip']
    digest = hashlib.sha256(tif.read_bytes()).hexdigest()
    validation = check_tiff(tif)
    validation['file'] = str(tif.relative_to(ROOT))
    if 'template_report' in validation:
        validation['template_report']['path'] = str(tif.relative_to(ROOT))
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        zip_ok = names == [tif.name] and z.read(names[0]) == tif.read_bytes()
    format_ok = validation['all_checks_passed'] and zip_ok and digest == card['raster_sha256']
    # Binding duplicate STOP is not overridable by a mutable approval flag.
    return {'schema': 'wbg2-corrected-preflight-v1', 'raster_sha256': digest,
            'validator': validation, 'zip_identical_single_member': zip_ok,
            'format_ok': bool(format_ok), 'ok_to_submit': False,
            'holdout_dti': card['holdout'], 'score_estimate': None,
            'recorded_max_forward_overlap': card['registry']['max_forward_3px_overlap'],
            'surface_gate_measured': False, 'verdict': 'negative',
            'reason': card['decision']['reason']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--format-only', action='store_true')
    p.add_argument('--write-report', action='store_true')
    args = p.parse_args()
    try:
        report = review()
    except Exception as exc:
        print(json.dumps({'format_ok': False, 'ok_to_submit': False, 'error': str(exc)}))
        return 2
    text = json.dumps(report, indent=2) + '\n'
    if args.write_report:
        (ROOT / 'evidence/wbg2/corrected_preflight.json').write_text(text)
    print(text)
    return 0 if args.format_only and report['format_ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
