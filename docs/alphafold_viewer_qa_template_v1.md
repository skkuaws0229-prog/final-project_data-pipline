# AlphaFold viewer QA template v1

작성일: 2026-05-14

## 목적

프론트엔드에서 27개 AlphaFold `.cif` 구조 파일이 실제 viewer에서 정상 렌더링되는지 기록하기 위한 QA 양식이다.

API 기준으로는 27개 구조가 모두 `available`이고 `/api/structures/{structure_id}/file` checksum 검증도 통과했다.

이 문서는 브라우저 viewer 렌더링까지 확인하기 위한 별도 QA 기록이다.

## QA 대상

```text
GET /api/structures/targets?limit=200
```

`structure_status=available`인 27개 row.

## QA 컬럼

```text
structure_id
gene_symbol
uniprot_id
diseases
viewer_library
viewer_load_status
load_time_ms
render_status
error_message
tested_by
tested_at
notes
```

## 상태값

```text
viewer_load_status:
  pass
  fail
  partial
  not_tested

render_status:
  visible
  blank
  slow
  error
  not_tested
```

## 권장 QA 흐름

```text
1. GET /api/structures/targets?limit=200
2. available row 선택
3. GET /api/structures/{structure_id}
4. viewer에 GET /api/structures/{structure_id}/file URL 전달
5. 구조가 보이면 pass/visible
6. 빈 화면, 파싱 오류, CORS, timeout은 fail 또는 partial로 기록
```

## 우선 확인할 대표 target

```text
JAK1   af_p23458_f1_v6
EGFR   af_p00533_f1_v6
TP53   af_p04637_f1_v6
MTOR   af_p42345_f1_v6
KDR    af_p35968_f1_v6
```

## 산출물

프론트 QA 결과는 아래 CSV 형식으로 저장한다.

```text
10_alphafold/alphafold_viewer_qa_results_v1.csv
```
