# Graph 검증 요약 v1

## 범위

Neo4j graph import 산출물은 `03_normalized/` 데이터를 기준으로 생성했습니다. 원본 데이터와 PostgreSQL 정규화 CSV는 수정하지 않았습니다.

## 생성된 Node 수

```text
Disease nodes: 11
Drug nodes: 170
DrugAlias nodes: 181
DiseaseAlias nodes: 31
TargetConcept nodes: 133
ImageCluster nodes: 31
ImageEvidence nodes: 430
```

## 생성된 Relationship 수

```text
CANDIDATE_FOR edges: 255
HAS_TARGET candidate edges: 311
HAS_IMAGE_EVIDENCE edges: 430
SUPPORTS_DRUG edges: 430
MENTIONS_TARGET evidence edges: 542
```

## 주요 검증 결과

```text
Evidence-only Drug nodes: 10
Evidence-only SUPPORTS_DRUG edges: 27
Unmatched image-modal evidence edges: 0
Broken graph endpoint references: 0
Candidate rows without target/pathway: 62
Image-modal evidence rows without target/pathway: 0
Removed placeholder raw target values: 문자열 `nan` 78개를 blank로 처리하고 TargetConcept에서 제외
```

## v1 Schema 결정사항

- Drug node는 source `drug_id`가 아니라 `canonical_drug_id`를 사용합니다.
- Drug/Disease alias는 `DrugAlias`, `DiseaseAlias` node로 보존하고 `ALIAS_OF` 관계로 연결합니다.
- Evidence-only 약물은 `drug_source_status = evidence_only`인 `Drug` node로 보존합니다.
- Candidate ADMET 값은 `CANDIDATE_FOR` relationship property로 저장합니다.
- Raw `target`, `target_pathway` 값은 `TargetConcept`로 저장합니다.
- Target concept은 아직 gene/pathway/mechanism으로 분리하지 않습니다.
- TxGNN은 base graph 검증 이후 `TXGNN_PREDICTED_FOR` relationship으로 추가할 예정입니다.

## 참조 무결성 검증

추가 참조 무결성 검증 파일:

```text
06_graph/validation/graph_integrity_checks_v1.csv
06_graph/validation/graph_broken_references_v1.csv
06_graph/validation/graph_target_omissions_v1.csv
```

모든 graph edge endpoint reference는 통과했습니다. `target`, `target_pathway`가 없는 candidate row 62개는 원본 정규화 CSV에서 해당 field가 비어 있었기 때문에 `HAS_TARGET` edge가 생성되지 않은 정상 케이스입니다.

## Neo4j 적재 검증

Neo4j는 Docker Compose에서 `LOAD CSV` 방식으로 적재했습니다.

```text
Neo4j Browser: http://localhost:7474
username: neo4j
password: drug_service_neo4j
```

적재 count는 아래 파일에 기록했습니다.

```text
06_graph/validation/neo4j_loaded_counts_v1.csv
06_graph/validation/neo4j_sample_queries_v1.md
```

질병 범위 sample query 결과:

```text
RA + Ruxolitinib -> rank 1, tier pass_admet_gate, RA image-modal evidence count 2
```

추가 Cypher 검증:

```text
11/11 질병 모두 candidate, cluster, image evidence graph data 존재
Evidence-only 약물은 BRCA, Colon, PAH, Psoriasis에만 존재
DrugAlias -> Drug lookup 정상
중복 표시 alias는 API/frontend에서 distinct-collapse 필요
상위 TargetConcept 값에 placeholder `nan` 없음
```

Deep integrity validation:

```text
06_graph/validation/neo4j_integrity_deep_checks_v1.md
```

결과:

```text
Duplicate relationship checks: PASS, 0 issues
Orphan node checks: PASS, 0 issues
Required blank field checks: PASS, 0 issues
Disease-scope mismatch checks: PASS, 0 issues
Alias duplicate display candidates: 6 groups, provenance 보존 후 API/frontend에서 distinct-collapse
TargetConcept review candidates: 존재, 삭제하지 말고 v2에서 분류
```

## 다음 단계

FastAPI에 Neo4j 연결 설정을 추가했고 `/health/graph` 검증까지 완료했습니다.

```text
GET /health/graph -> {"status":"ok","graph":"ok"}
```

`/graph/relations?disease_id=...` graph endpoint도 구현했습니다.

검증 결과:

```text
11개 질병 전체 limit=200 검증 완료
Duplicate node id: 0
Duplicate edge id: 0
Broken edge endpoint: 0
Neo4j import CSV 대비 candidate/support/cluster/target edge count mismatch: 0
```

Graph API 검증 리포트:

```text
06_graph/validation/graph_api_validation_v1.md
06_graph/validation/graph_api_summary_v1.csv
06_graph/validation/graph_api_issues_v1.csv
```

다음 단계는 React v2 또는 graph viewer에서 이 응답을 시각화하는 것입니다.
