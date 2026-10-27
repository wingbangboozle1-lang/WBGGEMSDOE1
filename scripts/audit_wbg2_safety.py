#!/usr/bin/env python3
"""Recheck the stopped WBG-2 file against pinned public references.

This is an audit of an already generated TIFF, NOT a model experiment.  The
first witness proves a stop; nine champion comparisons after that are only
inventory diagnostics, not permission to place or relocate dots.  Uses the
unchanged shared gems57 gate, including Euclidean 3-pixel support, with no
density exemption. Downloads are GitHub-pinned, hash verified, and ignored.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor'), str(ROOT / 'scripts')]
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402
from gems57 import uniqueness  # noqa: E402
from wbg2 import prior  # noqa: E402
from validate_submission import check_tiff  # noqa: E402

TIF = ROOT / 'docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif'
ZIP = TIF.with_suffix('.zip')
EXPECTED = 'f5b37051a26b3bc5d2d53dfd6fe1ca8c293cc62fb01a97aa8f36a959625430f3'
WITNESS_SHA = 'b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2'
WITNESS_REF = '7ab1c8f77f0b4b8644e3929403a0dab65838b008'
WITNESS_PATH = 'inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif'
CACHE = ROOT / '.cache/registry'
OUT = ROOT / 'evidence/wbg2/safety_audit_20261027.json'


def digest(p: Path) -> str:
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def fetch(repo: str, ref: str, remote: str, expected: str, target: Path) -> Path:
    if target.is_file() and digest(target) == expected:
        return target
    if (not repo.startswith('buffedlizard55-lab/GEMSDOE') or len(ref) != 40
            or any(c not in '0123456789abcdef' for c in ref)
            or remote.startswith('/') or '..' in Path(remote).parts):
        raise ValueError('invalid pinned registry source')
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.partial')
    try:
        with temporary.open('wb') as out:
            subprocess.run(['gh', 'api', f'repos/{repo}/contents/{remote}?ref={ref}',
                            '-H', 'Accept: application/vnd.github.raw+json'],
                           stdout=out, check=True, timeout=180)
        if digest(temporary) != expected:
            raise ValueError(f'pin mismatch for {repo}/{remote}')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def sources(do_fetch: bool):
    rows = json.loads((ROOT / 'evidence/nine_site_audit.json').read_text())['rows']
    witness = dict(site='GEMSDOE24 lattice witness', repo='buffedlizard55-lab/GEMSDOE24',
                   ref=WITNESS_REF, remote=WITNESS_PATH, sha256=WITNESS_SHA,
                   file=CACHE / 'r13-lattice-s5.tif')
    champs = []
    prefix = 'https://github.com/'
    for row in rows:
        url = row['immutable_file_url']
        if not url.startswith(prefix):
            raise ValueError('untrusted immutable registry URL')
        owner, repo, marker, ref, *parts = url[len(prefix):].split('/')
        if marker != 'blob' or ref != row['snapshot_sha']:
            raise ValueError('immutable registry reference mismatch')
        champs.append(dict(site=row['site'], repo=f'{owner}/{repo}', ref=ref,
                           remote='/'.join(parts), sha256=row['sha256'],
                           file=CACHE / 'champions' / (row['site'] + '.tif')))
    all_sources = [witness, *champs]
    def ensure(s):
        if do_fetch:
            fetch(s['repo'], s['ref'], s['remote'], s['sha256'], s['file'])
        if not s['file'].is_file() or digest(s['file']) != s['sha256']:
            raise FileNotFoundError(f"missing or mismatched pinned witness: {s['site']}")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(ensure, all_sources))
    return witness, champs


def audit(do_fetch=False):
    witness, champs = sources(do_fetch)
    if digest(TIF) != EXPECTED:
        raise ValueError('existing WBG-2 TIFF bytes changed')
    validation = check_tiff(TIF)
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        zip_ok = names == [TIF.name] and hashlib.sha256(z.read(names[0])).hexdigest() == EXPECTED
    with rasterio.open(ROOT / 'data/bridge/sample_submission.tif') as ref:
        footprint = np.isfinite(ref.read(1))
        grid = (ref.shape, ref.crs, ref.transform)
    with rasterio.open(ROOT / 'data/bridge/labels.tif') as ref:
        if (ref.shape, ref.crs, ref.transform) != grid:
            raise ValueError('catalogue grid mismatch')
        catalogue = ref.read(1) == 1
    with rasterio.open(TIF) as src:
        if (src.shape, src.crs, src.transform) != grid:
            raise ValueError('candidate grid mismatch')
        final = src.read(1)
    # Reconstruct the prior used by the historic builder. This is RETROSPECTIVE;
    # it is not evidence that the required check happened before dot placement.
    operative = np.where(footprint & ~prior.catalogue_buffer(catalogue),
                         prior.density_prior(catalogue), 0).astype('float32')
    # The historical mask is a 4-connected dilation, not a Euclidean disc.
    # Measure the actual file; this does not modify its predictions.
    distance = distance_transform_edt(~catalogue)
    dot_distance = distance[(final > 0) & footprint]
    if dot_distance.size != 36000:
        raise ValueError('unexpected existing WBG-2 dot count')
    catalogue_distance = {
        'historical_mask': 'four 4-connected dilation steps; Manhattan distance <=4 pixels',
        'pixel_size_m': 100,
        'min_euclidean_distance_px': float(dot_distance.min()),
        'min_euclidean_distance_m': float(dot_distance.min() * 100),
        'dots_less_than_400m_euclidean': int((dot_distance < 4).sum()),
        'dots_at_or_within_300m_euclidean': int((dot_distance <= 3).sum()),
        'dots_inside_historical_manhattan_mask': int(((final > 0) & prior.catalogue_buffer(catalogue)).sum()),
        'interpretation': 'The prior claim that all dots are at least 400 m Euclidean from the catalogue was incorrect.',
    }
    del distance, dot_distance

    def compare(candidate, entries):
        index = {'rasters': [dict(repo_first=s['repo'], sources=[s['remote']],
                                  cache_file=str(s['file']), sha256=s['sha256']) for s in entries],
                 'complete_accessible_scan': False, 'errors': []}
        # A witness proves failure even though this is not a complete inventory.
        result = uniqueness.compare_array_to_registry(candidate, index, footprint,
                         file_sha256=EXPECTED if candidate is final else None,
                         include_reverse=False, expected_grid=grid)
        if len(result['rows']) != len(entries) or any('error' in x for x in result['rows']):
            raise ValueError('a registry comparison failed; no clearance possible')
        wanted = ('sha256', 'their_dots', 'my_dots_within_3px_of_theirs',
                  'spearman_full_footprint', 'identical_bytes',
                  'identical_decoded_predictions', 'duplicate_by_rho', 'duplicate_by_overlap')
        return [{**{'site': s['site'], 'source': f"https://github.com/{s['repo']}/blob/{s['ref']}/{s['remote']}"},
                 **{k: r[k] for k in wanted}} for s, r in zip(entries, result['rows'])]

    # Witness tested first: if it fails, only the recorded diagnostic below is permitted.
    surface = compare(operative, [witness])[0]
    dots = compare(final, [witness])[0]
    if not surface['duplicate_by_overlap'] or not dots['duplicate_by_overlap']:
        raise ValueError('expected negative witness not reproduced; review before publishing')
    by_site = compare(final, champs)  # post-stop diagnostics; not clearance
    result = {
        'schema': 'wbg2-safety-audit-v1', 'review_date_utc': '2026-10-27',
        'evidence_class': 'REGISTRY-MEASUREMENT', 'scientific_experiments_started': 0,
        'existing_tiff_sha256': EXPECTED, 'no_new_dots_placed': True,
        'surface_phase': 'Retrospective deterministic reconstruction, not a contemporaneous pre-placement check.',
        'surface_witness': surface, 'already_placed_final_dots_witness': dots,
        'catalogue_buffer_diagnostic': catalogue_distance,
        'nine_champion_diagnostics': by_site,
        'scope': 'One hash-pinned lattice plus one historical champion per focus site; not a complete registry, all submissions, later commits, or private rasters.',
        'metric': 'shared gems57.uniqueness, positive support, Euclidean distance <=3 pixels; signed Spearman over footprint',
        'literal_rule': 'STOP when signed rho > 0.90 OR forward overlap > 0.70, without enrichment/density exemptions',
        'passed_literal_gate': False, 'verdict': 'negative', 'ok_to_submit': False,
        'local_format_passed': bool(validation['all_checks_passed']),
        'local_format': {k: validation[k] for k in ('sha256', 'meta', 'n_nan', 'n_infinite', 'min', 'max', 'checks')},
        'zip_single_member_identical': zip_ok,
        'format_caveat': 'Local mirrored-grid check and zero-exterior policy only, not organizer acceptance or proof of official data origin.',
        'slots_used': 0,
    }
    if not result['local_format_passed'] or not zip_ok:
        raise ValueError('existing TIFF or ZIP failed local format/identity checks')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fetch', action='store_true', help='restore hash-pinned comparison bytes from GitHub')
    ap.add_argument('--record', action='store_true', help='write the audit JSON')
    args = ap.parse_args()
    result = audit(args.fetch)
    if args.record:
        OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(json.dumps({'error': str(exc), 'ok_to_submit': False}), file=sys.stderr)
        raise SystemExit(1)
