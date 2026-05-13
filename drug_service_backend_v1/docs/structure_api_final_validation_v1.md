# Structure API 최종 검증 v1

## 목적

프론트엔드 전달 전 AlphaFold structure metadata/API의 최종 상태를 검증했다.

## DB Row Count

```text
protein_targets: 27
target_protein_links: 28
alphafold_structures: 27
candidate_protein_structure_links: 261
```

## 중복 검증

```text
protein_id_duplicate: 0
uniprot_id_duplicate: 0
target_link_duplicate: 0
structure_id_duplicate: 0
structure_protein_duplicate: 0
context_id_duplicate: 0
context_semantic_duplicate: 0
```

## FK 검증

```text
target_link_missing_protein_fk: 0
structure_missing_protein_fk: 0
context_missing_disease_fk: 0
context_missing_candidate_fk: 0
context_missing_evidence_fk: 0
context_missing_canonical_fk: 0
context_missing_protein_fk: 0
context_missing_structure_fk: 0
```

## 질환 Coverage

```text
BRCA: 4
Colon: 36
HNSC: 45
IPF: 15
Liver: 7
LUNG: 3
PAH: 28
PDAC: 48
Psoriasis: 54
RA: 4
STAD: 17
```

총 11개 질환 모두 context link가 존재한다.

## API 검증

### Target 목록

```http
GET /api/structures/targets?disease_id=RA
```

결과:

```text
status: 200
targets: JAK1, JAK2
structure_status: pending
structure_count: 1
```

### Structure 상세

```http
GET /api/structures/af_p23458_f1_v6
```

결과:

```text
status: 200
structure_id: af_p23458_f1_v6
gene_symbol: JAK1
status: to_fetch
structure_status: pending
target_texts: JAK1
diseases: IPF, Psoriasis, RA
context_links: 25
```

### 없는 structure_id

```http
GET /api/structures/not_found
```

결과:

```text
status: 404
```

### OpenAPI

```text
/api/structures/targets: registered
/api/structures/{structure_id}: registered
StructureDetailResponse.context_links: registered
StructureDetailResponse.target_links: registered
```

## Seed 검증

```text
candidate_protein_structure_links_seed_v1.csv rows: 261
canonical_drug_id empty: 0
```

## 현재 상태 해석

```text
structure_status=pending
```

의미:

```text
AlphaFold DB metadata는 DB에 있음
structure_uri는 현재 AlphaFold DB 외부 cifUrl
실제 .cif/.pdb 파일은 아직 S3에 저장하지 않음
3D viewer용 S3 파일 준비는 다음 단계
```

## 판정

```text
PASS
```

프론트엔드 개발자가 목록/상세/context 연결 UI를 붙일 수 있는 상태다.
