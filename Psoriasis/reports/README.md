# Psoriasis 138-Drug Baseline Branch

This directory is the canonical psoriasis baseline branch built around the 138-drug ChEMBL-named universe.

It is organized so that another reader can follow the pipeline in one direction:

1. `step0_psoriasis_source_inventory_20260507_v1`
2. `step0_psoriasis_geo_omics_download_20260504_v2`
3. `step1_psoriasis_label_cleanup_normalization_20260504_v2`
4. `step1b_psoriasis_expression_matrix_extraction_20260504_v2`
5. `step2_psoriasis_disease_signature_20260504_v2`
6. `step3_psoriasis_chembl_target_ic50_20260504_v2`
7. `step4_psoriasis_feature_engineering_20260504_v2`
8. `step5b_psoriasis_ml_sagemaker_20260507_v1`
9. `step6_psoriasis_external_validation_20260507_v2_baseline`
10. `step6b_psoriasis_molecular_validation_20260507_v2_baseline`
11. `step7_psoriasis_admet_filter_20260507_v2_baseline`

## Canonical vs archival Step5 outputs

The current canonical ML branch is:

- `step5b_psoriasis_ml_sagemaker_20260507_v1`

Older directories such as:

- `step5_psoriasis_ml_all_20260504_v2`
- `step5_psoriasis_dl_all_20260504_v2`
- `step5_psoriasis_graph_all_20260504_v2`
- `step5_fullrun_logs_20260504_v2`

are kept as historical artifacts, but they are not the current branch-of-record for the baseline handoff.

## Why this is not mixed with the middle-universe branch

This branch keeps the psoriasis 138-drug baseline as the main universe from upstream through downstream interpretation.

- Step0 through Step4 are baseline-native in this directory.
- Step5 was rerun on SageMaker for the baseline branch.
- Step6, Step6b, and Step7 were recreated with baseline-specific scripts and write their outputs back into this directory.

This means the current psoriasis baseline flow does **not** depend on the earlier `v3_name_recovery` middle-universe outputs for its canonical downstream results.

## Main files

- lineage manifest:
  - [psoriasis_v2_baseline_lineage_manifest_20260507_v1.json](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/psoriasis_v2_baseline_lineage_manifest_20260507_v1.json)
- final handoff:
  - [FINAL_HANDOFF_20260507.md](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/FINAL_HANDOFF_20260507.md)
- Step6 summary:
  - [step6 summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/step6_psoriasis_external_validation_20260507_v2_baseline/step6_psoriasis_external_validation_20260507_v2_baseline_summary.json)
- Step6b summary:
  - [step6b summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/step6b_psoriasis_molecular_validation_20260507_v2_baseline/step6b_psoriasis_molecular_validation_20260507_v2_baseline_summary.json)
- Step7 summary:
  - [step7 summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/step7_psoriasis_admet_filter_20260507_v2_baseline/step7_psoriasis_admet_filter_20260507_v2_baseline_summary.json)
