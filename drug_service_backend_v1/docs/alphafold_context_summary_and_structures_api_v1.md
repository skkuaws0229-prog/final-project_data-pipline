# AlphaFold context summary and structures API v1

작성일: 2026-05-14

## 목적

프론트엔드 구조보기 화면에서 `context_links` 원자료를 직접 집계하지 않아도 되도록 `context_summary`와 구조 중심 목록 endpoint를 제공한다.

## 추가 필드

`GET /api/structures/{structure_id}` 응답에 아래 필드를 추가했다.

```text
context_summary
```

필드 구성:

```text
total_links
diseases
disease_count
drug_count
evidence_count
candidate_target_count
image_evidence_count
target_source_counts
```

## 추가 endpoint

```http
GET /api/structures
```

Query:

```text
disease_id optional
q optional
limit optional, default 100, max 200
```

예:

```text
GET /api/structures?disease_id=RA
GET /api/structures?q=JAK
```

## 검증 예시

JAK1:

```text
structure_id: af_p23458_f1_v6
total_links: 25
diseases: IPF, Psoriasis, RA
disease_count: 3
candidate_target_count: 13
image_evidence_count: 12
```

EGFR:

```text
structure_id: af_p00533_f1_v6
total_links: 12
diseases: HNSC
disease_count: 1
candidate_target_count: 4
image_evidence_count: 8
```

## 프론트 사용

구조 목록 화면:

```text
GET /api/structures?disease_id=RA
```

구조 상세 화면:

```text
GET /api/structures/{structure_id}
```

viewer:

```text
{BASE_URL}{file_endpoint}
```
