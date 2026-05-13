# Drug Service Validation Report v2

Generated at: 2026-05-13T08:44:39.592487+00:00

## Summary

- Markdown image-modal linkage for Colon/IPF/PAH was parsed into structured evidence rows.
- Previously unmatched image-modal drugs are now preserved as `evidence_only` canonical drugs.
- Target normalization is explicitly deferred to the Neo4j/OpenSearch phase.

## Key Counts

- image_modal_drug_evidence: 430
- image_modal_evidence_drug_matches: 430
- canonical_drugs: 170
- matched evidence rows: 403
- evidence_only rows: 27

## Evidence By Disease

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

## Deferred To Later Phase

- Build target canonicalization as `target_raw`, `target_type`, and extracted canonical gene/pathway/mechanism tokens.
- Use Neo4j for Drug-Gene/Protein-Pathway-Disease graph relationships.
- Use OpenSearch/RAG for free-text mechanism and report retrieval.

## Artifacts

- validation_counts_v2.csv
- image_modal_evidence_by_disease_v2.csv
- image_modal_match_status_v2.csv
- evidence_only_drugs_v2.csv
- target_profile_v2.csv
- validation_checks_v2.csv
- api_smoke_test_v2.json
