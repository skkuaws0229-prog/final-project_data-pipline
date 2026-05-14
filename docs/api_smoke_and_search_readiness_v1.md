# API Smoke Test 및 OpenSearch Evidence 검색 준비 리포트 v1

작성 시각: 2026-05-14 11:01:36 KST

## 목적

프론트엔드에서 AlphaFold viewer 연결을 진행하는 동안, 백엔드 API 전체 호출 가능 여부와 OpenSearch text evidence 검색 준비 상태를 검증했다.

이번 검증은 배포 검증이 아니라 로컬 Docker Compose 기반 smoke test이다.

## 실행 환경

```text
FastAPI: http://localhost:8010
PostgreSQL: localhost:5433
Neo4j: localhost:7687 / http://localhost:7474
OpenSearch: http://localhost:9200
OpenSearch index: drug_service_text_v1
```

Docker Compose 기준 주요 서비스는 모두 running 또는 healthy 상태였다.

## API Smoke Test 결과

| 구분 | Endpoint | 결과 | 확인 내용 |
|---|---|---:|---|
| 기본 상태 | `GET /health` | 200 | database/status 응답 |
| OpenSearch 상태 | `GET /health/search` | 200 | search/status 응답 |
| 약물 목록 | `GET /drugs?disease_id=RA&limit=3` | 200 | RA 후보 약물 row 반환 |
| Neo4j 관계 그래프 | `GET /graph/relations?disease_id=RA` | 200 | nodes 71, edges 132 |
| AlphaFold 구조 목록 | `GET /api/structures?q=JAK&limit=10` | 200 | JAK1, JAK2, JAK3 반환 |
| AlphaFold 구조 상세 | `GET /api/structures/af_p23458_f1_v6` | 200 | JAK1 context_summary 포함 |
| AlphaFold 파일 proxy | `GET /api/structures/af_p23458_f1_v6/file` | 200 | `chemical/x-cif` 응답 |
| OpenSearch RA 검색 | `GET /search?q=JAK&disease_id=RA&limit=5` | 200 | total 14, hits 5 |
| OpenSearch evidence 검색 | `GET /search?q=immune&doc_type=image_evidence&limit=5` | 200 | total 26, hits 5 |
| Pipeline run 목록 | `GET /api/pipeline-runs?limit=5` | 200 | runs 5 |

## AlphaFold JAK1 상세 검증

`GET /api/structures/af_p23458_f1_v6`의 `context_summary`:

```json
{
  "total_links": 25,
  "diseases": ["IPF", "Psoriasis", "RA"],
  "disease_count": 3,
  "drug_count": 6,
  "evidence_count": 12,
  "candidate_target_count": 13,
  "image_evidence_count": 12,
  "target_source_counts": {
    "candidate_target": 13,
    "image_evidence": 12
  }
}
```

프론트엔드에서는 상세 화면 상단 요약으로 `context_summary`를 먼저 보여주고, 상세 근거는 `context_links`를 접기/테이블 형태로 보여주는 방식이 적합하다.

## OpenSearch 색인 검증

OpenSearch 전체 문서 수:

```text
total: 699
```

문서 타입별 색인 수:

| doc_type | count |
|---|---:|
| drug_candidate | 255 |
| image_evidence | 430 |
| image_report | 14 |

PostgreSQL 원천 테이블 수와 대조한 결과:

| PostgreSQL table | count | OpenSearch doc_type | count | 일치 |
|---|---:|---|---:|---|
| drug_candidates | 255 | drug_candidate | 255 | yes |
| image_modal_drug_evidence | 430 | image_evidence | 430 | yes |
| image_modal_reports | 14 | image_report | 14 | yes |

필수 필드 누락:

| 필드 | 누락 수 |
|---|---:|
| doc_type | 0 |
| disease_id | 0 |
| source_file | 0 |

## 질환별 색인 수

| disease_id | count |
|---|---:|
| BRCA | 48 |
| Colon | 57 |
| HNSC | 91 |
| IPF | 25 |
| Liver | 26 |
| LUNG | 34 |
| PAH | 43 |
| PDAC | 91 |
| Psoriasis | 151 |
| RA | 63 |
| STAD | 70 |

OpenSearch 질환별 count와 PostgreSQL 기준 통합 count가 일치했다.

## 현재 가능 범위

현재 `/search`는 vector search가 아니라 text search 전용이다.

가능한 검색:

```text
GET /search?q=JAK
GET /search?q=JAK&disease_id=RA
GET /search?q=immune&doc_type=image_evidence
GET /search?q=fibrosis&doc_type=image_report
```

검색 대상 필드:

```text
title
drug_name
target
target_pathway
evidence_text
report_text
clinical_summary
pathway_summary
source_file
```

## 다음 단계 제안

1. 프론트엔드에서 검색 UI가 필요하면 `/search`를 먼저 text evidence 검색으로 연결한다.
2. 검색 결과에는 `doc_type`, `disease_id`, `drug_name`, `snippet`, `source_file`을 우선 표시한다.
3. RAG/Bedrock 단계에서는 `/search` 결과를 retrieval candidate로 사용하되, `source_file`과 `doc_type`을 근거 출처로 함께 넘긴다.
4. vector search는 CT-CLIP/UNI2 embedding 원본, 차원, 저장 위치, 검색 단위를 확정한 뒤 v2에서 추가한다.

## 결론

로컬 기준 백엔드 핵심 API는 정상 동작한다.

OpenSearch text evidence index는 PostgreSQL 원천 테이블과 문서 수가 일치하며, 필수 provenance 필드 누락도 없다.

따라서 프론트엔드 AlphaFold viewer QA가 진행되는 동안, 다음 백엔드 작업은 OpenSearch 검색 UI 연결 지원 또는 RAG/Bedrock retrieval 계약 설계로 넘어갈 수 있다.
