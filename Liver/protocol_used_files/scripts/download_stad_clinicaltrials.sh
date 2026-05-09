#!/usr/bin/env bash
# Fetch ClinicalTrials.gov (gastric / stomach neoplasms) into curated_data/, optional S3 upload.
#
# Reference (Lung layout): s3://say2-4team/Lung_raw/additional_sources/clinicaltrials/
# Python: 20260421_new_pre_project_biso_STAD/scripts/download_clinicaltrials_stad.py
#
# Usage:
#   ./scripts/download_stad_clinicaltrials.sh
#   SYNC_S3=1 ./scripts/download_stad_clinicaltrials.sh
#   QUERY_COND='gastric cancer' SYNC_S3=1 ./scripts/download_stad_clinicaltrials.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SYNC_S3="${SYNC_S3:-0}"
export S3_STAD_RAW="${S3_STAD_RAW:-s3://say2-4team/Stad_raw}"
cd "$ROOT"
mkdir -p "$ROOT/logs"

OPTS=()
if [[ -n "${QUERY_COND:-}" ]]; then
  OPTS+=(--query-cond "$QUERY_COND")
fi
if [[ "${NO_COMBINED:-0}" == "1" ]]; then
  OPTS+=(--no-combined)
fi

exec python3 "$ROOT/scripts/download_clinicaltrials_stad.py" "${OPTS[@]}"
