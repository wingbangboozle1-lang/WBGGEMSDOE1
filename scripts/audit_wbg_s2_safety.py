#!/usr/bin/env python3
"""Recheck the parallel WBG-S2 artifact against two pinned literal witnesses.

Forensic remeasurement only: no fitting, placement, altered TIFF, new lane,
selector or upload. A failing witness proves STOP, not a complete registry
scan. The original pre-placement report checked a sampled correlation screen,
not the required literal overlap against every registry raster.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor'), str(ROOT / 'scripts')]
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from gems57 import uniqueness  # noqa: E402
from audit_wbg2_safety import (  # noqa: E402
    CACHE, WITNESS_PATH, WITNESS_REF, WITNESS_SHA, fetch,
)
from validate_submission import check_tiff  # noqa: E402
from verify_wbg2_download import compare_audit  # noqa: E402

TIF = ROOT / 'docs/downloads/wbggemsdoe1-wbg-s2-exp3-mksf-vierbeincoulomb-20261027-e9b4a3c09065-zeros.tif'
ZIP = TIF.with_suffix('.zip')
EXPECTED = '6992387620fcb2d7f3a06d867b79b6ad770d7006b87d35b131e27a5035c62880'
C1 = ROOT / 'docs/downloads/wbg-c1-commutator-research-surface-20261026-acea88448272.tif'
C1_SHA = '8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875'
OUT = ROOT / 'evidence/wbg_s2/safety_review_20261027.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit(do_fetch=False):
    lattice = CACHE / 'r13-lattice-s5.tif'
    if do_fetch:
        fetch('buffedlizard55-lab/GEMSDOE24', WITNESS_REF, WITNESS_PATH, WITNESS_SHA, lattice)
    if digest(TIF) != EXPECTED or digest(lattice) != WITNESS_SHA or digest(C1) != C1_SHA:
        raise ValueError('candidate or witness SHA-256 changed')
    report = check_tiff(TIF)
    with zipfile.ZipFile(ZIP) as archive:
        names = archive.namelist()
        zip_ok = names == [TIF.name] and hashlib.sha256(archive.read(names[0])).hexdigest() == EXPECTED
    with rasterio.open(ROOT / 'data/bridge/sample_submission.tif') as sample:
        footprint = np.isfinite(sample.read(1))
        grid = (sample.shape, sample.crs, sample.transform)
    references = [
        {'file': str(lattice), 'repo': 'GEMSDOE24', 'submission': 'pinned r13 spacing-5 lattice', 'sha256': WITNESS_SHA},
        {'file': str(C1), 'repo': 'WBGGEMSDOE1', 'submission': 'C1 continuous research surface', 'sha256': C1_SHA},
    ]
    compared = uniqueness.compare_to_registry(TIF, references, footprint, expected_grid=grid, include_reverse=False)
    wanted = ('repo', 'submission', 'sha256', 'their_dots', 'my_dots_within_3px_of_theirs',
              'spearman_full_footprint', 'duplicate_by_overlap', 'duplicate_by_rho')
    rows = []
    for row in compared['rows']:
        if 'error' in row:
            raise ValueError(f"literal registry comparison failed: {row['error']}")
        rows.append({key: row[key] for key in wanted})
    if (not report['all_checks_passed'] or not zip_ok or len(rows) != 2
            or not all(row['duplicate_by_overlap'] for row in rows) or not compared['stop_required']):
        raise ValueError('the expected exact-file format or decisive STOP did not reproduce')
    return {
        'schema': 'wbg-s2-literal-safety-review-v1', 'review_date_utc': '2026-10-27',
        'evidence_class': 'REGISTRY-MEASUREMENT', 'existing_tiff_sha256': EXPECTED,
        'existing_positive_pixels': report['emitted_positive_pixels'],
        'local_format_passed': bool(report['all_checks_passed']),
        'zip_single_member_identical': zip_ok, 'witnesses': rows,
        'phase': 'Final dots from a parallel session; forensic remeasurement, not a new placement.',
        'pre_placement_limitation': 'The original record reports a sampled Spearman screen only, not the full literal overlap test against every registry raster. No qualifying pre-placement clearance is established.',
        'scope': 'Two hash-pinned references. Either STOP is decisive; this is not a complete registry scan or proof of copying.',
        'correction': 'The earlier report paired the r13 lattice overlap with the C1 peer name. Measured separately: 99.5538% against r13 and 100% against C1.',
        'holdout_limitation': 'The parallel-run HOLDOUT-DTI figures were not independently replayed here; arms were selected on the reported holdouts and no untouched confirmation is established.',
        'verdict': 'negative', 'ok_to_submit': False, 'eligible_for_separate_selector': False,
        'new_experiments_in_this_audit': 0, 'submission_slots_used_in_this_audit': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--record', action='store_true')
    mode.add_argument('--check', action='store_true')
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    result = audit(do_fetch=args.fetch)
    if args.record:
        OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    else:
        differences = compare_audit(result, json.loads(OUT.read_text()))
        if differences:
            raise ValueError('recorded safety review differs: ' + '; '.join(differences[:10]))
    print(json.dumps({'verdict': 'negative', 'ok_to_submit': False,
                      'lattice_overlap': result['witnesses'][0]['my_dots_within_3px_of_theirs'],
                      'c1_overlap': result['witnesses'][1]['my_dots_within_3px_of_theirs']}, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, rasterio.errors.RasterioError) as error:
        print(json.dumps({'ok_to_submit': False, 'error': str(error)}), file=sys.stderr)
        raise SystemExit(1)
