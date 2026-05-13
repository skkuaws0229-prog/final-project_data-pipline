# AlphaFold Target Mapping 무결성 검증 v1

## 목적

`10_alphafold` 산출물을 수동 검토로 넘기기 전에, 자동 분류 결과에 명백한 오류가 없는지 다시 검증했다.

이번 검증에서도 외부 API는 호출하지 않았다.

```text
AlphaFold DB API 호출 없음
AlphaFold Server 호출 없음
UniProt API 호출 없음
구조 파일 다운로드 없음
DB seed 적재 없음
```

## 검증 대상

```text
10_alphafold/build_target_mapping_candidates_v1.py
10_alphafold/target_mapping_candidates_v1.csv
10_alphafold/target_mapping_exclusions_v1.csv
10_alphafold/target_mapping_parsed_tokens_v1.csv
10_alphafold/protein_targets_seed_v1.csv
10_alphafold/target_mapping_summary_v1.md
```

## 최종 생성 건수

| file | rows |
| --- | ---: |
| target_mapping_candidates_v1.csv | 80 |
| target_mapping_exclusions_v1.csv | 58 |
| target_mapping_parsed_tokens_v1.csv | 181 |
| protein_targets_seed_v1.csv | 80 |

요약:

```text
unique raw target/pathway texts: 138
mapping candidates: 80
exclusions: 58
protein seed rows: 80
parsed multi-target token rows: 181
```

## 검증 항목

| 검증 항목 | 결과 |
| --- | --- |
| candidate CSV 안에 placeholder 혼입 | PASS |
| candidate CSV 안에 pathway/free-text keyword 혼입 | PASS |
| exclusion CSV 안에 clean gene symbol 혼입 | PASS |
| parsed token CSV 안에 nan/Other/others 혼입 | PASS |
| parsed token CSV 안에 ANTHRACYCLINE/ANTIMETABOLITE 혼입 | PASS |
| UniProt ID 자동 확정 여부 | PASS: 모두 비워둠 |
| 외부 API 호출 여부 | PASS: 없음 |

## Candidate class 분포

| class | count |
| --- | ---: |
| exact_gene_symbol_candidate | 18 |
| alias_or_family_review | 10 |
| multi_target_parse_review | 52 |

해석:

```text
단일 gene symbol 후보는 18개다.
alias/family/complex 검토 대상은 10개다.
multi-target raw text는 52개이며, 이 때문에 parsed token CSV를 별도로 생성했다.
```

## Exclusion reason 분포

| reason | count |
| --- | ---: |
| pathway_or_free_text | 33 |
| non_protein_mechanism | 13 |
| free_text_or_mechanism | 9 |
| placeholder | 3 |

## Parsed Token 보강

수동 검토 전 보강으로 아래 파일을 추가했다.

```text
10_alphafold/target_mapping_parsed_tokens_v1.csv
```

이 파일은 `MEK1, MEK2`, `PARP1, PARP2`, `BCL2;NR1I2;TUBB1` 같은 다중 target raw text를 token 단위로 분리한 검토용 파일이다.

예시:

| source_target_text | parsed_token | suggested_gene_symbol |
| --- | --- | --- |
| MEK1, MEK2 | MEK1 | MAP2K1 |
| MEK1, MEK2 | MEK2 | MAP2K2 |
| PARP1, PARP2 | PARP1 | PARP1 |
| PARP1, PARP2 | PARP2 | PARP2 |
| AURKA, AURKB, AURKC, others | AURKA | AURKA |
| AURKA, AURKB, AURKC, others | AURKB | AURKB |
| AURKA, AURKB, AURKC, others | AURKC | AURKC |

보정 사항:

```text
others 제거
ANTHRACYCLINE 제거
ANTIMETABOLITE 제거
```

## 아직 사람이 봐야 하는 이유

아래 값은 자동 확정하면 위험하다.

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

이들은 alias, family, protein complex, isoform, pathway shorthand일 수 있다. 따라서 UniProt ID는 자동으로 채우지 않았다.

## 수동 검토 전 우선순위

수동 검토를 하더라도 전부 한꺼번에 보면 비효율적이다. 아래 순서를 권장한다.

```text
1. exact_gene_symbol_candidate 18개
2. target_mapping_parsed_tokens_v1.csv에서 suggested_gene_symbol이 채워진 token
3. alias_or_family_review 10개
4. multi_target_parse_review 원문 중 parse가 애매한 row
```

## 다음 산출물

다음 단계에서 만들 파일:

```text
10_alphafold/protein_targets_seed_reviewed_v1.csv
10_alphafold/target_protein_links_seed_reviewed_v1.csv
```

이 두 파일에는 사람이 확인한 `gene_symbol`, `uniprot_id`, `mapping_status`, `confidence`를 넣는다.

## 결론

현재 mapping 후보 산출물은 수동 검토로 넘길 수 있는 수준까지 정리됐다.

다만 아직 UniProt ID가 없으므로 AlphaFold 구조 metadata 조회나 `/api/structures` 구현으로 넘어가면 안 된다.
