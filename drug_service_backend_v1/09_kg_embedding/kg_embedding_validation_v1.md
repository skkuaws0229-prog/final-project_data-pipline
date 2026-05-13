# KG Embedding 검증 리포트 v1

Generated at: 2026-05-13T09:01:16.036897+00:00

## 학습 설정

- Seed: 20260513
- Triples: 1875
- Entities: 775
- Relations: 6
- Models: DistMult, TransE

## 산출물

- kg_embedding_scores_v1.csv rows: 1870
- known candidate score rows: 247

## 해석

KG embedding score는 graph 구조를 학습한 보조 점수입니다. 최종 추천 근거로 단독 사용하지 않고 path_score, ADMET, image-modal evidence, OpenSearch/RAG 근거와 함께 사용해야 합니다.
