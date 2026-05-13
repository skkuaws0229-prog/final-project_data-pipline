# Drug Service 검증 리포트 v2

생성 시각: 2026-05-13T01:56:26.839380+00:00

## 요약

- Colon/IPF/PAH의 Markdown image-modal linkage를 structured evidence row로 parsing했습니다.
- 기존에 unmatched였던 image-modal drug는 `evidence_only` canonical drug로 보존했습니다.
- Target normalization은 Neo4j/OpenSearch 단계로 명시적으로 defer했습니다.

## 주요 Count

- image_modal_drug_evidence: 430
- image_modal_evidence_drug_matches: 430
- canonical_drugs: 170
- matched evidence rows: 403
- evidence_only rows: 27

## 질병별 Evidence 수

- BRCA: 32
- Colon: 40
- HNSC: 60
- IPF: 8
- Liver: 10
- LUNG: 18
- PAH: 11
- PDAC: 60
- Psoriasis: 120
- RA: 32
- STAD: 39

## 이후 단계로 미룬 항목

- `target_raw`, `target_type`, extracted canonical gene/pathway/mechanism token 구조로 target canonicalization을 구축합니다.
- Neo4j에서 Drug-Gene/Protein-Pathway-Disease graph relationship을 구성합니다.
- OpenSearch/RAG에서 free-text mechanism과 report retrieval을 처리합니다.

## 산출물

- validation_counts_v2.csv
- image_modal_evidence_by_disease_v2.csv
- image_modal_match_status_v2.csv
- evidence_only_drugs_v2.csv
- target_profile_v2.csv
- validation_checks_v2.csv
- api_smoke_test_v2.json
