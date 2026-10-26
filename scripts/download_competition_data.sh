#!/usr/bin/env bash
# Restore official competition rasters from the public GitHub data bridge
# (buffedlizard55-lab/GEMSDOE data/bridge). DrivenData login is not required.
# SHA-256 pins are enforced by scripts/prepare_data.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/data/bridge"
mkdir -p "$DEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "Cloning buffedlizard55-lab/GEMSDOE (sparse data/bridge)..."
git clone --depth 1 --filter=blob:none --sparse https://github.com/buffedlizard55-lab/GEMSDOE.git "$TMP/gemsdoe"
git -C "$TMP/gemsdoe" sparse-checkout set data/bridge
cp -a "$TMP/gemsdoe/data/bridge/." "$DEST/"
python3 "$ROOT/scripts/prepare_data.py"
echo "Data ready in $DEST"
