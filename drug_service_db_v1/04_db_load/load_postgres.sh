#!/usr/bin/env bash
set -euo pipefail

DB_CONTAINER="${DB_CONTAINER:-drug-service-postgres}"
DB_NAME="${DB_NAME:-drug_service}"
DB_USER="${DB_USER:-drug_service}"

docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /schema/postgres_schema.sql

docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
TRUNCATE TABLE
  image_modal_evidence_drug_matches,
  drug_aliases,
  disease_aliases,
  canonical_drugs,
  image_modal_reports,
  image_modal_drug_evidence,
  image_modal_cluster_members,
  image_modal_clusters,
  image_modal_sources,
  admet_results,
  drug_candidates,
  drugs,
  diseases
RESTART IDENTITY CASCADE;

\copy diseases(disease_id, display_name, source_file, source_s3_key) FROM '/normalized/diseases.csv' WITH (FORMAT csv, HEADER true)
\copy drugs(drug_id, drug_name, canonical_smiles, first_seen_disease_id) FROM '/normalized/drugs.csv' WITH (FORMAT csv, HEADER true)
\copy drug_candidates(candidate_id, disease_id, drug_id, rank, tier, score, target, target_pathway, evidence_summary, source_file, source_row_number, raw_json) FROM '/normalized/drug_candidates.csv' WITH (FORMAT csv, HEADER true)
\copy admet_results(admet_id, candidate_id, disease_id, drug_id, safety_score, verdict, admet_status, hard_fail, hard_fail_reasons, soft_flags, raw_json) FROM '/normalized/admet_results.csv' WITH (FORMAT csv, HEADER true)
\copy image_modal_sources(source_id, disease_id, source_kind, local_file, source_s3_key) FROM '/normalized/image_modal_sources.csv' WITH (FORMAT csv, HEADER true)
\copy image_modal_clusters(cluster_id, disease_id, cluster_key, cluster_label, n_observations, clinical_summary, pathway_summary, source_file, raw_json) FROM '/normalized/image_modal_clusters.csv' WITH (FORMAT csv, HEADER true)
\copy image_modal_cluster_members(member_id, disease_id, cluster_id, patient_id, sample_id, slide_id, image_id, source_file, source_row_number, raw_json) FROM '/normalized/image_modal_cluster_members.csv' WITH (FORMAT csv, HEADER true)
\copy image_modal_drug_evidence(evidence_id, disease_id, cluster_id, drug_id, drug_name, rank, tier, target, target_pathway, evidence_text, source_file, source_row_number, raw_json) FROM '/normalized/image_modal_drug_evidence.csv' WITH (FORMAT csv, HEADER true)
\copy image_modal_reports(report_id, disease_id, source_id, report_kind, title, report_text, source_file) FROM '/normalized/image_modal_reports.csv' WITH (FORMAT csv, HEADER true)
\copy canonical_drugs(canonical_drug_id, primary_drug_name, primary_smiles, primary_source_drug_id) FROM '/normalized/canonical_drugs.csv' WITH (FORMAT csv, HEADER true)
\copy drug_aliases(alias_id, canonical_drug_id, source_drug_id, alias_name, normalized_alias, alias_type) FROM '/normalized/drug_aliases.csv' WITH (FORMAT csv, HEADER true)
\copy disease_aliases(alias_id, disease_id, alias, normalized_alias) FROM '/normalized/disease_aliases.csv' WITH (FORMAT csv, HEADER true)
\copy image_modal_evidence_drug_matches(evidence_id, disease_id, drug_name, normalized_drug_name, canonical_drug_id, match_status) FROM '/normalized/image_modal_evidence_drug_matches.csv' WITH (FORMAT csv, HEADER true)

SELECT 'diseases' AS table_name, COUNT(*) FROM diseases
UNION ALL
SELECT 'canonical_drugs', COUNT(*) FROM canonical_drugs
UNION ALL
SELECT 'drug_aliases', COUNT(*) FROM drug_aliases
UNION ALL
SELECT 'disease_aliases', COUNT(*) FROM disease_aliases
UNION ALL
SELECT 'drugs', COUNT(*) FROM drugs
UNION ALL
SELECT 'drug_candidates', COUNT(*) FROM drug_candidates
UNION ALL
SELECT 'admet_results', COUNT(*) FROM admet_results
UNION ALL
SELECT 'image_modal_sources', COUNT(*) FROM image_modal_sources
UNION ALL
SELECT 'image_modal_clusters', COUNT(*) FROM image_modal_clusters
UNION ALL
SELECT 'image_modal_cluster_members', COUNT(*) FROM image_modal_cluster_members
UNION ALL
SELECT 'image_modal_drug_evidence', COUNT(*) FROM image_modal_drug_evidence
UNION ALL
SELECT 'image_modal_reports', COUNT(*) FROM image_modal_reports
UNION ALL
SELECT 'image_modal_evidence_drug_matches', COUNT(*) FROM image_modal_evidence_drug_matches
ORDER BY table_name;
SQL
