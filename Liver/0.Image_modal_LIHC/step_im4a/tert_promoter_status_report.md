# LIHC TERT promoter mutation status update

## Summary

TERT promoter mutation was reviewed for the LIHC image-modal cluster analysis.
The TCGA LIHC paper reports TERT promoter mutations as the most common somatic
event in the assayed subset: 87 of 196 HCCs analyzed in the promoter region
(44%). However, the current local cBioPortal PanCancer Atlas export used by
this pipeline does not contain patient-level TERT promoter mutation status.

## Current local data finding

- Local LIHC image-modal table patients: 223
- Local LIHC image-modal rows/slides: 223
- cBioPortal default mutation profile TERT coding calls found locally: 2
- Interpretation: these coding calls are not promoter mutations and should not
  be interpreted as the expected 40-60% LIHC TERT promoter signal.

## Pipeline update

- `TERT_promoter_mut` was added to `lihc_cluster_clinical_mutation_table.csv`
  as an explicit unavailable field.
- `cluster_driver_mutation_frequency.csv` and `cluster_mutation_frequency.csv`
  now use the requested driver set:
  TERT promoter, TP53, CTNNB1, AXIN1, ARID1A.
- `cluster_statistical_tests.csv` now includes `TERT_promoter_mut` as
  `not_tested` because patient-level promoter status is unavailable.
- `tert_mutation_cooccurrence.csv` documents that TERT promoter with CTNNB1
  and TP53 co-occurrence/mutual-exclusivity tests were not possible in the
  current data.

## Required future addition

TERT promoter mutation is biologically important in LIHC/HCC and should be
added once a patient-level supplement table can be mapped to the 223 local
TCGA-LIHC patients. Until then, cluster-level TERT promoter frequency,
chi-squared testing, and TERT+CTNNB1 / TERT+TP53 relationship tests are not
quantitatively reported.
