# Neo4j Graph v1

이 폴더는 PostgreSQL 정규화 CSV를 바탕으로 생성한 Neo4j graph 산출물을 보관합니다.

## 진행 순서

```text
1. Graph schema 확정
2. Neo4j import CSV 생성
3. Docker Compose에 Neo4j 추가
4. CSV를 Neo4j에 적재
5. FastAPI graph endpoint 추가
6. Base graph 검증 후 TxGNN prediction edge 추가
```

## Import CSV 생성

```bash
cd drug_service_build
python3 06_graph/build_neo4j_import_csv.py
```

생성 결과:

```text
06_graph/import/
06_graph/validation/graph_import_counts_v1.csv
```

## Schema 문서

```text
06_graph/schema/graph_schema_v1.md
06_graph/schema/neo4j_constraints.cypher
06_graph/schema/neo4j_load_csv_v1.cypher
```

## v1 주의사항

`TargetConcept` 노드는 raw target/pathway text를 그대로 보존합니다. 모든 target을 gene으로 간주하면 안 됩니다. Gene/pathway/mechanism 정규화는 이후 Neo4j/OpenSearch/TxGNN v2 검증 단계에서 진행합니다.

## 로컬 Neo4j 실행

```bash
cd drug_service_build
docker compose up -d neo4j neo4j-loader
```

Neo4j Browser:

```text
http://localhost:7474
```

로그인:

```text
username: neo4j
password: drug_service_neo4j
```

현재 데이터 규모는 `LOAD CSV` 방식으로 충분합니다. 나중에 graph data가 수십만~수백만 node/relationship 이상으로 커지거나 CSV가 수백 MB~GB 단위가 되면, 초기 대량 적재 속도를 위해 `neo4j-admin database import` 방식을 검토합니다.
