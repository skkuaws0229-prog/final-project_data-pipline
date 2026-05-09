# Psoriasis Baseline Final Handoff (2026-05-07)

## Canonical branch

- root:
  - [/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata)
- universe:
  - 138 named drugs
- canonical lineage:
  - Step0 through Step4 branch-native
  - Step5 rerun on SageMaker
  - Step6/6b/7 rerun specifically for the baseline branch

## Current branch-of-record artifacts

- lineage manifest:
  - [psoriasis_v2_baseline_lineage_manifest_20260507_v1.json](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/psoriasis_v2_baseline_lineage_manifest_20260507_v1.json)
- Step5 ML summary:
  - [psoriasis_v2_baseline_ml_summary_20260507_v1.json](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/step5b_psoriasis_ml_sagemaker_20260507_v1/psoriasis-v2-baseline-ml-20260507-152948/summary/psoriasis_v2_baseline_ml_summary_20260507_v1.json)
- Step6 summary:
  - [step6 summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/step6_psoriasis_external_validation_20260507_v2_baseline/step6_psoriasis_external_validation_20260507_v2_baseline_summary.json)
- Step6b summary:
  - [step6b summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/step6b_psoriasis_molecular_validation_20260507_v2_baseline/step6b_psoriasis_molecular_validation_20260507_v2_baseline_summary.json)
- Step7 summary:
  - [step7 summary](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/step7_psoriasis_admet_filter_20260507_v2_baseline/step7_psoriasis_admet_filter_20260507_v2_baseline_summary.json)

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
  - direct validation cohorts: `GSE69967`, `GSE106992`, `GSE117239`
  - same-axis cohort: `GSE136757`
  - direct validation drugs in strict label space: `1`
- Step6b:
  - direct Tofacitinib recovery delta vs placebo: `0.5121`
  - same-axis day28 recovery delta vs placebo: `0.8565`
- Step7:
  - all five models kept `30/30` top30 candidates after ADMET gate
  - no hard toxicity-flagged candidate was filtered in the baseline run

## Interpretation

- Performance favored `phase2a` over `phase2b` for the baseline branch.
- The downstream validation stack was therefore executed as a `phase2a`-first interpretation layer.
- The branch is self-consistent and should be treated as the current psoriasis baseline handoff surface.

## Non-canonical but preserved

These directories remain in the root for history, but they are not the current branch-of-record for downstream baseline interpretation:

- `step5_psoriasis_ml_all_20260504_v2`
- `step5_psoriasis_dl_all_20260504_v2`
- `step5_psoriasis_graph_all_20260504_v2`
- `step5_fullrun_logs_20260504_v2`
