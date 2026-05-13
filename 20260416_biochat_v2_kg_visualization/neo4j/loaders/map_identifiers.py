"""
UniProt 기반 통합 식별자 매핑 + 엣지 생성

Step 1. ChEMBL uniprot mapping (S3)  →  Target 노드에 gene_symbol 추가
Step 2. STRING protein_info (S3)     →  gene_symbol 보강
Step 3. OpenTargets target (S3)      →  ensembl_id → gene_symbol 매핑
Step 4. DrugBank target_table (S3)   →  Drug-TARGETS 엣지
Step 5. STRING links (S3)            →  INTERACTS_WITH 엣지
Step 6. OpenTargets association (S3) →  ASSOCIATED_WITH 엣지
"""

import io
import os
from pathlib import Path
from collections import Counter

import boto3
import pandas as pd
import yaml
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


def read_parquet(key, columns=None):
    print(f"    S3: s3://{BUCKET}/{key}")
    resp = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()), columns=columns)
    print(f"    → {len(df):,} rows")
    return df


def batch_run(session, query, rows, batch_size=500):
    for i in range(0, len(rows), batch_size):
        session.run(query, rows=rows[i : i + batch_size])
    return len(rows)


# ═══════════════════════════════════════════════════════════════
#  Step 1. Target 노드에 gene_symbol 추가 (ChEMBL uniprot mapping)
# ═══════════════════════════════════════════════════════════════
def step1_add_gene_symbol(driver):
    print("\n" + "=" * 60)
    print("  Step 1. ChEMBL uniprot → Target gene_symbol 추가")
    print("=" * 60)

    # ChEMBL uniprot mapping: target_chembl_id → uniprot_id
    df_uniprot = read_parquet(
        f"{PREFIX}/chembl/chembl_uniprot_target_mapping_basic_20260406.parquet",
    )
    # chembl_target_id → uniprot_id
    chembl_uniprot = dict(zip(df_uniprot["target_chembl_id"], df_uniprot["uniprot_id"]))

    # STRING protein_info: string_protein_id → gene_symbol
    df_string = read_parquet(
        f"{PREFIX}/string/string_protein_info_basic_20260406.parquet",
        columns=["string_protein_id", "preferred_name"],
    )
    # gene_symbol → string_protein_id (역매핑)
    gene_to_string = dict(zip(df_string["preferred_name"], df_string["string_protein_id"]))

    # OpenTargets target: ensembl_id → gene_symbol
    df_ot = read_parquet(
        f"{PREFIX}/opentargets/opentargets_target_basic_20260406.parquet",
        columns=["id", "approvedSymbol"],
    )
    ensembl_to_gene = dict(zip(df_ot["id"], df_ot["approvedSymbol"]))
    gene_to_ensembl = dict(zip(df_ot["approvedSymbol"], df_ot["id"]))

    # DrugBank target_table: gene_name 으로 기존 Target 매핑
    df_dbt = read_parquet(
        f"{PREFIX}/drugbank/drugbank_target_table_basic_20260406.parquet",
        columns=["drugbank_id", "gene_name", "target_name"],
    )
    # gene_name → target_name 매핑 (추후 사용)
    gene_to_target_name = {}
    for _, r in df_dbt.iterrows():
        if pd.notna(r["gene_name"]):
            gene_to_target_name[r["gene_name"]] = r["target_name"]

    # --- Target 노드에 gene_symbol 부여 ---
    # 전략: ChEMBL pref_name → DrugBank gene_name 목록에서 매칭
    # 또는 ChEMBL chembl_target_id → uniprot_id → STRING gene_symbol

    with driver.session(database=DATABASE) as session:
        # 현재 Target 노드 조회
        targets = session.run(
            "MATCH (t:Target) RETURN t.gene_name AS pref_name, "
            "t.chembl_target_id AS chembl_id, t.uniprot_id AS uniprot_id"
        ).data()
        print(f"\n    현재 Target 노드: {len(targets):,}개")

        # uniprot_id가 있는 Target → STRING preferred_name으로 gene_symbol 찾기
        update_rows = []
        for t in targets:
            chembl_id = t.get("chembl_id")
            uniprot_id = t.get("uniprot_id")

            # uniprot_id가 없으면 ChEMBL mapping에서 가져오기
            if not uniprot_id and chembl_id:
                uniprot_id = chembl_uniprot.get(chembl_id)

            if not uniprot_id:
                continue

            # STRING에서 이 uniprot 매핑은 직접 불가 (STRING은 ENSP 기반)
            # 대신 OpenTargets에서 gene_symbol 찾기
            # → ChEMBL pref_name은 protein name이라 gene symbol과 다름
            # pref_name이 짧으면(10자 이하) gene symbol일 가능성 높음
            pref = t["pref_name"]
            gene_symbol = None

            # 1) pref_name 자체가 gene_symbol인 경우 (짧고 대문자)
            if pref and len(pref) <= 15 and pref == pref.upper():
                gene_symbol = pref

            # 2) 아직 못 찾으면 → pref_name이 DrugBank target_name에 있는지
            if not gene_symbol:
                for gn, tn in gene_to_target_name.items():
                    if pref and tn and pref.lower() in tn.lower():
                        gene_symbol = gn
                        break

            if gene_symbol:
                row = {
                    "pref_name": pref,
                    "gene_symbol": gene_symbol,
                    "uniprot_id": uniprot_id,
                }
                # string_id 추가
                if gene_symbol in gene_to_string:
                    row["string_id"] = gene_to_string[gene_symbol]
                # ensembl_id 추가
                if gene_symbol in gene_to_ensembl:
                    row["ensembl_id"] = gene_to_ensembl[gene_symbol]
                update_rows.append(row)

        print(f"    gene_symbol 매핑 성공: {len(update_rows):,} / {len(targets):,}")

        # 업데이트
        q = """
        UNWIND $rows AS r
        MATCH (t:Target {gene_name: r.pref_name})
        SET t.gene_symbol = r.gene_symbol,
            t.uniprot_id  = r.uniprot_id
        """
        batch_run(session, q, update_rows)

        # string_id 추가
        string_rows = [r for r in update_rows if "string_id" in r]
        if string_rows:
            q_s = """
            UNWIND $rows AS r
            MATCH (t:Target {gene_name: r.pref_name})
            SET t.string_id = r.string_id
            """
            batch_run(session, q_s, string_rows)
            print(f"    string_id 추가: {len(string_rows):,}개")

        # ensembl_id 추가
        ensembl_rows = [r for r in update_rows if "ensembl_id" in r]
        if ensembl_rows:
            q_e = """
            UNWIND $rows AS r
            MATCH (t:Target {gene_name: r.pref_name})
            SET t.ensembl_id = r.ensembl_id
            """
            batch_run(session, q_e, ensembl_rows)
            print(f"    ensembl_id 추가: {len(ensembl_rows):,}개")

    return gene_to_string, ensembl_to_gene, gene_to_ensembl


# ═══════════════════════════════════════════════════════════════
#  Step 2. Drug-[:TARGETS]->Target 엣지 (DrugBank 기반)
# ═══════════════════════════════════════════════════════════════
def step2_drug_targets(driver):
    print("\n" + "=" * 60)
    print("  Step 2. Drug-TARGETS->Target 엣지 생성")
    print("=" * 60)

    df_dbt = read_parquet(
        f"{PREFIX}/drugbank/drugbank_target_table_basic_20260406.parquet",
        columns=["drugbank_id", "gene_name", "target_name", "target_actions", "known_action"],
    )
    df_dbt = df_dbt[df_dbt["gene_name"].notna()].copy()

    # DrugBank drug_master → name ↔ drugbank_id
    df_dbm = read_parquet(
        f"{PREFIX}/drugbank/drugbank_drug_master_basic_20260406.parquet",
        columns=["drugbank_id", "name"],
    )
    id_to_name = dict(zip(df_dbm["drugbank_id"], df_dbm["name"]))

    # 수동 매핑 YAML 로드
    manual_yaml = Path(__file__).parent / "manual_drug_target_mapping.yaml"
    manual_mappings = []
    ALIAS = {}
    if manual_yaml.exists():
        cfg = yaml.safe_load(manual_yaml.read_text(encoding="utf-8"))
        manual_mappings = cfg.get("manual_mappings", [])
        for m in manual_mappings:
            if m.get("drugbank_alias"):
                ALIAS[m["drugbank_alias"]] = m["drug_name"]
        print(f"    수동 매핑 로드: {len(manual_mappings)}개 ({manual_yaml.name})")

    # 파이프라인 약물 (Neo4j에서 rank 있는 것)
    with driver.session(database=DATABASE) as session:
        pipeline_drugs = {
            r["name"]
            for r in session.run(
                "MATCH (d:Drug) WHERE d.rank IS NOT NULL RETURN d.name AS name"
            ).data()
        }
    print(f"    파이프라인 Drug: {pipeline_drugs}")

    # DrugBank 매칭 (이름 기준)
    name_to_dbid = {v.lower(): k for k, v in id_to_name.items()}
    # alias 추가 (수동 매핑에서)
    for alias, real in ALIAS.items():
        if alias.lower() in name_to_dbid:
            name_to_dbid[real.lower()] = name_to_dbid[alias.lower()]

    edges = []
    mapped_drugs = set()
    unmapped_drugs = set()

    for drug_name in pipeline_drugs:
        dbid = name_to_dbid.get(drug_name.lower())
        if not dbid:
            unmapped_drugs.add(drug_name)
            continue

        targets = df_dbt[df_dbt["drugbank_id"] == dbid]
        if len(targets) == 0:
            unmapped_drugs.add(drug_name)
            continue

        mapped_drugs.add(drug_name)
        for _, t in targets.iterrows():
            edges.append({
                "drug_name": ALIAS.get(id_to_name.get(dbid, drug_name), drug_name),
                "gene_name": t["gene_name"],
                "target_name": t["target_name"] if pd.notna(t["target_name"]) else None,
                "action": t["target_actions"] if pd.notna(t["target_actions"]) else None,
            })

    # 수동 매핑 처리 (DrugBank 미등재 약물)
    for m in manual_mappings:
        dname = m["drug_name"]
        if dname in unmapped_drugs:
            for gene in m.get("gene_targets", []):
                edges.append({
                    "drug_name": dname,
                    "gene_name": gene,
                    "target_name": None,
                    "action": None,
                })
            unmapped_drugs.discard(dname)
            mapped_drugs.add(dname)
            print(f"    수동 매핑 적용: {dname} → {m['gene_targets']} ({m['source']})")

    print(f"    매핑 성공: {len(mapped_drugs)}개 → {mapped_drugs}")
    print(f"    매핑 실패: {len(unmapped_drugs)}개 → {unmapped_drugs}")
    print(f"    엣지 후보: {len(edges)}개")

    with driver.session(database=DATABASE) as session:
        # 먼저 gene_symbol 또는 gene_name으로 Target 매칭 시도
        q = """
        UNWIND $rows AS r
        MATCH (d:Drug {name: r.drug_name})
        MATCH (t:Target)
        WHERE t.gene_symbol = r.gene_name OR t.gene_name = r.gene_name
        MERGE (d)-[rel:TARGETS]->(t)
        SET rel.source      = 'DrugBank',
            rel.target_name = r.target_name,
            rel.action       = r.action
        """
        batch_run(session, q, edges)

        result = session.run(
            "MATCH ()-[r:TARGETS]->() RETURN count(r) AS cnt"
        ).single()
        print(f"  ✓ Drug-TARGETS->Target 엣지: {result['cnt']}개")

    return unmapped_drugs


# ═══════════════════════════════════════════════════════════════
#  Step 3. Target-[:INTERACTS_WITH]->Target (STRING PPI)
# ═══════════════════════════════════════════════════════════════
def step3_string_ppi(driver):
    print("\n" + "=" * 60)
    print("  Step 3. STRING PPI → INTERACTS_WITH 엣지")
    print("=" * 60)

    df_info = read_parquet(
        f"{PREFIX}/string/string_protein_info_basic_20260406.parquet",
        columns=["string_protein_id", "preferred_name"],
    )
    ensp_to_gene = dict(zip(df_info["string_protein_id"], df_info["preferred_name"]))

    # 기존 Target 중 gene_symbol 있는 것
    with driver.session(database=DATABASE) as session:
        existing = {
            r["gs"]
            for r in session.run(
                "MATCH (t:Target) WHERE t.gene_symbol IS NOT NULL "
                "RETURN t.gene_symbol AS gs"
            ).data()
        }
    print(f"    gene_symbol 있는 Target: {len(existing):,}개")

    df_links = read_parquet(f"{PREFIX}/string/string_links_basic_20260406.parquet")
    df_links = df_links[df_links["combined_score"] >= 700].copy()
    print(f"    score >= 700: {len(df_links):,} edges")

    df_links["gene1"] = df_links["protein1"].map(ensp_to_gene)
    df_links["gene2"] = df_links["protein2"].map(ensp_to_gene)
    df_links = df_links.dropna(subset=["gene1", "gene2"])

    df_links = df_links[
        df_links["gene1"].isin(existing) & df_links["gene2"].isin(existing)
    ].copy()
    print(f"    Target 매칭 후: {len(df_links):,} edges")

    if len(df_links) == 0:
        print("  ⚠ 매칭 없음")
        return

    edges = df_links[["gene1", "gene2", "combined_score"]].to_dict("records")

    with driver.session(database=DATABASE) as session:
        q = """
        UNWIND $rows AS r
        MATCH (t1:Target {gene_symbol: r.gene1})
        MATCH (t2:Target {gene_symbol: r.gene2})
        MERGE (t1)-[rel:INTERACTS_WITH]->(t2)
        SET rel.score  = r.combined_score,
            rel.source = 'STRING'
        """
        batch_run(session, q, edges)

        result = session.run(
            "MATCH ()-[r:INTERACTS_WITH]->() RETURN count(r) AS cnt"
        ).single()
        print(f"  ✓ INTERACTS_WITH 엣지: {result['cnt']:,}개")


# ═══════════════════════════════════════════════════════════════
#  Step 4. Target-[:ASSOCIATED_WITH]->Disease (OpenTargets)
# ═══════════════════════════════════════════════════════════════
def step4_opentargets_association(driver):
    print("\n" + "=" * 60)
    print("  Step 4. OpenTargets → ASSOCIATED_WITH 엣지")
    print("=" * 60)

    df_dis = read_parquet(
        f"{PREFIX}/opentargets/opentargets_disease_basic_20260406.parquet",
        columns=["id", "name"],
    )
    brca_ids = set(
        df_dis[df_dis["name"].str.contains("breast", case=False, na=False)]["id"]
    )
    print(f"    breast 관련 disease IDs: {len(brca_ids)}개")

    df_assoc = read_parquet(
        f"{PREFIX}/opentargets/opentargets_association_overall_direct_basic_20260406.parquet",
    )
    df_assoc = df_assoc[
        (df_assoc["score"] >= 0.5) & (df_assoc["diseaseId"].isin(brca_ids))
    ].copy()
    print(f"    BRCA + score>=0.5: {len(df_assoc):,} associations")

    # target ID (Ensembl) → gene_symbol
    df_ot = read_parquet(
        f"{PREFIX}/opentargets/opentargets_target_basic_20260406.parquet",
        columns=["id", "approvedSymbol"],
    )
    ensembl_to_gene = dict(zip(df_ot["id"], df_ot["approvedSymbol"]))
    df_assoc["gene_symbol"] = df_assoc["targetId"].map(ensembl_to_gene)
    df_assoc = df_assoc.dropna(subset=["gene_symbol"])

    # gene_symbol 있는 Target만
    with driver.session(database=DATABASE) as session:
        existing = {
            r["gs"]
            for r in session.run(
                "MATCH (t:Target) WHERE t.gene_symbol IS NOT NULL "
                "RETURN t.gene_symbol AS gs"
            ).data()
        }

    df_matched = df_assoc[df_assoc["gene_symbol"].isin(existing)].copy()
    print(f"    Target 매칭: {len(df_matched):,} associations")

    if len(df_matched) == 0:
        print("  ⚠ 매칭 없음")
        return

    edges = df_matched[["gene_symbol", "score", "evidenceCount"]].to_dict("records")

    with driver.session(database=DATABASE) as session:
        q = """
        UNWIND $rows AS r
        MATCH (t:Target {gene_symbol: r.gene_symbol})
        MATCH (dis:Disease {code: 'BRCA'})
        MERGE (t)-[rel:ASSOCIATED_WITH]->(dis)
        SET rel.score          = r.score,
            rel.evidence_count = r.evidenceCount,
            rel.source         = 'OpenTargets'
        """
        batch_run(session, q, edges)

        result = session.run(
            "MATCH ()-[r:ASSOCIATED_WITH]->() RETURN count(r) AS cnt"
        ).single()
        print(f"  ✓ ASSOCIATED_WITH 엣지: {result['cnt']:,}개")


# ═══════════════════════════════════════════════════════════════
#  전체 통계
# ═══════════════════════════════════════════════════════════════
def print_stats(driver):
    print("\n" + "=" * 60)
    print("  최종 Neo4j 통계")
    print("=" * 60)

    with driver.session(database=DATABASE) as session:
        nodes = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY label"
        ).data()
        edges = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt ORDER BY type"
        ).data()

        # gene_symbol 커버리지
        gs = session.run(
            "MATCH (t:Target) "
            "RETURN count(t) AS total, "
            "count(t.gene_symbol) AS with_symbol"
        ).single()

    total_n = sum(n["cnt"] for n in nodes)
    total_e = sum(e["cnt"] for e in edges)

    print(f"\n  노드 ({total_n:,}개):")
    for n in nodes:
        print(f"    :{n['label']:20s} {n['cnt']:>10,}개")
    print(f"\n  엣지 ({total_e:,}개):")
    for e in edges:
        print(f"    -[:{e['type']:20s}]-> {e['cnt']:>10,}개")
    print(f"\n  Target gene_symbol 커버리지: {gs['with_symbol']:,} / {gs['total']:,}")


# ═══════════════════════════════════════════════════════════════
def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}")

    step1_add_gene_symbol(driver)
    step2_drug_targets(driver)
    step3_string_ppi(driver)
    step4_opentargets_association(driver)
    print_stats(driver)

    driver.close()


if __name__ == "__main__":
    main()
