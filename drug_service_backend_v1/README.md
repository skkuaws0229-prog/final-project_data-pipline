# Drug Service Backend v1

이 파일은 `drug_service_backend_v1` 폴더용 README입니다. 파일명 혼동을 줄이기 위해 같은 내용을 `DRUG_SERVICE_BACKEND_V1_README.md`에도 둡니다.

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
09_kg_embedding/      DistMult/TransE KG embedding baseline 산출물
10_alphafold/         AlphaFold target mapping 후보 CSV
docs/                 Pipeline run control API 설계/검증 문서
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
GET /health/kg-embedding
GET /graph/kg-embedding?disease_id=RA&model=ensemble&limit=50
GET /health/search
GET /search?q=JAK&disease_id=RA
GET /api/structures/targets
GET /api/structures/targets?disease_id=RA
GET /api/structures/targets?q=JAK
GET /api/structures/{structure_id}
GET /api/structures/{structure_id}/file
POST /api/pipeline-runs
GET /api/pipeline-runs
GET /api/pipeline-runs/{run_id}
GET /api/pipeline-runs/{run_id}/events
GET /api/pipeline-runs/{run_id}/artifacts
POST /api/pipeline-runs/{run_id}/cancel
POST /api/pipeline-runs/{run_id}/complete
```

React v2 API 계약과 인수인계 문서는 아래 파일을 기준으로 합니다.

```text
API_CONTRACT_REACT_V2.md
FRONTEND_HANDOFF_REACT_V2.md
MODEL_ROADMAP_v2.md
docs/pipeline_backend_integration_plan.md
docs/pipeline_run_frontend_handoff_v1.md
docs/pipeline_run_api_openapi.yaml
docs/alphafold_structure_schema_v1.md
docs/alphafold_integrity_validation_v1.md
docs/alphafold_target_mapping_plan_v1.md
docs/alphafold_target_mapping_integrity_v1.md
docs/target_mapping_policy_and_review_v1.md
docs/uniprot_auto_mapping_validation_v1.md
docs/uniprot_auto_mapping_integrity_v1.md
docs/uniprot_mapping_duplicate_check_v1.md
docs/reviewed_seed_integrity_v1.md
docs/reviewed_seed_db_load_validation_v1.md
docs/structures_targets_api_validation_v1.md
docs/alphafold_metadata_lookup_policy_v1.md
docs/alphafold_metadata_lookup_validation_v1.md
docs/alphafold_metadata_db_load_validation_v1.md
docs/structures_detail_api_validation_v1.md
docs/structure_api_integrity_recheck_v1.md
docs/candidate_structure_links_validation_v1.md
docs/structure_api_final_validation_v1.md
docs/alphafold_pilot_file_proxy_validation_v1.md
docs/alphafold_full_file_proxy_validation_v1.md
FRONTEND_HANDOFF_STRUCTURE_API_v1.md
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
KG Embedding Health: http://localhost:8010/health/kg-embedding
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

## Pipeline run control API

이 API는 Bedrock/RAG/LLM 챗봇이 나중에 직접 파이프라인을 만지지 않고, 백엔드 제어 계층만 호출하도록 만들기 위한 준비 단계입니다.

현재 동작 backend:

```text
mock
```

현재 skeleton backend:

```text
local_agent
aws_stepfunctions
```

`local_agent`와 `aws_stepfunctions`는 feature flag 없이 실제 실행되지 않으며, 비용 발생 AWS job은 launch하지 않습니다.
`execution_backend` 입력은 특수문자 alias도 허용합니다.

```text
$ -> mock
@ -> local_agent
# -> aws_stepfunctions
```

대표 요청:

```json
{
  "disease_name": "난소암",
  "mode": "full",
  "execution_backend": "mock"
}
```

관련 문서:

```text
docs/pipeline_backend_integration_plan.md
docs/pipeline_run_api_openapi.yaml
docs/pipeline_run_validation_v1.md
docs/pipeline_run_backend_alias_validation_v1.md
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

KG embedding v1 기준:

```text
Triples: 1875
Entities: 775
Relations: 6
Score rows: 1870
Known candidate score rows: 247
상세: 09_kg_embedding/kg_embedding_api_validation_v1.md
```

Pipeline run control API v1 기준:

```text
Mock run 생성/상태조회/이벤트조회/artifact조회/취소 완료
Run 목록조회/완료처리/중복완료 guardrail 완료
AWS Step Functions backend guardrail blocked 확인
잘못된 질환명 400 Bad Request 확인
실제 SageMaker/Step Functions job 미실행
상세: docs/pipeline_run_validation_v1.md
```

AlphaFold structure file pilot 기준:

```text
JAK1 / af_p23458_f1_v6 1건 available
S3 URI: s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/11_structures/alphafold/P23458/AF-P23458-F1-model_v6.cif
GET /api/structures/af_p23458_f1_v6/file 정상
상세: docs/alphafold_pilot_file_proxy_validation_v1.md
```

AlphaFold structure file 전체 처리 기준:

```text
27개 구조 파일 전체 available
S3 .cif 파일 27개 업로드 완료
GET /api/structures/{structure_id}/file 27개 전체 checksum 검증 완료
상세: docs/alphafold_full_file_proxy_validation_v1.md
```

## 주의사항

- `.venv`, `.env`, cache file은 GitHub에 포함하지 않습니다.
- `node_modules`, Docker volume, PostgreSQL/Neo4j/OpenSearch 실제 데이터 디렉터리도 GitHub에 포함하지 않습니다.
- 위 항목들은 누락이 아니라 의도적으로 제외한 실행환경/로컬 산출물입니다.
- Python 의존성은 `backend/requirements.txt`, DB/Search/Graph 실행환경은 `docker-compose.backend.yml`로 다시 생성합니다.
- 현재 비밀번호는 로컬 Docker 검증용 개발 값입니다.
- React v1은 연결 검증용이며, 본격 UI는 React v2에서 진행합니다.
- OpenSearch v1은 text search만 포함합니다. vector search는 이후 embedding 정책 확정 뒤 추가합니다.
- TxGNN은 v1/v2 구현 범위에서 제외합니다. 비용/환경 부담 대비 현재 후보 약물 coverage가 낮아, 다음 단계는 Pipeline run control API와 Bedrock RAG/LLM explanation입니다.
