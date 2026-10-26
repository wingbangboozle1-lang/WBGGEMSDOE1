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
