# Neo4j Path Scoring v1

이 폴더는 `Neo4j path scoring v1` 구현/검증 자료입니다.

## 목적

TxGNN을 v1/v2 구현 범위에서 제외한 대신, 현재 Neo4j에 적재된 내부 그래프 근거를 이용해 설명 가능한 약물-질병 기준 점수를 생성합니다.

## API

```text
GET /graph/path-score?disease_id=RA&limit=100
```

응답은 프론트엔드와 RAG/LLM 설명에서 바로 재사용하기 쉽도록 근거 source와 risk source를 함께 반환합니다.

```json
{
  "disease_id": "RA",
  "scoring_version": "path_scoring_v1",
  "scores": []
}
```

## 점수 구성

```text
positive_score =
  candidate_rank   최대 0.30
  ADMET            최대 0.20
  image evidence   최대 0.25
  target overlap   최대 0.15

path_score = positive_score - risk_penalty
```

`risk_penalty`는 ADMET hard fail, verdict/status 미통과, soft flag를 기준으로 계산합니다.

## 중요한 설계 기준

- `limit`은 반환 개수만 제어합니다.
- rank 정규화 기준은 해당 질병의 전체 candidate rank max를 사용합니다.
- 모든 점수 row는 `evidence_sources`와 `risk_sources`를 함께 반환합니다.
- RAG/LLM은 점수만 보지 않고 source와 risk를 함께 설명해야 합니다.

## 검증 파일

```text
validate_path_score_v1.py
path_score_summary_v1.csv
path_score_validation_v1.md
```

