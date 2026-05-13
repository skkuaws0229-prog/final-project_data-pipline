# UniProt 자동 매핑 무결성 검증 v1

## 목적

`uniprot_auto_mapping_candidates_v1.csv`를 DB seed 후보로 승격하기 전에 파일 내부 무결성과 원본 검토표와의 연결성을 확인했다.

이번 검증은 UniProt 자동 매핑 결과만 대상으로 하며, AlphaFold DB API나 구조 다운로드는 실행하지 않았다.

## 검증 대상

```text
10_alphafold/uniprot_auto_mapping_candidates_v1.csv
10_alphafold/target_priority_for_structure_v1.csv
10_alphafold/alias_resolution_review_v1.csv
```

## 결과 요약

| 항목 | 결과 |
| --- | ---: |
| auto mapping rows | 28 |
| auto_suggested | 27 |
| needs_review_multi_hit | 1 |
| query_failed | 0 |
| blank accession | 0 |
| blank suggested gene | 0 |
| duplicate accession | 0 |
| gene mismatch | 0 |
| expected gene missing from auto result | 0 |
| unexpected auto gene | 0 |
| duplicate raw_text pipe values | 0 |

## Status 분포

```text
auto_suggested: 27
needs_review_multi_hit: 1
```

## 원본 검토표 연결성

원본 검토표에서 자동 매핑 대상으로 선정된 gene:

```text
expected genes: 28
auto result genes: 28
missing expected: 0
unexpected auto: 0
```

자동 결과 priority 분포:

| priority | rows |
| --- | ---: |
| P1 | 6 |
| P2 | 14 |
| P2_alias | 8 |

## P1 자동 매핑

| gene | UniProt | entry | protein |
| --- | --- | --- | --- |
| JAK1 | P23458 | JAK1_HUMAN | Tyrosine-protein kinase JAK1 |
| JAK2 | O60674 | JAK2_HUMAN | Tyrosine-protein kinase JAK2 |
| JAK3 | P52333 | JAK3_HUMAN | Tyrosine-protein kinase JAK3 |
| MTOR | P42345 | MTOR_HUMAN | Serine/threonine-protein kinase mTOR |
| TOP1 | P11387 | TOP1_HUMAN | DNA topoisomerase 1 |
| TYK2 | P29597 | TYK2_HUMAN | Non-receptor tyrosine-protein kinase TYK2 |

## 보류 항목

| gene | UniProt | hit_count | status | 조치 |
| --- | --- | ---: | --- | --- |
| MET | P08581 | 2 | needs_review_multi_hit | UniProt 결과 2개 확인 후 하나만 승격 |

## 확인한 무결성 조건

```text
1. 모든 row에 suggested_gene_symbol 존재
2. 모든 row에 auto_uniprot_id 존재
3. UniProt primary gene과 suggested gene 불일치 없음
4. auto_uniprot_id 중복 없음
5. P1/P2/alias 원본에서 자동 매핑 대상으로 잡은 28개 gene이 모두 결과에 존재
6. query_failed 없음
7. raw_text 중복 병합 오류 없음
```

## 아직 seed로 확정하지 않는 이유

`auto_suggested`라도 바로 production table에 넣지 않는다.

이유:

```text
- alias/family 항목은 disease context 확인 필요
- MET는 multi-hit라 보류 필요
- AlphaFold 구조 coverage는 아직 확인하지 않음
- protein_targets / target_protein_links seed format으로 변환 전 검토 필요
```

## 다음 단계

권장 순서:

```text
1. MET multi-hit 수동 확인
2. auto_suggested 27개를 reviewed seed 후보로 변환
3. protein_targets_seed_reviewed_v1.csv 생성
4. target_protein_links_seed_reviewed_v1.csv 생성
5. seed CSV 중복/FK 검증
6. 그 다음 PostgreSQL seed 적재
```

아직 하지 말 것:

```text
AlphaFold DB API metadata 조회
구조 파일 다운로드
FastAPI /api/structures 구현
React structure viewer 구현
```
