CREATE TABLE IF NOT EXISTS diseases (
  disease_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  source_file TEXT NOT NULL,
  source_s3_key TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drugs (
  drug_id TEXT PRIMARY KEY,
  drug_name TEXT NOT NULL,
  canonical_smiles TEXT,
  first_seen_disease_id TEXT REFERENCES diseases(disease_id)
);

CREATE TABLE IF NOT EXISTS drug_candidates (
  candidate_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  drug_id TEXT NOT NULL REFERENCES drugs(drug_id),
  rank INTEGER,
  tier TEXT,
  score TEXT,
  target TEXT,
  target_pathway TEXT,
  evidence_summary TEXT,
  source_file TEXT NOT NULL,
  source_row_number INTEGER NOT NULL,
  raw_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS admet_results (
  admet_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES drug_candidates(candidate_id),
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  drug_id TEXT NOT NULL REFERENCES drugs(drug_id),
  safety_score TEXT,
  verdict TEXT,
  admet_status TEXT,
  hard_fail TEXT,
  hard_fail_reasons TEXT,
  soft_flags TEXT,
  raw_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_drug_candidates_disease_rank
  ON drug_candidates(disease_id, rank);

CREATE INDEX IF NOT EXISTS idx_drug_candidates_drug
  ON drug_candidates(drug_id);

CREATE INDEX IF NOT EXISTS idx_drugs_name
  ON drugs(drug_name);

CREATE TABLE IF NOT EXISTS image_modal_sources (
  source_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  source_kind TEXT NOT NULL,
  local_file TEXT NOT NULL,
  source_s3_key TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS image_modal_clusters (
  cluster_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  cluster_key TEXT NOT NULL,
  cluster_label TEXT,
  n_observations INTEGER,
  clinical_summary TEXT,
  pathway_summary TEXT,
  source_file TEXT NOT NULL,
  raw_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS image_modal_cluster_members (
  member_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  cluster_id TEXT REFERENCES image_modal_clusters(cluster_id),
  patient_id TEXT,
  sample_id TEXT,
  slide_id TEXT,
  image_id TEXT,
  source_file TEXT NOT NULL,
  source_row_number INTEGER NOT NULL,
  raw_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS image_modal_drug_evidence (
  evidence_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  cluster_id TEXT REFERENCES image_modal_clusters(cluster_id),
  drug_id TEXT,
  drug_name TEXT,
  rank INTEGER,
  tier TEXT,
  target TEXT,
  target_pathway TEXT,
  evidence_text TEXT,
  source_file TEXT NOT NULL,
  source_row_number INTEGER NOT NULL,
  raw_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS image_modal_reports (
  report_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  source_id TEXT REFERENCES image_modal_sources(source_id),
  report_kind TEXT NOT NULL,
  title TEXT,
  report_text TEXT NOT NULL,
  source_file TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_image_modal_clusters_disease
  ON image_modal_clusters(disease_id);

CREATE INDEX IF NOT EXISTS idx_image_modal_members_disease_cluster
  ON image_modal_cluster_members(disease_id, cluster_id);

CREATE INDEX IF NOT EXISTS idx_image_modal_evidence_disease_cluster
  ON image_modal_drug_evidence(disease_id, cluster_id);

CREATE INDEX IF NOT EXISTS idx_image_modal_evidence_drug_name
  ON image_modal_drug_evidence(drug_name);

CREATE TABLE IF NOT EXISTS canonical_drugs (
  canonical_drug_id TEXT PRIMARY KEY,
  primary_drug_name TEXT NOT NULL,
  primary_smiles TEXT,
  primary_source_drug_id TEXT REFERENCES drugs(drug_id)
);

CREATE TABLE IF NOT EXISTS drug_aliases (
  alias_id TEXT PRIMARY KEY,
  canonical_drug_id TEXT NOT NULL REFERENCES canonical_drugs(canonical_drug_id),
  source_drug_id TEXT REFERENCES drugs(drug_id),
  alias_name TEXT NOT NULL,
  normalized_alias TEXT NOT NULL,
  alias_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS disease_aliases (
  alias_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  alias TEXT NOT NULL,
  normalized_alias TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS image_modal_evidence_drug_matches (
  evidence_id TEXT PRIMARY KEY REFERENCES image_modal_drug_evidence(evidence_id),
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  drug_name TEXT,
  normalized_drug_name TEXT,
  canonical_drug_id TEXT REFERENCES canonical_drugs(canonical_drug_id),
  match_status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_drug_aliases_normalized
  ON drug_aliases(normalized_alias);

CREATE INDEX IF NOT EXISTS idx_disease_aliases_normalized
  ON disease_aliases(normalized_alias);

CREATE INDEX IF NOT EXISTS idx_image_modal_matches_canonical
  ON image_modal_evidence_drug_matches(canonical_drug_id);
