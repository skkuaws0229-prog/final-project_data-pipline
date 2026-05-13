# Drug Uniqueness 검증 리포트 v1

Generated at: 2026-05-13T08:32:35.878617+00:00

## 기준

- 같은 질병 안의 후보/결과/API 목록에서는 같은 `canonical_drug_id`가 중복 노출되면 안 됩니다.
- 같은 약물이 서로 다른 질병에 등장하는 것은 오류가 아니라 cross-disease 관계성 분석 대상입니다.
- image-modal evidence는 같은 약물이 여러 cluster 근거로 여러 번 등장할 수 있으므로 원본 근거 row는 보존합니다.

## 검증 결과

- API presentation duplicate count: 0
- Source candidate duplicate disease count: 3
- Cross-disease related drugs: 43

## 산출물

- drug_uniqueness_api_summary_v1.csv
- drug_uniqueness_source_duplicates_v1.csv
- cross_disease_drug_relations_v1.csv

## 해석

API presentation duplicate count는 반드시 0이어야 합니다. Source candidate duplicate는 canonicalization 또는 원천 후보 생성 단계에서 같은 질병 안에 같은 canonical drug가 여러 row로 들어온 경우이며, 이후 정규화 단계에서 우선순위 1개로 접거나 canonicalization key를 보강해야 합니다.
