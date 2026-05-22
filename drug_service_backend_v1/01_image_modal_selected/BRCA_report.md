# BRCA Image Cluster Clinical/Mutation Analysis

## Downloads

- GDC clinical cases: 281/281
- cBioPortal PanCancer clinical matched cases: 279
- cBioPortal legacy receptor matched cases: 281
- cBioPortal mutation rows: 207

## Case Coverage

- Clustered TCGA cases: 281
- Cases with OS months: 279
- Cases with subtype: 248

## Stage Distribution (%)

| majority_cluster   |    0 |     I |   IA |   IIA |   IIB |   IIIA |   IIIB |   IIIC |    IV |   Unknown |    X |
|:-------------------|-----:|------:|-----:|------:|------:|-------:|-------:|-------:|------:|----------:|-----:|
| C0                 | 0.78 | 10.85 | 9.3  | 28.68 | 20.16 |  10.85 |   3.1  |   7.75 |  1.55 |      6.98 | 0    |
| C1                 | 0    |  4.55 | 0    | 27.27 | 22.73 |   9.09 |   9.09 |   0    |  9.09 |     13.64 | 4.55 |
| C2                 | 1.65 |  4.96 | 8.26 | 35.54 | 19.83 |  13.22 |   1.65 |   4.13 |  1.65 |      9.09 | 0    |
| C3                 | 0    |  0    | 0    | 33.33 | 22.22 |  11.11 |  22.22 |   0    | 11.11 |      0    | 0    |

## Molecular Subtype Distribution (%)

| majority_cluster   |   BRCA_Basal |   BRCA_Her2 |   BRCA_LumA |   BRCA_LumB |   BRCA_Normal |   Unknown |
|:-------------------|-------------:|------------:|------------:|------------:|--------------:|----------:|
| C0                 |        10.85 |        5.43 |       47.29 |       19.38 |          1.55 |     15.5  |
| C1                 |         0    |        9.09 |       54.55 |       22.73 |          0    |     13.64 |
| C2                 |        19.01 |        7.44 |       40.5  |       19.83 |          4.96 |      8.26 |
| C3                 |        44.44 |        0    |       33.33 |       22.22 |          0    |      0    |

## Mutation Frequency

| majority_cluster   |   n_cases |   TP53_mut_pct |   TP53_mut_n |   PIK3CA_mut_pct |   PIK3CA_mut_n |   BRCA1_mut_pct |   BRCA1_mut_n |   BRCA2_mut_pct |   BRCA2_mut_n |
|:-------------------|----------:|---------------:|-------------:|-----------------:|---------------:|----------------:|--------------:|----------------:|--------------:|
| C0                 |       129 |          25.58 |           33 |            39.53 |             51 |            1.55 |             2 |            1.55 |             2 |
| C1                 |        22 |          31.82 |            7 |            31.82 |              7 |            0    |             0 |            4.55 |             1 |
| C2                 |       121 |          39.67 |           48 |            28.1  |             34 |            2.48 |             3 |            1.65 |             2 |
| C3                 |         9 |          44.44 |            4 |            33.33 |              3 |           11.11 |             1 |            0    |             0 |

## Association Tests

| feature          | test   |     p_value |   dof |
|:-----------------|:-------|------------:|------:|
| HER2_FISH_STATUS | chi2   | 1.58786e-08 |     9 |
| ER_STATUS_BY_IHC | chi2   | 3.80242e-06 |     9 |
| IHC_HER2         | chi2   | 4.44422e-06 |    12 |
| PR_STATUS_BY_IHC | chi2   | 7.99208e-06 |     6 |
| stage_clean      | chi2   | 0.0341292   |    30 |
| TP53_mut         | chi2   | 0.101883    |     3 |
| SUBTYPE          | chi2   | 0.113524    |    15 |
| BRCA1_mut        | chi2   | 0.237707    |     3 |
| PIK3CA_mut       | chi2   | 0.296623    |     3 |
| BRCA2_mut        | chi2   | 0.758776    |     3 |

## Top30 Drug Hypotheses by Cluster

| majority_cluster   |   cluster_n_cases |   drug_rank | drug_name    |   canonical_drug_id | target               | pathway             | rationale                                                                                                              |
|:-------------------|------------------:|------------:|:-------------|--------------------:|:---------------------|:--------------------|:-----------------------------------------------------------------------------------------------------------------------|
| C0                 |               129 |           5 | Temozolomide |                1375 | DNA alkylating agent | DNA replication     | PIK3CA mutation 40%; TP53 mutation 26%; BRCA1/2 mutation 3%                                                            |
| C0                 |               129 |           7 | CZC24832     |                1615 | PI3Kgamma            | PI3K/MTOR signaling | PIK3CA mutation 40%; TP53 mutation 26%; BRCA1/2 mutation 3%                                                            |
| C0                 |               129 |           9 | Oxaliplatin  |                1089 | DNA alkylating agent | DNA replication     | PIK3CA mutation 40%; TP53 mutation 26%; BRCA1/2 mutation 3%                                                            |
| C0                 |               129 |          10 | Fludarabine  |                1813 | Antimetabolite       | DNA replication     | PIK3CA mutation 40%; TP53 mutation 26%; BRCA1/2 mutation 3%                                                            |
| C0                 |               129 |          14 | THR-101      |                2360 | Mutant RAS           | PI3K/MTOR signaling | PIK3CA mutation 40%; TP53 mutation 26%; BRCA1/2 mutation 3%                                                            |
| C0                 |               129 |          18 | Nelarabine   |                1814 | <NA>                 | DNA replication     | PIK3CA mutation 40%; TP53 mutation 26%; BRCA1/2 mutation 3%                                                            |
| C0                 |               129 |          19 | Veliparib    |                1018 | PARP1, PARP2         | Genome integrity    | PIK3CA mutation 40%; TP53 mutation 26%; BRCA1/2 mutation 3%                                                            |
| C0                 |               129 |          20 | MIRA-1       |                1931 | TP53                 | p53 pathway         | PIK3CA mutation 40%; TP53 mutation 26%; BRCA1/2 mutation 3%                                                            |
| C1                 |                22 |           5 | Temozolomide |                1375 | DNA alkylating agent | DNA replication     | PIK3CA mutation 32%; TP53 mutation 32%; BRCA1/2 mutation 5%                                                            |
| C1                 |                22 |           7 | CZC24832     |                1615 | PI3Kgamma            | PI3K/MTOR signaling | PIK3CA mutation 32%; TP53 mutation 32%; BRCA1/2 mutation 5%                                                            |
| C1                 |                22 |           9 | Oxaliplatin  |                1089 | DNA alkylating agent | DNA replication     | PIK3CA mutation 32%; TP53 mutation 32%; BRCA1/2 mutation 5%                                                            |
| C1                 |                22 |          10 | Fludarabine  |                1813 | Antimetabolite       | DNA replication     | PIK3CA mutation 32%; TP53 mutation 32%; BRCA1/2 mutation 5%                                                            |
| C1                 |                22 |          14 | THR-101      |                2360 | Mutant RAS           | PI3K/MTOR signaling | PIK3CA mutation 32%; TP53 mutation 32%; BRCA1/2 mutation 5%                                                            |
| C1                 |                22 |          18 | Nelarabine   |                1814 | <NA>                 | DNA replication     | PIK3CA mutation 32%; TP53 mutation 32%; BRCA1/2 mutation 5%                                                            |
| C1                 |                22 |          19 | Veliparib    |                1018 | PARP1, PARP2         | Genome integrity    | PIK3CA mutation 32%; TP53 mutation 32%; BRCA1/2 mutation 5%                                                            |
| C1                 |                22 |          20 | MIRA-1       |                1931 | TP53                 | p53 pathway         | PIK3CA mutation 32%; TP53 mutation 32%; BRCA1/2 mutation 5%                                                            |
| C2                 |               121 |           5 | Temozolomide |                1375 | DNA alkylating agent | DNA replication     | PIK3CA mutation 28%; TP53 mutation 40%; BRCA1/2 mutation 4%                                                            |
| C2                 |               121 |           7 | CZC24832     |                1615 | PI3Kgamma            | PI3K/MTOR signaling | PIK3CA mutation 28%; TP53 mutation 40%; BRCA1/2 mutation 4%                                                            |
| C2                 |               121 |           9 | Oxaliplatin  |                1089 | DNA alkylating agent | DNA replication     | PIK3CA mutation 28%; TP53 mutation 40%; BRCA1/2 mutation 4%                                                            |
| C2                 |               121 |          10 | Fludarabine  |                1813 | Antimetabolite       | DNA replication     | PIK3CA mutation 28%; TP53 mutation 40%; BRCA1/2 mutation 4%                                                            |
| C2                 |               121 |          14 | THR-101      |                2360 | Mutant RAS           | PI3K/MTOR signaling | PIK3CA mutation 28%; TP53 mutation 40%; BRCA1/2 mutation 4%                                                            |
| C2                 |               121 |          18 | Nelarabine   |                1814 | <NA>                 | DNA replication     | PIK3CA mutation 28%; TP53 mutation 40%; BRCA1/2 mutation 4%                                                            |
| C2                 |               121 |          19 | Veliparib    |                1018 | PARP1, PARP2         | Genome integrity    | PIK3CA mutation 28%; TP53 mutation 40%; BRCA1/2 mutation 4%                                                            |
| C2                 |               121 |          20 | MIRA-1       |                1931 | TP53                 | p53 pathway         | PIK3CA mutation 28%; TP53 mutation 40%; BRCA1/2 mutation 4%                                                            |
| C3                 |                 9 |           5 | Temozolomide |                1375 | DNA alkylating agent | DNA replication     | PIK3CA mutation 33%; TP53 mutation 44%; BRCA1/2 mutation 11%; Basal-enriched subtype {'BRCA_Basal': 4, 'BRCA_LumA': 3} |
| C3                 |                 9 |           7 | CZC24832     |                1615 | PI3Kgamma            | PI3K/MTOR signaling | PIK3CA mutation 33%; TP53 mutation 44%; BRCA1/2 mutation 11%; Basal-enriched subtype {'BRCA_Basal': 4, 'BRCA_LumA': 3} |
| C3                 |                 9 |           9 | Oxaliplatin  |                1089 | DNA alkylating agent | DNA replication     | PIK3CA mutation 33%; TP53 mutation 44%; BRCA1/2 mutation 11%; Basal-enriched subtype {'BRCA_Basal': 4, 'BRCA_LumA': 3} |
| C3                 |                 9 |          10 | Fludarabine  |                1813 | Antimetabolite       | DNA replication     | PIK3CA mutation 33%; TP53 mutation 44%; BRCA1/2 mutation 11%; Basal-enriched subtype {'BRCA_Basal': 4, 'BRCA_LumA': 3} |
| C3                 |                 9 |          12 | CCT007093    |                1067 | PPM1D                | Cell cycle          | PIK3CA mutation 33%; TP53 mutation 44%; BRCA1/2 mutation 11%; Basal-enriched subtype {'BRCA_Basal': 4, 'BRCA_LumA': 3} |
| C3                 |                 9 |          14 | THR-101      |                2360 | Mutant RAS           | PI3K/MTOR signaling | PIK3CA mutation 33%; TP53 mutation 44%; BRCA1/2 mutation 11%; Basal-enriched subtype {'BRCA_Basal': 4, 'BRCA_LumA': 3} |

## Note

Drug links are hypothesis-generating only. They map cluster-enriched subtype/mutation patterns to Top30 drug target/pathway annotations; they are not patient-level response predictions.
