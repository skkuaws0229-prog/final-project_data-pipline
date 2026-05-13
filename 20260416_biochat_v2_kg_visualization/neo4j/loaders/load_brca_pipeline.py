"""BRCA 파이프라인 결과 (api_server_v2.py) → Neo4j 적재"""

from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

# api_server_v2.py의 FINAL_CANDIDATES 데이터
FINAL_CANDIDATES = [
    {"rank": 1, "name": "Romidepsin", "target": "HDAC1, HDAC2, HDAC3, HDAC8", "pathway": "Chromatin histone acetylation", "ic50": -4.741, "validation": 6.90, "safety": 12.00, "combined": 19.00, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": False, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 2, "name": "Sepantronium bromide", "target": "BIRC5", "pathway": "Apoptosis regulation", "ic50": -3.855, "validation": 7.35, "safety": 10.00, "combined": 16.50, "category": "unused", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "재창출 관점의 exploratory candidate"},
    {"rank": 3, "name": "Staurosporine", "target": "Broad spectrum kinase inhibitor", "pathway": "RTK signaling", "ic50": -2.476, "validation": 7.55, "safety": 10.00, "combined": 13.50, "category": "unused", "flags": [], "target_expr": True, "brca_pathway": False, "survival": True, "recommendation": "재창출 관점의 exploratory candidate"},
    {"rank": 4, "name": "SN-38", "target": "TOP1", "pathway": "DNA replication", "ic50": -2.462, "validation": 9.00, "safety": 10.00, "combined": 13.00, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 5, "name": "Docetaxel", "target": "Microtubule stabiliser", "pathway": "Mitosis", "ic50": -3.303, "validation": 9.30, "safety": 6.83, "combined": 12.83, "category": "current", "flags": ["DILI"], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
    {"rank": 6, "name": "Bortezomib", "target": "Proteasome", "pathway": "Protein stability and degradation", "ic50": -4.752, "validation": 9.45, "safety": 5.29, "combined": 12.79, "category": "expansion", "flags": ["DILI"], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 7, "name": "Dactinomycin", "target": "RNA polymerase", "pathway": "Other", "ic50": -3.018, "validation": 7.75, "safety": 7.00, "combined": 12.50, "category": "unused", "flags": ["DILI"], "target_expr": True, "brca_pathway": False, "survival": True, "recommendation": "재창출 관점의 exploratory candidate"},
    {"rank": 8, "name": "Vinorelbine", "target": "Microtubule destabiliser", "pathway": "Mitosis", "ic50": -2.830, "validation": 9.15, "safety": 8.00, "combined": 12.50, "category": "current", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
    {"rank": 9, "name": "Dinaciclib", "target": "CDK1, CDK2, CDK5, CDK9", "pathway": "Cell cycle", "ic50": -2.191, "validation": 8.90, "safety": 10.00, "combined": 12.00, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 10, "name": "Paclitaxel", "target": "Microtubule stabiliser", "pathway": "Mitosis", "ic50": -2.837, "validation": 9.20, "safety": 6.83, "combined": 11.83, "category": "current", "flags": ["DILI"], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
    {"rank": 11, "name": "Vinblastine", "target": "Microtubule destabiliser", "pathway": "Mitosis", "ic50": -2.741, "validation": 9.10, "safety": 7.83, "combined": 11.83, "category": "current", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
    {"rank": 12, "name": "Camptothecin", "target": "TOP1", "pathway": "DNA replication", "ic50": -0.544, "validation": 8.65, "safety": 10.00, "combined": 11.00, "category": "unused", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "재창출 관점의 exploratory candidate"},
    {"rank": 13, "name": "Rapamycin", "target": "MTORC1", "pathway": "PI3K/MTOR signaling", "ic50": -2.395, "validation": 8.95, "safety": 7.71, "combined": 10.21, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 14, "name": "Luminespib", "target": "HSP90", "pathway": "Protein stability and degradation", "ic50": -1.834, "validation": 8.80, "safety": 5.00, "combined": 6.50, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 15, "name": "Epirubicin", "target": "Anthracycline", "pathway": "DNA replication", "ic50": 0.093, "validation": 8.30, "safety": 2.83, "combined": 3.33, "category": "current", "flags": ["Ames", "DILI"], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
]

ENSEMBLE_RESULT = {
    "weighted_spearman": 0.8720,
    "weighted_rmse": 1.1016,
    "ensemble_spearman": 0.8720,
    "ensemble_rmse": 1.1016,
}


def load_brca_pipeline():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}\n")

    with driver.session(database=DATABASE) as session:
        # 1) Disease 노드 MERGE
        session.run(
            """
            MERGE (dis:Disease {code: 'BRCA'})
            SET dis.name = 'Breast Cancer',
                dis.pipeline_date = '2026-04-06',
                dis.ensemble_spearman = $ensemble_spearman,
                dis.ensemble_rmse = $ensemble_rmse
            """,
            ensemble_spearman=ENSEMBLE_RESULT["ensemble_spearman"],
            ensemble_rmse=ENSEMBLE_RESULT["ensemble_rmse"],
        )
        print("✓ Disease 노드 MERGE: Breast Cancer (BRCA)")

        # 2) Drug 노드 업데이트 + TREATS 엣지
        updated = 0
        not_found = []

        for drug in FINAL_CANDIDATES:
            # Drug 노드에 파이프라인 결과 추가
            result = session.run(
                """
                MATCH (d:Drug {name: $name})
                SET d.pipeline_rank = $rank,
                    d.ic50_log = $ic50,
                    d.target = $target,
                    d.pathway = $pathway,
                    d.brca_status = $category,
                    d.validation_score = $validation,
                    d.safety_score = $safety,
                    d.overall_score = $combined,
                    d.target_expr = $target_expr,
                    d.brca_pathway = $brca_pathway,
                    d.survival_significant = $survival,
                    d.recommendation = $recommendation,
                    d.flags = $flags
                RETURN d.name AS name
                """,
                name=drug["name"],
                rank=drug["rank"],
                ic50=drug["ic50"],
                target=drug["target"],
                pathway=drug["pathway"],
                category=drug["category"],
                validation=drug["validation"],
                safety=drug["safety"],
                combined=drug["combined"],
                target_expr=drug["target_expr"],
                brca_pathway=drug["brca_pathway"],
                survival=drug["survival"],
                recommendation=drug["recommendation"],
                flags=drug["flags"],
            )

            if result.single():
                updated += 1

                # TREATS 엣지 생성
                session.run(
                    """
                    MATCH (d:Drug {name: $name})
                    MATCH (dis:Disease {code: 'BRCA'})
                    MERGE (d)-[r:TREATS]->(dis)
                    SET r.status = $status,
                        r.rank = $rank,
                        r.overall_score = $combined
                    """,
                    name=drug["name"],
                    status=drug["category"],
                    rank=drug["rank"],
                    combined=drug["combined"],
                )
            else:
                not_found.append(drug["name"])

        print(f"✓ Drug 노드 업데이트: {updated}개")
        if not_found:
            print(f"⚠ Neo4j에 없는 약물: {len(not_found)}개")
            for name in not_found[:5]:
                print(f"  - {name}")
            if len(not_found) > 5:
                print(f"  ... 외 {len(not_found)-5}개")

        # 3) TREATS 엣지 통계
        result = session.run(
            """
            MATCH (d:Drug)-[r:TREATS]->(dis:Disease {code: 'BRCA'})
            RETURN count(r) AS cnt
            """
        ).single()
        print(f"✓ TREATS 엣지: {result['cnt']}개")

        # 4) 전체 통계
        print("\n" + "="*60)
        print("  Neo4j 업데이트 완료")
        print("="*60)

        stats = session.run(
            """
            MATCH (n)
            RETURN labels(n)[0] AS label, count(*) AS cnt
            ORDER BY label
            """
        ).data()

        print("\n노드 통계:")
        for stat in stats:
            print(f"  :{stat['label']:20s} {stat['cnt']:>10,}개")

    driver.close()


if __name__ == "__main__":
    load_brca_pipeline()
