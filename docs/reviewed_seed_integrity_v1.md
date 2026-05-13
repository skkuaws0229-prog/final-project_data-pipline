# Reviewed UniProt Seed 생성 결과 v1

## 목적

UniProt 자동 매핑 후보 중 `auto_suggested`만 DB seed 후보로 분리했다.
이 단계에서는 AlphaFold DB 구조 조회, 구조 다운로드, DB 적재를 실행하지 않았다.

## 생성 파일

```text
10_alphafold/protein_targets_seed_reviewed_v1.csv
10_alphafold/target_protein_links_seed_reviewed_v1.csv
10_alphafold/uniprot_mapping_hold_v1.csv
```

## Row Count

| file | rows |
| --- | ---: |
| protein_targets_seed_reviewed_v1.csv | 27 |
| target_protein_links_seed_reviewed_v1.csv | 28 |
| uniprot_mapping_hold_v1.csv | 1 |

## Link Mapping Status

| mapping_status | rows |
| --- | ---: |
| alias | 11 |
| exact | 17 |

## Disease Coverage

| disease | proteins |
| --- | ---: |
| BRCA | 2 |
| Colon | 6 |
| HNSC | 7 |
| IPF | 4 |
| LUNG | 2 |
| Liver | 2 |
| PAH | 3 |
| PDAC | 7 |
| Psoriasis | 4 |
| RA | 2 |
| STAD | 3 |

## 보류 항목

| gene | uniprot_id | status | reason |
| --- | --- | --- | --- |
| MET | P08581 | needs_review_multi_hit | auto_suggested가 아니므로 reviewed seed v1에서 보류 |

## 무결성 결과

```text
protein_id duplicate: 0
uniprot_id duplicate: 0
gene_symbol duplicate: 0
target_text + protein_id duplicate: 0
target_protein_links -> protein_targets FK missing: 0
hold list: MET only
```

판정: 통과

## 다음 단계

```text
1. reviewed seed CSV를 사람이 최종 확인
2. MET multi-hit를 수동 검토
3. protein_targets / target_protein_links DB seed 적재 스크립트 작성
4. 이후 AlphaFold DB 구조 조회는 별도 단계에서 실행
```
