# 파이프라인 실행 backend alias 검증 리포트 v1

작성일: 2026-05-14

## 목적

프론트엔드/챗봇에서 긴 실행 backend 이름을 직접 입력하지 않아도 되도록 특수문자 alias를 허용한다.

내부 DB와 API 응답은 기존 canonical 값을 유지한다.

## Alias 정책

```text
$ -> mock
@ -> local_agent
# -> aws_stepfunctions
```

## 설계 원칙

- 입력값에서만 alias를 허용한다.
- DB에는 `$`, `@`, `#`를 저장하지 않는다.
- DB에는 `mock`, `local_agent`, `aws_stepfunctions`만 저장한다.
- `config_snapshot.execution_backend_input`에 원 입력값을 보존한다.
- `@`, `#`는 현재 feature flag가 꺼져 있으므로 실제 실행하지 않고 `blocked`로 차단한다.

## 로컬 검증 결과

| 검증 항목 | 결과 | 비고 |
|---|---:|---|
| `$` 입력 | PASS | `execution_backend=mock`, `status=running` |
| `@` 입력 | PASS | `execution_backend=local_agent`, `status=blocked` |
| `#` 입력 | PASS | `execution_backend=aws_stepfunctions`, `status=blocked` |
| 목록 필터 `execution_backend=$` | PASS | mock run 목록 조회 정상 |
| AlphaFold 링크 row 유지 | PASS | 재빌드 후 `candidate_protein_structure_links=261` 복구 확인 |

## 확인된 예시

### `$` mock 실행

```json
{
  "disease_name": "류마티스 관절염",
  "disease_slug": "ra",
  "mode": "full",
  "execution_backend": "mock",
  "status": "running",
  "current_step": "mock_pipeline",
  "config_snapshot": {
    "execution_backend": "mock",
    "execution_backend_input": "$"
  }
}
```

### `@` local agent 차단

```json
{
  "execution_backend": "local_agent",
  "status": "blocked",
  "current_step": "guardrail",
  "error_message": "local_agent backend disabled"
}
```

### `#` AWS Step Functions 차단

```json
{
  "execution_backend": "aws_stepfunctions",
  "status": "blocked",
  "current_step": "guardrail",
  "error_message": "aws_stepfunctions backend disabled"
}
```

## 프론트/챗봇 입력 예시

```text
류마티스 관절염 파이프라인 $ 로 실행해줘
폐암 파이프라인 @ 로 실행해줘
대장암 파이프라인 # 로 실행해줘
```

현재 단계에서는 `$`만 실제 mock 실행으로 진행된다.

`@`, `#`는 향후 local agent 또는 AWS Step Functions feature flag를 명시적으로 켠 뒤에만 실제 실행한다.
