# Lung Cancer Drug Repurposing Pipeline

## Current reproducibility status (2026-04-29)

- Current canonical rerun scope: `Step5 ensemble -> Step6 external validation -> Step7 ADMET/Top15`
- Current Top30 basis: `LUAD 2C directive ensemble`, deduplicated, `canonical_smiles 30/30`
- Current Step6 status: rerun completed on the exact current Top30 package
- Current Step7 status: completed on the current 30-drug input

### Current reproducibility docs

- Protocol: [../reports/lung_reproducibility/LUNG_reproduction_protocol_20260429_v1.md](../reports/lung_reproducibility/LUNG_reproduction_protocol_20260429_v1.md)
- Execution scope: [../reports/lung_reproducibility/lung_step6_step7_execution_scope_20260429.md](../reports/lung_reproducibility/lung_step6_step7_execution_scope_20260429.md)
- Execution report: [../reports/lung_reproducibility/lung_execution_report_20260429.md](../reports/lung_reproducibility/lung_execution_report_20260429.md)
- S3 upload manifest: [../reports/lung_reproducibility/lung_s3_upload_manifest_20260429.md](../reports/lung_reproducibility/lung_s3_upload_manifest_20260429.md)

### Current final outputs

- Step5 ensemble summary: `../reports/lung_directive_ensemble/lung_directive_ensemble_summary.md`
- Step6 package: `../reports/lung_step6_package/lung_step6_package_summary.md`
- Step6 current-package validation: `../reports/lung_step6_current_package/lung_step6_current_package_summary.md`
- Step7 final top15: `results/lung_final_top15.csv`
- Step7 ADMET summary: `results/lung_admet_summary.json`

## 프로젝트 개요
- **질병**: Lung Cancer (폐암)
- **샘플 수**: 125,427
- **최종 Feature 수**: 5,761 (원본 20,512에서 71.9% 감소)
- **데이터 소스**: DepMap (CRISPR, Expression), ChEMBL (Drug), LINCS L1000

## 디렉토리 구조

```
20260416_new_pre_project_biso_Lung/
├── scripts/                    # Nextflow FE pipeline & 데이터 처리 스크립트
│   ├── main.nf                # Feature Engineering 워크플로우
│   ├── nextflow.config        # AWS Batch 설정
│   └── *.py, *.sh            # 데이터 처리 스크립트
├── results/                    # ML 학습 결과 (부분)
│   └── lung_numeric_ml_v1_oof/ # Out-of-fold predictions
├── reports/                    # QC 및 검증 리포트
├── run_ml_all.py              # ML 모델 학습 메인 스크립트
├── run_phase2a_only.py        # Phase 2A 전용 래퍼 스크립트
├── feature_selection_log.json # Feature selection 상세 기록
├── drug_repurposing_pipeline_protocol.md  # 전체 파이프라인 프로토콜
└── README.md                  # 본 문서
```

## ⚠️ GitHub에 업로드되지 않은 대용량 파일

GitHub의 파일 크기 제한(100MB)으로 인해 다음 파일들은 `.gitignore`에 포함되어 업로드되지 않았습니다.

### 1. 원본 데이터 (Raw Data)
**위치**: `curated_data/`
**크기**: 17 GB
**내용**:
- DepMap CRISPR gene dependency 데이터
- DepMap Expression 데이터
- ChEMBL drug information
- LINCS L1000 drug signatures

**재생성 방법**:
```bash
# Nextflow 파이프라인의 prepare_fe_inputs 스테이지 실행
cd scripts/
nextflow run main.nf -resume -process.name prepare_fe_inputs
```

### 2. ChEMBL 임시 파일
**위치**: `temp_chembl/`
**크기**: 19 GB
**내용**: ChEMBL SQLite 데이터베이스 추출 중간 파일

**재생성 방법**:
```bash
python scripts/extract_chembl_from_sqlite.py
```

### 3. Feature Engineering 결과
**위치**: `fe_qc/`
**크기**: 280 MB
**내용**:
- `features.parquet` - CRISPR + Drug 기본 features (125,427 × 18,441)
- `labels.parquet` - Regression labels (IC50 값)
- `pair_features.parquet` - LINCS drug signatures (125,427 × 2,075)

**재생성 방법**:
```bash
# AWS Batch에서 Nextflow 전체 파이프라인 실행
cd scripts/
nextflow run main.nf -resume
```

**S3 위치**: `s3://say2-4team/skku_aws2_14/20260416_new_pre_project_biso_Lung/fe_output/20260416_lung_fe_v1/`

### 4. Feature Selection 결과
**위치**: 현재 디렉토리
**크기**: 35 MB
**파일**: `features_slim.parquet`

**내용**: Feature selection 완료된 데이터 (125,427 × 5,766)
- Gene (CRISPR): 4,703
- Morgan FP: 1,032
- LINCS + Target + Pathway + Drug: 29
- Metadata: 2 (sample_id, canonical_drug_id)

**재생성 방법**:
```python
# Feature selection 스크립트 실행 (약 30분 소요)
# fe_qc/features.parquet + fe_qc/pair_features.parquet 필요
python -c "
import pandas as pd
import numpy as np
from sklearn.feature_selection import VarianceThreshold

# 1. 데이터 병합
df_features = pd.read_parquet('fe_qc/features.parquet')
df_pairs = pd.read_parquet('fe_qc/pair_features.parquet')
df_merged = pd.merge(df_features, df_pairs, on=['sample_id', 'canonical_drug_id'])

# 2. Feature selection (프로토콜 Section 7 참조)
# - Gene: Low variance + High correlation
# - Morgan: Low variance + High correlation
# - LINCS/Target/Pathway/Drug: Keep all

# 3. 저장
df_slim.to_parquet('features_slim.parquet')
"
```

### 5. 학습 데이터 (NumPy)
**위치**: `data/`
**크기**: 4.6 GB
**파일**:
- `X_numeric.npy` - 2.7 GB (125,427 × 5,761, float32)
- `y_train.npy` - 490 KB (125,427,, float32)

**재생성 방법**:
```python
import numpy as np
import pandas as pd

# features_slim.parquet에서 변환
df = pd.read_parquet('features_slim.parquet')
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
feature_cols = [c for c in numeric_cols if c not in ['sample_id', 'canonical_drug_id']]

X = df[feature_cols].values.astype(np.float32)
np.save('data/X_numeric.npy', X)

# labels.parquet에서 변환
df_labels = pd.read_parquet('fe_qc/labels.parquet')
y = df_labels['label_regression'].values.astype(np.float32)
np.save('data/y_train.npy', y)
```

### 6. 로그 파일
**위치**: `logs/`
**크기**: 9.5 MB
**내용**: Nextflow 실행 로그, AWS Batch 작업 로그

**참고**: 로그는 재생성 불필요하며, 필요 시 AWS CloudWatch에서 확인 가능

## Feature Selection 결과

상세 내용은 `feature_selection_log.json` 참조

| Feature Type | 원본 | 최종 | 제거율 |
|-------------|------|------|--------|
| Gene (CRISPR) | 18,435 | 4,703 | 74.5% |
| Morgan FP | 2,048 | 1,032 | 49.6% |
| LINCS + Other | 29 | 29 | 0% |
| **합계** | **20,512** | **5,764** | **71.9%** |

**제거 기준**:
- Low variance: variance < 0.01
- High correlation: Pearson correlation > 0.95

## Phase 2A ML 모델 학습

### 모델 구성 (6개)
1. LightGBM
2. LightGBM DART
3. XGBoost
4. CatBoost
5. RandomForest
6. ExtraTrees

### 평가 방식 (3개)
1. **Holdout**: 8:2 train-test split
2. **5-Fold CV**: Stratified cross-validation
3. **GroupCV**: canonical_drug_id 기준 3-fold (unseen drug generalization)

### 실행 방법
```bash
# Phase 2A만 실행
python run_phase2a_only.py

# 또는 전체 Phase (2A, 2B, 2C)
python run_ml_all.py
```

### 필요 패키지
```bash
pip install lightgbm xgboost catboost scikit-learn pandas numpy
```

## 데이터 접근

### AWS S3
```bash
# Feature Engineering 결과 다운로드
aws s3 sync s3://say2-4team/skku_aws2_14/20260416_new_pre_project_biso_Lung/fe_output/20260416_lung_fe_v1/ ./fe_qc/
```

### 로컬 재생성
전체 파이프라인을 로컬에서 재실행하려면:
1. `scripts/nextflow.config`에서 AWS Batch 설정 제거
2. `nextflow run scripts/main.nf` 실행 (로컬 모드)

## 문의
프로젝트 관련 문의사항은 GitHub Issues에 등록해주세요.
