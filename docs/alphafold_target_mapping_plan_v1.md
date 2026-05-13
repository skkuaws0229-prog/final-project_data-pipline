# AlphaFold Target Mapping Plan v1

## 목적

AlphaFold 구조보기로 가기 전에, 현재 DB/CSV에 있는 raw `target`, `target_pathway` 값을 단백질 구조 매핑 후보와 제외 대상으로 분리했다.

이번 단계에서는 AlphaFold DB API, AlphaFold Server, UniProt API, 구조 파일 다운로드를 실행하지 않았다. 오직 로컬 CSV만 사용했다.

## 입력 데이터

```text
03_normalized/drug_candidates.csv
03_normalized/image_modal_drug_evidence.csv
```

사용한 컬럼:

```text
target
target_pathway
disease_id
source_file
```

## 산출물

```text
10_alphafold/target_mapping_candidates_v1.csv
10_alphafold/target_mapping_exclusions_v1.csv
10_alphafold/target_mapping_parsed_tokens_v1.csv
10_alphafold/protein_targets_seed_v1.csv
10_alphafold/target_mapping_summary_v1.md
10_alphafold/build_target_mapping_candidates_v1.py
```

## 생성 결과

```text
unique raw target/pathway texts: 138
mapping candidates: 80
exclusions: 58
protein seed rows: 80
```

CSV line count:

```text
protein_targets_seed_v1.csv: 81 lines including header
target_mapping_candidates_v1.csv: 81 lines including header
target_mapping_exclusions_v1.csv: 59 lines including header
target_mapping_parsed_tokens_v1.csv: 182 lines including header
```

## Mapping Candidate 기준

후보로 분리한 값:

```text
clean gene-like symbol
alias/family/complex review 대상
multi-target parsing review 대상
```

대표 후보:

| target_text | candidate_class | suggested_gene_symbol | mentions | 비고 |
| --- | --- | --- | ---: | --- |
| TOP1 | exact_gene_symbol_candidate | TOP1 | 40 | UniProt 확인 필요 |
| JAK1 | exact_gene_symbol_candidate | JAK1 | 25 | UniProt 확인 필요 |
| JAK2 | exact_gene_symbol_candidate | JAK2 | 22 | UniProt 확인 필요 |
| MTOR | exact_gene_symbol_candidate | MTOR | 19 | UniProt 확인 필요 |
| PDE5 | alias_or_family_review | PDE5A | 14 | 수동 검토 필요 |
| ETA | alias_or_family_review | EDNRA | 11 | 수동 검토 필요 |
| JAK3 | exact_gene_symbol_candidate | JAK3 | 10 | UniProt 확인 필요 |
| TYK2 | exact_gene_symbol_candidate | TYK2 | 10 | UniProt 확인 필요 |
| HSP90 | alias_or_family_review |  | 9 | family/isoform 검토 필요 |
| MEK1, MEK2 | multi_target_parse_review |  | 8 | MAP2K1/MAP2K2 parsing 필요 |

중요:

```text
suggested_gene_symbol은 확정값이 아니다.
UniProt ID는 아직 비워뒀다.
사람이 검토한 뒤 protein_targets / target_protein_links에 적재해야 한다.
```

## Exclusion 기준

제외로 분리한 값:

```text
placeholder
non-protein mechanism
pathway/free-text
drug class
biological process
```

대표 제외:

| target_text | exclusion_reason | mentions | 비고 |
| --- | --- | ---: | --- |
| DNA replication | non_protein_mechanism | 101 | 단일 protein 아님 |
| nan | placeholder | 78 | 반드시 제외 |
| Mitosis | non_protein_mechanism | 59 | 단일 protein 아님 |
| PI3K/MTOR signaling | pathway_or_free_text | 50 | pathway |
| Microtubule stabiliser | non_protein_mechanism | 21 | drug mechanism |
| Protein stability and degradation | pathway_or_free_text | 21 | pathway/free-text |
| Other | placeholder | 17 | 제외 |
| ERK MAPK signaling | pathway_or_free_text | 14 | pathway |
| JAK/STAT inflammatory axis | pathway_or_free_text | 14 | pathway/axis |
| B-cell / BTK axis | pathway_or_free_text | 10 | pathway/axis |

## 왜 UniProt ID를 자동으로 채우지 않았는가

이번 요청의 조건은 AlphaFold 실행/API 호출 없이 매핑부터 진행하는 것이다.

또한 아래 값들은 겉보기에는 protein처럼 보여도 여러 의미를 가질 수 있다.

```text
PDE5
ETA
ETB
HSP90
MTORC1
Proteasome
TOP2
NAE
PI3Kgamma
PI3Kbeta
```

예를 들어 `HSP90`은 여러 isoform/family member가 있을 수 있고, `Proteasome`은 단일 단백질이 아니라 복합체다. 따라서 API로 자동 매핑하기 전에 수동 검토가 필요하다.

## 다음 단계

권장 순서:

```text
1. target_mapping_candidates_v1.csv 검토
2. exact_gene_symbol_candidate부터 UniProt ID 매핑
3. target_mapping_parsed_tokens_v1.csv에서 다중 target 분해 후보 검토
4. alias_or_family_review는 수동 검토
5. 검토 완료된 row만 protein_targets_seed_v1.csv에 uniprot_id 입력
6. protein_targets / target_protein_links에 seed data 적재
7. 그 다음 AlphaFold DB API metadata 조회
```

## 아직 하지 않은 것

```text
AlphaFold DB API 호출
AlphaFold Server 호출
UniProt REST API 호출
AlphaFold/PDB 구조 파일 다운로드
S3 구조 파일 업로드
PostgreSQL protein_targets seed 적재
FastAPI /api/structures 구현
React structure viewer 구현
```

## 무결성 판단

현재 매핑 준비 단계는 통과다.

```text
raw target/pathway 후보 추출 완료
protein mapping 후보/제외 분리 완료
placeholder nan 제외 목록 분리 완료
UniProt 자동 확정 없음
외부 API 호출 없음
구조 다운로드 없음
```

다음 단계의 핵심 산출물은 UniProt ID가 채워진 `protein_targets_seed_v1.csv`다.
