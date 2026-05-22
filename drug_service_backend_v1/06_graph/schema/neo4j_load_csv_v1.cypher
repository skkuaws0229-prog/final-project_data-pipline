// Run after copying 06_graph/import/*.csv into Neo4j import directory.
// This script uses LOAD CSV so it works with Docker Compose Neo4j without neo4j-admin import.

LOAD CSV WITH HEADERS FROM 'file:///graph_diseases.csv' AS row
MERGE (d:Disease {disease_id: row.disease_id})
SET d.display_name = row.display_name,
    d.source_file = row.source_file,
    d.source_s3_key = row.source_s3_key;

LOAD CSV WITH HEADERS FROM 'file:///graph_drugs.csv' AS row
MERGE (d:Drug {canonical_drug_id: row.canonical_drug_id})
SET d.primary_drug_name = row.primary_drug_name,
    d.primary_smiles = row.primary_smiles,
    d.primary_source_drug_id = row.primary_source_drug_id,
    d.drug_source_status = row.drug_source_status;

LOAD CSV WITH HEADERS FROM 'file:///graph_drug_aliases.csv' AS row
MATCH (drug:Drug {canonical_drug_id: row.canonical_drug_id})
MERGE (a:DrugAlias {alias_id: row.alias_id})
SET a.canonical_drug_id = row.canonical_drug_id,
    a.source_drug_id = row.source_drug_id,
    a.alias_name = row.alias_name,
    a.normalized_alias = row.normalized_alias,
    a.alias_type = row.alias_type
MERGE (a)-[r:ALIAS_OF]->(drug)
SET r.alias_type = row.alias_type,
    r.source_drug_id = row.source_drug_id;

LOAD CSV WITH HEADERS FROM 'file:///graph_disease_aliases.csv' AS row
MATCH (disease:Disease {disease_id: row.disease_id})
MERGE (a:DiseaseAlias {alias_id: row.alias_id})
SET a.disease_id = row.disease_id,
    a.alias = row.alias,
    a.normalized_alias = row.normalized_alias
MERGE (a)-[:ALIAS_OF]->(disease);

LOAD CSV WITH HEADERS FROM 'file:///graph_target_concepts.csv' AS row
MERGE (t:TargetConcept {target_id: row.target_id})
SET t.concept_text = row.concept_text,
    t.normalized_text = row.normalized_text,
    t.concept_type = row.concept_type;

LOAD CSV WITH HEADERS FROM 'file:///graph_image_clusters.csv' AS row
MATCH (d:Disease {disease_id: row.disease_id})
MERGE (c:ImageCluster {cluster_id: row.cluster_id})
SET c.disease_id = row.disease_id,
    c.cluster_key = row.cluster_key,
    c.cluster_label = row.cluster_label,
    c.n_observations = CASE row.n_observations WHEN '' THEN NULL ELSE toInteger(row.n_observations) END,
    c.clinical_summary = row.clinical_summary,
    c.pathway_summary = row.pathway_summary,
    c.source_file = row.source_file
MERGE (d)-[r:HAS_IMAGE_CLUSTER]->(c)
SET r.source_file = row.source_file;

LOAD CSV WITH HEADERS FROM 'file:///graph_image_evidence.csv' AS row
MERGE (e:ImageEvidence {evidence_id: row.evidence_id})
SET e.disease_id = row.disease_id,
    e.cluster_id = row.cluster_id,
    e.drug_name = row.drug_name,
    e.rank = CASE row.rank WHEN '' THEN NULL ELSE toInteger(row.rank) END,
    e.tier = row.tier,
    e.target = row.target,
    e.target_pathway = row.target_pathway,
    e.evidence_text = row.evidence_text,
    e.source_file = row.source_file,
    e.match_status = row.match_status,
    e.canonical_drug_id = row.canonical_drug_id;

LOAD CSV WITH HEADERS FROM 'file:///graph_candidate_for_edges.csv' AS row
MATCH (drug:Drug {canonical_drug_id: row.canonical_drug_id})
MATCH (disease:Disease {disease_id: row.disease_id})
MERGE (drug)-[r:CANDIDATE_FOR {candidate_id: row.candidate_id}]->(disease)
SET r.rank = CASE row.rank WHEN '' THEN NULL ELSE toInteger(row.rank) END,
    r.tier = row.tier,
    r.score = row.score,
    r.evidence_summary = row.evidence_summary,
    r.safety_score = row.safety_score,
    r.verdict = row.verdict,
    r.admet_status = row.admet_status,
    r.hard_fail = row.hard_fail,
    r.hard_fail_reasons = row.hard_fail_reasons,
    r.soft_flags = row.soft_flags,
    r.source_file = row.source_file,
    r.source_row_number = CASE row.source_row_number WHEN '' THEN NULL ELSE toInteger(row.source_row_number) END;

LOAD CSV WITH HEADERS FROM 'file:///graph_candidate_target_edges.csv' AS row
MATCH (drug:Drug {canonical_drug_id: row.canonical_drug_id})
MATCH (target:TargetConcept {target_id: row.target_id})
MERGE (drug)-[r:HAS_TARGET {source_id: row.source_id, relation_kind: row.relation_kind}]->(target)
SET r.source_kind = row.source_kind,
    r.disease_id = row.disease_id;

LOAD CSV WITH HEADERS FROM 'file:///graph_cluster_evidence_edges.csv' AS row
MATCH (cluster:ImageCluster {cluster_id: row.cluster_id})
MATCH (evidence:ImageEvidence {evidence_id: row.evidence_id})
MERGE (cluster)-[r:HAS_IMAGE_EVIDENCE]->(evidence)
SET r.disease_id = row.disease_id,
    r.source_file = row.source_file;

LOAD CSV WITH HEADERS FROM 'file:///graph_evidence_drug_edges.csv' AS row
MATCH (evidence:ImageEvidence {evidence_id: row.evidence_id})
MATCH (drug:Drug {canonical_drug_id: row.canonical_drug_id})
MERGE (evidence)-[r:SUPPORTS_DRUG]->(drug)
SET r.match_status = row.match_status,
    r.drug_name = row.drug_name,
    r.rank = CASE row.rank WHEN '' THEN NULL ELSE toInteger(row.rank) END,
    r.tier = row.tier;

LOAD CSV WITH HEADERS FROM 'file:///graph_evidence_target_edges.csv' AS row
MATCH (evidence:ImageEvidence {evidence_id: row.evidence_id})
MATCH (target:TargetConcept {target_id: row.target_id})
MERGE (evidence)-[r:MENTIONS_TARGET {relation_kind: row.relation_kind}]->(target)
SET r.source_kind = row.source_kind,
    r.source_id = row.source_id,
    r.disease_id = row.disease_id;
