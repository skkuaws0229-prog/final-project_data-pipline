# OpenSearch Text Search 검증 v1

## 범위

OpenSearch v1은 vector search가 아니라 text search만 검증했습니다.

색인 대상:

```text
drug_candidate
image_evidence
image_report
```

## 색인 결과

`search-loader` 로그 기준:

```text
Indexed 699 documents into drug_service_text_v1:
drug_candidate: 255
image_evidence: 430
image_report: 14
```

## 연결 검증

FastAPI endpoint:

```text
GET /health/search -> {"status":"ok","search":"ok"}
```

Docker Compose 상태:

```text
opensearch: healthy
api: running
```

## 구현 endpoint

```text
GET /health/search
GET /search?q={query}
GET /search?q={query}&disease_id=RA
GET /search?q={query}&doc_type=image_evidence
```

## 응답 형태

```json
{
  "query": "JAK",
  "total": 0,
  "hits": []
}
```

## v1 제한사항

- 아직 vector field는 없습니다.
- `target`, `target_pathway`, `TargetConcept`는 raw text입니다.
- text search 샘플 query는 Swagger 또는 브라우저에서 추가 확인하면 됩니다.
- vector search는 CT-CLIP/UNI2 embedding 원본과 차원 정책을 확정한 뒤 v2에서 진행합니다.
