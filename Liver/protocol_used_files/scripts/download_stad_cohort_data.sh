#!/usr/bin/env bash
# Download STAD-specific open data into curated_data/, then optionally sync to S3 Stad_raw/.
#
# Sources (document for reproducibility):
#   GEO GSE62254 matrix: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE62nnn/GSE62254/matrix/GSE62254_series_matrix.txt.gz
#   GEO GSE15459 matrix: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE15nnn/GSE15459/matrix/GSE15459_series_matrix.txt.gz
#   TCGA STAD PanCanAtlas 2018 (cBioPortal staging tarball, mirrored on GitHub):
#     https://github.com/labxscut/HCG/releases/download/HCG/stad_tcga_pan_can_atlas_2018.tar.gz
#     (Same study as cBioPortal stad_tcga_pan_can_atlas_2018 per that repository README.)
#
# Outputs (local):
#   curated_data/geo/GSE62254/matrix/*.gz
#   curated_data/geo/GSE15459/matrix/*.gz
#   curated_data/cbioportal/stad_tcga_pan_can_atlas_2018/  (extracted from tarball)
#
# Usage:
#   ./scripts/download_stad_cohort_data.sh              # download only
#   SYNC_S3=1 ./scripts/download_stad_cohort_data.sh    # also aws s3 sync to s3://say2-4team/Stad_raw/

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CUR="$ROOT/curated_data"
LOG="$ROOT/logs/download_stad_cohort_$(date +%Y%m%d_%H%M%S).log"
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

log "=== STAD cohort download ROOT=$ROOT ==="

mkdir -p "$CUR/geo/GSE62254/matrix" "$CUR/geo/GSE15459/matrix" "$CUR/cbioportal" "$ROOT/logs"

fetch "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE62nnn/GSE62254/matrix/GSE62254_series_matrix.txt.gz" \
  "$CUR/geo/GSE62254/matrix/GSE62254_series_matrix.txt.gz"

fetch "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE15nnn/GSE15459/matrix/GSE15459_series_matrix.txt.gz" \
  "$CUR/geo/GSE15459/matrix/GSE15459_series_matrix.txt.gz"

STAD_TGZ_URL="https://github.com/labxscut/HCG/releases/download/HCG/stad_tcga_pan_can_atlas_2018.tar.gz"
STUDY_DIR="$CUR/cbioportal/stad_tcga_pan_can_atlas_2018"
TGZ="$CUR/cbioportal/stad_tcga_pan_can_atlas_2018.tar.gz"

if [[ -d "$STUDY_DIR" ]] && [[ -f "$STUDY_DIR/meta_study.txt" || -f "$STUDY_DIR/data_clinical_patient.txt" ]]; then
  log "SKIP extract: $STUDY_DIR already looks populated"
else
  fetch "$STAD_TGZ_URL" "$TGZ"
  log "Extracting tarball (may take 1–2 min)..."
  mkdir -p "$CUR/cbioportal"
  tar -xzf "$TGZ" -C "$CUR/cbioportal"
  log "Extracted under $CUR/cbioportal/ (tar root is usually stad_tcga_pan_can_atlas_2018/)"
fi

log "Disk usage (new paths):"
du -sh "$CUR/geo/GSE62254" "$CUR/geo/GSE15459" "$STUDY_DIR" 2>/dev/null | tee -a "$LOG"

if [[ "${SYNC_S3:-}" == "1" ]]; then
  log "=== aws s3 sync -> $S3_DST ==="
  aws s3 sync "$CUR/geo/" "${S3_DST}/geo/" --only-show-errors 2>&1 | tee -a "$LOG"
  aws s3 sync "$CUR/cbioportal/" "${S3_DST}/cbioportal/" --only-show-errors 2>&1 | tee -a "$LOG"
  log "S3 sync done."
fi

log "Log: $LOG"
log "=== Done ==="
