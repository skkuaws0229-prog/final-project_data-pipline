# AlphaFold pilot file proxy 검증 리포트 v1

작성일: 2026-05-14

## 목적

프론트엔드가 S3 권한/CORS를 직접 처리하지 않고, 백엔드 proxy endpoint로 AlphaFold `.cif` 구조 파일을 로딩할 수 있는지 pilot 검증한다.

## Pilot 대상

```text
structure_id: af_p23458_f1_v6
gene_symbol: JAK1
uniprot_id: P23458
file_format: cif
source: AlphaFold DB
source_uri: https://alphafold.ebi.ac.uk/files/AF-P23458-F1-model_v6.cif
```

JAK1은 RA/Psoriasis/IPF에 연결되어 있고, 프론트에서 `q=JAK`로 빠르게 찾을 수 있어 pilot 대상으로 선택했다.

## 저장 위치

로컬 API cache:

```text
11_structures/alphafold/P23458/AF-P23458-F1-model_v6.cif
```

S3:

```text
s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/11_structures/alphafold/P23458/AF-P23458-F1-model_v6.cif
```

## DB 업데이트

`alphafold_structures`에 아래 컬럼을 추가했다.

```text
structure_source_uri
file_size_bytes
checksum_sha256
```

JAK1 row는 아래 상태로 갱신했다.

```text
status: available
structure_uri: s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/11_structures/alphafold/P23458/AF-P23458-F1-model_v6.cif
structure_source_uri: https://alphafold.ebi.ac.uk/files/AF-P23458-F1-model_v6.cif
file_size_bytes: 1115383
checksum_sha256: 7d93bd9305cc8a38d9bd2edc8b127d4e5c2f964b2143bc4de845980662b4680e
```

## API 추가

```http
GET /api/structures/{structure_id}/file
```

pilot:

```http
GET /api/structures/af_p23458_f1_v6/file
```

정상 응답:

```text
HTTP 200
Content-Type: chemical/x-cif
Content-Disposition: attachment; filename="AF-P23458-F1-model_v6.cif"
Content-Length: 1115383
```

## 검증 결과

| 항목 | 결과 | 비고 |
|---|---:|---|
| AlphaFold DB `.cif` 다운로드 | PASS | 1,115,383 bytes |
| S3 업로드 | PASS | `drug_service_build/11_structures/...` |
| DB status 업데이트 | PASS | JAK1 `available` |
| `/api/structures/targets?q=JAK` | PASS | JAK1 `structure_status=available` |
| `/api/structures/af_p23458_f1_v6` | PASS | S3 URI, source URI, size, checksum 반환 |
| `/api/structures/af_p23458_f1_v6/file` | PASS | `.cif` 파일 다운로드 |
| file checksum 재검증 | PASS | SHA256 일치 |
| pending 구조 file 요청 | PASS | EGFR `409 Conflict` |
| 없는 structure file 요청 | PASS | `404 Not Found` |
| context link 복구 | PASS | 전체 261건, JAK1 25건 |

## 현재 구조 파일 상태

```text
available: 1
pending: 26
total: 27
```

## 프론트엔드 확인 요청

프론트에서는 우선 아래 URL로 viewer pilot을 확인한다.

```text
GET /api/structures/af_p23458_f1_v6/file
```

권장 흐름:

```text
GET /api/structures/targets?q=JAK
-> JAK1 row의 structure_status=available 확인
-> GET /api/structures/af_p23458_f1_v6
-> 구조보기 버튼 활성화
-> GET /api/structures/af_p23458_f1_v6/file URL을 viewer에 전달
```

## 다음 단계

```text
1. 프론트 viewer에서 JAK1 .cif 로딩 확인
2. viewer 라이브러리 확정
3. 통과하면 나머지 26개 구조 파일 다운로드/S3 저장/DB 갱신
4. 전체 available 구조에 대해 file proxy endpoint 검증
```
