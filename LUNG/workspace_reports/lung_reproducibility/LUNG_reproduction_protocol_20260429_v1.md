# LUNG Reproduction Protocol

- Date: 2026-04-29
- Version: v1
- Scope: reproduce the current LUNG/LUAD rerun from Step5 ensemble through Step7 ADMET
- Extended scope: allow Step0 raw-source bootstrap from the current LUNG workspace S3 mirror

## Canonical scope

- Disease scope: `All Lung` dataset as currently processed in `20260416_new_pre_project_biso_Lung`
- Modeling scope: `LUAD`, `2C_numeric_smiles_context`
- Step5 ensemble: directive ensemble based on 5 selected models
- Step6 external validation: `PRISM + ClinicalTrials.gov + COSMIC + CPTAC`
- Step7 safety gate: current LUNG ADMET gate in `step7_0/1/2`

## Fixed decisions

- Current Step5 ensemble members:
  - `XGBoost 0.25`
  - `FTTransformer 0.22`
  - `CatBoost 0.20`
  - `LightGBM 0.18`
  - `ResidualMLP 0.15`
- `TabTransformer` excluded due to high redundancy with other transformer-family DL models
- Current Top30 basis: `unseen_drug`
- Current Top30 rule: deduplicated by drug name, `canonical_smiles` required
- Current replacement decision: `TAF1_5496` kept as `Tier4` research compound but excluded from final Top30 because `canonical_smiles` missing; replaced by `Doramapimod`
- Current Step7 input: all 30 finalized drugs
- Final candidate cut: top 15 after Step7 ranking

## Key inputs

- Step4 ML outputs:
  - `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/ml_step4_1/luad/2C_numeric_smiles_context/`
- Step4 DL outputs:
  - `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_models/fs_a_stad_baseline/dl_step4_2_7model_full/luad/2C_numeric_smiles_context/`
- Step4 feature-track built inputs:
  - `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/step4_feature_tracks/built_inputs/2C_numeric_smiles_context/luad/`
- LUNG project root:
  - `20260416_new_pre_project_biso_Lung/`
- Current workspace reports:
  - `reports/lung_directive_ensemble/`
  - `reports/lung_step6_package/`
  - `reports/lung_step6_current_package/`

## Reproduction order

0. Optional Step0 raw-source bootstrap
   - Read-only raw source mirror path:
     - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/raw_source_snapshot/Lung_raw/`
   - Restore the Step0 raw package into local `curated_data/` layout:
     - `./scripts/bootstrap_lung_step0_raw_from_s3.sh /path/to/workspace-root s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG`
   - Source policy:
     - original `s3://say2-4team/Lung_raw/` is treated as read-only and is never modified or deleted

1. Bootstrap current rerun package from S3
   - Environment guide:
     - `reports/lung_reproducibility/LUNG_repro_environment_20260429.md`
   - Restore current package from S3:
     - `./scripts/bootstrap_lung_repro_from_s3.sh /path/to/workspace-root s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG`
   - Assumption:
     - local directory names are restored to the same relative layout used in this protocol

2. Step5 ensemble rerun
   - Command: `python3 scripts/build_lung_directive_ensemble.py`
   - Outputs:
     - `reports/lung_directive_ensemble/lung_directive_ensemble_metrics.csv`
     - `reports/lung_directive_ensemble/lung_directive_ensemble_predictions_detailed.csv`
     - `reports/lung_directive_ensemble/lung_directive_ensemble_top30_by_eval_mode.csv`

3. Finalize current Top30
   - Command: `python3 scripts/finalize_lung_top30.py`
   - Rule:
     - `eval_mode = unseen_drug`
     - ascending `pred_ic50_weighted_mean`
     - deduplicate by normalized drug name
     - keep only drugs with `canonical_smiles`
   - Outputs:
     - `reports/lung_directive_ensemble/lung_directive_ensemble_top30_unseen_drug_finalized.csv`
     - `reports/lung_directive_ensemble/lung_directive_ensemble_top30_unseen_drug_finalization_audit.csv`

4. Tier classification and Step6 package
   - Command: `python3 scripts/prepare_lung_step6_package.py`
   - Outputs:
     - `reports/lung_step6_package/lung_step6_top30_tiered_candidates.csv`
     - `reports/lung_step6_package/lung_step6_external_validation_readiness_summary.json`

5. Step6 current-package rerun
   - Command: `python3 scripts/run_lung_step6_current_package.py`
   - Outputs:
     - `reports/lung_step6_current_package/`
     - `20260416_new_pre_project_biso_Lung/results/lung_final_drug_ranking_with_scores.csv`
     - `20260416_new_pre_project_biso_Lung/results/lung_final_drug_ranking_dedup.csv`

6. Step7 duplicate cleanup
   - Command:
     - `cd 20260416_new_pre_project_biso_Lung`
     - `python3 step7_0_remove_duplicates.py`

7. Step7 ADMET rerun
   - Command:
     - `cd 20260416_new_pre_project_biso_Lung`
     - `python3 step7_1_admet_filtering.py`

8. Step7 final top15 selection
   - Command:
     - `cd 20260416_new_pre_project_biso_Lung`
     - `python3 step7_2_select_top15.py`

## Current acceptance view

- Step5 current Top30: `30`
- Step5 SMILES coverage after finalization: `30/30`
- Step6 external validation current counts:
  - PRISM matched drugs: `19`
  - ClinicalTrials matched drugs: `10`
  - COSMIC matched drugs: `12`
  - CPTAC expression-supported drugs: `13`
- Step7 ADMET:
  - PASS: `28`
  - WARNING: `0`
  - FAIL: `2`
- Current Step7 fail drugs:
  - `Venetoclax`
  - `Bleomycin (50 uM)`

## Current Final Top15

| Rank | Drug | Usage Category | ADMET | Confidence |
| ---: | --- | --- | --- | ---: |
| 1 | Docetaxel | FDA_APPROVED_LUNG | PASS | 75 |
| 2 | Paclitaxel | FDA_APPROVED_LUNG | PASS | 75 |
| 3 | Savolitinib | FDA_APPROVED_LUNG | PASS | 75 |
| 4 | Entinostat | RESEARCH_PHASE | PASS | 100 |
| 5 | Tanespimycin | RESEARCH_PHASE | PASS | 75 |
| 6 | Bortezomib | CLINICAL_TRIAL | PASS | 75 |
| 7 | Methotrexate | CLINICAL_TRIAL | PASS | 75 |
| 8 | Buparlisib | CLINICAL_TRIAL | PASS | 75 |
| 9 | Pictilisib | CLINICAL_TRIAL | PASS | 50 |
| 10 | Dactinomycin | REPURPOSING_CANDIDATE | PASS | 50 |
| 11 | EPZ004777 | REPURPOSING_CANDIDATE | PASS | 50 |
| 12 | Teniposide | REPURPOSING_CANDIDATE | PASS | 50 |
| 13 | IOX2 | REPURPOSING_CANDIDATE | PASS | 50 |
| 14 | BI-2536 | REPURPOSING_CANDIDATE | PASS | 50 |
| 15 | EPZ5676 | REPURPOSING_CANDIDATE | PASS | 25 |

## Notes

- This protocol captures the current rerun, not the older `41-drug` Step7 execution.
- `20260416_new_pre_project_biso_Lung/results/` now contains the current rerun Step6-Step7 outputs that should be treated as canonical for this turn.
- `All Lung` remains the current official scope. `NSCLC-only` is still a possible future sensitivity rerun, not the current canonical result.
