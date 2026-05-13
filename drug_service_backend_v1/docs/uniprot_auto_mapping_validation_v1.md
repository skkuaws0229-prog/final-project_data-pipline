# UniProt 자동 매핑 검증 리포트 v1

## 목적

P1/P2 target과 alias 검토표에서 suggested gene symbol이 있는 항목을 대상으로 UniProt 자동 매핑 후보를 생성했다.

이번 단계는 자동 후보 생성 단계이며, production 확정 또는 DB seed 적재 단계가 아니다.

## 실행 범위

실행함:

```text
UniProt REST API gene_exact query
Homo sapiens organism filter
reviewed entry filter
```

실행하지 않음:

```text
AlphaFold DB API 호출
AlphaFold Server 호출
구조 파일 다운로드
S3 구조 파일 업로드
PostgreSQL seed 적재
FastAPI /api/structures 구현
```

## 입력 파일

```text
10_alphafold/target_priority_for_structure_v1.csv
10_alphafold/alias_resolution_review_v1.csv
```

## 출력 파일

```text
10_alphafold/auto_map_uniprot_candidates_v1.py
10_alphafold/uniprot_auto_mapping_candidates_v1.csv
10_alphafold/uniprot_auto_mapping_summary_v1.md
```

## 결과 요약

```text
input targets: 28
auto_suggested: 27
needs_review_multi_hit: 1
query failures: 0
```

## 자동 매핑 정책

자동 조회 조건:

```text
gene_exact:{gene_symbol}
organism_id:9606
reviewed:true
```

`auto_suggested` 조건:

```text
UniProt accession 존재
UniProt primary gene이 suggested_gene_symbol과 일치
hit_count = 1
```

`needs_review_multi_hit` 조건:

```text
UniProt accession 존재
primary gene은 일치
hit_count > 1
```

## 자동 제안된 P1 target

| target | UniProt | protein |
| --- | --- | --- |
| JAK1 | P23458 | Tyrosine-protein kinase JAK1 |
| JAK2 | O60674 | Tyrosine-protein kinase JAK2 |
| JAK3 | P52333 | Tyrosine-protein kinase JAK3 |
| MTOR | P42345 | Serine/threonine-protein kinase mTOR |
| TOP1 | P11387 | DNA topoisomerase 1 |
| TYK2 | P29597 | Non-receptor tyrosine-protein kinase TYK2 |

## 재검토 필요 항목

| gene | suggested UniProt | hit_count | status | 이유 |
| --- | --- | ---: | --- | --- |
| MET | P08581 | 2 | needs_review_multi_hit | reviewed human gene_exact hit이 2개라 수동 확인 필요 |

## 주의사항

```text
auto_suggested는 확정이 아니다.
자동 결과는 reviewed seed로 승격하기 전에 사람이 한 번 더 확인한다.
alias/family/complex 항목은 특히 문맥 검토가 필요하다.
MET처럼 multi-hit인 항목은 우선 보류한다.
```

## 다음 단계

권장:

```text
1. uniprot_auto_mapping_candidates_v1.csv 검토
2. auto_suggested 27개 중 P1부터 reviewed seed로 승격
3. MET multi-hit 원인 확인
4. protein_targets_seed_reviewed_v1.csv 생성
5. target_protein_links_seed_reviewed_v1.csv 생성
6. DB 적재 전 FK/중복 검증
```

아직 금지:

```text
AlphaFold structure metadata 조회
구조 파일 다운로드
프론트 viewer 구현
```
