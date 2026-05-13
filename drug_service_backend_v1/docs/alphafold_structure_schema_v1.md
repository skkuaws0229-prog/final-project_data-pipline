# AlphaFold 구조보기 DB Schema v1

## 목적

추천받은 약물 또는 신규 후보 약물에서 연결된 target protein 구조를 나중에 프론트엔드에서 볼 수 있도록, AlphaFold 구조 데이터의 저장 위치와 연결 schema를 먼저 정의한다.

이번 단계는 schema 설계 단계다. AlphaFold 예측 실행, 대용량 구조 다운로드, 프론트 3D viewer 구현은 아직 하지 않는다.

## 현재 전제

현재 graph의 `TargetConcept`는 raw `target`, `target_pathway` text를 그대로 보존한다.

주의:

```text
target 값은 gene만이 아니다.
gene / pathway / mechanism / drug class / free-text가 섞여 있다.
```

따라서 AlphaFold 구조보기는 raw target을 바로 구조로 연결하면 안 된다. 반드시 protein mapping layer가 필요하다.

## 목표 연결 흐름

```text
Drug Candidate
  ↓
raw target / target_pathway
  ↓
target_protein_links
  ↓
protein_targets
  ↓
alphafold_structures
  ↓
React Structure Viewer
```

image-modal evidence에서도 같은 구조를 사용한다.

```text
Image Evidence
  ↓
raw target / pathway text
  ↓
target_protein_links
  ↓
protein_targets
  ↓
alphafold_structures
```

## 추가 DB Tables

### 1. protein_targets

단백질 또는 gene/protein target의 canonical table이다.

```text
protein_id
gene_symbol
uniprot_id
protein_name
organism
source
created_at
```

권장 사용:

```text
protein_id: 내부 ID
gene_symbol: EGFR, JAK1, TNF 등
uniprot_id: AlphaFold DB와 연결할 핵심 ID
organism: 기본 Homo sapiens
source: manual, uniprot, hgnc 등
```

### 2. target_protein_links

raw target text를 protein target으로 매핑하는 table이다.

```text
link_id
target_text
normalized_target_text
protein_id
mapping_status
confidence
source
raw_json
created_at
```

`mapping_status`:

```text
exact
alias
manual
unresolved
rejected
```

중요:

```text
pathway나 mechanism처럼 단백질 구조와 직접 연결할 수 없는 target은 unresolved 또는 rejected로 둔다.
억지로 AlphaFold 구조에 연결하지 않는다.
```

### 3. alphafold_structures

AlphaFold/PDB/local/predicted 구조 파일의 위치를 저장한다.

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
created_at
updated_at
```

`provider`:

```text
alphafold_db
pdb
local
predicted
```

`status`:

```text
available
to_fetch
missing
failed
```

권장:

```text
AlphaFold DB에서 이미 제공되는 구조는 provider=alphafold_db
PDB 실험 구조를 쓰는 경우 provider=pdb
직접 예측한 구조는 provider=predicted
파일을 S3에 둔 경우 structure_uri에 s3://... 저장
```

### 4. candidate_protein_structure_links

질환/약물 후보 context와 protein structure를 연결하는 table이다.

```text
context_id
disease_id
candidate_id
canonical_drug_id
evidence_id
protein_id
structure_id
target_source
relation_note
created_at
```

`target_source`:

```text
candidate_target
image_evidence
kg_target
manual
```

의미:

```text
같은 protein structure라도 어떤 질환, 어떤 후보 약물, 어떤 근거에서 연결됐는지 보존한다.
프론트에서 약물 상세 화면의 "구조보기" 버튼을 만들 때 이 table을 기준으로 조회한다.
```

## 왜 약물에 바로 AlphaFold를 붙이지 않는가

AlphaFold는 약물 구조가 아니라 protein structure를 제공한다.

따라서 아래 흐름이 맞다.

```text
약물
→ 약물이 작용한다고 추정되는 target protein
→ target protein의 AlphaFold/PDB 구조
```

약물 자체의 3D structure는 AlphaFold가 아니라 PubChem/ChEMBL/RDKit/PDB ligand 같은 별도 영역이다.

## API 초안

이번 단계에서는 구현하지 않고 계약만 둔다.

### 후보 약물 구조 목록

```http
GET /api/structures?disease_id=RA&canonical_drug_id=cdrug_xxx
```

응답 초안:

```json
{
  "disease_id": "RA",
  "canonical_drug_id": "cdrug_xxx",
  "structures": [
    {
      "protein_id": "protein_egfr",
      "gene_symbol": "EGFR",
      "uniprot_id": "P00533",
      "provider": "alphafold_db",
      "structure_uri": "s3://say2-4team/structures/alphafold/P00533.cif",
      "file_format": "mmcif",
      "mean_plddt": 86.4,
      "target_source": "candidate_target"
    }
  ]
}
```

### 단백질 구조 상세

```http
GET /api/structures/{structure_id}
```

응답 초안:

```json
{
  "structure_id": "af_p00533_v4",
  "protein_id": "protein_egfr",
  "gene_symbol": "EGFR",
  "uniprot_id": "P00533",
  "provider": "alphafold_db",
  "file_format": "mmcif",
  "structure_uri": "s3://say2-4team/structures/alphafold/P00533.cif",
  "source_url": "https://alphafold.ebi.ac.uk/entry/P00533",
  "status": "available"
}
```

## 프론트엔드 구조보기 방향

프론트에서는 약물 상세 panel에 아래처럼 붙이는 것이 좋다.

```text
약물 선택
→ target/protein mapping 존재 여부 확인
→ 구조보기 버튼 활성화
→ structure viewer modal open
```

viewer 후보:

```text
Mol*
NGL Viewer
3Dmol.js
```

현재 추천:

```text
Mol* 또는 3Dmol.js
```

## Guardrail

```text
- AlphaFold를 약물 구조 예측 도구로 오해하지 않는다.
- raw target이 pathway/free-text인 경우 protein으로 강제 매핑하지 않는다.
- 구조 파일 원본을 GitHub에 올리지 않는다.
- 대용량 PDB/mmCIF/PAE 파일은 S3에 둔다.
- DB에는 structure URI와 metadata만 저장한다.
- 예측 실행은 별도 승인 전까지 하지 않는다.
```

## 다음 단계

```text
1. raw target text 중 gene/protein 후보만 분류
2. UniProt ID 매핑 table 생성
3. AlphaFold DB URL/파일 URI 매핑
4. FastAPI /api/structures endpoint 구현
5. React structure viewer modal 구현
6. 필요 시 S3 구조 파일 cache 정책 결정
```

## 현재 완료 기준

```text
- AlphaFold 구조보기용 DB schema 초안 작성
- raw target과 protein을 분리하는 설계 반영
- protein structure metadata table 정의
- 후보 약물/질환 context와 구조 연결 table 정의
- 실제 AlphaFold 실행/다운로드는 하지 않음
```
