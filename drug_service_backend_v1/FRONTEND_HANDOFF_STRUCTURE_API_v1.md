# Frontend Handoff: Structure API v1

## 목적

프론트엔드에서 질환별 protein structure 후보 목록과 상세 metadata를 연결하기 위한 API 계약이다.

현재 AlphaFold 구조 파일 27건은 다운로드/S3 저장/API proxy 제공까지 완료됐다.

```text
현재 가능: 목록 조회, 상세 metadata 조회, 약물/근거 context 표시, 27개 .cif 파일 proxy 조회
아직 아님: production viewer 확정
```

## Base URL

로컬 개발:

```text
http://localhost:8010
```

같은 네트워크에서 다른 컴퓨터가 붙을 때는 백엔드 실행 PC IP를 사용한다.

예:

```text
http://172.16.0.64:8010
```

## Endpoint 1: 질환별 구조 후보 목록

```http
GET /api/structures/targets
```

Query:

```text
disease_id optional
q optional
limit optional, default 100, max 200
```

예:

```http
GET /api/structures/targets?disease_id=RA
GET /api/structures/targets?q=JAK
```

주의:

```text
target/protein 검색 UI는 GET /api/structures/targets?q=JAK를 사용한다.
GET /api/structures?q=JAK는 structure 중심 목록 조회용이다.
```

응답 예:

```json
{
  "targets": [
    {
      "protein_id": "protein_p23458",
      "gene_symbol": "JAK1",
      "uniprot_id": "P23458",
      "protein_name": "Tyrosine-protein kinase JAK1",
      "organism": "Homo sapiens",
      "source": "uniprot_auto_mapping_v1",
      "target_texts": ["JAK1"],
      "mapping_statuses": ["exact"],
      "diseases": ["IPF", "Psoriasis", "RA"],
      "structure_status": "available",
      "structure_count": 1
    }
  ]
}
```

UI 권장:

```text
disease_id 선택
→ targets list 표시
→ gene_symbol / protein_name / UniProt ID 표시
→ structure_status 배지 표시
→ target 클릭 시 detail endpoint 호출
→ structure_status=available이면 구조보기 버튼 활성화
```

## Endpoint 2: 구조 상세 metadata

## Endpoint 2: 구조 중심 목록

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

```http
GET /api/structures?disease_id=RA
GET /api/structures?q=JAK
```

응답 주요 필드:

```text
structure_id
gene_symbol
uniprot_id
protein_name
file_format
structure_status
mean_plddt
file_size_bytes
diseases
target_texts
context_summary
file_endpoint
```

이 endpoint는 구조보기 버튼/테이블을 만들 때 사용한다.

## Endpoint 3: 구조 상세 metadata

```http
GET /api/structures/{structure_id}
```

예:

```http
GET /api/structures/af_p23458_f1_v6
```

응답 주요 필드:

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
structure_source_uri
file_size_bytes
checksum_sha256
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
context_links
context_summary
```

상세 응답 예:

```json
{
  "structure_id": "af_p23458_f1_v6",
  "protein_id": "protein_p23458",
  "gene_symbol": "JAK1",
  "uniprot_id": "P23458",
  "protein_name": "Tyrosine-protein kinase JAK1",
  "provider": "alphafold_db",
  "version": "v6",
  "file_format": "cif",
  "structure_uri": "s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/11_structures/alphafold/P23458/AF-P23458-F1-model_v6.cif",
  "structure_source_uri": "https://alphafold.ebi.ac.uk/files/AF-P23458-F1-model_v6.cif",
  "file_size_bytes": 1115383,
  "checksum_sha256": "7d93bd9305cc8a38d9bd2edc8b127d4e5c2f964b2143bc4de845980662b4680e",
  "source_url": "https://alphafold.ebi.ac.uk/entry/AF-P23458-F1",
  "pae_uri": "https://alphafold.ebi.ac.uk/files/AF-P23458-F1-predicted_aligned_error_v6.json",
  "mean_plddt": 85.56,
  "license": "CC-BY-4.0",
  "status": "available",
  "structure_status": "available",
  "target_texts": ["JAK1"],
  "diseases": ["IPF", "Psoriasis", "RA"],
  "context_links": [],
  "context_summary": {
    "total_links": 25,
    "diseases": ["IPF", "Psoriasis", "RA"],
    "disease_count": 3,
    "drug_count": 17,
    "evidence_count": 3,
    "candidate_target_count": 22,
    "image_evidence_count": 3,
    "target_source_counts": {
      "candidate_target": 22,
      "image_evidence": 3
    }
  }
}
```

실제 응답의 `context_links`에는 후보 약물/이미지 근거 연결이 들어간다.
`context_summary`는 상세 화면에서 구조-질환-약물 연결 규모를 빠르게 보여주기 위한 집계 필드다.

## Endpoint 4: 구조 파일 proxy

```http
GET /api/structures/{structure_id}/file
```

예:

```http
GET /api/structures/af_p23458_f1_v6/file
```

응답:

```text
Content-Type: chemical/x-cif
Content-Disposition: attachment; filename="AF-P23458-F1-model_v6.cif"
Content-Length: 1115383
```

프론트 viewer는 S3를 직접 읽지 말고 이 endpoint를 사용한다.

```text
viewer file URL = {BASE_URL}/api/structures/af_p23458_f1_v6/file
```

## context_links 의미

`context_links`는 이 structure가 어떤 질환/약물 후보/이미지 근거와 연결되는지 보여준다.

주요 필드:

```text
context_id
disease_id
candidate_id
evidence_id
canonical_drug_id
drug_name
target_source
relation_note
```

`target_source`:

```text
candidate_target
image_evidence
```

`relation_note`는 JSON string이다. 필요하면 parse해서 아래 값을 표시할 수 있다.

```text
matched_target_text
source_target
target_pathway
mapping_status
confidence
drug_id
drug_name
source_file
```

## 상태값 의미

```text
structure_status=pending
```

현재 의미:

```text
AlphaFold DB metadata는 있음
실제 구조 파일은 아직 S3/API cache에 없음
structure_uri는 AlphaFold DB 외부 cifUrl 또는 S3 URI
```

프론트 표시 권장:

```text
pending: "구조 metadata 확인됨 / 파일 준비 전"
available: "구조 파일 사용 가능"
not_loaded: "metadata 없음"
missing: "AlphaFold DB entry 없음"
failed: "조회 실패"
```

현재 v1에서는 27건 모두 `available`이다.

## 화면 구성 제안

최소 구성:

```text
질환 선택 dropdown
protein structure 후보 table
protein row 클릭
우측 drawer 또는 modal에서 상세 metadata 표시
context_links table 표시
```

권장 컬럼:

```text
gene_symbol
protein_name
uniprot_id
target_texts
mean_plddt
structure_status
context link count
```

상세 패널:

```text
AlphaFold source_url
structure_uri
structure_source_uri
file_size_bytes
checksum_sha256
pae_uri
license
target_links
context_links
context_summary
file endpoint URL
```

## 아직 하지 말 것

```text
3D viewer를 바로 production으로 고정하지 않기
structure_status=pending을 available처럼 표시하지 않기
AlphaFold 외부 URL을 장기 운영 파일 저장소로 가정하지 않기
S3 URI를 프론트에서 직접 fetch하지 않기
```

## 현재 전체 구조 파일 검증 상태

```text
structures: 27
available: 27
pending: 0
S3 .cif files: 27
file proxy checksum 검증: 27/27 PASS
```

## 다음 단계

```text
1. 프론트에서 viewer 라이브러리 확정
2. available row에 구조보기 버튼 활성화
3. GET /api/structures/{structure_id}/file URL을 viewer에 전달
4. 주요 질환별 대표 target viewer 렌더링 QA
```
