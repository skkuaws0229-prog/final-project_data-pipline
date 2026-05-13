# AlphaFold Metadata DB 적재 검증 v1

## 목적

`alphafold_structures_seed_candidates_v1.csv`를 PostgreSQL `alphafold_structures` metadata row로 적재할 수 있는지 검증한다.
구조 파일 다운로드와 S3 업로드는 실행하지 않는다.

## 입력 파일

```text
10_alphafold/alphafold_structures_seed_candidates_v1.csv
```

## Row Count

| 대상 | rows |
| --- | ---: |
| alphafold structure metadata seed | 27 |

## Status Count

| status | rows |
| --- | ---: |
| to_fetch | 27 |

## 실행 모드

```text
applied_to_db: true
```

## DB Count

| table | rows |
| --- | ---: |
| protein_targets | 27 |
| alphafold_structures | 27 |

## 검증 결과

```text
structure_id duplicate: 0
to_fetch protein_id duplicate: 0
provider_accession duplicate: 0
protein_id FK candidate missing: 0
provider invalid: 0
file_format invalid: 0
status invalid: 0
to_fetch structure_uri missing: 0
noncanonical entry selected: 0
mean_plddt invalid: 0
```

판정: 통과

## 주의

```text
status=to_fetch는 구조 파일을 아직 로컬/S3로 받지 않았다는 뜻이다.
structure_uri는 현재 AlphaFold DB 외부 cifUrl이다.
실제 파일을 S3에 저장하는 단계에서 structure_uri를 S3 URI로 바꿀 수 있다.
```
