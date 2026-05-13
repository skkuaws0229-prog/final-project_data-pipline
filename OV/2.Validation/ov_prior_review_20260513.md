# OV Prior Review 20260513

| 항목 | 자동생성값 | 정답/수정값 | 일치여부 | 수정사항 |
|---|---|---|---|---|
| `random_seed` | `null` | `42` | NO | added top-level reproducibility seed |
| `analysis.driver_genes` | `["TP53", "BRCA1", "BRCA2", "PIK3CA", "PTEN", "RB1", "NF1", "KRAS"]` | `["TP53", "BRCA1", "BRCA2", "NF1", "RB1", "CDK12"]` | NO | aligned to required TCGA-OV/HGSOC core list; removed PIK3CA/PTEN/KRAS from TCGA-OV prior |
| `analysis.subtypes` | `["immunoreactive", "differentiated", "proliferative", "mesenchymal"]` | `["HGSOC", "LGSOC", "Endometrioid", "Clear cell", "Mucinous"]` | NO | changed from TCGA expression subtypes to ovarian histologic categories; TCGA-OV mostly HGSOC |
| `tier_classification.tier1_drugs` | `["Carboplatin", "Paclitaxel", "Cisplatin", "Doxorubicin"]` | `["Carboplatin", "Paclitaxel", "Olaparib", "Niraparib", "Bevacizumab", "Cisplatin", "Doxorubicin"]` | NO | added required FDA-approved ovarian cancer therapies; retained Cisplatin/Doxorubicin for review |
| `tier_classification.tier4_exclude` | `["Bevacizumab", "Olaparib", "Niraparib"]` | `[]` | NO | removed Bevacizumab/Olaparib/Niraparib from exclusion list |
| `analysis.k_values/clustering_k_range` | `[3, 4, 5, 6]` | `[2, 3, 4, 5, 6, 7, 8]` | NO | expanded IM3 search to k=2..8 |
| `data.tcga_project` | `"TCGA-OV"` | `"TCGA-OV"` | YES | already correct |
| `model.foundation_model` | `"UNI2"` | `"UNI2"` | YES | already correct for current image workflow |

## 판정

- `tcga_project=TCGA-OV`와 `foundation_model=UNI2`는 유지했습니다.
- driver genes, subtypes, tier1/tier4 drug prior, k search range, random_seed는 수정했습니다.
- IM4a clinical 미충족은 데이터 확보 문제로 본 prior review 범위에서 제외했습니다.
