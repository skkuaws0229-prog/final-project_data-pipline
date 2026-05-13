# KG Embedding API 검증 리포트 v1

## 검증 대상

- `/health/kg-embedding`: score_rows=1870
- `/graph/kg-embedding?model=ensemble` 11개 질병

## 검증 결과

- 문제 수: 0
- score 범위: 0~1
- 질병 내 duplicate canonical drug 없음

## 산출물

- kg_embedding_api_summary_v1.csv

## 해석 주의

KG embedding score는 학습 기반 보조 점수입니다. Path scoring처럼 source/risk를 설명하는 점수가 아니므로 단독 추천 근거로 사용하지 않습니다.
