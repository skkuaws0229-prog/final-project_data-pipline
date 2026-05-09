# LUNG Finalized Top30

- Source: `reports/lung_directive_ensemble/lung_directive_ensemble_predictions_detailed.csv`
- Rule: `unseen_drug` rank ascending, unique drug name, `canonical_smiles` required

## Summary

- Finalized candidate count: `30`
- Unique names: `30`
- Canonical SMILES coverage: `30/30`

## Replacement Notes

- Skipped `TAF1_5496` (raw rank 16) because `canonical_smiles` was missing.
- Final slot filled by `Doramapimod` from raw rank `31`.

## Finalized Top30

|   dedup_rank |   raw_rank | drug_name_display   |   pred_ic50_weighted_mean | confidence_grade   |
|-------------:|-----------:|:--------------------|--------------------------:|:-------------------|
|            1 |          1 | Dactinomycin        |                   -4.0533 | C                  |
|            2 |          2 | Docetaxel           |                   -3.7604 | C                  |
|            3 |          3 | Paclitaxel          |                   -2.2444 | C                  |
|            4 |          4 | Tanespimycin        |                    0.6622 | C                  |
|            5 |          5 | Teniposide          |                    1.0416 | B                  |
|            6 |          6 | BX795               |                    1.5265 | C                  |
|            7 |          7 | Pictilisib          |                    1.7778 | C                  |
|            8 |          8 | Sinularin           |                    1.9385 | C                  |
|            9 |          9 | BI-2536             |                    2.1204 | B                  |
|           10 |         10 | EPZ004777           |                    2.1988 | B                  |
|           11 |         11 | Bleomycin (50 uM)   |                    2.3972 | A                  |
|           12 |         12 | Entinostat          |                    2.4012 | B                  |
|           13 |         13 | EPZ5676             |                    2.4992 | C                  |
|           14 |         14 | UNC0379             |                    2.5675 | C                  |
|           15 |         15 | SGC-CBP30           |                    2.5934 | B                  |
|           16 |         17 | AZD8055             |                    2.6519 | C                  |
|           17 |         18 | Buparlisib          |                    2.6604 | B                  |
|           18 |         19 | Elesclomol          |                    2.7993 | C                  |
|           19 |         20 | Venetoclax          |                    2.8153 | B                  |
|           20 |         21 | Methotrexate        |                    2.8239 | C                  |
|           21 |         22 | OF-1                |                    2.8324 | A                  |
|           22 |         23 | GSK343              |                    2.8715 | A                  |
|           23 |         24 | Bortezomib          |                    2.9094 | C                  |
|           24 |         25 | Savolitinib         |                    2.9153 | C                  |
|           25 |         26 | PFI3                |                    2.9464 | C                  |
|           26 |         27 | IOX2                |                    2.9629 | B                  |
|           27 |         28 | NVP-ADW742          |                    3.2943 | C                  |
|           28 |         29 | KU-55933            |                    3.2998 | B                  |
|           29 |         30 | Piperlongumine      |                    3.3375 | C                  |
|           30 |         31 | Doramapimod         |                    3.3906 | B                  |