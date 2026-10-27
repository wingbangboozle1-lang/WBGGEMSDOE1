#!/usr/bin/env bash
# Reproducible competition + official external + scored-registry data restorer.
# Uses SHA-256 verified pinned mirrors via `scripts/restore_data.py` when GitHub
# access is available, or validates local files placed in `data/raw` / `WBG_DATA_DIR`.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${WBG_DATA_DIR:-${1:-/tmp/gems_raw}}"

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

echo "[WBGGEMSDOE1] Restoring and SHA-256 verifying competition + external + registry datasets into ${TARGET_DIR} ..."
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/restore_data.py" --group all --include-registry --target-dir "${TARGET_DIR}"
echo "[WBGGEMSDOE1] Data restoration complete."
