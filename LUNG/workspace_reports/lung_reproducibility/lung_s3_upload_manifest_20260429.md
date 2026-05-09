# LUNG S3 Upload Manifest

- Date: 2026-04-29
- Target: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/`
- Purpose: make the current LUNG rerun reproducible by another team member

## Upload policy

- Upload the full `20260416_new_pre_project_biso_Lung/` project root
- Upload the exact Step4 dependency folders used by the current Step5 ensemble
- Upload current workspace reports and helper scripts created during this rerun
- Upload current protocol/report documents so the rerun order is explicit

## Source mapping

| S3 subpath | Local source | Files | Approx size |
| --- | --- | ---: | ---: |
| `project_root/` | `20260416_new_pre_project_biso_Lung/` | 450 | 46.219 GB |
| `supporting_inputs/step4_models/ml_step4_1/luad/2C_numeric_smiles_context/` | `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/ml_step4_1/luad/2C_numeric_smiles_context/` | 130 | 0.032 GB |
| `supporting_inputs/step4_models/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/` | `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/` | 175 | 0.274 GB |
| `supporting_inputs/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/` | `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/` | 4 | 0.025 GB |
| `workspace_reports/lung_directive_ensemble/` | `reports/lung_directive_ensemble/` | 8 | 0.085 GB |
| `workspace_reports/lung_step6_package/` | `reports/lung_step6_package/` | 5 | ~0 GB |
| `workspace_reports/lung_step6_current_package/` | `reports/lung_step6_current_package/` | 13 | ~0 GB |
| `workspace_reports/lung_reproducibility/` | `reports/lung_reproducibility/` | generated docs | ~0 GB |
| `workspace_scripts/` | selected helper scripts listed below | selected | ~0 GB |
| `workspace_docs/` | `drug_repurposing_pipeline_protocol.md`, `20260416_new_pre_project_biso_Lung/README.md` | 2 | ~0 GB |

## Helper scripts to upload

- `scripts/build_lung_directive_ensemble.py`
- `scripts/bootstrap_lung_repro_from_s3.sh`
- `scripts/finalize_lung_top30.py`
- `scripts/prepare_lung_step6_package.py`
- `scripts/run_lung_step6_current_package.py`
- `scripts/sync_lung_repro_to_s3.sh`
- `20260416_new_pre_project_biso_Lung/step7_0_remove_duplicates.py`
- `20260416_new_pre_project_biso_Lung/step7_1_admet_filtering.py`
- `20260416_new_pre_project_biso_Lung/step7_2_select_top15.py`

## Expected result

- Another teammate should be able to:
  - bootstrap the local workspace from S3
  - inspect the exact current dataset and results
  - rerun `Step5 -> Step6 -> Step7`
  - verify the current finalized Top30 and Final Top15
