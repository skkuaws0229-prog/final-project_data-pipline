# Liver One-Click Runbook v2

## Purpose
LIHC **v2** 라인(`result_tag=20260428_liver_step4_v2`)에서 Step6 이후(ADMET·Top15·tier)까지 동일 정책으로 돌리되, **v1 파일을 덮어쓰지 않는다.**

## S3 재현 번들
- 패키징: `scripts/package_lihc_v2_repro_bundle.sh`
- 업로드: `scripts/upload_lihc_v2_repro_to_s3.sh`
- 설명: `reports/LIHC_V2_S3_REPRO_HANDOFF.md`
- 업로드 예시 prefix:  
  `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_<STAMP>/`

## Step6 — 외부검증 (CPTAC 제외)
프로젝트 루트는 **`Liver cancer`** 폴더.

근거 파일(선택): `external_validation/<RESULT_TAG>/sources/` 아래  
`depmap_prism/`, `clinicaltrials/`, `geo_gse14520/`, `cosmic/`, `opentargets/`  
— 없으면 해당 소스는 `PENDING_DATA`. S3에만 있으면 로컬로 `sync` 후 실행.  
전체 표·설명: `reports/LIHC_V2_S3_REPRO_HANDOFF.md`

```bash
cd "Liver cancer"
python3 scripts/step6_ext_lihc_independent_cptac_excluded.py \
  --project-root . \
  --result-tag "20260428_liver_step4_v2"
```

입력 Top30 (동일 태그 폴더에 있어야 함):  
`results/20260428_liver_step4_v2/lihc_top30_directive_ensemble_with_names.csv`

## Step7 이후 (ADMET / Top15 / tier)
v1 원클릭과 동일 스크립트를 쓰되, **`--top30-csv`** 에 위 경로를 넘긴다.

```bash
cd "Liver cancer"
bash scripts/run_liver_oneclick.sh \
  --top30-csv "${PWD}/results/20260428_liver_step4_v2/lihc_top30_directive_ensemble_with_names.csv" \
  --result-tag "20260428_liver_step4_v2"
```

(`run_liver_oneclick_v2.sh` 는 경로 기본값만 조정한 래퍼로 사용 가능.)

## Naming
- 출력물은 가능하면 파일명·하위폴더에 **`v2`** 또는 **`20260428_liver_step4_v2`** 를 포함한다.
