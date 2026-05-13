# Neo4j Graph Schema v1

## 목적

이 schema는 현재 PostgreSQL-first 정규화 데이터를 원본 CSV나 PostgreSQL table을 수정하지 않고 Neo4j graph로 변환하기 위한 기준입니다.

React v1은 PostgreSQL/FastAPI 연결 검증용 화면으로 유지합니다. Neo4j v1은 관계 탐색과 이후 TxGNN 연동을 위한 다음 backend layer입니다.

## Node Labels

### `Disease`

Source: `03_normalized/diseases.csv`

Key:

```text
disease_id
```

주요 properties:

```text
disease_id
display_name
source_file
source_s3_key
```

### `Drug`

Source: `03_normalized/canonical_drugs.csv`

Key:

```text
canonical_drug_id
```

주요 properties:

```text
canonical_drug_id
primary_drug_name
primary_smiles
primary_source_drug_id
drug_source_status
```

`drug_source_status` 값:

```text
candidate_table
evidence_only
```

### `DrugAlias`

Source: `03_normalized/drug_aliases.csv`

Key:

```text
alias_id
```

주요 properties:

```text
alias_id
canonical_drug_id
source_drug_id
alias_name
normalized_alias
alias_type
```

Drug alias는 Neo4j graph search/matching에 사용하기 위해 포함합니다. 프론트엔드 표시용으로는 PostgreSQL/FastAPI에서도 노출할 수 있습니다.

### `DiseaseAlias`

Source: `03_normalized/disease_aliases.csv`

Key:

```text
alias_id
```

주요 properties:

```text
alias_id
disease_id
alias
normalized_alias
```

### `TargetConcept`

Source: drug candidate와 image-modal evidence의 raw `target`, `target_pathway` field.

Key:

```text
target_id
```

주요 properties:

```text
target_id
concept_text
normalized_text
concept_type
```

`concept_type`은 v1에서 보수적으로 유지합니다.

```text
raw_target
raw_pathway
```

현재 target field에는 gene/pathway/mechanism/free-text가 섞여 있으므로 전부 gene이라고 가정하면 안 됩니다. Gene/pathway/mechanism 정규화는 Neo4j/OpenSearch/TxGNN v2 검증 단계로 미룹니다.

`nan`, `none`, `null`, `na`, `n/a` 같은 placeholder 값은 blank로 처리하고 `TargetConcept`로 import하지 않습니다.

### `ImageCluster`

Source: `03_normalized/image_modal_clusters.csv`

Key:

```text
cluster_id
```

주요 properties:

```text
cluster_id
disease_id
cluster_key
cluster_label
n_observations
clinical_summary
pathway_summary
source_file
```

### `ImageEvidence`

Source: `03_normalized/image_modal_drug_evidence.csv` + `image_modal_evidence_drug_matches.csv`

Key:

```text
evidence_id
```

주요 properties:

```text
evidence_id
disease_id
cluster_id
drug_name
rank
tier
target
target_pathway
evidence_text
source_file
match_status
canonical_drug_id
```

### 향후 `TxGNNRun`

TxGNN 단계에서 사용할 예정입니다.

Key:

```text
run_id
```

예정 properties:

```text
run_id
model_version
created_at
source_file
notes
```

## Relationships

### `(Drug)-[:CANDIDATE_FOR]->(Disease)`

Source: `03_normalized/drug_candidates.csv` + `admet_results.csv`

Relationship key:

```text
candidate_id
```

Properties:

```text
candidate_id
rank
tier
score
evidence_summary
safety_score
verdict
admet_status
hard_fail
hard_fail_reasons
soft_flags
source_file
source_row_number
```

### `(Drug)-[:HAS_TARGET]->(TargetConcept)`

Source: candidate `target`, `target_pathway`

Properties:

```text
source_kind = candidate
source_id = candidate_id
disease_id
relation_kind = target | pathway
```

### `(DrugAlias)-[:ALIAS_OF]->(Drug)`

Source: `03_normalized/drug_aliases.csv`

Properties:

```text
alias_type
source_drug_id
```

### `(DiseaseAlias)-[:ALIAS_OF]->(Disease)`

Source: `03_normalized/disease_aliases.csv`

### `(Disease)-[:HAS_IMAGE_CLUSTER]->(ImageCluster)`

Source: `03_normalized/image_modal_clusters.csv`

Properties:

```text
source_file
```

### `(ImageCluster)-[:HAS_IMAGE_EVIDENCE]->(ImageEvidence)`

Source: `03_normalized/image_modal_drug_evidence.csv`

Properties:

```text
disease_id
source_file
```

### `(ImageEvidence)-[:SUPPORTS_DRUG]->(Drug)`

Source: `03_normalized/image_modal_evidence_drug_matches.csv`

Properties:

```text
match_status
drug_name
rank
tier
```

`evidence_only` 약물은 `Drug` node로 보존합니다. 삭제하면 안 됩니다.

### `(ImageEvidence)-[:MENTIONS_TARGET]->(TargetConcept)`

Source: evidence `target`, `target_pathway`

Properties:

```text
source_kind = image_modal_evidence
source_id = evidence_id
disease_id
relation_kind = target | pathway
```

### 향후 `(Drug)-[:TXGNN_PREDICTED_FOR]->(Disease)`

TxGNN prediction을 위해 예약한 관계입니다.

예정 properties:

```text
run_id
score
rank
prediction_label
model_version
source_file
```

이 관계는 `CANDIDATE_FOR`와 분리합니다. `CANDIDATE_FOR`는 현재 pipeline output이고, `TXGNN_PREDICTED_FOR`는 model-derived graph prediction이기 때문입니다.

## v1 설계 원칙

- 원본 S3 data나 PostgreSQL normalized CSV는 수정하지 않습니다.
- Graph import 산출물은 `06_graph/` 아래에 보관합니다.
- Evidence-only 약물은 보존합니다.
- v1에서는 target text를 raw concept으로 보존합니다.
- TxGNN은 base graph 검증 이후 별도 relationship family로 추가합니다.
