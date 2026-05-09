# STAD Image Modal Step4 Summary

- Slide embedding shape: [225, 1536]
- Patient embedding shape: [225, 1536]
- NaN/Inf: 0 / 0
- Best k: 3
- Silhouette: 0.1515
- Top30 4-tier counts: {'Tier3': 14, 'Tier2': 10, 'Tier1': 3, 'Tier4': 3}
- Cluster-drug linkage rows: 39

## Statistical Tests

| variable                 | test        |       p_value |       chi2 |   dof |
|:-------------------------|:------------|--------------:|-----------:|------:|
| ajcc_stage               | chi_squared |   1.07045e-06 |  65.2354   |    20 |
| path_t_stage             | chi_squared |   9.2036e-05  |  55.7768   |    22 |
| path_n_stage             | chi_squared |   0.0016741   |  34.6176   |    14 |
| path_m_stage             | chi_squared |   0.0194351   |  15.1077   |     6 |
| grade                    | chi_squared |   0.0732453   |  14.3433   |     8 |
| molecular_subtype_4class | chi_squared |   0.0989648   |  16.0234   |    10 |
| lauren_classification    | chi_squared | nan           | nan        |   nan |
| TP53_mut                 | chi_squared |   0.855983    |   0.31101  |     2 |
| CDH1_mut                 | chi_squared |   0.177794    |   3.45426  |     2 |
| ARID1A_mut               | chi_squared |   0.628212    |   0.929755 |     2 |
| PIK3CA_mut               | chi_squared |   0.733657    |   0.619428 |     2 |
| ERBB2_mut                | chi_squared |   0.863459    |   0.293617 |     2 |
| KRAS_mut                 | chi_squared |   0.274091    |   2.58859  |     2 |
| overall_survival         | logrank     |   0.500295    |   1.38511  |     2 |