#!/usr/bin/env bash
# Run from any working directory. Downloads never spend a submission slot.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
"$PYTHON" "$ROOT/scripts/restore_data.py"
