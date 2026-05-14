# OpenSearch Text Search v1

이 단계는 vector search가 아니라 **text search 전용 v1**입니다.

## Index

```text
drug_service_text_v1
```

## Indexed document types

```text
candidate_pool  : broader candidate pool for view=all
drug_candidate  : PostgreSQL drug_candidates + drugs + admet_results
image_evidence  : image_modal_drug_evidence + cluster summary + match status
image_report    : image_modal_reports
```

## 실행

전체 stack 실행:

```bash
docker compose up -d --build
```

OpenSearch health:

```text
GET http://localhost:8010/health/search
```

Text search:

```text
GET http://localhost:8010/search?q=JAK&disease_id=RA
GET http://localhost:8010/search?q=Ruxolitinib&doc_type=candidate_pool
GET http://localhost:8010/search?q=immune&doc_type=image_evidence
```

## v1 주의사항

- 이 index에는 embedding/vector field가 없습니다.
- `target`, `target_pathway`, `TargetConcept`는 아직 raw text입니다.
- Vector search는 CT-CLIP/UNI2 embedding 원본과 차원 정책을 확정한 뒤 v2에서 추가합니다.
