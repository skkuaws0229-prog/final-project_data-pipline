# LIHC v2 Readiness Checklist

## A. Candidate pool (선행)
- [x] `scripts/build_v2_candidate_pool_lihc.py`
- [x] `results/lihc_candidate_pool_v2.csv`
- [x] `results/lihc_top50_candidate_pre_step4_v2.csv`
- [x] `results/lihc_v2_candidate_pool_summary.json`

## B. Step4 재학습 (`20260428_liver_step4_v2`)
- [x] STAD 결과 디렉터리 존재: `20260421_new_pre_project_biso_STAD/results/20260428_liver_step4_v2/`
- [x] 메트릭 리뷰: `reports/step4_metrics_review_20260428_liver_step4_v2*.csv`

## C. 앙상블 + Top30 + Tier + Sorafenib 앵커
- [x] `ensemble_lihc_v2_directive_weighted.py` 산출 CSV
- [x] `prepare_lihc_v2_top30_dedup_tiered.py` 산출 (`lihc_top30_directive_ensemble_with_names.csv`)

## D. Step6 외부검증
- [x] 실행 가능한 입력 CSV (`Liver cancer/results/<tag>/`)
- [ ] 증거 소스 디렉터리 채움 → PRISM/GEO/ClinicalTrials 등 **OK** (현재 미비 시 PENDING)

## E. S3 재현 번들
- [x] `scripts/package_lihc_v2_repro_bundle.sh` 로컬 스테이징
- [x] `scripts/upload_lihc_v2_repro_to_s3.sh` 업로드 (`generated/repro_<tag>_<stamp>/`)
- [x] 기존 S3 프로토콜 문서 미러 (`protocol_mirror/…`)

## F. Step7 (선택)
- [ ] ADMET22 + Top15 + tier 표 (`run_liver_oneclick.sh` + v2 Top30 경로)
