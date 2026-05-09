# STAD 재현 프로토콜 (로컬 실행 기준)

본 문서는 위암(TCGA-STAD) 파이프라인을 Step 0부터 재현할 때의 실행 순서를 정리합니다.  
원칙은 다음과 같습니다.

- 코드: Colon/Lung 선행 구현 재사용
- 데이터: STAD 실제 데이터만 사용
- raw mirror: `curated_data/`는 읽기 전용

## 0. 사전 준비

- 작업 경로: `20260421_new_pre_project_biso_STAD`
- Python: 3.10 (`conda` env `drug4` 권장)
- AWS CLI 인증
- 참조 프로토콜: `/Users/skku_aws2_14/Downloads/drug_repurposing_pipeline_protocol (2).md` (업데이트 중)

## 1. Raw 수집/동기화

### 1-1. 팀 S3 raw mirror 동기화

```bash
cd 20260421_new_pre_project_biso_STAD
./scripts/parallel_download_stad.sh
```

주요 소스:
- `s3://say2-4team/Stad_raw/gdsc/`
- `s3://say2-4team/Stad_raw/depmap/`
- `s3://say2-4team/Stad_raw/cbioportal/stad_tcga_pan_can_atlas_2018/`
- `s3://say2-4team/Stad_raw/geo/{GSE62254,GSE15459,GSE84437}/`
- `s3://say2-4team/Stad_raw/additional_sources/cosmic_stad/`
- `s3://say2-4team/Stad_raw/cptac_stad/pdc_manifests/`

### 1-2. LINCS GSE92742 정렬

`lincs_source.json` 기준 표준은 `GSE92742`입니다.  
`Stad_raw/LInc1000`에 `GSE92742`가 아직 없고 Colon 쪽에 이미 있으면, 로컬 심볼릭 링크로 맞춥니다.

```bash
./scripts/link_lincs_gse92742_from_colon.sh
```

## 2. 전처리 (Step 2)

```bash
./scripts/run_step2_stad.sh
```

생성되는 주요 산출물:
- `curated_data/processed/gdsc/*.parquet`
- `curated_data/processed/depmap/*.parquet`
- `curated_data/processed/chembl/*.parquet`
- `curated_data/processed/drugbank/*.parquet`
- `data/labels.parquet`
- `data/drug_features.parquet`
- `data/drug_target_mapping.parquet`
- `data/lincs_stad.parquet`
- `data/lincs_stad_drug_level.parquet`
- `data/lincs_stad_drug_level_with_crispr_prefix.parquet`
- `reports/step2_integrated_qc_report.json`

### 2.1 depmap 재필터링 (STAD 고유 단계)

`filter_stad_depmap_to_labels.py`는 STAD에서만 수행하는 후처리입니다.

**왜 필요한가:**
Colon/Lung은 depmap cell_line_name이 labels sample_id와 우연히 일치해 문제가 없지만,
STAD는 표기가 달라 FE의 exact string join이 실패합니다.

**동작:**
1. `labels.parquet`의 24 sample_id를 `Model.parquet`과 normalize 매칭
2. 매칭된 cell만 `data/depmap/depmap_crispr_long_stad.parquet` 재저장 (1150→20 cells)
3. depmap cell_line_name을 labels sample_id 형식으로 rename (`KATO III` → `KATOIII`)
4. `data/GDSC2-dataset.parquet`의 cell_line_name도 labels 형식으로 동기화
5. `reports/step2_stad_depmap_refilter.json`에 매핑 내역 저장

**예상 결과:**
- `matched_total`: 24
- `matched_with_crispr`: 20
- `unmatched_crispr`: 4 (`MKN7`, `NUGC4`, `RF48`, `TGBC11TKB` — DepMap CRISPR 데이터 부재, 정당한 drop)
- `output_depmap_cells`: 20
- `gdsc_cells_remapped_count`: 24/24

**⚠️ 결과가 예상과 다르면 Step 3로 넘어가지 마세요:**
- `matched_with_crispr`이 20 미달 → `Model.parquet` 버전 확인
- `unmatched_model_count > 0` → normalize 로직 / Model 무결성 이슈
- `gdsc_cells_unmapped > 0` → GDSC 원본 이름 변경 가능성

## 3. LINCS cell_id 재검증 (GSE92742 only)

후보 리스트를 GSE92742 실데이터(`cell_info`, `sig_info`) 기준으로 재작성합니다.

```bash
python3 scripts/rebuild_stad_lincs_cell_ids_gse92742.py --project-root .
```

필수 산출물:
- `configs/stad_lincs_cell_ids.json` (usable cell만)
- `reports/lincs/stad_lincs_cell_id_review.csv`
- `reports/lincs/stad_lincs_cell_id_qc.json`
- `logs/rebuild_stad_lincs_cell_ids_*.log`

## 3-1. FE 실행 (Step 3) — AWS Batch

Nextflow awsbatch executor는 S3 작업 디렉터리가 필수입니다.  
반드시 `-work-dir` 옵션을 붙여 실행하세요.

실행:

```bash
cd 20260421_new_pre_project_biso_STAD/nextflow
nextflow run main.nf -profile awsbatch \
  -work-dir s3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/work \
  -resume
```

전제 조건:
- `./scripts/upload_stad_data_to_s3.sh` 로 `data/` 업로드 완료
- `aws sts get-caller-identity` 로 Batch/ECR 접근 가능 확인
- `queue=team4-fe-queue-cpu`, `container=fe-v2-nextflow:v2-pip-awscli` 상태 정상

산출물 (`s3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/fe_output/20260421_stad_fe_v1/`):
- `features/features.parquet`
- `pair_features/pair_features_newfe_v2.parquet`
- `reports/fe_report_20260421_stad_fe_v1.html`

최초 실행 이력: 2026-04-21

## 3-2. Feature Selection (Step 3.5)

**스크립트**: `scripts/feature_selection.py` (Colon에서 복사, Lung 로직 100% 재현)

**실행**:

```bash
python3 scripts/feature_selection.py \
  --features fe_qc/20260421_stad_fe_v1/features/features.parquet \
  --pair-features fe_qc/20260421_stad_fe_v1/pair_features/pair_features_newfe_v2.parquet \
  --output-dir fe_qc/20260421_stad_fe_v1 \
  --low-var-threshold 0.01 \
  --high-corr-threshold 0.95
```

**산출물**: `fe_qc/20260421_stad_fe_v1/` 하위
- `features_slim.parquet` (모델 학습 입력)
- `feature_selection_log.json` (단계별 로그)
- `feature_categories.json`, `final_columns.json`, `selection_log_init.json`

**실적** (2026-04-21):
- initial: 19998 cols → final: 5008 cols (감축률 75.0%)
- rows: 5118 유지

**Step 4 입력 경로**: `fe_qc/20260421_stad_fe_v1/features_slim.parquet`

## §3.5 학습 / 앙상블 (Step 3.5~5) — 대장암 완료 후 이식 예정

**프로토콜 기반:** v2.4 (2026-04-21, Scaffold Split 공식화)

#### STAD 실행 순서 (ML → DL → Graph, Scaffold 처음부터 포함)

대장암(Colon)은 모델 측정 진행 중간에 Scaffold split이 사후 도입되어
실행 순서가 꼬임(ml/dl 측정 후 역으로 scaffold 추가 등).
STAD는 **Colon 구현 완료 후** 깔끔한 순서로 이식한다.

실행 순서:
1. **ML Phase 2A/2B/2C** (Holdout + 5-Fold CV + GroupCV + ScaffoldCV)
2. **DL Phase 2A/2B/2C** (동일 4종 평가)
3. **Graph Phase 2A/2B/2C** (GroupCV + ScaffoldCV, ⚠️ Scaffold 해석 주의)
4. **앙상블 (Phase 3)**: 결과 통합, Top30 추출
5. **최종 종합 평가 (Phase 2 comprehensive metrics)**

#### 이식 대상 구현 (Colon에서 작업 중)

- 전체 실험: Phase 2A/2B/2C × (ML 6 + DL 7 + Graph 2) = 45 실험
- 평가 방식 4종:
  - Holdout (train:test = 8:2)
  - 5-Fold CV (일반 KFold)
  - GroupCV (drug split, canonical_drug_id 기준 3-fold)
  - **ScaffoldCV (v2.4 신규, Murcko scaffold 기준 3-fold)**

#### Scaffold Split 구현 (Colon 참조)

핵심 스크립트 (Colon에서 이식 예정):
- `compute_scaffolds.py` — RDKit MurckoScaffoldSmiles 계산
- `run_ml_scaffold_all.py` — ML 6 모델 × 3 Phase
- `run_dl_scaffold_all.py` — DL 7 모델 × 3 Phase
- `run_graph_scaffold_all.py` — Graph 2 모델 × 3 Phase

설정:
- `eval_mode='scaffoldcv'`
- 결과 파일 접미사: `_scaffoldcv.json`
- GroupKFold 구조는 drug split과 동일, `groups` 파라미터만 scaffold_id로 교체

#### ⚠️ Graph + Scaffold 해석 주의 (v2.4 §8-2)

Graph 모델(GraphSAGE, GAT)에 Scaffold split 적용 시, **KNN graph의 edge가
scaffold 경계를 넘을 수 있음** (transductive 특성상 val 노드가 train 노드의
이웃이 될 수 있음). 이로 인해:

- 완전히 엄격한 scaffold 검증은 불가능
- **상대적 비교**는 유효
- 결과 해석 시 반드시 "Graph+Scaffold는 상대 비교만" 명시할 것

#### STAD 적용 예상

- labels: 24 cells, 20 CRISPR 포함, 295 drugs
- Scaffold 수: Colon 결과 참고 후 Step 3.5 진입 시점에 업데이트
- 예상 산출: `results/stad_top30_phase2b_catboost_with_names.csv`,
  `stad_top30_phase2c_catboost_with_names.csv`,
  `stad_top30_unified_2b_and_2c_with_names.csv` (Step 6 전제)

#### STAD 적용 시점

- **Colon Step 4 완료 후** 시작
- Colon의 `run_*_scaffold_all.py` 등을 STAD 경로로 이식
- STAD는 Colon의 retrofitting 순서 꼬임 없이 처음부터 ML→DL→Graph 순서로 깔끔히 실행

## 4. 외부검증 (Step 6)

Step 6 실행 전, 학습 산출 Top30 CSV 3종이 필요합니다.

- `results/stad_top30_phase2b_catboost_with_names.csv`
- `results/stad_top30_phase2c_catboost_with_names.csv`
- `results/stad_top30_unified_2b_and_2c_with_names.csv`

실행:

```bash
SYNC_S3=1 ./scripts/run_step6_stad.sh
```

## 5. 알려진 제한 사항 (현재 확정)

LINCS evidence in STAD is AGS-only under GSE92742 (362 trt_cp signatures).  
This limitation has been triple-verified (2026-04-21):  
(a) GSE92742 primary_site/subtype strict: AGS only  
(b) GSE70138 phase II plate: AGS present but 0 trt_cp; merge/replace yields no gain  
(c) Deep alias/normalize/substring check: no missed stomach cells  
Downstream interpretation relies more heavily on DepMap/GDSC/PRISM axes  
for drug repurposing evidence, with LINCS used as supporting signal for AGS only.

근거 문서:
- `reports/lincs/stad_lincs_cell_id_qc.json` (1차 검증)
- `reports/lincs/stad_lincs_gse70138_verification.json` (2차 검증)
- `reports/lincs/stad_lincs_alias_deep_check.json` (3차 검증)

## 6. 운영 체크리스트

### 6.1 Step 2 완료 후 (Step 3 진입 전 반드시 확인)

기본:
- [ ] `reports/step2_integrated_qc_report.json`: `passed=true`
- [ ] `reports/step2_integrated_qc_report.json`: `warnings=[]` 또는 info-level만
- [ ] `reports/step2_integrated_qc_report.json`: `labels_cells_in_depmap=20`
- [ ] `reports/step2_integrated_qc_report.json`: `labels_not_in_depmap=4` (`MKN7`, `NUGC4`, `RF48`, `TGBC11TKB`)

depmap 재필터링:
- [ ] `reports/step2_stad_depmap_refilter.json`: `matched_with_crispr=20`
- [ ] `reports/step2_stad_depmap_refilter.json`: `output_depmap_cells=20`
- [ ] `reports/step2_stad_depmap_refilter.json`: `gdsc_cells_unmapped_count=0`
- [ ] `data/depmap/depmap_crispr_long_stad.parquet` 존재 (수 MB, 재필터 후)

정합성:
- [ ] `data/GDSC2-dataset.parquet` 샘플 확인 (cell_line_name이 labels 형식)
- [ ] `curated_data/` 수정/삭제 안 함

### 6.2 Step 3 완료 후

실행:
- [ ] Nextflow exit code = 0
- [ ] S3 `fe_output/20260421_stad_fe_v1/` 존재

핵심 수치 (`work/.../join_qc_report.json`):
- [ ] `labels_unique_samples=24`
- [ ] `sample_features_rows=20`
- [ ] `join_rate_samples >= 0.83`
- [ ] `unmatched_drugs=0`

FE 품질 (`features/manifest.json`):
- [ ] `features_rows ~= 5,118` (±100)
- [ ] `features_cols ~= 17,925`
- [ ] `dropped_high_missing_count=0`
- [ ] `dropped_low_variance_count < 100`

### 6.3 LINCS 확인

- [ ] `reports/lincs/stad_lincs_cell_id_qc.json` 존재 (1차 검증)
- [ ] `reports/lincs/stad_lincs_gse70138_verification.json` 존재 (2차 검증)
- [ ] `reports/lincs/stad_lincs_alias_deep_check.json` 존재 (3차 검증)
- [ ] README/protocol에 AGS-only 한계 명시됨
- [ ] 해석이 DepMap/GDSC/PRISM 축 중심임을 문서화

## 7. 과거 이슈 및 재발 방지

### 7.1 2026-04-21: Step 2 QC 경고 경시로 Step 3 37% row loss

**무슨 일이 있었나:**
Step 2 QC에서 "19 label sample_id not in depmap" 경고 발생.
Colon의 labels_sample_id_duplicate_rows 지표(9657/9692)와 비슷한 패턴이라고 판단하고
Step 3 진입. → Step 3에서 features_rows가 6060 → 3,721로 37% 감소.
원인 규명에 거의 하루 소요.

**실제 원인 (2개 레이어):**
1. **Colon의 경고**: labels_sample_id_duplicate_rows 지표 (pair 중복, 정상)
   **STAD의 경고**: labels_not_in_depmap 지표 (매핑 실패, 심각)
   → 완전히 다른 두 지표를 같은 것으로 잘못 비교함

2. **근본 원인**: Colon은 depmap_long을 수동으로 35 cells로 축소했으나
   (`differences.md` 기록), STAD는 이 단계가 없어서 1150 cells 전체가 FE에 투입됨.
   labels(stripped 형식) vs depmap(원본 형식) exact join 실패.

**해결:**
- `scripts/filter_stad_depmap_to_labels.py` 신규 작성 (Colon 수동 작업의 자동화)
- `run_step2_stad.sh`에 통합
- `step2_qc.py`가 `data/depmap/` 경로 검증하도록 수정
- 재실행 후 `features_rows`: 3,721 → 5,118 (+37.5%), join_rate 61% → 84%

**❌ 재발 방지 원칙 (반드시 지킬 것):**
1. Step 2 QC 경고의 지표 이름과 수치를 **정확히** 읽을 것
2. 다른 암종과 비교할 때는 **같은 이름의 지표**만 비교할 것
3. "패턴이 비슷해 보인다"로 절대 넘기지 말 것. 숫자로 확인할 것.
4. labels_cells_in_depmap은 labels unique cell 수와 같거나 근소 차이여야 함
   - STAD 정상: 20/24 = 83% (4개는 예상 drop)
   - Colon 정상: 35/35 = 100%
5. 지표가 50% 미만이면 Step 3 진입 금지. 원인 규명 먼저.

**근거 문서:**
- `reports/step3_row_drop_analysis.json` (증상)
- `reports/step3_sample_mismatch_diagnosis.json` (매칭 실패 진단)
- `reports/step3_filter_script_deep_diagnosis.json` (Step 2 실행 증거)
- `reports/step3_colon_vs_stad_final_key_check.json` (Colon vs STAD 차이)
- `reports/step3_colon_depmap_workflow_analysis.md` (Colon 수동 작업 증거)
- `reports/step3_fe_gdsc_parquet_check.json` (최종 원인)

### 7.2 Nextflow awsbatch -work-dir 누락

awsbatch 실행은 항상 아래처럼 `-work-dir`를 명시

```bash
cd 20260421_new_pre_project_biso_STAD/nextflow
nextflow run main.nf -profile awsbatch \
  -work-dir s3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/work
```

- **실패 케이스 상세:** 2026-04-21 첫 실행 시
  `When using awsbatch executor an S3 bucket must be provided as working directory` 에러 발생.
