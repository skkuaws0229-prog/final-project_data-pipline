# Frontend timeout recovery and summary API validation

## 배경

2026-05-19 프론트엔드 5174에서 team API 호출 시 아래 endpoint들이 timeout으로 보고되었다.

```text
GET /health
GET /diseases
GET /v1/diseases/BRCA/final-candidates
GET /api/diseases/BRCA/summary
```

프론트 관측 내용은 TCP 연결은 되지만 0 bytes received 상태였다.

## 원인

로컬 `127.0.0.1:8010` 기준에서도 동일하게 `/health`부터 timeout이 재현되었다.

확인 결과:

```text
8010 listener: Docker Desktop port proxy
Docker CLI: docker ps/logs/stats/version 모두 hang
```

따라서 FastAPI 라우팅 문제가 아니라 Docker Desktop daemon/port proxy hang 상태로 판단했다.

## 조치

1. 멈춰 있던 Docker CLI 조회 프로세스 정리
2. Docker Desktop backend 재기동
3. `docker compose up -d`로 stack 복구
4. API 컨테이너 재빌드
5. 프론트가 호출하던 누락 endpoint 추가

추가된 endpoint:

```text
GET /api/diseases/{disease_code}/summary
GET /v1/diseases/{disease_code}/summary
```

5174 프론트 접근을 위해 CORS 허용 origin도 추가했다.

```text
http://localhost:5174
http://127.0.0.1:5174
http://172.16.0.64:5174
```

## Summary response

`GET /api/diseases/BRCA/summary`는 overview 화면용 요약을 반환한다.

주요 필드:

```text
disease_id
display_name
final_candidate_count
candidate_pool_count
image_evidence_count
image_cluster_count
graph_node_count
graph_edge_count
structure_target_count
available_structure_target_count
top_final_candidates
source_endpoints
status
```

## 검증 결과

LAN IP 기준:

```text
GET http://172.16.0.64:8010/health
-> 200, 31 bytes

GET http://172.16.0.64:8010/diseases
-> 200, 907 bytes

GET http://172.16.0.64:8010/v1/diseases/BRCA/final-candidates
-> 200, 7583 bytes

GET http://172.16.0.64:8010/api/diseases/BRCA/summary
-> 200, 3048 bytes
```

CORS:

```text
Origin: http://172.16.0.64:5174
access-control-allow-origin: http://172.16.0.64:5174
```

DB 핵심 카운트:

```text
diseases = 11
drug_candidates = 255
candidate_pool = 432
candidate_protein_structure_links = 261
```

## 주의

API 재빌드 시 `db-loader`가 재실행되면서 `candidate_protein_structure_links`가 0으로 초기화될 수 있다.

재빌드 후에는 반드시 아래를 확인한다.

```sql
SELECT count(*) FROM candidate_protein_structure_links;
```

기대값:

```text
261
```
