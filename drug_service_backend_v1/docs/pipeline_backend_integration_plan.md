# 파이프라인 백엔드 연결 준비 계획

## 목적

현재 프로젝트는 Neo4j/KG 구축 단계에 있다. Bedrock/RAG/LLM 챗봇을 붙이기 전에, 약물 재창출 파이프라인을 백엔드 API에서 실행 요청하고 상태를 조회할 수 있는 제어 계층을 먼저 준비한다.

이번 단계에서는 실제 SageMaker, Step Functions, local agent 실행을 하지 않는다. 비용이 발생하는 작업은 모두 feature flag 뒤에 두고, `mock` backend만 동작하게 한다.

## 목표 아키텍처

```text
Frontend / Chatbot
  ↓
Backend API
  ↓
Pipeline Run DB
  ↓
Pipeline Orchestrator Adapter
      ├─ mock
      ├─ local_agent
      └─ aws_stepfunctions
  ↓
S3 / SageMaker / Step Functions / Local Agent
```

챗봇은 파이프라인을 직접 실행하지 않는다. 챗봇은 백엔드 API만 호출한다.

## 현재 전제

- 파이프라인 코드는 `final-project_data-pipline/pipeline/`에 있다.
- 로컬 실행 프로토콜은 `pipeline/README_local_agent.md`를 따른다.
- AWS 실행 프로토콜은 `pipeline/sagemaker/README_sagemaker.md`, `pipeline/sagemaker/automation_protocol.md`를 따른다.
- Bedrock/RAG/LLM 연결은 이번 단계에서 하지 않는다.

## DB Schema

### pipeline_runs

```text
run_id
disease_name
disease_slug
mode
execution_backend
status
current_step
requested_by
s3_output_prefix
config_snapshot
random_seed
verdict
error_message
estimated_cost_usd
estimated_time_minutes
created_at
started_at
ended_at
updated_at
```

### pipeline_run_events

```text
event_id
run_id
timestamp
level
step
message
payload_json
```

### pipeline_artifacts

```text
artifact_id
run_id
artifact_type
step
name
uri
size_bytes
checksum
created_at
```

### pipeline_configs

```text
config_id
run_id
disease_name
disease_slug
config_yaml
config_hash
created_at
```

## API Endpoint

### Run 생성

```http
POST /api/pipeline-runs
```

기본 `execution_backend`는 `mock`이다.

프론트엔드/챗봇 입력에서는 아래 alias도 허용한다. 단, DB와 API 응답에는 canonical 값만 저장/반환한다.

```text
$ -> mock
@ -> local_agent
# -> aws_stepfunctions
```

```json
{
  "disease_name": "난소암",
  "mode": "full",
  "execution_backend": "mock"
}
```

### Run 상태 조회

```http
GET /api/pipeline-runs/{run_id}
```

### Run 목록 조회

```http
GET /api/pipeline-runs?status=completed&execution_backend=mock&limit=50
```

프론트엔드와 챗봇이 최근 실행 목록을 볼 수 있도록 `disease_slug`, `status`, `execution_backend`, `limit` 필터를 지원한다.
`execution_backend` 필터도 `$`, `@`, `#` alias를 허용한다.

### Run 이벤트 조회

```http
GET /api/pipeline-runs/{run_id}/events
```

### Run artifact 조회

```http
GET /api/pipeline-runs/{run_id}/artifacts
```

### Run 취소

```http
POST /api/pipeline-runs/{run_id}/cancel
```

이번 단계에서는 mock run 상태만 `cancelled`로 바꾼다. 실제 SageMaker stop은 다음 단계에서 구현한다.

### Mock Run 완료 처리

```http
POST /api/pipeline-runs/{run_id}/complete
```

이번 단계에서는 mock run만 수동으로 `completed` 상태로 바꿀 수 있다. 이미 `completed`, `cancelled`, `blocked` 상태인 run은 `409 Conflict`로 거부한다.

## Disease Mapping

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

## Orchestrator Adapter

공통 interface:

```python
class PipelineOrchestrator:
    def submit_run(self, run):
        pass

    def get_status(self, run_id):
        pass

    def cancel_run(self, run_id):
        pass

    def complete_run(self, run_id):
        pass
```

구현체:

```text
MockPipelineOrchestrator
LocalAgentPipelineOrchestrator
AwsStepFunctionsOrchestrator
```

이번 단계에서는 `MockPipelineOrchestrator`만 실제 동작한다.

## Mock 실행 흐름

1. `pipeline_runs`에 row 생성
2. `pipeline_configs`에 config snapshot/hash 저장
3. `pipeline_run_events`에 preflight event 추가
4. status를 `running`으로 변경
5. current_step을 `mock_pipeline`으로 설정
6. mock artifact 2개 생성
7. cancel endpoint 호출 시 status를 `cancelled`로 변경

## Guardrail

- `execution_backend` 기본값은 `mock`
- `local_agent`, `aws_stepfunctions`는 feature flag가 꺼져 있으면 `blocked`
- SageMaker, Step Functions, WSI download, embedding 생성은 실행하지 않음
- 질환명이 mapping에 없으면 `400 Bad Request`
- mode는 `basic`, `image_modal`, `full`만 허용
- secret/API key/token은 DB에 저장하지 않음
- config에는 secret 값이 아니라 secret id만 저장하는 정책을 문서화

## Neo4j/KG와의 관계

이번 단계에서는 pipeline run을 Neo4j에 직접 쓰지 않는다.

추후 확장 가능성:

- `disease_slug`를 KG disease node와 연결
- `drug_name`을 KG drug node와 연결
- `target_gene`를 KG gene/protein node와 연결
- pipeline artifact에서 cluster-drug link를 Neo4j edge로 적재

## Bedrock/RAG/LLM 이전에 필요한 이유

RAG/LLM 챗봇이 파이프라인을 직접 실행하게 만들면 실행 상태, 비용 통제, 중복 job 방지, 실패 복구가 흐려진다. 먼저 백엔드 API와 run DB를 안정화하면 챗봇은 안전한 API만 호출하면 된다.

권장 순서:

```text
DB/API 안정화
-> pipeline run 상태 조회 가능
-> KG query 안정화
-> RAG index 구성
-> Bedrock/LLM chatbot 연결
```

## 다음 단계 TODO

- local_agent backend feature flag 설계 고도화
- aws_stepfunctions backend 연결 시 IAM/preflight 검증 추가
- 실제 SageMaker stop/cancel 연결
- pipeline artifact S3 head/checksum 검증
- pipeline 결과를 Neo4j/OpenSearch에 ingest하는 `/internal/ingest` 계약 설계
