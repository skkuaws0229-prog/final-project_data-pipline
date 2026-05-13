# AlphaFold DB Metadata 조회 정책 v1

## 목적

`protein_targets`에 적재된 UniProt ID를 기준으로 AlphaFold DB에 예측 구조 entry가 있는지 확인한다.

이번 단계는 구조 파일을 내려받는 작업이 아니다.

```text
실행 대상: AlphaFold DB metadata lookup
실행 제외: .cif/.pdb 다운로드, PAE JSON 다운로드, S3 업로드, 구조 viewer 구현
```

## 공식 기준

AlphaFold DB는 UniProt accession 기반으로 prediction metadata를 조회할 수 있다.

```text
https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}
```

AlphaFold DB 데이터는 CC-BY-4.0 라이선스로 제공된다.

## 입력

```text
10_alphafold/protein_targets_seed_reviewed_v1.csv
```

대상:

```text
reviewed UniProt seed protein 27개
```

## 출력

```text
10_alphafold/alphafold_structures_seed_candidates_v1.csv
10_alphafold/alphafold_metadata_raw_v1.json
10_alphafold/alphafold_metadata_summary_v1.md
docs/alphafold_metadata_lookup_validation_v1.md
```

## DB 적재 정책

metadata 확인 후 `alphafold_structures`에 들어갈 후보 필드는 아래와 같다.

```text
structure_id
protein_id
provider
provider_accession
version
file_format
structure_uri
source_url
pae_uri
mean_plddt
confidence_summary
license
status
```

`structure_uri`는 이 단계에서는 AlphaFold DB의 외부 `cifUrl`이다.

실제 `.cif` 파일을 S3에 저장하는 단계가 오면 `structure_uri`를 S3 URI로 바꿀 수 있다.

## status 정책

```text
to_fetch
  AlphaFold DB metadata가 존재하고 cifUrl이 있다.
  아직 로컬/S3로 구조 파일을 받지 않았다는 뜻이다.

missing
  AlphaFold DB metadata가 반환되지 않았다.

failed
  API 호출이 실패했다.
```

## 주의

```text
status=to_fetch는 구조 파일이 DB/S3에 있다는 뜻이 아니다.
structure viewer에서 바로 파일을 렌더링하면 안 된다.
React에는 아직 structure_status=not_loaded 또는 to_fetch 상태로 표시해야 한다.
```

## 다음 단계

```text
1. AlphaFold DB metadata lookup 실행
2. seed candidate CSV 생성
3. 중복/FK/URL 검증
4. PostgreSQL alphafold_structures metadata dry-run
5. 통과 후 metadata만 DB 적재
```
