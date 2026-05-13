# Path Scoring 검증 리포트 v1

## 검증 대상

- API: `http://127.0.0.1:8010/graph/path-score`
- 질병: BRCA, Colon, HNSC, IPF, LUNG, Liver, PAH, PDAC, Psoriasis, RA, STAD
- 제외 질병: OV, SKCM

## 검증 항목

- 11개 질병 endpoint 200 응답
- `canonical_drug_id` 중복 여부
- `path_score`, `positive_score`, `risk_penalty` 범위 0~1 여부
- 각 score row의 `evidence_sources` 존재 여부
- `risk_sources` 반환 구조 확인

## 결과

- 전체 score row: 247
- 문제 발생 질병 수: 0
- CSV 요약: `path_score_summary_v1.csv`

## 비고

`path_score`는 최종 임상 판단 점수가 아니라, 내부 후보 rank, ADMET, image-modal evidence, target overlap을 합친 설명 가능한 기준 점수입니다. RAG/LLM 설명에서는 반드시 `evidence_sources`와 `risk_sources`를 함께 사용해야 합니다.
