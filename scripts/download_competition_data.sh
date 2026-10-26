#!/usr/bin/env bash
# Download competition data into data/raw/.
# Two paths:
#   1) OFFICIAL (needs a login session / manual download):
#        https://www.drivendata.org/competitions/306/competition-doe-gems/data/
#      Place training_features.tif (a.k.a. gems-geodawn-numerical-features.tif),
#      labels.tif, existing_faults.tif, sample_submission.tif into data/raw/.
#   2) GITHUB MIRRORS (automated, integrity-pinned, NOT organizer-authenticated):
#      run with MIRRORS=1 (default). Uses sparse checkout so only data blobs
#      are fetched. Every file is hash-verified by scripts/prepare_data.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/data/raw"
MIRRORS="${MIRRORS:-1}"

mkdir -p "$DEST/external" "$ROOT/data/registry"
export GIT_TERMINAL_PROMPT=0

if [ "$MIRRORS" = "1" ]; then
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  echo "[1/3] sparse-fetch GEMSDOE24 (labels/sample/externals/champions)..."
  git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/buffedlizard55-lab/GEMSDOE24 "$TMP/g24" >&2
  (cd "$TMP/g24" && git sparse-checkout set data/bridge data/external docs/downloads >&2)
  cp "$TMP/g24/data/bridge/labels.tif" "$TMP/g24/data/bridge/sample_submission.tif" \
     "$TMP/g24/data/bridge/existing_faults.tif" "$DEST/"
  cp "$TMP/g24/data/external/"*.tif "$TMP/g24/data/external/"*.json \
     "$TMP/g24/data/external/"*.csv "$DEST/external/" 2>/dev/null || true
  cp "$TMP/g24/data/external/"*.zip "$DEST/external/" 2>/dev/null || true
  cp "$TMP/g24/docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif" \
     "$ROOT/data/registry/g25-d28-nan.tif"
  cp "$TMP/g24/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif" \
     "$ROOT/data/registry/g24-d15-nan.tif"

  echo "[2/3] sparse-fetch GEMSDOE (19-band feature stack, 5 parts)..."
  git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/buffedlizard55-lab/GEMSDOE "$TMP/gmain" >&2
  (cd "$TMP/gmain" && git sparse-checkout set data/bridge >&2)
  cat "$TMP/gmain/data/bridge/gems-geodawn-numerical-features.tif.part-"* \
    > "$DEST/training_features.tif"

  echo "[3/3] fetch remaining focus-9 champion rasters..."
  fetch_one() { # repo, srcpath, dest
    local repo="$1" src="$2" dest="$3" d="$TMP/c_$1"
    if [ ! -d "$d" ]; then
      git clone --depth 1 --filter=blob:none --sparse \
        "https://github.com/buffedlizard55-lab/$repo" "$d" >&2
    fi
    (cd "$d" && git sparse-checkout set --skip-checks "$src" >&2)
    cp "$d/$src" "$ROOT/data/registry/$dest"
  }
  fetch_one GEMSDOE32 docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif g32-h33-champ-zeros.tif
  fetch_one GEMSDOE28 docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif g28-rung30-nan.tif
  fetch_one GEMSDOE31 docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif g31-h274solo-nan.tif
  fetch_one GEMSDOE36 docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif g36-pinn-zeros.tif
  fetch_one GEMSDOE30 docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif g30-poisson.tif
  fetch_one GEMSDOE33 docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif g33-analog.tif
  fetch_one GEMSDOE27 docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif g27-gap-nan.tif
  echo "mirror fetch complete."
else
  echo "MIRRORS=0: expecting official files already in $DEST"
fi

echo "verifying + preparing..."
python3 "$ROOT/scripts/prepare_data.py"
