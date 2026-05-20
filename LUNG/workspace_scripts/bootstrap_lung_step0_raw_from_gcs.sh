#!/bin/zsh
set -euo pipefail

WORKSPACE_ROOT="${1:-$PWD}"
GCS_BASE="${2:-gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso/202604_Final_data/LUNG}"
TARGET_ROOT="$WORKSPACE_ROOT/20260416_new_pre_project_biso_Lung/curated_data"

echo "Workspace root: $WORKSPACE_ROOT"
echo "GCS source: $GCS_BASE/raw_source_snapshot/Lung_raw/"
echo "Target curated_data root: $TARGET_ROOT"

mkdir -p "$TARGET_ROOT"

gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/GDSC/" "$TARGET_ROOT/gdsc/"
gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/admet/" "$TARGET_ROOT/admet/"
gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/CPTAC/" "$TARGET_ROOT/cptac/"
gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/depmap/" "$TARGET_ROOT/depmap/"
gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/drugbank/" "$TARGET_ROOT/drugbank/"
gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/additional_sources/" "$TARGET_ROOT/validation/"
gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/chembl/" "$TARGET_ROOT/chembl/"
gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/LInc1000(세포주)/" "$TARGET_ROOT/lincs/LInc1000_cell_lines/"
gcloud storage rsync -r "$GCS_BASE/raw_source_snapshot/Lung_raw/lincs/" "$TARGET_ROOT/lincs/lincs_main/"

echo "LUNG Step0 raw bootstrap from GCS complete."
