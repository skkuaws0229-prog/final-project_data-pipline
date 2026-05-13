// ===== 제약조건 (Constraints) =====
CREATE CONSTRAINT drug_name IF NOT EXISTS
  FOR (d:Drug) REQUIRE d.name IS UNIQUE;

CREATE CONSTRAINT target_gene IF NOT EXISTS
  FOR (t:Target) REQUIRE t.gene_name IS UNIQUE;

CREATE CONSTRAINT disease_code IF NOT EXISTS
  FOR (dis:Disease) REQUIRE dis.code IS UNIQUE;

CREATE CONSTRAINT trial_nct IF NOT EXISTS
  FOR (tr:Trial) REQUIRE tr.nct_id IS UNIQUE;

CREATE CONSTRAINT hospital_id IF NOT EXISTS
  FOR (h:Hospital) REQUIRE h.hospital_id IS UNIQUE;

CREATE CONSTRAINT pathway_id IF NOT EXISTS
  FOR (p:Pathway) REQUIRE p.pathway_id IS UNIQUE;

CREATE CONSTRAINT sideeffect_name IF NOT EXISTS
  FOR (s:SideEffect) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT variant_id IF NOT EXISTS
  FOR (v:Variant) REQUIRE v.variant_id IS UNIQUE;

CREATE CONSTRAINT cellline_id IF NOT EXISTS
  FOR (c:CellLine) REQUIRE c.depmap_id IS UNIQUE;

// ===== 인덱스 (Indexes) =====
CREATE INDEX drug_disease IF NOT EXISTS
  FOR (d:Drug) ON (d.disease_code);

CREATE INDEX trial_status IF NOT EXISTS
  FOR (t:Trial) ON (t.status);

CREATE INDEX hospital_region IF NOT EXISTS
  FOR (h:Hospital) ON (h.region);
