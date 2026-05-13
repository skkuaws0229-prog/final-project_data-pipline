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
| canonical_drug_id present | 243 |
| canonical_drug_id empty | 18 |

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

## API 반영 확인

```text
GET /api/structures/af_p23458_f1_v6
structure_status: pending
context_links: 25
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
canonical_drug_id가 비어도 relation_note에 drug_id/drug_name을 보존한다.
```

## 운영 주의

```text
docker compose up -d --build api 실행 시 db-loader가 다시 실행될 수 있다.
이 경우 candidate_protein_structure_links가 비워지면 아래 loader를 다시 실행한다.

DATABASE_URL=postgresql://drug_service:drug_service_local@localhost:5433/drug_service \
  backend/.venv/bin/python 10_alphafold/build_candidate_structure_links_v1.py --apply
```
