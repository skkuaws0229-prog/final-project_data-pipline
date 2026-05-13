# Drug Service FastAPI

이 API는 PostgreSQL-first canonical load에 연결됩니다. Neo4j, TxGNN, OpenSearch는 단계적으로 추가합니다.

## 로컬 실행

```bash
cd drug_service_build/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql://drug_service:drug_service_local@localhost:5433/drug_service uvicorn app.main:app --reload
```

## 엔드포인트

```text
GET /health
GET /health/graph
GET /diseases
GET /drugs?disease_id=BRCA
GET /drugs/{drug_id}
GET /image-modal/clusters?disease_id=BRCA
GET /image-modal/evidence?disease_id=BRCA
GET /image-modal/reports?disease_id=BRCA
GET /graph/relations?disease_id=RA&limit=50
GET /health/search
GET /search?q=JAK&disease_id=RA
```

## 프론트엔드 인수인계

Docker Compose로 이 머신에서 API를 실행 중일 때, 같은 네트워크의 프론트엔드 개발자는 아래 주소를 사용할 수 있습니다.

```text
API_BASE_URL=http://172.16.0.64:8010
Swagger=http://172.16.0.64:8010/docs
```

현재 CORS allowlist에는 Vite 개발 서버 `localhost:5173`, `127.0.0.1:5173`, `172.16.0.64:5173`가 포함되어 있습니다.

## Neo4j 연결

FastAPI는 아래 환경변수로 Neo4j에 연결합니다.

```text
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=drug_service_neo4j
```

로컬 host에서 backend를 직접 실행할 때는 `NEO4J_URI=bolt://localhost:7687`을 사용합니다.

연결 확인:

```text
GET /health/graph
```

Graph 관계 조회:

```text
GET /graph/relations?disease_id=RA&limit=50
```

응답 형태:

```json
{
  "disease_id": "RA",
  "nodes": [],
  "edges": []
}
```

`nodes[].label`은 `Disease`, `Drug`, `ImageCluster`, `ImageEvidence`, `TargetConcept` 중 하나입니다. `edges[].type`은 `CANDIDATE_FOR`, `HAS_IMAGE_CLUSTER`, `HAS_IMAGE_EVIDENCE`, `SUPPORTS_DRUG`, `HAS_TARGET`, `MENTIONS_TARGET` 중 하나입니다.

## OpenSearch 연결

FastAPI는 아래 환경변수로 OpenSearch에 연결합니다.

```text
OPENSEARCH_URL=http://opensearch:9200
OPENSEARCH_INDEX=drug_service_text_v1
```

연결 확인:

```text
GET /health/search
```

Text search:

```text
GET /search?q=JAK&disease_id=RA
GET /search?q=immune&doc_type=image_evidence
```

지원 `doc_type`:

```text
drug_candidate
image_evidence
image_report
```

검증 결과:

```text
11개 질병 전체 /graph/relations 응답 검증 완료
Duplicate node id: 0
Duplicate edge id: 0
Broken edge endpoint: 0
Neo4j import CSV 대비 candidate/support/cluster/target edge count mismatch: 0
```

OpenSearch text index 검증:

```text
Index: drug_service_text_v1
Documents: 699
drug_candidate: 255
image_evidence: 430
image_report: 14
GET /health/search -> {"status":"ok","search":"ok"}
```

## Docker/AWS 메모

Backend에는 Dockerfile이 있으므로 같은 FastAPI app을 로컬 또는 EC2에서 실행할 수 있습니다. EC2에서 실행할 때는 `DATABASE_URL`이 Docker Compose의 PostgreSQL service name을 가리키도록 설정합니다.

예:

```text
postgresql://drug_service:drug_service_local@postgres:5432/drug_service
```
