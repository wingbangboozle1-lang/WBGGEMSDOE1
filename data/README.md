# Reproducible inputs, not committed data

Run `bash scripts/download_competition_data.sh`, then `.venv/bin/python scripts/prepare_data.py`.
The core rasters are public **owner mirrors**, not independently authenticated organizer downloads.
`registry/data_manifest.json` records immutable source pins and expected hashes. The unchanged
shared template assembles the large feature raster and creates its sentinel-safe band cache.
All nineteen local band hashes must match the template's expected hashes before research runs.

- `training_features.tif`: nineteen measured feature bands, **not hidden test labels**.
- `labels.tif` / `existing_faults.tif`: public mapped-fault catalogue.
- `sample_submission.tif`: grid and finite-footprint mask only. Its nonzero values are never model inputs.
- `template57/.cache/features/`: ignored, memory-mapped original template band cache.

Never interpret a known catalogue fault as a newly discovered vent. No hidden organizer truth is available.
Never commit the feature raster, band caches, downloaded repositories, or generated training matrices.

## Inherited parallel-lane inputs

Concurrent main retained small, hash-pinned grid/catalogue files under `data/bridge/` and the
TIP1 LiDAR provenance JSON under `data/external/`. They are preserved for frozen TIP1/MVGZ
receipt checks, not used as inherited prediction features in WBG-C1. The current validator can
use the bridge grid/catalogue only after verifying the same expected SHA-256 pins.

- TIP1's original independent restore is `scripts/restore_inputs.py`; this is data retrieval,
  not permission to rerun its stopped experiment.
- The older full bridge assembly commands remain available as `scripts/download_bridge_legacy.sh`
  and `scripts/prepare_bridge_legacy.py`. They are not the current WBG-C1 cache-preparation entry point.
- Do not commit restored LiDAR rasters, raw feature parts or `registry/cache/`.
