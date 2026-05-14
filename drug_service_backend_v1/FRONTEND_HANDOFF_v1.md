# 프론트엔드 인수인계 v1

## 현재 API

FastAPI 서비스는 현재 이 로컬 머신에서 실행 중입니다.

```text
API_BASE_URL=http://172.16.0.64:8010
Swagger=http://172.16.0.64:8010/docs
Health=http://172.16.0.64:8010/health
Graph Health=http://172.16.0.64:8010/health/graph
```

## 현재 React v1

React v1 개발 서버도 현재 이 로컬 머신에서 실행 중입니다.

```text
Local=http://localhost:5173/
Network=http://172.16.0.64:5173/
```

React v1은 최종 프론트엔드가 아니라 **PostgreSQL/FastAPI 연결 검증용 화면**입니다. 프론트 담당자는 이 화면을 먼저 확인해서 현재 데이터 구조를 이해하면 됩니다. 본격적인 UI 작업은 Neo4j/OpenSearch API와 이후 path scoring/RAG endpoint가 연결된 뒤 React v2에서 진행하는 것이 좋습니다.

Vite 프론트엔드에서는 아래 값을 사용합니다.

```env
VITE_API_BASE_URL=http://172.16.0.64:8010
```

두 컴퓨터는 같은 LAN/Wi-Fi에 있어야 합니다. 다른 컴퓨터에서 URL이 열리지 않으면 네트워크 분리 여부나 API 호스트의 macOS 방화벽을 확인해야 합니다.

## 구현된 엔드포인트

```text
GET /health
GET /health/graph
GET /diseases
GET /drugs?disease_id=BRCA
GET /api/diseases/{disease_code}/candidates
GET /v1/diseases/{disease_code}/candidates
GET /v1/diseases/{disease_code}/final-candidates
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
GET /search?q=Ruxolitinib&doc_type=candidate_pool
GET /search?q=Oxaliplatin&disease_id=BRCA&doc_type=candidate_pool
POST /api/pipeline-runs
GET /api/pipeline-runs
GET /api/pipeline-runs/{run_id}
GET /api/pipeline-runs/{run_id}/events
GET /api/pipeline-runs/{run_id}/artifacts
POST /api/pipeline-runs/{run_id}/cancel
POST /api/pipeline-runs/{run_id}/complete
```

## 프론트엔드 주의사항

- 질병 ID는 `BRCA`, `Colon`, `HNSC`, `IPF`, `LUNG`, `Liver`, `PAH`, `PDAC`, `Psoriasis`, `RA`, `STAD`입니다.
- 기본 후보 화면은 `GET /v1/diseases/{disease_code}/final-candidates`를 사용합니다.
- 전체 후보 보기(`view=all`)는 `GET /api/diseases/{disease_code}/candidates`를 사용합니다.
- 전체 후보 응답의 `is_final_candidate` 값으로 “최종 후보 / 탈락” 표시를 구분합니다.
- 전체 후보 검색은 `GET /search?q={query}&doc_type=candidate_pool`를 사용합니다.
- `candidate_pool` 검색은 같은 질환 안 같은 `drug_name`을 기본 collapse해서 1개만 반환합니다.
- 중복 원천 row 수는 `raw_total`, `provenance_count`, `provenance_note`로 표시합니다.
- `OV`, `SKCM`은 의도적으로 제외했습니다.
- 일반 약물 후보와 image-modal evidence를 연결할 때는 `canonical_drug_id`를 사용합니다.
- 같은 질병 안의 후보/score/result 목록에서는 같은 `canonical_drug_id`를 중복 표시하지 않습니다.
- 같은 약물이 여러 질병에 등장하는 것은 오류가 아니라 cross-disease 관계성 분석 대상입니다.
- `match_status = evidence_only`는 해당 약물이 main candidate table에는 없고 image-modal evidence에만 있다는 뜻입니다.
- `cluster_label`이 비어 있으면 `cluster_key`를 표시합니다.
- v1에서는 `target`, `target_pathway`를 raw text 그대로 표시합니다. Target 정규화는 Neo4j/OpenSearch/path scoring 이후 보강합니다.
- `target`이 항상 gene이라고 가정하면 안 됩니다. gene/pathway/mechanism/free-text가 섞여 있습니다.

## React v1 검증 결과

로컬에서 아래 항목을 확인했습니다.

```text
npm run build
Browser: http://localhost:5173/
API health: connected
BRCA: 15 candidates, 4 clusters, 32 evidence rows
RA: 30 candidates, 2 clusters, 32 evidence rows
Drug row selection: Ruxolitinib 선택 시 image-modal evidence 2개 표시
```

## 프론트 v1 연결 QA 통과

프론트 담당자가 2026-05-14 기준 `5174` 프론트에서 6개 QA 항목을 확인했고, 연결 QA는 PASS로 기록합니다.

```text
BRCA final-candidates: 15개, 중복 없음
BRCA candidates view=all: 60개, final 15 / non-final 45, 중복 없음
Oxaliplatin candidate_pool search: total 1, raw_total 2, provenance_count 2
JAK1/JAK2/JAK3 structure_status=available
JAK1 file proxy: GET /api/structures/af_p23458_f1_v6/file 정상
RA graph: nodes 71, edges 132
/diseases: 11개 질환 확인
```

상세 기록은 `docs/frontend_v1_connection_qa_pass_20260514.md`를 확인합니다.

## 백엔드/DB 전체 무결성 PASS

프론트 전달 전 backend/DB 전체 무결성 검증은 PASS입니다.

```text
PostgreSQL FK/고아 데이터 문제 없음
API 표시 계층 drug_name 중복 0
OpenSearch 1131 docs 정상
Neo4j graph count/API 정상
AlphaFold 27 structures available
candidate_protein_structure_links 261건 복구/확인 완료
Explanation context API ready
```

상세 기록은 `docs/backend_db_integrity_frontend_handoff_v1.md`를 확인합니다.

## 프론트 API 전달 목록과 전체 워크플로우

프론트 담당자에게 전달할 endpoint 목록, 화면 연결 흐름, 전체 데이터 흐름은 아래 문서를 기준으로 합니다.

```text
docs/frontend_api_handoff_workflow_v1.md
```

## React v2 인수인계 메모

나중에 React v2를 전달할 때 아래 맥락을 함께 전달합니다.

```text
React v1은 PostgreSQL/FastAPI 연결 검증용 화면으로 완료되었습니다.
React v2 작업 전에 React v1을 먼저 확인해서 질병 선택, 약물 후보 테이블,
image-modal evidence 연결 방식, 주의사항을 파악해주세요.
본격적인 프론트엔드 구현은 PostgreSQL, Neo4j, OpenSearch 엔드포인트가
모두 연결된 React v2 기준으로 진행하는 것이 좋습니다.
```

React v2에서 함께 논의할 graph/API 항목:

```text
- Alias 표시는 PostgreSQL/FastAPI에서 제공할 수 있고, graph search는 Neo4j의 DrugAlias/DiseaseAlias 노드를 사용할 수 있습니다.
- match_status = evidence_only는 ranked main candidate가 아니라 supporting evidence 전용 약물로 표시해야 합니다.
- target/pathway가 비어 있는 candidate row 62개는 v2 보강 대상으로 관리합니다.
- TargetConcept 값은 raw text이며, 이후 Gene, Pathway, Mechanism, DrugClass, FreeText로 분류해야 합니다.
- TxGNN은 v1/v2 구현 범위에서 제외합니다. 비용/환경 부담 대비 현재 후보 약물 coverage가 낮아, 우선 path scoring과 KG embedding을 사용합니다.
- Graph API v1은 react-force-graph 같은 graph viewer와 맞추기 위해 { nodes: [], edges: [] } 형태로 반환하는 것이 좋습니다.
- `/graph/relations`는 빈 image cluster도 `Disease -> ImageCluster`로 포함합니다. 약물 근거가 있는 경우에만 `ImageCluster -> ImageEvidence -> Drug`로 이어집니다.
- Graph edge type은 `CANDIDATE_FOR`, `HAS_IMAGE_CLUSTER`, `HAS_IMAGE_EVIDENCE`, `SUPPORTS_DRUG`, `HAS_TARGET`, `MENTIONS_TARGET`를 예상하면 됩니다.
- OpenSearch text search v1은 `/search`로 연결했습니다. `candidate_pool`, `drug_candidate`, `image_evidence`, `image_report`를 검색합니다.
- `candidate_pool` 검색은 기본적으로 dedup/collapse된 화면용 결과를 반환하고, 원천 row는 `include_provenance=true`로 확인합니다.
- Vector search는 아직 제외이며 CT-CLIP/UNI2 embedding 원본과 차원 정책 확정 뒤 v2로 추가합니다.
- Bedrock/RAG 설명 기능은 아직 붙이지 않았고, prompt에 넣을 backend retrieval 계약은 `docs/rag_bedrock_retrieval_contract_v1.md`에 정리했습니다.
- Bedrock 호출 전 설명용 근거 패키지는 `GET /api/explanation-context?disease_id=RA&drug_name=Ruxolitinib`로 받을 수 있습니다.
- Neo4j path scoring v1은 `/graph/path-score`로 연결했습니다. 프론트는 `path_score`만 보여주지 말고 `components`, `evidence_sources`, `risk_sources`를 함께 표시하는 구성이 좋습니다.
- DistMult/TransE KG embedding baseline은 `/graph/kg-embedding`으로 연결했습니다. 이 점수는 graph 구조 학습 기반 보조 점수이므로 단독 추천 근거로 쓰지 말고 path score/evidence/risk와 함께 표시해야 합니다.
- Pipeline run control API는 챗봇/Bedrock/RAG가 나중에 호출할 제어 계층입니다. 현재는 `mock` backend만 실제 동작하며, `local_agent`와 `aws_stepfunctions`는 feature flag 없이는 비용 발생 실행을 하지 않습니다.
- 다음 모델/설명 레이어는 `Bedrock RAG/LLM explanation`입니다.
```

## Pipeline run control API

이 API는 React v1 화면용 핵심 기능이 아니라, 이후 챗봇/Bedrock/RAG가 파이프라인 실행 상태를 백엔드로 조회할 수 있게 준비한 연결 지점입니다.

프론트엔드 전용 상세 인수인계는 아래 문서를 기준으로 합니다.

```text
docs/pipeline_run_frontend_handoff_v1.md
```

예시 요청:

```json
{
  "disease_name": "난소암",
  "mode": "full",
  "execution_backend": "mock"
}
```

주의사항:

```text
- 기본 backend는 mock입니다.
- `GET /api/pipeline-runs`로 최근 실행 목록을 조회할 수 있습니다.
- `POST /api/pipeline-runs/{run_id}/complete`는 mock run의 완료 상태 UI 검증용입니다.
- local_agent / aws_stepfunctions는 skeleton만 있으며 feature flag 없이는 blocked 처리됩니다.
- SageMaker, Step Functions, WSI 다운로드, 대용량 embedding 생성은 이 단계에서 실행하지 않습니다.
- secret/API key는 DB에 저장하지 않습니다.
```

## Backend 연결 상태

현재 FastAPI는 PostgreSQL과 Neo4j 모두 연결되어 있습니다.

```text
GET /health       -> {"status":"ok","database":"ok"}
GET /health/graph -> {"status":"ok","graph":"ok"}
```

Graph relation endpoint도 추가했습니다.

```text
GET /graph/relations?disease_id=RA&limit=50
```

응답은 React graph viewer에서 쓰기 쉽게 아래 형태로 반환합니다.

```json
{
  "disease_id": "RA",
  "nodes": [],
  "edges": []
}
```

검증 결과:

```text
11개 질병 전체 limit=200 검증 완료
Duplicate node id: 0
Duplicate edge id: 0
Broken edge endpoint: 0
Neo4j import CSV 대비 candidate/support/cluster/target edge count mismatch: 0
```

## 원본 데이터와 빌드 위치

원본 S3 데이터는 수정하지 않습니다.

```text
s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/
```

빌드 산출물과 인수인계 파일은 아래 경로에 복사합니다.

```text
s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/
```

## S3에서 내려받은 뒤 로컬 실행

```bash
cd drug_service_build
docker compose up -d --build
```

이후 아래 주소를 엽니다.

```text
http://localhost:8010/docs
```

React 프론트엔드 실행:

```bash
cd frontend
npm install
npm run dev
```
