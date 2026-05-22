CREATE CONSTRAINT disease_id_unique IF NOT EXISTS
FOR (n:Disease) REQUIRE n.disease_id IS UNIQUE;

CREATE CONSTRAINT drug_id_unique IF NOT EXISTS
FOR (n:Drug) REQUIRE n.canonical_drug_id IS UNIQUE;

CREATE CONSTRAINT drug_alias_id_unique IF NOT EXISTS
FOR (n:DrugAlias) REQUIRE n.alias_id IS UNIQUE;

CREATE CONSTRAINT disease_alias_id_unique IF NOT EXISTS
FOR (n:DiseaseAlias) REQUIRE n.alias_id IS UNIQUE;

CREATE CONSTRAINT target_id_unique IF NOT EXISTS
FOR (n:TargetConcept) REQUIRE n.target_id IS UNIQUE;

CREATE CONSTRAINT image_cluster_id_unique IF NOT EXISTS
FOR (n:ImageCluster) REQUIRE n.cluster_id IS UNIQUE;

CREATE CONSTRAINT image_evidence_id_unique IF NOT EXISTS
FOR (n:ImageEvidence) REQUIRE n.evidence_id IS UNIQUE;

CREATE INDEX disease_display_name IF NOT EXISTS
FOR (n:Disease) ON (n.display_name);

CREATE INDEX drug_primary_name IF NOT EXISTS
FOR (n:Drug) ON (n.primary_drug_name);

CREATE INDEX drug_alias_normalized IF NOT EXISTS
FOR (n:DrugAlias) ON (n.normalized_alias);

CREATE INDEX disease_alias_normalized IF NOT EXISTS
FOR (n:DiseaseAlias) ON (n.normalized_alias);

CREATE INDEX target_normalized_text IF NOT EXISTS
FOR (n:TargetConcept) ON (n.normalized_text);

CREATE INDEX image_evidence_disease IF NOT EXISTS
FOR (n:ImageEvidence) ON (n.disease_id);
