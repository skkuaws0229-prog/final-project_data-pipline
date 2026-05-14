# AlphaFold full file proxy 검증 리포트 v1

작성일: 2026-05-14

## 목적

JAK1 pilot viewer 로딩 확인 후, AlphaFold 구조 파일 27건 전체를 S3/API proxy 방식으로 제공할 수 있는지 검증한다.

## 처리 범위

```text
alphafold_structures total: 27
downloaded .cif files: 27
S3 uploaded .cif files: 27
API file proxy checked: 27
```

## 저장 정책

GitHub에는 대량 구조 파일을 직접 올리지 않는다.

구조 파일은 S3와 로컬/EC2 cache에 둔다.

```text
S3 base:
s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/11_structures/alphafold/

local/API cache:
11_structures/alphafold/{uniprot_id}/AF-{uniprot_id}-F1-model_v6.cif
```

## 산출물

```text
10_alphafold/fetch_alphafold_files_v1.py
10_alphafold/alphafold_file_manifest_v1.csv
11_structures/README.md
```

`alphafold_file_manifest_v1.csv`에는 27개 구조 파일의 source URI, local path, S3 URI, file size, SHA256 checksum이 들어 있다.

## DB 상태

```text
status=available: 27
status=to_fetch: 0
file_size_bytes missing: 0
checksum_sha256 missing: 0
```

추가/사용 컬럼:

```text
structure_source_uri
file_size_bytes
checksum_sha256
```

## API 검증

### Targets API

```http
GET /api/structures/targets?limit=200
```

결과:

```text
targets: 27
available: 27
other statuses: available only
```

### File proxy API

```http
GET /api/structures/{structure_id}/file
```

27개 전체에 대해 아래를 검증했다.

```text
HTTP 200
Content-Type: chemical/x-cif
Content-Length == DB file_size_bytes
SHA256(response body) == DB checksum_sha256
```

결과:

```text
checked: 27
errors: 0
```

## S3 검증

```text
S3 .cif count: 27
```

## 프론트엔드 전달 사항

프론트는 S3 URI를 직접 fetch하지 않는다.

viewer에는 아래 URL 형태를 전달한다.

```text
{BASE_URL}/api/structures/{structure_id}/file
```

예:

```text
http://172.16.0.64:8010/api/structures/af_p23458_f1_v6/file
```

화면 흐름:

```text
GET /api/structures/targets
-> structure_status=available인 row에 구조보기 버튼 활성화
-> GET /api/structures/{structure_id}
-> GET /api/structures/{structure_id}/file URL을 viewer에 전달
```

## 다음 단계

```text
1. 프론트 viewer 라이브러리 확정
2. 27개 structure_id 중 대표 target 몇 개 렌더링 QA
3. 필요 시 파일 다운로드 실패/로딩 실패 UI 추가
4. EC2 배포 시 11_structures cache를 S3에서 sync
```
