# AlphaFold 구조보기 무결성 검증 리포트 v1

## 목적

AlphaFold 구조보기 단계로 넘어가기 전에, 현재 로컬 DB에 필요한 schema와 원천 target 데이터가 충분한지 검증했다.

이번 검증은 로컬 PostgreSQL 기준이며, AlphaFold 예측 실행, AlphaFold DB 다운로드, UniProt 외부 조회, 구조 파일 생성은 하지 않았다.

## 검증일

```text
2026-05-13
```

## 결론

현재 상태는 **schema는 준비됐지만, 구조보기 데이터는 아직 부족**하다.

즉, AlphaFold 구조보기의 1단계인 DB 구조 설계는 통과했지만, 실제 구조보기까지 가려면 아래 데이터가 추가로 필요하다.

```text
1. raw target text 정규화
2. gene/protein 후보 분류
3. UniProt ID 매핑
4. AlphaFold/PDB structure URI
5. 후보 약물/질환 context와 protein structure 연결 row
```

## AlphaFold Schema 무결성

생성 확인된 table:

```text
protein_targets
target_protein_links
alphafold_structures
candidate_protein_structure_links
```

현재 row count:

| table | rows |
| --- | ---: |
| protein_targets | 0 |
| target_protein_links | 0 |
| alphafold_structures | 0 |
| candidate_protein_structure_links | 0 |

FK 검증:

| 항목 | 결과 |
| --- | ---: |
| alphafold_structures -> protein_targets broken FK | 0 |
| candidate_protein_structure_links -> protein_targets broken FK | 0 |
| candidate_protein_structure_links -> alphafold_structures broken FK | 0 |

해석:

```text
schema 자체는 정상이다.
아직 매핑/구조 데이터가 없기 때문에 프론트 구조보기 API를 만들 수는 있지만, 실제 표시할 구조는 없다.
```

## 기존 Target 데이터 Coverage

### 원천 table별 target coverage

| source | rows | rows_with_target | rows_with_pathway |
| --- | ---: | ---: | ---: |
| drug_candidates | 255 | 191 | 120 |
| image_modal_drug_evidence | 430 | 402 | 218 |

해석:

```text
candidate target만 보면 일부 질환에서 비어 있는 후보가 많다.
image-modal evidence에는 target/pathway text가 더 풍부하다.
따라서 AlphaFold mapping은 candidate target과 image-modal evidence target을 함께 봐야 한다.
```

### 질환별 candidate target 누락

| disease_id | candidate_rows | rows_without_target_or_pathway | rows_with_any_target_text |
| --- | ---: | ---: | ---: |
| BRCA | 15 | 15 | 0 |
| Colon | 15 | 0 | 15 |
| HNSC | 30 | 0 | 30 |
| IPF | 15 | 0 | 15 |
| Liver | 15 | 0 | 15 |
| LUNG | 15 | 1 | 14 |
| PAH | 30 | 0 | 30 |
| PDAC | 30 | 0 | 30 |
| Psoriasis | 30 | 20 | 10 |
| RA | 30 | 26 | 4 |
| STAD | 30 | 0 | 30 |

중요:

```text
BRCA는 candidate table 기준 target/pathway가 전부 비어 있다.
RA와 Psoriasis도 candidate target coverage가 낮다.
이 질환들은 image-modal evidence 또는 별도 target annotation을 활용해야 구조보기 연결이 가능하다.
```

## 약물 후보 연결 무결성

candidate row의 canonical drug 연결:

| disease_id | candidate_rows | rows_with_canonical_drug | rows_missing_canonical_drug |
| --- | ---: | ---: | ---: |
| BRCA | 15 | 15 | 0 |
| Colon | 15 | 15 | 0 |
| HNSC | 30 | 30 | 0 |
| IPF | 15 | 15 | 0 |
| Liver | 15 | 15 | 0 |
| LUNG | 15 | 15 | 0 |
| PAH | 30 | 30 | 0 |
| PDAC | 30 | 30 | 0 |
| Psoriasis | 30 | 30 | 0 |
| RA | 30 | 30 | 0 |
| STAD | 30 | 30 | 0 |

해석:

```text
약물 후보와 canonical_drug_id 연결은 충분하다.
AlphaFold 구조보기의 병목은 약물 매칭이 아니라 target -> protein -> structure 매핑이다.
```

## Gene-like Target 후보

현재 raw target 중 gene/protein처럼 보이는 주요 후보:

| target | mentions |
| --- | ---: |
| TOP1 | 40 |
| JAK1 | 25 |
| JAK2 | 22 |
| MTOR | 19 |
| PDE5 | 14 |
| ETA | 11 |
| JAK3 | 10 |
| TYK2 | 10 |
| HSP90 | 9 |
| MTORC1 | 8 |
| Proteasome | 5 |
| PI3Kgamma | 4 |
| CDK2 | 3 |
| ETB | 3 |
| PDGFRB | 3 |
| PI3Kbeta | 3 |
| PIK3CG | 3 |
| TP53 | 3 |
| DOT1L | 2 |
| KDR | 2 |
| AURKA | 1 |
| EGFR | 1 |
| EGLN1 | 1 |
| FGFR2 | 1 |
| MET | 1 |
| NAE | 1 |
| PPM1D | 1 |
| TOP2 | 1 |

주의:

```text
gene-like 문자열이라고 해서 모두 바로 UniProt 단백질로 확정하면 안 된다.
예: PDE5, ETA, ETB, HSP90, MTORC1, Proteasome, PI3Kgamma, PI3Kbeta는 alias/complex/family 표현일 수 있다.
UniProt/HGNC/manual mapping이 필요하다.
```

## 제외 또는 보류해야 할 Target Text

AlphaFold 구조에 바로 연결하면 안 되는 대표 값:

| target/pathway text | mentions |
| --- | ---: |
| nan | 78 |
| PI3K/MTOR signaling | 50 |
| Other | 17 |
| ERK MAPK signaling | 14 |
| Endothelin + NO/PDE5 pathway | 7 |
| Other, kinases | 7 |
| RTK signaling | 7 |
| EGFR signaling | 3 |
| IGF1R signaling | 3 |
| p53 pathway | 3 |

해석:

```text
이 값들은 pathway, placeholder, free-text, 복합축 표현이다.
target_protein_links에서 unresolved 또는 rejected로 관리해야 한다.
특히 nan은 Postgres raw text에 남아 있으므로 AlphaFold mapping 입력에서 반드시 제외해야 한다.
```

## 빠진 데이터

현재 없는 데이터:

```text
protein_targets row
target_protein_links row
alphafold_structures row
candidate_protein_structure_links row
UniProt ID
AlphaFold DB accession/version
structure_uri
source_url
mean_plddt
PAE file URI
structure license
target mapping confidence
```

아직 없는 API:

```text
GET /api/structures
GET /api/structures/{structure_id}
```

아직 없는 프론트 기능:

```text
약물 상세의 구조보기 버튼
protein target 선택 UI
3D structure viewer modal
S3 structure file 로딩
```

## 무결성 판단

### 통과

```text
AlphaFold schema 생성
AlphaFold table FK 구조
candidate -> canonical_drug_id 연결
target raw text source 존재
image-modal evidence target source 존재
```

### 보강 필요

```text
raw target 정규화
placeholder nan 제거
pathway/free-text와 gene/protein 분리
gene/protein alias mapping
UniProt ID mapping
AlphaFold/PDB structure metadata 적재
candidate/evidence context와 protein structure 연결
```

### 현재 바로 하면 위험한 것

```text
raw target을 전부 gene으로 간주
pathway text를 단일 AlphaFold 구조로 강제 연결
ETA/ETB/PDE5/HSP90 같은 alias를 검증 없이 UniProt에 연결
BRCA/RA/Psoriasis를 candidate target만 기준으로 구조보기 판단
구조 파일을 GitHub에 저장
```

## 다음 작업 제안

우선순위 2단계:

```text
1. target_normalization 후보 CSV 생성
2. gene/protein-like target만 선별
3. nan/Other/pathway/free-text 제외 목록 생성
4. UniProt ID 수동/반자동 매핑 table 작성
5. protein_targets, target_protein_links에 seed data 적재
6. AlphaFold DB URL 또는 S3 URI metadata 적재
```

권장 산출물:

```text
docs/alphafold_target_mapping_plan_v1.md
10_alphafold/target_mapping_candidates_v1.csv
10_alphafold/target_mapping_exclusions_v1.csv
10_alphafold/protein_targets_seed_v1.csv
```

## 결론

AlphaFold 구조보기는 진행 가능하지만, 지금 바로 viewer/API를 붙이면 보여줄 구조 데이터가 없다.

따라서 다음 단계는 구조 viewer가 아니라 **target -> protein -> UniProt 매핑 데이터 생성**이다.
