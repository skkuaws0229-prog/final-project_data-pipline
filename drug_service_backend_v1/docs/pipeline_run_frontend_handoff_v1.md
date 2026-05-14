# Pipeline Run API 프론트엔드 인수인계 v1

## 목적

이 문서는 React v2 또는 이후 챗봇 UI에서 파이프라인 실행 상태를 조회하기 위한 인수인계 문서다.

현재 API는 실제 SageMaker/Step Functions/Local Agent를 실행하지 않는다. Bedrock/RAG/LLM 챗봇을 붙이기 전에, 프론트엔드가 백엔드의 파이프라인 제어 계층과 먼저 연결되는지 확인하는 단계다.

## 현재 연결 범위

```text
완료:
- pipeline run 생성
- run 목록 조회
- run 상세 상태 조회
- run event timeline 조회
- run artifact 조회
- mock run 취소
- mock run 완료 처리

아직 제외:
- Bedrock 연결
- RAG 연결
- LLM agent 호출
- SageMaker 실제 실행
- Step Functions 실제 실행
- Local Agent 실제 실행
- WSI 다운로드
- 대용량 embedding 생성
```

## API 기본 주소

로컬 개발:

```text
API_BASE_URL=http://localhost:8010
Swagger=http://localhost:8010/docs
```

다른 PC에서 접속:

```text
API_BASE_URL=http://{API_HOST_IP}:8010
```

현재 테스트된 LAN 예시:

```text
API_BASE_URL=http://172.16.0.64:8010
```

## 권장 화면 흐름

```text
1. Run 목록 화면
2. Run 생성 버튼 또는 form
3. Run 상세 panel
4. Event timeline
5. Artifact 목록
6. Mock complete/cancel 버튼
```

프론트 v2에서 꼭 멋있게 만들 필요는 없고, 우선 상태 흐름이 잘 보이는 관리 화면이면 충분하다.

## Endpoint 요약

```text
POST /api/pipeline-runs
GET /api/pipeline-runs
GET /api/pipeline-runs/{run_id}
GET /api/pipeline-runs/{run_id}/events
GET /api/pipeline-runs/{run_id}/artifacts
POST /api/pipeline-runs/{run_id}/complete
POST /api/pipeline-runs/{run_id}/cancel
```

## 1. Run 생성

```http
POST /api/pipeline-runs
```

Request:

```json
{
  "disease_name": "건선",
  "mode": "basic",
  "execution_backend": "mock",
  "requested_by": "frontend"
}
```

필드:

```text
disease_name       required
mode               optional: basic, image_modal, full / default full
execution_backend  optional: mock, local_agent, aws_stepfunctions / default mock
requested_by       optional
random_seed        optional / default 42
config_snapshot    optional object
```

Response 예시:

```json
{
  "run_id": "run_6de4d9c29734474b",
  "disease_name": "건선",
  "disease_slug": "psoriasis",
  "mode": "basic",
  "execution_backend": "mock",
  "status": "running",
  "current_step": "mock_pipeline",
  "s3_output_prefix": "s3://say2-4team/pipeline_results/psoriasis/",
  "verdict": null,
  "error_message": null
}
```

프론트 처리:

```text
- 생성 성공 시 run_id를 저장한다.
- 바로 상세 조회 또는 event/artifact 조회를 호출한다.
- 현재는 mock이므로 생성 직후 running/mock_pipeline 상태가 된다.
- `execution_backend`는 특수문자 alias도 허용한다.
```

```text
$ -> mock
@ -> local_agent
# -> aws_stepfunctions
```

예:

```json
{
  "disease_name": "류마티스 관절염",
  "mode": "full",
  "execution_backend": "$"
}
```

주의:

```text
DB에는 $, @, #가 저장되지 않고 mock/local_agent/aws_stepfunctions로 정규화되어 저장된다.
```

## 2. Run 목록 조회

```http
GET /api/pipeline-runs?limit=20
```

Query:

```text
disease_slug       optional: psoriasis, ra, ov 등
status             optional: running, completed, cancelled, blocked 등
execution_backend  optional: mock, local_agent, aws_stepfunctions 또는 $, @, #
limit              optional: default 50, max 200
```

Response:

```json
{
  "runs": [
    {
      "run_id": "run_6de4d9c29734474b",
      "disease_name": "건선",
      "disease_slug": "psoriasis",
      "status": "completed",
      "current_step": "completed",
      "execution_backend": "mock",
      "verdict": "mock_completed",
      "created_at": "2026-05-13T09:52:10.000000+00:00"
    }
  ]
}
```

프론트 처리:

```text
- 최근 실행 목록 table/list로 표시한다.
- row 클릭 시 run 상세, events, artifacts를 함께 조회한다.
- status별 badge 색상을 나누는 것이 좋다.
```

## 3. Run 상세 조회

```http
GET /api/pipeline-runs/{run_id}
```

프론트 표시 추천:

```text
run_id
disease_name / disease_slug
mode
execution_backend
status
current_step
verdict
error_message
s3_output_prefix
created_at / started_at / ended_at / updated_at
```

## 4. Event Timeline 조회

```http
GET /api/pipeline-runs/{run_id}/events
```

Response:

```json
{
  "run_id": "run_6de4d9c29734474b",
  "events": [
    {
      "timestamp": "2026-05-13T09:52:10.000000+00:00",
      "level": "info",
      "step": "preflight",
      "message": "mock 권한 사전검사 통과",
      "payload_json": {
        "execution_backend": "mock"
      }
    }
  ]
}
```

프론트 처리:

```text
- timestamp 순서대로 timeline 또는 log list로 표시한다.
- level이 warning/error면 강조한다.
- payload_json은 접힘 영역으로 표시하면 된다.
```

## 5. Artifact 조회

```http
GET /api/pipeline-runs/{run_id}/artifacts
```

Response:

```json
{
  "run_id": "run_6de4d9c29734474b",
  "artifacts": [
    {
      "artifact_type": "validation",
      "step": "validation",
      "name": "psoriasis_mock_validation_report.md",
      "uri": "s3://say2-4team/pipeline_results/psoriasis/validation/psoriasis_mock_validation_report.md"
    }
  ]
}
```

프론트 처리:

```text
- artifact_type, step, name, uri를 table로 표시한다.
- 현재 uri는 S3 경로 문자열이다.
- 브라우저에서 바로 열리는 presigned URL은 아직 제공하지 않는다.
```

## 6. Mock 완료 처리

```http
POST /api/pipeline-runs/{run_id}/complete
```

현재는 mock run만 완료 처리할 수 있다.

성공 시:

```json
{
  "status": "completed",
  "current_step": "completed",
  "verdict": "mock_completed"
}
```

주의:

```text
- completed/cancelled/blocked 상태의 run에 다시 complete를 호출하면 409 Conflict
- local_agent/aws_stepfunctions run은 수동 complete 대상이 아님
- 이 버튼은 실제 실행 완료가 아니라 UI 상태 검증용이다.
```

## 7. Mock 취소

```http
POST /api/pipeline-runs/{run_id}/cancel
```

성공 시:

```json
{
  "status": "cancelled",
  "current_step": "cancelled"
}
```

현재 단계에서는 mock run 취소 상태만 검증한다. 실제 SageMaker stop이나 Step Functions stop은 다음 단계에서 별도 구현한다.

## 상태값

```text
queued
preflight
running
waiting_external_job
validating
completed
failed
cancelled
blocked
```

프론트 badge 제안:

```text
queued/preflight: 대기
running/waiting_external_job/validating: 진행 중
completed: 완료
failed: 실패
cancelled: 취소
blocked: 차단
```

## Disease Mapping

run 생성 시 `disease_name`은 아래 한국어 이름을 사용한다.

```text
난소암 -> ov
유방암 -> brca
폐암 -> luad
간암 -> lihc
대장암 -> coad
위암 -> stad
췌장암 -> pdac
두경부암 -> hnsc
특발성 폐섬유증 -> ipf
폐동맥고혈압 -> pah
건선 -> psoriasis
류마티스 관절염 -> ra
```

주의: 현재 후보/React v1의 11개 질환에서는 `OV`, `SKCM`을 제외했지만, pipeline mapping에는 향후 실행 연결을 위해 `난소암 -> ov`가 포함되어 있다.

## Guardrail

프론트에서 반드시 알아야 할 점:

```text
- 기본 execution_backend는 mock이다.
- local_agent/aws_stepfunctions는 아직 실제 실행하지 않는다.
- feature flag가 꺼진 backend는 blocked 상태가 된다.
- blocked는 오류라기보다 안전장치다.
- 비용 발생 작업은 이 단계에서 실행하지 않는다.
- secret/API key는 DB에 저장하지 않는다.
```

## 에러 처리

잘못된 질환명:

```text
HTTP 400
Unsupported disease_name: ...
```

잘못된 mode:

```text
HTTP 400
Unsupported mode: ...
```

없는 run_id:

```text
HTTP 404
Unknown run_id: ...
```

완료 불가능 상태에서 complete:

```text
HTTP 409
Run cannot be completed from status: completed
```

## 로컬 검증 결과

검증일:

```text
2026-05-13
```

확인된 항목:

```text
GET /health 정상
POST /api/pipeline-runs 정상
GET /api/pipeline-runs 정상
GET /api/pipeline-runs/{run_id} 정상
GET /api/pipeline-runs/{run_id}/events 정상
GET /api/pipeline-runs/{run_id}/artifacts 정상
POST /api/pipeline-runs/{run_id}/complete 정상
POST /api/pipeline-runs/{run_id}/cancel 정상
중복 complete 409 확인
aws_stepfunctions feature flag off 상태에서 blocked 확인
DB orphan events/artifacts/configs 0 확인
```

대표 검증 run:

```text
run_id: run_6de4d9c29734474b
disease_slug: psoriasis
status: completed
current_step: completed
verdict: mock_completed
event count: 4
artifact count: 2
```

## 프론트 구현 우선순위

```text
1. GET /api/pipeline-runs 목록 table
2. row 선택 시 GET /api/pipeline-runs/{run_id}
3. event timeline 연결
4. artifact table 연결
5. mock complete/cancel 버튼 연결
6. create run form 연결
```

## 다음 단계에서 논의할 것

```text
- 실제 local_agent 실행 버튼을 언제 열지
- aws_stepfunctions 실행 전 승인 UI가 필요한지
- estimated_cost_usd / estimated_time_minutes 표시 방식
- artifact S3 uri를 presigned URL로 내려줄지
- completed pipeline artifact를 OpenSearch/RAG evidence로 적재할지
- Bedrock 챗봇이 어떤 endpoint까지 호출할지
```
