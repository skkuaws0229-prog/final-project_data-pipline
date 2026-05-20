#!/bin/zsh
set -euo pipefail

ROOT="/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest"
GCS_BASE="${1:-gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso/202604_Final_data/LUNG}"

echo "Sync target: $GCS_BASE"

gcloud storage rsync -r "$ROOT/20260416_new_pre_project_biso_Lung/" "$GCS_BASE/project_root/"

gcloud storage rsync -r \
  "$ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/ml_step4_1/luad/2C_numeric_smiles_context/" \
  "$GCS_BASE/supporting_inputs/step4_models/ml_step4_1/luad/2C_numeric_smiles_context/"

gcloud storage rsync -r \
  "$ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/" \
  "$GCS_BASE/supporting_inputs/step4_models/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/"

gcloud storage rsync -r \
  "$ROOT/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/" \
  "$GCS_BASE/supporting_inputs/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/"

gcloud storage rsync -r "$ROOT/reports/lung_directive_ensemble/" "$GCS_BASE/workspace_reports/lung_directive_ensemble/"
gcloud storage rsync -r "$ROOT/reports/lung_step6_package/" "$GCS_BASE/workspace_reports/lung_step6_package/"
gcloud storage rsync -r "$ROOT/reports/lung_step6_current_package/" "$GCS_BASE/workspace_reports/lung_step6_current_package/"
gcloud storage rsync -r "$ROOT/reports/lung_reproducibility/" "$GCS_BASE/workspace_reports/lung_reproducibility/"

gcloud storage cp "$ROOT/drug_repurposing_pipeline_protocol.md" "$GCS_BASE/workspace_docs/drug_repurposing_pipeline_protocol.md"
gcloud storage cp "$ROOT/20260416_new_pre_project_biso_Lung/README.md" "$GCS_BASE/workspace_docs/LUNG_README.md"

gcloud storage cp "$ROOT/scripts/build_lung_directive_ensemble.py" "$GCS_BASE/workspace_scripts/build_lung_directive_ensemble.py"
gcloud storage cp "$ROOT/scripts/bootstrap_lung_step0_raw_from_gcs.sh" "$GCS_BASE/workspace_scripts/bootstrap_lung_step0_raw_from_gcs.sh"
gcloud storage cp "$ROOT/scripts/bootstrap_lung_repro_from_gcs.sh" "$GCS_BASE/workspace_scripts/bootstrap_lung_repro_from_gcs.sh"
gcloud storage cp "$ROOT/scripts/finalize_lung_top30.py" "$GCS_BASE/workspace_scripts/finalize_lung_top30.py"
gcloud storage cp "$ROOT/scripts/mirror_lung_raw_to_current_s3.sh" "$GCS_BASE/workspace_scripts/mirror_lung_raw_to_current_s3.sh"
gcloud storage cp "$ROOT/scripts/prepare_lung_step6_package.py" "$GCS_BASE/workspace_scripts/prepare_lung_step6_package.py"
gcloud storage cp "$ROOT/scripts/run_lung_step6_current_package.py" "$GCS_BASE/workspace_scripts/run_lung_step6_current_package.py"
gcloud storage cp "$ROOT/scripts/sync_lung_repro_to_gcs.sh" "$GCS_BASE/workspace_scripts/sync_lung_repro_to_gcs.sh"
gcloud storage cp "$ROOT/20260416_new_pre_project_biso_Lung/step7_0_remove_duplicates.py" "$GCS_BASE/workspace_scripts/step7_0_remove_duplicates.py"
gcloud storage cp "$ROOT/20260416_new_pre_project_biso_Lung/step7_1_admet_filtering.py" "$GCS_BASE/workspace_scripts/step7_1_admet_filtering.py"
gcloud storage cp "$ROOT/20260416_new_pre_project_biso_Lung/step7_2_select_top15.py" "$GCS_BASE/workspace_scripts/step7_2_select_top15.py"

echo "LUNG reproducibility package sync to GCS complete."
