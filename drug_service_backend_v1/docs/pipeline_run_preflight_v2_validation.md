# Pipeline run preflight v2 검증 리포트

작성일: 2026-05-14

## 목적

챗봇/프론트에서 아래 형태로 질환명 앞에 실행 backend 기호를 붙여 요청할 수 있게 한다.

```text
$질환명 -> mock/preflight
@질환명 -> local_agent
#질환명 -> aws_stepfunctions
```

신규 질환은 바로 실행하지 않고, `needs_registration` 상태로 차단한다.

## 추가 endpoint

```http
POST /api/pipeline-runs/preflight
```

이 endpoint는 DB run을 만들지 않고 실행 가능 여부만 확인한다.

## 기존 run 생성 endpoint 보강

```http
POST /api/pipeline-runs
```

`disease_name`에 `$`, `@`, `#` prefix가 붙어 있으면 backend alias로 해석한다.

예:

```json
{
  "disease_name": "$알츠하이머",
  "mode": "full"
}
```

## 신규 질환 처리 정책

신규 질환은 deterministic slug를 만든 뒤 run을 `blocked`로 저장한다.

예:

```text
알츠하이머 -> new_e533d1ded4eb
```

반환 상태:

```text
status: blocked
current_step: preflight
verdict: needs_registration
error_message: disease registration and input data verification required
```

## Preflight 응답 필드

```text
input_disease_name
disease_name
disease_slug
mode
execution_backend
execution_backend_alias
is_supported_disease
backend_enabled
preflight_status
can_create_run
will_execute
reasons
required_actions
```

## 검증 결과

| 입력 | 결과 | 비고 |
|---|---:|---|
| `$류마티스 관절염` preflight | PASS | 기존 질환, `ready`, `will_execute=true` |
| `$알츠하이머` preflight | PASS | 신규 질환, `needs_registration` |
| `@류마티스 관절염` preflight | PASS | 기존 질환, `backend_disabled` |
| `#알츠하이머` preflight | PASS | 신규 질환, `needs_registration` |
| `$류마티스 관절염` run 생성 | PASS | `mock`, `running`, `mock_pipeline` |
| `$알츠하이머` run 생성 | PASS | `blocked`, `needs_registration` |
| `#알츠하이머` run 생성 | PASS | `aws_stepfunctions`, `blocked`, `needs_registration` |

## 신규 질환 required_actions

```text
register_disease_mapping
confirm_s3_input_prefix
define_column_mapping
run_data_integrity_check
```

## Guardrail

```text
신규 질환은 실제 local/aws 실행으로 넘어가지 않는다.
@/#는 feature flag가 꺼져 있으면 기존 질환도 실제 실행하지 않는다.
비용 발생 AWS job은 실행하지 않았다.
secret/API key는 저장하지 않는다.
```

## 프론트/챗봇 권장 흐름

```text
1. 사용자가 "$알츠하이머" 입력
2. POST /api/pipeline-runs/preflight 호출
3. preflight_status 확인
4. ready면 POST /api/pipeline-runs 생성
5. needs_registration이면 등록 필요 UI 표시
6. backend_disabled이면 feature flag/실행권한 안내
```
