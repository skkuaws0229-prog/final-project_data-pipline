# LIHC Image Modal Downstream Report

## Embedding Merge
- Actual merged matrix: `223 x 1536`
- NaN: `0`, +Inf: `0`, -Inf: `0`
- Note: available LIHC Step3 parquet contains the successfully embedded slide rows.

## Clustering
- Best K: `3` by silhouette.
- Silhouette table: `step_im3/clustering_optimization.csv`

## Clinical / Mutation
- Source: cBioPortal TCGA-LIHC PanCancer Atlas 2018 API.
- Driver genes: TERT, TP53, CTNNB1, AXIN1, ARID1A, ALB.
- Survival log-rank p-value: `2.8980287572812305e-14`
- Molecular subtype uses cBioPortal `SUBTYPE` when present; otherwise driver-proxy labels are used.

## Drug Mapping
- Liver/LIHC Top30 candidates were connected to WSI clusters by target/MoA/pathway keyword overlap and existing LIHC tier evidence.
- This is a stratification hypothesis only, not direct patient-level drug-response inference.

## WSI Cleanup
- Raw WSI deletion was not executed automatically because it is destructive.
- Suggested cleanup commands are in `step_im5/s3_cleanup_manifest.json`.
