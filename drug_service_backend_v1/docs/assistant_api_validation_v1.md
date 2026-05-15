# Assistant API validation v1

## 목적

프론트엔드 챗봇 화면이 Bedrock fallback으로만 동작하지 않고, 백엔드 team API assistant 계층을 먼저 호출할 수 있도록 최소 endpoint를 추가했다.

이번 단계는 Bedrock/RAG/LLM 실제 호출이 아니다. 백엔드가 이미 적재된 PostgreSQL, Neo4j, OpenSearch, AlphaFold metadata를 read-only로 요약해서 질환 맥락 답변 패키지를 반환하는 단계다.

## Endpoint

### Suggested questions

```http
GET /api/assistant/{disease}/suggested-questions
```

예:

```http
GET /api/assistant/BRCA/suggested-questions
GET /api/assistant/RA/suggested-questions
```

응답 필드:

```json
{
  "disease_id": "BRCA",
  "display_name": "Breast cancer",
  "questions": ["..."],
  "items": [
    { "id": "q1", "question": "..." }
  ],
  "source": "team_api_static_v1"
}
```

### Ask

```http
POST /api/assistant/{disease}/ask
```

요청:

```json
{
  "question": "BRCA 최종 후보 약물 Top 5는?",
  "mode": "read_only"
}
```

응답 주요 필드:

```json
{
  "disease_id": "BRCA",
  "display_name": "Breast cancer",
  "question": "BRCA 최종 후보 약물 Top 5는?",
  "mode": "read_only",
  "answer": "...",
  "answer_type": "final_candidates_summary",
  "used_bedrock": false,
  "context": {},
  "sources": [],
  "suggested_followups": [],
  "guardrails": [],
  "status": "ready"
}
```

## Answer routing

질문 키워드에 따라 내부 자료를 read-only로 조회한다.

| 질문 유형 | 내부 조회 |
|---|---|
| 후보, 추천, Top, 약물, candidate | `/v1/diseases/{disease}/final-candidates` |
| ADMET, 독성, 위험, 주의, safety | final candidate ADMET columns |
| 이미지, image, cluster, 클러스터, 근거 | `image_modal_drug_evidence` |
| AlphaFold, 구조, structure, protein, 단백질 | `/api/structures/targets` |
| graph, 그래프, 관계, path, target, pathway, 기전 | `/graph/relations`, `/graph/path-score` |
| 기타 | final candidates + OpenSearch context summary |

주의: AlphaFold/구조 질문은 graph 질문보다 먼저 분기한다. `"target protein"` 같은 문장이 graph 답변으로 오분류되지 않게 하기 위함이다.

## Guardrail

- 현재 지원 mode는 `read_only`만이다.
- Bedrock/LLM은 호출하지 않는다.
- 응답의 `used_bedrock`은 항상 `false`다.
- 알 수 없는 질환 코드는 `404`를 반환한다.
- `read_only` 외 mode는 `400`을 반환한다.
- 내부 점수와 그래프 근거는 임상 효능 주장이 아니라 후보 검토용 근거다.

## Validation

검증일: 2026-05-15

| 검증 항목 | 결과 |
|---|---|
| `GET /api/assistant/BRCA/suggested-questions` | 200 |
| `POST /api/assistant/BRCA/ask` | 200 |
| `GET /api/assistant/RA/suggested-questions` | 200 |
| `POST /api/assistant/RA/ask` AlphaFold 질문 | 200, `answer_type=structure_summary` |
| invalid mode | 400 |
| unknown disease | 404 |
| OpenAPI 노출 | `/api/assistant/{disease_code}/suggested-questions`, `/api/assistant/{disease_code}/ask` 확인 |

## Data integrity note

Docker rebuild 시 `db-loader`가 다시 실행되면 `candidate_protein_structure_links`가 0으로 초기화될 수 있다. 재빌드 후에는 아래 카운트를 확인한다.

```sql
SELECT count(*) FROM candidate_protein_structure_links;
```

기대값:

```text
261
```

이번 검증 후 복구 결과:

```text
candidate_protein_structure_links = 261
alphafold_structures(status='available') = 27
```

## 프론트 전달 사항

프론트가 요청한 경로가 맞다.

```text
GET  /api/assistant/{disease}/suggested-questions
POST /api/assistant/{disease}/ask
```

이제 위 endpoint는 404가 아니라 200 응답을 반환한다. Bedrock fallback은 team API 호출 실패 시에만 사용하면 된다.

현재 ask 응답은 백엔드 read-only 요약이다. Bedrock/RAG가 실제 답변 생성을 맡는 구조로 확장하더라도, 이 endpoint의 `context`, `sources`, `guardrails`는 프론트 챗봇 UI와 citation 표시의 기본 계약으로 유지할 수 있다.
