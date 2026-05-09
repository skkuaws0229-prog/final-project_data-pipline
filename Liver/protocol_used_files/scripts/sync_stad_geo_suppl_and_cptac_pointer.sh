#!/usr/bin/env bash
# Stream GEO supplemental archives to S3 (no full local copy) + upload CPTAC-STAD access notes.
#
# GEO (NCBI FTP):
#   GSE62254 suppl: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE62nnn/GSE62254/suppl/
#   GSE15459 suppl: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE15nnn/GSE15459/suppl/
#
# CPTAC-STAD: TCIA collection is ~1.12 TB and requires TCIA Data Retriever + Aspera (see TCIA page).
#   This script uploads a README under Stad_raw/cptac_stad/ with official links and CRDC portals.
#
# Usage:
#   ./scripts/sync_stad_geo_suppl_and_cptac_pointer.sh
#   S3_STAD_RAW=s3://other-bucket/prefix ./scripts/sync_stad_geo_suppl_and_cptac_pointer.sh

set -euo pipefail
S3="${S3_STAD_RAW:-s3://say2-4team/Stad_raw}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/logs/sync_stad_suppl_cptac_$(date +%Y%m%d_%H%M%S).log"
TMPDIR="$(mktemp -d)"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

stream_ftp_to_s3() {
  local url="$1" s3key="$2"
  log "STREAM (curl|aws s3 cp -) $url -> $s3key"
  curl -fL --retry 5 --connect-timeout 60 --max-time 0 "$url" | aws s3 cp - "$s3key" --storage-class INTELLIGENT_TIERING
}

small_to_s3() {
  local url="$1" s3key="$2"
  local tmp
  tmp="$(mktemp "${TMPDIR}/small.XXXXXX")"
  log "GET $url -> $s3key"
  curl -fL --retry 5 -o "$tmp" "$url"
  aws s3 cp "$tmp" "$s3key" --storage-class INTELLIGENT_TIERING
  rm -f "$tmp"
}

log "=== GEO suppl -> $S3/geo (streaming) ==="
mkdir -p "$ROOT/logs"

stream_ftp_to_s3 \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE62nnn/GSE62254/suppl/GSE62254_RAW.tar" \
  "${S3}/geo/GSE62254/suppl/GSE62254_RAW.tar"

small_to_s3 \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE62nnn/GSE62254/suppl/filelist.txt" \
  "${S3}/geo/GSE62254/suppl/filelist.txt"

stream_ftp_to_s3 \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE15nnn/GSE15459/suppl/GSE15459_RAW.tar" \
  "${S3}/geo/GSE15459/suppl/GSE15459_RAW.tar"

small_to_s3 \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE15nnn/GSE15459/suppl/filelist.txt" \
  "${S3}/geo/GSE15459/suppl/filelist.txt"

small_to_s3 \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE15nnn/GSE15459/suppl/GSE15459_outcome.xls" \
  "${S3}/geo/GSE15459/suppl/GSE15459_outcome.xls"

log "=== CPTAC-STAD docs -> $S3/cptac_stad/ (from repo configs/) ==="

README_SRC="$ROOT/configs/README_CPTAC_STAD_ACCESS.md"
if [[ ! -f "$README_SRC" ]]; then
  log "ERROR missing $README_SRC"
  exit 1
fi
aws s3 cp "$README_SRC" "${S3}/cptac_stad/README_CPTAC_STAD_ACCESS.md" \
  --content-type "text/markdown; charset=utf-8" --storage-class INTELLIGENT_TIERING
log "Uploaded README from $README_SRC"

log "Log: $LOG"
log "=== Done ==="
