# Backend/DB 전체 무결성 검증 및 프론트 전달 준비 v1

작성일: 2026-05-14

## 목적

프론트엔드 담당자에게 API를 전달하기 전에, 현재 로컬 backend와 DB 상태가 전체적으로 문제 없는지 확인했다.

검증 범위:

```text
Docker service 상태
FastAPI health/OpenAPI
PostgreSQL row count/FK/중복/coverage
OpenSearch index count
Neo4j node/edge count
AlphaFold structure/file proxy/link table
Explanation context API
프론트 QA 핵심 endpoint 유지 여부
```

## 최종 판정

```text
Frontend handoff readiness: PASS
Backend health: PASS
PostgreSQL integrity: PASS
OpenSearch integrity: PASS
Neo4j integrity: PASS
AlphaFold structure/file proxy: PASS
Explanation context API: PASS
```

주의가 필요한 운영 항목:

```text
docker compose up --build api 실행 시 db-loader가 다시 실행될 수 있음.
db-loader는 기본 canonical/image-modal 테이블을 TRUNCATE ... CASCADE로 재적재한다.
이 과정에서 candidate_protein_structure_links가 0건이 될 수 있으므로,
API 재빌드 후 반드시 candidate_protein_structure_links=261인지 확인한다.
현재 검증에서는 0건을 발견했고, seed CSV 기준으로 261건 복구 완료했다.
```

## Docker/Health 상태

Docker Compose:

```text
drug-service-api: Up, 8010->8000
drug-service-postgres: Up healthy, 5433->5432
drug-service-neo4j: Up healthy, 7474/7687
drug-service-opensearch: Up healthy, 9200/9600
```

Health endpoint:

```text
GET /health -> {"status":"ok","database":"ok"}
GET /health/search -> {"status":"ok","search":"ok"}
GET /health/graph -> {"status":"ok","graph":"ok"}
GET /health/kg-embedding -> {"status":"ok","kg_embedding":"ok","score_rows":1870}
```

OpenAPI:

```text
path_count: 29
/api/explanation-context: present
/v1/diseases/{disease_code}/final-candidates: present
/api/diseases/{disease_code}/candidates: present
/graph/relations: present
/search: present
/api/structures/{structure_id}/file: present
```

## PostgreSQL row count

| Table | Rows |
|---|---:|
| diseases | 11 |
| drugs | 171 |
| canonical_drugs | 170 |
| drug_aliases | 181 |
| drug_candidates | 255 |
| admet_results | 255 |
| candidate_pool | 432 |
| image_modal_clusters | 31 |
| image_modal_drug_evidence | 430 |
| image_modal_reports | 14 |
| protein_targets | 27 |
| alphafold_structures | 27 |
| candidate_protein_structure_links | 261 |
| pipeline_runs | 14 |

Uniqueness/coverage:

```text
drug_candidates candidate_id unique: 255/255
candidate_pool candidate_id unique: 432/432
admet_results candidate_id coverage: 255/255
alphafold_structures available: 27/27
candidate_protein_structure_links restored: 261
```

## PostgreSQL FK/고아 데이터 검증

아래 항목은 모두 0건이다.

```text
drug_candidates_missing_disease: 0
drug_candidates_missing_drug: 0
admet_missing_candidate: 0
candidate_pool_missing_disease: 0
image_evidence_missing_disease: 0
image_evidence_missing_cluster: 0
structure_links_missing_disease: 0
structure_links_missing_protein: 0
structure_links_missing_structure: 0
```

판정:

```text
FK/고아 데이터 문제 없음
```

## 원천 중복과 API dedup 상태

원천 DB에는 provenance 보존 목적의 중복 row가 남아 있다.

Raw duplicate:

```text
final_candidate raw canonical duplicate groups: 3
candidate_pool raw drug_name duplicate groups: 5
candidate_pool duplicate groups:
  BRCA Fulvestrant: 2
  BRCA Oxaliplatin: 2
  IPF Unnamed JAK1 preclinical compound: 20
  LUNG Dactinomycin: 2
  LUNG Docetaxel: 2
```

이 중복은 삭제하지 않는다.

API 표시 계층에서는 11개 질환 모두 중복 노출 0건이다.

Final candidates API:

| Disease | Rows | Duplicate drug_name | Final true |
|---|---:|---:|---:|
| BRCA | 15 | 0 | 15 |
| Colon | 15 | 0 | 15 |
| HNSC | 30 | 0 | 30 |
| IPF | 9 | 0 | 9 |
| Liver | 14 | 0 | 14 |
| LUNG | 15 | 0 | 15 |
| PAH | 30 | 0 | 30 |
| PDAC | 30 | 0 | 30 |
| Psoriasis | 30 | 0 | 30 |
| RA | 30 | 0 | 30 |
| STAD | 29 | 0 | 29 |

Candidates API:

| Disease | Rows | Duplicate drug_name | Final true |
|---|---:|---:|---:|
| BRCA | 60 | 0 | 15 |
| Colon | 50 | 0 | 15 |
| HNSC | 50 | 0 | 30 |
| IPF | 11 | 0 | 9 |
| Liver | 31 | 0 | 15 |
| LUNG | 37 | 0 | 15 |
| PAH | 30 | 0 | 30 |
| PDAC | 50 | 0 | 30 |
| Psoriasis | 30 | 0 | 30 |
| RA | 30 | 0 | 30 |
| STAD | 30 | 0 | 30 |

주의:

```text
IPF/Liver/STAD final API rows가 raw final count보다 적은 이유는 canonical dedup 때문이다.
프론트 표시 기준으로는 중복 노출이 없어 정상이다.
```

## OpenSearch 검증

Index:

```text
drug_service_text_v1
```

Document count:

```text
total: 1131
candidate_pool: 432
image_evidence: 430
drug_candidate: 255
image_report: 14
```

Collapse 검증:

```text
GET /search?q=Oxaliplatin&disease_id=BRCA&doc_type=candidate_pool
total: 1
raw_total: 2
provenance_count: 2
```

판정:

```text
검색 화면에는 중복 1건으로 collapse되고, 원천 row 2건은 provenance로 보존된다.
```

## Neo4j 검증

Node counts:

| Label | Count |
|---|---:|
| Disease | 11 |
| DiseaseAlias | 31 |
| Drug | 170 |
| DrugAlias | 181 |
| ImageCluster | 31 |
| ImageEvidence | 430 |
| TargetConcept | 133 |

Edge counts:

| Type | Count |
|---|---:|
| ALIAS_OF | 212 |
| CANDIDATE_FOR | 255 |
| HAS_IMAGE_CLUSTER | 31 |
| HAS_IMAGE_EVIDENCE | 430 |
| HAS_TARGET | 311 |
| MENTIONS_TARGET | 542 |
| SUPPORTS_DRUG | 430 |

RA graph API:

```text
GET /graph/relations?disease_id=RA&limit=50
nodes: 71
edges: 132
duplicate_node_id: 0
duplicate_edge_id: 0
```

판정:

```text
Neo4j graph/API 무결성 정상
```

## AlphaFold 검증

DB:

```text
protein_targets: 27
alphafold_structures: 27
alphafold_structures status=available: 27
candidate_protein_structure_links: 261
```

질환별 structure link:

| Disease | Links |
|---|---:|
| BRCA | 4 |
| Colon | 36 |
| HNSC | 45 |
| IPF | 15 |
| Liver | 7 |
| LUNG | 3 |
| PAH | 28 |
| PDAC | 48 |
| Psoriasis | 54 |
| RA | 4 |
| STAD | 17 |

API:

```text
GET /api/structures/targets?q=JAK
targets: 3
available: 3
genes: JAK1, JAK2, JAK3

GET /api/structures/af_p23458_f1_v6/file
HTTP 200
Content-Type: chemical/x-cif
size: 1115383 bytes
```

JAK1 detail:

```text
structure_id: af_p23458_f1_v6
status: available
context_summary.total_links: 25
diseases: IPF, Psoriasis, RA
disease_count: 3
drug_count: 6
candidate_target_count: 13
image_evidence_count: 12
```

판정:

```text
AlphaFold metadata/file proxy/context link 정상
```

## Explanation context API 검증

Endpoint:

```text
GET /api/explanation-context
```

RA/Ruxolitinib:

```text
status: ready
contract_version: retrieval_context_v1
retrieval_sources: 10
prompt_guardrails: 6
```

BRCA/Oxaliplatin:

```text
status: ready
contract_version: retrieval_context_v1
retrieval_sources: 13
prompt_guardrails: 6
candidate_pool.provenance_count: 2
```

Guardrail:

```text
missing drug_name/canonical_drug_id -> HTTP 400
unknown disease_id -> HTTP 404
unknown drug_name -> status no_evidence
```

판정:

```text
Bedrock 연결 전 retrieval_context JSON 제공 가능
Bedrock 호출 없음
secret/API key 저장 없음
```

## 프론트 전달 기준

프론트에 전달해도 되는 항목:

```text
1. /diseases
2. /v1/diseases/{disease_code}/final-candidates
3. /api/diseases/{disease_code}/candidates
4. /search
5. /graph/relations
6. /graph/path-score
7. /graph/kg-embedding
8. /api/structures/targets
9. /api/structures
10. /api/structures/{structure_id}
11. /api/structures/{structure_id}/file
12. /api/explanation-context
13. /api/pipeline-runs
```

프론트에 같이 전달할 주의사항:

```text
candidate_pool raw 중복은 provenance 보존 목적이며 API에서는 dedup/collapse된다.
final-candidates도 canonical dedup 후 반환되므로 일부 질환은 raw final count보다 적게 보일 수 있다.
AlphaFold 구조는 약효 증명이 아니라 target/protein 참고자료다.
Bedrock 호출은 프론트/챗봇 레이어에서 하되, prompt 근거는 /api/explanation-context 응답만 사용한다.
API 재빌드 후 candidate_protein_structure_links=261인지 확인한다.
```

## 결론

현재 backend/DB는 프론트 전달 가능한 상태다.

단, API 컨테이너 재빌드 또는 DB 재적재 후에는 아래 확인을 다시 수행한다.

```text
SELECT count(*) FROM candidate_protein_structure_links;
expected: 261
```
