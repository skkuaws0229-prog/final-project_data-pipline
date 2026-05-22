# Graph API 검증 리포트 v1

## 범위

FastAPI `/graph/relations` 응답을 기준으로 React v2 graph viewer에 넘겨도 되는지 검증했습니다.

검증 대상 질병:

```text
BRCA, Colon, HNSC, IPF, LUNG, Liver, PAH, PDAC, Psoriasis, RA, STAD
```

## Endpoint

```text
GET /graph/relations?disease_id={disease_id}&limit=200
```

응답 형태:

```json
{
  "disease_id": "RA",
  "nodes": [],
  "edges": []
}
```

## 검증 결과

```text
Duplicate node id: 0
Duplicate edge id: 0
Broken edge endpoint: 0
Missing candidate edge disease: 0
API issue rows: 0
Neo4j import CSV 대비 edge count mismatch: 0
```

## 질병별 API 응답 수

```text
BRCA       nodes 69   edges 143
Colon      nodes 90   edges 207
HNSC       nodes 153  edges 272
IPF        nodes 26   edges 56
LUNG       nodes 54   edges 101
Liver      nodes 51   edges 88
PAH        nodes 51   edges 95
PDAC       nodes 128  edges 329
Psoriasis  nodes 160  edges 328
RA         nodes 71   edges 132
STAD       nodes 103  edges 248
```

## 매칭/중복 검토 메모

- `Drug` node id는 `canonical_drug_id`를 사용합니다.
- `evidence_only` 약물도 `Drug` node로 포함합니다.
- 일반 후보 약물은 `Drug -> Disease` 방향의 `CANDIDATE_FOR` edge로 표시합니다.
- Image-modal 근거는 `Disease -> ImageCluster -> ImageEvidence -> Drug` 순서로 표시합니다.
- 약물 근거가 없는 빈 cluster도 `Disease -> ImageCluster`로 포함합니다.
- Candidate target은 `Drug -> TargetConcept`의 `HAS_TARGET` edge입니다.
- Image-modal target/pathway 언급은 `ImageEvidence -> TargetConcept`의 `MENTIONS_TARGET` edge입니다.
- `TargetConcept`는 아직 raw text입니다. gene/pathway/mechanism/free-text 분류는 v2 보강 대상입니다.

## 산출 파일

```text
06_graph/validation/graph_api_summary_v1.csv
06_graph/validation/graph_api_issues_v1.csv
```
