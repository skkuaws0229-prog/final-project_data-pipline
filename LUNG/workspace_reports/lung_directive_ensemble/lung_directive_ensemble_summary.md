# LUNG Directive Ensemble Output

- Source directive: `/Users/skku_aws2_14/Downloads/LUNG_ensemble_directive.md`
- Cancer: `luad`
- Track: `2C_numeric_smiles_context`
- Ensemble: 0.25 XGBoost + 0.22 FTTransformer + 0.20 CatBoost + 0.18 LightGBM + 0.15 ResidualMLP

## Metrics

| eval_mode   |   ensemble_spearman |   ensemble_pearson |   ensemble_kendall_tau |   ensemble_rmse |   ensemble_mae |   ensemble_r2 | best_single_model   |   best_single_spearman |   spearman_gain_vs_best_single |   n_rows |
|:------------|--------------------:|-------------------:|-----------------------:|----------------:|---------------:|--------------:|:--------------------|-----------------------:|-------------------------------:|---------:|
| cv          |              0.8149 |             0.87   |                 0.633  |          1.4163 |         1.0807 |        0.7365 | ResidualMLP         |                 0.827  |                        -0.012  |   125427 |
| groupcv     |              0.4688 |             0.5212 |                 0.3278 |          2.3609 |         1.7821 |        0.2678 | XGBoost             |                 0.4401 |                         0.0287 |   125427 |
| holdout     |              0.8158 |             0.8699 |                 0.6345 |          1.4034 |         1.0679 |        0.7365 | ResidualMLP         |                 0.8303 |                        -0.0145 |    25086 |
| scaffoldcv  |              0.4689 |             0.5273 |                 0.3283 |          2.3516 |         1.7618 |        0.2736 | ResidualMLP         |                 0.4487 |                         0.0203 |   125427 |
| unseen_drug |              0.4463 |             0.5495 |                 0.3119 |          2.3985 |         1.822  |        0.2928 | LightGBM            |                 0.4791 |                        -0.0328 |    24092 |

## Key Readout

- GroupCV Spearman: `0.4688` vs best single `XGBoost` `0.4401`
- ScaffoldCV Spearman: `0.4689` vs best single `ResidualMLP` `0.4487`

## Holdout Top 10 Recommendations

|   rank |   canonical_drug_id | drug_name_display    |   pred_ic50_weighted_mean |   ensemble_member_std_mean |   top_model_vote_count | confidence_grade   |
|-------:|--------------------:|:---------------------|--------------------------:|---------------------------:|-----------------------:|:-------------------|
|      1 |                1817 | Romidepsin           |                   -4.4163 |                     0.9855 |                      5 | C                  |
|      2 |                1941 | Sepantronium bromide |                   -3.7245 |                     0.6388 |                      5 | C                  |
|      3 |                1191 | Bortezomib           |                   -3.7195 |                     1.1134 |                      5 | C                  |
|      4 |                1911 | Dactinomycin         |                   -3.3176 |                     0.8271 |                      5 | C                  |
|      5 |                1007 | Docetaxel            |                   -3.2615 |                     0.6592 |                      5 | C                  |
|      6 |                1819 | Docetaxel            |                   -3.2435 |                     0.6406 |                      5 | C                  |
|      7 |                1811 | Dactinomycin         |                   -3.0493 |                     0.5237 |                      5 | C                  |
|      8 |                1004 | Vinblastine          |                   -2.8313 |                     0.7072 |                      5 | C                  |
|      9 |                2048 | Vinorelbine          |                   -2.769  |                     0.6804 |                      5 | C                  |
|     10 |                1080 | Paclitaxel           |                   -2.6343 |                     0.6039 |                      5 | C                  |

## Unseen Drug Top 10 Recommendations

|   rank |   canonical_drug_id | drug_name_display   |   pred_ic50_weighted_mean |   ensemble_member_std_mean |   top_model_vote_count | confidence_grade   |
|-------:|--------------------:|:--------------------|--------------------------:|---------------------------:|-----------------------:|:-------------------|
|      1 |                1811 | Dactinomycin        |                   -4.0533 |                     0.8652 |                      5 | C                  |
|      2 |                1819 | Docetaxel           |                   -3.7604 |                     0.6366 |                      5 | C                  |
|      3 |                1080 | Paclitaxel          |                   -2.2444 |                     0.8516 |                      5 | C                  |
|      4 |                1026 | Tanespimycin        |                    0.6622 |                     0.9488 |                      3 | C                  |
|      5 |                1809 | Teniposide          |                    1.0416 |                     0.5334 |                      3 | B                  |
|      6 |                1037 | BX795               |                    1.5265 |                     0.7956 |                      2 | C                  |
|      7 |                1058 | Pictilisib          |                    1.7778 |                     0.6519 |                      0 | C                  |
|      8 |                1838 | Sinularin           |                    1.9385 |                     1.4438 |                      1 | C                  |
|      9 |                1086 | BI-2536             |                    2.1204 |                     0.5385 |                      0 | C                  |
|     10 |                1237 | EPZ004777           |                    2.1988 |                     0.3861 |                      0 | C                  |