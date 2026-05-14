# RAG/Bedrock Retrieval 계약 연결 검증 v1

작성일: 2026-05-14

## 목적

`docs/rag_bedrock_retrieval_contract_v1.md` 문서 작성 후, 현재 로컬 FastAPI/DB/Search/Graph/Structure 연결 상태가 유지되는지 확인했다.

이번 검증은 실제 Bedrock 호출이나 RAG endpoint 구현 검증이 아니다.

```text
검증 대상: 현재 구현된 backend endpoint 연결 상태
설계-only 확인: /api/explanation-context는 아직 구현 전임을 확인
Bedrock 호출: 미실행
AWS 비용 발생 작업: 미실행
```

## Docker Compose 상태

```text
drug-service-api: Up, 0.0.0.0:8010->8000
drug-service-postgres: Up healthy, 0.0.0.0:5433->5432
drug-service-neo4j: Up healthy, 7474/7687
drug-service-opensearch: Up healthy, 9200/9600
```

## Health Check

| Endpoint | 결과 |
|---|---|
| `GET /health` | `{"status":"ok","database":"ok"}` |
| `GET /health/search` | `{"status":"ok","search":"ok"}` |
| `GET /health/graph` | `{"status":"ok","graph":"ok"}` |
| `GET /health/kg-embedding` | `{"status":"ok","kg_embedding":"ok","score_rows":1870}` |

판정:

```text
FastAPI/PostgreSQL 연결 정상
OpenSearch 연결 정상
Neo4j 연결 정상
KG embedding score table 연결 정상
```

## Candidate API 검증

### BRCA final-candidates

```text
GET /v1/diseases/BRCA/final-candidates?limit=100
rows: 15
duplicate_drug_name: 0
final_true: 15
```

### BRCA broader candidates

```text
GET /api/diseases/BRCA/candidates?limit=100
rows: 60
duplicate_drug_name: 0
final_true: 15
```

판정:

```text
final-candidates와 candidates는 분리되어 있음
기본 후보 화면은 15개 final 후보
view=all 후보 화면은 60개 broader 후보
API 응답 기준 같은 질환 안 drug_name 중복 노출 없음
```

## OpenSearch candidate_pool 검색 검증

```text
GET /search?q=Oxaliplatin&disease_id=BRCA&doc_type=candidate_pool
```

결과:

```text
total: 1
raw_total: 2
first_drug: Oxaliplatin
provenance_count: 2
provenance_note: 원천 candidate_pool row 2개에서 집계됨
```

판정:

```text
화면용 검색 결과는 1건으로 collapse됨
원천 row 2개는 provenance로 보존됨
검색/RAG 근거용 source_file/provenance_count 전달 가능
```

## Neo4j graph 검증

```text
GET /graph/relations?disease_id=RA&limit=50
```

결과:

```text
nodes: 71
edges: 132
duplicate_node_id: 0
duplicate_edge_id: 0
```

판정:

```text
graph viewer용 nodes/edges 응답 정상
node/edge id 중복 없음
```

## Path scoring 검증

```text
GET /graph/path-score?disease_id=RA&limit=100
```

결과:

```text
rows: 30
duplicate_canonical_drug_id: 0
missing_evidence_sources: 0
```

판정:

```text
path_score 결과 중복 없음
RAG 설명에 필요한 evidence_sources 누락 없음
```

## KG embedding 검증

```text
GET /graph/kg-embedding?disease_id=RA&model=ensemble&limit=50
```

결과:

```text
rows: 50
model: ensemble
duplicate_canonical_drug_id: 0
```

판정:

```text
DistMult/TransE ensemble score 응답 정상
같은 질환 안 canonical_drug_id 중복 없음
```

## AlphaFold structure 검증

### Target 목록

```text
GET /api/structures/targets?q=JAK
```

결과:

```text
targets: 3
available: 3
genes: JAK1, JAK2, JAK3
```

### JAK1 file proxy

```text
GET /api/structures/af_p23458_f1_v6/file
```

결과:

```text
HTTP 200
content_type: chemical/x-cif
size_download: 1115383 bytes
```

주의:

```text
HEAD /api/structures/{structure_id}/file 는 405 Method Not Allowed
현재 file proxy는 GET만 지원함
프론트 viewer는 GET으로 로딩해야 함
```

## Pipeline run API 검증

```text
GET /api/pipeline-runs?limit=5
```

결과:

```text
runs: 5
statuses: blocked, completed, blocked, blocked, blocked
backends: mock, mock, aws_stepfunctions, aws_stepfunctions, mock
```

판정:

```text
run 목록 조회 정상
mock/blocked 상태 기록 정상
실제 AWS job 실행 없음
```

## RAG/Bedrock 계약 상태 확인

```text
GET /openapi.json
```

확인 결과:

```text
has_explanation_context: false
has_search: true
has_pipeline_runs: true
has_structure_file: true
```

판정:

```text
/api/explanation-context는 아직 구현 전인 설계 endpoint가 맞음
현재 상태는 문서 계약 완료 단계
다음 단계에서 mock endpoint를 추가해야 함
```

## 최종 판정

```text
현재 backend 연결 상태 정상
PostgreSQL/FastAPI 정상
Neo4j graph/path scoring 정상
OpenSearch text search/candidate_pool collapse 정상
KG embedding 정상
AlphaFold structure proxy 정상
Pipeline run control API 정상
RAG/Bedrock retrieval endpoint는 아직 미구현 상태가 맞음
```

## 다음 단계

```text
1. 프론트 QA 응답 대기
2. 필요 시 GET /api/explanation-context mock endpoint 구현
3. mock endpoint가 final_candidate/candidate_pool/search/path/structure context를 한 JSON으로 묶는지 검증
4. 이후 프론트 Bedrock prompt 연결
```
