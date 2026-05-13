# PostgreSQL 우선 적재

이 디렉터리는 PostgreSQL 적재 검증만 담당합니다. Neo4j, TxGNN, OpenSearch는 canonical relational load가 검증된 이후 단계에서 진행합니다.

## 로컬 검증

```bash
cd drug_service_build/04_db_load
docker compose -f docker-compose.postgres.yml up -d
bash load_postgres.sh
```

현재 11개 질병 S3 selection 기준 기대 row count:

```text
diseases: 11
drugs: 171
drug_candidates: 255
admet_results: 255
```

## AWS/S3 기준 경로

원본 기준 경로:

```text
s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/
```

빌드 작업공간:

```text
s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/
```

`OV`, `SKCM`은 의도적으로 제외했으며, 최종 대상 질병은 11개입니다.
