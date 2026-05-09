# LIHC Data + STAD Protocol Execution Report v2

## 1) Purpose
- **Formal v2** 재학습·앙상블·Top30·외부검증 패키지 상태를 기록한다.
- v1 산출물은 덮어쓰지 않는다.

## 2) Locked identifiers
- **result_tag:** `20260428_liver_step4_v2`
- **run_id:** `step4_lihc_v2_manual`
- **S3 repro bundle (example stamp):**  
  `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/`

## 3) Completed (v2 line)
- Candidate pool expansion artifacts (`results/lihc_candidate_pool_v2.csv` 등) — 선행 단계.
- Step4 ML/DL/Graph 재학습 산출: `20260421_new_pre_project_biso_STAD/results/20260428_liver_step4_v2/`
- Step4 메트릭 리뷰 CSV: `reports/step4_metrics_review_20260428_liver_step4_v2*.csv`
- Directive 가중 앙상블 (6-model): `ensemble_lihc_v2_directive_weighted.py`
- Top30 중복 제거 + Tier1–4 + (선택) Sorafenib 앵커: `prepare_lihc_v2_top30_dedup_tiered.py`
- Step6 외부검증 스모크 (소스 미비 시 `PENDING_DATA`):  
  `Liver cancer/external_validation/20260428_liver_step4_v2/`
- **S3 업로드:** 로컬 번들 복사본 → `generated/repro_<tag>_<stamp>/` (원본 레포 파일은 변경 없음)
- **S3 기존 문서 미러:** `protocol_used_files/docs/LIHC_ensemble_directive.md` → 번들 내 `protocol_mirror/LIHC_ensemble_directive_v1_from_s3_docs.md` 복사

## 4) Pending / optional
- Step6 증거 소스 디렉터리 채우기 → PRISM/GEO/ClinicalTrials 등 `OK` 상태.
- Step7 ADMET + Top15를 동일 `result_tag`로 연결하려면 `run_liver_oneclick.sh` 또는 전용 v2 원클릭에서 Top30 경로를 본 v2 CSV로 지정.

## 5) Naming
- 신규 파일은 `*_v2` 또는 태그 디렉터리 (`20260428_liver_step4_v2`) 로 구분한다.
