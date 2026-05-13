# Drug Service 검증 리포트 v1

생성 시각: 2026-05-13T01:46:39.997400+00:00

## 요약

- 전체 checks: 27
- Pass: 24
- Warn: 3
- Fail: 0

## 주요 Count

- admet_results: 255
- canonical_drugs: 160
- disease_aliases: 31
- diseases: 11
- drug_aliases: 171
- drug_candidates: 255
- drugs: 171
- image_modal_cluster_members: 1694
- image_modal_clusters: 31
- image_modal_drug_evidence: 371
- image_modal_reports: 14
- image_modal_sources: 33

## v1 경고 사항

- Colon, IPF, PAH의 image-modal drug linkage는 주로 Markdown report 안에 있어 structured evidence row가 아직 충분히 추출되지 않았습니다.
- image-modal evidence 약물 중 매칭되지 않은 unique name이 6개 있었습니다.
- Target term에는 gene, pathway, mechanism, free-text target axis가 섞여 있습니다. 다음 graph/search 단계에서는 원본 target text와 canonical token을 함께 관리해야 합니다.
- 일부 image-modal cluster label이 비어 있으므로 화면에서는 `cluster_key` fallback이 필요합니다.

## 산출물

- validation_counts_v1.csv
- api_disease_counts_v1.csv
- unresolved_aliases_v1.csv
- cross_disease_canonical_drugs_v1.csv
- target_profile_v1.csv
- cluster_profile_v1.csv
- validation_checks_v1.csv
- api_smoke_test_v1.json
