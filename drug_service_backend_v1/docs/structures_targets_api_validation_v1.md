# Structure Targets API 검증 v1

## 목적

PostgreSQL에 적재된 `target -> protein -> UniProt` 매핑을 FastAPI에서 조회할 수 있는지 검증했다.

이 단계는 구조 파일 조회 단계가 아니다.

```text
AlphaFold DB API 호출 없음
구조 파일 다운로드 없음
S3 구조 파일 적재 없음
alphafold_structures row 생성 없음
```

## Endpoint

```http
GET /api/structures/targets
```

지원 query parameter:

```text
disease_id: optional, 예: RA, PAH, HNSC
q: optional, gene/protein/UniProt/target text 검색
limit: optional, 기본 100, 최대 200
```

## 응답 형태

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
      "structure_status": "not_loaded",
      "structure_count": 0
    }
  ]
}
```

AlphaFold DB metadata 적재 후에는 `alphafold_structures`가 27건이며, 구조 파일 다운로드 전 상태이므로 `structure_status`는 `pending`이다.

## 검증 결과

### Health

```text
GET /health
status: 200
response: {"status":"ok","database":"ok"}
```

### 전체 조회

```text
GET /api/structures/targets?limit=3
status: 200
first rows: AURKA, BCL2L1, CDK2
```

### Disease filter

```text
GET /api/structures/targets?disease_id=RA
status: 200
targets: JAK1, JAK2

GET /api/structures/targets?disease_id=PAH
status: 200
targets: EDNRA/ETA, EDNRB/ETB, PDE5A/PDE5
```

### Search filter

```text
GET /api/structures/targets?q=JAK
status: 200
targets: JAK1, JAK2, JAK3
```

### Unknown disease

```text
GET /api/structures/targets?disease_id=BAD
status: 404
```

## DB 상태

```text
protein_targets: 27
target_protein_links: 28
alphafold_structures: 27
candidate_protein_structure_links: 0
```

## Metadata 적재 후 상태

```text
alphafold_structures.status=to_fetch: 27
/api/structures/targets?disease_id=RA
  JAK1 structure_status=pending, structure_count=1
  JAK2 structure_status=pending, structure_count=1
```

## 판정

```text
PASS
```

FastAPI에서 structure viewer 후보 protein 목록 조회가 가능하다.

## 다음 단계

```text
1. /api/structures/{structure_id} 상세 endpoint 사용
2. React v2 구조보기 버튼 연결
3. 실제 .cif/.pdb 파일은 S3에 저장
```
