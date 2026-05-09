# LUAD Image Modal Downstream Report

## Embedding Merge
- Actual merged matrix: `250 x 1536`
- NaN: `0`, +Inf: `0`, -Inf: `0`
- Note: request expected 254 rows; available LUAD Step3 parquet contains 250 rows.

## Clustering
- Best K: `3` by silhouette.
- Silhouette table: `step_im3/clustering_optimization.csv`

## Clinical / Mutation
- Source: cBioPortal TCGA-LUAD PanCancer Atlas 2018 API.
- Driver genes: EGFR, KRAS, ALK, STK11, KEAP1, TP53.
- Survival log-rank p-value: `0.44125538906000183`
- Molecular subtype uses cBioPortal `SUBTYPE` when present; otherwise driver-proxy labels are used.

## Drug Mapping
- LUNG Top30 candidates were connected to WSI clusters by target/MoA/pathway keyword overlap and existing LUNG tier evidence.
- This is a stratification hypothesis only, not direct patient-level drug-response inference.

## WSI Cleanup
- Raw WSI deletion was not executed automatically because it is destructive.
- Suggested cleanup commands are in `step_im5/s3_cleanup_manifest.json`.
