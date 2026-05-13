"""
범용 파이프라인 결과 Neo4j 적재 로더

사용법:
  python load_pipeline_results.py --disease BRCA
  python load_pipeline_results.py --disease LUAD
  python load_pipeline_results.py --disease all
"""

import argparse
from pathlib import Path
from collections import Counter

import yaml
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISEASE_DIR = PROJECT_ROOT / "config" / "diseases"

load_dotenv(PROJECT_ROOT / ".env")

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")


def load_yaml(disease_code: str) -> dict:
    path = DISEASE_DIR / f"{disease_code}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"설정 파일 없음: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def list_diseases() -> list[str]:
    return sorted(p.stem for p in DISEASE_DIR.glob("*.yaml"))


def load_disease(driver, config: dict):
    disease = config["disease"]
    drugs = config["drugs"]
    code = disease["code"]

    with driver.session(database=DATABASE) as session:
        # 1) Disease 노드 MERGE
        session.run(
            """
            MERGE (dis:Disease {code: $code})
            SET dis.name            = $name,
                dis.pipeline_date   = $pipeline_date,
                dis.ensemble_spearman = $ensemble_spearman,
                dis.ensemble_rmse   = $ensemble_rmse
            """,
            code=code,
            name=disease["name"],
            pipeline_date=disease["pipeline_date"],
            ensemble_spearman=disease["ensemble_spearman"],
            ensemble_rmse=disease["ensemble_rmse"],
        )
        print(f"  Disease 노드 MERGE: {disease['name']} ({code})")

        # 2) Drug 노드 MERGE + TREATS 엣지
        status_counter = Counter()
        drug_names = set()

        for d in drugs:
            session.run(
                """
                MERGE (drug:Drug {name: $name})
                SET drug.disease_code        = $disease_code,
                    drug.rank                = $rank,
                    drug.ic50                = $ic50,
                    drug.target              = $target,
                    drug.brca_status         = $brca_status,
                    drug.dili_flag           = $dili_flag,
                    drug.ames_flag           = $ames_flag,
                    drug.safety_score        = $safety_score,
                    drug.overall_score       = $overall_score,
                    drug.repurposing_evidence = $repurposing_evidence,
                    drug.pipeline_date       = $pipeline_date,
                    drug.ensemble_spearman   = $ensemble_spearman,
                    drug.ensemble_rmse       = $ensemble_rmse
                """,
                name=d["name"],
                disease_code=code,
                rank=d["rank"],
                ic50=d["ic50"],
                target=d["target"],
                brca_status=d["brca_status"],
                dili_flag=d["dili_flag"],
                ames_flag=d["ames_flag"],
                safety_score=d["safety_score"],
                overall_score=d["overall_score"],
                repurposing_evidence=d["repurposing_evidence"],
                pipeline_date=disease["pipeline_date"],
                ensemble_spearman=disease["ensemble_spearman"],
                ensemble_rmse=disease["ensemble_rmse"],
            )

            # 3) TREATS 엣지
            session.run(
                """
                MATCH (drug:Drug {name: $name})
                MATCH (dis:Disease {code: $code})
                MERGE (drug)-[r:TREATS]->(dis)
                SET r.status = $status,
                    r.rank   = $rank
                """,
                name=d["name"],
                code=code,
                status=d["brca_status"],
                rank=d["rank"],
            )

            drug_names.add(d["name"])
            status_counter[d["brca_status"]] += 1

        # 4) 통계 조회
        result = session.run(
            "MATCH (drug:Drug)-[r:TREATS]->(dis:Disease {code: $code}) "
            "RETURN count(DISTINCT drug) AS drugs, count(r) AS edges",
            code=code,
        ).single()

        print(f"\n{'='*50}")
        print(f"  [{code}] 적재 완료")
        print(f"{'='*50}")
        print(f"  Drug 노드 (고유)  : {len(drug_names)}개")
        print(f"  Disease 노드      : 1개")
        print(f"  TREATS 엣지       : {result['edges']}개")
        print(f"  Neo4j 확인 Drug   : {result['drugs']}개")
        print()
        for status, cnt in sorted(status_counter.items()):
            print(f"    {status}: {cnt}개")


def print_global_stats(driver):
    with driver.session(database=DATABASE) as session:
        nodes = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt").data()
        edges = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt"
        ).data()

    print(f"\n{'='*50}")
    print("  Neo4j 전체 현황")
    print(f"{'='*50}")
    for n in sorted(nodes, key=lambda x: x["label"]):
        print(f"    :{n['label']}  {n['cnt']}개")
    for e in sorted(edges, key=lambda x: x["type"]):
        print(f"    -[:{e['type']}]->  {e['cnt']}개")


def main():
    parser = argparse.ArgumentParser(description="파이프라인 결과 Neo4j 적재")
    parser.add_argument(
        "--disease",
        required=True,
        help="암종 코드 (BRCA, LUAD, ...) 또는 'all'",
    )
    args = parser.parse_args()

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결 확인: {URI}\n")

    if args.disease.lower() == "all":
        diseases = list_diseases()
        print(f"전체 암종 적재: {diseases}\n")
        for code in diseases:
            config = load_yaml(code)
            load_disease(driver, config)
    else:
        config = load_yaml(args.disease.upper())
        load_disease(driver, config)

    print_global_stats(driver)
    driver.close()


if __name__ == "__main__":
    main()
