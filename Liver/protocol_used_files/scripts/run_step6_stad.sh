#!/usr/bin/env bash
# Run Step 6 external validation for STAD using shared Lung scripts + JSON config.
#
# Required local layout (after optional S3 sync):
#   curated_data/additional_sources/cosmic_stad/20260421/*.parquet
#   curated_data/geo/GSE62254/ (series matrix or SOFT)
#   curated_data/geo/GSE15459/
#   curated_data/geo/GSE84437/
#   results/stad_top30_*.csv  (from upstream training)
#
# Optional:
#   curated_data/cptac_stad/pdc_manifests/20260421/
#   curated_data/additional_sources/prism/*.csv
#   curated_data/additional_sources/clinicaltrials/clinicaltrials_gastric_cancer*.json
#
# Usage:
#   ./scripts/run_step6_stad.sh
#   SYNC_S3=1 ./scripts/run_step6_stad.sh
#   LUNG_DIR=/path/to/20260416_new_pre_project_biso_Lung ./scripts/run_step6_stad.sh

set -euo pipefail

STAD_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$STAD_ROOT/.." && pwd)"
LUNG_DIR="${LUNG_DIR:-$REPO_ROOT/20260416_new_pre_project_biso_Lung}"
CFG="$STAD_ROOT/configs/step6_validation.stad.json"
S3_RAW="${S3_STAD_RAW:-s3://say2-4team/Stad_raw}"
RUN_DATE_COSMIC="${RUN_DATE_COSMIC:-20260421}"
RUN_DATE_PDC="${RUN_DATE_PDC:-20260421}"
export SYNC_S3="${SYNC_S3:-0}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

mkdir -p "$STAD_ROOT/logs" "$STAD_ROOT/results"

if [[ ! -f "$CFG" ]]; then
  echo "Missing config: $CFG" >&2
  exit 1
fi
if [[ ! -d "$LUNG_DIR" ]]; then
  echo "Lung scripts directory not found: $LUNG_DIR (set LUNG_DIR)" >&2
  exit 1
fi

if [[ "$SYNC_S3" == "1" ]]; then
  log "S3 sync ON: $S3_RAW -> $STAD_ROOT/curated_data/..."
  aws s3 sync "${S3_RAW}/additional_sources/cosmic_stad/${RUN_DATE_COSMIC}/" \
    "$STAD_ROOT/curated_data/additional_sources/cosmic_stad/${RUN_DATE_COSMIC}/" --only-show-errors
  for gse in GSE62254 GSE15459 GSE84437; do
    aws s3 sync "${S3_RAW}/geo/${gse}/" "$STAD_ROOT/curated_data/geo/${gse}/" --only-show-errors
  done
  aws s3 sync "${S3_RAW}/cptac_stad/pdc_manifests/${RUN_DATE_PDC}/" \
    "$STAD_ROOT/curated_data/cptac_stad/pdc_manifests/${RUN_DATE_PDC}/" --only-show-errors || true
  if aws s3 ls "${S3_RAW}/additional_sources/prism/" >/dev/null 2>&1; then
    log "Sync PRISM -> curated_data/additional_sources/prism/"
    aws s3 sync "${S3_RAW}/additional_sources/prism/" \
      "$STAD_ROOT/curated_data/additional_sources/prism/" --only-show-errors
  else
    log "Optional PRISM prefix not on S3 — skip prism sync"
  fi
  if aws s3 ls "${S3_RAW}/additional_sources/clinicaltrials/" >/dev/null 2>&1; then
    log "Sync ClinicalTrials -> curated_data/additional_sources/clinicaltrials/"
    aws s3 sync "${S3_RAW}/additional_sources/clinicaltrials/" \
      "$STAD_ROOT/curated_data/additional_sources/clinicaltrials/" --only-show-errors
  else
    log "Optional clinicaltrials prefix not on S3 — skip clinicaltrials sync"
  fi
else
  log "S3 sync OFF (set SYNC_S3=1 to pull Stad_raw)"
fi

STEP=( python3 )
COMMON=( --validation-config "$CFG" --project-root "$STAD_ROOT" )

log "Step 6.1 GEO audit"
"${STEP[@]}" "$LUNG_DIR/step6_geo_external_cohorts.py" "${COMMON[@]}"

log "Step 6.2 PRISM"
"${STEP[@]}" "$LUNG_DIR/step6_2_prism_validation.py" "${COMMON[@]}"

log "Step 6.3 ClinicalTrials"
"${STEP[@]}" "$LUNG_DIR/step6_3_clinical_trials_validation.py" "${COMMON[@]}"

log "Step 6.4 COSMIC"
"${STEP[@]}" "$LUNG_DIR/step6_4_cosmic_validation.py" "${COMMON[@]}"

log "Step 6.5 CPTAC / PDC manifest"
"${STEP[@]}" "$LUNG_DIR/step6_5_cptac_validation.py" "${COMMON[@]}"

log "Step 6.6 Comprehensive scoring"
"${STEP[@]}" "$LUNG_DIR/step6_6_comprehensive_scoring.py" "${COMMON[@]}"

log "Done Step 6 STAD. Sources log: $STAD_ROOT/results/stad_step6_sources_read.json"
