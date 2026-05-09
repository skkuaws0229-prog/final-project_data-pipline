# HNSC Pipeline Full Summary (2026-04-28)

## Files
- `results/20260427_hnsc_step4_v1/top30_tier1234_fixed_hnsc.csv`
- `external_validation/20260427_hnsc_step4_v1/top30_external_validation_independent.csv`
- `results/20260427_hnsc_step4_v1/step7_top15_hnsc_provisional_with_fixed_tier.csv`
- `results/20260427_hnsc_step4_v1/step7_top30_hnsc_extended.csv`
- `results/20260427_hnsc_step4_v1/step7_top15_hnsc_extended.csv`

## Top30 Fixed Tier1/2/3/4
|   rank | drug_name        | tier   | definition_basis                |
|-------:|:-----------------|:-------|:--------------------------------|
|      1 | Dactinomycin     | Tier2  | 타암종 승인/적응증확장 연구축   |
|      2 | Docetaxel        | Tier1  | 두경부암 승인/표준치료 축       |
|      3 | Vinorelbine      | Tier2  | 타암종 승인/적응증확장 연구축   |
|      4 | Paclitaxel       | Tier1  | 두경부암 승인/표준치료 축       |
|      5 | Temsirolimus     | Tier2  | 타암종 승인/적응증확장 연구축   |
|      6 | Topotecan        | Tier2  | 타암종 승인/적응증확장 연구축   |
|      7 | Vinblastine      | Tier2  | 타암종 승인/적응증확장 연구축   |
|      8 | SN-38            | Tier2  | 타암종 승인/적응증확장 연구축   |
|      9 | Lestaurtinib     | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     10 | SL0101           | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     11 | Teniposide       | Tier2  | 타암종 승인/적응증확장 연구축   |
|     12 | Irinotecan       | Tier2  | 타암종 승인/적응증확장 연구축   |
|     13 | Camptothecin     | Tier4  | 화합물/검증추가필요             |
|     14 | Pyridostatin     | Tier4  | 화합물/검증추가필요             |
|     15 | Schweinfurthin A | Tier4  | 화합물/검증추가필요             |
|     16 | GSK1904529A      | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     17 | Staurosporine    | Tier4  | 화합물/검증추가필요             |
|     18 | Epirubicin       | Tier2  | 타암종 승인/적응증확장 연구축   |
|     19 | Tozasertib       | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     20 | Mitoxantrone     | Tier2  | 타암종 승인/적응증확장 연구축   |
|     21 | MG-132           | Tier4  | 화합물/검증추가필요             |
|     22 | Sabutoclax       | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     23 | AZD5582          | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     24 | Rapamycin        | Tier2  | 타암종 승인/적응증확장 연구축   |
|     25 | AZD2014          | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     26 | Refametinib      | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     27 | LMP744           | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     28 | ZM447439         | Tier3  | 두경부암 미사용 치료제/신규탐색 |
|     29 | Tanespimycin     | Tier2  | 타암종 승인/적응증확장 연구축   |
|     30 | Bleomycin        | Tier1  | 두경부암 승인/표준치료 축       |

## Step6 External Validation Snapshot
|   rank | DRUG_NAME        | prism_status   | clinical_trial_has_evidence   | patient_context_has_evidence   | opentargets_has_evidence   | cosmic_has_evidence   |
|-------:|:-----------------|:---------------|:------------------------------|:-------------------------------|:---------------------------|:----------------------|
|      1 | Dactinomycin     | LIBRARY_ONLY   | True                          | False                          | False                      | False                 |
|      2 | Docetaxel        | NO_MATCH       | True                          | False                          | False                      | True                  |
|      3 | Vinorelbine      | OK             | True                          | False                          | False                      | False                 |
|      4 | Paclitaxel       | OK             | True                          | False                          | False                      | True                  |
|      5 | Temsirolimus     | OK             | True                          | True                           | True                       | False                 |
|      6 | Topotecan        | OK             | True                          | True                           | True                       | False                 |
|      7 | Vinblastine      | OK             | False                         | False                          | False                      | False                 |
|      8 | SN-38            | OK             | False                         | True                           | True                       | False                 |
|      9 | Lestaurtinib     | OK             | False                         | True                           | True                       | False                 |
|     10 | SL0101           | NO_MATCH       | False                         | True                           | True                       | False                 |
|     11 | Teniposide       | OK             | False                         | False                          | False                      | False                 |
|     12 | Irinotecan       | OK             | True                          | True                           | True                       | False                 |
|     13 | Camptothecin     | OK             | True                          | True                           | True                       | False                 |
|     14 | Pyridostatin     | NO_MATCH       | False                         | False                          | False                      | False                 |
|     15 | Schweinfurthin A | NO_MATCH       | False                         | False                          | False                      | False                 |

## Step7 Top15 Provisional + Fixed Tier
|   rank | drug_name        | step6_external_match   | validation_evidence_tier   | step7_decision   |   notes | fixed_tier   |
|-------:|:-----------------|:-----------------------|:---------------------------|:-----------------|--------:|:-------------|
|      1 | Dactinomycin     | matched                | VT3                        | KEEP_TOP15       |     nan | Tier2        |
|      2 | Docetaxel        | matched                | VT3                        | KEEP_TOP15       |     nan | Tier1        |
|      3 | Vinorelbine      | matched                | VT3                        | KEEP_TOP15       |     nan | Tier2        |
|      4 | Paclitaxel       | matched                | VT3                        | KEEP_TOP15       |     nan | Tier1        |
|      5 | Temsirolimus     | matched                | VT3                        | KEEP_TOP15       |     nan | Tier2        |
|      6 | Topotecan        | matched                | VT3                        | KEEP_TOP15       |     nan | Tier2        |
|      7 | Vinblastine      | unmatched              | VT3                        | REVIEW           |     nan | Tier2        |
|      8 | SN-38            | matched                | VT3                        | KEEP_TOP15       |     nan | Tier2        |
|      9 | Lestaurtinib     | matched                | VT3                        | KEEP_TOP15       |     nan | Tier3        |
|     10 | SL0101           | matched                | VT3                        | KEEP_TOP15       |     nan | Tier3        |
|     11 | Teniposide       | unmatched              | VT3                        | REVIEW           |     nan | Tier2        |
|     12 | Irinotecan       | matched                | VT3                        | KEEP_TOP15       |     nan | Tier2        |
|     13 | Camptothecin     | matched                | VT3                        | KEEP_TOP15       |     nan | Tier4        |
|     14 | Pyridostatin     | unmatched              | VT3                        | REVIEW           |     nan | Tier4        |
|     15 | Schweinfurthin A | unmatched              | VT3                        | REVIEW           |     nan | Tier4        |

## Step7 Extended Top30 (All Rows)
|   rank | drug_name        | tier   | definition_basis                | prism_status   |   clinical_trial_has_evidence |   patient_context_has_evidence |   opentargets_has_evidence |   cosmic_has_evidence | external_any_support   | external_data_status   | step7_extended_decision   |
|-------:|:-----------------|:-------|:--------------------------------|:---------------|------------------------------:|-------------------------------:|---------------------------:|----------------------:|:-----------------------|:-----------------------|:--------------------------|
|      1 | Dactinomycin     | Tier2  | 타암종 승인/적응증확장 연구축   | LIBRARY_ONLY   |                             1 |                              0 |                          0 |                     0 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      2 | Docetaxel        | Tier1  | 두경부암 승인/표준치료 축       | NO_MATCH       |                             1 |                              0 |                          0 |                     1 | True                   | HAS_SOURCE_ROWS        | PRIORITY_1                |
|      3 | Vinorelbine      | Tier2  | 타암종 승인/적응증확장 연구축   | OK             |                             1 |                              0 |                          0 |                     0 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      4 | Paclitaxel       | Tier1  | 두경부암 승인/표준치료 축       | OK             |                             1 |                              0 |                          0 |                     1 | True                   | HAS_SOURCE_ROWS        | PRIORITY_1                |
|      5 | Temsirolimus     | Tier2  | 타암종 승인/적응증확장 연구축   | OK             |                             1 |                              1 |                          1 |                     0 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      6 | Topotecan        | Tier2  | 타암종 승인/적응증확장 연구축   | OK             |                             1 |                              1 |                          1 |                     0 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      7 | Vinblastine      | Tier2  | 타암종 승인/적응증확장 연구축   | OK             |                             0 |                              0 |                          0 |                     0 | False                  | HAS_SOURCE_ROWS        | REVIEW                    |
|      8 | SN-38            | Tier2  | 타암종 승인/적응증확장 연구축   | OK             |                             0 |                              1 |                          1 |                     0 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      9 | Lestaurtinib     | Tier3  | 두경부암 미사용 치료제/신규탐색 | OK             |                             0 |                              1 |                          1 |                     0 | True                   | HAS_SOURCE_ROWS        | EXPLORE                   |
|     10 | SL0101           | Tier3  | 두경부암 미사용 치료제/신규탐색 | NO_MATCH       |                             0 |                              1 |                          1 |                     0 | True                   | HAS_SOURCE_ROWS        | EXPLORE                   |
|     11 | Teniposide       | Tier2  | 타암종 승인/적응증확장 연구축   | OK             |                             0 |                              0 |                          0 |                     0 | False                  | HAS_SOURCE_ROWS        | REVIEW                    |
|     12 | Irinotecan       | Tier2  | 타암종 승인/적응증확장 연구축   | OK             |                             1 |                              1 |                          1 |                     0 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|     13 | Camptothecin     | Tier4  | 화합물/검증추가필요             | OK             |                             1 |                              1 |                          1 |                     0 | True                   | HAS_SOURCE_ROWS        | REVIEW                    |
|     14 | Pyridostatin     | Tier4  | 화합물/검증추가필요             | NO_MATCH       |                             0 |                              0 |                          0 |                     0 | False                  | HAS_SOURCE_ROWS        | REVIEW                    |
|     15 | Schweinfurthin A | Tier4  | 화합물/검증추가필요             | NO_MATCH       |                             0 |                              0 |                          0 |                     0 | False                  | HAS_SOURCE_ROWS        | REVIEW                    |
|     16 | GSK1904529A      | Tier3  | 두경부암 미사용 치료제/신규탐색 | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     17 | Staurosporine    | Tier4  | 화합물/검증추가필요             | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     18 | Epirubicin       | Tier2  | 타암종 승인/적응증확장 연구축   | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     19 | Tozasertib       | Tier3  | 두경부암 미사용 치료제/신규탐색 | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     20 | Mitoxantrone     | Tier2  | 타암종 승인/적응증확장 연구축   | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     21 | MG-132           | Tier4  | 화합물/검증추가필요             | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     22 | Sabutoclax       | Tier3  | 두경부암 미사용 치료제/신규탐색 | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     23 | AZD5582          | Tier3  | 두경부암 미사용 치료제/신규탐색 | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     24 | Rapamycin        | Tier2  | 타암종 승인/적응증확장 연구축   | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     25 | AZD2014          | Tier3  | 두경부암 미사용 치료제/신규탐색 | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     26 | Refametinib      | Tier3  | 두경부암 미사용 치료제/신규탐색 | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     27 | LMP744           | Tier3  | 두경부암 미사용 치료제/신규탐색 | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     28 | ZM447439         | Tier3  | 두경부암 미사용 치료제/신규탐색 | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     29 | Tanespimycin     | Tier2  | 타암종 승인/적응증확장 연구축   | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |
|     30 | Bleomycin        | Tier1  | 두경부암 승인/표준치료 축       | nan            |                           nan |                            nan |                        nan |                   nan | False                  | PARTIAL_OR_UNKNOWN     | REVIEW                    |

## Step7 Extended Top15
|   rank | drug_name        | tier   | definition_basis                | prism_status   | clinical_trial_has_evidence   | patient_context_has_evidence   | opentargets_has_evidence   | cosmic_has_evidence   | external_any_support   | external_data_status   | step7_extended_decision   |
|-------:|:-----------------|:-------|:--------------------------------|:---------------|:------------------------------|:-------------------------------|:---------------------------|:----------------------|:-----------------------|:-----------------------|:--------------------------|
|      1 | Dactinomycin     | Tier2  | 타암종 승인/적응증확장 연구축   | LIBRARY_ONLY   | True                          | False                          | False                      | False                 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      2 | Docetaxel        | Tier1  | 두경부암 승인/표준치료 축       | NO_MATCH       | True                          | False                          | False                      | True                  | True                   | HAS_SOURCE_ROWS        | PRIORITY_1                |
|      3 | Vinorelbine      | Tier2  | 타암종 승인/적응증확장 연구축   | OK             | True                          | False                          | False                      | False                 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      4 | Paclitaxel       | Tier1  | 두경부암 승인/표준치료 축       | OK             | True                          | False                          | False                      | True                  | True                   | HAS_SOURCE_ROWS        | PRIORITY_1                |
|      5 | Temsirolimus     | Tier2  | 타암종 승인/적응증확장 연구축   | OK             | True                          | True                           | True                       | False                 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      6 | Topotecan        | Tier2  | 타암종 승인/적응증확장 연구축   | OK             | True                          | True                           | True                       | False                 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      7 | Vinblastine      | Tier2  | 타암종 승인/적응증확장 연구축   | OK             | False                         | False                          | False                      | False                 | False                  | HAS_SOURCE_ROWS        | REVIEW                    |
|      8 | SN-38            | Tier2  | 타암종 승인/적응증확장 연구축   | OK             | False                         | True                           | True                       | False                 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|      9 | Lestaurtinib     | Tier3  | 두경부암 미사용 치료제/신규탐색 | OK             | False                         | True                           | True                       | False                 | True                   | HAS_SOURCE_ROWS        | EXPLORE                   |
|     10 | SL0101           | Tier3  | 두경부암 미사용 치료제/신규탐색 | NO_MATCH       | False                         | True                           | True                       | False                 | True                   | HAS_SOURCE_ROWS        | EXPLORE                   |
|     11 | Teniposide       | Tier2  | 타암종 승인/적응증확장 연구축   | OK             | False                         | False                          | False                      | False                 | False                  | HAS_SOURCE_ROWS        | REVIEW                    |
|     12 | Irinotecan       | Tier2  | 타암종 승인/적응증확장 연구축   | OK             | True                          | True                           | True                       | False                 | True                   | HAS_SOURCE_ROWS        | PRIORITY_2                |
|     13 | Camptothecin     | Tier4  | 화합물/검증추가필요             | OK             | True                          | True                           | True                       | False                 | True                   | HAS_SOURCE_ROWS        | REVIEW                    |
|     14 | Pyridostatin     | Tier4  | 화합물/검증추가필요             | NO_MATCH       | False                         | False                          | False                      | False                 | False                  | HAS_SOURCE_ROWS        | REVIEW                    |
|     15 | Schweinfurthin A | Tier4  | 화합물/검증추가필요             | NO_MATCH       | False                         | False                          | False                      | False                 | False                  | HAS_SOURCE_ROWS        | REVIEW                    |
