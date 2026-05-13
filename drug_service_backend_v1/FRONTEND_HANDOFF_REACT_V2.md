# React v2 프론트엔드 인수인계

## 현재 backend 상태

현재 v1 backend는 아래 범위까지 연결되어 있습니다.

```text
PostgreSQL: 연결 완료
Neo4j: 연결 완료
FastAPI: 구현 완료
Graph API: /graph/relations 검증 완료
OpenSearch: text search 연결 완료
Path scoring: /graph/path-score 검증 완료
KG embedding: /graph/kg-embedding 검증 완료
Pipeline run control API: mock backend 검증 완료
TxGNN: v1/v2 구현 범위에서 제외
RAG/LLM: 아직 미연결
```

React v2는 PostgreSQL + Neo4j + OpenSearch + path scoring + KG embedding 기반 화면을 먼저 붙이고, pipeline run control API는 이후 챗봇/Bedrock/RAG 연결 전 상태조회 패널로 붙이는 방향이 좋습니다.

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
GET /graph/path-score?disease_id=RA&limit=100
GET /health/kg-embedding
GET /graph/kg-embedding?disease_id=RA&model=ensemble&limit=50
GET /health/search
GET /search?q=JAK&disease_id=RA
POST /api/pipeline-runs
GET /api/pipeline-runs
GET /api/pipeline-runs/{run_id}
GET /api/pipeline-runs/{run_id}/events
GET /api/pipeline-runs/{run_id}/artifacts
POST /api/pipeline-runs/{run_id}/cancel
POST /api/pipeline-runs/{run_id}/complete
```

## 데이터 매칭 규칙

약물 연결 기준:

```text
canonical_drug_id
```

중복 기준:

```text
같은 질병 안의 후보/score/result 목록에서는 같은 canonical_drug_id를 중복 표시하지 않음
같은 약물이 여러 질병에 등장하는 것은 오류가 아니라 cross-disease 관계성 분석 대상
image-modal evidence는 같은 약물이 여러 cluster 근거로 여러 번 나올 수 있으므로 근거 row는 보존
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

## Path scoring 참고

`/graph/path-score`는 Neo4j graph와 기존 candidate/ADMET/image-modal evidence를 이용해 설명 가능한 기준 점수를 반환합니다.

```json
{
  "disease_id": "RA",
  "scoring_version": "path_scoring_v1",
  "scores": [
    {
      "canonical_drug_id": "cdrug_xxx",
      "drug_name": "Ruxolitinib",
      "rank": 1,
      "tier": "pass_admet_gate",
      "path_score": 0.6667,
      "positive_score": 0.6667,
      "risk_penalty": 0.0,
      "components": {},
      "evidence_sources": [],
      "risk_sources": []
    }
  ]
}
```

프론트 표시 제안:

```text
path_score: 정렬/요약 점수
components: rank, ADMET, image evidence, target overlap 분해 표시
evidence_sources: 근거 펼침 영역
risk_sources: 주의/감점 근거 영역
```

주의: `path_score`는 최종 임상 판단 점수가 아니라 설명 가능한 내부 기준 점수입니다. 점수만 단독 표시하지 말고 source와 risk를 같이 보여주는 것이 좋습니다.

## KG embedding 참고

`/graph/kg-embedding`은 DistMult/TransE baseline 점수를 반환합니다.

```json
{
  "disease_id": "RA",
  "model": "ensemble",
  "scoring_version": "kg_embedding_v1",
  "scores": [
    {
      "canonical_drug_id": "cdrug_xxx",
      "drug_name": "BRANEBRUTINIB",
      "kg_score": 0.987658,
      "distmult_score": 1.0,
      "transe_score": 0.975316,
      "ensemble_score": 0.987658,
      "is_known_candidate": true,
      "candidate_rank": 3,
      "candidate_tier": "pass_admet_gate"
    }
  ]
}
```

프론트 표시 제안:

```text
KG score는 별도 보조 점수 컬럼 또는 모델 tab으로 표시
is_known_candidate=false 항목은 신규 후보/확장 후보로 구분
KG score만으로 추천 문구를 만들지 말고 path_score/evidence/risk와 함께 표시
```

## Pipeline run control API 참고

`/api/pipeline-runs`는 Bedrock/RAG/LLM 챗봇이 나중에 파이프라인을 직접 실행하지 않고 backend API만 호출하게 하기 위한 제어 계층입니다.

현재는 mock backend만 실제 동작합니다.

```json
{
  "disease_name": "난소암",
  "mode": "full",
  "execution_backend": "mock"
}
```

프론트 표시 제안:

```text
run status: queued/running/completed/failed/cancelled/blocked
current_step: 현재 단계 표시
events: timeline/log panel
artifacts: 결과 report/csv/json link 목록
complete button: mock run의 완료 상태 UI 검증용
```

주의:

```text
local_agent와 aws_stepfunctions는 skeleton만 있습니다.
feature flag 없이는 실제 실행되지 않고 blocked 처리됩니다.
SageMaker, Step Functions, WSI 다운로드, 대용량 embedding 생성은 이 단계에서 실행하지 않습니다.
secret/API key는 DB에 저장하지 않습니다.
```

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

Path scoring v1 검증:

```text
11개 질병 전체 검증 완료
Score rows: 247
Duplicate canonical_drug_id: 0
Out-of-range score: 0
Missing evidence_sources: 0
상세 리포트: drug_service_backend_v1/08_path_scoring/path_score_validation_v1.md
```

Drug uniqueness 검증:

```text
/drugs duplicate canonical_drug_id: 0
/graph/relations CANDIDATE_FOR duplicate drug: 0
/graph/path-score duplicate canonical_drug_id: 0
Cross-disease related drugs: 43
Source candidate duplicate disease count: 3
상세 리포트: drug_service_db_v1/05_validation/drug_uniqueness_validation_v1.md
```

Source candidate duplicate 3건은 API에서는 중복 노출되지 않지만, 원천 candidate 정규화 단계에서 보강할 대상입니다.

KG embedding 검증:

```text
Triples: 1875
Entities: 775
Relations: 6
Score rows: 1870
Known candidate score rows: 247
질병 내 duplicate canonical_drug_id: 0
상세 리포트: drug_service_backend_v1/09_kg_embedding/kg_embedding_api_validation_v1.md
```

Pipeline run control API v1 검증:

```text
Mock run 생성/상태조회/이벤트조회/artifact조회/취소 완료
Run 목록조회/완료처리/중복완료 guardrail 완료
AWS Step Functions backend guardrail blocked 확인
잘못된 질환명 400 Bad Request 확인
실제 SageMaker/Step Functions job 미실행
상세 리포트: drug_service_backend_v1/docs/pipeline_run_validation_v1.md
```

## 아직 구현하지 않는 것

React v2 초기 구현에서 아래 항목은 제외해도 됩니다.

```text
OpenSearch vector search
RAG explanation
AlphaFold structure viewer
```

TxGNN은 비용/환경 부담 대비 현재 후보 약물 coverage가 낮아 제외합니다. 나머지 항목들은 backend endpoint가 추가된 뒤 React v3 또는 v2 확장으로 붙이는 것이 안전합니다.

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
