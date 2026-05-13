# React v2 프론트엔드 인수인계

## 현재 backend 상태

현재 v1 backend는 아래 범위까지 연결되어 있습니다.

```text
PostgreSQL: 연결 완료
Neo4j: 연결 완료
FastAPI: 구현 완료
Graph API: /graph/relations 검증 완료
OpenSearch: text search 연결 완료
TxGNN: 아직 미연결
RAG/LLM: 아직 미연결
```

React v2는 PostgreSQL + Neo4j 기반 화면을 먼저 붙이고, 이후 OpenSearch/TxGNN/RAG를 단계적으로 추가하는 방향이 좋습니다.

## 실행 방법

repository root에서 실행합니다.

```bash
docker compose -f drug_service_backend_v1/docker-compose.backend.yml up --build
```

확인 주소:

```text
Swagger: http://localhost:8010/docs
Health: http://localhost:8010/health
Graph Health: http://localhost:8010/health/graph
Neo4j Browser: http://localhost:7474
```

프론트 `.env` 예시:

```env
VITE_API_BASE_URL=http://localhost:8010
```

다른 PC에서 API에 붙는 경우:

```env
VITE_API_BASE_URL=http://{API_HOST_IP}:8010
```

## 프론트 담당자에게 전달할 핵심

React v1은 연결 검증용 화면입니다. React v2는 실제 사용자 흐름 기준으로 새로 구성하면 됩니다.

우리가 프론트 담당자에게 확정해서 넘기는 것은 아래입니다.

```text
API endpoint
request query
response field
데이터 의미
주의해야 할 매칭 규칙
검증 완료 여부
```

화면 레이아웃, 컴포넌트 분리, 상태관리 방식, graph viewer 라이브러리 선택은 프론트엔드 담당자가 주도하는 것이 좋습니다.

## 권장 화면 구성

아래는 요구사항 전달용 제안입니다. 구현 방식은 프론트 담당자가 조정해도 됩니다.

```text
1. 상단: 질병 선택
2. 좌측 또는 메인: 후보 약물 테이블
3. 우측 detail panel: 선택 약물의 ADMET/target/evidence
4. 하단 또는 별도 tab: image-modal cluster/evidence
5. Graph tab: Neo4j 관계 graph viewer
```

## 필수 연결 endpoint

상세 계약은 `API_CONTRACT_REACT_V2.md`를 기준으로 합니다.

```text
GET /health
GET /health/graph
GET /diseases
GET /drugs?disease_id=RA
GET /image-modal/evidence?disease_id=RA
GET /image-modal/clusters?disease_id=RA
GET /graph/relations?disease_id=RA&limit=50
GET /health/search
GET /search?q=JAK&disease_id=RA
```

## 데이터 매칭 규칙

약물 연결 기준:

```text
canonical_drug_id
```

주의할 값:

```text
match_status = matched
match_status = evidence_only
```

의미:

```text
matched: main candidate table과 image-modal evidence가 연결된 약물
evidence_only: image-modal evidence에만 등장하고 main candidate table에는 없는 약물
```

Target 관련 주의:

```text
target / target_pathway / TargetConcept는 아직 raw text
모든 target을 gene으로 간주하면 안 됨
gene/pathway/mechanism/free-text가 섞여 있음
```

Cluster 관련 주의:

```text
cluster_label이 비어 있으면 cluster_key 표시
약물 evidence가 없는 cluster도 graph API에는 Disease -> ImageCluster로 포함됨
image-modal 데이터는 이미지 파일 자체가 아니라 환자 cluster/근거 요약 데이터
```

## Graph viewer 참고

`/graph/relations` 응답은 아래 형태입니다.

```json
{
  "disease_id": "RA",
  "nodes": [],
  "edges": []
}
```

Node label:

```text
Disease
Drug
ImageCluster
ImageEvidence
TargetConcept
```

Edge type:

```text
CANDIDATE_FOR
HAS_IMAGE_CLUSTER
HAS_IMAGE_EVIDENCE
SUPPORTS_DRUG
HAS_TARGET
MENTIONS_TARGET
```

프론트 표시 제안:

```text
Disease: 질병 중심 node
Drug: 약물 node
ImageCluster: cluster node
ImageEvidence: 근거 node
TargetConcept: target/pathway raw concept node
```

`CANDIDATE_FOR`와 `SUPPORTS_DRUG`는 의미가 다르므로 색상이나 edge style을 분리하는 것이 좋습니다.

## 검증 완료 사항

Graph API 검증 결과:

```text
11개 질병 전체 검증 완료
Duplicate node id: 0
Duplicate edge id: 0
Broken edge endpoint: 0
Neo4j import CSV 대비 edge count mismatch: 0
```

상세 리포트:

```text
drug_service_db_v1/06_graph/validation/graph_api_validation_v1.md
```

OpenSearch text search 검증:

```text
Index: drug_service_text_v1
Documents: 699
drug_candidate: 255
image_evidence: 430
image_report: 14
GET /health/search -> {"status":"ok","search":"ok"}
```

## 아직 구현하지 않는 것

React v2 초기 구현에서 아래 항목은 제외해도 됩니다.

```text
OpenSearch vector search
TxGNN prediction score
RAG explanation
AlphaFold structure viewer
```

이 항목들은 backend endpoint가 추가된 뒤 React v3 또는 v2 확장으로 붙이는 것이 안전합니다.

## 다음 논의 포인트

프론트 담당자와 논의할 항목:

```text
Graph viewer 라이브러리 선택: react-force-graph 등
약물 테이블 컬럼 우선순위
ADMET filter UX
evidence_only 약물 표시 방식
TargetConcept raw text 표시 방식
질병별 graph가 클 때 node filter/search를 넣을지 여부
```
