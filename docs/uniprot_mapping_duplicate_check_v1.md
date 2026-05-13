# UniProt/Target Mapping 중복 검증 v1

## 목적

reviewed seed CSV를 만들기 전에 target/UniProt 매핑 산출물에 중복 문제가 있는지 확인했다.

검증 대상:

```text
10_alphafold/uniprot_auto_mapping_candidates_v1.csv
10_alphafold/target_mapping_candidates_v1.csv
10_alphafold/target_mapping_parsed_tokens_v1.csv
10_alphafold/alias_resolution_review_v1.csv
10_alphafold/target_priority_for_structure_v1.csv
```

## 핵심 결론

```text
최종 UniProt 자동 매핑 결과에는 중복 없음
reviewed seed 후보 27개에도 protein_id/gene/accession 중복 없음
parsed token/alias 검토표에는 의도된 provenance 중복 존재
```

## Auto Mapping 중복 검증

| 항목 | 중복 수 |
| --- | ---: |
| suggested_gene_symbol duplicate | 0 |
| auto_uniprot_id duplicate | 0 |
| uniprot_entry_name duplicate | 0 |
| uniprot_primary_gene duplicate | 0 |
| raw target -> multiple auto genes | 0 |

해석:

```text
uniprot_auto_mapping_candidates_v1.csv는 seed 후보로 변환하기 전에 중복 문제가 없다.
MET는 중복이 아니라 multi-hit 검토 상태다.
```

## Reviewed Seed 후보 중복 검증

`auto_mapping_status=auto_suggested`만 seed 후보로 본 경우:

| 항목 | 결과 |
| --- | ---: |
| reviewed seed rows | 27 |
| protein_id duplicate | 0 |
| reviewed gene duplicate | 0 |

예상 protein_id:

```text
protein_{uniprot_id_lower}
```

## 원천 후보 CSV 중복 검증

| file | 중복 기준 | 결과 |
| --- | --- | --- |
| target_mapping_candidates_v1.csv | normalized_target_text | 0 |
| target_priority_for_structure_v1.csv | target_text | 0 |
| target_mapping_parsed_tokens_v1.csv | parsed_token | 41 duplicated token groups |
| alias_resolution_review_v1.csv | raw_text | 6 duplicated raw_text groups |

## Parsed/Alias 중복 해석

`target_mapping_parsed_tokens_v1.csv`의 중복은 같은 gene/protein token이 여러 raw target text에서 반복된 것이다.

예:

```text
BCL2
PARP1
PARP2
AURKA
AURKB
AURKC
MAP2K1
MAP2K2
TOP2A
TOP2B
PIK3CG
```

이 중복은 삭제 대상이 아니다. 이유:

```text
같은 protein이 여러 약물/질환/원천 target에서 반복되는 provenance 정보이기 때문
```

단, DB seed 생성 시에는 아래 기준으로 dedupe해야 한다.

```text
protein_targets: uniprot_id 기준 1개
target_protein_links: raw target text + protein_id 기준
candidate_protein_structure_links: disease/candidate/evidence context 기준
```

## Alias 검토표 중복 해석

`alias_resolution_review_v1.csv`에서 반복된 raw_text:

```text
MTORC1
PROTEASOME
BCL-XL
TOP2
EPHRINS
PDGFR
```

이 값들은 여러 원문 target에서 반복 등장했기 때문에 검토표에 중복 provenance로 나타난다.

seed 생성 시에는 alias term 자체를 하나로 합치되, source raw text는 보존하는 것이 좋다.

## 보류 항목

```text
MET -> P08581
status: needs_review_multi_hit
hit_count: 2
```

MET는 중복 문제라기보다 UniProt query 결과가 2개인 multi-hit 이슈다. reviewed seed v1에서는 제외하거나 별도 보류 목록에 둔다.

## 다음 단계 판단

중복 검증 결과, 다음 단계로 넘어가도 된다.

권장:

```text
1. auto_suggested 27개만 reviewed seed 후보로 변환
2. MET는 hold/review list로 분리
3. protein_targets_seed_reviewed_v1.csv 생성
4. target_protein_links_seed_reviewed_v1.csv 생성
5. seed CSV 중복/FK 검증
```
