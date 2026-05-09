#!/bin/zsh
set -euo pipefail

SOURCE_S3="${1:-s3://say2-4team/Lung_raw/}"
TARGET_BASE="${2:-s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG}"
TARGET_S3="${TARGET_BASE%/}/raw_source_snapshot/Lung_raw/"

echo "Read-only source : $SOURCE_S3"
echo "Mirror target    : $TARGET_S3"
echo "Mode             : copy-only mirror (source untouched)"

aws s3 sync "$SOURCE_S3" "$TARGET_S3" --exact-timestamps

echo "Lung raw snapshot mirror complete."
