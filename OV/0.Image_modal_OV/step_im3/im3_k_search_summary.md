# IM3 k Search Summary

- random_seed: 42
- search_range: k=2..8
- best_k: 2
- best_silhouette: 0.191136
- best_cluster_sizes: [38, 12]

|   k |   silhouette | cluster_sizes             |   min_cluster |   max_cluster |   imbalance_ratio |
|----:|-------------:|:--------------------------|--------------:|--------------:|------------------:|
|   2 |     0.191136 | [38, 12]                  |            12 |            38 |              3.17 |
|   3 |     0.1634   | [12, 15, 23]              |            12 |            23 |              1.92 |
|   4 |     0.172951 | [15, 23, 5, 7]            |             5 |            23 |              4.6  |
|   5 |     0.149593 | [14, 7, 9, 15, 5]         |             5 |            15 |              3    |
|   6 |     0.117784 | [6, 13, 6, 6, 10, 9]      |             6 |            13 |              2.17 |
|   7 |     0.124549 | [15, 10, 4, 8, 5, 7, 1]   |             1 |            15 |             15    |
|   8 |     0.104173 | [9, 11, 7, 9, 1, 8, 3, 2] |             1 |            11 |             11    |

Best k was selected by maximum silhouette score. Cluster size imbalance is reported for review but was not used as the primary optimizer.
