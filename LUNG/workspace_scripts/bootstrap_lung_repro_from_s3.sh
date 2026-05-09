#!/bin/zsh
set -euo pipefail

WORKSPACE_ROOT="${1:-$PWD}"
S3_BASE="${2:-s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG}"

echo "Workspace root: $WORKSPACE_ROOT"
echo "S3 source: $S3_BASE"

mkdir -p "$WORKSPACE_ROOT/20260416_new_pre_project_biso_Lung"
mkdir -p "$WORKSPACE_ROOT/reports"
mkdir -p "$WORKSPACE_ROOT/scripts"
mkdir -p "$WORKSPACE_ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/ml_step4_1/luad/2C_numeric_smiles_context"
mkdir -p "$WORKSPACE_ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/dl_step4_2_7model_full/luad/2C_numeric_smiles_context"
mkdir -p "$WORKSPACE_ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad"

aws s3 sync "$S3_BASE/project_root/" "$WORKSPACE_ROOT/20260416_new_pre_project_biso_Lung/" --exact-timestamps
aws s3 sync "$S3_BASE/workspace_reports/" "$WORKSPACE_ROOT/reports/" --exact-timestamps
aws s3 sync "$S3_BASE/workspace_scripts/" "$WORKSPACE_ROOT/scripts/" --exact-timestamps

aws s3 sync \
  "$S3_BASE/supporting_inputs/step4_models/ml_step4_1/luad/2C_numeric_smiles_context/" \
  "$WORKSPACE_ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/ml_step4_1/luad/2C_numeric_smiles_context/" \
  --exact-timestamps

aws s3 sync \
  "$S3_BASE/supporting_inputs/step4_models/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/" \
  "$WORKSPACE_ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/" \
  --exact-timestamps

aws s3 sync \
  "$S3_BASE/supporting_inputs/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/" \
  "$WORKSPACE_ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/" \
  --exact-timestamps

aws s3 cp "$S3_BASE/workspace_docs/drug_repurposing_pipeline_protocol.md" "$WORKSPACE_ROOT/drug_repurposing_pipeline_protocol.md"

echo "LUNG reproducibility bootstrap complete."
