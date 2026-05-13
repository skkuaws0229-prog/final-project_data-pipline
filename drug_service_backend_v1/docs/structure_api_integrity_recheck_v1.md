# Structure API 무결성 재검증 v1

## 목적

Structure targets/detail API 보강 후 중복, 누락, FK 오류, 질환 coverage 누락이 없는지 재검증했다.

## DB Row Count

```text
protein_targets: 27
target_protein_links: 28
alphafold_structures: 27
candidate_protein_structure_links: 0
```

## 중복 검증

```text
protein_id_duplicate: 0
uniprot_id_duplicate: 0
target_link_duplicate: 0
structure_id_duplicate: 0
structure_protein_duplicate: 0
structure_accession_duplicate: 0
```

## 누락/FK 검증

```text
target_link_missing_protein_fk: 0
structure_missing_protein_fk: 0
protein_without_structure: 0
protein_without_target_link: 0
```

## CSV-DB 연결 검증

```text
csv_proteins: 27
csv_links: 28
csv_structures: 27
link_missing_csv_protein: 0
structure_missing_csv_protein: 0
csv_protein_without_structure: 0
csv_protein_without_link: 0
```

## 질환 Coverage

```text
BRCA: 2
Colon: 6
HNSC: 7
IPF: 4
LUNG: 2
Liver: 2
PAH: 3
PDAC: 7
Psoriasis: 4
RA: 2
STAD: 3
```

예상 11개 질환:

```text
BRCA
Colon
HNSC
IPF
LUNG
Liver
PAH
PDAC
Psoriasis
RA
STAD
```

검증:

```text
missing_expected_diseases: 0
extra_diseases: 0
```

## API 전체 상세 조회 검증

```text
checked structure detail endpoints: 27
failures: 0
expected structure_status: pending
```

## 현재 남은 의도적 공백

```text
candidate_protein_structure_links: 0
```

이 테이블은 아직 비어 있는 것이 맞다.

이유:

```text
질환/약물 후보/이미지 evidence context와 structure를 직접 연결하는 단계는 아직 진행하지 않았다.
현재는 protein-level structure metadata까지만 적재했다.
```

## 판정

```text
PASS
```

현재 AlphaFold metadata/API 단계에서 중복 또는 누락 문제는 발견되지 않았다.
