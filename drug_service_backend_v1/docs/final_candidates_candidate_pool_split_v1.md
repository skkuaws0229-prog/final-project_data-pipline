# Final Candidates / Candidate Pool 분리 검증 v1

작성일: 2026-05-14

## 목적

프론트엔드 Candidates 화면 요구에 맞춰 후보 API 의미를 분리했다.

```text
기본 Candidates 화면
-> GET /v1/diseases/{disease_code}/final-candidates
-> final/admet canonical artifact 기반 최종 후보

전체 후보 보기 view=all
-> GET /api/diseases/{disease_code}/candidates
-> broader candidate pool 기반 후보
```

## 변경 사항

기존에는 아래 endpoint가 모두 같은 `drug_candidates` 테이블을 조회했다.

```text
GET /v1/diseases/{disease_code}/final-candidates
GET /v1/diseases/{disease_code}/candidates
GET /api/diseases/{disease_code}/candidates
```

이제는 다음처럼 분리했다.

| endpoint | DB source | 의미 |
|---|---|---|
| `GET /v1/diseases/{disease_code}/final-candidates` | `drug_candidates` + `admet_results` | final/admet 이후 최종 후보 |
| `GET /api/diseases/{disease_code}/candidates` | `candidate_pool` | top30/top50 등 broader 후보 pool |
| `GET /v1/diseases/{disease_code}/candidates` | `candidate_pool` | 내부 호환 alias |
| `GET /drugs?disease_id=RA` | `drug_candidates` + `admet_results` | 기존 호환 final 후보 |

## 신규 테이블

```text
candidate_pool
```

핵심 필드:

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
source_file
source_row_number
raw_json
is_final_candidate
```

`is_final_candidate`는 broader pool row가 현재 final 후보 집합에도 포함되는지 표시한다.

프론트 `view=all` 화면에서는 이 값을 사용해 각 row에 “최종 후보 / 탈락” 표시를 붙일 수 있다.

## 후보 pool 원천

| disease_id | selected broader source |
|---|---|
| BRCA | `step7_admet60_tiered_candidates.csv` |
| Colon | `20260428_colon_v2_colon_top50_drugs_ensemble.csv` |
| HNSC | `hnsc_selected_drugs_top50.csv` |
| IPF | `ipf_top30_clinical_reranked.csv` |
| LUNG | `lung_top30_phase2b_catboost_with_names.csv` |
| Liver | `lihc_top30_directive_ensemble_with_names.csv` |
| PAH | `pah_top30_clinical_reranked.csv` |
| PDAC | `top50_external_validation.csv` |
| Psoriasis | `phase2a_CatBoost_top30.csv` |
| RA | `phase2a_CatBoost_top30.csv` |
| STAD | `stad_top30_4tier_classification.csv` |

## 적재 결과

정규화 row:

```text
candidate_pool rows: 432
is_final_candidate=true: 271
```

질환별 정규화 row:

| disease_id | candidate_pool rows |
|---|---:|
| BRCA | 62 |
| Colon | 50 |
| HNSC | 50 |
| IPF | 30 |
| LUNG | 39 |
| Liver | 31 |
| PAH | 30 |
| PDAC | 50 |
| Psoriasis | 30 |
| RA | 30 |
| STAD | 30 |

API는 같은 질환 안에서 같은 `drug_name`이 중복 표시되지 않도록 dedup 후 반환한다.

## API 검증

BRCA:

```text
GET /v1/diseases/BRCA/final-candidates?limit=100
-> 15 rows
-> candidate_source = final_candidate
-> is_final_candidate = true 15 rows

GET /api/diseases/BRCA/candidates?limit=100
-> 60 rows
-> candidate_source = candidate_pool
-> is_final_candidate = true 15 rows
```

LUNG:

```text
GET /v1/diseases/LUNG/final-candidates?limit=100
-> 15 rows

GET /api/diseases/LUNG/candidates?limit=100
-> 37 rows
-> is_final_candidate = true 15 rows
```

RA:

```text
GET /v1/diseases/RA/final-candidates?limit=100
-> 30 rows

GET /api/diseases/RA/candidates?limit=100
-> 30 rows
-> is_final_candidate = true 30 rows
```

RA는 현재 선택된 final artifact 자체가 top30 ADMET annotated 계열이므로 final/all row 수가 같다. 이 경우 endpoint 분리는 되어 있지만, 실제 row 집합 차이는 원천 final artifact 정책에 따라 달라진다.

## 프론트엔드 사용 기준

기본 화면:

```text
GET /v1/diseases/{disease_code}/final-candidates
```

전체 후보 보기:

```text
GET /api/diseases/{disease_code}/candidates
```

행 표시:

```text
is_final_candidate = true  -> 최종 후보
is_final_candidate = false -> 탈락 또는 후보 pool 단계
```

## 주의사항

- `candidate_pool`은 기존 final/admet 테이블을 수정하지 않고 별도 테이블로 추가했다.
- broader source는 질환별로 top30/top50 계열 대표 파일을 선택했다.
- 일부 질환은 현재 final artifact가 이미 top30 계열이라 final/all row 수가 같을 수 있다.
- `raw_json`에 원본 row 전체를 보존했다.
