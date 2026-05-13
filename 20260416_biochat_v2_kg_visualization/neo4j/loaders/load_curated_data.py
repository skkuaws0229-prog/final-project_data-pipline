"""
S3 curated_date → Neo4j 적재 로더

사용법:
  python load_curated_data.py                  # 전체 적재
  python load_curated_data.py --source drugbank chembl  # 특정 소스만
"""

import argparse
import io
import os
from pathlib import Path

import boto3
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")
BUCKET = os.getenv("AWS_BUCKET", "say2-4team")

PREFIX = "curated_date"

s3 = boto3.client("s3")


# ── helpers ──────────────────────────────────────────────────────────
def read_parquet(key: str, columns: list[str] | None = None) -> pd.DataFrame:
    """S3에서 parquet 읽기 (읽기 전용)"""
    print(f"    S3 읽기: s3://{BUCKET}/{key}")
    resp = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()), columns=columns)
    print(f"    → {len(df):,} rows x {len(df.columns)} cols")
    return df


def batch_run(session, query: str, rows: list[dict], batch_size: int = 500):
    """UNWIND 배치 적재"""
    total = len(rows)
    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        session.run(query, rows=batch)
    return total


# ── 1. DrugBank ──────────────────────────────────────────────────────
def load_drugbank(driver):
    print("\n" + "=" * 60)
    print("  [1/7] DrugBank")
    print("=" * 60)

    df = read_parquet(
        f"{PREFIX}/drugbank/drugbank_drug_master_basic_20260406.parquet",
        columns=["drugbank_id", "name", "smiles", "inchi", "inchikey",
                 "molecular_formula", "molecular_weight", "drug_type"],
    )
    # NaN → None
    df = df.where(df.notna(), None)

    rows = df.to_dict("records")

    query = """
    UNWIND $rows AS r
    MERGE (d:Drug {name: r.name})
    SET d.drugbank_id        = r.drugbank_id,
        d.smiles             = r.smiles,
        d.inchi              = r.inchi,
        d.inchikey           = r.inchikey,
        d.molecular_formula  = r.molecular_formula,
        d.molecular_weight   = r.molecular_weight,
        d.drug_type          = r.drug_type
    """

    with driver.session(database=DATABASE) as session:
        cnt = batch_run(session, query, rows)
        result = session.run(
            "MATCH (d:Drug) WHERE d.drugbank_id IS NOT NULL RETURN count(d) AS cnt"
        ).single()
        print(f"  ✓ Drug 노드 MERGE(drugbank_id 부여): {result['cnt']:,}개")


# ── 2. ChEMBL ────────────────────────────────────────────────────────
def load_chembl(driver):
    print("\n" + "=" * 60)
    print("  [2/7] ChEMBL")
    print("=" * 60)

    # 2-a) drug_mechanism → Drug-TARGETS->Target 매핑에 사용
    df_mech = read_parquet(
        f"{PREFIX}/chembl/chembl_drug_mechanism_basic_20260406.parquet",
        columns=["molregno", "tid", "mechanism_of_action", "action_type"],
    )

    # 2-b) target_master
    df_target = read_parquet(
        f"{PREFIX}/chembl/chembl_target_master_basic_20260406.parquet",
        columns=["tid", "chembl_id", "pref_name", "target_type", "organism"],
    )
    # 사람 타겟만
    df_target = df_target[df_target["organism"] == "Homo sapiens"].copy()

    # 2-c) uniprot-target mapping (gene_name 확보)
    df_uniprot = read_parquet(
        f"{PREFIX}/chembl/chembl_uniprot_target_mapping_basic_20260406.parquet",
        columns=["uniprot_id", "target_chembl_id", "target_name"],
    )

    # tid → chembl_id 매핑
    tid_to_chembl = dict(zip(df_target["tid"], df_target["chembl_id"]))
    tid_to_name = dict(zip(df_target["tid"], df_target["pref_name"]))

    # Target 노드 생성 (chembl_id 기준)
    target_rows = []
    for _, row in df_target.iterrows():
        target_rows.append({
            "chembl_target_id": row["chembl_id"],
            "pref_name": row["pref_name"],
            "target_type": row["target_type"],
        })

    # uniprot 매핑으로 gene_name 보강 (target_chembl_id 기준)
    chembl_to_uniprot = {}
    for _, row in df_uniprot.iterrows():
        chembl_to_uniprot[row["target_chembl_id"]] = row["uniprot_id"]

    with driver.session(database=DATABASE) as session:
        # Target 노드 MERGE (gene_name = pref_name 으로 사용)
        q_target = """
        UNWIND $rows AS r
        MERGE (t:Target {gene_name: r.pref_name})
        SET t.chembl_target_id = r.chembl_target_id,
            t.target_type      = r.target_type
        """
        cnt_t = batch_run(session, q_target, target_rows)
        print(f"  ✓ Target 노드 MERGE: {cnt_t:,}개 (Homo sapiens)")

        # uniprot_id 추가
        uniprot_rows = [
            {"chembl_target_id": cid, "uniprot_id": uid}
            for cid, uid in chembl_to_uniprot.items()
        ]
        q_uniprot = """
        UNWIND $rows AS r
        MATCH (t:Target {chembl_target_id: r.chembl_target_id})
        SET t.uniprot_id = r.uniprot_id
        """
        batch_run(session, q_uniprot, uniprot_rows)

        # Drug-TARGETS->Target 엣지 (기존 Drug 노드 13개 + mechanism)
        # molregno → Drug name 매핑은 compound_master(435MB)에 있어서 직접 조인 불가
        # 대신 mechanism의 tid로 Target 매칭, 기존 Drug.target 속성으로 매칭
        mech_edges = []
        for _, row in df_mech.iterrows():
            tid = row["tid"]
            target_name = tid_to_name.get(tid)
            if target_name:
                mech_edges.append({
                    "target_name": target_name,
                    "mechanism": row["mechanism_of_action"],
                    "action_type": str(row["action_type"]) if pd.notna(row["action_type"]) else None,
                })

        # 기존 Drug.target과 Target.gene_name 매칭으로 TARGETS 엣지 생성
        q_edge = """
        MATCH (d:Drug)
        WHERE d.target IS NOT NULL
        MATCH (t:Target {gene_name: d.target})
        MERGE (d)-[r:TARGETS]->(t)
        SET r.source = 'drug_yaml_target'
        RETURN count(r) AS cnt
        """
        edge_cnt = session.run(q_edge).single()["cnt"]
        print(f"  ✓ Drug-TARGETS->Target 엣지 (직접 매칭): {edge_cnt}개")

        result = session.run("MATCH (t:Target) RETURN count(t) AS cnt").single()
        print(f"  ✓ Target 노드 전체: {result['cnt']:,}개")


# ── 3. GDSC ──────────────────────────────────────────────────────────
def load_gdsc(driver):
    print("\n" + "=" * 60)
    print("  [3/7] GDSC")
    print("=" * 60)

    # 기존 Drug 이름 가져오기
    with driver.session(database=DATABASE) as session:
        drug_names = {
            r["name"]
            for r in session.run("MATCH (d:Drug) RETURN d.name AS name").data()
        }
    print(f"    기존 Drug 노드: {len(drug_names)}개 → GDSC 필터링 기준")

    df = read_parquet(
        f"{PREFIX}/gsdc/gdsc2_basic_clean_20260406.parquet",
        columns=["DRUG_NAME", "DRUG_ID", "CELL_LINE_NAME", "SANGER_MODEL_ID",
                 "TCGA_DESC", "LN_IC50", "AUC", "Z_SCORE"],
    )

    # 기존 Drug 노드에 있는 약물만 필터
    df = df[df["DRUG_NAME"].isin(drug_names)].copy()
    print(f"    필터링 후: {len(df):,} rows ({df['DRUG_NAME'].nunique()} drugs, {df['CELL_LINE_NAME'].nunique()} cell lines)")

    df = df.where(df.notna(), None)

    # Drug 노드에 gdsc_id 추가
    drug_ids = df.drop_duplicates("DRUG_NAME")[["DRUG_NAME", "DRUG_ID"]].to_dict("records")
    with driver.session(database=DATABASE) as session:
        q_drug = """
        UNWIND $rows AS r
        MATCH (d:Drug {name: r.DRUG_NAME})
        SET d.gdsc_id = r.DRUG_ID
        """
        batch_run(session, q_drug, drug_ids)

    # CellLine 노드 생성
    cl = df.drop_duplicates("SANGER_MODEL_ID")[
        ["SANGER_MODEL_ID", "CELL_LINE_NAME", "TCGA_DESC"]
    ].to_dict("records")

    with driver.session(database=DATABASE) as session:
        q_cl = """
        UNWIND $rows AS r
        MERGE (c:CellLine {depmap_id: r.SANGER_MODEL_ID})
        SET c.name   = r.CELL_LINE_NAME,
            c.tissue = r.TCGA_DESC
        """
        batch_run(session, q_cl, cl)
        print(f"  ✓ CellLine 노드 MERGE: {len(cl):,}개")

    # Drug-TESTED_IN->CellLine 엣지
    edges = df[["DRUG_NAME", "SANGER_MODEL_ID", "LN_IC50", "AUC", "Z_SCORE"]].to_dict("records")

    with driver.session(database=DATABASE) as session:
        q_edge = """
        UNWIND $rows AS r
        MATCH (d:Drug {name: r.DRUG_NAME})
        MATCH (c:CellLine {depmap_id: r.SANGER_MODEL_ID})
        MERGE (d)-[rel:TESTED_IN {depmap_id: r.SANGER_MODEL_ID}]->(c)
        SET rel.ln_ic50 = r.LN_IC50,
            rel.auc     = r.AUC,
            rel.z_score = r.Z_SCORE
        """
        cnt = batch_run(session, q_edge, edges)
        print(f"  ✓ Drug-TESTED_IN->CellLine 엣지: {cnt:,}개")


# ── 4. STRING ────────────────────────────────────────────────────────
def load_string(driver):
    print("\n" + "=" * 60)
    print("  [4/7] STRING PPI")
    print("=" * 60)

    # protein_info로 ENSP → gene_name 매핑
    df_info = read_parquet(
        f"{PREFIX}/string/string_protein_info_basic_20260406.parquet",
        columns=["string_protein_id", "preferred_name"],
    )
    ensp_to_gene = dict(zip(df_info["string_protein_id"], df_info["preferred_name"]))

    # 기존 Target gene_name 목록 가져오기
    with driver.session(database=DATABASE) as session:
        existing_genes = {
            r["g"]
            for r in session.run("MATCH (t:Target) RETURN t.gene_name AS g").data()
        }
    print(f"    기존 Target 노드: {len(existing_genes):,}개")

    # links 읽기 → score >= 700 필터
    df_links = read_parquet(
        f"{PREFIX}/string/string_links_basic_20260406.parquet",
    )
    df_links = df_links[df_links["combined_score"] >= 700].copy()
    print(f"    score >= 700 필터 후: {len(df_links):,} edges")

    # gene name 매핑
    df_links["gene1"] = df_links["protein1"].map(ensp_to_gene)
    df_links["gene2"] = df_links["protein2"].map(ensp_to_gene)
    df_links = df_links.dropna(subset=["gene1", "gene2"])

    # 양쪽 모두 기존 Target에 있는 것만
    df_links = df_links[
        df_links["gene1"].isin(existing_genes) & df_links["gene2"].isin(existing_genes)
    ].copy()
    print(f"    기존 Target 매칭 후: {len(df_links):,} edges")

    if len(df_links) == 0:
        print("  ⚠ 매칭되는 PPI 엣지 없음 (건너뜀)")
        return

    edges = df_links[["gene1", "gene2", "combined_score"]].to_dict("records")

    with driver.session(database=DATABASE) as session:
        q = """
        UNWIND $rows AS r
        MATCH (t1:Target {gene_name: r.gene1})
        MATCH (t2:Target {gene_name: r.gene2})
        MERGE (t1)-[rel:INTERACTS_WITH]->(t2)
        SET rel.score  = r.combined_score,
            rel.source = 'STRING'
        """
        cnt = batch_run(session, q, edges)
        print(f"  ✓ Target-INTERACTS_WITH->Target 엣지: {cnt:,}개")


# ── 5. OpenTargets ───────────────────────────────────────────────────
def load_opentargets(driver):
    print("\n" + "=" * 60)
    print("  [5/7] OpenTargets")
    print("=" * 60)

    # disease
    df_dis = read_parquet(
        f"{PREFIX}/opentargets/opentargets_disease_basic_20260406.parquet",
        columns=["id", "name", "code"],
    )

    # BRCA 관련 disease 찾기
    brca_diseases = df_dis[
        df_dis["name"].str.contains("breast", case=False, na=False)
    ].copy()
    print(f"    breast 관련 disease: {len(brca_diseases)}개")

    # Disease 노드에 efo_id 추가 (BRCA)
    with driver.session(database=DATABASE) as session:
        for _, row in brca_diseases.head(5).iterrows():
            session.run(
                """
                MATCH (dis:Disease {code: 'BRCA'})
                SET dis.efo_ids = coalesce(dis.efo_ids, []) + $efo_id
                """,
                efo_id=row["id"],
            )

    brca_disease_ids = set(brca_diseases["id"].tolist())

    # association (score >= 0.5)
    df_assoc = read_parquet(
        f"{PREFIX}/opentargets/opentargets_association_overall_direct_basic_20260406.parquet",
    )
    df_assoc = df_assoc[df_assoc["score"] >= 0.5].copy()
    print(f"    score >= 0.5: {len(df_assoc):,} associations")

    # breast cancer 관련만
    df_assoc = df_assoc[df_assoc["diseaseId"].isin(brca_disease_ids)].copy()
    print(f"    BRCA 질환 필터: {len(df_assoc):,} associations")

    # target (gene symbol 매핑용)
    df_tgt = read_parquet(
        f"{PREFIX}/opentargets/opentargets_target_basic_20260406.parquet",
        columns=["id", "approvedSymbol", "approvedName"],
    )
    ensembl_to_symbol = dict(zip(df_tgt["id"], df_tgt["approvedSymbol"]))

    df_assoc["gene_name"] = df_assoc["targetId"].map(ensembl_to_symbol)
    df_assoc = df_assoc.dropna(subset=["gene_name"])

    # 기존 Target에 있는 것만
    with driver.session(database=DATABASE) as session:
        existing_genes = {
            r["g"]
            for r in session.run("MATCH (t:Target) RETURN t.gene_name AS g").data()
        }

    df_assoc_matched = df_assoc[df_assoc["gene_name"].isin(existing_genes)].copy()
    print(f"    기존 Target 매칭: {len(df_assoc_matched):,} associations")

    if len(df_assoc_matched) == 0:
        print("  ⚠ 매칭되는 association 없음 (건너뜀)")
        return

    edges = df_assoc_matched[["gene_name", "score", "evidenceCount"]].to_dict("records")

    with driver.session(database=DATABASE) as session:
        q = """
        UNWIND $rows AS r
        MATCH (t:Target {gene_name: r.gene_name})
        MATCH (dis:Disease {code: 'BRCA'})
        MERGE (t)-[rel:ASSOCIATED_WITH]->(dis)
        SET rel.score          = r.score,
            rel.evidence_count = r.evidenceCount,
            rel.source         = 'OpenTargets'
        """
        cnt = batch_run(session, q, edges)
        print(f"  ✓ Target-ASSOCIATED_WITH->Disease 엣지: {cnt:,}개")


# ── 6. MSigDB ────────────────────────────────────────────────────────
def load_msigdb(driver):
    print("\n" + "=" * 60)
    print("  [6/7] MSigDB Pathways")
    print("=" * 60)

    df_master = read_parquet(
        f"{PREFIX}/msigdb/msigdb_gene_set_master_basic_20260406.parquet",
        columns=["gene_set_name", "collection_code", "description", "gene_count"],
    )

    df_member = read_parquet(
        f"{PREFIX}/msigdb/msigdb_gene_set_membership_basic_20260406.parquet",
        columns=["gene_set_name", "gene_symbol", "collection_code"],
    )

    # 기존 Target gene_name 목록
    with driver.session(database=DATABASE) as session:
        existing_genes = {
            r["g"]
            for r in session.run("MATCH (t:Target) RETURN t.gene_name AS g").data()
        }
    print(f"    기존 Target 노드: {len(existing_genes):,}개")

    # 기존 Target에 있는 유전자만 필터
    df_member = df_member[df_member["gene_symbol"].isin(existing_genes)].copy()
    print(f"    기존 Target 매칭 멤버십: {len(df_member):,}개")

    if len(df_member) == 0:
        print("  ⚠ 매칭 없음 (건너뜀)")
        return

    # 매칭된 gene set만 Pathway 노드 생성
    matched_sets = set(df_member["gene_set_name"])
    df_master = df_master[df_master["gene_set_name"].isin(matched_sets)].copy()

    pathway_rows = []
    for _, row in df_master.iterrows():
        pathway_rows.append({
            "pathway_id": row["gene_set_name"],
            "name": row["gene_set_name"],
            "collection": row["collection_code"],
            "gene_count": int(row["gene_count"]),
        })

    with driver.session(database=DATABASE) as session:
        q_path = """
        UNWIND $rows AS r
        MERGE (p:Pathway {pathway_id: r.pathway_id})
        SET p.name       = r.name,
            p.collection = r.collection,
            p.gene_count = r.gene_count
        """
        batch_run(session, q_path, pathway_rows)
        print(f"  ✓ Pathway 노드 MERGE: {len(pathway_rows):,}개")

        # Target-IN_PATHWAY->Pathway 엣지
        edge_rows = df_member[["gene_symbol", "gene_set_name"]].to_dict("records")
        q_edge = """
        UNWIND $rows AS r
        MATCH (t:Target {gene_name: r.gene_symbol})
        MATCH (p:Pathway {pathway_id: r.gene_set_name})
        MERGE (t)-[:IN_PATHWAY]->(p)
        """
        cnt = batch_run(session, q_edge, edge_rows)
        print(f"  ✓ Target-IN_PATHWAY->Pathway 엣지: {cnt:,}개")


# ── 7. DepMap ────────────────────────────────────────────────────────
def load_depmap(driver):
    print("\n" + "=" * 60)
    print("  [7/7] DepMap (Cell Line metadata)")
    print("=" * 60)

    df = read_parquet(
        f"{PREFIX}/depmap/depmap_model_basic_clean_20260406.parquet",
        columns=["ModelID", "CellLineName", "StrippedCellLineName",
                 "OncotreeLineage", "OncotreePrimaryDisease", "OncotreeSubtype",
                 "SangerModelID", "COSMICID", "Sex", "PrimaryOrMetastasis"],
    )
    df = df.where(df.notna(), None)

    rows = df.to_dict("records")

    with driver.session(database=DATABASE) as session:
        # 기존 CellLine에 DepMap 메타데이터 보강
        q = """
        UNWIND $rows AS r
        MATCH (c:CellLine {depmap_id: r.SangerModelID})
        SET c.model_id             = r.ModelID,
            c.stripped_name        = r.StrippedCellLineName,
            c.lineage              = r.OncotreeLineage,
            c.primary_disease      = r.OncotreePrimaryDisease,
            c.subtype              = r.OncotreeSubtype,
            c.cosmic_id            = r.COSMICID,
            c.sex                  = r.Sex,
            c.primary_or_metastasis = r.PrimaryOrMetastasis
        """
        batch_run(session, q, rows)

        result = session.run(
            "MATCH (c:CellLine) WHERE c.model_id IS NOT NULL RETURN count(c) AS cnt"
        ).single()
        print(f"  ✓ CellLine 메타데이터 보강: {result['cnt']}개 (SangerModelID 매칭)")

        total_cl = session.run("MATCH (c:CellLine) RETURN count(c) AS cnt").single()
        print(f"  ✓ CellLine 노드 전체: {total_cl['cnt']:,}개")


# ── 전체 통계 ────────────────────────────────────────────────────────
def print_stats(driver):
    print("\n" + "=" * 60)
    print("  Neo4j 전체 통계")
    print("=" * 60)

    with driver.session(database=DATABASE) as session:
        nodes = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt "
            "ORDER BY label"
        ).data()
        edges = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt "
            "ORDER BY type"
        ).data()

    total_n = sum(n["cnt"] for n in nodes)
    total_e = sum(e["cnt"] for e in edges)

    print(f"\n  노드 ({total_n:,}개):")
    for n in nodes:
        print(f"    :{n['label']:20s} {n['cnt']:>10,}개")
    print(f"\n  엣지 ({total_e:,}개):")
    for e in edges:
        print(f"    -[:{e['type']:20s}]-> {e['cnt']:>10,}개")


# ── main ─────────────────────────────────────────────────────────────
ALL_SOURCES = {
    "drugbank": load_drugbank,
    "chembl": load_chembl,
    "gdsc": load_gdsc,
    "string": load_string,
    "opentargets": load_opentargets,
    "msigdb": load_msigdb,
    "depmap": load_depmap,
}


def main():
    parser = argparse.ArgumentParser(description="curated_date → Neo4j 적재")
    parser.add_argument(
        "--source",
        nargs="*",
        default=list(ALL_SOURCES.keys()),
        help="적재할 소스 (drugbank chembl gdsc string opentargets msigdb depmap)",
    )
    args = parser.parse_args()

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}")

    for src in args.source:
        src = src.lower()
        if src not in ALL_SOURCES:
            print(f"  ⚠ 알 수 없는 소스: {src} (건너뜀)")
            continue
        try:
            ALL_SOURCES[src](driver)
        except Exception as e:
            print(f"  ✗ [{src}] 에러: {e}")
            import traceback
            traceback.print_exc()
            print("  → 다음 소스로 계속")

    print_stats(driver)
    driver.close()


if __name__ == "__main__":
    main()
