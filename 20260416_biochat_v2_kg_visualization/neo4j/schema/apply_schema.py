"""Neo4j 스키마(제약조건 + 인덱스) 적재 스크립트"""

from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path
import os

# 프로젝트 루트의 .env 로드
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

URI      = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")


def parse_cypher(file_path: str) -> list[str]:
    """schema.cypher 파일에서 개별 Cypher 문을 파싱"""
    text = Path(file_path).read_text()
    statements = []
    for line in text.split(";"):
        stmt = line.strip()
        # 주석·빈줄 제거
        cleaned = "\n".join(
            l for l in stmt.splitlines() if l.strip() and not l.strip().startswith("//")
        )
        if cleaned:
            statements.append(cleaned)
    return statements


def apply_schema():
    cypher_path = Path(__file__).parent / "schema.cypher"
    statements = parse_cypher(cypher_path)

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결 확인: {URI}")

    with driver.session(database=DATABASE) as session:
        for i, stmt in enumerate(statements, 1):
            label = stmt.split("\n")[0].strip()
            session.run(stmt)
            print(f"  [{i}/{len(statements)}] {label}")

    # 적용 결과 확인
    with driver.session(database=DATABASE) as session:
        constraints = session.run("SHOW CONSTRAINTS").data()
        indexes = session.run("SHOW INDEXES").data()
        print(f"\n✅ 스키마 적용 완료!")
        print(f"   제약조건: {len(constraints)}개")
        print(f"   인덱스  : {len(indexes)}개")

    driver.close()


if __name__ == "__main__":
    apply_schema()
