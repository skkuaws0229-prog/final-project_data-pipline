# AlphaFold DB Metadata 조회 검증 v1

## 목적

UniProt ID 27개 기준으로 AlphaFold DB prediction metadata 존재 여부만 확인했다.
구조 파일 다운로드, PAE JSON 다운로드, S3 업로드, PostgreSQL 적재는 실행하지 않았다.

## 기준 API

```text
https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}
```

## 생성 파일

```text
10_alphafold/alphafold_structures_seed_candidates_v1.csv
10_alphafold/alphafold_metadata_raw_v1.json
10_alphafold/alphafold_metadata_summary_v1.md
```

## Status Count

| status | rows |
| --- | ---: |
| to_fetch | 27 |

## Canonical Selection

| 항목 | rows |
| --- | ---: |
| canonical AF-{UniProt}-F1 selected | 27 |
| seed candidate rows | 27 |

## API Status Count

| api_status | rows |
| --- | ---: |
| http_200 | 27 |

## 무결성 결과

```text
structure_id duplicate: 0
to_fetch protein_id duplicate: 0
to_fetch structure_uri missing: 0
provider invalid: 0
file_format invalid: 0
status invalid: 0
```

판정: 통과

## 다음 단계

```text
1. alphafold_structures_seed_candidates_v1.csv 수동 확인
2. PostgreSQL alphafold_structures metadata 적재 dry-run
3. 통과 후 metadata만 DB 적재
4. 실제 .cif/.pdb 파일 다운로드와 S3 저장은 별도 단계에서 실행
```
