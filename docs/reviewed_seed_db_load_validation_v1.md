# Reviewed UniProt Seed DB 적재 검증 v1

## 목적

`protein_targets_seed_reviewed_v1.csv`와 `target_protein_links_seed_reviewed_v1.csv`를 PostgreSQL seed로 적재하기 전 검증한다.
기본 실행은 dry-run이며, 실제 DB 변경은 `--apply` 실행 시에만 수행한다.

## 입력 파일

```text
10_alphafold/protein_targets_seed_reviewed_v1.csv
10_alphafold/target_protein_links_seed_reviewed_v1.csv
10_alphafold/uniprot_mapping_hold_v1.csv
```

## Row Count

| 대상 | rows |
| --- | ---: |
| protein_targets seed | 27 |
| target_protein_links seed | 28 |
| hold list | 1 |

## 실행 모드

```text
applied_to_db: true
```

## 검증 결과

```text
protein_id duplicate: 0
uniprot_id duplicate: 0
gene_symbol duplicate: 0
link_id duplicate: 0
target_text + protein_id duplicate: 0
target_protein_links -> protein_targets FK missing: 0
mapping_status enum invalid: 0
confidence invalid: 0
raw_json invalid: 0
hold list: MET only
```

판정: 통과

## 주의

```text
이 loader는 protein_targets와 target_protein_links만 다룬다.
alphafold_structures와 candidate_protein_structure_links는 구조 metadata 확보 후 별도 단계에서 적재한다.
AlphaFold DB API 호출과 구조 다운로드는 이 단계에서 실행하지 않는다.
```
