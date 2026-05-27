# COAD GCS 4-Agent Auto Loop

- SDK: pdrp_sdk.v0.1
- Status: completed
- Started: 2026-05-27T05:40:26+00:00
- Completed: 2026-05-27T05:40:27+00:00

## Agents

### preflight_qa_agent

- status: completed
- action: verified_inputs_and_cost_state

### pipeline_agent

- status: completed
- action: resume_mode_verified_existing_admet_top15
- output admet_top15: `/private/tmp/coad_step3_outputs/final_selection/admet_filtered_top15.csv`

### image_modal_agent

- status: completed
- action: ran image remap exit=0
- output im4c_drug_summary: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/Colon/0.Image_modal_COAD/step_gcs_basic_top15_im4c_remap/coad_gcs_basic_top15_im4c_drug_summary.csv`
- output im4c_summary: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/Colon/0.Image_modal_COAD/step_gcs_basic_top15_im4c_remap/coad_gcs_basic_top15_im4c_summary.json`

### evidence_report_agent

- status: completed
- action: ran evidence agent exit=0
- output verified_tiers: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/Colon/0.Image_modal_COAD/step_gcs_basic_top15_evidence_agent/coad_gcs_basic_top15_evidence_verified_tiers.csv`
- output report: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/Colon/0.Image_modal_COAD/step_gcs_basic_top15_evidence_agent/coad_gcs_basic_top15_evidence_report.md`
- output summary: `/Users/skku_aws2_14/Documents/New project 2/final-project_data-pipline/Colon/0.Image_modal_COAD/step_gcs_basic_top15_evidence_agent/coad_gcs_basic_top15_evidence_summary.json`

## DB Status

- loaded_to_postgres: false
- note: DB loading has not been executed yet. Add a separate DB Load Agent when the service schema target is finalized.
