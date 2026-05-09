# RA Named-Drug Baseline Final Handoff (2026-05-07)

## Canonical branch

- root:
  - [/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline)
- universe:
  - 127 named drugs
- canonical lineage:
  - disease-side preprocessing carried as frozen Step1/Step2 snapshots
  - named-drug divergence begins at Step3
  - Step4 through Step7 are branch-native

## Current branch-of-record artifacts

- lineage manifest:
  - [ra_v3_named_drug_baseline_lineage_manifest_20260507_v1.json](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/ra_v3_named_drug_baseline_lineage_manifest_20260507_v1.json)
- Step5 ML summary:
  - [ra_v3_named_drug_baseline_ml_summary_20260507_v1.json](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/step5b_ra_ml_sagemaker_20260507_v1/ra-v3-named-drug-baseline-ml-20260507-155014/summary/ra_v3_named_drug_baseline_ml_summary_20260507_v1.json)
- Step6 summary:
  - [step6 summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/step6_ra_external_validation_20260507_v1/step6_ra_external_validation_20260507_v1_summary.json)
- Step7 summary:
  - [step7 summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/step7_ra_admet_filter_20260507_v1/step7_ra_admet_filter_20260507_v1_summary.json)

## Status summary

- Step5:
  - phases run: `phase2a`, `phase2b`
  - models run:
    - `RandomForest`
    - `ExtraTrees`
    - `LightGBM`
    - `XGBoost`
    - `CatBoost`
- Step6:
  - validation cohorts:
    - `GSE89408` primary synovium backbone
    - `GSE55235` external synovium validation
    - `GSE55457` external synovium validation
    - `GSE93272` blood-side support
  - synovium mean same-direction fraction: `0.8525`
  - synovium mean signed spearman: `0.7894`
  - blood support same-direction fraction: `0.5668`
- Step7:
  - all five models kept `30/30` top30 candidates after ADMET gate
  - no hard toxicity-flagged candidate was filtered in the named-drug baseline run

## Interpretation

- Performance favored `phase2a` over `phase2b` for the named-drug baseline branch.
- RA Step6 was implemented as a synovium-first validation layer with blood support kept separate.
- The branch should be treated as the current RA named-drug baseline handoff surface.

## Provenance note

- `step1` and `step2` are copied into this branch as frozen upstream snapshots.
- `step1b` is linked because the expression matrices are large.
- This branch does **not** use the older middle-universe `step4b` or `step5` outputs as downstream inputs.
