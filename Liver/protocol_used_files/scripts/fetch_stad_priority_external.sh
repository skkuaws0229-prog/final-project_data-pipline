#!/usr/bin/env bash
# Priority external assets (user order): cosmic_stad → GSE84437 → PDC manifests.
#
# Reference (Lung cosmic_lung): s3://say2-4team/Lung_raw/additional_sources/cosmic_lung/
# COSMIC build: scripts/build_cosmic_stad.py
# GEO: scripts/download_stad_geo_gse84437.sh
# PDC: scripts/fetch_pdc_cptac_stad_manifest.py
#
# Usage:
#   ./scripts/fetch_stad_priority_external.sh
#   SYNC_S3=1 ./scripts/fetch_stad_priority_external.sh
#   SKIP_COSMIC=1 SYNC_S3=1 ./scripts/fetch_stad_priority_external.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SYNC_S3="${SYNC_S3:-0}"
export S3_STAD_RAW="${S3_STAD_RAW:-s3://say2-4team/Stad_raw}"
cd "$ROOT"
mkdir -p "$ROOT/logs" "$ROOT/curated_data/additional_sources/cosmic"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== fetch_stad_priority_external SYNC_S3=$SYNC_S3 ==="

if [[ "${SKIP_COSMIC:-0}" != "1" ]]; then
  log "(1) build_cosmic_stad"
  if ! compgen -G "$ROOT/curated_data/additional_sources/cosmic/"*.tar >/dev/null; then
    log "  syncing COSMIC tars from S3 -> curated_data/additional_sources/cosmic/"
    aws s3 sync "${S3_STAD_RAW}/additional_sources/cosmic/" "$ROOT/curated_data/additional_sources/cosmic/" \
      --exclude "*" --include "*.tar" --only-show-errors
  fi
  RUN_DATE="${COSMIC_STAD_DATE:-$(date +%Y%m%d)}"
  SYNC_S3="$SYNC_S3" python3 "$ROOT/scripts/build_cosmic_stad.py" --root "$ROOT" --run-date "$RUN_DATE"
else
  log "(1) SKIP_COSMIC=1 — skip cosmic_stad"
fi

log "(2) GSE84437"
SYNC_S3="$SYNC_S3" "$ROOT/scripts/download_stad_geo_gse84437.sh"

log "(3) PDC CPTAC-STAD manifests"
RUN_DATE="${PDC_MANIFEST_DATE:-$(date +%Y%m%d)}"
SYNC_S3="$SYNC_S3" python3 "$ROOT/scripts/fetch_pdc_cptac_stad_manifest.py" --root "$ROOT" --run-date "$RUN_DATE"

log "=== Done ==="
