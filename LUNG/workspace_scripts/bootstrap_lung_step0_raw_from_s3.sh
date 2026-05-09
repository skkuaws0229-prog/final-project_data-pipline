#!/bin/zsh
set -euo pipefail

WORKSPACE_ROOT="${1:-$PWD}"
S3_BASE="${2:-s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG}"
TARGET_ROOT="$WORKSPACE_ROOT/20260416_new_pre_project_biso_Lung/curated_data"

echo "Workspace root: $WORKSPACE_ROOT"
echo "S3 source: $S3_BASE/raw_source_snapshot/Lung_raw/"
echo "Target curated_data root: $TARGET_ROOT"

mkdir -p "$TARGET_ROOT"

aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/GDSC/" "$TARGET_ROOT/gdsc/" --exact-timestamps
aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/admet/" "$TARGET_ROOT/admet/" --exact-timestamps
aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/CPTAC/" "$TARGET_ROOT/cptac/" --exact-timestamps
aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/depmap/" "$TARGET_ROOT/depmap/" --exact-timestamps
aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/drugbank/" "$TARGET_ROOT/drugbank/" --exact-timestamps
aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/additional_sources/" "$TARGET_ROOT/validation/" --exact-timestamps
aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/chembl/" "$TARGET_ROOT/chembl/" --exact-timestamps
aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/LInc1000(세포주)/" "$TARGET_ROOT/lincs/LInc1000_cell_lines/" --exact-timestamps
aws s3 sync "$S3_BASE/raw_source_snapshot/Lung_raw/lincs/" "$TARGET_ROOT/lincs/lincs_main/" --exact-timestamps

echo "LUNG Step0 raw bootstrap complete."
