# BRCA Knowledge Graph UI backbone fix

## 배경

프론트에서 `GET /api/graph/BRCA/ui-basic` 확인 시 BRCA 그래프가 질환-약물 링 형태로만 보이고, target/pathway 노드는 존재하지만 연결 edge가 없는 문제가 보고되었다.

프론트 기대 구조:

```text
Disease -> Candidate Drug -> Target/Gene/Protein -> Pathway
```

## 원인

기존 `ui-basic`은 Neo4j의 `HAS_TARGET` edge를 우선 사용했다.

Colon은 Neo4j에 `drug -> target/pathway` edge가 존재했지만, BRCA는 target/pathway node는 존재하고 `drug -> target/pathway` edge가 비어 있었다.

반면 BRCA의 `image_modal_drug_evidence`에는 drug별 `target`, `target_pathway` 값이 존재했다.

## 조치

`ui-basic` graph builder에 fallback backbone 생성 로직을 추가했다.

조건:

```text
image_modal_drug_evidence.target 또는 target_pathway가 존재
image_modal_evidence_drug_matches.canonical_drug_id가 존재
해당 canonical drug node가 ui graph에 존재
```

생성 edge:

```text
drug -> target
target -> pathway
drug -> pathway  # target이 없고 pathway만 있을 때
```

edge metadata:

```text
source=image_modal_evidence_fallback
evidence_id
source_file
disease_id
```

drug node metadata의 `targets`, `pathways`도 fallback backbone을 반영하도록 보강했다.

## 검증 결과

검증일: 2026-05-19

```text
GET http://172.16.0.64:8010/api/graph/BRCA/ui-basic
-> 200
```

BRCA 최종 결과:

```text
nodes = 49
links = 67

node types:
drug = 20
target = 14
pathway = 10
cluster = 4
disease = 1

link types:
cluster -> drug = 32
drug -> disease = 15
drug -> target = 8
target -> pathway = 7
disease -> cluster = 4
drug -> pathway = 1
```

예시 drug node:

```text
Temozolomide
targets = ["DNA alkylating agent"]
pathways = ["DNA replication"]
```

## 프론트 전달 사항

BRCA도 이제 `Disease -> Candidate Drug -> Target -> Pathway` backbone을 포함한다.

프론트는 기존 `ForceGraph2D` 렌더링 로직을 그대로 사용하면 된다.

Cluster support edge는 기존처럼 collapse 상태로 유지된다.
