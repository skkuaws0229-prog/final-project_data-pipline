# LIHC TERT expression and copy-number update

## What was added

- TERT mRNA expression from cBioPortal TCGA-LIHC PanCancer Atlas RNA-seq.
- TERT mRNA z-scores, using diploid samples as the primary comparison scale.
- TERT GISTIC copy-number calls and log2 copy-number values.
- Cluster-level expression, copy-number, and survival-link summary tables.

## Key result

- Highest TERT mRNA cluster: cluster 1
- Median TERT mRNA z-score in highest cluster: -0.2054

## Files

- `cluster_tert_expression_stats.csv`
- `cluster_tert_cna_stats.csv`
- `cluster_tert_expression_survival_link.csv`
- `tert_expression_cna_statistical_tests.csv`
- `cluster_tert_mrna_expression_boxplot.png`
- `tert_expression_cna_summary.json`

## Note

This complements, but does not replace, TERT promoter mutation analysis.
Patient-level TERT promoter mutation status remains unavailable in the current
cBioPortal default mutation/clinical export, so mRNA expression is used here as
a telomerase activity proxy.
