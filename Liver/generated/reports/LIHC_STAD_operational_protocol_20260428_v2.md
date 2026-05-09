# LIHC-STAD Operational Protocol v2 (No Overwrite)

## A. Scope
- This protocol is a **new v2 track**.
- Existing v1 outputs and docs remain unchanged.
- Objective: start from expanded LIHC candidate pool, then re-run Step4~Step7.

## B. v2 Runtime Inputs
- Candidate pool builder:
  - `scripts/build_v2_candidate_pool_lihc.py`
- Generated v2 pool artifacts:
  - `results/lihc_candidate_pool_v2.csv`
  - `results/lihc_top50_candidate_pre_step4_v2.csv`
  - `results/lihc_v2_candidate_pool_summary.json`

## C. v2 Execution Policy
1. Expand LIHC drug library with HCC approved set (no changes to v1 files).
2. Regenerate model-scoring input rows from expanded pool.
3. Run Step4/5 using v2 tag and write only `*_v2` outputs.
4. Run Step6/7 with v2 inputs and write only `*_v2` outputs.

## D. v2 Naming Rule (Mandatory)
- All outputs, reports, summaries, and dashboard artifacts must end with `v2`.
- Do not overwrite any of:
  - v1 files (`*_v1`)
  - previous canonical files from prior runs.

## E. Suggested v2 Output Set
- `results/lihc_top30_v2.csv`
- `results/lihc_top50_v2.csv`
- `results/lihc_final_top15_v2.csv`
- `results/lihc_step7_final_top15_tier4_v2.csv`
- `external_validation/<result_tag>/top30_external_validation_lihc_cptac_excluded_v2.csv`
- `results/lihc_v2_manifest.json`

## F. v2 QC Checklist
- [ ] HCC approved drugs exist in candidate pool (>= 3 target minimum)
- [ ] Sorafenib present in v2 pool and assigned a model-scored rank
- [ ] Top50 includes HCC approved drugs
- [ ] Top30 includes HCC approved drugs
- [ ] Step7 Top15 generated with v2 file names only

## G. Canonical v2 run (Step4 pool / formal retrain line)
- **Result tag:** `20260428_liver_step4_v2`
- **Run id:** `step4_lihc_v2_manual`
- **Eval modes:** `cv5`, `groupcv`, `scaffoldcv` (holdout omitted per v2 lane policy)
- **Metrics review (wide/long):**  
  `20260421_new_pre_project_biso_STAD/reports/step4_metrics_review_20260428_liver_step4_v2*.csv`
- **Directive ensemble (LIHC v2):** 가중 6모델 OOF →  
  `scripts/ensemble_lihc_v2_directive_weighted.py` →  
  `results/20260428_liver_step4_v2/lihc_v2_directive_weighted_ensemble_*.csv`
- **Top30 dedup + Tier1–4 + Sorafenib 앵커(선택):**  
  `scripts/prepare_lihc_v2_top30_dedup_tiered.py`  
  → `results/<tag>/lihc_top30_directive_ensemble_with_names.csv`
- **Tier / 앵커 설정:**  
  `configs/lihc_v2_clinical_tier_overrides.tsv`, `configs/lihc_v2_hcc_approved_anchors.tsv`

## H. S3 재현 번들 (원본 불변, 복사본만 업로드)
- **Handoff 문서:** `reports/LIHC_V2_S3_REPRO_HANDOFF.md`
- **패키징:** `scripts/package_lihc_v2_repro_bundle.sh` → 로컬 `s3_staging_upload/repro_<RESULT_TAG>_<STAMP>/`
- **업로드:** `scripts/upload_lihc_v2_repro_to_s3.sh` →  
  `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_<RESULT_TAG>_<STAMP>/`
- **예시 (업로드 완료):**  
  `.../generated/repro_20260428_liver_step4_v2_20260429/`  
  (포함: `stad_results_*`, `stad_data_*`, `liver_processed_snapshot`, `stad_scripts_snapshot`, `REPRO_MANIFEST.json`, 선택적 `protocol_mirror/LIHC_ensemble_directive_v1_from_s3_docs.md`)

## I. Step6 (LIHC package root 기준)
- Top30 입력: `Liver cancer/results/<RESULT_TAG>/lihc_top30_directive_ensemble_with_names.csv`
- 실행:  
  `python3 scripts/step6_ext_lihc_independent_cptac_excluded.py --project-root . --result-tag <RESULT_TAG>`
- 외부 근거 파일 (선택·팀 공유용): 로컬 경로  
  `external_validation/<RESULT_TAG>/sources/`  
  하위에 최소 `depmap_prism/`, `clinicaltrials/`, `geo_gse14520/`, `cosmic/`, `opentargets/` 를 두면 PRISM·GEO 등이 `OK`로 채워질 수 있다. 파일이 없으면 `PENDING_DATA`.  
  S3에 올려두었다면 재현 시 **`aws s3 sync` 로 위 로컬 경로로 받은 뒤** Step6 실행. 상세 표는 `reports/LIHC_V2_S3_REPRO_HANDOFF.md` 참고.
- 실행 환경(Python 패키지 버전 등)은 재현자가 맞춘다.

## J. 재현 번들과의 관계
- `generated/repro_<RESULT_TAG>_<STAMP>/` 번들은 주로 **Step4·데이터·앙상블 산출**이며, Step6 외부 소스 전체를 반드시 포함하지는 않을 수 있다. 외부 소스는 별도 prefix 업로드 또는 팀 NAS 등 운영 정책에 따른다.
