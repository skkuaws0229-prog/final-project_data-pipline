"""Neo4j 쿼리 테스트"""

from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path
import os
import json

load_dotenv(Path(__file__).parent / ".env")

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

print("="*60)
print("  Neo4j 쿼리 테스트")
print("="*60)

with driver.session(database=DATABASE) as session:
    # 1. BRCA 치료 약물 조회
    print("\n1️⃣ BRCA 치료 약물 (Top 5):")
    result = session.run(
        """
        MATCH (d:Drug)-[r:TREATS]->(dis:Disease {code: 'BRCA'})
        RETURN d.name AS name, d.target AS target, d.overall_score AS score, r.rank AS rank
        ORDER BY r.rank
        LIMIT 5
        """
    ).data()

    for row in result:
        print(f"  #{row['rank']} {row['name']:20s} - Target: {row['target']:30s} Score: {row['score']}")

    # 2. Docetaxel 부작용 조회
    print("\n2️⃣ Docetaxel 부작용:")
    result = session.run(
        """
        MATCH (d:Drug {name: 'Docetaxel'})-[r:HAS_SIDE_EFFECT]->(s:SideEffect)
        RETURN s.name AS side_effect
        LIMIT 10
        """
    ).data()

    if result:
        for row in result:
            print(f"  - {row['side_effect']}")
    else:
        print("  ⚠ Docetaxel 부작용 관계 없음 (데이터 추가 필요)")

    # 3. Docetaxel 타겟 조회
    print("\n3️⃣ Docetaxel 타겟:")
    result = session.run(
        """
        MATCH (d:Drug {name: 'Docetaxel'})-[r:TARGETS]->(t:Target)
        RETURN t.gene_name AS target
        """
    ).data()

    if result:
        for row in result:
            print(f"  - {row['target']}")
    else:
        print("  ⚠ Docetaxel TARGETS 관계 없음")
        print("  → d.target 속성은 있음:", session.run("MATCH (d:Drug {name: 'Docetaxel'}) RETURN d.target").single()["d.target"])

    # 4. 임상시험 조회
    print("\n4️⃣ 임상시험 샘플 (5개):")
    result = session.run(
        """
        MATCH (t:Trial)
        RETURN t.nct_id AS nct_id, t.title AS title
        LIMIT 5
        """
    ).data()

    for row in result:
        print(f"  - {row['nct_id']}: {row['title'][:60]}...")

    # 5. 병원 조회
    print("\n5️⃣ 병원 샘플 (5개):")
    result = session.run(
        """
        MATCH (h:Hospital)
        RETURN h.name AS name, h.region AS region
        LIMIT 5
        """
    ).data()

    for row in result:
        print(f"  - {row['name']} ({row['region']})")

driver.close()
