# HNSC Image Modal Step4 Summary

## Embedding merge
- Slide embeddings: 225 x 1536
- Source counts: {'step3-hnsc-part00-20260504': 50, 'step3-hnsc-part01-20260504': 50, 'step3-hnsc-part02-20260504': 50, 'step3-hnsc-part03-20260504': 50, 'step3-hnsc-part04-20260504': 25}
- NaN: 0, Inf: 0

## Clustering
- Patient count: 225
- Best k: 2
- Silhouette: 0.2201
- Cluster counts: {'0': 209, '1': 16}

## Clinical and mutation
- Survival log-rank p-value: 0.38187242511143815
- Driver genes: TP53, CDKN2A, PIK3CA, NOTCH1, FAT1, CASP8
- HPV status: derived from p16/ISH testing in TCGA Xena clinical matrix.
- Requested HNSC four molecular subtype labels were not available; PanCancer RNA subtype was exported as a surrogate.

## Drug connection
- Top30 drugs: 30
- ADMET counts: {'KEEP': 20, 'EXCLUDE': 10}
- 4-Tier counts: {'Tier 1': 2, 'Tier 2': 6, 'Tier 3': 20, 'Tier 4': 2}
- Cluster-drug links: 60
