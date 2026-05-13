# Target/UniProt Mapping Policy v1

## 목적

이 문서는 AlphaFold 구조보기만을 위한 문서가 아니다.

약물 후보의 raw `target`, `target_pathway` 값을 전체 프로젝트에서 재사용 가능한 표준 target/protein 데이터로 정리하기 위한 운영 기준이다.

사용처:

```text
PostgreSQL target/protein tables
Neo4j KG target/protein node 보강
OpenSearch/RAG evidence 정리
Bedrock/LLM 설명 근거
AlphaFold/PDB 구조보기
React 약물 상세 화면
```

## 기본 원칙

```text
1. raw target을 모두 gene으로 간주하지 않는다.
2. pathway, mechanism, drug class, free-text는 protein target과 분리한다.
3. UniProt ID는 Homo sapiens reviewed canonical protein을 우선한다.
4. alias/family/complex 표현은 자동 확정하지 않는다.
5. 다중 target은 token 단위로 분해하되 원문도 보존한다.
6. 판단 근거와 mapping_status를 반드시 남긴다.
```

## 표준 Target Type

| type | 의미 | 예시 | 처리 |
| --- | --- | --- | --- |
| protein_gene | 단일 gene/protein | JAK1, TOP1, EGFR | UniProt 매핑 우선 |
| protein_alias | 관용 alias | PDE5, ETA, BCL-XL | 수동 검토 후 매핑 |
| protein_family | family/isoform 표현 | HSP90, TOP2 | 보류 또는 복수 매핑 |
| protein_complex | 복합체 | MTORC1, Proteasome | 단일 구조 강제 연결 금지 |
| pathway | pathway/axis | PI3K/MTOR signaling | RAG/KG pathway로 보존 |
| mechanism | 약물 작용 기전 | DNA alkylating agent | protein 구조 매핑 제외 |
| placeholder | 비정보 값 | nan, Other | 제외 |
| free_text | 긴 설명/혼합 텍스트 | EGFR signaling ... | parsing 후 검토 |

## Mapping Status

| status | 의미 |
| --- | --- |
| exact | gene_symbol과 UniProt canonical gene이 일치 |
| alias | alias를 표준 gene으로 변환 |
| manual | 사람이 근거를 보고 확정 |
| multi_target | 여러 gene/protein으로 분해 필요 |
| complex | 복합체라 단일 UniProt으로 확정 불가 |
| unresolved | 현재 정보만으로 확정 불가 |
| rejected | protein target이 아니므로 제외 |

## UniProt 선택 기준

우선순위:

```text
1. organism = Homo sapiens
2. reviewed Swiss-Prot entry
3. canonical accession
4. gene symbol exact match
5. protein name/alias와 source target text 일치
```

동명이의어가 있으면:

```text
- 자동 확정하지 않는다.
- alias_resolution_review_v1.csv에서 manual review로 남긴다.
- mapping_status = unresolved 또는 manual_candidate로 둔다.
```

## Alias 처리 예시

| raw target | suggested gene | 정책 |
| --- | --- | --- |
| PDE5 | PDE5A | PAH 문맥에서는 가능성이 높지만 수동 확인 |
| ETA | EDNRA | endothelin receptor A로 검토 |
| ETB | EDNRB | endothelin receptor B로 검토 |
| MEK1 | MAP2K1 | alias 매핑 가능 |
| MEK2 | MAP2K2 | alias 매핑 가능 |
| BCL-XL | BCL2L1 | alias 매핑 가능 |
| IR | INSR | insulin receptor 문맥이면 가능 |
| HSP90 |  | family 표현이라 isoform 선택 필요 |
| TOP2 |  | TOP2A/TOP2B 분해 검토 |
| Proteasome |  | 복합체, 단일 protein 구조로 강제 연결 금지 |
| MTORC1 |  | complex, MTOR 단일 구조와 구분 |

## Exclusion 기준

아래 값은 AlphaFold 구조와 직접 연결하지 않는다.

```text
nan
Other
Other, kinases
DNA replication
Mitosis
Cell cycle
PI3K/MTOR signaling
ERK MAPK signaling
JAK/STAT inflammatory axis
DNA alkylating agent
Microtubule stabiliser
Microtubule destabiliser
Antimetabolite
Anthracycline
```

단, pathway/mechanism으로는 별도 보존한다.

## 우선순위 정책

먼저 처리할 target:

```text
1. mentions가 많고 여러 질환에서 반복되는 exact gene symbol
2. 상위 rank/tier candidate와 연결된 target
3. RAG/LLM 설명에서 자주 등장하는 target
4. 구조보기 효용이 큰 단일 protein
```

나중에 처리할 target:

```text
1. 복합체
2. family/isoform 표현
3. pathway/free-text
4. mentions가 낮고 source가 불명확한 target
```

## 산출물 흐름

```text
target_mapping_candidates_v1.csv
target_mapping_parsed_tokens_v1.csv
        ↓ review
alias_resolution_review_v1.csv
target_priority_for_structure_v1.csv
        ↓ confirmed
protein_targets_seed_reviewed_v1.csv
target_protein_links_seed_reviewed_v1.csv
        ↓ later
AlphaFold DB metadata fetch
```

## 금지 사항

```text
- UniProt ID를 근거 없이 자동 확정하지 않는다.
- pathway를 단일 protein으로 강제 매핑하지 않는다.
- complex를 단일 AlphaFold 구조로 단순화하지 않는다.
- 구조 파일을 GitHub에 올리지 않는다.
- 검토 전 후보를 production table에 적재하지 않는다.
```
