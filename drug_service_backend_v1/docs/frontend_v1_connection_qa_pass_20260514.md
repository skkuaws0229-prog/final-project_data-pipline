# Frontend v1 연결 QA 통과 기록

작성일: 2026-05-14

## 목적

프론트엔드 담당자가 `5174` 프론트에서 6개 QA 기준을 확인했고, 현재 기준으로 프론트 v1 연결 QA를 통과 상태로 기록한다.

## QA 판정

```text
Frontend v1 connection QA: PASS
검증 기준: 후보 목록, 전체 후보, 후보 검색 collapse, AlphaFold 구조 proxy, RA graph, 질환 목록
```

## 1. BRCA 기본 Candidates

Endpoint:

```text
GET /v1/diseases/BRCA/final-candidates
```

결과:

```text
rows: 15
drug_name/rank/tier/score 필드 확인
drug_name 중복 없음
```

판정:

```text
PASS
기본 Candidates 화면은 final-candidates를 사용한다.
```

## 2. BRCA 전체 후보 보기

Endpoint:

```text
GET /api/diseases/BRCA/candidates
```

결과:

```text
rows: 60
is_final_candidate=true: 15
is_final_candidate=false: 45
drug_name 중복 없음
```

판정:

```text
PASS
view=all 화면은 broader candidate pool을 사용한다.
final 후보와 broader 후보가 15 vs 60으로 분리되어 있다.
```

## 3. BRCA Oxaliplatin 검색 collapse

Endpoint:

```text
GET /search?q=Oxaliplatin&disease_id=BRCA&doc_type=candidate_pool
```

결과:

```text
화면용 반환: 1개
raw_total: 2
provenance_count: 2
provenance_note: 원천 candidate_pool row 2개에서 집계됨
```

판정:

```text
PASS
중복 2줄 노출이 아니라 1줄 collapse가 맞다.
원천 row 2개는 provenance로 보존된다.
```

## 4. JAK AlphaFold 구조

Target 검색 endpoint:

```text
GET /api/structures/targets?q=JAK
```

결과:

```text
JAK1 검색됨, structure_status=available
JAK2 검색됨, structure_status=available
JAK3 검색됨, structure_status=available
```

JAK1 file proxy:

```text
GET /api/structures/af_p23458_f1_v6/file
```

결과:

```text
정상 응답
Content-Type: chemical/x-cif
Content-Length: 1115383
백엔드 proxy로 viewer 로딩 가능
```

판정:

```text
PASS
프론트 viewer는 S3를 직접 읽지 않고 backend file proxy를 사용한다.
```

주의:

```text
JAK target 검색 예시는 GET /api/structures/targets?q=JAK 기준으로 사용한다.
GET /api/structures?q=JAK는 구조 중심 목록 조회에 사용한다.
```

## 5. RA graph

Endpoint:

```text
GET /graph/relations?disease_id=RA&limit=50
```

결과:

```text
nodes: 71
edges: 132
node label 구분: Disease / Drug / ImageCluster / ImageEvidence / TargetConcept
```

판정:

```text
PASS
graph viewer 연결 기준 응답 형태 정상
```

## 6. 질환 목록

Endpoint:

```text
GET /diseases
```

결과:

```text
11개 질환 응답 확인
```

판정:

```text
PASS
질환 선택 UI 연결 가능
```

## 추가 확인

프론트에서 함께 확인된 사항:

```text
Drug Detail hook error 수정 완료
최종 후보 보기와 전체 후보 약물 보기가 같아 보이던 문제 수정 완료
현재 기준 API는 15 vs 60으로 분리됨
```

## 최종 결론

```text
프론트 v1 연결 QA는 통과로 본다.
후보 목록 정상
후보 검색 collapse 정상
AlphaFold 구조 proxy 정상
RA graph 정상
질환 목록 정상
```

## 다음 단계

```text
1. React v2 화면 구성/UX는 프론트 담당자가 진행
2. 백엔드는 RAG/Bedrock retrieval contract에 맞춰 /api/explanation-context mock endpoint 준비 가능
3. AlphaFold 27개 전체 viewer QA 결과가 오면 pass/fail CSV에 반영
4. EC2 배포 전 API_BASE_URL 전환 계획 별도 문서화
```
