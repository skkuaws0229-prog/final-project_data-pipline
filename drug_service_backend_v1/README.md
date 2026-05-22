# Drug Service Build

이 파일은 로컬 `drug_service_build` 전체 작업공간용 README입니다. 파일명 혼동을 줄이기 위해 같은 내용을 `DRUG_SERVICE_BUILD_README.md`에도 둡니다.

이 작업공간은 아래 순서로 구축합니다.

```text
1. PostgreSQL canonical load
2. FastAPI
3. React
4. Neo4j graph
5. OpenSearch
6. Neo4j path scoring
7. KG embedding baseline
8. Pipeline run control API
9. Bedrock RAG/LLM explanation
10. AlphaFold structure viewer extension
```

원본 데이터는 아래 S3 경로에 그대로 둡니다.

```text
s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/
```

빌드 산출물은 아래 경로에 저장합니다.

```text
s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/
```

프론트엔드 인수인계는 `FRONTEND_HANDOFF_v1.md`를 확인합니다.
Pipeline run control API 전용 인수인계는 `docs/pipeline_run_frontend_handoff_v1.md`를 확인합니다.
Pipeline run backend alias 검증은 `docs/pipeline_run_backend_alias_validation_v1.md`를 확인합니다.
AlphaFold 구조보기 schema 초안은 `docs/alphafold_structure_schema_v1.md`를 확인합니다.
AlphaFold 무결성 검증 결과는 `docs/alphafold_integrity_validation_v1.md`를 확인합니다.
AlphaFold target 매핑 후보는 `docs/alphafold_target_mapping_plan_v1.md`와 `10_alphafold/`를 확인합니다.
AlphaFold target 매핑 후보 재검증은 `docs/alphafold_target_mapping_integrity_v1.md`를 확인합니다.
Target/UniProt 매핑 정책과 검토표는 `docs/target_mapping_policy_and_review_v1.md`를 확인합니다.
UniProt 자동 매핑 검증 결과는 `docs/uniprot_auto_mapping_validation_v1.md`를 확인합니다.
UniProt 자동 매핑 무결성 검증은 `docs/uniprot_auto_mapping_integrity_v1.md`를 확인합니다.
UniProt/target 중복 검증은 `docs/uniprot_mapping_duplicate_check_v1.md`를 확인합니다.
Reviewed UniProt seed 생성 결과는 `docs/reviewed_seed_integrity_v1.md`와 `10_alphafold/*_seed_reviewed_v1.csv`를 확인합니다.
Reviewed UniProt seed DB 적재 dry-run 검증은 `docs/reviewed_seed_db_load_validation_v1.md`를 확인합니다.
Structure targets API 검증은 `docs/structures_targets_api_validation_v1.md`를 확인합니다.
AlphaFold DB metadata 조회 정책은 `docs/alphafold_metadata_lookup_policy_v1.md`를 확인합니다.
AlphaFold DB metadata 조회 검증은 `docs/alphafold_metadata_lookup_validation_v1.md`와 `10_alphafold/alphafold_structures_seed_candidates_v1.csv`를 확인합니다.
AlphaFold DB metadata 적재 검증은 `docs/alphafold_metadata_db_load_validation_v1.md`를 확인합니다.
Structure detail API 검증은 `docs/structures_detail_api_validation_v1.md`를 확인합니다.
Structure API 무결성 재검증은 `docs/structure_api_integrity_recheck_v1.md`를 확인합니다.
Candidate-protein-structure context link 검증은 `docs/candidate_structure_links_validation_v1.md`를 확인합니다.
Structure API 최종 검증은 `docs/structure_api_final_validation_v1.md`를 확인합니다.
프론트엔드 structure API 전달 문서는 `FRONTEND_HANDOFF_STRUCTURE_API_v1.md`를 확인합니다.
AlphaFold JAK1 pilot file proxy 검증은 `docs/alphafold_pilot_file_proxy_validation_v1.md`를 확인합니다.
AlphaFold 전체 file proxy 검증은 `docs/alphafold_full_file_proxy_validation_v1.md`를 확인합니다.
API smoke test와 OpenSearch evidence 검색 준비 검증은 `docs/api_smoke_and_search_readiness_v1.md`를 확인합니다.
Final candidates와 broader candidate pool 분리 검증은 `docs/final_candidates_candidate_pool_split_v1.md`를 확인합니다.
Candidate layer 무결성과 OpenSearch candidate_pool 확장 검증은 `docs/candidate_layer_integrity_and_search_v1.md`를 확인합니다.
RAG/Bedrock explanation retrieval 계약은 `docs/rag_bedrock_retrieval_contract_v1.md`를 확인합니다.
RAG/Bedrock retrieval 계약 작성 후 연결 재검증은 `docs/rag_bedrock_retrieval_connection_validation_v1.md`를 확인합니다.
프론트 v1 연결 QA 통과 기록은 `docs/frontend_v1_connection_qa_pass_20260514.md`를 확인합니다.
Explanation context API 검증은 `docs/explanation_context_api_validation_v1.md`를 확인합니다.
Assistant/chatbot team API 검증은 `docs/assistant_api_validation_v1.md`를 확인합니다.
백엔드/DB 전체 무결성과 프론트 전달 준비 검증은 `docs/backend_db_integrity_frontend_handoff_v1.md`를 확인합니다.
프론트 API 전달 목록과 전체 워크플로우는 `docs/frontend_api_handoff_workflow_v1.md`를 확인합니다.

## TxGNN 제외 결정

TxGNN은 외부 biomedical KG 기반 확장 후보로 검토했습니다. 그러나 현재 프로젝트 후보 약물과 TxGNN/DrugBank node의 매칭 coverage가 제한적이고, Python 3.8 + DGL 0.5.2 실행환경과 EC2 비용 부담이 큽니다.

따라서 v1/v2 구현 범위에서는 TxGNN을 제외하고, 아래 3개 레이어를 우선 진행합니다.

```text
1. Neo4j path scoring
2. DistMult/TransE KG embedding baseline
3. Bedrock RAG/LLM explanation
```

## GitHub/S3 제외 항목

아래 항목은 누락이 아니라 의도적으로 제외합니다.

```text
.venv
node_modules
Docker volume
PostgreSQL/Neo4j/OpenSearch 실제 데이터 디렉터리
__pycache__, *.pyc
frontend dist/build output
원본 WSI/이미지/embedding 대용량 파일
```

GitHub와 S3에는 재현 가능한 코드, 설정, schema, 정규화 CSV, 검증 리포트를 올립니다. 실행환경과 로컬 cache/build 산출물은 `requirements.txt`, `package.json`, Docker Compose 파일을 기준으로 다시 생성합니다.

## 전체 로컬/EC2 스택 실행

```bash
cd drug_service_build
docker compose up --build
```

PostgreSQL 적재, FastAPI, Neo4j를 실행합니다. FastAPI 주소:
OpenSearch text index도 함께 생성합니다.

```text
http://localhost:8010
```

API health 확인:

```text
http://localhost:8010/health
http://localhost:8010/health/graph
```

Graph 관계 API:

```text
http://localhost:8010/graph/relations?disease_id=RA&limit=50
```

Neo4j path scoring API:

```text
http://localhost:8010/graph/path-score?disease_id=RA&limit=100
```

KG embedding baseline API:

```text
http://localhost:8010/health/kg-embedding
http://localhost:8010/graph/kg-embedding?disease_id=RA&model=ensemble&limit=50
```

OpenSearch text search API:

```text
http://localhost:8010/health/search
http://localhost:8010/search?q=JAK&disease_id=RA
```

Explanation context API:

```text
http://localhost:8010/api/explanation-context?disease_id=RA&drug_name=Ruxolitinib
http://localhost:8010/api/explanation-context?disease_id=BRCA&drug_name=Oxaliplatin
```

Pipeline run control API:

```text
POST /api/pipeline-runs/preflight
POST /api/pipeline-runs
GET /api/pipeline-runs
GET /api/pipeline-runs/{run_id}
GET /api/pipeline-runs/{run_id}/events
GET /api/pipeline-runs/{run_id}/artifacts
POST /api/pipeline-runs/{run_id}/cancel
POST /api/pipeline-runs/{run_id}/complete
```

Run 목록 조회는 `requested_by` 필터도 지원합니다. 예: `GET /api/pipeline-runs?requested_by=frontend&limit=20`.

현재 단계에서는 기본 실행 backend가 `mock`입니다. `local_agent`와 `aws_stepfunctions`는 feature flag 없이 실제 실행되지 않으며, 비용 발생 AWS job은 launch하지 않습니다.
`execution_backend` 입력은 특수문자 alias도 허용합니다: `$=mock`, `@=local_agent`, `#=aws_stepfunctions`.
`disease_name` 앞에 `$`, `@`, `#`를 붙이는 입력도 허용합니다. 예: `$알츠하이머`, `@류마티스 관절염`, `#폐암`.
신규 질환은 실제 실행하지 않고 `blocked / needs_registration`으로 저장합니다.

Structure targets API:

```text
GET /api/structures/targets
GET /api/structures/targets?disease_id=RA
GET /api/structures/targets?q=JAK
GET /api/structures?disease_id=RA
GET /api/structures?q=JAK
GET /api/structures/{structure_id}
GET /api/structures/{structure_id}/file
```

현재는 구조 파일이 아니라 `target -> protein -> UniProt` 후보 목록을 반환합니다. `alphafold_structures`가 비어 있으므로 `structure_status`는 `not_loaded`입니다.
AlphaFold DB metadata를 적재한 뒤에는 구조 파일 다운로드 전 상태이므로 `structure_status`는 `pending`입니다.
AlphaFold 구조 파일 27건은 S3 저장과 API proxy 제공이 완료되어 `structure_status=available`입니다.

Neo4j Browser 주소:

```text
http://localhost:7474
```

## React v1 실행

```bash
cd frontend
npm install
npm run dev
```

React v1 주소:

```text
http://localhost:5173
```

## API-only 로컬 확인

PostgreSQL이 host의 `5433` 포트에서 이미 실행 중일 때만 사용합니다.

```bash
cd drug_service_build
docker compose -f docker-compose.api-local.yml up --build
```
