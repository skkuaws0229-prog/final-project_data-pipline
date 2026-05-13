# Candidate Protein Structure Link 생성/적재 검증 v1

## 목적

`drug_candidates`와 `image_modal_drug_evidence`의 target 표현을 `target_protein_links`와 보수적으로 매칭해 `candidate_protein_structure_links` seed를 생성한다.

## 생성 파일

```text
10_alphafold/candidate_protein_structure_links_seed_v1.csv
```

## Row Count

| 대상 | rows |
| --- | ---: |
| candidate_protein_structure_links seed | 261 |

## Source Count

| target_source | rows |
| --- | ---: |
| candidate_target | 108 |
| image_evidence | 153 |

## Canonical Drug Mapping

| 항목 | rows |
| --- | ---: |
| canonical_drug_id present | 261 |
| canonical_drug_id empty | 0 |

## Disease Count

| disease_id | rows |
| --- | ---: |
| BRCA | 4 |
| Colon | 36 |
| HNSC | 45 |
| IPF | 15 |
| LUNG | 3 |
| Liver | 7 |
| PAH | 28 |
| PDAC | 48 |
| Psoriasis | 54 |
| RA | 4 |
| STAD | 17 |

## 실행 모드

```text
applied_to_db: true
```

## 검증 결과

```text
context_id duplicate: 0
context semantic duplicate: 0
target_source invalid: 0
disease_id FK missing: 0
candidate_id FK missing: 0
canonical_drug_id FK missing: 0
evidence_id FK missing: 0
protein_id FK missing: 0
structure_id FK missing: 0
```

판정: 통과

## 매칭 정책

```text
target_protein_links.target_text가 candidate/evidence target 문자열 안에 token 단위로 등장하는 경우만 연결했다.
target_protein_links.raw_json.diseases에 현재 disease_id가 포함된 경우만 연결했다.
복합 target의 모든 구성요소를 임의로 확장하지 않고, reviewed seed에 있는 target 표현만 사용했다.
canonical_drug_id는 source_drug_id 우선, drug name/alias fallback 순서로 채웠다.
relation_note에는 원천 drug_id/drug_name을 함께 보존한다.
```

## Canonical Drug 보강 확인

초기 검증에서 `canonical_drug_id`가 비어 있던 18개 row는 모두 `image_evidence`에서 온 row였다.

원인은 source_drug_id 직접 매핑 누락이었고, drug name/alias로는 이미 canonical drug이 존재했다.

보강 후 아래 6개 source drug이 canonical으로 연결됐다.

```text
CCT007093 -> cdrug_c7bcca826492e28a
JNJ-7706621 -> cdrug_93ce5173efc14556
LMP744 -> cdrug_25c95fa72ddae840
MIRA-1 -> cdrug_d8014f6e4666f0f3
PD0325901 -> cdrug_437729aca9b5a6f7
Refametinib -> cdrug_8bfd50149ba3e72c
```
