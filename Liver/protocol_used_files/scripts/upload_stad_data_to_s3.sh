#!/usr/bin/env bash
# Upload STAD ./data/ (FE inputs) to team S3 prefix (matches nextflow.config params.s3_base).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
S3_TARGET="s3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/data/"
LOG="$ROOT/logs/upload_data_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

log "=== STAD data/ -> S3 ==="
log "Local: $ROOT/data/"
log "Target: $S3_TARGET"

aws s3 sync "$ROOT/data/" "$S3_TARGET" \
  --storage-class INTELLIGENT_TIERING \
  2>&1 | tee -a "$LOG"

log "=== Done ==="
