# Structure Detail API 검증 v1

## 목적

프론트엔드 구조보기 버튼에서 특정 AlphaFold structure metadata를 조회할 수 있도록 상세 API를 추가하고 검증했다.

이 단계에서도 구조 파일 다운로드와 S3 업로드는 실행하지 않았다.

## Endpoint

```http
GET /api/structures/{structure_id}
```

예:

```http
GET /api/structures/af_p23458_f1_v6
```

## 응답 주요 필드

```text
structure_id
protein_id
gene_symbol
uniprot_id
protein_name
provider
provider_accession
version
file_format
structure_uri
source_url
pae_uri
mean_plddt
license
status
structure_status
target_texts
mapping_statuses
diseases
target_links
```

## 검증 결과

### DB 유지 상태

```text
protein_targets: 27
target_protein_links: 28
alphafold_structures: 27
```

### 상세 조회

```text
GET /api/structures/af_p23458_f1_v6
status: 200
gene_symbol: JAK1
uniprot_id: P23458
version: v6
file_format: cif
status: to_fetch
structure_status: pending
target_texts: JAK1
diseases: IPF, Psoriasis, RA
```

### 없는 structure_id

```text
GET /api/structures/unknown_structure
status: 404
```

### 목록 API 영향 확인

```text
GET /api/structures/targets?disease_id=RA
status: 200
targets: JAK1, JAK2
structure_status: pending
```

### OpenAPI 등록 확인

```text
/api/structures/targets: registered
/api/structures/{structure_id}: registered
```

## 판정

```text
PASS
```

프론트엔드는 목록에서 받은 `structure_id`를 기준으로 상세 metadata를 조회할 수 있다.

## 주의

```text
structure_uri는 현재 AlphaFold DB 외부 cifUrl이다.
status=to_fetch, structure_status=pending은 파일이 아직 S3에 없다는 뜻이다.
실제 viewer에서 파일을 직접 렌더링할지, S3 저장 후 렌더링할지는 다음 단계에서 결정한다.
```
