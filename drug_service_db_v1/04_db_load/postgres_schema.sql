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

CREATE TABLE IF NOT EXISTS protein_targets (
  protein_id TEXT PRIMARY KEY,
  gene_symbol TEXT,
  uniprot_id TEXT UNIQUE,
  protein_name TEXT,
  organism TEXT NOT NULL DEFAULT 'Homo sapiens',
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_protein_targets_gene_symbol
  ON protein_targets(gene_symbol);

CREATE TABLE IF NOT EXISTS target_protein_links (
  link_id TEXT PRIMARY KEY,
  target_text TEXT NOT NULL,
  normalized_target_text TEXT NOT NULL,
  protein_id TEXT REFERENCES protein_targets(protein_id),
  mapping_status TEXT NOT NULL CHECK (mapping_status IN ('exact', 'alias', 'manual', 'unresolved', 'rejected')),
  confidence NUMERIC,
  source TEXT NOT NULL,
  raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_target_protein_links_normalized
  ON target_protein_links(normalized_target_text);

CREATE INDEX IF NOT EXISTS idx_target_protein_links_protein
  ON target_protein_links(protein_id);

CREATE TABLE IF NOT EXISTS alphafold_structures (
  structure_id TEXT PRIMARY KEY,
  protein_id TEXT NOT NULL REFERENCES protein_targets(protein_id),
  provider TEXT NOT NULL CHECK (provider IN ('alphafold_db', 'pdb', 'local', 'predicted')),
  provider_accession TEXT,
  version TEXT,
  file_format TEXT NOT NULL CHECK (file_format IN ('pdb', 'mmcif', 'cif')),
  structure_uri TEXT NOT NULL,
  structure_source_uri TEXT,
  file_size_bytes BIGINT,
  checksum_sha256 TEXT,
  source_url TEXT,
  pae_uri TEXT,
  mean_plddt NUMERIC,
  confidence_summary TEXT,
  license TEXT,
  status TEXT NOT NULL CHECK (status IN ('available', 'to_fetch', 'missing', 'failed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alphafold_structures_protein
  ON alphafold_structures(protein_id);

CREATE TABLE IF NOT EXISTS candidate_protein_structure_links (
  context_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  candidate_id TEXT REFERENCES drug_candidates(candidate_id),
  canonical_drug_id TEXT REFERENCES canonical_drugs(canonical_drug_id),
  evidence_id TEXT REFERENCES image_modal_drug_evidence(evidence_id),
  protein_id TEXT NOT NULL REFERENCES protein_targets(protein_id),
  structure_id TEXT REFERENCES alphafold_structures(structure_id),
  target_source TEXT NOT NULL CHECK (target_source IN ('candidate_target', 'image_evidence', 'kg_target', 'manual')),
  relation_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_candidate_structure_links_disease
  ON candidate_protein_structure_links(disease_id);

CREATE INDEX IF NOT EXISTS idx_candidate_structure_links_candidate
  ON candidate_protein_structure_links(candidate_id);

CREATE INDEX IF NOT EXISTS idx_candidate_structure_links_canonical
  ON candidate_protein_structure_links(canonical_drug_id);

CREATE INDEX IF NOT EXISTS idx_candidate_structure_links_protein
  ON candidate_protein_structure_links(protein_id);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  disease_name TEXT NOT NULL,
  disease_slug TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('basic', 'image_modal', 'full')),
  execution_backend TEXT NOT NULL CHECK (execution_backend IN ('local_agent', 'aws_stepfunctions', 'mock')),
  status TEXT NOT NULL CHECK (status IN ('queued', 'preflight', 'running', 'waiting_external_job', 'validating', 'completed', 'failed', 'cancelled', 'blocked')),
  current_step TEXT,
  requested_by TEXT,
  s3_output_prefix TEXT,
  config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  random_seed INTEGER,
  verdict TEXT,
  error_message TEXT,
  estimated_cost_usd NUMERIC,
  estimated_time_minutes INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_disease_status
  ON pipeline_runs(disease_slug, status);

CREATE TABLE IF NOT EXISTS pipeline_run_events (
  event_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  level TEXT NOT NULL CHECK (level IN ('info', 'warning', 'error', 'debug')),
  step TEXT,
  message TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_pipeline_run_events_run_time
  ON pipeline_run_events(run_id, timestamp);

CREATE TABLE IF NOT EXISTS pipeline_artifacts (
  artifact_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
  artifact_type TEXT NOT NULL CHECK (artifact_type IN ('report', 'csv', 'json', 'plot', 'model_summary', 's3_prefix', 'log', 'validation')),
  step TEXT,
  name TEXT NOT NULL,
  uri TEXT NOT NULL,
  size_bytes BIGINT,
  checksum TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_run
  ON pipeline_artifacts(run_id);

CREATE TABLE IF NOT EXISTS pipeline_configs (
  config_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
  disease_name TEXT NOT NULL,
  disease_slug TEXT NOT NULL,
  config_yaml TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_configs_run
  ON pipeline_configs(run_id);
