#!/usr/bin/env bash
# GEO GSE84437 — series matrix (sample-level abundance table) + SOFT metadata + optional RAW tar.
#
# Matrix: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE84nnn/GSE84437/matrix/GSE84437_series_matrix.txt.gz
# SOFT:  https://ftp.ncbi.nlm.nih.gov/geo/series/GSE84nnn/GSE84437/soft/GSE84437_family.soft.gz
# Suppl: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE84nnn/GSE84437/suppl/GSE84437_RAW.tar  (large)
#
# Usage:
#   ./scripts/download_stad_geo_gse84437.sh
#   SYNC_S3=1 ./scripts/download_stad_geo_gse84437.sh
#   WITH_RAW_TAR=1 SYNC_S3=1 ./scripts/download_stad_geo_gse84437.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CUR="$ROOT/curated_data"
LOG="$ROOT/logs/download_geo_gse84437_$(date +%Y%m%d_%H%M%S).log"
S3_DST="${S3_STAD_RAW:-s3://say2-4team/Stad_raw}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

fetch() {
  local url="$1" out="$2"
  mkdir -p "$(dirname "$out")"
  if [[ -f "$out" ]] && [[ -s "$out" ]]; then
    log "SKIP exists: $out"
    return 0
  fi
  log "GET $url -> $out"
  curl -fL --retry 3 --connect-timeout 30 -o "$out.partial" "$url"
  mv "$out.partial" "$out"
}

log "=== GSE84437 download ROOT=$ROOT ==="
mkdir -p "$CUR/geo/GSE84437/matrix" "$CUR/geo/GSE84437/soft" "$ROOT/logs"

fetch "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE84nnn/GSE84437/matrix/GSE84437_series_matrix.txt.gz" \
  "$CUR/geo/GSE84437/matrix/GSE84437_series_matrix.txt.gz"

fetch "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE84nnn/GSE84437/soft/GSE84437_family.soft.gz" \
  "$CUR/geo/GSE84437/soft/GSE84437_family.soft.gz"

if [[ "${WITH_RAW_TAR:-0}" == "1" ]]; then
  mkdir -p "$CUR/geo/GSE84437/suppl"
  fetch "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE84nnn/GSE84437/suppl/GSE84437_RAW.tar" \
    "$CUR/geo/GSE84437/suppl/GSE84437_RAW.tar"
else
  log "SKIP GSE84437_RAW.tar (set WITH_RAW_TAR=1 to download; large)"
fi

du -sh "$CUR/geo/GSE84437" 2>/dev/null | tee -a "$LOG"

if [[ "${SYNC_S3:-}" == "1" ]]; then
  log "=== aws s3 sync geo/GSE84437 -> $S3_DST/geo/GSE84437/ ==="
  aws s3 sync "$CUR/geo/GSE84437/" "${S3_DST}/geo/GSE84437/" --only-show-errors 2>&1 | tee -a "$LOG"
fi

log "Log: $LOG"
log "=== Done ==="
