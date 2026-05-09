# External Validation Report

## Scope
Full-fit Step5 models were applied to EV patient features from GSE110147 and GSE150910.
Drug-level ranking is the mean predicted y across patients; lower score is better.

## 2A Ensemble Performance
- GSE110147: Spearman=0.9365, RMSE=0.9640, MAE=0.5722, R2=0.8738
- GSE150910: Spearman=0.9365, RMSE=0.9645, MAE=0.5728, R2=0.8737

## 2A Top30 Overlap
- GSE110147 vs GSE150910: 30/30, Jaccard=1.0000

## Outputs
- `ev_performance_summary_20260504.csv`
- `ev_drug_ranking_GSE110147_20260504.csv`
- `ev_drug_ranking_GSE150910_20260504.csv`
- `ev_top30_overlap_20260504.json`
- `ev_special_drug_ranks_20260504.csv`
- `ev_top30_table_20260504.csv`
