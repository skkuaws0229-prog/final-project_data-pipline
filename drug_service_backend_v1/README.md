# Drug Service Backend v1

이 폴더는 drug recommendation service v1의 FastAPI backend 코드입니다.

DB 적재 자료는 같은 repository의 아래 폴더를 사용합니다.

```text
drug_service_db_v1/
```

## 포함 자료

```text
backend/app/          FastAPI application code
backend/Dockerfile    API container build file
backend/requirements.txt
backend/.env.example  로컬 실행용 환경변수 예시
08_path_scoring/      Neo4j path scoring v1 설계/검증 리포트
docker-compose.backend.yml
```

## 구현된 endpoint

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
GET /graph/path-score?disease_id=RA&limit=100
GET /health/search
GET /search?q=JAK&disease_id=RA
```

React v2 API 계약과 인수인계 문서는 아래 파일을 기준으로 합니다.

```text
API_CONTRACT_REACT_V2.md
FRONTEND_HANDOFF_REACT_V2.md
MODEL_ROADMAP_v2.md
```

## Docker Compose 실행

Repository root에서 실행합니다.

```bash
docker compose -f drug_service_backend_v1/docker-compose.backend.yml up --build
```

실행 후 확인 주소:

```text
FastAPI: http://localhost:8010
Swagger: http://localhost:8010/docs
Health: http://localhost:8010/health
Graph Health: http://localhost:8010/health/graph
Search Health: http://localhost:8010/health/search
Neo4j Browser: http://localhost:7474
```

## 로컬 Python 실행

DB는 먼저 `drug_service_db_v1/docker-compose.db.yml`로 띄워둡니다.

```bash
cd drug_service_backend_v1/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Graph API 응답 형태

`/graph/relations`는 React graph viewer에 바로 연결하기 쉽도록 아래 형태로 반환합니다.

```json
{
  "disease_id": "RA",
  "nodes": [],
  "edges": []
}
```

주요 node label:

```text
Disease, Drug, ImageCluster, ImageEvidence, TargetConcept
```

주요 edge type:

```text
CANDIDATE_FOR, HAS_IMAGE_CLUSTER, HAS_IMAGE_EVIDENCE, SUPPORTS_DRUG, HAS_TARGET, MENTIONS_TARGET
```

## 검증 상태

`drug_service_db_v1/06_graph/validation/graph_api_validation_v1.md` 기준:

```text
Duplicate node id: 0
Duplicate edge id: 0
Broken edge endpoint: 0
Neo4j import CSV 대비 edge count mismatch: 0
```

OpenSearch text index 기준:

```text
Index: drug_service_text_v1
Documents: 699
drug_candidate: 255
image_evidence: 430
image_report: 14
```

Path scoring v1 기준:

```text
11개 질병 전체 검증 완료
Score rows: 247
Duplicate canonical_drug_id: 0
Out-of-range score: 0
Missing evidence_sources: 0
상세: 08_path_scoring/path_score_validation_v1.md
```

## 주의사항

- `.venv`, `.env`, cache file은 GitHub에 포함하지 않습니다.
- `node_modules`, Docker volume, PostgreSQL/Neo4j/OpenSearch 실제 데이터 디렉터리도 GitHub에 포함하지 않습니다.
- 위 항목들은 누락이 아니라 의도적으로 제외한 실행환경/로컬 산출물입니다.
- Python 의존성은 `backend/requirements.txt`, DB/Search/Graph 실행환경은 `docker-compose.backend.yml`로 다시 생성합니다.
- 현재 비밀번호는 로컬 Docker 검증용 개발 값입니다.
- React v1은 연결 검증용이며, 본격 UI는 React v2에서 진행합니다.
- OpenSearch v1은 text search만 포함합니다. vector search는 이후 embedding 정책 확정 뒤 추가합니다.
- TxGNN은 v1/v2 구현 범위에서 제외합니다. 비용/환경 부담 대비 현재 후보 약물 coverage가 낮아, 다음 단계는 DistMult/TransE KG embedding baseline, Bedrock RAG/LLM explanation입니다.
