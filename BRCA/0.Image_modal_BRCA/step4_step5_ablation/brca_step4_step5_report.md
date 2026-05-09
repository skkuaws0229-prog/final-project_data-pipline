# BRCA Step 4/5 Local Reranking Report

## Data Matching

- Base unique sample IDs: 29
- TCGA unique case IDs: 281
- Direct matched patient IDs: 0
- Matching note: Base pipeline rows use GDSC BRCA cell-line IDs, while image embeddings come from TCGA WSI patient slides. Direct patient-level matching has 0 rows.

Because direct TCGA patient to GDSC cell-line row matching is zero, image ablation used the BRCA shard00 mean embedding repeated as a cancer-level representative image vector.

## Spearman Change

- cv5: Spearman delta = 0.000000
- groupcv: Spearman delta = 0.000000
- scaffoldcv: Spearman delta = 0.000000

## Ablation Metrics

| experiment          | eval_mode   |   spearman |    rmse |     mae |           r2 |   n_train_total |   n_test_total |   n_folds | model             | image_strategy                                                   |
|:--------------------|:------------|-----------:|--------:|--------:|-------------:|----------------:|---------------:|----------:|:------------------|:-----------------------------------------------------------------|
| baseline_no_image   | cv5         |  0.452019  | 2.25476 | 1.7087  |  0.262339    |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |
| baseline_plus_image | cv5         |  0.452019  | 2.25476 | 1.7087  |  0.262339    |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |
| image_only          | cv5         | -0.0225285 | 2.62587 | 1.97598 | -0.000465035 |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |
| baseline_no_image   | groupcv     |  0.396939  | 2.38113 | 1.79424 |  0.177333    |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |
| baseline_plus_image | groupcv     |  0.396939  | 2.38113 | 1.79424 |  0.177333    |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |
| image_only          | groupcv     | -0.0689198 | 2.63257 | 1.97973 | -0.0055809   |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |
| baseline_no_image   | scaffoldcv  |  0.40162   | 2.40176 | 1.80513 |  0.163016    |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |
| baseline_plus_image | scaffoldcv  |  0.40162   | 2.40176 | 1.80513 |  0.163016    |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |
| image_only          | scaffoldcv  | -0.0973434 | 2.63592 | 1.9822  | -0.00814366  |           30920 |           7730 |         5 | LightGBMRegressor | brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows |

## Top 30 Rank Change

- Top30 drugs with changed rank after image features: 0/30

No Top30 rank changes.

## Feature Importance

- Image feature importance ratio: 0.000000
- Image importance total: 0.000
- Base importance total: 15000.000
