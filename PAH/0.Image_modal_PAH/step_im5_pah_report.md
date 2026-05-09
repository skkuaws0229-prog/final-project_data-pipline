# PAH Image Modal Report

## Reused OSIC CT-CLIP Outputs

- CT-CLIP embeddings: `step_im2/ct_clip_embeddings_176.parquet`
- Patient clusters: `step_im3/patient_clusters.csv`
- Clustering optimization: `step_im3/clustering_optimization.csv`
- Clinical association and validation outputs: `step_im4a/`, `step_im4b/`

## PAH-Specific IM-4C Mapping

- Input PAH final drug list: `step7_admet_final_15_tiered_20260506.csv`
- Mapped drugs: 11
- Cluster 0: early vascular remodeling, endothelin and NO/PDE5 pathway hypothesis.
- Cluster 1: advanced vascular disease, prostacyclin and anti-remodeling hypothesis.

## Output Files

- `im4c_pah_cluster_drug_mapping.csv`
- `im4c_pah_stratification_hypothesis.md`
- `step_im5_pah_report.md`

## Important Caveat

This is a stratification hypothesis only. OSIC is not a PAH CT cohort, and no direct drug-response labels are available.
