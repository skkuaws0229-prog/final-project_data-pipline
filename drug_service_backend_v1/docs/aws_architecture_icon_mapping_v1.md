# AWS architecture icon mapping v1

## Draw.io file

```text
docs/aws_architecture_drug_repurposing_v1.drawio
```

이 파일은 diagrams.net(draw.io)에서 바로 열 수 있는 초안이다.

## 권장 AWS 아이콘 교체표

| 현재 박스 | 권장 아이콘 |
|---|---|
| Researcher Browser / React Frontend | User / Client / Web app |
| Amazon EC2 Docker Runtime | Amazon EC2 |
| FastAPI Backend | Amazon EC2 또는 Container |
| PostgreSQL | Amazon RDS for PostgreSQL 또는 PostgreSQL on EC2 |
| Neo4j | Amazon EC2 또는 Database custom icon |
| OpenSearch | Amazon OpenSearch Service |
| Amazon S3 Data Lake | Amazon S3 |
| AWS Lambda | AWS Lambda |
| AWS Step Functions | AWS Step Functions |
| Amazon SageMaker | Amazon SageMaker |
| Amazon Bedrock | Amazon Bedrock |
| GitHub Repository | GitHub icon |
| Google Cloud Storage Backup | Google Cloud Storage 또는 external backup |

## 현재 구현 기준

현재 live path:

```text
React Frontend
-> FastAPI :8010
-> PostgreSQL / Neo4j / OpenSearch
-> S3 artifacts
```

현재 backend API:

```text
/diseases
/v1/diseases/{disease}/final-candidates
/api/diseases/{disease}/summary
/api/graph/{disease}/ui-basic
/api/image-modal/{disease}
/api/structures/*
/search
/api/explanation-context
/api/assistant/*
/api/pipeline-runs/*
```

Feature-flagged or future path:

```text
S3 upload
-> Lambda
-> Step Functions
-> SageMaker
-> S3 results
-> FastAPI internal ingest
```

RAG/LLM path:

```text
PostgreSQL + Neo4j + OpenSearch + AlphaFold metadata
-> /api/explanation-context
-> Bedrock prompt context
-> frontend/chatbot answer
```

## 수정 추천

발표용으로 다듬을 때는 아래 순서가 좋다.

```text
1. 각 박스를 AWS 아이콘으로 교체
2. Docker Compose 내부는 EC2 안쪽에 묶기
3. 현재 구현 완료 path는 실선
4. Step Functions/SageMaker/Bedrock은 점선 또는 "planned" 라벨 유지
5. GCS 백업은 AWS 외부 영역으로 분리
```
