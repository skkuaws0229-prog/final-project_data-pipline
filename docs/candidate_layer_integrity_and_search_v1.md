# Candidate Layer 무결성 및 OpenSearch 확장 검증 v1

작성일: 2026-05-14

## 목적

프론트엔드 Candidates 화면 요구에 맞춰 분리한 두 후보 계층을 재검증하고, broader candidate pool을 OpenSearch text search 대상으로 확장했다.

```text
final-candidates -> drug_candidates final/admet 계층
candidates       -> candidate_pool broader 후보 계층
```

## PostgreSQL 계층 검증

테이블 카운트:

| table | count |
|---|---:|
| drug_candidates | 255 |
| candidate_pool | 432 |
| admet_results | 255 |

질환별 검증:

| disease_id | final_rows | final_drugs | pool_rows | pool_drugs | pool_final_marked | pool_final_drugs |
|---|---:|---:|---:|---:|---:|---:|
| BRCA | 15 | 15 | 62 | 60 | 16 | 15 |
| Colon | 15 | 15 | 50 | 50 | 15 | 15 |
| HNSC | 30 | 30 | 50 | 50 | 30 | 30 |
| IPF | 15 | 9 | 30 | 11 | 28 | 9 |
| Liver | 15 | 15 | 31 | 31 | 15 | 15 |
| LUNG | 15 | 15 | 39 | 37 | 17 | 15 |
| PAH | 30 | 30 | 30 | 30 | 30 | 30 |
| PDAC | 30 | 30 | 50 | 50 | 30 | 30 |
| Psoriasis | 30 | 30 | 30 | 30 | 30 | 30 |
| RA | 30 | 30 | 30 | 30 | 30 | 30 |
| STAD | 30 | 30 | 30 | 30 | 30 | 30 |

## 누락/중복 검증

Final 후보가 candidate_pool에 매칭되지 않는 경우:

```text
0
```

원천 candidate_pool 안에 같은 질환/같은 약물명 중복 row가 있는 경우:

| disease_id | normalized_name | rows |
|---|---|---:|
| BRCA | fulvestrant | 2 |
| BRCA | oxaliplatin | 2 |
| IPF | unnamed jak1 preclinical compound | 20 |
| LUNG | dactinomycin | 2 |
| LUNG | docetaxel | 2 |

이 중복은 원천 broader 후보 pool의 provenance row로 보존한다. API 응답은 같은 질환 안에서 같은 `drug_name`을 dedup하여 반환한다.

## API 검증

BRCA:

```text
GET /v1/diseases/BRCA/final-candidates?limit=100
-> 15 rows, is_final_candidate=true 15

GET /api/diseases/BRCA/candidates?limit=100
-> 60 rows, is_final_candidate=true 15
```

LUNG:

```text
GET /v1/diseases/LUNG/final-candidates?limit=100
-> 15 rows, is_final_candidate=true 15

GET /api/diseases/LUNG/candidates?limit=100
-> 37 rows, is_final_candidate=true 15
```

## OpenSearch 확장

`candidate_pool`을 text search index에 추가했다.

OpenSearch document count:

| doc_type | count |
|---|---:|
| candidate_pool | 432 |
| drug_candidate | 255 |
| image_evidence | 430 |
| image_report | 14 |

전체 문서 수:

```text
1131
```

## Search API 검증

Candidate pool 검색:

```text
GET /search?q=Ruxolitinib&doc_type=candidate_pool&limit=5
-> 200
-> total 4
-> hits 4
-> first drug_name: Ruxolitinib
-> first is_final_candidate: true
```

질환 필터 포함:

```text
GET /search?q=Ruxolitinib&disease_id=RA&doc_type=candidate_pool&limit=5
-> 200
-> total 1
-> hits 1
-> first drug_name: RUXOLITINIB
-> first is_final_candidate: true
```

기존 final candidate 검색도 유지:

```text
GET /search?q=Ruxolitinib&disease_id=RA&doc_type=drug_candidate&limit=5
-> 200
-> total 1
-> hits 1
```

## Frontend 사용 기준

Candidates 기본 화면:

```text
GET /v1/diseases/{disease_code}/final-candidates
```

전체 후보 보기:

```text
GET /api/diseases/{disease_code}/candidates
```

후보 검색:

```text
GET /search?q={query}&doc_type=candidate_pool
GET /search?q={query}&disease_id={disease_code}&doc_type=candidate_pool
```

근거/보고서 검색:

```text
GET /search?q={query}&doc_type=image_evidence
GET /search?q={query}&doc_type=image_report
```

## 결론

후보 계층은 의미상 분리되었고, final 후보가 broader candidate pool에서 누락되는 문제는 없다.

OpenSearch text index에도 `candidate_pool`이 추가되어, 전체 후보 보기와 검색 UI/RAG retrieval에서 broader 후보 pool을 사용할 수 있다.
