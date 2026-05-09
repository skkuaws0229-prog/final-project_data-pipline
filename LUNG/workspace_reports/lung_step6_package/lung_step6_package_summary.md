# LUNG Step6 Package

- Status date: 2026-04-29
- Ensemble source: `reports/lung_directive_ensemble/lung_directive_ensemble_top30_unseen_drug_finalized.csv`
- Scope: deduped 30-drug package before Step6 external validation / Step7 ADMET

## Candidate Summary

- Candidate count: `30`
- Unique drug names: `30`
- Canonical SMILES coverage: `30/30`
- Tier coverage: `30/30`

## Tier Count

| Tier | Count |
| --- | ---: |
| LUNG 치료제 | 3 |
| 타암 치료제 + LUNG 적응증 확장 연구 | 2 |
| LUNG 미사용 치료제 | 3 |
| 화합물 / 확인 필요 약물 | 22 |

## Top30 Tiered Candidates

|   rank | tier_code   | drug_name_display   |   pred_ic50_weighted_mean | confidence_grade   |   ct_match_count | prism_phase   |
|-------:|:------------|:--------------------|--------------------------:|:-------------------|-----------------:|:--------------|
|      1 | Tier3       | Dactinomycin        |                   -4.0533 | C                  |                0 | Launched      |
|      2 | Tier1       | Docetaxel           |                   -3.7604 | C                  |              423 | Launched      |
|      3 | Tier1       | Paclitaxel          |                   -2.2444 | C                  |              489 | Launched      |
|      4 | Tier4       | Tanespimycin        |                    0.6622 | C                  |                1 | Phase 3       |
|      5 | Tier3       | Teniposide          |                    1.0416 | B                  |                0 | Launched      |
|      6 | Tier4       | BX795               |                    1.5265 | C                  |                0 |               |
|      7 | Tier4       | Pictilisib          |                    1.7778 | C                  |                0 |               |
|      8 | Tier4       | Sinularin           |                    1.9385 | C                  |                0 |               |
|      9 | Tier4       | BI-2536             |                    2.1204 | B                  |                0 |               |
|     10 | Tier4       | EPZ004777           |                    2.1988 | B                  |                0 | Preclinical   |
|     11 | Tier4       | Bleomycin (50 uM)   |                    2.3972 | A                  |                0 |               |
|     12 | Tier4       | Entinostat          |                    2.4012 | B                  |               13 | Phase 3       |
|     13 | Tier4       | EPZ5676             |                    2.4992 | C                  |                0 |               |
|     14 | Tier4       | UNC0379             |                    2.5675 | C                  |                0 |               |
|     15 | Tier4       | SGC-CBP30           |                    2.5934 | B                  |                0 |               |
|     16 | Tier4       | AZD8055             |                    2.6519 | C                  |                0 |               |
|     17 | Tier4       | Buparlisib          |                    2.6604 | B                  |                0 |               |
|     18 | Tier4       | Elesclomol          |                    2.7993 | C                  |                0 |               |
|     19 | Tier2       | Venetoclax          |                    2.8153 | B                  |                0 |               |
|     20 | Tier3       | Methotrexate        |                    2.8239 | C                  |                0 |               |
|     21 | Tier4       | OF-1                |                    2.8324 | A                  |                0 |               |
|     22 | Tier4       | GSK343              |                    2.8715 | A                  |                0 |               |
|     23 | Tier2       | Bortezomib          |                    2.9094 | C                  |                0 |               |
|     24 | Tier1       | Savolitinib         |                    2.9153 | C                  |                0 |               |
|     25 | Tier4       | PFI3                |                    2.9464 | C                  |                0 |               |
|     26 | Tier4       | IOX2                |                    2.9629 | B                  |                0 |               |
|     27 | Tier4       | NVP-ADW742          |                    3.2943 | C                  |                0 |               |
|     28 | Tier4       | KU-55933            |                    3.2998 | B                  |                0 |               |
|     29 | Tier4       | Piperlongumine      |                    3.3375 | C                  |                0 |               |
|     30 | Tier4       | Doramapimod         |                    3.3906 | B                  |                0 |               |

## External Validation Asset Checks

| check_id                        | exists   | path                                                                                                                                                                                                                                                          |   size_bytes |
|:--------------------------------|:---------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------:|
| top30_dedup_csv                 | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/reports/lung_directive_ensemble/lung_directive_ensemble_top30_unseen_drug_finalized.csv                                                       |        15360 |
| drug_features_parquet           | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/data/drug_features.parquet                                                                                 |        26852 |
| gdsc_annotation_parquet         | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/processed/gdsc_annotation.parquet                                                             |        27494 |
| clinicaltrials_all_studies_json | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/validation/clinicaltrials/clinicaltrials_lung_cancer_all_studies.json                         |    403111145 |
| clinicaltrials_summary_json     | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/validation/clinicaltrials/clinicaltrials_lung_cancer_summary.json                             |           68 |
| prism_treatment_info_csv        | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/validation/prism/prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv |      1312286 |
| prism_cell_line_info_csv        | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/validation/prism/prism-repurposing-20q2-primary-screen-cell-line-info.csv                     |        46849 |
| cosmic_actionability_tar        | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/validation/cosmic/Actionability_AllData_Tsv_v19_GRCh37.tar                                    |      5918720 |
| cosmic_cgc_tar                  | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/validation/cosmic/Cosmic_CancerGeneCensus_Tsv_v103_GRCh38.tar                                 |        71680 |
| cptac_mrna_file                 | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/cptac/lusc_cptac_2021/data_mrna_seq_fpkm.txt                                                  |     17089875 |
| cptac_clinical_patient_file     | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/curated_data/cptac/luad_cptac_2020/data_clinical_patient.txt                                               |        23397 |
| prior_ct_results_json           | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/results/lung_clinical_trials_validation_results.json                                                       |          403 |
| prior_prism_results_json        | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/results/lung_prism_validation_results.json                                                                 |          424 |
| prior_cosmic_results_json       | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/results/lung_cosmic_validation_results.json                                                                |          182 |
| prior_cptac_results_json        | True     | /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260416_new_pre_project_biso_Lung/results/lung_cptac_validation_results.json                                                                 |          194 |

## Decision

- ready_to_start_step6_external_validation: **True**
- ready_to_enter_step7_now: **False**
- blocker: Current Top30 has been deduped and tiered, but Step6 external validation has not yet been rerun on this exact package.

## Tier Notes

- Tier1: 현재 lung 치료 맥락에 직접 연결되는 약물
- Tier2: 다른 암종 치료제로 사용 중이며 lung 적응증 확장/연구 흔적이 있는 약물
- Tier3: 승인 치료제지만 lung 직접 사용 근거가 현재 패키지 기준 제한적인 약물
- Tier4: 비승인 화합물, probe compound, 개발 코드명, 또는 추가 확인이 필요한 약물