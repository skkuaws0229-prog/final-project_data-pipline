# Pipeline Run Control API 검증 리포트 v1

## 목적

Bedrock/RAG/LLM 챗봇을 붙이기 전에, 백엔드에서 파이프라인 실행 요청과 상태 조회를 받을 수 있는 제어 계층이 동작하는지 확인했다.

이번 검증은 mock backend만 대상으로 하며, SageMaker, Step Functions, Local Agent, WSI 다운로드, 대용량 embedding 생성은 실행하지 않았다.

## 검증 환경

```text
Date: 2026-05-13
API: http://localhost:8010
PostgreSQL: docker compose service postgres
FastAPI: docker compose service api
Execution backend under test: mock
```

## 검증 항목

| 항목 | 결과 | 메모 |
| --- | --- | --- |
| Health check | PASS | `GET /health` 정상 |
| Mock run 생성 | PASS | `POST /api/pipeline-runs` 정상 |
| Run 목록 조회 | PASS | `GET /api/pipeline-runs?limit=1` 정상 |
| Run 상태 조회 | PASS | `GET /api/pipeline-runs/{run_id}` 정상 |
| Run 이벤트 조회 | PASS | `GET /api/pipeline-runs/{run_id}/events` 정상 |
| Run artifact 조회 | PASS | `GET /api/pipeline-runs/{run_id}/artifacts` 정상 |
| Mock run 완료 | PASS | `POST /api/pipeline-runs/{run_id}/complete` 정상 |
| Mock run 취소 | PASS | `POST /api/pipeline-runs/{run_id}/cancel` 정상 |
| AWS backend guardrail | PASS | feature flag 없이 `blocked` 처리 |
| 잘못된 질환명 거부 | PASS | `400 Bad Request` 반환 |
| 중복 완료 거부 | PASS | completed run 재완료 시 `409 Conflict` |
| 비용 발생 작업 미실행 | PASS | SageMaker/Step Functions 호출 없음 |
| Secret 저장 방지 | PASS | config에는 secret 값 저장 없음 |

## 대표 Run

```text
run_id: run_24171fce856a4172
disease_name: 난소암
disease_slug: ov
mode: full
execution_backend: mock
created status: running
current_step: mock_pipeline
cancel status: cancelled
```

## 완료 상태 검증 Run

```text
run_id: run_6de4d9c29734474b
disease_name: 건선
disease_slug: psoriasis
mode: basic
execution_backend: mock
complete status: completed
current_step: completed
verdict: mock_completed
event count: 4
artifact count: 2
```

## 생성된 Mock Artifact

```text
s3_prefix:
  s3://say2-4team/pipeline_results/ov/

validation:
  s3://say2-4team/pipeline_results/ov/validation/ov_mock_validation_report.md
```

## Guardrail 검증

`execution_backend=aws_stepfunctions`로 요청했을 때 실제 AWS job은 실행되지 않았고, run 상태는 아래처럼 차단되었다.

```text
status: blocked
current_step: guardrail
error_message: aws_stepfunctions backend disabled
```

## 결론

Pipeline run control API v1은 현재 단계의 완료 기준을 만족한다.

```text
- DB schema 초안 생성 완료
- endpoint 계약 문서 작성 완료
- mock orchestrator 동작 확인 완료
- run 생성/상태조회/이벤트조회/artifact조회 확인 완료
- run 목록조회/완료처리/중복완료 guardrail 확인 완료
- 실제 AWS/SageMaker job 미실행 확인 완료
- Bedrock/RAG/LLM 이전 단계임을 문서화 완료
```

다음 단계에서는 실제 실행 backend를 붙이기 전에 feature flag, 권한 사전검사, 예상 비용/시간 산정, 취소 정책을 먼저 확정해야 한다.
