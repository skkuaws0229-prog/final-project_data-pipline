# LIHC v2 — S3 재현 번들 (Handoff)

## 목적
원본 레포/원본 데이터 폴더는 **수정·삭제하지 않고**, 재현에 필요한 산출물만 **복사본**으로 묶어 S3에 올린다.

## S3 위치 (기본)
- 버킷 접두: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/`
- 번들 업로드 경로: `generated/repro_<RESULT_TAG>_<STAMP>/`
- 예시 (`RESULT_TAG=20260428_liver_step4_v2`, `STAMP=20260429`):
  - `.../generated/repro_20260428_liver_step4_v2_20260429/`

## 로컬에서 번들 만들기
```bash
cd "/path/to/Liver cancer"
chmod +x scripts/package_lihc_v2_repro_bundle.sh scripts/upload_lihc_v2_repro_to_s3.sh
STAMP=20260429 RESULT_TAG=20260428_liver_step4_v2 RUN_ID=step4_lihc_v2_manual bash scripts/package_lihc_v2_repro_bundle.sh
```

생성 디렉터리: `s3_staging_upload/repro_20260428_liver_step4_v2_<STAMP>/`  
- `stad_results_*`: Step4 OOF·메트릭·앙상블 CSV·JSON  
- `stad_data_*`: 학습용 `y_train`, `X_*.npy`, `drug_features.parquet` 등  
- `liver_processed_snapshot/`: STAD가 참조하는 `train_table`, `model_inputs` 스냅샷  
- `stad_scripts_snapshot/`: 앙상블·Top30 tier 스크립트 복사본  
- `liver_cancer_results_*` / `liver_cancer_external_validation_*`: Liver 패키지 산출  
- `REPRO_MANIFEST.json`: 파일 목록 메타  

선택: `~/Downloads/LIHC_v2_ensemble_directive.md` 가 있으면 `protocol_used_files/docs/` 아래로 복사된다.

## 업로드
```bash
STAMP=20260429 RESULT_TAG=20260428_liver_step4_v2 bash scripts/upload_lihc_v2_repro_to_s3.sh
```
요구: AWS CLI 권한 (`aws s3 sync`).

## S3에 이미 있는 문서와의 관계
- `protocol_used_files/docs/LIHC_ensemble_directive.md` (v1 이름) 등은 **별도 경로**에 있을 수 있다.
- 업로드 스크립트는 (가능 시) 해당 객체를 번들 내 `protocol_mirror/` 에 **복사본**으로 추가한다.

## 재현 시 필요한 추가물 (번들 외)

### 실행 환경
- 동일(또는 호환) 커밋의 `20260421_new_pre_project_biso_STAD` + `Liver cancer` 스크립트  
- Python 의존성: pandas, numpy, scipy, scikit-learn, xgboost, lightgbm, catboost, torch(학습 시), rdkit 등 — **버전은 재현자가 맞춤**

### Step6 외부 소스 (팀 공유 시 S3 업로드 → 로컬 동기화)

스크립트는 **`Liver cancer` 프로젝트 루트** 기준으로만 읽는다:

`external_validation/<RESULT_TAG>/sources/` 아래 **하위 디렉터리**:

| 하위 폴더 | 용도 |
|-----------|------|
| `depmap_prism/` | PRISM 참조 CSV (`lihc_drug_names_reference_*.csv` 등) |
| `clinicaltrials/` | ClinicalTrials 스크래프트 JSON |
| `geo_gse14520/` | GSE14520 종양 매트릭스 CSV (스크립트에 파일명 고정) |
| `cosmic/` | Cancer Gene Census tar 등 |
| `opentargets/` | OpenTargets association 등 스크립트가 기대하는 파일 |

- 소스가 **없으면** 해당 채널은 `PENDING_DATA` 이고 증거 플래그는 채워지지 않는다.  
- **S3에만 올려두고 끝이 아니라**, 재현 시 `aws s3 sync s3://…/external_validation_sources/<RESULT_TAG>/ sources/` 형태로 **로컬 위 경로에 받은 다음** Step6를 실행한다 (prefix는 팀 규칙으로 정하면 됨).  
- **CPTAC** 은 본 스크립트에서 정책상 제외(`EXCLUDED_BY_REQUEST`)로 고정이다.
