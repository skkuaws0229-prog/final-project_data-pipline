# RAG/Bedrock Retrieval 계약 v1

작성일: 2026-05-14

## 목적

Bedrock/LLM 호출을 붙이기 전에, 프론트엔드가 LLM prompt에 넣을 수 있는 근거 패키지의 백엔드 계약을 먼저 정의한다.

이번 단계에서는 Bedrock을 호출하지 않는다.

```text
Frontend
-> Backend explanation context API
-> 표준 JSON 근거 패키지
-> Frontend Bedrock prompt
-> LLM explanation 화면
```

## 역할 분리

| 영역 | 담당 |
|---|---|
| Bedrock 호출 | Frontend 또는 별도 챗봇 레이어 |
| 근거 데이터 조회/정규화 | Backend |
| source_file/provenance/risk 보존 | Backend |
| prompt 구성/UX | Frontend |
| LLM answer 생성 | Bedrock |

핵심 원칙:

```text
LLM은 데이터를 직접 조회하지 않는다.
LLM은 백엔드가 제공한 retrieval_context JSON 안의 근거만 사용한다.
근거 없는 내용은 추측하지 않는다.
```

## 제안 Endpoint

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
search_limit        optional number, default 10
```

사용 예:

```text
GET /api/explanation-context?disease_id=RA&drug_name=Ruxolitinib
GET /api/explanation-context?disease_id=BRCA&drug_name=Oxaliplatin
GET /api/explanation-context?disease_id=RA&canonical_drug_id=CHEMBL1789941
```

## Response Contract

```json
{
  "contract_version": "retrieval_context_v1",
  "disease_id": "RA",
  "drug_name": "Ruxolitinib",
  "canonical_drug_id": "cdrug_xxx",
  "query": {
    "disease_id": "RA",
    "drug_name": "Ruxolitinib",
    "canonical_drug_id": "cdrug_xxx"
  },
  "final_candidate": {
    "candidate_id": "cand_xxx",
    "rank": 1,
    "tier": "pass_admet_gate",
    "score": "0.95",
    "target": "JAK1/JAK2",
    "target_pathway": "JAK-STAT signaling",
    "source_file": "RA_final_admet.csv"
  },
  "candidate_pool": {
    "is_final_candidate": true,
    "provenance_count": 1,
    "provenance_note": "원천 candidate_pool row 1개에서 집계됨",
    "source_files": ["RA_candidates_pool.csv"]
  },
  "admet": {
    "safety_score": "7.1",
    "verdict": "PASS",
    "admet_status": "pass_admet_gate",
    "hard_fail": "0",
    "hard_fail_reasons": "",
    "soft_flags": ""
  },
  "search_context": {
    "candidate_pool_hits": [],
    "final_candidate_hits": [],
    "image_evidence_hits": [],
    "image_report_hits": []
  },
  "graph_context": {
    "path_score": null,
    "positive_score": null,
    "risk_penalty": null,
    "components": {},
    "evidence_sources": [],
    "risk_sources": []
  },
  "structure_context": {
    "available_structures": [],
    "target_genes": [],
    "context_summary": {}
  },
  "retrieval_sources": [
    {
      "source_type": "candidate_pool",
      "source_id": "poolcand_xxx",
      "source_file": "RA_candidates_pool.csv",
      "evidence_role": "support",
      "summary": "Candidate pool row for Ruxolitinib",
      "provenance_count": 1
    }
  ],
  "prompt_guardrails": [
    "Use only the evidence in retrieval_context.",
    "Do not claim clinical efficacy beyond the provided evidence.",
    "Mention risk_evidence when present.",
    "Cite source_file or source_type for key claims."
  ],
  "status": "ready"
}
```

## Retrieval Source 우선순위

1. Final candidate

```text
GET /v1/diseases/{disease_code}/final-candidates
```

사용 목적:

```text
최종 후보 여부, rank, tier, score, target, ADMET 요약
```

2. Candidate pool

```text
GET /api/diseases/{disease_code}/candidates
GET /search?q={drug_name}&disease_id={disease_id}&doc_type=candidate_pool
```

사용 목적:

```text
전체 후보 pool 맥락
is_final_candidate
provenance_count
원천 row 수와 source_file
```

3. Image-modal evidence

```text
GET /image-modal/evidence?disease_id={disease_id}&drug_name={drug_name}
GET /search?q={drug_name}&disease_id={disease_id}&doc_type=image_evidence
```

사용 목적:

```text
환자/병리 cluster 기반 약물 추천 근거
cluster_key
cluster_label
evidence_text
```

4. Image report

```text
GET /image-modal/reports?disease_id={disease_id}
GET /search?q={query}&disease_id={disease_id}&doc_type=image_report
```

사용 목적:

```text
질환별 image-modal 분석 요약
근거 전문 retrieval
```

5. Graph/path score

```text
GET /graph/path-score?disease_id={disease_id}
```

사용 목적:

```text
path_score
components
evidence_sources
risk_sources
```

주의:

```text
path_score는 임상 효능 점수가 아니라 설명 가능한 내부 기준 점수다.
LLM은 반드시 evidence_sources와 risk_sources를 함께 설명해야 한다.
```

6. AlphaFold structure context

```text
GET /api/structures?q={target_gene}
GET /api/structures/{structure_id}
```

사용 목적:

```text
target gene/protein 구조 보기 가능 여부
structure_status
context_summary
관련 질환/약물/근거 수
```

주의:

```text
AlphaFold 구조는 추천 근거 자체가 아니라 target/protein 구조 참고 자료다.
구조가 있다고 해서 약물 효과를 단정하면 안 된다.
```

## Frontend Prompt 구성 예시

프론트는 Bedrock에 아래처럼 전달하면 된다.

```text
아래 retrieval_context JSON만 근거로 사용해서 설명해줘.
근거 없는 내용은 추측하지 마.
추천 이유와 주의할 점을 분리해서 설명해.
source_file 또는 source_type을 함께 언급해.
risk_sources 또는 ADMET risk가 있으면 반드시 포함해.
AlphaFold 구조 정보는 target/protein 참고 자료로만 설명해.

retrieval_context:
{...}
```

## Prompt Guardrails

LLM 설명에는 아래 제한을 둔다.

```text
1. 임상 처방/치료 확정 문구 금지
2. 근거 없는 효능 주장 금지
3. source_file/source_type 없는 단정 금지
4. risk_evidence 누락 금지
5. AlphaFold 구조를 약효 증명처럼 표현 금지
6. path_score/KG score를 임상 점수처럼 표현 금지
```

## Frontend 표시 제안

설명 화면은 아래 섹션으로 나누는 것이 좋다.

```text
1. 한 줄 요약
2. 추천 근거
3. 환자/이미지 모달 근거
4. ADMET/risk 주의사항
5. Graph/path-score 근거
6. 구조보기 참고
7. 출처/source files
```

## 구현 TODO

이번 문서는 계약 설계 단계다. 다음 단계 구현 순서는 아래와 같다.

```text
1. Pydantic schema 추가
2. /api/explanation-context mock endpoint 추가
3. final_candidate + admet 조회 연결
4. candidate_pool search/provenance 연결
5. image_modal evidence/report 연결
6. graph/path-score context 연결
7. AlphaFold structure context 연결
8. 프론트가 Bedrock prompt에 넣는 예시 검증
```

## 완료 기준

v1 retrieval contract 완료 기준:

```text
문서화 완료
Bedrock 호출 없음
secret/API key 저장 없음
source_file/provenance/risk 필드 명시
프론트가 prompt에 넣을 JSON 구조 명확화
```
