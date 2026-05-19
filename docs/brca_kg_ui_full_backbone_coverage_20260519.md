# BRCA KG UI full backbone coverage

## 배경

1차 BRCA UI graph 보강 후에도 일부 candidate drug만 `drug -> target/pathway` backbone을 가지고 있었다.

프론트 확인:

```text
drug node = 20
backbone 있음 = 9
backbone 없음 = 11
```

## 원인

남은 11개 약물은 `image_modal_drug_evidence`, `candidate_pool`, `drug_candidates`의 target/pathway 원천 컬럼이 비어 있었다.

따라서 DB 원천 edge만으로는 모든 drug에 backbone을 만들 수 없었다.

## 조치

연구자 UI graph 안정화를 위해 curated mechanism fallback을 추가했다.

적용 조건:

```text
drug node가 ui-basic graph에 존재
drug -> target/pathway backbone이 아직 없음
해당 drug_name이 curated fallback map에 있음
```

fallback edge metadata:

```text
source = curated_mechanism_fallback
provenance_note = Added only for UI backbone coverage when source target/pathway edges are missing.
```

이 metadata를 통해 원천 DB evidence edge와 UI 보강 edge를 구분할 수 있다.

## 검증 결과

검증일: 2026-05-19

```text
GET http://172.16.0.64:8010/api/graph/BRCA/ui-basic
-> 200
```

최종 BRCA 결과:

```text
nodes = 69
links = 89

node type:
disease = 1
drug = 20
target = 25
pathway = 19
cluster = 4

drug_count = 20
with_backbone = 20
missing = 0

link type:
cluster -> drug = 32
drug -> target = 19
target -> pathway = 18
drug -> disease = 15
disease -> cluster = 4
drug -> pathway = 1

curated_mechanism_fallback edges = 22
```

예시:

```text
Ruxolitinib
targets = ["JAK1/JAK2"]
pathways = ["JAK/STAT signaling"]
```

## 프론트 전달 사항

BRCA도 이제 20개 drug node 모두 최소 1개 이상 `drug -> target` 또는 `drug -> pathway` backbone을 가진다.

프론트는 기존 ForceGraph2D 렌더링 로직 그대로 사용하면 된다.

주의:

```text
source=curated_mechanism_fallback edge는 화면 backbone coverage를 위한 보강 edge다.
원천 evidence 기반 edge와 구분해서 tooltip 또는 detail panel에 표시할 수 있다.
```
