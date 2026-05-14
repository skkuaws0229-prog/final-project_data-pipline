# Pipeline run requested_by filter 검증 리포트 v1

작성일: 2026-05-14

## 목적

`GET /api/pipeline-runs?requested_by=...` query가 조용히 무시되지 않고 실제 필터로 동작하도록 보강한다.

## 변경 사항

```http
GET /api/pipeline-runs?requested_by=validation-recheck&limit=5
```

`requested_by`는 아래 필터와 조합 가능하다.

```text
disease_slug
status
execution_backend
requested_by
limit
```

## 검증 기준

```text
requested_by=validation-recheck 요청 시 validation-recheck run만 반환
requested_by=preflight-v2-test 요청 시 preflight-v2-test run만 반환
requested_by와 status 조합 필터 정상
```

## 프론트/챗봇 사용 예

```text
GET /api/pipeline-runs?requested_by=frontend&limit=20
GET /api/pipeline-runs?requested_by=chatbot&status=blocked&limit=20
GET /api/pipeline-runs?requested_by=frontend&execution_backend=$&limit=20
```
