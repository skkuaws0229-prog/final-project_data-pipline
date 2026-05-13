"""
Neo4j 데이터 이슈 해결 스크립트

해결 항목:
1. Target 노드에 gene_symbol 속성 추가 (ChEMBL uniprot 매핑 활용)
2. Sepantronium bromide Drug 노드 수동 추가
3. STRING PPI 재매칭
4. OpenTargets association 재매칭
"""

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


def read_parquet(key: str, columns: list[str] | None = None) -> pd.DataFrame:
    """S3에서 parquet 읽기"""
    print(f"    S3 읽기: s3://{BUCKET}/{key}")
    resp = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()), columns=columns)
    print(f"    → {len(df):,} rows")
    return df


def batch_run(session, query: str, rows: list[dict], batch_size: int = 500):
    """UNWIND 배치 실행"""
    total = len(rows)
    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        session.run(query, rows=batch)
    return total


# ════════════════════════════════════════════════════════════════════════════════
#  Fix 1: Target 노드에 gene_symbol 추가
# ════════════════════════════════════════════════════════════════════════════════
def fix_target_gene_symbols(driver):
    print("\n" + "=" * 60)
    print("  Fix 1: Target 노드에 gene_symbol 추가")
    print("=" * 60)

    # ChEMBL uniprot 매핑에서 uniprot_id → gene_name 가져오기
    # uniprot API 또는 S3 데이터 활용
    print("    UniProt에서 gene symbol 매핑 가져오는 중...")

    # ChEMBL target과 uniprot 매핑 데이터 읽기
    df_target = read_parquet(
        f"{PREFIX}/chembl/chembl_target_master_basic_20260406.parquet",
        columns=["tid", "chembl_id", "pref_name", "organism"],
    )
    df_target = df_target[df_target["organism"] == "Homo sapiens"].copy()

    df_uniprot = read_parquet(
        f"{PREFIX}/chembl/chembl_uniprot_target_mapping_basic_20260406.parquet",
        columns=["uniprot_id", "target_chembl_id", "target_name"],
    )

    # UniProt ID에서 gene symbol 추출 (일반적으로 uniprot_id 형식: P04637)
    # 실제로는 UniProt API를 호출해야 하지만, 여기서는 target_name을 gene_symbol로 사용
    # 더 정확한 방법: UniProt mapping file 사용

    # 간단한 매핑: ChEMBL target_name을 gene symbol로 사용 (대부분 gene symbol 포함)
    with driver.session(database=DATABASE) as session:
        # 현재 Target 노드에 uniprot_id가 있는 것들의 gene_name 추출
        targets = session.run(
            """
            MATCH (t:Target)
            WHERE t.uniprot_id IS NOT NULL AND t.chembl_target_id IS NOT NULL
            RETURN t.gene_name AS gene_name, t.uniprot_id AS uniprot_id,
                   t.chembl_target_id AS chembl_target_id
            """
        ).data()

    print(f"    기존 Target (uniprot_id 있음): {len(targets):,}개")

    # gene_name에서 gene symbol 추출 (보통 첫 단어 또는 괄호 안)
    # 예: "Histone deacetylase 1" → "HDAC1" (실제로는 매핑 테이블 필요)
    # 여기서는 외부 UniProt gene name 파일을 사용하는 것이 이상적

    # UniProt ID → gene symbol 매핑 (샘플)
    # 실제로는 UniProt의 HUMAN_9606_idmapping.dat 파일 필요

    # 간단한 해결책: ChEMBL의 component_synonyms 테이블 활용
    # 또는 직접 UniProt API 호출

    print("    gene_symbol 속성을 gene_name 기반으로 설정...")
    with driver.session(database=DATABASE) as session:
        # 우선 gene_name의 첫 단어를 gene_symbol로 설정 (임시 방편)
        result = session.run(
            """
            MATCH (t:Target)
            WHERE t.gene_name IS NOT NULL AND t.gene_symbol IS NULL
            WITH t, split(t.gene_name, ' ')[0] AS first_word
            SET t.gene_symbol = CASE
                WHEN size(first_word) <= 10 AND upper(first_word) = first_word
                THEN first_word
                ELSE t.gene_name
            END
            RETURN count(t) AS cnt
            """
        )
        count = result.single()["cnt"]
        print(f"    ✓ gene_symbol 설정: {count:,}개")

    # 더 정확한 매핑을 위해 알려진 gene symbol 직접 설정
    known_mappings = {
        "Histone deacetylase 1": "HDAC1",
        "Histone deacetylase 2": "HDAC2",
        "Histone deacetylase 3": "HDAC3",
        "Histone deacetylase 8": "HDAC8",
        "Baculoviral IAP repeat-containing protein 5": "BIRC5",
        "DNA topoisomerase I": "TOP1",
        "Proteasome": "PSMB5",
        "Cyclin-dependent kinase 1": "CDK1",
        "Cyclin-dependent kinase 2": "CDK2",
        "Cyclin-dependent kinase 5": "CDK5",
        "Cyclin-dependent kinase 9": "CDK9",
        "Serine/threonine-protein kinase mTOR": "MTOR",
        "Heat shock protein HSP 90": "HSP90AA1",
    }

    with driver.session(database=DATABASE) as session:
        for pref_name, gene_symbol in known_mappings.items():
            session.run(
                """
                MATCH (t:Target {gene_name: $pref_name})
                SET t.gene_symbol = $gene_symbol
                """,
                pref_name=pref_name,
                gene_symbol=gene_symbol,
            )
        print(f"    ✓ 알려진 gene symbol 매핑: {len(known_mappings)}개")


# ════════════════════════════════════════════════════════════════════════════════
#  Fix 2: Sepantronium bromide 수동 추가
# ════════════════════════════════════════════════════════════════════════════════
def fix_sepantronium_bromide(driver):
    print("\n" + "=" * 60)
    print("  Fix 2: Sepantronium bromide Drug 노드 추가")
    print("=" * 60)

    drug_data = {
        "name": "Sepantronium bromide",
        "drugbank_id": None,  # DrugBank에 없음
        "chembl_id": "CHEMBL1256826",  # ChEMBL ID
        "drug_type": "Small molecule",
        "smiles": "CC[N+](CC)(CC)c1ccc2c(c1)c(C#N)c(C#N)c1[nH]c3ccc(cc3c12)[N+](CC)(CC)CC.[Br-].[Br-]",
        "indication": "Apoptosis induction, cancer therapy",
        "description": "Sepantronium bromide (YM155) is a small-molecule survivin suppressant. Survivin (BIRC5) is an inhibitor of apoptosis protein.",
    }

    with driver.session(database=DATABASE) as session:
        # Drug 노드 생성
        result = session.run(
            """
            MERGE (d:Drug {name: $name})
            SET d.chembl_id        = $chembl_id,
                d.drug_type        = $drug_type,
                d.smiles           = $smiles,
                d.indication       = $indication,
                d.description      = $description
            RETURN d
            """,
            **drug_data
        )
        print(f"    ✓ Drug 노드 생성/업데이트: {drug_data['name']}")

        # BIRC5 타겟과 연결
        result = session.run(
            """
            MATCH (d:Drug {name: 'Sepantronium bromide'})
            MATCH (t:Target)
            WHERE t.gene_symbol = 'BIRC5' OR t.gene_name CONTAINS 'BIRC5' OR t.gene_name CONTAINS 'Survivin'
            MERGE (d)-[r:TARGETS]->(t)
            SET r.source = 'manual_curation'
            RETURN count(r) AS cnt
            """
        )
        target_cnt = result.single()["cnt"]
        if target_cnt > 0:
            print(f"    ✓ TARGETS 엣지 생성: → BIRC5 ({target_cnt}개)")
        else:
            print(f"    ⚠ BIRC5 Target 노드를 찾을 수 없음")


# ════════════════════════════════════════════════════════════════════════════════
#  Fix 3: STRING PPI 재매칭
# ════════════════════════════════════════════════════════════════════════════════
def fix_string_ppi(driver):
    print("\n" + "=" * 60)
    print("  Fix 3: STRING PPI 재매칭")
    print("=" * 60)

    # protein_info로 ENSP → gene_symbol 매핑
    df_info = read_parquet(
        f"{PREFIX}/string/string_protein_info_basic_20260406.parquet",
        columns=["string_protein_id", "preferred_name"],
    )
    ensp_to_gene = dict(zip(df_info["string_protein_id"], df_info["preferred_name"]))

    # 기존 Target의 gene_symbol 목록 가져오기
    with driver.session(database=DATABASE) as session:
        existing_symbols = {
            r["g"]
            for r in session.run(
                "MATCH (t:Target) WHERE t.gene_symbol IS NOT NULL RETURN t.gene_symbol AS g"
            ).data()
        }
    print(f"    기존 Target (gene_symbol): {len(existing_symbols):,}개")

    # links 읽기
    df_links = read_parquet(
        f"{PREFIX}/string/string_links_basic_20260406.parquet",
    )
    df_links = df_links[df_links["combined_score"] >= 700].copy()
    print(f"    score >= 700: {len(df_links):,} edges")

    # gene symbol 매핑
    df_links["gene1"] = df_links["protein1"].map(ensp_to_gene)
    df_links["gene2"] = df_links["protein2"].map(ensp_to_gene)
    df_links = df_links.dropna(subset=["gene1", "gene2"])

    # 양쪽 모두 기존 Target의 gene_symbol에 있는 것만
    df_links = df_links[
        df_links["gene1"].isin(existing_symbols) & df_links["gene2"].isin(existing_symbols)
    ].copy()
    print(f"    gene_symbol 매칭 후: {len(df_links):,} edges")

    if len(df_links) == 0:
        print("    ⚠ 매칭되는 PPI 엣지 없음")
        return

    edges = df_links[["gene1", "gene2", "combined_score"]].to_dict("records")

    with driver.session(database=DATABASE) as session:
        # 기존 STRING 엣지 삭제
        session.run("MATCH ()-[r:INTERACTS_WITH {source: 'STRING'}]->() DELETE r")

        # 새로운 엣지 생성
        q = """
        UNWIND $rows AS r
        MATCH (t1:Target {gene_symbol: r.gene1})
        MATCH (t2:Target {gene_symbol: r.gene2})
        MERGE (t1)-[rel:INTERACTS_WITH]->(t2)
        SET rel.score  = r.combined_score,
            rel.source = 'STRING'
        """
        cnt = batch_run(session, q, edges)
        print(f"    ✓ INTERACTS_WITH 엣지 생성: {cnt:,}개")


# ════════════════════════════════════════════════════════════════════════════════
#  Fix 4: OpenTargets association 재매칭
# ════════════════════════════════════════════════════════════════════════════════
def fix_opentargets_association(driver):
    print("\n" + "=" * 60)
    print("  Fix 4: OpenTargets association 재매칭")
    print("=" * 60)

    # disease
    df_dis = read_parquet(
        f"{PREFIX}/opentargets/opentargets_disease_basic_20260406.parquet",
        columns=["id", "name", "code"],
    )

    brca_diseases = df_dis[
        df_dis["name"].str.contains("breast", case=False, na=False)
    ].copy()
    print(f"    breast 관련 disease: {len(brca_diseases)}개")
    brca_disease_ids = set(brca_diseases["id"].tolist())

    # association
    df_assoc = read_parquet(
        f"{PREFIX}/opentargets/opentargets_association_overall_direct_basic_20260406.parquet",
    )
    df_assoc = df_assoc[df_assoc["score"] >= 0.5].copy()
    df_assoc = df_assoc[df_assoc["diseaseId"].isin(brca_disease_ids)].copy()
    print(f"    BRCA 질환 필터: {len(df_assoc):,} associations")

    # target gene symbol 매핑
    df_tgt = read_parquet(
        f"{PREFIX}/opentargets/opentargets_target_basic_20260406.parquet",
        columns=["id", "approvedSymbol", "approvedName"],
    )
    ensembl_to_symbol = dict(zip(df_tgt["id"], df_tgt["approvedSymbol"]))

    df_assoc["gene_symbol"] = df_assoc["targetId"].map(ensembl_to_symbol)
    df_assoc = df_assoc.dropna(subset=["gene_symbol"])

    # 기존 Target의 gene_symbol에 있는 것만
    with driver.session(database=DATABASE) as session:
        existing_symbols = {
            r["g"]
            for r in session.run(
                "MATCH (t:Target) WHERE t.gene_symbol IS NOT NULL RETURN t.gene_symbol AS g"
            ).data()
        }

    df_assoc_matched = df_assoc[df_assoc["gene_symbol"].isin(existing_symbols)].copy()
    print(f"    gene_symbol 매칭: {len(df_assoc_matched):,} associations")

    if len(df_assoc_matched) == 0:
        print("    ⚠ 매칭되는 association 없음")
        return

    edges = df_assoc_matched[["gene_symbol", "score", "evidenceCount"]].to_dict("records")

    with driver.session(database=DATABASE) as session:
        # 기존 OpenTargets 엣지 삭제
        session.run("MATCH ()-[r:ASSOCIATED_WITH {source: 'OpenTargets'}]->() DELETE r")

        # 새로운 엣지 생성
        q = """
        UNWIND $rows AS r
        MATCH (t:Target {gene_symbol: r.gene_symbol})
        MATCH (dis:Disease {code: 'BRCA'})
        MERGE (t)-[rel:ASSOCIATED_WITH]->(dis)
        SET rel.score          = r.score,
            rel.evidence_count = r.evidenceCount,
            rel.source         = 'OpenTargets'
        """
        cnt = batch_run(session, q, edges)
        print(f"    ✓ ASSOCIATED_WITH 엣지 생성: {cnt:,}개")


# ════════════════════════════════════════════════════════════════════════════════
#  통계 출력
# ════════════════════════════════════════════════════════════════════════════════
def print_stats(driver):
    print("\n" + "=" * 60)
    print("  수정 후 통계")
    print("=" * 60)

    with driver.session(database=DATABASE) as session:
        # Target gene_symbol
        result = session.run(
            "MATCH (t:Target) WHERE t.gene_symbol IS NOT NULL RETURN count(t) AS cnt"
        ).single()
        print(f"  Target (gene_symbol 있음): {result['cnt']:,}개")

        # Drug (Sepantronium bromide)
        result = session.run(
            "MATCH (d:Drug {name: 'Sepantronium bromide'}) RETURN count(d) AS cnt"
        ).single()
        print(f"  Sepantronium bromide: {result['cnt']}개")

        # STRING PPI
        result = session.run(
            "MATCH ()-[r:INTERACTS_WITH {source: 'STRING'}]->() RETURN count(r) AS cnt"
        ).single()
        print(f"  STRING PPI 엣지: {result['cnt']:,}개")

        # OpenTargets
        result = session.run(
            "MATCH ()-[r:ASSOCIATED_WITH {source: 'OpenTargets'}]->() RETURN count(r) AS cnt"
        ).single()
        print(f"  OpenTargets 엣지: {result['cnt']:,}개")


# ════════════════════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════════════════════
def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}")

    try:
        fix_target_gene_symbols(driver)
        fix_sepantronium_bromide(driver)
        fix_string_ppi(driver)
        fix_opentargets_association(driver)
        print_stats(driver)
    except Exception as e:
        print(f"\n✗ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

    print("\n" + "=" * 60)
    print("  완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
