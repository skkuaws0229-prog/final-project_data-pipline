# RA X-ray Image Modal RAM-W600 Summary

- Dataset: RAM-W600 / RAM-W1K-style wrist X-ray, local root `C:\Users\biso8\20260503_final_project\ra_xray\0.Image_modal_RA`
- Patients clustered: 207
- Selected k: 2
- Silhouette: 0.1326
- SvdH ANOVA p-value: 0.03104
- SvdH Kruskal-Wallis p-value: 0.000451
- Severity chi-squared p-value: 1.479e-05
- Cluster-drug linkage rows: 32

## Cluster Clinical Summary

|   cluster |   n_wrist_images |   n_patients |   mean_svdh_bone_erosion |   median_svdh_bone_erosion |   max_svdh_bone_erosion |
|----------:|-----------------:|-------------:|-------------------------:|---------------------------:|------------------------:|
|         0 |              477 |          134 |                 0.937139 |                        0.5 |                      10 |
|         1 |              323 |           73 |                 0.640982 |                        0   |                      12 |

## Statistical Tests

| variable                | test           |     p_value |
|:------------------------|:---------------|------------:|
| total_svdh_bone_erosion | one_way_anova  | 0.0310401   |
| total_svdh_bone_erosion | kruskal_wallis | 0.000450962 |
| severity_bin            | chi_squared    | 1.47936e-05 |