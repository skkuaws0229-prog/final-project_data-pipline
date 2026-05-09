# Psoriasis Clinical Photo Image-Modal Summary

- Source: Kaggle Skin Diseases Dataset, psoriasis/lichen-planus-related class (100 selected images).
- BiomedCLIP embeddings: 100 x 512, NaN/Inf: False.
- Best k: 4, silhouette: 0.1179.
- PASI severity labels were not available in the selected Kaggle class; severity association is therefore not_applicable.

## Cluster Statistical Tests
| variable       | test           |   p_value | note                                                                  |
|:---------------|:---------------|----------:|:----------------------------------------------------------------------|
| label          | not_applicable |       nan | Only one observed category; statistical association cannot be tested. |
| severity_label | not_applicable |       nan | Only one observed category; statistical association cannot be tested. |

## Psoriasis 4-Tier Counts
| tier   |   n_drugs |
|:-------|----------:|
| Tier 2 |        16 |
| Tier 3 |        12 |
| Tier 1 |         2 |

Cluster-drug linkage rows: 120