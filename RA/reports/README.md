# RA Named-Drug Baseline Branch

This directory is the canonical rheumatoid arthritis named-drug baseline branch.

It is organized so that another reader can follow the pipeline in one direction:

1. `step0_ra_source_inventory_20260507_v1`
2. `step1_ra_label_cleanup_normalization_20260506_v2`
3. `step1b_ra_expression_matrix_extraction_20260506_v2`
4. `step2_ra_disease_signature_20260506_v2`
5. `step3_ra_chembl_target_ic50_20260507_v1`
6. `step4_ra_feature_engineering_20260507_v1`
7. `step5b_ra_ml_sagemaker_20260507_v1`
8. `step6_ra_external_validation_20260507_v1`
9. `step7_ra_admet_filter_20260507_v1`

## What is copied vs linked

- `step1` and `step2` are copied into this branch as frozen upstream snapshots.
- `step1b` is linked as a frozen snapshot because the expression matrices are large.
- `step3` is the point where the named-drug universe is intentionally redefined for this branch.
- `step4` through `step7` are branch-native outputs built from that named-drug Step3 universe.

## Why this is not a mixed branch

This branch does **not** reuse the older middle-universe `step4b` or `step5` outputs as downstream inputs.

The branch logic is:

- disease-side preprocessing stays fixed through shared upstream RA preprocessing
- drug universe diverges explicitly at `step3`
- all modeling and downstream validation then continue inside this branch

## Main files

- lineage manifest:
  - [ra_v3_named_drug_baseline_lineage_manifest_20260507_v1.json](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/ra_v3_named_drug_baseline_lineage_manifest_20260507_v1.json)
- final handoff:
  - [FINAL_HANDOFF_20260507.md](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/FINAL_HANDOFF_20260507.md)
- Step6 summary:
  - [step6 summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/step6_ra_external_validation_20260507_v1/step6_ra_external_validation_20260507_v1_summary.json)
- Step7 summary:
  - [step7 summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/step7_ra_admet_filter_20260507_v1/step7_ra_admet_filter_20260507_v1_summary.json)
