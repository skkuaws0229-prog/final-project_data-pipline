# Explanation Context API 검증 v1

작성일: 2026-05-14

## 목적

Bedrock/RAG/LLM 연결 전에, 백엔드가 설명용 근거 패키지 `retrieval_context_v1`을 실제 JSON으로 반환하는지 검증했다.

이번 단계에서는 Bedrock을 호출하지 않는다.

```text
구현 endpoint: GET /api/explanation-context
Bedrock 호출: 없음
secret/API key 저장: 없음
AWS 비용 발생 작업: 없음
```

## Endpoint

```http
GET /api/explanation-context
```

Query:

```text
disease_id          required string
drug_name           optional string
canonical_drug_id   optional string
include_search      optional boolean, default true
include_graph       optional boolean, default true
include_structure   optional boolean, default true
search_limit        optional number, default 10, max 50
```

주의:

```text
drug_name 또는 canonical_drug_id 중 하나는 필수다.
```

## Response 핵심 필드

```text
contract_version: retrieval_context_v1
disease_id
drug_name
canonical_drug_id
final_candidate
candidate_pool
admet
search_context
graph_context
structure_context
retrieval_sources
prompt_guardrails
status
```

## OpenAPI 등록 확인

```text
/api/explanation-context: true
```

## BRCA Oxaliplatin 검증

Request:

```text
GET /api/explanation-context?disease_id=BRCA&drug_name=Oxaliplatin&search_limit=5
```

결과:

```text
status: ready
contract_version: retrieval_context_v1
disease_id: BRCA
drug_name: Oxaliplatin
final_candidate.rank: 11
candidate_pool.provenance_count: 2
search_context.candidate_pool_hits.total: 1
graph_context.path_score: 0.3357
structure_context.available_structures: 1
retrieval_sources: 13
```

판정:

```text
PASS
candidate_pool 중복 row는 1개 화면 결과로 collapse되고 provenance_count=2로 보존된다.
final candidate, search, path score, structure context가 하나의 JSON에 묶인다.
```

## RA Ruxolitinib 검증

Request:

```text
GET /api/explanation-context?disease_id=RA&drug_name=Ruxolitinib&search_limit=5
```

결과:

```text
status: ready
contract_version: retrieval_context_v1
disease_id: RA
drug_name: Ruxolitinib
final_candidate.rank: 1
candidate_pool.provenance_count: 1
search_context.image_evidence_hits.total: 2
graph_context.path_score: 0.6667
graph_context.risk_sources: 0
structure_context.available_structures: 3
structure_context.resolution_method: target_text_fallback
structure_context.target_genes: JAK1, JAK2, JAK3
structure_context.matched_target_tokens: JAK
retrieval_sources: 10
```

판정:

```text
PASS
image-modal evidence의 JAK/STAT target text를 fallback으로 사용해 JAK1/JAK2/JAK3 구조 context를 반환한다.
직접 candidate_protein_structure_links가 없는 경우에도 설명용 구조 참고자료를 제공할 수 있다.
```

## Guardrail 검증

잘못된 질환:

```text
GET /api/explanation-context?disease_id=NOPE&drug_name=Ruxolitinib
HTTP 404
```

drug_name/canonical_drug_id 누락:

```text
GET /api/explanation-context?disease_id=RA
HTTP 400
```

판정:

```text
PASS
질환명 오류와 필수 query 누락을 거부한다.
```

## Structure context 동작

우선순위:

```text
1. candidate_protein_structure_links 기반 직접 연결
2. 직접 연결이 없으면 final/image evidence target text에서 protein token 추출
3. 추출 token으로 /api/structures 검색
```

예:

```text
Ruxolitinib image evidence target: JAK/STAT inflammatory axis
추출 token: JAK
구조 context: JAK1, JAK2, JAK3
```

주의:

```text
AlphaFold 구조는 약효 증명이 아니라 target/protein 참고자료다.
LLM prompt에는 이 guardrail을 반드시 포함한다.
```

## 최종 판정

```text
/api/explanation-context mock endpoint 구현 완료
실제 DB/OpenSearch/Neo4j/AlphaFold context 조립 확인
Bedrock 호출 없음
secret/API key 저장 없음
프론트/챗봇이 Bedrock prompt에 넣을 retrieval_context JSON 준비 완료
```

## 다음 단계

```text
1. 프론트에서 설명 버튼 클릭 시 /api/explanation-context 호출
2. 프론트/챗봇 레이어에서 retrieval_context를 Bedrock prompt에 전달
3. LLM 응답에는 source_file/source_type/risk_sources 표시
4. 이후 필요 시 /api/explanation-context에 evidence filtering 옵션 추가
```
