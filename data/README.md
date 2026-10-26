# Data

Official rasters are **not** stored in git (GitHub 100 MB limit; 419 MB feature stack).

```bash
bash scripts/download_competition_data.sh
python scripts/prepare_data.py
```

Restores `data/bridge/{example_submission,existing_faults,gems-geodawn-numerical-features}.tif` from `buffedlizard55-lab/GEMSDOE` and checks SHA-256 pins in `src/gems1/grid.py`.
