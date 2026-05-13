# Drug Service DB 자료 v1

이 폴더는 drug recommendation service v1의 DB 적재/검증 자료입니다.

기존 원본 S3 데이터는 수정하지 않고, 아래 11개 질병만 PostgreSQL/Neo4j 적재용으로 정규화한 산출물입니다.

```text
BRCA, Colon, HNSC, IPF, LUNG, Liver, PAH, PDAC, Psoriasis, RA, STAD
```

`OV`, `SKCM`은 의도적으로 제외했습니다.

## 포함 자료

```text
03_normalized/   PostgreSQL 적재용 정규화 CSV
04_db_load/      PostgreSQL schema와 load script
05_validation/   PostgreSQL/API 검증 결과
06_graph/        Neo4j graph schema, import CSV, 검증 결과
```

## 포함하지 않은 자료

아래 자료는 GitHub에 올리지 않고 S3 또는 별도 저장소 기준으로 관리합니다.

```text
WSI 원본 이미지
tile 이미지/좌표
slide embedding .npy
CT-CLIP/UNI2 embedding 원본
Docker volume
PostgreSQL/Neo4j 실제 volume dump
FastAPI/React application 전체 코드
```

## PostgreSQL 적재

PostgreSQL만 먼저 확인하려면 아래 방식으로 실행합니다.

```bash
cd drug_service_db_v1
docker compose -f docker-compose.db.yml up postgres db-loader
```

Host 접속 정보:

```text
host: localhost
port: 5433
database: drug_service
user: drug_service
password: drug_service_local
```

## Neo4j 적재

Neo4j graph까지 확인하려면 아래 방식으로 실행합니다.

```bash
cd drug_service_db_v1
docker compose -f docker-compose.db.yml up neo4j neo4j-loader
```

Neo4j Browser:

```text
http://localhost:7474
username: neo4j
password: drug_service_neo4j
```

## 주요 검증 결과

PostgreSQL v2 기준:

```text
diseases: 11
drugs: 171
canonical_drugs: 170
drug_aliases: 181
disease_aliases: 31
drug_candidates: 255
admet_results: 255
image_modal_sources: 33
image_modal_clusters: 31
image_modal_cluster_members: 1694
image_modal_drug_evidence: 430
image_modal_evidence_drug_matches: 430
image_modal_reports: 14
```

Neo4j v1 기준:

```text
Disease nodes: 11
Drug nodes: 170
TargetConcept nodes: 133
ImageCluster nodes: 31
ImageEvidence nodes: 430
CANDIDATE_FOR edges: 255
SUPPORTS_DRUG edges: 430
MENTIONS_TARGET edges: 542
```

Graph API 검증 기준:

```text
Duplicate node id: 0
Duplicate edge id: 0
Broken edge endpoint: 0
Neo4j import CSV 대비 edge count mismatch: 0
```

상세 검증은 아래 파일을 확인합니다.

```text
05_validation/validation_summary_v2.md
06_graph/validation/graph_validation_summary_v1.md
06_graph/validation/graph_api_validation_v1.md
```

## 주의사항

- 약물 연결 기준은 `canonical_drug_id`입니다.
- `evidence_only` 약물은 main candidate table에는 없고 image-modal evidence에만 있는 약물입니다.
- `TargetConcept`는 아직 raw target/pathway text입니다.
- target 값을 모두 gene으로 간주하면 안 됩니다. gene/pathway/mechanism/free-text 분류는 v2 보강 대상입니다.
- TxGNN 예측 edge는 이 v1 DB 자료에 아직 포함하지 않았습니다. 이후 `TXGNN_PREDICTED_FOR` 관계로 분리해서 추가할 예정입니다.
