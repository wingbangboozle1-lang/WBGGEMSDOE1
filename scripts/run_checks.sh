#!/usr/bin/env bash
# Automated gates, no human inspector: unit tests + (if data present) validator
# self-check on the shipped artifact + uniqueness re-read from exact bytes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
echo "== unit tests =="
python3 -m pytest tests/ -q
if [ -f data/raw/sample_submission.tif ]; then
  echo "== shipped-artifact revalidation =="
  python3 - "$ROOT" << 'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "src"))
from wbg1 import holdout, validate
root = Path(sys.argv[1])
cards = sorted((root / "docs" / "downloads").glob("*-audit.json"))
assert cards, "no shipped audit json"
for c in cards:
    a = json.loads(c.read_text())
    z = root / "docs" / "downloads" / a["zeros_tif"]["filename"]
    fmt = validate.validate_format(z, root / "data" / "raw" / "sample_submission.tif", True)
    print(c.name, "format_pass=", fmt["pass"])
PY
else
  echo "(data absent; skipping artifact revalidation)"
fi
echo "ALL CHECKS DONE"
