# Target Mapping Policy and Review Tables v1

## 목적

AlphaFold 구조보기뿐 아니라 KG, RAG, LLM 설명, 프론트 약물 상세 화면에서 함께 쓸 수 있는 target 표준화 정책과 검토표를 만들었다.

이번 단계에서는 외부 API를 호출하지 않았다.

```text
UniProt API 호출 없음
AlphaFold DB API 호출 없음
AlphaFold Server 호출 없음
구조 파일 다운로드 없음
DB seed 적재 없음
```

## 산출물

```text
10_alphafold/uniprot_mapping_policy_v1.md
10_alphafold/alias_resolution_review_v1.csv
10_alphafold/target_priority_for_structure_v1.csv
10_alphafold/mapping_review_tables_summary_v1.md
10_alphafold/build_mapping_review_tables_v1.py
```

## 정책 문서 핵심

`uniprot_mapping_policy_v1.md`는 아래 기준을 정의한다.

```text
- raw target을 모두 gene으로 간주하지 않음
- pathway/mechanism/drug class/free-text는 protein target과 분리
- UniProt은 Homo sapiens reviewed canonical protein 우선
- alias/family/complex는 자동 확정하지 않음
- 다중 target은 token 단위로 분해하되 원문 보존
- mapping_status와 판단 근거를 남김
```

## Alias 검토표

파일:

```text
10_alphafold/alias_resolution_review_v1.csv
```

row count:

```text
30 rows
```

대표 항목:

| raw_text | suggested_gene_symbol | reason |
| --- | --- | --- |
| PDE5 | PDE5A | PAH 문맥에서 검토 필요 |
| ETA | EDNRA | endothelin receptor A 검토 |
| HSP90 |  | family/isoform 선택 필요 |
| MEK1 | MAP2K1 | parsed token alias |
| MEK2 | MAP2K2 | parsed token alias |
| MTORC1 |  | complex 처리 필요 |
| Proteasome |  | complex 처리 필요 |
| BCL-XL | BCL2L1 | alias 검토 |
| IKK-1 | CHUK | alias 검토 |
| IKK-2 | IKBKB | alias 검토 |
| IR | INSR | 문맥 검토 |

## Target 우선순위표

파일:

```text
10_alphafold/target_priority_for_structure_v1.csv
```

row count:

```text
80 rows
```

우선순위 기준:

| priority | 의미 |
| --- | --- |
| P1 | mentions가 많고 exact gene symbol인 target |
| P2 | exact gene 또는 빈도 높은 alias/family target |
| P3 | multi-target parsing 또는 candidate source가 있는 target |
| P4 | 낮은 빈도 또는 evidence-only target |

P1 target:

```text
TOP1
JAK1
JAK2
MTOR
JAK3
TYK2
```

P2 주요 target:

```text
PDE5
ETA
HSP90
MTORC1
Proteasome
CDK2
PDGFRB
PIK3CG
TP53
EGFR
MET
```

## 사용 방법

권장 순서:

```text
1. uniprot_mapping_policy_v1.md 확인
2. target_priority_for_structure_v1.csv에서 P1부터 검토
3. alias_resolution_review_v1.csv에서 alias/family/complex 검토
4. 확인된 gene_symbol/uniprot_id를 reviewed seed CSV로 복사
5. protein_targets / target_protein_links seed 적재
6. 이후 AlphaFold DB metadata 조회
```

## 아직 하지 않은 것

```text
UniProt ID 확정
AlphaFold DB coverage 확인
AlphaFold structure URI 생성
PostgreSQL seed 적재
FastAPI /api/structures 구현
React structure viewer 구현
```

## 결론

이제 수동 검토를 하더라도 전체 138개 raw target을 처음부터 보는 것이 아니라, 정책과 우선순위에 따라 P1/P2와 alias 검토표부터 보면 된다.

이 자료는 AlphaFold뿐 아니라 KG/RAG/LLM 설명의 target 표준화 기준으로도 사용할 수 있다.
