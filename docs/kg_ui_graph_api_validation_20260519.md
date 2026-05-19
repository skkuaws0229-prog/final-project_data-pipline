# Knowledge Graph UI API validation

## 목적

프론트 연구자용 Knowledge Graph 화면은 raw pipeline graph가 아니라 아래 흐름 중심의 정제 그래프를 사용한다.

```text
Disease -> Candidate Drug -> Target/Gene/Protein -> Pathway
```

따라서 raw 운영 노드와 중간 evidence 노드는 화면에서 제외하거나 collapse한다.

## 추가 endpoint

### UI basic graph

```http
GET /api/graph/{disease}/ui-basic
```

응답:

```json
{
  "disease_id": "RA",
  "nodes": [],
  "links": []
}
```

노드 type은 화면용으로 정규화한다.

```text
disease
drug
target
gene
protein
pathway
cluster
```

현재 raw `ImageEvidence` 노드는 UI graph에서 제외하고, `cluster -> drug` link로 collapse한다.

### Graph summary

```http
GET /api/graph/{disease}/summary
```

응답 필드:

```text
node_count
edge_count
graph_status
has_tier
node_types
note
```

### Node detail

```http
GET /api/graph/{disease}/nodes/{node_id}
```

응답 필드:

```text
title
description
type
fields
relationships
```

### Node neighbors

```http
GET /api/graph/{disease}/neighbors/{node_id}
```

응답 필드:

```text
neighbors[].id
neighbors[].label
neighbors[].type
neighbors[].relationship
neighbors[].direction
```

### Image modal bundle

```http
GET /api/image-modal/{disease}
```

질환별 image-modal cluster/evidence/report bundle을 반환한다.

### Image modal file provenance URL

```http
GET /api/image-modal/{disease}/{file_name}/url
```

현재 원본 파일 직접 다운로드 URL이 아니라 DB 적재 provenance 기준의 file-level reference를 반환한다.

## Relationship label

화면용 label을 반환한다.

```text
CANDIDATE_FOR -> candidate drug for
HAS_TARGET -> targets / targets gene / targets protein / associated pathway
CLUSTER_SUPPORTS_DRUG -> cluster supports candidate
HAS_IMAGE_CLUSTER -> has image-modal cluster
```

## Drug node metadata

drug node metadata에는 가능한 경우 아래 값을 포함한다.

```text
rank
tier
score
verdict
admet_status
targets
pathways
```

## 검증 결과

검증일: 2026-05-19

LAN IP 기준:

```text
GET http://172.16.0.64:8010/api/graph/RA/summary
-> 200
node_count=39
edge_count=68
graph_status=ready
has_tier=true

GET http://172.16.0.64:8010/api/graph/RA/ui-basic
-> 200

GET http://172.16.0.64:8010/api/graph/RA/nodes/cdrug_6c95cca9e9b8fc23
-> 200
title=Ruxolitinib
type=drug

GET http://172.16.0.64:8010/api/graph/RA/neighbors/cdrug_6c95cca9e9b8fc23
-> 200

GET http://172.16.0.64:8010/api/image-modal/RA
-> 200

GET http://172.16.0.64:8010/api/image-modal/RA/RA_drug_linkage.csv/url
-> 200
```

## 주의

- `ui-basic`은 raw Neo4j graph를 그대로 노출하지 않는다.
- `ImageEvidence` 노드는 UI graph에서 제외하고 cluster-drug support link로 요약한다.
- `targets/pathways`는 원천 후보 컬럼과 UI graph 연결 target을 합쳐 가능한 범위에서 채운다.
- API 재빌드 후 `candidate_protein_structure_links=261` 확인이 필요하다.
