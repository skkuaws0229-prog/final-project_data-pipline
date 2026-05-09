#!/bin/zsh
set -euo pipefail

ROOT="/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest"
S3_BASE="${1:-s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG}"

echo "Sync target: $S3_BASE"

aws s3 sync "$ROOT/20260416_new_pre_project_biso_Lung/" "$S3_BASE/project_root/" --exact-timestamps

aws s3 sync \
  "$ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/ml_step4_1/luad/2C_numeric_smiles_context/" \
  "$S3_BASE/supporting_inputs/step4_models/ml_step4_1/luad/2C_numeric_smiles_context/" \
  --exact-timestamps

aws s3 sync \
  "$ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/" \
  "$S3_BASE/supporting_inputs/step4_models/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/" \
  --exact-timestamps

aws s3 sync \
  "$ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/" \
  "$S3_BASE/supporting_inputs/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/" \
  --exact-timestamps

aws s3 sync "$ROOT/reports/lung_directive_ensemble/" "$S3_BASE/workspace_reports/lung_directive_ensemble/" --exact-timestamps
aws s3 sync "$ROOT/reports/lung_step6_package/" "$S3_BASE/workspace_reports/lung_step6_package/" --exact-timestamps
aws s3 sync "$ROOT/reports/lung_step6_current_package/" "$S3_BASE/workspace_reports/lung_step6_current_package/" --exact-timestamps
aws s3 sync "$ROOT/reports/lung_reproducibility/" "$S3_BASE/workspace_reports/lung_reproducibility/" --exact-timestamps

aws s3 cp "$ROOT/drug_repurposing_pipeline_protocol.md" "$S3_BASE/workspace_docs/drug_repurposing_pipeline_protocol.md"
aws s3 cp "$ROOT/20260416_new_pre_project_biso_Lung/README.md" "$S3_BASE/workspace_docs/LUNG_README.md"

aws s3 cp "$ROOT/scripts/build_lung_directive_ensemble.py" "$S3_BASE/workspace_scripts/build_lung_directive_ensemble.py"
aws s3 cp "$ROOT/scripts/bootstrap_lung_step0_raw_from_s3.sh" "$S3_BASE/workspace_scripts/bootstrap_lung_step0_raw_from_s3.sh"
aws s3 cp "$ROOT/scripts/bootstrap_lung_repro_from_s3.sh" "$S3_BASE/workspace_scripts/bootstrap_lung_repro_from_s3.sh"
aws s3 cp "$ROOT/scripts/finalize_lung_top30.py" "$S3_BASE/workspace_scripts/finalize_lung_top30.py"
aws s3 cp "$ROOT/scripts/mirror_lung_raw_to_current_s3.sh" "$S3_BASE/workspace_scripts/mirror_lung_raw_to_current_s3.sh"
aws s3 cp "$ROOT/scripts/prepare_lung_step6_package.py" "$S3_BASE/workspace_scripts/prepare_lung_step6_package.py"
aws s3 cp "$ROOT/scripts/run_lung_step6_current_package.py" "$S3_BASE/workspace_scripts/run_lung_step6_current_package.py"
aws s3 cp "$ROOT/scripts/sync_lung_repro_to_s3.sh" "$S3_BASE/workspace_scripts/sync_lung_repro_to_s3.sh"
aws s3 cp "$ROOT/20260416_new_pre_project_biso_Lung/step7_0_remove_duplicates.py" "$S3_BASE/workspace_scripts/step7_0_remove_duplicates.py"
aws s3 cp "$ROOT/20260416_new_pre_project_biso_Lung/step7_1_admet_filtering.py" "$S3_BASE/workspace_scripts/step7_1_admet_filtering.py"
aws s3 cp "$ROOT/20260416_new_pre_project_biso_Lung/step7_2_select_top15.py" "$S3_BASE/workspace_scripts/step7_2_select_top15.py"

echo "LUNG reproducibility package sync complete."
