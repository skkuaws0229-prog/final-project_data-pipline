# React v2 API 계약서

이 문서는 React v2 frontend가 FastAPI backend에 연결할 때 사용할 API 계약입니다.

## 기본 정보

로컬 개발 기본 주소:

```text
API_BASE_URL=http://localhost:8010
Swagger=http://localhost:8010/docs
```

같은 네트워크의 다른 PC에서 접속할 때는 API가 실행 중인 PC의 IP를 사용합니다.

```text
API_BASE_URL=http://{API_HOST_IP}:8010
```

현재 테스트된 LAN 예시:

```text
API_BASE_URL=http://172.16.0.64:8010
```

## 질병 ID

React v2에서 사용할 질병 ID는 아래 11개입니다.

```text
BRCA, Colon, HNSC, IPF, LUNG, Liver, PAH, PDAC, Psoriasis, RA, STAD
```

`OV`, `SKCM`은 의도적으로 제외했습니다.

## 1. Health

### GET /health

PostgreSQL 연결 상태를 확인합니다.

응답 예시:

```json
{
  "status": "ok",
  "database": "ok"
}
```

### GET /health/graph

Neo4j 연결 상태를 확인합니다.

응답 예시:

```json
{
  "status": "ok",
  "graph": "ok"
}
```

### GET /health/kg-embedding

KG embedding score CSV 연결 상태를 확인합니다.

응답 예시:

```json
{
  "status": "ok",
  "kg_embedding": "ok",
  "score_rows": 1870
}
```

## 2. Disease 목록

### GET /diseases

질병 목록과 후보 약물 수를 반환합니다.

응답 필드:

```text
disease_id       string
display_name     string
candidate_count  number
```

응답 예시:

```json
[
  {
    "disease_id": "RA",
    "display_name": "RA",
    "candidate_count": 30
  }
]
```

프론트 사용처:

```text
질병 선택 select/tab
질병별 후보 약물 수 표시
```

## 3. 후보 약물 목록

### GET /drugs

질병별 후보 약물 목록을 반환합니다.

Query:

```text
disease_id  required string
limit       optional number, default 100, max 500
offset      optional number, default 0
```

예시:

```text
GET /drugs?disease_id=RA&limit=100
```

주요 응답 필드:

```text
candidate_id
disease_id
drug_id
canonical_drug_id
drug_name
rank
tier
score
target
target_pathway
evidence_summary
canonical_smiles
safety_score
verdict
admet_status
hard_fail
hard_fail_reasons
soft_flags
```

프론트 사용처:

```text
약물 후보 테이블
rank/tier/safety_score/verdict 표시
ADMET 필터
약물 row 선택
```

주의사항:

- 약물 연결 기준은 `canonical_drug_id`입니다.
- `target`, `target_pathway`는 raw text입니다.
- target 값을 모두 gene으로 간주하면 안 됩니다.
- `hard_fail`, `hard_fail_reasons`, `soft_flags`는 문자열로 내려옵니다.

## 4. 약물 상세

### GET /drugs/{drug_id}

source `drug_id` 기준으로 약물 상세와 질병별 후보 이력을 반환합니다.

예시:

```text
GET /drugs/drug_brca_0001
```

응답 필드:

```text
drug_id
drug_name
canonical_smiles
first_seen_disease_id
candidates[]
```

프론트 사용처:

```text
약물 detail panel
다른 질병에서도 후보로 등장했는지 확인
SMILES 표시
```

## 5. Image-modal cluster

### GET /image-modal/clusters

질병별 image-modal cluster 목록을 반환합니다.

Query:

```text
disease_id required string
```

예시:

```text
GET /image-modal/clusters?disease_id=RA
```

응답 필드:

```text
cluster_id
disease_id
cluster_key
cluster_label
n_observations
clinical_summary
pathway_summary
source_file
```

주의사항:

- `cluster_label`이 비어 있으면 `cluster_key`를 표시합니다.
- cluster는 환자/병리 cluster 기반 요약이지 이미지 파일 자체가 아닙니다.

## 6. Image-modal evidence

### GET /image-modal/evidence

질병별 또는 cluster별 image-modal drug evidence를 반환합니다.

Query:

```text
disease_id required string
cluster_id optional string
drug_name  optional string
limit      optional number, default 100, max 500
```

예시:

```text
GET /image-modal/evidence?disease_id=RA&limit=100
GET /image-modal/evidence?disease_id=RA&cluster_id=imcluster_xxx
```

응답 필드:

```text
evidence_id
disease_id
cluster_id
cluster_key
cluster_label
drug_id
canonical_drug_id
match_status
drug_name
rank
tier
target
target_pathway
evidence_text
source_file
```

프론트 사용처:

```text
선택한 약물의 image-modal 근거 panel
cluster별 추천 근거 표시
evidence_only 약물 표시
```

주의사항:

- `match_status = matched`: 후보 약물 테이블과 매칭된 evidence입니다.
- `match_status = evidence_only`: main candidate table에는 없고 image-modal evidence에만 있는 약물입니다.
- `evidence_text`는 추천 근거 요약이며 WSI 이미지 원본이 아닙니다.

## 7. Image-modal report

### GET /image-modal/reports

질병별 image-modal report text를 반환합니다.

Query:

```text
disease_id required string
```

예시:

```text
GET /image-modal/reports?disease_id=BRCA
```

응답 필드:

```text
report_id
disease_id
report_kind
title
report_text
source_file
```

프론트 사용처:

```text
질병별 image-modal 분석 요약
근거 전문 보기
```

## 8. Graph relations

### GET /graph/relations

React graph viewer에서 바로 사용할 수 있는 `{ nodes: [], edges: [] }` 형태의 graph 응답입니다.

Query:

```text
disease_id        required string
limit             optional number, default 50, max 200
include_evidence  optional boolean, default true
include_targets   optional boolean, default true
```

예시:

```text
GET /graph/relations?disease_id=RA&limit=50
GET /graph/relations?disease_id=RA&limit=200&include_evidence=true&include_targets=true
```

응답 형태:

```json
{
  "disease_id": "RA",
  "nodes": [
    {
      "id": "RA",
      "label": "Disease",
      "name": "RA",
      "properties": {
        "disease_id": "RA"
      }
    }
  ],
  "edges": [
    {
      "id": "CANDIDATE_FOR:candidate_xxx",
      "source": "canonical_drug_xxx",
      "target": "RA",
      "type": "CANDIDATE_FOR",
      "properties": {}
    }
  ]
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

Graph 구조:

```text
Drug -> Disease
Disease -> ImageCluster
ImageCluster -> ImageEvidence
ImageEvidence -> Drug
Drug -> TargetConcept
ImageEvidence -> TargetConcept
```

주의사항:

- 약물 근거가 없는 빈 cluster도 `Disease -> ImageCluster`로 포함됩니다.
- evidence-only 약물도 `Drug` node로 포함됩니다.
- `TargetConcept`는 raw text입니다.
- TxGNN 예측 edge는 v1/v2 구현 범위에서 제외합니다. 다음 graph score layer는 KG embedding입니다.

## 9. Path scoring

### GET /graph/path-score

Neo4j graph와 기존 candidate/ADMET/image-modal evidence를 이용해 설명 가능한 약물-질병 기준 점수를 반환합니다.

Query:

```text
disease_id required string
limit      optional number, default 100, max 200
```

응답 예시:

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
      "components": {
        "candidate_rank": 0.3,
        "admet": 0.2,
        "image_evidence": 0.1667,
        "target_overlap": 0.0
      },
      "evidence_sources": [],
      "risk_sources": []
    }
  ]
}
```

주의사항:

- `limit`은 반환 개수만 제어하며 rank 정규화 기준은 질병 전체 후보군입니다.
- 같은 `canonical_drug_id`가 여러 candidate row에 있어도 API 응답에서는 가장 높은 `path_score` 1개만 반환합니다.
- `evidence_sources`는 지원 근거, `risk_sources`는 ADMET 기반 감점/주의 근거입니다.
- RAG/LLM 설명과 프론트엔드 상세 패널은 점수만 사용하지 말고 source/risk를 함께 사용해야 합니다.

## 10. KG embedding baseline

### GET /graph/kg-embedding

DistMult/TransE KG embedding baseline 점수를 반환합니다.

Query:

```text
disease_id required string
model      optional string: distmult, transe, ensemble
limit      optional number, default 50, max 200
```

응답 예시:

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

주의사항:

- KG embedding score는 graph 구조 학습 기반 보조 점수입니다.
- Path scoring처럼 source/risk를 설명하는 점수가 아니므로 단독 추천 근거로 사용하지 않습니다.
- `is_known_candidate=false`는 현재 candidate table에는 없지만 graph embedding이 drug-disease 유사성을 높게 본 약물입니다.

## 11. Drug uniqueness rule

아래 규칙은 모든 후보/score/result API에 적용합니다.

```text
같은 질병 안에서는 같은 canonical_drug_id를 중복 노출하지 않습니다.
같은 약물이 여러 질병에 등장하는 것은 cross-disease 관계성 분석 대상으로 유지합니다.
image-modal evidence의 다중 cluster 근거 row는 삭제하지 않고 evidence source로 보존합니다.
```

검증 산출물:

```text
drug_service_db_v1/05_validation/drug_uniqueness_api_summary_v1.csv
drug_service_db_v1/05_validation/cross_disease_drug_relations_v1.csv
drug_service_db_v1/05_validation/drug_uniqueness_validation_v1.md
```

## 12. Text search

### GET /health/search

OpenSearch 연결 상태를 확인합니다.

응답 예시:

```json
{
  "status": "ok",
  "search": "ok"
}
```

### GET /search

OpenSearch text search 결과를 반환합니다.

Query:

```text
q          required string
disease_id optional string
doc_type   optional string: drug_candidate, image_evidence, image_report
limit      optional number, default 20, max 50
```

예시:

```text
GET /search?q=JAK&disease_id=RA
GET /search?q=immune&doc_type=image_evidence
```

응답 필드:

```text
query
total
hits[]
hits[].id
hits[].score
hits[].doc_type
hits[].disease_id
hits[].title
hits[].drug_name
hits[].canonical_drug_id
hits[].cluster_id
hits[].match_status
hits[].source_file
hits[].snippet
hits[].highlights
hits[].source
```

지원 document type:

```text
drug_candidate: PostgreSQL 후보 약물 + ADMET
image_evidence: image-modal drug evidence + cluster summary
image_report: image-modal report 본문
```

주의사항:

- 이 endpoint는 text search입니다.
- vector search는 아직 포함하지 않았습니다.
- 검색 대상 문서는 총 699개입니다.
- `snippet`에는 OpenSearch highlight 첫 fragment 또는 fallback text가 들어갑니다.

## 공통 에러 처리

존재하지 않는 `disease_id`:

```text
HTTP 404
```

예시:

```json
{
  "detail": "Unknown disease_id: TEST"
}
```

Neo4j 연결 실패:

```text
HTTP 503
```

## React v2 구현 우선순위 제안

프론트 구현 자체는 프론트엔드 담당자가 결정합니다. 다만 API 연결 우선순위는 아래 순서가 좋습니다.

```text
1. /health, /health/graph 연결 상태 표시
2. /diseases 질병 선택
3. /drugs 후보 약물 테이블
4. /image-modal/evidence 약물별 근거 panel
5. /graph/relations graph viewer
6. /search text search
7. /image-modal/reports 상세 report 보기
```
