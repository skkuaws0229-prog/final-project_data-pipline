# LUAD GCS 4-Agent Auto Loop

- SDK: pdrp_sdk.v0.2
- Status: completed
- Started: 2026-05-27T05:57:57+00:00
- Completed: 2026-05-27T05:57:58+00:00

## Agents

### preflight_qa_agent

- status: completed
- action: verified_inputs_and_cost_state

### pipeline_agent

- status: completed
- action: resume_mode_verified_existing_admet_top15
- output admet_top15: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/LUNG/workspace_reports/lung_step6_current_package/luad_gcs_basic_admet_filtered_top15.csv`

### image_modal_agent

- status: completed
- action: ran image remap exit=0
- output im4c_drug_summary: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/LUNG/0.Image_modal_LUAD/step_gcs_basic_top15_im4c_remap/luad_gcs_basic_top15_im4c_drug_summary.csv`
- output im4c_summary: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/LUNG/0.Image_modal_LUAD/step_gcs_basic_top15_im4c_remap/luad_gcs_basic_top15_im4c_summary.json`

### evidence_report_agent

- status: completed
- action: ran evidence agent exit=0
- output verified_tiers: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/LUNG/0.Image_modal_LUAD/step_gcs_basic_top15_evidence_agent/luad_gcs_basic_top15_evidence_verified_tiers.csv`
- output report: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/LUNG/0.Image_modal_LUAD/step_gcs_basic_top15_evidence_agent/luad_gcs_basic_top15_evidence_report.md`
- output summary: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/LUNG/0.Image_modal_LUAD/step_gcs_basic_top15_evidence_agent/luad_gcs_basic_top15_evidence_summary.json`

## DB Status

- loaded_to_postgres: false
- note: DB loading has not been executed yet. Add a separate DB Load Agent when the service schema target is finalized.
