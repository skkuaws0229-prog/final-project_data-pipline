# PAH CT-CLIP Cluster Drug Stratification Hypothesis

This analysis reuses the OSIC CT-CLIP image-modal clusters generated in the IPF pipeline. The PAH mapping is a mechanism-of-action hypothesis, not a direct drug-response prediction.

## Cluster Mapping

| Cluster | Label | PAH Interpretation | Key Pathway | Drug Candidates |
|---:|---|---|---|---|
| 0 | Early Vascular Remodeling | Preserved lung function with rapid decline risk | Endothelin + NO/PDE5 pathway | VARDENAFIL, SILDENAFIL, AMBRISENTAN, MACITENTAN, TADALAFIL, BOSENTAN, unnamed lead (CHEMBL304460) |
| 1 | Advanced Vascular Disease | Lower lung function with structural remodeling | Prostacyclin + advanced anti-remodeling | EPOPROSTENOL, ILOPROST, SELEXIPAG, ATRASENTAN |

## Limitations

1. OSIC is a pulmonary fibrosis/ILD CT dataset, not a PAH-specific HRCT cohort.
2. PAH HRCT phenotypes such as pulmonary artery enlargement and mosaic perfusion are not explicitly modeled here.
3. GEO expression patients and OSIC CT patients are different cohorts, so no patient-level linkage is possible.
4. Cluster-drug mapping is based on PAH pathway/MoA knowledge and requires clinical validation.
5. Future work should repeat CT-CLIP clustering on PAH-specific CT data or CT-RATE PAH-filtered cohorts.
